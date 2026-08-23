# -*- coding: utf-8 -*-
"""三尺互证估值方法论模块（方法论升级 v2.1）。

解决两个底层问题：
  1) 盈利端（E）：A股卖方一致预期系统性乐观（东方证券2020实证：利润增速预测
     年年高估，中位数 10%~15%；约八成预测偏乐观）。对一致预期按行业折扣后再入估值。
  2) 倍数端（PE）：历史 TTM 分位单尺定价存在基数错配（spec 3.1/3.2 已确认），
     升级为三把独立尺子互证取中位数：
       · 尺1 公式尺：戈登合理 PE = payout × (1+g) ÷ (r − g)，
         其中 g 为永续增速（配置/长期EPS CAGR/默认2.5%，clamp 至 r−2%），
         禁止用 FY1 短期增速冒充永续——那是与"TTM 冒充预测"同款的口径错配
       · 尺2 同行尺：行业/可比 PE 代理（显式传入 peer_industry_pe，缺失即跳过）
       · 尺3 历史尺：5年 TTM 分位 P25/P50/P75（保留，重塑带宽 + 护栏）

融合纪律（只降不升）：
  · 任两尺分歧 > 1.8× → warn MULTIPLE_SOURCE_DIVERGENCE → 引擎强制 reference_only
  · 融合后中枢 = 可用候选的中位数；带宽按历史分位相对形状重塑，
    并夹取在 [hist_low×0.7, hist_high×1.6] 护栏内（历史锚不删除，降级为围栏）
  · 3 尺齐 → 融合倍数 B 级；2 尺 → C 级；仅 1 尺 → 维持原状不融合

反向验证（回答"现价是否已透支预期"，绕开 PE 该给几倍的争论）：
  由合理 PE 公式反解现价隐含永续增长 g_impl = (PE_now×r − payout) ÷ (PE_now + payout)，
  当 g_impl 显著高于一致预期增速（+5pp 且绝对值 >3pp）时 warn
  PRICE_EMBEDS_EXCESS_OPTIMISM。

所有经验参数（折扣系数、ERP、g 封顶等）均为 D 级工程参数，必须随账本落盘审计。
空值就是空值：任何一把尺子缺输入就跳过该尺，禁止硬造。
"""
from __future__ import annotations

import datetime as dt
import math

# ---- D 级经验参数（全部入账本审计）----
HAIRCUT_ACCURATE = 0.95   # 预测误差较小行业（银行/消费/医药/建材/地产/非银等）
HAIRCUT_DEFAULT = 0.90    # 行业未知时的兜底
HAIRCUT_PRONE = 0.85      # 易高估行业（军工/TMT/通信/电子/机械/电气设备/农牧/有色等）
DEFAULT_ERP = 0.06        # 股权风险溢价（中国市场长期经验值，D 级）
DEFAULT_RF = 0.02         # 十年期国债缺失时的兜底无风险利率（D 级）
DEFAULT_G = 0.025         # 无长期历史时的永续增速兜底（≈实际GDP，D 级）
G_CAP = 0.05              # 公式尺永续增速上限（≈名义GDP）；FY1 短期增速禁止充当永续
MIN_R_MINUS_G = 0.02      # r−g 低于此值时戈登公式失真，拒绝出值
DIVERGENCE_MAX = 1.8      # 尺间最大/最小比超过此值 → 分歧 warn
BAND_CLAMP_LOW = 0.7      # 护栏：融合下界不低于历史 P25 的 0.7×
BAND_CLAMP_HIGH = 1.6     # 护栏：融合上界不高于历史 P75 的 1.6×
REVERSE_MARGIN = 0.05     # 隐含增长超出预期增速 5pp 视为透支
REVERSE_ABS_MIN = 0.03    # 隐含增长绝对值低于 3pp 不告警（噪声过滤）

_INDUSTRY_KEYWORDS = {
    HAIRCUT_ACCURATE: (
        "银行", "非银", "保险", "券商", "建材", "医药", "医疗", "地产", "商贸",
        "食品", "饮料", "白酒", "家电", "消费", "中药", "公路", "电力", "港口",
        "水务", "燃气", "高速", "交通",
    ),
    HAIRCUT_PRONE: (
        "军工", "国防", "通信", "计算机", "传媒", "电子", "半导体", "面板", "光伏",
        "锂电", "电池", "有色", "钢铁", "农林", "牧渔", "养殖", "机械", "电气设备",
        "机床", "消费电子", "元件", "软件", "互联网", "TMT", "精密", "光电",
    ),
}


def resolve_industry_haircut(config: dict, route_code: str | None) -> dict | None:
    """确定行业折扣系数。优先级：配置 industry_tag 关键词匹配 > 路由默认值。

    返回 {"haircut", "tag", "basis", "quality"} 或 None（非 PE 路由不适用）。
    """
    if route_code not in ("forward_pe", "growth_pe"):
        return None
    tag = str(config.get("industry_tag") or "")
    hay = tag + " " + str(config.get("notes") or "") + " " + str(config.get("name") or "")
    for haircut, words in _INDUSTRY_KEYWORDS.items():
        for w in words:
            if w in hay:
                return {
                    "haircut": haircut,
                    "tag": tag or w,
                    "basis": f"industry_keyword:{w}",
                    "quality": "D_industry_haircut",
                }
    route_default = HAIRCUT_ACCURATE if route_code == "forward_pe" else HAIRCUT_PRONE
    return {
        "haircut": route_default,
        "tag": tag or ("路由默认·稳定盈利" if route_code == "forward_pe" else "路由默认·高成长"),
        "basis": f"route_default:{route_code}",
        "quality": "D_industry_haircut",
    }


def apply_haircut(selected: dict, haircut: float) -> dict:
    """对一致预期 EPS 三档打折，返回新 dict（绝不修改原始 selected）。"""
    return {k: round(float(selected[k]) * haircut, 6) for k in ("bear", "base", "bull")}


def fy1_growth(selected: dict, actual_history: list) -> float | None:
    """FY1 一致预期增速 = FY1 基准 EPS / 最近实际 EPS − 1。缺实际历史则 None。"""
    try:
        rows = sorted(actual_history or [], key=lambda x: x.get("year", 0))
        last = rows[-1]["eps"] if rows else None
        if not last or last <= 0:
            return None
        return float(selected["base"]) / float(last) - 1.0
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return None


def equity_cost_r(market: dict, config: dict) -> float | None:
    """股权成本 r = 无风险利率 + ERP。国债利率来自大盘数据，缺省用 DEFAULT_RF。

    中债-akshare 返回小数形式（0.0168=1.68%），腾讯等部分源为百分数（2.5=2.5%）；
    以 0.5 为分界自适应判别（中国10Y历史区间 0.5%~5%，两种口径不重叠）。
    """
    ke = config.get("ke")
    if isinstance(ke, (int, float)) and 0 < ke < 0.5:
        return float(ke)
    bond = (market or {}).get("bond_10y") or {}
    val = bond.get("value")
    if isinstance(val, (int, float)) and 0 < val < 20:
        rf = float(val) if val < 0.5 else float(val) / 100.0
    else:
        rf = DEFAULT_RF
    return rf + DEFAULT_ERP


def resolve_payout(config: dict, market: dict) -> tuple | None:
    """分红率 payout ∈ (0,1]。优先显式配置，其次 股息率×PE(TTM) 推导。返回 (payout, how)。"""
    p = config.get("dividend_payout_ratio")
    if isinstance(p, (int, float)) and 0 < p <= 1:
        return float(p), "config:dividend_payout_ratio"
    dy = (config.get("dividend_yield_ttm") or {})
    dy_val = dy.get("value_pct") if isinstance(dy, dict) else dy
    pe_ttm = (market or {}).get("pe_ttm")
    if isinstance(dy_val, (int, float)) and dy_val > 0 and \
       isinstance(pe_ttm, (int, float)) and pe_ttm > 0:
        payout = min(0.9, max(0.05, float(dy_val) / 100.0 * float(pe_ttm)))
        return payout, "derived:dividend_yield_x_pe_ttm"
    return None


def sustainable_growth(actual_history: list, r: float | None, config: dict | None = None) -> float:
    """公式尺专用永续增速 g（单阶段戈登口径，非 FY1 短期增速）。

    来源优先级：配置 sustainable_growth > 长期 EPS CAGR（≥3 个年度且跨度 ≥2 年，
    封顶 G_CAP）> DEFAULT_G。最终 clamp 到 r−MIN_R_MINUS_G 以内保证公式有效。
    """
    cfg_g = (config or {}).get("sustainable_growth")
    if isinstance(cfg_g, (int, float)) and 0 <= cfg_g < 0.20:
        g = float(cfg_g)
    else:
        rows = sorted([x for x in (actual_history or [])
                       if isinstance(x.get("eps"), (int, float)) and x["eps"] > 0],
                      key=lambda x: x.get("year", 0))
        if len(rows) >= 3 and (rows[-1].get("year", 0) - rows[0].get("year", 0)) >= 2:
            cagr = (rows[-1]["eps"] / rows[0]["eps"]) ** (1.0 / (rows[-1]["year"] - rows[0]["year"])) - 1.0
            g = min(max(cagr, 0.0), G_CAP)
        else:
            g = DEFAULT_G
    ceiling = max((r if isinstance(r, (int, float)) else 0.08) - MIN_R_MINUS_G - 1e-9, 0.0)
    return min(g, ceiling)


def justified_pe(payout: float, g: float, r: float) -> float | None:
    """戈登合理 PE = payout×(1+g)/(r−g)；r−g 过小或输入非法时拒绝出值（空即空）。"""
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (payout, g, r)):
        return None
    if not (0 < payout <= 1) or g < 0 or r <= 0:
        return None
    spread = r - g
    if spread < MIN_R_MINUS_G:
        return None
    return round(payout * (1.0 + g) / spread, 4)


def implied_growth_from_pe(pe_now: float, payout: float, r: float) -> float | None:
    """由现价 PE 反解隐含永续增长：g = (PE×r − payout) ÷ (PE + payout)。"""
    if not all(isinstance(v, (int, float)) and math.isfinite(v) and v > 0
               for v in (pe_now, payout, r)):
        return None
    denom = pe_now + payout
    if denom <= 0:
        return None
    return (pe_now * r - payout) / denom


def _median(vals: list) -> float:
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def fuse_multiples(hist_band: dict, extra_candidates: list,
                   as_of: dt.date) -> tuple:
    """三尺融合。返回 (fused_dict, meta) ；不可融合时 (None, reason)。

    fused_dict 结构与 multiple 对象同形（low/mid/high/source），
    source.method = tri_ruler_consensus，fusion 明细全部内嵌供审计。
    """
    hist = {k: hist_band.get(k) for k in ("low", "mid", "high")}
    if not all(isinstance(v, (int, float)) and math.isfinite(v) and v > 0
               for v in hist.values()):
        return None, "history band invalid"
    if not (hist["low"] <= hist["mid"] <= hist["high"]):
        return None, "history band unordered"

    rulers = [{"ruler": "history_percentile", "mid": float(hist["mid"]),
               "detail": f"P25={hist['low']}/P50={hist['mid']}/P75={hist['high']}"}]
    for c in extra_candidates:
        if c and isinstance(c.get("mid"), (int, float)) and math.isfinite(c["mid"]) and c["mid"] > 0:
            rulers.append({"ruler": c.get("ruler", "extra"), "mid": float(c["mid"]),
                           "detail": c.get("detail", "")})

    mids = [r["mid"] for r in rulers]
    if len(mids) < 2:
        return None, "insufficient rulers (<2)"

    eff_mid = round(_median(mids), 4)
    ratio_lo = hist["low"] / hist["mid"]
    ratio_hi = hist["high"] / hist["mid"]
    eff_low = round(eff_mid * ratio_lo, 4)
    eff_high = round(eff_mid * ratio_hi, 4)
    floor = round(hist["low"] * BAND_CLAMP_LOW, 4)
    cap = round(hist["high"] * BAND_CLAMP_HIGH, 4)
    eff_low = round(min(max(eff_low, floor), eff_mid), 4)
    eff_high = round(max(min(eff_high, cap), eff_mid), 4)

    divergence = max(mids) / min(mids)
    divergent = len(mids) >= 2 and divergence > DIVERGENCE_MAX
    quality = "B" if len(mids) >= 3 else "C"
    meta = {
        "method": "tri_ruler_consensus",
        "rulers": rulers,
        "n_rulers": len(mids),
        "effective": {"low": eff_low, "mid": eff_mid, "high": eff_high},
        "guardrails": {"floor": floor, "cap": cap,
                       "note": "历史分位降级为护栏（clamp），不再单尺主导"},
        "divergence_ratio": round(divergence, 4),
        "divergent": divergent,
        "divergence_threshold": DIVERGENCE_MAX,
        "quality": quality,
        "parameter_tags": ["D_industry_haircut", "D_default_erp", "D_g_cap"],
        "as_of": as_of.isoformat(),
        "formula": "PE_eff 中位数 = median(公式尺, 同行尺, 历史P50)；带宽=历史形状×新中枢，clamp进[P25×0.7, P75×1.6]",
    }
    return {"low": eff_low, "mid": eff_mid, "high": eff_high}, meta


def reverse_valuation(pe_now: float, payout: float, r: float,
                      g_expected: float) -> dict | None:
    """反向验证：现价隐含永续增长 vs 一致预期增速。

    透支判定：g_impl > g_expected + REVERSE_MARGIN 且 g_impl > REVERSE_ABS_MIN。
    返回审计 dict（含 verdict）；输入不足返回 None。
    """
    g_impl = implied_growth_from_pe(pe_now, payout, r)
    if g_impl is None or g_expected is None:
        return None
    excess = g_impl - g_expected
    overheated = bool(g_impl > REVERSE_ABS_MIN and excess > REVERSE_MARGIN)
    return {
        "formula": "g_impl = (PE_now×r − payout) ÷ (PE_now + payout)",
        "pe_now": round(pe_now, 4),
        "payout": round(payout, 4),
        "r": round(r, 4),
        "g_implied": round(g_impl, 4),
        "g_expected_consensus": round(g_expected, 4),
        "excess_pp": round(excess * 100, 2),
        "overheated": overheated,
        "verdict": ("PRICE_EMBEDS_EXCESS_OPTIMISM：现价隐含增长已高于一致预期，"
                    "上行空间依赖预测上调，警惕透支" if overheated else
                    "现价隐含增长未超一致预期，未见明显透支"),
        "parameter_tags": ["D_default_erp"],
    }
