# -*- coding: utf-8 -*-
"""估值倍数自动校准器：百度股市通 5 年 PE(TTM) 历史分位 → 锚定目标 PE 三档。

解决"估值倍数为人工政策假设（D级）"硬伤：
  pe_low  = 历史 P25（保守档）
  pe_mid  = 历史 P50（中位数，价值中枢锚）
  pe_high = 历史 P75（乐观档）

护栏：
  · 历史序列少于 500 个交易日 → 不校准，保留原值并标注
  · 当前 PE 超出 [P10, P90] 区间 → 倍数有效但加注"当前处于历史极端分位"
  · PE(TTM) 分位按 spec 3.1/3.2 定级 C：历史 TTM 分位 × 前瞻 NTM EPS 存在基数错配，
    引擎强制 reference_only、不得生成买卖动作（MULTIPLE_TTM_BASIS_MISMATCH）
  · PB 分位（银行 PB-ROE / 基建 PB 路由）基数匹配（净资产×PB），保持 B 级
  · 保险 P/EV、周期、ETF、亏损路由不在此校准（各自专用口径）

用法：python calibrate_multiples.py   # 校准 forward_pe / growth_pe / normalized_pe
"""
import io
import json
import os
import sys
import datetime
import statistics

# 仅作为主脚本运行时包装 stdout（被 update_daily import 时不包装，避免管道关闭）
if __name__ == '__main__':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

BASE = r"E:\财报解读\watchlist"
WATCHLIST = os.path.join(BASE, "watchlist.json")
STATE = os.path.join(BASE, "state.json")
CALIBRATE_ROUTES = {"forward_pe", "growth_pe", "normalized_pe"}
PB_ROUTES = {"bank_pb_roe", "infrastructure_cashflow"}
BAIDU_URL = "https://finance.pae.baidu.com/vapi/v1/getquotation"


def _fresh_pe_ttm(ticker: str, fallback) -> float | None:
    """极端分位注记用当前 PE：优先取昨日流水线 state 的行情值，其次配置旧值。"""
    try:
        if os.path.exists(STATE):
            with open(STATE, encoding="utf-8") as f:
                st = json.load(f)
            val = (st.get("stocks") or {}).get(ticker, {}).get("pe_ttm")
            if isinstance(val, (int, float)):
                return float(val)
    except Exception:
        pass
    return fallback


def fetch_pe_history(symbol: str, years: str = "近五年") -> list:
    import akshare as ak
    df = ak.stock_zh_valuation_baidu(symbol=symbol, indicator="市盈率(TTM)", period=years)
    if df is None or df.empty or "value" not in df.columns:
        return []
    return sorted(df["value"].dropna().astype(float).tolist())


def fetch_pb_history(symbol: str, years: str = "近五年") -> list:
    import akshare as ak
    df = ak.stock_zh_valuation_baidu(symbol=symbol, indicator="市净率", period=years)
    if df is None or df.empty or "value" not in df.columns:
        return []
    return sorted(df["value"].dropna().astype(float).tolist())


def quantile(vals, q):
    if not vals:
        return None
    idx = int(len(vals) * q)
    idx = max(0, min(len(vals) - 1, idx))
    return round(vals[idx], 2)


def main():
    with open(WATCHLIST, encoding="utf-8") as f:
        wl = json.load(f)
    today = datetime.date.today().isoformat()
    changed = 0

    for s in wl["stocks"]:
        vm = s.get("valuation_model")
        code = vm.get("code") if isinstance(vm, dict) else vm
        if code not in CALIBRATE_ROUTES and code not in PB_ROUTES:
            continue
        ticker = s["ticker"]
        if code in PB_ROUTES:
            # PB 路由：百度股市通 5 年 PB 分位 → pb_low/mid/high（银行/建筑现金流路由用）
            hist = [v for v in fetch_pb_history(ticker) if v > 0]
            if len(hist) < 500:
                print(f"{ticker} {s.get('name')}: PB 历史序列不足({len(hist)})，跳过校准")
                continue
            p25, p50, p75 = quantile(hist, .25), quantile(hist, .50), quantile(hist, .75)
            if not (0 < p25 <= p50 <= p75):
                print(f"{ticker} {s.get('name')}: PB 分位异常，跳过")
                continue
            s["pb_low"], s["pb_mid"], s["pb_high"] = p25, p50, p75
            s["pb_source"] = (
                f"百度股市通 5 年 PB 历史分位自动校准（{today}）："
                f"P25={p25}/P50={p50}/P75={p75}，样本 {len(hist)} 日"
            )
            src_obj = {
                "id": f"baidu-pb-percentile-{ticker}",
                "title": f"百度股市通 5 年 PB 分位校准（P25/P50/P75）",
                "method": "history_percentile_calibration",
                "quality": "B",
                "as_of": today,
                "source_id": f"baidu-{ticker}",
                "type": "valuation_multiple",
                "metric": "pb",
                "unit": "x",
            }
            s["multiple_source"] = dict(src_obj)
            s["multiple"] = {"low": p25, "mid": p50, "high": p75, "source": dict(src_obj)}
            s["multiple_source_method"] = "history_percentile_calibration"
            s["multiple_source_quality"] = "B"
            print(f"{ticker} {s.get('name')}: PB → {p25}/{p50}/{p75}（B级·历史分位校准）")
            changed += 1
            continue

        hist = fetch_pe_history(ticker)
        if len(hist) < 500:
            print(f"{ticker} {s.get('name')}: 历史序列不足({len(hist)})，跳过校准")
            continue

        p25, p50, p75 = quantile(hist, .25), quantile(hist, .50), quantile(hist, .75)
        pe_now = _fresh_pe_ttm(ticker,
                               s.get("market", {}).get("pe_ttm") if isinstance(s.get("market"), dict) else None)
        if p25 is None or p50 is None or p75 is None or not (0 < p25 <= p50 <= p75):
            print(f"{ticker} {s.get('name')}: 分位异常 P25={p25} P50={p50} P75={p75}，跳过")
            continue

        old = f"{s.get('pe_low')}/{s.get('pe_mid')}/{s.get('pe_high')}"
        s["pe_low"], s["pe_mid"], s["pe_high"] = p25, p50, p75
        extreme = ""
        if pe_now is not None:
            p10, p90 = quantile(hist, .10), quantile(hist, .90)
            if p10 is not None and pe_now < p10:
                extreme = f"；当前 PE {pe_now} 处于历史 10% 以下极端低位"
            elif p90 is not None and pe_now > p90:
                extreme = f"；当前 PE {pe_now} 处于历史 90% 以上极端高位"
        s["pe_source"] = (
            f"百度股市通 5 年 PE(TTM) 历史分位自动校准（{today}）："
            f"P25={p25}/P50={p50}/P75={p75}，样本 {len(hist)} 日"
            + extreme
            + "；TTM 分位向 Forward 转换存在基数错配风险（spec 3.1/3.2，C 级仅参考）"
        )
        s["multiple_source"] = {
            "id": f"baidu-pe-percentile-{ticker}",
            "title": f"百度股市通 5 年 PE(TTM) 分位校准（P25/P50/P75）",
            "method": "history_percentile_calibration",
            "quality": "C",
            "as_of": today,
            "source_id": f"baidu-{ticker}",
            "type": "valuation_multiple",
            "metric": "forward_pe",
            "unit": "x",
        }
        # 同步替换引擎优先读取的 multiple 对象（含 low/mid/high 与来源）
        s["multiple"] = {
            "low": p25, "mid": p50, "high": p75,
            "source": dict(s["multiple_source"]),
        }
        s["multiple_source_method"] = "history_percentile_calibration"
        s["multiple_source_quality"] = "C"
        print(f"{ticker} {s.get('name')}: {old} → {p25}/{p50}/{p75}（C级·历史TTM分位校准，仅参考）")
        changed += 1

    with open(WATCHLIST, "w", encoding="utf-8") as f:
        json.dump(wl, f, ensure_ascii=False, indent=2)
    print(f"\n完成：{changed} 只股票倍数已校准为历史分位锚定（B 级）")


if __name__ == "__main__":
    main()
