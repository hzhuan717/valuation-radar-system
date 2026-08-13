# -*- coding: utf-8 -*-
"""估值雷达 · 终端仪表盘生成器 v7（UI/UX 深度优化版）

v7 优化（2026-08-13 用户验收标准）：
  · 字体系统重构：全局无低于 12px 的数据文本，正文 13px、卡片标题 14px、行高 ≥1.5；
    辅助色对比度达 WCAG AA（--sub/--meta 均 #6e6e73 及以上）
  · K 线主图 <g id="sr-layer">：支撑 #34c759 / 压力 #ff3b30 虚线(4 3) + 右侧底色标签(12px)，
    过近(<15px)合并降级；估值三区背景带按新透明度；均线 1.5px、chip hover 放大
  · 右墙新增「关键价位 · S/R」价格轨道卡（250日区间轨道 + 当前价蓝点 + A/B 级点位 + 两列明细）
  · 卡片结构：核心指标区 + 详情折叠区（默认折叠，首屏文字量 -40%+）
  · Step2 三色块、Step3 阶梯瀑布、Step4 均线排列状态 + 迷你走势、Step5 半圆仪表盘、
    Step6 来源徽章(首字母+等级+时间) + 质检(默认仅阻断/警告)
  · Hero：价格 32px、涨跌箭头、MOS 滑轨两端标注、脉冲圆点、结论性文案
  · 交互：Popover ↑↓/Enter 键盘导航、ktip 增加估值状态与临近 S/R 提示、
    Modal 复制公式 + 编号圆圈步骤
  · 动效：切换股票数字滚动 300ms、S/R 线绘制动画 600ms、卡片错峰入场、行 hover 微动
  · 移动端：图表 45vh 置顶、卡片全宽大数字布局
"""
import json
import math
import os

BASE = r"E:\财报解读\watchlist"
STATE = os.path.join(BASE, "state.json")
OUT = os.path.join(BASE, "output", "估值雷达门户.html")

PRICE_NEAR = 0.015   # 与现价 ±1.5% 内视为贴线，降 C 级
MERGE_TOL = 0.02     # 同侧点位价差 <2% 合并去重
EV_ORDER = {"A": 0, "B": 1, "C": 2}


def _num(v):
    return isinstance(v, (int, float)) and math.isfinite(v)


def _price_of(st):
    p = st.get("price")
    if _num(p) and p > 0:
        return p
    k = st.get("kline") or []
    if k and _num(k[-1].get("c")):
        return k[-1]["c"]
    return None


def _anchor_item(item):
    """V_low/V_mid/V_high 是估值锚（基本面），不是技术位：统一改名 + 降 C 级。
    仅匹配方法名开头（合并后的复合文本不重命名）；锚点文本不带价格，避免合并后过期。"""
    m = item.get("method") or ""
    lv = item.get("level")
    if m.startswith("V_low") or m.startswith("买入启动区") or m.startswith("估值锚 V_low"):
        return {"level": lv, "method": "估值锚 V_low（下沿）", "level_ev": "C"}
    if m.startswith("V_high") or m.startswith("卖出启动区") or m.startswith("估值锚 V_high"):
        return {"level": lv, "method": "估值锚 V_high（上沿）", "level_ev": "C"}
    if m.startswith("V_mid") or m.startswith("估值锚 V_mid"):
        return {"level": lv, "method": "估值锚 V_mid（中枢）", "level_ev": "C"}
    return item


def _strip_notes(method):
    """剥离历史标注后缀，保证 sanitize 幂等（可重复执行）。"""
    for note in (" · 现价贴线，参考性弱", " · 已跌破转压", " · 已突破转支"):
        method = method.replace(note, "")
    return method


def _flip_note(method, from_sup):
    """破位/突破后角色转换标注。"""
    if from_sup:
        if any(t in method for t in ("低点", "缺口", "支撑", "启动")):
            return method + " · 已跌破转压"
    elif any(t in method for t in ("高点", "压力", "回撤")):
        return method + " · 已突破转支"
    return method


def sanitize_sr(st: dict) -> tuple:
    """支撑/压力统一校验（v8）：
    1) 方向铁律：支撑必须低于现价、压力必须高于现价；±1.5% 贴线保留原侧但降 C 级；
    2) 角色转换：原支撑跌破→转压力、原压力突破→转支撑（标注并降 C 级）；
    3) 估值锚统一改名 + 降 C 级；
    4) 同侧价差 <2% 合并去重（保留高等级，方法拼接）；
    5) 每侧最多 5 条，支撑按距现价由近到远排列。
    """
    price = _price_of(st)
    raw = [(True, it) for it in (st.get("support") or [])] + [(False, it) for it in (st.get("resistance") or [])]
    if price is None:
        sup = [it for from_sup, it in raw if from_sup and _num(it.get("level"))][:5]
        res = [it for from_sup, it in raw if not from_sup and _num(it.get("level"))][:5]
        return sup, res
    pool = []  # [level, item, is_support]
    for from_sup, it in raw:
        lv = it.get("level")
        if not _num(lv) or lv <= 0:
            continue
        item = dict(_anchor_item(it))
        item["method"] = _strip_notes(item.get("method") or "")
        delta = (lv - price) / price
        if abs(delta) < 1e-9:
            continue  # 点位恰好等于现价，无方向信息
        if abs(delta) < PRICE_NEAR:
            item = dict(item)
            item["level_ev"] = "C"
            item["method"] = item["method"] + " · 现价贴线，参考性弱"
            side = delta < 0
        elif lv < price:
            side = True
            if not from_sup:
                item = dict(item)
                item["method"] = _flip_note(item["method"], False)
                item["level_ev"] = "C"
        else:
            side = False
            if from_sup:
                item = dict(item)
                item["method"] = _flip_note(item["method"], True)
                item["level_ev"] = "C"
        pool.append([lv, item, side])
    pool.sort(key=lambda x: x[0])
    merged = []
    for lv, item, side in pool:
        hit = next((m for m in merged if m[2] == side and abs(m[0] - lv) <= MERGE_TOL * price), None)
        if hit:
            if EV_ORDER.get(item.get("level_ev"), 9) < EV_ORDER.get(hit[1].get("level_ev"), 9):
                hit[0] = lv  # 采用高等级点位的价格
                hit[1]["level_ev"] = item.get("level_ev")
            elif EV_ORDER.get(item.get("level_ev"), 9) == EV_ORDER.get(hit[1].get("level_ev"), 9):
                hit[0] = round((hit[0] + lv) / 2, 2)  # 同级取中点
            hit[1]["level"] = hit[0]  # 同步输出字段
            hit[1]["method"] = hit[1]["method"] + " / " + item["method"]
        else:
            merged.append([lv, item, side])
    sup = sorted((m for m in merged if m[2]), key=lambda m: -m[0])[:5]
    res = sorted((m for m in merged if not m[2]), key=lambda m: m[0])[:5]
    return [m[1] for m in sup], [m[1] for m in res]


def auto_sr(st: dict) -> tuple:
    """候选点位生成（v8）：估值锚(C) + 60/250日高低点(B) + MA20/60(B) + 斐波那契回撤(B，带基期)。
    方向校正、贴线降级、去重统一交给 sanitize_sr 完成。"""
    k = st.get("kline") or []
    cand_sup, cand_res = [], []
    if not k:
        return [], []
    v_low, v_high = st.get("v_low"), st.get("v_high")
    if _num(v_low) and v_low > 0:
        cand_sup.append({"level": round(v_low, 2), "method": "估值锚 V_low（下沿）", "level_ev": "C"})
    if _num(v_high) and v_high > 0:
        cand_res.append({"level": round(v_high, 2), "method": "估值锚 V_high（上沿）", "level_ev": "C"})
    if len(k) >= 60:
        seg = k[-60:]
        cand_sup.append({"level": round(min(r["l"] for r in seg), 2), "method": "近60日低点", "level_ev": "B"})
        cand_res.append({"level": round(max(r["h"] for r in seg), 2), "method": "近60日高点", "level_ev": "B"})
    if len(k) >= 250:
        seg = k[-250:]
        lo250 = round(min(r["l"] for r in seg), 2)
        hi250 = round(max(r["h"] for r in seg), 2)
        cand_sup.append({"level": lo250, "method": "250日低点", "level_ev": "B"})
        cand_res.append({"level": hi250, "method": "250日高点", "level_ev": "B"})
        rng = hi250 - lo250
        if rng > 0:
            for ratio in (0.382, 0.5, 0.618):
                cand_res.append({"level": round(lo250 + rng * ratio, 2),
                                 "method": f"斐波那契{ratio}回撤（250日 {lo250}→{hi250}）", "level_ev": "B"})
    if len(k) >= 20:
        cand_sup.append({"level": round(sum(r["c"] for r in k[-20:]) / 20, 2), "method": "MA20 均线", "level_ev": "B"})
    if len(k) >= 60:
        cand_sup.append({"level": round(sum(r["c"] for r in k[-60:]) / 60, 2), "method": "MA60 均线", "level_ev": "B"})
    return sanitize_sr({"support": cand_sup, "resistance": cand_res, "price": _price_of(st)})


def build() -> str:
    with open(STATE, encoding="utf-8") as f:
        state = json.load(f)
    market = state.get("market", {})
    stocks = list(state.get("stocks", {}).values())
    if not stocks:
        raise SystemExit("state.json 无股票数据，请先运行 update_daily.py")

    for st in stocks:
        if not st.get("support") and not st.get("resistance"):
            st["support"], st["resistance"] = auto_sr(st)
        else:
            st["support"], st["resistance"] = sanitize_sr(st)
        q = st.get("data_quality") or {}
        st["_blockers"] = [b.get("detail", "") for b in q.get("blockers", [])]
        st["_warnings"] = [w.get("detail", "") for w in q.get("warnings", [])]

    data = {"updated_at": state.get("meta", {}).get("updated_at", ""),
            "data_date": market.get("data_date", ""),
            "market": market, "stocks": stocks,
            "pe_history": state.get("pe_history", {})}
    data_json = json.dumps(data, ensure_ascii=False)

    html = TEMPLATE
    html = html.replace("__DATA__", data_json)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    return f"门户已生成: {OUT}（{len(html):,} 字符 · {len(stocks)} 只）"


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>估值雷达 · 终端仪表盘</title>
<style>
/* ============ Design Tokens（v7 字体系统 · WCAG AA） ============ */
:root{
  --font-base:-apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei","Noto Sans SC",sans-serif;
  --font-mono:"SF Mono",SFMono-Regular,"DIN Alternate","Helvetica Neue",ui-monospace,Menlo,Consolas,monospace;
  /* 四级字体规范（全局无低于12px的数据文本） */
  --text-xs:12px; --text-sm:13px; --text-base:14px; --text-lg:24px; --text-xl:32px;
  --fs-title:12px; --fs-data:13px; --fs-meta:12px;
  /* 背景与文字（辅助色对比度 ≥4.5:1） */
  --bg:#f5f5f7; --bg2:#ffffff; --hair:rgba(0,0,0,.08); --hair2:rgba(0,0,0,.14);
  --ink:#1d1d1f; --sub:#6e6e73; --sub2:#48484a; --meta:#6e6e73;
  /* 品牌与语义 */
  --blue:#0071e3; --blue-lt:rgba(0,113,227,.08);
  --green:#34c759; --green-d:#1f9d4d; --red:#ff3b30; --red-d:#d70015; --gold:#a0742f; --violet:#5e5ce6;
  --candle-up:#d94a47; --candle-dn:#178a59;
  --color-support:#34c759; --color-resist:#ff3b30;
  --color-support-bg:rgba(52,199,89,.08); --color-resist-bg:rgba(255,59,48,.08);
  /* 间距与外观 */
  --space-unit:4px;
  --r-card:8px;
  --shadow-card:0 2px 8px rgba(0,0,0,.06),0 1px 2px rgba(0,0,0,.04);
}
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%;overflow:hidden}
body{font-family:var(--font-base);background:var(--bg);color:var(--ink);font-size:var(--text-sm);line-height:1.6}
button{font-family:var(--font-base);cursor:pointer}
a{color:var(--blue)}
b{font-weight:600}

/* ============ 顶栏 44px ============ */
.topbar{height:44px;display:flex;align-items:center;gap:12px;padding:0 14px;background:var(--bg2);
  border-bottom:1px solid var(--hair);position:relative;z-index:30}
.brand{display:flex;align-items:center;gap:8px;border:none;background:none;font-size:14px;font-weight:600;color:var(--ink);padding:5px 10px;border-radius:6px;transition:background .15s}
.brand:hover{background:var(--blue-lt);color:var(--blue)}
.brand i{width:15px;height:15px;border-radius:5px;background:var(--blue);display:inline-block}
.stock-trig{display:flex;align-items:center;gap:10px;border:1px solid var(--hair);background:var(--bg2);
  border-radius:var(--r-card);padding:6px 12px;font-size:13px;min-width:240px;max-width:330px}
.stock-trig:hover{border-color:var(--blue)}
.stock-trig span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.stock-trig .arr{margin-left:auto;color:var(--sub)}
.top-gate{margin-left:auto;display:flex;align-items:center;gap:6px;font-size:13px;color:var(--sub2)}
.top-gate .dot{width:8px;height:8px;border-radius:50%;flex:none}
.dot-ok{background:var(--green)}.dot-warn{background:var(--gold)}.dot-bad{background:var(--red)}
.top-upd{font-size:var(--text-xs);color:var(--meta)}

/* ============ 弹出选股器 ============ */
.popover{position:absolute;top:50px;left:12px;width:440px;background:var(--bg2);border:1px solid var(--hair);
  border-radius:10px;box-shadow:0 12px 40px rgba(0,0,0,.14);display:none;z-index:50;padding:8px}
.popover.on{display:block}
.pop-search{width:100%;border:1px solid var(--hair);border-radius:6px;padding:8px 10px;font-size:13px;margin-bottom:6px}
.pop-list{max-height:440px;overflow-y:auto}
.pop-item{display:flex;align-items:center;gap:10px;width:100%;text-align:left;border:none;background:none;
  padding:8px 10px;border-radius:6px;font-size:13px;transition:background .15s,transform .15s}
.pop-item:hover,.pop-item.sel{background:var(--blue-lt)}
.pop-item:hover{transform:translateX(2px)}
.pop-item .nm{font-weight:600}
.pop-item .cd{color:var(--meta);font-family:var(--font-mono)}
.pop-item .st{margin-left:auto;font-size:12px}

/* ============ 主体三栏 Grid（100vh 单屏） ============ */
.shell{display:grid;grid-template-columns:210px minmax(0,1fr) 400px;grid-template-rows:minmax(0,1fr);
  height:calc(100vh - 44px);overflow:hidden}

/* ---- 左导航 210px ---- */
.sidebar{border-right:1px solid var(--hair);background:var(--bg2);display:flex;flex-direction:column;min-height:0;min-width:0}
.sb-hd{display:flex;justify-content:space-between;align-items:baseline;padding:12px 12px 8px;
  font-size:var(--fs-title);font-weight:600;letter-spacing:.05em;color:var(--sub);text-transform:uppercase}
.sb-search{margin:0 10px 8px;border:1px solid var(--hair);border-radius:6px;padding:7px 10px;font-size:13px}
.sb-list{flex:1;overflow-y:auto;min-height:0}
.sb-item{display:block;width:100%;text-align:left;border:none;background:none;padding:8px 12px;
  border-bottom:1px solid var(--hair);font-size:13px;position:relative;transition:background .15s,transform .15s}
.sb-item:hover{background:var(--blue-lt);transform:translateX(2px)}
.sb-item.on{background:var(--blue-lt);box-shadow:inset 3px 0 0 var(--blue)}
.sb-item .nm{font-weight:600;font-size:13px}
.sb-item .cd{color:var(--meta);font-family:var(--font-mono);font-size:12px;margin-left:4px}
.sb-item .px{margin-left:auto;font-family:var(--font-mono);font-weight:600;font-size:13px}
.sb-item .chg{font-size:12px;font-family:var(--font-mono)}
.sb-item .l1{display:flex;align-items:baseline;gap:6px;min-width:0}
.sb-item .code{display:none}
/* 估值位置条：三色底 + 当前价竖线标记 */
.sb-item .bar{position:absolute;left:12px;right:12px;bottom:0;height:4px;border-radius:2px;overflow:hidden;
  background:linear-gradient(90deg,rgba(52,199,89,.55) 0 25%,rgba(0,113,227,.45) 25% 75%,rgba(255,59,48,.55) 75% 100%)}
.sb-item .bar i{display:none}
.sb-item .bar .mark{position:absolute;top:-1px;width:2px;height:6px;background:var(--ink);border-radius:1px}
.up-c{color:var(--candle-up)}.dn-c{color:var(--candle-dn)}
.sb-zone{font-size:12px;margin-left:auto;color:var(--sub2)}
.sb-zone.z0,.sb-zone.z1{color:var(--green-d)}.sb-zone.z4,.sb-zone.z5{color:var(--red-d)}.sb-zone.z2,.sb-zone.z3{color:var(--gold)}

/* ---- 中央区 ---- */
.center{display:flex;flex-direction:column;min-width:0;min-height:0;background:var(--bg)}
.hero-strip{display:flex;align-items:center;gap:18px;padding:10px 16px;background:var(--bg2);
  border-bottom:1px solid var(--hair);flex-wrap:wrap}
.hero-strip .hl{min-width:0;flex:1}
.hero-strip .eyebrow{font-size:12px;letter-spacing:.05em;color:var(--sub2);text-transform:uppercase}
.hero-strip h1{font-size:23px;font-weight:700;letter-spacing:-.02em;line-height:1.3}
.hero-strip .tick{font-size:12px;color:var(--sub2);font-family:var(--font-mono)}
.hero-strip .pills{display:flex;gap:6px;flex-wrap:wrap;margin-top:4px}
.pill{display:inline-flex;align-items:center;gap:6px;border-radius:999px;padding:4px 12px;font-size:12px;
  border:1px solid var(--hair);background:var(--bg2);line-height:1.5}
.pill .dot{width:7px;height:7px;border-radius:50%}
.hero-strip .hr{margin-left:auto;text-align:right;min-width:250px}
.hero-strip .price{font-size:var(--text-xl);font-weight:600;font-family:var(--font-mono);font-variant-numeric:tabular-nums;
  letter-spacing:-.01em;line-height:1.2}
.hero-strip .pct{font-size:16px;font-family:var(--font-mono);font-variant-numeric:tabular-nums}
.hero-strip .mos-wrap{margin-top:5px}
.mos-track{display:flex;justify-content:space-between;font-size:12px;color:var(--sub2);margin-bottom:3px}
.mos-bar{display:flex;height:8px;border-radius:4px;overflow:hidden;background:#e8e8ed;position:relative}
.mos-bar i{display:block;height:100%}
.mos-marker{position:relative;height:0}
.mos-dot{position:absolute;top:-9px;width:12px;height:12px;border-radius:50%;background:var(--blue);
  border:2px solid #fff;transform:translateX(-50%);box-shadow:0 0 0 1px var(--hair2);
  animation:pulseRing 2s ease-out infinite}
@keyframes pulseRing{0%{box-shadow:0 0 0 1px var(--hair2),0 0 0 0 rgba(0,113,227,.35)}
  70%{box-shadow:0 0 0 1px var(--hair2),0 0 0 8px rgba(0,113,227,0)}100%{box-shadow:0 0 0 1px var(--hair2),0 0 0 0 rgba(0,113,227,0)}}
.mos-txt{font-size:13px;color:var(--sub2);margin-top:7px;line-height:1.5}

/* ---- K线主画布 ---- */
.chart-zone{flex:1;display:flex;flex-direction:column;min-height:0;padding:8px 10px 6px}
.chart-toolbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:6px}
.chart-toolbar h3{font-size:14px;font-weight:600}
.chart-toolbar .info{font-size:12px;color:var(--sub2)}
.range-btns{display:flex;gap:4px}
.range-btn{font-size:12px;padding:4px 11px;border-radius:999px;border:1px solid var(--hair);
  background:var(--bg2);color:var(--sub2);transition:all .15s}
.range-btn:hover{border-color:var(--blue);color:var(--blue)}
.range-btn.on{background:var(--blue);border-color:var(--blue);color:#fff;font-weight:600}
.ma-legend{margin-left:auto;display:flex;gap:6px}
.ma-chip{display:inline-flex;align-items:center;gap:4px;font-size:12px;border:1px solid var(--hair);
  border-radius:999px;padding:3px 10px;background:var(--bg2);color:var(--sub2);transition:transform .15s,box-shadow .15s}
.ma-chip:hover{transform:scale(1.05)}
.ma-chip.on{box-shadow:0 2px 6px rgba(0,0,0,.12)}
.ma-chip i{width:9px;height:3px;display:inline-block;border-radius:1px}
.ma-chip.off{opacity:.4;text-decoration:line-through}
.chart-wrap{flex:1;position:relative;min-height:0;border:1px solid var(--hair);border-radius:var(--r-card);
  background:var(--bg2);overflow:hidden}
.chart-wrap svg{display:block;width:100%;height:100%}
.chart-foot{display:flex;gap:16px;font-size:12px;color:var(--sub2);padding:5px 2px 0;flex-wrap:wrap;line-height:1.5}
.legend-mini{display:inline-flex;align-items:center;gap:5px}
.legend-mini i{width:10px;height:3px;border-radius:2px;display:inline-block}
.ktip{position:absolute;top:8px;right:8px;background:rgba(255,255,255,.97);border:1px solid var(--hair2);
  border-radius:10px;padding:10px 14px;font-family:var(--font-mono);font-size:12px;line-height:1.7;color:var(--ink);
  box-shadow:0 4px 16px rgba(0,0,0,.1);pointer-events:none;opacity:0;min-width:186px;z-index:6;
  font-variant-numeric:tabular-nums;white-space:pre;transition:opacity .2s}
.ktip.show{opacity:1}
.ktip .tk{color:var(--sub2)}
.ktip .near-s{color:var(--green-d);font-weight:700}
.ktip .near-r{color:var(--red-d);font-weight:700}
.ktip .zone-badge{display:inline-block;border-radius:4px;padding:1px 8px;font-size:12px;font-weight:700}
.ov-wrap{flex:1;overflow-y:auto;min-height:0;padding:12px}
.ov-table{width:100%;border-collapse:collapse;font-size:13px;background:var(--bg2);
  border:1px solid var(--hair);border-radius:var(--r-card)}
.ov-table th{text-align:left;padding:8px 10px;font-size:12px;letter-spacing:.05em;text-transform:uppercase;
  color:var(--sub);border-bottom:1px solid var(--hair)}
.ov-table td{padding:8px 10px;border-bottom:1px solid var(--hair);font-family:var(--font-mono)}
.ov-table tr{cursor:pointer;transition:background .15s,transform .15s}
.ov-table tr:hover{background:var(--blue-lt);transform:translateX(2px)}

/* ---- 右数据墙 400px ---- */
.wall{background:var(--bg);border-left:1px solid var(--hair);overflow-y:auto;padding:10px;min-height:0}
.w-card{background:var(--bg2);border:1px solid var(--hair);border-radius:var(--r-card);
  padding:14px 16px;margin-bottom:12px;box-shadow:var(--shadow-card);
  animation:cardIn .4s var(--ease, ease-out) both}
@keyframes cardIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.w-title{font-size:var(--fs-title);font-weight:600;letter-spacing:.05em;text-transform:uppercase;
  color:var(--sub);margin-bottom:10px;display:flex;align-items:center;gap:6px;line-height:1.5}
.w-title .sp{margin-left:auto;font-size:12px;color:var(--meta);text-transform:none;letter-spacing:0}
/* 折叠区 */
.fold-toggle{display:block;width:100%;text-align:center;border:none;background:none;color:var(--blue);
  font-size:12px;padding:8px 0 2px;margin-top:8px;border-top:1px solid var(--hair);line-height:1.5}
.fold{display:none}
.fold.open{display:block}
/* 关键价位：价格轨道 */
.sr-track{position:relative;height:34px;border-radius:17px;margin:8px 0 10px;
  background:linear-gradient(90deg,var(--color-support-bg),rgba(0,113,227,.05) 50%,var(--color-resist-bg))}
.sr-track .tick{position:absolute;top:0;bottom:0;width:1px;background:var(--hair2)}
.sr-dot{position:absolute;top:50%;transform:translate(-50%,-50%);border-radius:50%;cursor:default}
.sr-dot.cur{width:14px;height:14px;background:var(--blue);border:2.5px solid #fff;box-shadow:0 0 0 1px var(--hair2),0 0 0 5px rgba(0,113,227,.15)}
.sr-dot.sA{width:12px;height:12px;background:var(--green-d);border:2px solid #fff;box-shadow:0 0 0 1px rgba(31,157,77,.5)}
.sr-dot.rA{width:12px;height:12px;background:var(--red-d);border:2px solid #fff;box-shadow:0 0 0 1px rgba(215,0,21,.5)}
.sr-dot.sB{width:11px;height:11px;background:#fff;border:2px dashed var(--green-d)}
.sr-dot.rB{width:11px;height:11px;background:#fff;border:2px dashed var(--red-d)}
.sr-dot.sC{width:9px;height:9px;background:#fff;border:2px solid rgba(31,157,77,.45)}
.sr-dot.rC{width:9px;height:9px;background:#fff;border:2px solid rgba(215,0,21,.45)}
.sr-list{display:grid;grid-template-columns:1fr 1fr;gap:4px 14px;font-size:13px;line-height:1.5}
.sr-list .row{display:flex;justify-content:space-between;gap:8px;border-bottom:1px solid var(--hair);padding:3px 0;font-family:var(--font-mono)}
.sr-list .row .m{font-family:var(--font-base);color:var(--sub2);font-size:12px}
.sr-list .row.s .v{color:var(--green-d);font-weight:600}
.sr-list .row.r .v{color:var(--red-d);font-weight:600}
/* 三色块 */
.v3-blocks{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:10px}
.v3b{border-radius:8px;padding:12px 8px;text-align:center;border:1px solid}
.v3b .k{font-size:12px;color:var(--sub2);letter-spacing:.03em;line-height:1.5}
.v3b .v{font-size:24px;font-weight:600;font-family:var(--font-mono);font-variant-numeric:tabular-nums;line-height:1.3}
.v3b .f{font-size:12px;color:var(--sub2);margin-top:2px;line-height:1.5}
.v3b.low{background:rgba(52,199,89,.07);border-color:rgba(52,199,89,.35)}.v3b.low .v{color:var(--green-d)}
.v3b.mid{background:rgba(0,113,227,.06);border-color:rgba(0,113,227,.3)}.v3b.mid .v{color:var(--blue)}
.v3b.high{background:rgba(175,82,222,.06);border-color:rgba(175,82,222,.3)}.v3b.high .v{color:#8940ab}
/* 阶梯瀑布 */
.wfall{display:flex;flex-direction:column;gap:2px;font-size:13px;line-height:1.5}
.wfall .step{display:flex;justify-content:space-between;align-items:center;border-radius:6px;padding:5px 10px;font-family:var(--font-mono)}
.wfall .step .lab{font-family:var(--font-base);color:var(--sub2);font-size:12px}
.wfall .step.buy{background:var(--color-support-bg);border-left:3px solid var(--green)}
.wfall .step.buy.touched{background:rgba(52,199,89,.16);font-weight:700;color:var(--green-d)}
.wfall .step.sell{background:var(--color-resist-bg);border-left:3px solid var(--red)}
.wfall .step.sell.touched{background:rgba(255,59,48,.14);font-weight:700;color:var(--red-d)}
.wfall .divider{display:flex;justify-content:space-between;padding:4px 10px;background:var(--blue-lt);
  border-radius:6px;font-weight:700;color:var(--blue);font-family:var(--font-mono)}
/* 迷你走势 + 均线排列 */
.spark-wrap{display:flex;align-items:center;gap:10px;margin-bottom:8px}
.spark-wrap svg{flex:none;border:1px solid var(--hair);border-radius:6px;background:var(--bg2)}
.ma-state{font-size:13px;font-weight:600;line-height:1.5}
.ma-state.bull{color:var(--green-d)}.ma-state.bear{color:var(--red-d)}.ma-state.mix{color:var(--gold)}
/* 半圆仪表盘 */
.gauge-wrap{display:flex;align-items:center;gap:14px}
.gauge-num{font-size:28px;font-weight:600;font-family:var(--font-mono);color:var(--blue);font-variant-numeric:tabular-nums}
.gauge-lab{font-size:12px;color:var(--sub2);line-height:1.5}
/* 来源徽章 */
.badge-wall{display:flex;flex-wrap:wrap;gap:6px}
.badge{display:inline-flex;align-items:center;gap:6px;font-size:12px;border:1px solid var(--hair);
  border-radius:999px;padding:3px 10px;background:var(--bg2);color:var(--sub2);cursor:default;line-height:1.5}
.badge .av{width:18px;height:18px;border-radius:50%;background:var(--blue-lt);color:var(--blue);
  font-size:11px;font-weight:700;display:inline-flex;align-items:center;justify-content:center;flex:none}
.badge b{color:var(--ink);font-weight:600}
.badge .g{font-weight:700}
.badge .gA{color:var(--blue)}.badge .gB{color:var(--green-d)}.badge .gC{color:var(--gold)}.badge .gD{color:var(--sub2)}
/* 质检列表 */
.checks{font-size:12px;line-height:1.6}
.checks .row{display:flex;gap:8px;padding:4px 0;border-bottom:1px solid var(--hair);align-items:baseline}
.checks .ic{flex:none;font-weight:700;font-size:12px}
.checks .row.block .ic{color:var(--red-d)}.checks .row.warn .ic{color:var(--gold)}.checks .row.pass .ic{color:var(--green-d)}
.checks .row .tx{color:var(--sub2)}
.warn-line{font-size:12px;color:var(--gold);line-height:1.6;margin-top:6px}
.blocker-line{font-size:12px;color:var(--red-d);line-height:1.6;margin-top:6px}
.jumbo{font-size:24px;font-weight:600;font-family:var(--font-mono);font-variant-numeric:tabular-nums;line-height:1.3}
.jumbo.green{color:var(--green-d)}.jumbo.blue{color:var(--blue)}.jumbo.red{color:var(--red-d)}
.micro-row{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;border-top:1px solid var(--hair);padding-top:10px}
.micro{min-width:0}
.micro .k{font-size:12px;color:var(--sub2);letter-spacing:.02em;line-height:1.5}
.micro .v{font-size:16px;font-weight:600;font-family:var(--font-mono);font-variant-numeric:tabular-nums;margin-top:3px;line-height:1.4}
.micro .m{font-size:12px;color:var(--meta);margin-top:2px;line-height:1.5}
.formula-mini{font-size:12px;color:var(--sub2);margin-top:8px;border-top:1px solid var(--hair);padding-top:8px;line-height:1.7}
.calc-body .row{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:8px}
.calc-body label{font-size:12px;color:var(--sub2);display:block;margin-bottom:3px;line-height:1.5}
.calc-body input{width:100%;border:1px solid var(--hair);border-radius:5px;padding:5px 7px;font-size:13px;
  font-family:var(--font-mono)}
.calc-out{font-size:13px;line-height:1.8;font-family:var(--font-mono);border-top:1px solid var(--hair);padding-top:8px}
.pos-legend{display:flex;gap:12px;flex-wrap:wrap;font-size:12px;color:var(--sub2);margin-top:8px;line-height:1.5}
.pos-legend b{font-family:var(--font-mono);font-weight:600;color:var(--ink)}
.trigger-line{font-size:12px;color:var(--sub2);margin-top:8px;border-top:1px solid var(--hair);padding-top:8px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:1.5}

/* ---- Modal ---- */
.mask{position:fixed;inset:0;background:rgba(0,0,0,.25);display:none;z-index:100;align-items:center;justify-content:center}
.mask.on{display:flex}
.modal{background:var(--bg2);border-radius:12px;width:min(640px,92vw);max-height:80vh;display:flex;flex-direction:column;
  box-shadow:0 20px 60px rgba(0,0,0,.18)}
.modal-hd{display:flex;justify-content:space-between;align-items:center;padding:14px 18px;border-bottom:1px solid var(--hair)}
.modal-hd h3{font-size:15px;font-weight:600}
.modal-hd .btns{display:flex;gap:8px;align-items:center}
.modal-hd .close,.modal-hd .copy{border:1px solid var(--hair);background:none;font-size:12px;color:var(--sub2);
  border-radius:6px;padding:4px 10px;transition:all .15s;line-height:1.5}
.modal-hd .copy:hover{border-color:var(--blue);color:var(--blue)}
.modal-bd{padding:14px 18px;overflow-y:auto;font-size:13px;line-height:1.7}
.formula-box{background:var(--bg);border:1px solid var(--hair);border-radius:8px;padding:12px 14px;
  margin-bottom:10px;font-size:13px;white-space:pre-wrap;line-height:1.7}
.step-item{display:flex;gap:10px;padding:7px 0;border-bottom:1px solid var(--hair);font-size:13px;line-height:1.6}
.step-item:last-child{border-bottom:none}
.step-no{flex:none;width:22px;height:22px;border-radius:50%;background:var(--blue-lt);color:var(--blue);
  font-size:12px;font-weight:700;display:inline-flex;align-items:center;justify-content:center;font-family:var(--font-mono)}
.eq{font-family:var(--font-mono);color:var(--blue);display:block;margin-top:4px}
.src{font-size:12px;color:var(--meta);display:block;margin-top:3px;line-height:1.5}
.src-badge{display:inline-block;font-size:12px;border:1px solid var(--hair);border-radius:999px;
  padding:2px 10px;color:var(--sub2);margin:4px 4px 0 0;line-height:1.5}

/* ============ 响应式 ============ */
@media(max-width:1399px){
  .shell{grid-template-columns:84px minmax(0,1fr) 340px}
  .sb-hd span:last-child,.sb-search{display:none}
  .sb-item .nm,.sb-item .cd,.sb-item .px{display:none}
  .sb-item{padding:10px 4px;text-align:center}
  .sb-item .l1{flex-direction:column;gap:2px;align-items:center}
  .sb-item .code{display:block;font-family:var(--font-mono);font-size:12px}
  .sb-item .bar{left:6px;right:6px}
}
@media(max-width:1099px){
  html,body{overflow:auto}
  .shell{grid-template-columns:1fr;grid-template-rows:auto;height:auto;display:block}
  .sidebar{border-right:none;border-bottom:1px solid var(--hair)}
  .sb-list{display:flex;overflow-x:auto;flex:none}
  .sb-item{min-width:120px;border-right:1px solid var(--hair);border-bottom:none}
  .center{min-height:0}
  .chart-zone{height:45vh;position:sticky;top:0;z-index:10;background:var(--bg2);border-bottom:1px solid var(--hair)}
  .hero-strip .hr{margin-left:0}
  .wall{max-height:none;overflow:visible;display:block;padding:10px}
  .w-card{margin-bottom:12px}
  .popover{left:6px;right:6px;width:auto}
}
@media(max-width:640px){
  .v3-blocks{grid-template-columns:1fr}
  .sr-list{grid-template-columns:1fr}
  .micro-row{grid-template-columns:1fr}
  .top-upd{display:none}
  .top-gate{max-width:150px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
  .stock-trig{max-width:150px}
}
</style>
</head>
<body>

<header class="topbar">
  <button class="brand" onclick="showOverview()"><i></i>估值雷达</button>
  <button class="stock-trig" id="stockTrig" onclick="togglePop()">
    <span id="trigName">—</span><span class="arr">▾</span>
  </button>
  <div class="top-gate"><span class="dot" id="gateDot"></span><span id="gateTxt">市场数据加载中…</span></div>
  <div class="top-upd">更新 <span id="updAt">—</span> ｜ 数据 <span id="dataDate">—</span></div>
  <div class="popover" id="popover">
    <input class="pop-search" id="popSearch" placeholder="搜索代码 / 名称…（Ctrl+K，↑↓ 选择，Enter 确认）" oninput="filterPop(this.value)">
    <div class="pop-list" id="popList"></div>
  </div>
</header>

<div class="shell">
  <aside class="sidebar">
    <div class="sb-hd"><span>自选池</span><span id="sbCnt">0</span></div>
    <input class="sb-search" id="sbSearch" placeholder="搜索…" oninput="filterList(this.value)">
    <div class="sb-list" id="sbList"></div>
  </aside>

  <main class="center" id="center">
    <div class="hero-strip" id="heroStrip">
      <div class="hl">
        <div class="eyebrow" id="hRoute">—</div>
        <h1 id="hName">—</h1>
        <div class="tick" id="hTicker">—</div>
        <div class="pills" id="hPills"></div>
      </div>
      <div class="hr">
        <div class="price" id="hPrice">—</div>
        <div class="pct" id="hPct">—</div>
        <div class="mos-wrap">
          <div class="mos-track"><span>低估</span><span>估值带 · 安全边际</span><span>高估</span></div>
          <div class="mos-bar">
            <i style="width:25%;background:rgba(52,199,89,.55)"></i>
            <i style="width:50%;background:rgba(0,113,227,.45)"></i>
            <i style="width:25%;background:rgba(255,59,48,.55)"></i>
          </div>
          <div class="mos-marker"><div class="mos-dot" id="mosDot" style="left:50%"></div></div>
          <div class="mos-txt" id="mosTxt">—</div>
        </div>
      </div>
    </div>

    <div class="chart-zone" id="chartZone">
      <div class="chart-toolbar">
        <h3 id="chartTitle">估值雷达主图 · 日K</h3>
        <span class="info" id="chartInfo">—</span>
        <div class="range-btns" id="rangeBtns">
          <button class="range-btn" data-n="60">60日</button>
          <button class="range-btn" data-n="120">120日</button>
          <button class="range-btn on" data-n="250">250日</button>
          <button class="range-btn" data-n="0">全部</button>
        </div>
        <div class="ma-legend" id="maLegend">
          <button class="ma-chip on" data-ma="5"><i style="background:#0071e3"></i>MA5</button>
          <button class="ma-chip on" data-ma="10"><i style="background:#5e5ce6"></i>MA10</button>
          <button class="ma-chip on" data-ma="20"><i style="background:#b8956a"></i>MA20</button>
          <button class="ma-chip on" data-ma="60"><i style="background:#86868b"></i>MA60</button>
        </div>
      </div>
      <div class="chart-wrap" id="chartWrap">
        <svg id="mainChart" role="img" aria-label="K线估值主图"></svg>
        <div class="ktip" id="chartTip"></div>
      </div>
      <div class="chart-foot">
        <span class="legend-mini"><i style="background:rgba(52,199,89,.45)"></i>低估区</span>
        <span class="legend-mini"><i style="background:rgba(0,113,227,.4)"></i>合理区</span>
        <span class="legend-mini"><i style="background:rgba(255,59,48,.45)"></i>高估区</span>
        <span class="legend-mini"><i style="background:var(--color-support)"></i>支撑 S</span>
        <span class="legend-mini"><i style="background:var(--color-resist)"></i>压力 R</span>
        <span class="legend-mini"><i style="background:var(--candle-up)"></i>上涨</span>
        <span class="legend-mini"><i style="background:var(--candle-dn)"></i>下跌</span>
      </div>
    </div>

    <div class="ov-wrap" id="ovWrap" style="display:none">
      <table class="ov-table" id="ovTable"></table>
    </div>
  </main>

  <aside class="wall" id="wall">
    <div class="w-card"><div class="w-title">关键价位 · 支撑压力</div><div id="c0Body">—</div></div>
    <div class="w-card"><div class="w-title">Step 1 · 市场与模型</div><div id="c1Body">—</div></div>
    <div class="w-card"><div class="w-title">Step 2 · 三档估值<span class="sp" id="c2Src"></span></div><div id="c2Body">—</div></div>
    <div class="w-card"><div class="w-title">Step 3 · 买卖阶梯</div><div id="c3Body">—</div></div>
    <div class="w-card"><div class="w-title">Step 4 · 技术择时</div><div id="c4Body">—</div></div>
    <div class="w-card"><div class="w-title">Step 5 · 仓位管理</div><div id="c5Body">—</div></div>
    <div class="w-card"><div class="w-title">Step 6 · 数据依据</div><div id="c6Body">—</div></div>
  </aside>
</div>

<div class="mask" id="mask" onclick="if(event.target===this)closeModal()">
  <div class="modal">
    <div class="modal-hd">
      <h3 id="m-title">计算过程</h3>
      <div class="btns"><button class="copy" onclick="copyFormula()">复制公式</button><button class="close" onclick="closeModal()">✕</button></div>
    </div>
    <div class="modal-bd" id="m-body"></div>
  </div>
</div>

<script>
const DATA = __DATA__;
/* ============ 状态 ============ */
const RANGE_STATE = { n: 250 };
const MA_VIS = {5:true, 10:true, 20:true, 60:true};
let CUR = null;
let VIEW = 'stock';
let PIN = null;
let CHART_ROWS = [];
let POP_IDX = -1;
const PREV = { price:null, pct:null, vLow:null, vMid:null, vHigh:null, base:null };

/* ============ 工具 ============ */
const fmt2 = v => v==null ? '—' : (+v).toLocaleString('zh-CN',{maximumFractionDigits:2});
const fmt0 = v => v==null ? '—' : (+v).toLocaleString('zh-CN',{maximumFractionDigits:0});
const pctCol = p => p > 0 ? 'up-c' : (p < 0 ? 'dn-c' : '');
const phDetail = ph => ph && ph.ok ? ((ph.metric||'PE') + ' ' + (ph.pe!=null?fmt2(ph.pe):'—') + (ph.pe_min!=null?' · 5年区间 '+fmt2(ph.pe_min)+'~'+fmt2(ph.pe_max):'') + (ph.source?' · '+ph.source:'')) : '—';
function maVal(rows, i, win){ if(i < win-1) return null; let s=0; for(let j=i-win+1;j<=i;j++) s+=rows[j].c; return s/win; }
function lastMa(rows, win){ if(!rows || rows.length < win) return null; let s=0; const n=rows.length; for(let j=n-win;j<n;j++) s+=rows[j].c; return s/win; }
function zoneIdx(z){ return { '深度低估':0,'低估':1,'合理下沿':2,'合理上沿':3,'高估':4,'泡沫':5 }[z] ?? 6; }
function zmeta(st){
  if(st.decision_usable) return { c: zoneIdx(st.zone), label: st.zone };
  if(st.decision_status === 'observe') return { c: 'o', label: '观察' };
  if(st.v_low != null && st.price != null){
    if(st.price <= st.v_low) return { c: 0, label: '低估可买' };
    if(st.price <= st.v_mid) return { c: 2, label: '合理偏低' };
    if(st.price <= st.v_high) return { c: 3, label: '合理偏高' };
    return { c: 4, label: '高估观望' };
  }
  const ph = (DATA.pe_history||{})[st.ticker];
  if(ph && ph.ok && ph.signal){
    return { c: ph.signal==='低估可买' ? 0 : (ph.signal==='高估观望' ? 4 : 3), label: ph.signal };
  }
  if(st.pe_ttm != null && st.pe_ttm > 0) return { c: 5, label: 'PE参考' };
  return { c: 6, label: '无数据' };
}
/* 数字滚动（300ms ease-out，切换股票时平滑过渡） */
function animateNum(el, from, to, fmt){
  if(!el) return;
  const f = fmt || fmt2;
  if(from == null || !isFinite(+from) || !isFinite(+to)){ el.textContent = f(to); return; }
  const t0 = performance.now(), dur = 300;
  function step(now){
    const p = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - p, 3);
    el.textContent = f(+from + (+to - +from) * e);
    if(p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

/* ============ 左导航列表 ============ */
function renderList(filter){
  const el = document.getElementById('sbList');
  const q = (filter||'').trim().toLowerCase();
  el.innerHTML = DATA.stocks.filter(s => !q || s.name.toLowerCase().includes(q) || s.ticker.includes(q))
    .map(s => {
      const zm = zmeta(s);
      const zc = ['z0','z0','z2','z2','z4','z4','z6'][zm.c] || 'z6';
      const rawPos = (s.v_low!=null && s.v_high!=null && s.v_high>s.v_low)
        ? Math.max(0, Math.min(100, (s.price - s.v_low) / (s.v_high - s.v_low) * 100)) : 50;
      return '<button class="sb-item '+(s.ticker===CUR?.ticker&&VIEW==='stock'?'on':'')+'" onclick="switchStock(\''+s.ticker+'\')">'
        + '<div class="l1"><span class="nm">'+s.name+'</span><span class="cd">'+s.ticker+'</span>'
        + '<span class="px">¥'+fmt2(s.price)+'</span>'
        + '<span class="chg '+pctCol(s.pct)+'">'+(s.pct>0?'+':'')+fmt2(s.pct)+'%</span></div>'
        + '<div class="l1"><span class="code">'+s.ticker+'</span>'
        + '<span class="sb-zone '+zc+'">'+zm.label+'</span></div>'
        + '<div class="bar"><span class="mark" style="left:'+rawPos+'%"></span></div>'
        + '</button>';
    }).join('');
  document.getElementById('sbCnt').textContent = DATA.stocks.length + ' 只';
}
function filterList(v){ renderList(v); }

/* ============ 弹出选股器（↑↓ Enter 键盘导航） ============ */
function togglePop(){ const p = document.getElementById('popover'); p.classList.toggle('on'); if(p.classList.contains('on')){ renderPop(); POP_IDX = -1; } }
function popItems(){ return Array.from(document.querySelectorAll('#popList .pop-item')); }
function popMove(dir){
  const items = popItems();
  if(!items.length) return;
  POP_IDX = Math.max(0, Math.min(items.length-1, POP_IDX + dir));
  items.forEach((it,i) => it.classList.toggle('sel', i === POP_IDX));
  items[POP_IDX].scrollIntoView({block:'nearest'});
}
function popConfirm(){
  const items = popItems();
  if(POP_IDX >= 0 && items[POP_IDX]) items[POP_IDX].click();
}
function renderPop(filter){
  const q = (filter||'').trim().toLowerCase();
  document.getElementById('popList').innerHTML =
    '<button class="pop-item" onclick="showOverview();togglePop()"><span class="nm">股票池总览</span><span class="st">全部 '+DATA.stocks.length+' 只</span></button>' +
    DATA.stocks.filter(s => !q || s.name.toLowerCase().includes(q) || s.ticker.includes(q))
      .map(s => { const zm = zmeta(s);
        return '<button class="pop-item" onclick="switchStock(\''+s.ticker+'\');togglePop()">'
          + '<span class="nm">'+s.name+'</span><span class="cd">'+s.ticker+'</span>'
          + '<span class="st" style="color:'+(zm.c===0||zm.c===1?'var(--green-d)':(zm.c>=4?'var(--red-d)':'var(--sub2)'))+'">'+zm.label+'</span>'
          + '</button>'; }).join('');
  POP_IDX = -1;
}
function filterPop(v){ renderPop(v); }
document.addEventListener('keydown', e => {
  const pop = document.getElementById('popover');
  if((e.ctrlKey||e.metaKey) && e.key.toLowerCase()==='k'){ e.preventDefault(); togglePop(); return; }
  if(pop.classList.contains('on')){
    if(e.key==='ArrowDown'){ e.preventDefault(); popMove(1); return; }
    if(e.key==='ArrowUp'){ e.preventDefault(); popMove(-1); return; }
    if(e.key==='Enter'){ e.preventDefault(); popConfirm(); return; }
  }
  if(e.key==='Escape'){ pop.classList.remove('on'); closeModal(); }
});

/* ============ 市场温度 ============ */
function grahamPill(){
  const m = DATA.market;
  const g = (m.graham_metrics||[]).find(x=>x.key==='cs985') || (m.graham_metrics||[])[0] || {};
  if(!g.graham){ document.getElementById('gateTxt').textContent='市场数据缺失'; return; }
  const dot = document.getElementById('gateDot');
  dot.className = 'dot ' + (g.graham>=2.3?'dot-ok':(g.graham>=1.8?'dot-warn':'dot-bad'));
  const stale = ((m.cs985||{}).stale || (m.bond_10y||{}).stale) ? ' · 滞后' : '';
  document.getElementById('gateTxt').textContent = '市场温度 ' + g.graham + ' · ' + g.band + stale;
  document.getElementById('updAt').textContent = (DATA.updated_at||'').slice(5,16);
  document.getElementById('dataDate').textContent = DATA.data_date || '—';
}

/* ============ 总览 ============ */
function showOverview(){
  VIEW = 'overview'; CUR = null; PIN = null;
  document.getElementById('chartZone').style.display = 'none';
  const ov = document.getElementById('ovWrap'); ov.style.display = 'block';
  document.getElementById('ovTable').innerHTML =
    '<tr><th>股票</th><th>现价</th><th>状态</th><th>质量</th><th>估值带</th><th>今日信号</th></tr>' +
    DATA.stocks.map(s => { const zm = zmeta(s);
      const g = ((s.decision_data||{}).quality||{}).grade || '—';
      const sig = (s.signals||[]).join('；') || '—';
      return '<tr onclick="switchStock(\''+s.ticker+'\')">'
        + '<td>'+s.name+'<br><span style="color:var(--meta);font-size:12px">'+s.ticker+'</span></td>'
        + '<td>'+fmt2(s.price)+'</td><td>'+zm.label+'</td><td>'+g+'</td>'
        + '<td>'+(s.v_low!=null?fmt2(s.v_low)+' ~ '+fmt2(s.v_high):'—')+'</td><td>'+sig+'</td></tr>'; }).join('');
  renderList();
  const w = document.getElementById('wall');
  w.innerHTML = '<div class="w-card"><div class="w-title">市场估值环境（格雷厄姆指数 · 仅背景）</div>'
    + (DATA.market.graham_metrics||[]).map(x=>'<div class="micro-row" style="border-top:none;padding-top:0;margin-bottom:8px">'
      + '<div class="micro"><div class="k">'+x.label+'</div><div class="v">'+x.pe+'</div><div class="m">PE</div></div>'
      + '<div class="micro"><div class="k">格雷厄姆</div><div class="v">'+x.graham+'</div><div class="m">'+x.band+'</div></div>'
      + '<div class="micro"><div class="k">公式</div><div class="v" style="font-size:13px">(1/PE)÷10Y国债</div><div class="m">'+fmt2(((DATA.market.bond_10y||{}).value||0)*100)+'%</div></div>'
      + '</div>').join('')
    + '<div class="formula-mini">v2 定位：仅市场背景参考，不构成仓位硬闸门；不生成个股动作、清仓命令或总仓上限。</div></div>';
}

/* ============ 切换股票（数字滚动过渡） ============ */
function switchStock(ticker){
  const st = DATA.stocks.find(s=>s.ticker===ticker);
  if(!st) return;
  const prevPrice = PREV.price, prevPct = PREV.pct;
  CUR = st; VIEW = 'stock'; PIN = null;
  localStorage.setItem('radar_last', ticker);
  document.getElementById('chartZone').style.display = '';
  document.getElementById('ovWrap').style.display = 'none';
  document.getElementById('trigName').textContent = st.name + ' ' + st.ticker;
  renderList();
  renderHero(st, prevPrice, prevPct);
  renderWall(st);
  renderKline();
  PREV.price = st.price; PREV.pct = st.pct;
}

/* ============ Hero 条 ============ */
function renderHero(st, prevPrice, prevPct){
  const model = st.valuation_model || {};
  document.getElementById('hRoute').textContent = (model.label || st.route || '—') + ' · ' +
    (st.decision_status === 'ready' ? '质量门通过' : st.decision_status === 'reference_only' ? '区间参考' : st.decision_status === 'observe' ? '观察' : '路由拦截');
  document.getElementById('hName').textContent = st.name;
  document.getElementById('hTicker').textContent = st.ticker + ' · TTM PE ' + fmt2(st.pe_ttm) + ' · PB ' + fmt2(st.pb);
  const zm = zmeta(st);
  const zcol = ['var(--green-d)','var(--green-d)','var(--gold)','var(--gold)','var(--red-d)','var(--red-d)','var(--sub2)'][zm.c] || 'var(--sub2)';
  const pills = ['<span class="pill"><span class="dot" style="background:'+zcol+'"></span>'+zm.label+'</span>'];
  if(st.decision_usable && st.band_pos_raw!=null) pills.push('<span class="pill num">估值带位置 '+fmt2(st.band_pos_raw*100)+'%</span>');
  if(st.decision_usable && st.mos!=null) pills.push('<span class="pill num">安全边际 '+(st.mos>=0?'+':'')+(st.mos*100).toFixed(1)+'%</span>');
  if(!st.decision_usable && st.reference_usable && st.reference_zone) pills.push('<span class="pill num">参考区间 '+st.reference_zone+'</span>');
  if(st.pe_ttm!=null && st.pe_ttm>0){ const ph=(DATA.pe_history||{})[st.ticker];
    if(ph && ph.ok && ph.pctile!=null) pills.push('<span class="pill num">PE分位 '+Math.round(ph.pctile*100)+'%</span>'); }
  document.getElementById('hPills').innerHTML = pills.join('');
  const pcol = st.pct>0?'var(--candle-up)':(st.pct<0?'var(--candle-dn)':'var(--sub2)');
  const priceEl = document.getElementById('hPrice');
  animateNum(priceEl, prevPrice, st.price, v => '¥' + fmt2(v));
  priceEl.style.color = pcol;
  const arrow = st.pct>0?'▲':(st.pct<0?'▼':'◆');
  const pctEl = document.getElementById('hPct');
  animateNum(pctEl, prevPct, st.pct, v => arrow + ' ' + (v>0?'+':'') + fmt2(v) + '%');
  pctEl.style.color = pcol;
  const dot = document.getElementById('mosDot');
  const raw = (st.v_low!=null && st.v_high!=null && st.v_high>st.v_low) ? (st.price-st.v_low)/(st.v_high-st.v_low) : null;
  if(raw != null){
    dot.style.left = Math.max(0,Math.min(100,raw*100)) + '%';
    dot.style.display = '';
    let concl;
    if(st.decision_usable){
      concl = '当前处于' + st.zone + '区，安全边际 ' + (st.mos>=0?'+':'') + (st.mos*100).toFixed(1) + '%';
    } else if(st.reference_zone){
      concl = '参考区间：' + st.reference_zone + '（质量门未通过，不可执行）';
    } else {
      concl = '估值带 V_low ¥'+fmt2(st.v_low)+' / V_mid ¥'+fmt2(st.v_mid)+' / V_high ¥'+fmt2(st.v_high)+'（参考级）';
    }
    document.getElementById('mosTxt').textContent = concl;
  } else {
    dot.style.display = 'none';
    document.getElementById('mosTxt').textContent = '无估值区间（路由拦截/观察）';
  }
}

/* ============ 折叠组件 ============ */
function foldHTML(id, inner){
  return '<button class="fold-toggle" onclick="toggleFold(\''+id+'\')">展开计算过程 ▾</button>'
       + '<div class="fold" id="'+id+'">'+inner+'</div>';
}
function toggleFold(id){
  const f = document.getElementById(id);
  if(!f) return;
  f.classList.toggle('open');
  const btn = f.previousElementSibling;
  if(btn) btn.textContent = f.classList.contains('open') ? '收起计算过程 ▴' : '展开计算过程 ▾';
}
function calcStepsHTML(st){
  const steps = ((st.decision_data||{}).valuation||{}).calc_steps || [];
  if(!steps.length) return '<div class="formula-mini">引擎未输出计算步骤。</div>';
  return steps.map(s =>
    '<div class="step-item"><div class="step-no">' + (s.id==='v_low'?'低':(s.id==='v_mid'?'中':'高')) + '</div><div>'
    + '<b>' + (s.label||s.id) + '</b>：' + (s.formula||'') 
    + '<span class="eq">' + (s.substitution||'') + ' = ' + fmt2(s.result) + ' 元</span></div></div>'
  ).join('');
}

/* ============ 数据墙 ============ */
function renderWall(st){
  const model = st.valuation_model || {};
  const isBank = model.code==='bank_pb_roe', isInfra = model.code==='infrastructure_cashflow';
  const isIns = model.code==='insurance_pev', isNorm = st.forecast_basis==='NORMALIZED';
  const usable = st.decision_usable;
  const q = st.data_quality || {};
  const checks = q.checks || [];
  const checksCore = checks.filter(c => !c.passed && c.severity !== 'info');
  const checksAll = checks;
  const checksHTML = (all) => (all ? checksAll : checksCore).map(c =>
    '<div class="row ' + (c.passed ? 'pass' : (c.severity==='block'?'block':'warn')) + '">'
    + '<span class="ic">' + (c.passed ? '✓' : (c.severity==='block'?'✕':'!')) + '</span>'
    + '<span class="tx">' + c.id + '：' + c.detail + '</span></div>').join('')
    || '<div class="formula-mini">无质检项</div>';
  const foldChecks = (id) => foldHTML(id, '<div class="checks">' + checksHTML(false) + '</div>'
    + (checksAll.length > checksCore.length
      ? '<button class="fold-toggle" onclick="this.remove();document.getElementById(\''+id+'_all\').style.display=\'block\'">展开全部质检项</button>'
        + '<div id="'+id+'_all" style="display:none" class="checks">' + checksHTML(true) + '</div>' : ''));

  /* ---- Card 0：关键价位 · S/R 价格轨道 ---- */
  const srs = st.support||[], rrs = st.resistance||[];
  const k = st.kline||[];
  const lo250 = k.length ? Math.min(...k.slice(-250).map(r=>r.l)) : null;
  const hi250 = k.length ? Math.max(...k.slice(-250).map(r=>r.h)) : null;
  const allLv = srs.concat(rrs).map(x=>+x.level).filter(v=>isFinite(v));
  let tMin = Math.min(...allLv.concat([st.price, lo250].filter(v=>v!=null)));
  let tMax = Math.max(...allLv.concat([st.price, hi250].filter(v=>v!=null)));
  if(tMin === tMax){ tMin -= 1; tMax += 1; }
  const pos = v => Math.max(2, Math.min(98, (v - tMin) / (tMax - tMin) * 100));
  const dots = [];
  srs.forEach((x,i) => dots.push({cls:'s'+(x.level_ev==='A'?'A':(x.level_ev==='C'?'C':'B')), v:+x.level, t:'S'+(i+1)}));
  rrs.forEach((x,i) => dots.push({cls:'r'+(x.level_ev==='A'?'A':(x.level_ev==='C'?'C':'B')), v:+x.level, t:'R'+(i+1)}));
  dots.sort((a,b)=>a.v-b.v);
  let c0 = '<div class="sr-track">';
  [20,40,60,80].forEach(p => { c0 += '<span class="tick" style="left:'+p+'%"></span>'; });
  c0 += dots.map(d => '<span class="sr-dot '+d.cls+'" style="left:'+pos(d.v)+'%" title="'+d.t+' ¥'+fmt2(d.v)+'"></span>').join('');
  c0 += '<span class="sr-dot cur" style="left:'+pos(st.price)+'%" title="现价 ¥'+fmt2(st.price)+'"></span>';
  c0 += '</div>';
  c0 += '<div class="sr-list">';
  srs.forEach((x,i) => { c0 += '<div class="row s"><span class="m">S'+(i+1)+' · '+(x.method||'')+' <b class="g">'+x.level_ev+'级</b></span><span class="v">¥'+fmt2(x.level)+'</span></div>'; });
  rrs.forEach((x,i) => { c0 += '<div class="row r"><span class="m">R'+(i+1)+' · '+(x.method||'')+' <b class="g">'+x.level_ev+'级</b></span><span class="v">¥'+fmt2(x.level)+'</span></div>'; });
  c0 += '</div>';
  if(!srs.length && !rrs.length) c0 = '<div class="formula-mini">暂无支撑/压力数据（K线不足或未配置）。</div>';
  c0 += '<div class="formula-mini">轨道区间：¥'+fmt2(tMin)+' ~ ¥'+fmt2(tMax)+'（250日高低点）；蓝点=现价，实心=A级技术位，虚线=B级，细边=C级（估值锚/贴线/转换位）。</div>';
  document.getElementById('c0Body').innerHTML = c0;

  /* ---- Card 1：市场与模型 + 质检折叠 ---- */
  const g = (DATA.market.graham_metrics||[]).find(x=>x.key==='cs985') || (DATA.market.graham_metrics||[])[0] || {};
  const grade = q.grade || '—';
  const gCol = g.graham>=2.3?'var(--green-d)':(g.graham>=1.8?'var(--gold)':'var(--red-d)');
  document.getElementById('c1Body').innerHTML =
    '<div class="micro-row" style="border-top:none;padding-top:0">'
    + '<div class="micro"><div class="k">格雷厄姆指数</div><div class="v">'+(g.graham||'—')+'</div>'
    + '<div class="m" style="color:'+gCol+'">'+(g.band||'—')+((DATA.market.cs985||{}).stale?' · 滞后':'')+'</div></div>'
    + '<div class="micro"><div class="k">估值模型</div><div class="v" style="font-size:14px">'+(model.code||'—')+'</div>'
    + '<div class="m">'+((model.label||'').split('·')[0]||'')+'</div></div>'
    + '<div class="micro"><div class="k">数据质量</div><div class="v" style="color:'+(grade==='B'?'var(--green-d)':(grade==='C'?'var(--gold)':'var(--red-d)'))+'">'+grade+'</div>'
    + '<div class="m">'+checks.filter(c=>!c.passed&&c.severity!=='info').length+' 项未通过</div></div>'
    + '</div>'
    + foldChecks('fold1');

  /* ---- Card 2：三档估值（三色块 + 折叠计算过程/计算器） ---- */
  let c2 = '', c2src = '';
  if(st.decision_status==='blocked'){
    const ph = (DATA.pe_history||{})[st.ticker];
    c2 = '<div class="blocker-line">' + ((st._blockers||[])[0]||'路由拦截：模型输入不完整') + '</div>'
      + (ph && ph.ok ? '<div class="micro-row">'
        + '<div class="micro"><div class="k">PE/PB 历史分位</div><div class="v">'+(ph.pctile!=null?Math.round(ph.pctile*100)+'%':'—')+'</div><div class="m">'+phDetail(ph)+'</div></div>'
        + '<div class="micro"><div class="k">分位判断</div><div class="v" style="font-size:14px">'+(ph.signal||'—')+'</div><div class="m">'+(ph.note||'')+'</div></div>'
        + '<div class="micro"><div class="k">TTM PE/PB</div><div class="v">'+fmt2(st.pe_ttm)+'/'+fmt2(st.pb)+'</div><div class="m">行情源</div></div>'
        + '</div>' : '');
  } else {
    let fB='EPS', fM='PE档';
    if(isIns){ fB='每股EV'; fM='P/EV'; }
    else if(isBank||isInfra){ fB='BVPS'; fM='PB'; }
    else if(isNorm){ fB='正常化EPS'; fM='PE'; }
    const b1 = isIns?fmt2(st.ev_per_share):(isBank||isInfra?fmt2(st.bvps):fmt2(st.eps_base));
    const m1 = isIns?st.pev_low:(isBank||isInfra?st.pb_low:st.pe_low);
    const m2 = isIns?st.pev_mid:(isBank||isInfra?st.pb_mid:st.pe_mid);
    const m3 = isIns?st.pev_high:(isBank||isInfra?st.pb_high:st.pe_high);
    const e1 = isIns?'EV':(isBank||isInfra?'BVPS':fmt2(st.eps_bear));
    const e2 = isIns?'EV':(isBank||isInfra?'BVPS':fmt2(st.eps_base));
    const e3 = isIns?'EV':(isBank||isInfra?'BVPS':fmt2(st.eps_bull));
    c2 =
      '<div class="v3-blocks">'
      + '<div class="v3b low"><div class="k">保守 V_low'+(usable?' · 买入启动':'')+'</div><div class="v">¥'+fmt2(st.v_low)+'</div><div class="f">'+e1+' × '+m1+'×</div></div>'
      + '<div class="v3b mid"><div class="k">基准 V_mid · 价值中枢</div><div class="v">¥'+fmt2(st.v_mid)+'</div><div class="f">'+e2+' × '+m2+'×</div></div>'
      + '<div class="v3b high"><div class="k">乐观 V_high'+(usable?' · 卖出启动':'')+'</div><div class="v">¥'+fmt2(st.v_high)+'</div><div class="f">'+e3+' × '+m3+'×</div></div>'
      + '</div>'
      + '<div class="band-track"><div class="dot" style="left:'+(st.v_low!=null&&st.v_high!=null&&st.v_high>st.v_low?Math.max(0,Math.min(100,(st.price-st.v_low)/(st.v_high-st.v_low)*100)):50)+'%"></div></div>'
      + '<div class="band-labels" style="display:flex;justify-content:space-between;font-size:12px;color:var(--sub2);margin-top:4px"><span>低估 ¥'+fmt2(st.v_low)+'</span><span>现价 ¥'+fmt2(st.price)+'</span><span>高估 ¥'+fmt2(st.v_high)+'</span></div>'
      + (!usable?'<div class="warn-line">质量门未通过：参考级区间，不构成买卖动作。</div>':'');
    let foldInner = calcStepsHTML(st);
    if(usable && !isIns && !isBank && !isInfra && !isNorm){
      foldInner += '<div class="calc-body" style="display:block;padding-top:10px"><div class="row">'
        + '<div><label>现价 P</label><input id="i-price" type="number" step="0.01" value="'+st.price+'"></div>'
        + '<div><label>PE低/中/高</label><div style="display:flex;gap:4px"><input id="i-peL" type="number" step="0.5" value="'+st.pe_low+'"><input id="i-peM" type="number" step="0.5" value="'+st.pe_mid+'"><input id="i-peH" type="number" step="0.5" value="'+st.pe_high+'"></div></div>'
        + '<div><label>EPS保守/基准/乐观</label><div style="display:flex;gap:4px"><input id="i-epsB" type="number" step="0.01" value="'+st.eps_bear+'"><input id="i-epsM" type="number" step="0.01" value="'+st.eps_base+'"><input id="i-epsU" type="number" step="0.01" value="'+st.eps_bull+'"></div></div>'
        + '</div><div class="calc-out" id="calcOut">—</div></div>';
    }
    c2 += foldHTML('fold2', foldInner);
    c2src = st.forecast_source || st.pb_source || st.pe_source || '';
  }
  document.getElementById('c2Body').innerHTML = c2 || '<div class="formula-box">无数据</div>';
  document.getElementById('c2Src').textContent = c2src ? c2src.slice(0,26) : '';
  bindCalc();

  /* ---- Card 3：买卖阶梯（瀑布） ---- */
  if(usable && st.v_low!=null && st.v_high!=null){
    const b1=st.v_low*.7, b2=st.v_low*.85, s2=st.v_high+(st.v_high-st.v_mid)*.5, s3=st.v_high*1.3;
    const sellRows = [
      {lab:'3档 · 泡沫警戒 V×1.3', v:s3},
      {lab:'2档 · 分批 V+0.5Δ', v:s2},
      {lab:'1档 · 卖出启动 V_high', v:st.v_high},
    ];
    const buyRows = [
      {lab:'3档 · 买入启动 V_low', v:st.v_low},
      {lab:'2档 · 分批 V×0.85', v:b2},
      {lab:'1档 · 深度低估 V×0.7', v:b1},
    ];
    document.getElementById('c3Body').innerHTML = '<div class="wfall">'
      + sellRows.map(r=>'<div class="step sell'+(st.price>=r.v?' touched':'')+'"><span class="lab">'+r.lab+'</span><span>¥'+fmt2(r.v)+'</span></div>').join('')
      + '<div class="divider"><span>现价</span><span>¥'+fmt2(st.price)+'</span></div>'
      + buyRows.map(r=>'<div class="step buy'+(st.price<=r.v?' touched':'')+'"><span class="lab">'+r.lab+'</span><span>¥'+fmt2(r.v)+'</span></div>').join('')
      + '</div>'
      + foldHTML('fold3','<div class="formula-mini">买入金字塔：每跌 20%~30% 补一档（A级）；卖出倒金字塔：V_high 启动、+0.5Δ 分批、×1.3 泡沫警戒（D级工程档位）。触达档位自动高亮。</div>');
  } else if(st.v_low!=null && st.v_high!=null){
    document.getElementById('c3Body').innerHTML =
      '<div class="warn-line">参考区间 ¥'+fmt2(st.v_low)+' ~ ¥'+fmt2(st.v_high)+'（不可执行）：质量门未通过，不生成买卖阶梯。</div>';
  } else {
    document.getElementById('c3Body').innerHTML =
      '<div class="warn-line">质量门拦截 / 观察路由：补齐输入后由引擎自动恢复。</div>';
  }

  /* ---- Card 4：技术择时（迷你走势 + 均线排列 + S/R + 折叠规则） ---- */
  const rows30 = (st.kline||[]).slice(-30);
  let spark = '';
  if(rows30.length >= 5){
    const mn = Math.min(...rows30.map(r=>r.l)), mx = Math.max(...rows30.map(r=>r.h));
    const pts = rows30.map((r,i) => (8+i*(84/(rows30.length-1))).toFixed(1)+','+(2+(mx-r.c)/(mx-mn||1)*26).toFixed(1)).join(' ');
    spark = '<svg width="100" height="30" viewBox="0 0 100 30"><polyline points="'+pts+'" fill="none" stroke="#0071e3" stroke-width="1.5"/></svg>';
  }
  const m5 = lastMa(st.kline||[],5), m10 = lastMa(st.kline||[],10), m20 = lastMa(st.kline||[],20), m60 = lastMa(st.kline||[],60);
  let maState = '均线缠绕', maCls = 'mix';
  if(m5!=null&&m10!=null&&m20!=null&&m60!=null){
    if(m5>m10&&m10>m20&&m20>m60){ maState='▲ 多头排列（5>10>20>60）'; maCls='bull'; }
    else if(m5<m10&&m10<m20&&m20<m60){ maState='▼ 空头排列（5<10<20<60）'; maCls='bear'; }
  }
  const srCell = (arr, cls, pre) => arr.slice(0,2).map((x,i)=>
    '<div class="sr-list"><div class="row '+cls+'"><span class="m">'+pre+(i+1)+' · '+(x.method||'')+'</span><span class="v">¥'+fmt2(x.level)+'</span></div></div>').join('');
  document.getElementById('c4Body').innerHTML =
    '<div class="spark-wrap">' + spark
    + '<div class="ma-state '+maCls+'">'+maState+'<br><span style="font-weight:400;font-size:12px;color:var(--sub2)">MA5 '+fmt2(m5)+' · MA10 '+fmt2(m10)+' · MA20 '+fmt2(m20)+' · MA60 '+fmt2(m60)+'</span></div></div>'
    + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">'
    + '<div>'+ (srs.slice(0,2).map((x,i)=>'<div class="row s" style="display:flex;justify-content:space-between;font-family:var(--font-mono);font-size:13px;padding:2px 0"><span class="m" style="font-family:var(--font-base);color:var(--sub2);font-size:12px">S'+(i+1)+'</span><span class="v" style="color:var(--green-d);font-weight:600">¥'+fmt2(x.level)+'</span></div>').join('')||'—') + '</div>'
    + '<div>'+ (rrs.slice(0,2).map((x,i)=>'<div class="row r" style="display:flex;justify-content:space-between;font-family:var(--font-mono);font-size:13px;padding:2px 0"><span class="m" style="font-family:var(--font-base);color:var(--sub2);font-size:12px">R'+(i+1)+'</span><span class="v" style="color:var(--red-d);font-weight:600">¥'+fmt2(x.level)+'</span></div>').join('')||'—') + '</div>'
    + '</div>'
    + foldHTML('fold4','<div class="formula-mini">触发规则（A级）：均线延长线/十周线=买点测试 · 强势股首阴回踩10均=短线买点 · 缺口不破是支撑、破则转弱 · 反弹逐根摸线30→60→90→120 · 黄金分割 0.382/0.5/0.618。</div>');

  /* ---- Card 5：仓位（半圆仪表盘） ---- */
  const tpl = {底仓:.55, 活动仓:.25, 短线:.10, 现金:.10};
  let plan = {...tpl};
  if(st.vol){ const sc = Math.min(1, .15/Math.max(st.vol,.01)); plan['底仓']=+(plan['底仓']*sc).toFixed(2); plan['现金']=+(1-plan['底仓']-plan['活动仓']-plan['短线']).toFixed(2); }
  const gaugeF = Math.max(0, Math.min(1, plan['底仓']));
  const th = Math.PI - Math.PI * gaugeF;
  const gx = 54 + 42 * Math.cos(th), gy = 54 - 42 * Math.sin(th);
  const arc = 'M 12 54 A 42 42 0 '+(gaugeF>0.5?1:0)+' 1 '+gx.toFixed(2)+' '+gy.toFixed(2);
  document.getElementById('c5Body').innerHTML =
    '<div class="gauge-wrap">'
    + '<svg width="108" height="60" viewBox="0 0 108 60">'
    + '<path d="M 12 54 A 42 42 0 0 1 96 54" fill="none" stroke="#e8e8ed" stroke-width="12" stroke-linecap="round"/>'
    + '<path d="'+arc+'" fill="none" stroke="var(--blue)" stroke-width="12" stroke-linecap="round"/>'
    + '</svg>'
    + '<div><div class="gauge-num">'+Math.round(plan['底仓']*100)+'%</div><div class="gauge-lab">建议底仓（D级示例模板，不随格雷厄姆指数变动）</div></div>'
    + '</div>'
    + '<div class="pos-legend">'
    + Object.keys(plan).map(k=>'<span>'+k+' <b>'+Math.round(plan[k]*100)+'%</b></span>').join('')
    + '</div>'
    + foldHTML('fold5','<div class="formula-mini">调整期底仓5-6成·进攻期+2成、活动仓2-3成、短线≤2成（A级原话）'+(st.vol?'｜ 波动率修正 σ='+(st.vol*100).toFixed(1)+'% → 底仓 = min(基准, 15%/σ)（D级）':'')+(usable?'':'｜ 仅 ready 个股才可按此执行')+'。格雷厄姆指数仅市场背景，不决定仓位。</div>');

  /* ---- Card 6：数据依据（来源徽章墙 + 质检折叠） ---- */
  const badges = [];
  (st.sources||[]).forEach(src => {
    const gq = src.quality || src.grade || 'C';
    const nm = (src.provider||src.title||'来源');
    badges.push('<span class="badge" title="'+nm+' · '+(src.as_of||'')+' · '+(src.url||'')+'"><span class="av">'+nm.slice(0,1)+'</span><b>'+nm.slice(0,10)+'</b><span class="g g'+gq+'">'+gq+'级</span></span>');
  });
  const ph = (DATA.pe_history||{})[st.ticker];
  if(ph && ph.ok) badges.push('<span class="badge" title="'+(ph.source||'')+' · '+(ph.hist_last_date||'')+'"><span class="av">分</span><b>分位信号</b><span class="g gD">D级</span></span>');
  if(st.pe_source) badges.push('<span class="badge" title="'+st.pe_source+'"><span class="av">倍</span><b>倍数分位</b><span class="g gB">B级</span></span>');
  if(st.pb_source) badges.push('<span class="badge" title="'+st.pb_source+'"><span class="av">PB</span><b>PB分位</b><span class="g gB">B级</span></span>');
  if(st.forecast_source) badges.push('<span class="badge" title="'+st.forecast_source+'"><span class="av">预</span><b>盈利预测</b><span class="g g'+(usable?'A':'D')+'">'+(usable?'A':'D')+'级</span></span>');
  document.getElementById('c6Body').innerHTML =
    '<div class="badge-wall">'+(badges.join('')||'<span class="badge"><b>无结构化来源</b></span>')+'</div>'
    + (st._warnings&&st._warnings.length ? '<div class="warn-line">⚠ '+String(st._warnings[0]).slice(0,90)+'</div>' : '')
    + foldChecks('fold6');
}

/* ============ 内嵌计算器 ============ */
function bindCalc(){
  ['i-price','i-peL','i-peM','i-peH','i-epsB','i-epsM','i-epsU'].forEach(id => {
    const el = document.getElementById(id);
    if(el){ el.oninput = calc; }
  });
  calc();
}
function calc(){
  if(!CUR || !CUR.decision_usable || !document.getElementById('i-price')) return;
  const g = id => { const el = document.getElementById(id); return el ? +el.value : NaN; };
  const P=g('i-price'), peL=g('i-peL'), peM=g('i-peM'), peH=g('i-peH');
  const eB=g('i-epsB'), eM=g('i-epsM'), eU=g('i-epsU');
  if(![P,peL,peM,peH,eB,eM,eU].every(Number.isFinite) || P<=0 || eB<=0) return;
  const vL=eB*peL, vM=eM*peM, vH=eU*peH;
  if(!(0<vL&&vL<=vM&&vM<=vH)) return;
  const raw=(P-vL)/(vH-vL);
  const zone = P<=vL*.9?'深度低估':P<=vL?'低估':P<=vM?'合理下沿':P<=vH?'合理上沿':P<=vH*1.3?'高估':'泡沫';
  const zcol = zone.indexOf('低估')>=0?'var(--green-d)':(zone.indexOf('高估')>=0||zone==='泡沫'?'var(--red-d)':'var(--gold)');
  document.getElementById('calcOut').innerHTML =
    'V = EPS × PE：' + fmt2(vL) + ' / ' + fmt2(vM) + ' / ' + fmt2(vH) + '<br>'
    + '现价 ' + fmt2(P) + ' → <b style="color:'+zcol+'">' + zone + '</b>'
    + ' ｜ 估值带位置 ' + fmt2(raw*100) + '%（模拟预览，不改冻结参数）';
}

/* ============ Modal ============ */
function openModal(title, body){
  document.getElementById('m-title').textContent = title;
  document.getElementById('m-body').innerHTML = body || '—';
  document.getElementById('mask').classList.add('on');
}
function closeModal(){ document.getElementById('mask').classList.remove('on'); }
function copyFormula(){
  const txt = document.getElementById('m-body').innerText || '';
  const done = () => { const b = document.querySelector('.modal-hd .copy'); if(b){ b.textContent='已复制 ✓'; setTimeout(()=>{ b.textContent='复制公式'; }, 1500); } };
  if(navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(txt).then(done).catch(()=>{ fallbackCopy(txt); done(); });
  } else { fallbackCopy(txt); done(); }
}
function fallbackCopy(txt){
  const ta = document.createElement('textarea');
  ta.value = txt; ta.style.position='fixed'; ta.style.opacity='0';
  document.body.appendChild(ta); ta.select();
  try{ document.execCommand('copy'); }catch(e){}
  document.body.removeChild(ta);
}
function stepsHTML(steps, level){
  return steps.map((s,i)=>'<div class="step-item"><div class="step-no">'+(i+1)+'</div><div>'+s.text+(s.eq?'<span class="eq">'+s.eq+'</span>':'')+(s.src?'<span class="src">'+s.src+'</span>':'')+'</div></div>').join('')
    + (level?'<span class="src-badge">'+level+'级依据</span>':'');
}
function ntmFormulaHTML(st){
  const dd = st.decision_data && st.decision_data.forecast;
  const w = dd && dd.weights, yrs = dd && dd.years;
  let html = '';
  if(w && yrs && yrs.length >= 2){
    html += '<div class="formula-box"><b>NTM 加权口径（动态计算，非固定）</b>\n'
      + 'NTM EPS = ' + yrs[0] + 'E × 剩余天数/365 + ' + yrs[1] + 'E × 已过天数/365\n'
      + '= ' + yrs[0] + 'E × ' + w[yrs[0]] + ' + ' + yrs[1] + 'E × ' + w[yrs[1]] + '</div>'
      + '<span class="src-badge">D级：NTM 时间加权，引擎按 as_of 动态计算</span>';
  }
  const gm = st.growth_momentum;
  if(gm && gm.growth > 0.30){
    html += '<div class="formula-box"><b>成长修正认知补偿（PEG 交叉检查）</b>\n'
      + 'FY1 盈利增速 = ' + gm.base_eps + ' ÷ ' + gm.last_eps + ' − 1 = ' + (gm.growth*100).toFixed(0) + '%\n'
      + 'PEG≈1 参考：合理PE ≈ 增速% = ' + gm.peg_pe + '×（高于历史P50时提示，不自动替换倍数）</div>'
      + '<span class="src-badge">A级：合理倍数结合基本面（ROE/净利率趋势）修正</span>';
  }
  return html;
}
function detailBody(st, key){
  const q = st.data_quality || {};
  if(key === 'quality'){
    const chk = (q.checks||[]).map(c => '<div class="step-item"><div class="step-no">'+(c.passed?'✓':'✕')+'</div><div>'+c.id+'：'+c.detail+'</div></div>').join('') || '<div class="formula-box">无检查项</div>';
    return '<div class="formula-box"><b>决策状态：' + st.decision_status + '</b></div>' + chk;
  }
  if(st.decision_status === 'blocked') return '<div class="formula-box"><b>路由拦截</b>：' + (st._blockers||[]).join('；') + '。</div>';
  if(st.decision_status === 'observe') return '<div class="formula-box">观察路由：亏损/特殊资产，不输出估值锚。</div>';
  const mdl = (st.valuation_model||{}).code;
  if(mdl === 'bank_pb_roe' || mdl === 'infrastructure_cashflow'){
    const dg = st.diagnostics || {};
    if(key === 'bvps') return '<div class="formula-box"><b>V = 每股净资产 × 历史PB分位带（百度股市通5年PB，B级校准）</b></div>'
      + stepsHTML([
        {text:'每股净资产 = '+fmt2(st.bvps)+' 元（最新年报，同花顺F10摘要）', src: st.pb_source || '—'},
        {text:'PB 三档 = '+st.pb_low+' / '+st.pb_mid+' / '+st.pb_high+'×（5年分位 P25/P50/P75）'},
        {text:'质量门诊断', src: (dg.note||'') + (dg.pb_theo_mid!=null?' ｜ PB-ROE理论中枢 '+dg.pb_theo_mid+'×（ROE P50 '+dg.roe_p50+'% − g '+((dg.g||0.03)*100).toFixed(0)+'%）÷（Ke '+((dg.ke||0.1)*100).toFixed(0)+'% − g）':'')},
      ], 'B');
    if(key === 'v_low' || key === 'v_mid' || key === 'v_high'){
      const m = {v_low:['P25', st.pb_low, st.v_low], v_mid:['P50', st.pb_mid, st.v_mid], v_high:['P75', st.pb_high, st.v_high]}[key];
      return '<div class="formula-box"><b>' + key + ' = 每股净资产 × 历史PB分位（' + m[0] + '）</b></div>'
        + stepsHTML([
          {text:'每股净资产 = '+fmt2(st.bvps)+' 元'},
          {text:'历史PB分位 = '+m[1]+'×'},
          {text:'计算', eq: key + ' = '+fmt2(st.bvps)+' × '+m[1]+' = '+fmt2(m[2])+' 元'}], 'B');
    }
  }
  if(mdl === 'insurance_pev'){
    const evSrc = ((st.decision_data&&st.decision_data.sources)||[]).find(x=>x.type==='insurance_ev');
    if(key === 'ev') return '<div class="formula-box"><b>V = 每股内含价值(EV) × 目标 P/EV</b></div>'
      + stepsHTML([
        {text:'每股EV = '+fmt2(st.ev_per_share)+' 元（年报 '+(st.ev_as_of||'—')+'）', src: evSrc ? evSrc.provider + ' · ' + evSrc.as_of : '—'},
        {text:'目标P/EV三档 = '+st.pev_low+' / '+st.pev_mid+' / '+st.pev_high+'×', src:'D级工程参数（行业惯例区间），待历史P/EV分位校准'},
      ], 'D') + (evSrc && evSrc.url ? '<a href="'+evSrc.url+'" target="_blank" style="font-size:12px">数据源 ↗</a>' : '');
    if(key === 'v_low' || key === 'v_mid' || key === 'v_high'){
      const m = {v_low:['低档','保守',st.pev_low,st.v_low], v_mid:['中枢','基准',st.pev_mid,st.v_mid], v_high:['高档','乐观',st.pev_high,st.v_high]}[key];
      return '<div class="formula-box"><b>' + key + ' = 每股EV × 目标P/EV' + m[0] + '</b></div>'
        + stepsHTML([
          {text:'每股EV = '+fmt2(st.ev_per_share)+' 元（年报 '+(st.ev_as_of||'—')+'）'},
          {text:'目标P/EV = '+m[2]+'×（'+m[1]+'档）'},
          {text:'计算', eq: key + ' = '+fmt2(st.ev_per_share)+' × '+m[2]+' = '+fmt2(m[3])+' 元'}], 'D');
    }
  }
  if(key==='eps'){
    if(st.forecast_basis === 'NORMALIZED'){
      const nm = st.norm || {};
      return '<div class="formula-box"><b>正常化EPS = 周期ROE分位(P25/P50/P75) × 最新每股净资产</b></div>'
        + stepsHTML([
          {text:'周期窗口 '+(nm.window||'—')+'（'+(nm.hist_n||'—')+' 个年报，覆盖至少一个完整周期）', src:'数据契约 5.2：跨周期中位法，禁止用峰值/谷底 TTM 冒充'},
          {text:'ROE 分位 = '+(nm.roe_low!=null?nm.roe_low+'% / ':'—')+(nm.roe_mid!=null?nm.roe_mid+'% / ':'—')+(nm.roe_high!=null?nm.roe_high+'%':'—')},
          {text:'最新每股净资产 = '+fmt2(nm.bps)+' 元（'+(nm.bps_as_of||'—')+'）'},
          {text:'计算', eq:'bear '+fmt2(st.eps_bear)+' ｜ base '+fmt2(st.eps_base)+' ｜ bull '+fmt2(st.eps_bull)}], 'D')
        + '<span class="src-badge">D级：中位ROE为工程化假设，周期股盈利预测质量 L/M，恒为参考级</span>';
    }
    return '<div class="formula-box"><b>EPS = 同花顺F10一致预期（引擎选定年度）</b></div>'
      + stepsHTML([
        {text:'年度口径：'+(st.forecast_basis||'FY1')+'（'+(st.forecast_year ? st.forecast_year + 'E' : '—')+'，最近实际年度 '+((st.actual_eps_history||[]).length?Math.max(...st.actual_eps_history.map(x=>x.year)):'—')+'）', src: st.forecast_source || '—'},
        {text:'保守/基准/乐观', eq:'bear '+fmt2(st.eps_bear)+' ｜ base '+fmt2(st.eps_base)+' ｜ bull '+fmt2(st.eps_bull)},
        {text:'统一 T+1/FY1 口径，禁止任意选年度拟合结论（v2 引擎强制）', src:'A级：用未来年份利润定价；D级：FY1口径由引擎强制执行'}], 'A')
      + ntmFormulaHTML(st);
  }
  if(key==='v_low') return '<div class="formula-box"><b>V_low = 保守EPS × 合理PE低档</b></div>'
    + stepsHTML([
      {text:'保守EPS = '+fmt2(st.eps_bear)+' 元/股'},
      {text:'合理PE低档 = '+st.pe_low+'×（'+((st.pe_source||'—'))+'）'},
      {text:'计算', eq:'V_low = '+fmt2(st.eps_bear)+' × '+st.pe_low+' = '+fmt2(st.v_low)+' 元'}], 'A');
  if(key==='v_mid') return '<div class="formula-box"><b>V_mid = 基准EPS × 合理PE中枢</b></div>'
    + stepsHTML([
      {text:'基准EPS = '+fmt2(st.eps_base)+' 元/股'},
      {text:'合理PE中枢 = '+st.pe_mid+'×'},
      {text:'计算', eq:'V_mid = '+fmt2(st.eps_base)+' × '+st.pe_mid+' = '+fmt2(st.v_mid)+' 元'}], 'A');
  if(key==='v_high') return '<div class="formula-box"><b>V_high = 乐观EPS × 合理PE高档</b></div>'
    + stepsHTML([
      {text:'乐观EPS = '+fmt2(st.eps_bull)+' 元/股'},
      {text:'合理PE高档 = '+st.pe_high+'×'},
      {text:'计算', eq:'V_high = '+fmt2(st.eps_bull)+' × '+st.pe_high+' = '+fmt2(st.v_high)+' 元'}], 'A');
  if(key==='mos') return '<div class="formula-box"><b>MOS = 1 − 当前价 ÷ 价值中枢</b></div>'
    + stepsHTML([{text:'当前价 P = '+fmt2(st.price)+'；价值中枢 V_mid = '+fmt2(st.v_mid)},
      {text:'计算安全边际', eq:'MOS = 1 − '+fmt2(st.price)+' ÷ '+fmt2(st.v_mid)+' = '+(st.mos>=0?'+':'')+(st.mos*100).toFixed(1)+'%'}], 'D');
  if(key==='pctile') return '<div class="formula-box"><b>估值带位置 = (当前价 − V_low) ÷ (V_high − V_low)</b></div>'
    + stepsHTML([{text:'P='+fmt2(st.price)+'；V_low='+fmt2(st.v_low)+'；V_high='+fmt2(st.v_high)},
      {text:'带内线性位置（非统计百分位，可小于0或大于100%）', eq:'('+fmt2(st.price)+'−'+fmt2(st.v_low)+')÷('+fmt2(st.v_high)+'−'+fmt2(st.v_low)+') = '+(st.band_pos_raw!=null?fmt2(st.band_pos_raw*100):'—')+'%'}], 'D');
  return '<div class="formula-box">暂无该指标的展开计算。</div>';
}
function openGraham(){
  const m = DATA.market, g = (m.graham_metrics||[]).find(x=>x.key==='cs985') || (m.graham_metrics||[])[0] || {};
  if(!g.graham){ openModal('格雷厄姆指数','<div class="formula-box">大盘数据缺失（联网采集失败）。</div>'); return; }
  const b = m.bond_10y||{};
  const rows = (m.graham_metrics||[]).map(x=>'<div class="step-item"><div class="step-no">•</div><div>'+x.label+'：PE '+x.pe+' → 指数 <b>'+x.graham+'</b>（'+x.band+'）</div></div>').join('');
  openModal('市场估值温度（格雷厄姆指数）',
    '<div class="formula-box"><b>公式：格雷厄姆指数 = (1÷全市场PE) ÷ 十年期国债收益率</b>\n分档：>2.3极低 / 2~2.3偏低 / 1.8~2略偏低 / 1.5~1.8中性 / 1~1.5偏高 / <1极高\n\nv2 定位：仅作市场背景参考，不构成仓位硬闸门。</div>' + rows
    + '<span class="src-badge">A级公式与分档</span><span class="src-badge">D级：中证全指000985双口径</span>');
}

/* ============ K线主画布（估值雷达主图 · 含 sr-layer） ============ */
function renderKline(){
  if(!CUR || VIEW!=='stock') return;
  const st = CUR;
  const wrap = document.getElementById('chartWrap');
  const svg = document.getElementById('mainChart');
  const tip = document.getElementById('chartTip');
  const all = (st.kline||[]).filter(r=>r&&[r.o,r.c,r.h,r.l,r.v].every(v=>Number.isFinite(+v)));
  if(all.length < 2){
    svg.innerHTML = '';
    document.getElementById('chartInfo').textContent = '暂无足够K线数据';
    return;
  }
  let rows = all.slice();
  if(RANGE_STATE.n > 0) rows = rows.slice(-RANGE_STATE.n);
  CHART_ROWS = rows;
  const W = Math.max(420, wrap.clientWidth || 800);
  const H = Math.max(320, wrap.clientHeight || 540);
  const AX = W < 560 ? 58 : 76;          /* 右侧价格轴（12px 标签） */
  const TL = 10;           /* 顶部留白 */
  const BX = 28;           /* 底部时间轴 */
  const volH = H * 0.20;
  const priceH = H - volH - BX - TL;
  const px0 = 8, px1 = W - AX;

  const V = { low: st.v_low, mid: st.v_mid, high: st.v_high };
  const hasV = V.low!=null && V.mid!=null && V.high!=null;
  let lo = Math.min(...rows.map(r=>r.l)), hi = Math.max(...rows.map(r=>r.h));
  const svals = (st.support||[]).map(s=>+s.level).filter(v=>isFinite(v));
  const rvals = (st.resistance||[]).map(r=>+r.level).filter(v=>isFinite(v));
  let pmin = lo, pmax = hi;
  if(hasV){ pmin = Math.min(pmin, V.low); pmax = Math.max(pmax, V.high); }
  if(svals.length) pmin = Math.min(pmin, ...svals);
  if(rvals.length) pmax = Math.max(pmax, ...rvals);
  const pad = (pmax - pmin) * 0.08;
  pmin -= pad; pmax += pad;

  const x = i => rows.length <= 1 ? px0 : px0 + i * (px1 - px0) / (rows.length - 1);
  const y = p => TL + priceH - (p - pmin) / (pmax - pmin) * priceH;
  const cw = Math.max(2, Math.min(4, (px1 - px0) / rows.length * 0.6));
  const vmax = Math.max(...rows.map(r=>r.v)) || 1;
  const vy = v => TL + priceH + 12 + (1 - v / vmax) * (volH - 22);

  let s = '';
  /* 图层1：背景估值色带（低绿/合蓝/高红，v7 透明度） */
  if(hasV){
    const bands = [
      { t:y(pmax), b:y(V.high), c:'rgba(255,59,48,.06)' },
      { t:y(V.high), b:y(V.low), c:'rgba(0,113,227,.04)' },
      { t:y(V.low), b:y(pmin), c:'rgba(48,209,88,.06)' },
    ];
    bands.forEach(bd => {
      const t = Math.min(bd.t, bd.b), h = Math.abs(bd.b - bd.t);
      s += '<rect x="0" y="'+t.toFixed(1)+'" width="'+px1+'" height="'+h.toFixed(1)+'" fill="'+bd.c+'"/>';
    });
  }
  /* 图层2：蜡烛 + 成交量 */
  rows.forEach((r,i) => {
    const up = r.c >= r.o, col = up ? '#d94a47' : '#178a59';
    const cx = x(i);
    s += '<line x1="'+cx.toFixed(1)+'" y1="'+y(r.h).toFixed(1)+'" x2="'+cx.toFixed(1)+'" y2="'+y(r.l).toFixed(1)+'" stroke="'+col+'" stroke-width="1"/>'
       + '<rect x="'+(cx-cw/2).toFixed(1)+'" y="'+y(Math.max(r.o,r.c)).toFixed(1)+'" width="'+cw.toFixed(1)+'" height="'+Math.max(1,Math.abs(y(r.o)-y(r.c))).toFixed(1)+'" fill="'+col+'"/>';
    const vh = Math.max(1.5, r.v / vmax * (volH - 22));
    s += '<rect x="'+(cx-cw/2).toFixed(1)+'" y="'+vy(r.v).toFixed(1)+'" width="'+cw.toFixed(1)+'" height="'+vh.toFixed(1)+'" fill="'+col+'" opacity=".35"/>';
  });
  /* 图层3：均线（1.5px） */
  const maC = {5:'#0071e3', 10:'#5e5ce6', 20:'#b8956a', 60:'#86868b'};
  [5,10,20,60].forEach(win => {
    if(!MA_VIS[win]) return;
    let pts = [];
    for(let i=0;i<rows.length;i++){ const m = maVal(rows,i,win); if(m!=null) pts.push(x(i).toFixed(1)+','+y(m).toFixed(1)); }
    if(pts.length > 1) s += '<polyline points="'+pts.join(' ')+'" fill="none" stroke="'+maC[win]+'" stroke-width="1.5" opacity=".85"/>';
  });
  /* 图层4：估值锚线 V_low绿虚 / V_mid蓝实 / V_high红虚 + 右侧标签 */
  if(hasV){
    const anchors = [
      { v:V.low, c:'#34c759', dash:'6 4', lab:'V_low ¥'+fmt0(V.low) },
      { v:V.mid, c:'#0071e3', dash:'', lab:'V_mid ¥'+fmt0(V.mid) },
      { v:V.high, c:'#ff3b30', dash:'6 4', lab:'V_high ¥'+fmt0(V.high) },
    ];
    anchors.forEach((a, idx) => {
      const yy = y(a.v);
      s += '<line x1="0" y1="'+yy.toFixed(1)+'" x2="'+px1+'" y2="'+yy.toFixed(1)+'" stroke="'+a.c+'" stroke-width="1.3"'+(a.dash?' stroke-dasharray="'+a.dash+'"':'')+' opacity=".9"/>'
         + '<rect x="'+(px1+3)+'" y="'+(yy-11)+'" width="'+(AX-6)+'" height="22" rx="4" fill="#ffffff" fill-opacity=".95"/>'
         + '<text x="'+(px1+7)+'" y="'+(yy+4)+'" font-size="12" font-weight="700" fill="'+a.c+'" font-family="SF Mono,monospace">'+a.lab+'</text>';
      if(!st.decision_usable && idx===0 && W >= 560){
        s += '<rect x="6" y="'+TL+'" width="140" height="22" rx="4" fill="#ffffff" fill-opacity=".94" stroke="rgba(0,0,0,.12)"/>'
           + '<text x="14" y="'+(TL+15)+'" font-size="12" fill="#48484a" font-weight="600">参考区间 · 不可执行</text>';
      }
    });
  }
  /* 图层5：sr-layer —— 支撑/压力虚线 + 左侧底色标签（A级优先、<15px 合并） */
  s += '<g id="sr-layer">';
  const srStyle = '<style>@keyframes srmarch{to{stroke-dashoffset:-28}}.srl{animation:srmarch .6s ease-out}</style>';
  const keep = [];   /* {y, cls, label} 已保留 */
  const drawSR = (arr, isSup) => {
    const sorted = arr.slice().map((sr,i) => ({...sr, i})).sort((a,b)=>b.level-a.level);
    sorted.forEach((sr, idx) => {
      const vv = +sr.level;
      if(!isFinite(vv) || vv < pmin || vv > pmax) return;
      const yy = y(vv);
      const conflict = keep.find(k => Math.abs(k.y - yy) < 15);
      if(conflict){
        const curA = sr.level_ev === 'A';
        if(!conflict.a && curA){ /* 升级：替换 B 为 A */
          conflict.label = conflict.label + '/' + (isSup?'S':'R')+(sr.i+1);
          conflict.a = true;
        } else {
          conflict.label = conflict.label + '/' + (isSup?'S':'R')+(sr.i+1);
        }
        return;
      }
      const isA = sr.level_ev === 'A';
      keep.push({ y: yy, a: isA, label: (isSup?'S':'R')+(sr.i+1) });
      const col = isSup ? '#34c759' : '#ff3b30';
      const colD = isSup ? '#1f9d4d' : '#d70015';
      const lab = (isSup?'S':'R')+(sr.i+1)+' ¥'+fmt0(vv);
      s += '<line class="srl" x1="0" y1="'+yy.toFixed(1)+'" x2="'+px1+'" y2="'+yy.toFixed(1)+'" stroke="'+col+'" stroke-width="1" stroke-dasharray="4 3" opacity="0.6"/>'
         + '<rect x="4" y="'+(yy-11)+'" width="92" height="22" rx="4" fill="'+colD+'"/>'
         + '<text x="10" y="'+(yy+4)+'" font-size="12" font-weight="700" fill="#ffffff" font-family="SF Mono,monospace">'+lab+'</text>';
    });
  };
  drawSR(st.support||[], true);
  drawSR(st.resistance||[], false);
  s += srStyle + '</g>';
  /* 图层6：当前价线（蓝实线，与 S/R 虚线区分） */
  const py = y(rows[rows.length-1].c);
  s += '<line x1="0" y1="'+py.toFixed(1)+'" x2="'+px1+'" y2="'+py.toFixed(1)+'" stroke="#0071e3" stroke-width="1" opacity=".35"/>';
  /* 图层7：Y轴（右5档，12px）与X轴 */
  [0,1,2,3,4].forEach(g => {
    const pv = pmax - (pmax - pmin) * g / 4, gy = TL + priceH * g / 4;
    s += '<text x="'+(px1+7)+'" y="'+(gy+4)+'" font-size="12" fill="#48484a" font-family="SF Mono,monospace">'+fmt2(pv)+'</text>';
  });
  const step = Math.max(1, Math.floor(rows.length / (W < 560 ? 3 : 6)));
  let lastLabelX = -1e9;
  rows.forEach((r,i) => {
    if(i % step !== 0 && i !== rows.length-1) return;
    const lx = x(i);
    if(lx - lastLabelX < 92) return;   /* 防日期标签重叠 */
    lastLabelX = lx;
    s += '<text x="'+lx.toFixed(1)+'" y="'+(TL+priceH+volH+13)+'" font-size="12" fill="#48484a" text-anchor="middle" font-family="SF Mono,monospace">'+String(r.d).slice(2,10)+'</text>';
  });
  /* 图层8：十字光标 */
  s += '<line id="chx" x1="0" y1="0" x2="0" y2="0" stroke="#86868b" stroke-width=".8" stroke-dasharray="4 4" opacity="0"/>'
     + '<line id="chy" x1="0" y1="0" x2="0" y2="0" stroke="#86868b" stroke-width=".8" stroke-dasharray="4 4" opacity="0"/>';

  svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
  svg.innerHTML = s;
  document.getElementById('chartInfo').textContent =
    '数据截止 ' + DATA.data_date + ' · ' + rows.length + ' 根 · 前复权 · 红涨绿跌 · 悬停十字光标 · 点击固定';
  document.getElementById('chartTitle').textContent = st.name + ' · 估值雷达主图（日K）';

  /* 十字光标 + Tooltip（估值状态 + 临近 S/R 提示） */
  const zm = zmeta(st);
  svg.onmousemove = function(e){
    const rect = svg.getBoundingClientRect();
    const px = (e.clientX - rect.left) * (W / rect.width);
    let i = Math.round((px - px0) / ((px1 - px0) / (rows.length - 1)));
    i = Math.max(0, Math.min(rows.length - 1, i));
    const r = rows[i];
    const cx = x(i), cy = y(r.c);
    const chx = document.getElementById('chx'), chy = document.getElementById('chy');
    chx.setAttribute('x1', cx.toFixed(1)); chx.setAttribute('x2', cx.toFixed(1));
    chx.setAttribute('y1', TL); chx.setAttribute('y2', (TL + priceH + volH));
    chx.setAttribute('opacity', '.5');
    chy.setAttribute('x1', 0); chy.setAttribute('x2', px1);
    chy.setAttribute('y1', cy.toFixed(1)); chy.setAttribute('y2', cy.toFixed(1));
    chy.setAttribute('opacity', '.5');
    const volTxt = r.v >= 1e6 ? (r.v/1e8).toFixed(2) + '亿' : (r.v/1e4).toFixed(0) + '万';
    const zoneCol = ['#1f9d4d','#1f9d4d','#a0742f','#a0742f','#d70015','#d70015','#6e6e73'][zm.c] || '#6e6e73';
    let t = '<span class="zone-badge" style="background:rgba(110,110,115,.12);color:'+zoneCol+'">' + (st.decision_usable?zm.label:(st.reference_zone?'参考 '+st.reference_zone:zm.label)) + '</span>\n'
      + '<span class="tk">日期: </span>' + r.d + '\n'
      + '<span class="tk">开盘: </span>' + fmt2(r.o) + '  <span class="tk">最高: </span>' + fmt2(r.h) + '\n'
      + '<span class="tk">收盘: </span>' + fmt2(r.c) + '  <span class="tk">最低: </span>' + fmt2(r.l) + '\n'
      + '<span class="tk">成交量: </span>' + volTxt;
    [5,10,20,60].forEach(win => { const m = maVal(rows,i,win); if(m!=null) t += '\n<span class="tk">MA'+win+': </span>' + fmt2(m); });
    if(hasV){
      t += '\n<span class="tk">距V_low: </span>' + fmt2((r.c/V.low-1)*100) + '%'
         + '  <span class="tk">距V_high: </span>' + fmt2((r.c/V.high-1)*100) + '%';
    }
    /* 临近 S/R（±2%） */
    let near = null;
    (st.support||[]).forEach((sr,idx) => {
      const vv = +sr.level;
      if(isFinite(vv) && Math.abs(r.c/vv - 1) <= 0.02 && (near==null || Math.abs(r.c/vv-1) < Math.abs(r.c/near.v-1))) near = {sr, idx, up:false};
    });
    (st.resistance||[]).forEach((sr,idx) => {
      const vv = +sr.level;
      if(isFinite(vv) && Math.abs(r.c/vv - 1) <= 0.02 && (near==null || Math.abs(r.c/vv-1) < Math.abs(r.c/near.v-1))) near = {sr, idx, up:true};
    });
    if(near){
      t += '\n<span class="'+(near.up?'near-r':'near-s')+'">⚠ '+(near.up?'临近压力':'临近支撑')+' '+(near.up?'R':'S')+(near.idx+1)+' ¥'+fmt0(+near.sr.level)+'（'+fmt2((r.c/+near.sr.level-1)*100)+'%）</span>';
    }
    tip.innerHTML = t;
    tip.classList.add('show');
  };
  svg.onmouseleave = function(){
    if(PIN != null) return;
    document.getElementById('chx').setAttribute('opacity','0');
    document.getElementById('chy').setAttribute('opacity','0');
    tip.classList.remove('show');
  };
  svg.onclick = function(){
    if(PIN != null){ PIN = null; return; }
    PIN = CHART_ROWS.length;
    tip.classList.add('show');
  };
}

/* ============ 初始化 ============ */
function init(){
  grahamPill();
  renderList();
  document.querySelectorAll('.range-btn').forEach(btn => {
    btn.onclick = function(){
      document.querySelectorAll('.range-btn').forEach(b=>b.classList.remove('on'));
      this.classList.add('on');
      RANGE_STATE.n = +this.dataset.n;
      renderKline();
    };
  });
  document.querySelectorAll('.ma-chip').forEach(chip => {
    chip.onclick = function(){
      const m = +this.dataset.ma;
      MA_VIS[m] = !MA_VIS[m];
      this.classList.toggle('off', !MA_VIS[m]);
      this.classList.toggle('on', MA_VIS[m]);
      renderKline();
    };
  });
  let resizeT = null;
  window.addEventListener('resize', () => { clearTimeout(resizeT); resizeT = setTimeout(renderKline, 150); });
  const last = localStorage.getItem('radar_last');
  if(last && DATA.stocks.some(s=>s.ticker===last)) switchStock(last);
  else switchStock(DATA.stocks[0].ticker);
}
init();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    print(build())
