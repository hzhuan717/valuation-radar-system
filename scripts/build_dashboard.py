# -*- coding: utf-8 -*-
"""估值雷达 · 终端仪表盘生成器 v6（K线为主、三栏环绕，单屏全览）

设计规范（2026-08-13 用户确认，终端风格）：
  · 宽屏 ≥1400px：左导航200px + 中央K线主图 + 右数据墙380px，100vh 单屏，页面禁止滚动
  · 笔记本 1100-1399px：左栏80px（Hover名称），K线55%宽，数据墙45%，内部2列微卡
  · 移动端 <1100px：单列滚动，K线固定50vh，卡片2列，总高≤150vh，无Tab切换
  · K线主画布图层（底→顶）：估值色带(低绿/合蓝/高红) → 蜡烛 → 均线(可点击显隐)
    → V_low绿虚/V_mid蓝实/V_high红虚+右侧价格标签 → 支撑S绿实/压力R红实+左侧标签
    → 成交量副图(底部20%) → 十字光标+右侧浮动面板Tooltip(日期/OHLC/量/均线/距V幅度)
  · 数据墙驾驶舱密度：4级字号(Jumbo28/Title11/Data12/Meta10)、6px圆角、1px边框、实色卡片
  · 买卖阶梯横向订单簿；Step6为来源徽章墙；计算器内嵌Card2(折叠展开)
  · 禁止：毛玻璃卡片、跨行复杂Grid、>4级字号、K线固定min-width/min-height、
    纵向长阶梯、大引用块、滚动浮现动画
  · K线蜡烛红涨绿跌（用户指定）；数据/交互逻辑（v2引擎、switchStock、Modal）全部保留
"""
import json
import os

BASE = r"E:\财报解读\watchlist"
STATE = os.path.join(BASE, "state.json")
OUT = os.path.join(BASE, "output", "估值雷达门户.html")


def auto_sr(st: dict) -> tuple:
    v_low, v_high = st.get("v_low"), st.get("v_high")
    k = st.get("kline") or []
    support, resistance = [], []
    if v_low and k:
        support.append({"level": v_low, "method": f"V_low 买入启动区（{v_low}）", "level_ev": "A"})
    if v_high and k:
        resistance.append({"level": v_high, "method": f"V_high 卖出启动区（{v_high}）", "level_ev": "A"})
    if len(k) >= 60:
        lo60 = round(min(r["l"] for r in k[-60:]), 2)
        hi60 = round(max(r["h"] for r in k[-60:]), 2)
        support.append({"level": lo60, "method": "近60日低点", "level_ev": "B"})
        resistance.append({"level": hi60, "method": "近60日高点", "level_ev": "B"})
    if len(k) >= 250:
        lo250 = round(min(r["l"] for r in k[-250:]), 2)
        hi250 = round(max(r["h"] for r in k[-250:]), 2)
        support.append({"level": lo250, "method": "250日低点", "level_ev": "B"})
        resistance.append({"level": hi250, "method": "250日高点", "level_ev": "B"})
    ma20s = [r["c"] for r in k[-20:]] if len(k) >= 20 else []
    ma60s = [r["c"] for r in k[-60:]] if len(k) >= 60 else []
    if ma60s:
        ma60 = sum(ma60s) / 60
        if ma60 < (v_low or 0) * 0.9:
            support.append({"level": round(ma60, 2), "method": "MA60 均线支撑", "level_ev": "B"})
        elif ma60 > (v_high or 1e9) * 1.1:
            resistance.append({"level": round(ma60, 2), "method": "MA60 均线压力", "level_ev": "B"})
    if ma20s:
        ma20 = sum(ma20s) / 20
        if ma20 < (v_low or 0) * 0.9:
            support.append({"level": round(ma20, 2), "method": "MA20 均线支撑", "level_ev": "B"})
        elif ma20 > (v_high or 1e9) * 1.1:
            resistance.append({"level": round(ma20, 2), "method": "MA20 均线压力", "level_ev": "B"})
    return support[:5], resistance[:5]


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
/* ============ Design Tokens（终端密度） ============ */
:root{
  --sans:-apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
  --mono:"SF Mono",SFMono-Regular,ui-monospace,Menlo,Consolas,monospace;
  --bg:#f5f5f7; --bg2:#ffffff; --hair:rgba(0,0,0,.06); --hair2:rgba(0,0,0,.1);
  --ink:#1d1d1f; --sub:#86868b; --sub2:#6e6e73; --meta:#a1a1a6;
  --blue:#0071e3; --blue-lt:rgba(0,113,227,.08);
  --green:#30d158; --green-d:#1f9d4d; --red:#ff3b30; --red-d:#d70015; --gold:#b8956a; --violet:#5e5ce6;
  --candle-up:#d94a47; --candle-dn:#178a59;
  --r-card:6px;
  --shadow-card:0 1px 2px rgba(0,0,0,.04);
  --fs-jumbo:28px; --fs-title:11px; --fs-data:12px; --fs-meta:10px;
}
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%;overflow:hidden}
body{font-family:var(--sans);background:var(--bg);color:var(--ink);font-size:var(--fs-data)}
button{font-family:var(--sans);cursor:pointer}
a{color:var(--blue)}

/* ============ 顶栏 40px ============ */
.topbar{height:40px;display:flex;align-items:center;gap:12px;padding:0 12px;background:var(--bg2);
  border-bottom:1px solid var(--hair);position:relative;z-index:30}
.brand{display:flex;align-items:center;gap:8px;border:none;background:none;font-size:13px;font-weight:600;color:var(--ink);padding:4px 10px;border-radius:4px}
.brand:hover{background:var(--blue-lt);color:var(--blue)}
.brand i{width:14px;height:14px;border-radius:4px;background:var(--blue);display:inline-block}
.stock-trig{display:flex;align-items:center;gap:10px;border:1px solid var(--hair);background:var(--bg2);
  border-radius:var(--r-card);padding:5px 12px;font-size:12.5px;min-width:230px;max-width:320px}
.stock-trig:hover{border-color:var(--blue)}
.stock-trig span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.stock-trig .arr{margin-left:auto;color:var(--sub)}
.top-gate{margin-left:auto;display:flex;align-items:center;gap:6px;font-size:11px;color:var(--sub2)}
.top-gate .dot{width:7px;height:7px;border-radius:50%;flex:none}
.dot-ok{background:var(--green)}.dot-warn{background:var(--gold)}.dot-bad{background:var(--red)}
.top-upd{font-size:var(--fs-meta);color:var(--meta)}

/* ============ 弹出选股器 ============ */
.popover{position:absolute;top:46px;left:10px;width:420px;background:var(--bg2);border:1px solid var(--hair);
  border-radius:10px;box-shadow:0 12px 40px rgba(0,0,0,.12);display:none;z-index:50;padding:8px}
.popover.on{display:block}
.pop-search{width:100%;border:1px solid var(--hair);border-radius:6px;padding:7px 10px;font-size:12.5px;margin-bottom:6px}
.pop-list{max-height:420px;overflow-y:auto}
.pop-item{display:flex;align-items:center;gap:10px;width:100%;text-align:left;border:none;background:none;
  padding:8px 10px;border-radius:6px;font-size:12.5px}
.pop-item:hover{background:var(--blue-lt)}
.pop-item .nm{font-weight:600}
.pop-item .cd{color:var(--meta);font-family:var(--mono)}
.pop-item .st{margin-left:auto;font-size:11px}

/* ============ 主体三栏 Grid（100vh 单屏） ============ */
.shell{display:grid;grid-template-columns:200px minmax(0,1fr) 380px;grid-template-rows:minmax(0,1fr);
  height:calc(100vh - 40px);overflow:hidden}

/* ---- 左导航 200px ---- */
.sidebar{border-right:1px solid var(--hair);background:var(--bg2);display:flex;flex-direction:column;min-height:0;min-width:0}
.sb-hd{display:flex;justify-content:space-between;align-items:baseline;padding:10px 12px 6px;
  font-size:var(--fs-title);font-weight:600;letter-spacing:.05em;color:var(--sub);text-transform:uppercase}
.sb-search{margin:0 10px 8px;border:1px solid var(--hair);border-radius:6px;padding:6px 10px;font-size:12px}
.sb-list{flex:1;overflow-y:auto;min-height:0}
.sb-item{display:block;width:100%;text-align:left;border:none;background:none;padding:7px 12px;
  border-bottom:1px solid var(--hair);font-size:12.5px;position:relative}
.sb-item:hover{background:var(--blue-lt)}
.sb-item.on{background:var(--blue-lt);box-shadow:inset 3px 0 0 var(--blue)}
.sb-item .nm{font-weight:600}
.sb-item .cd{color:var(--meta);font-family:var(--mono);font-size:11px;margin-left:4px}
.sb-item .px{margin-left:auto;font-family:var(--mono);font-weight:600}
.sb-item .chg{font-size:11px;font-family:var(--mono)}
.sb-item .l1{display:flex;align-items:baseline;gap:6px;min-width:0}
.sb-item .code{display:none}
.sb-item .bar{position:absolute;left:12px;right:12px;bottom:0;height:3px;border-radius:2px;overflow:hidden;background:#eee}
.sb-item .bar i{display:block;height:100%;background:var(--blue)}
.up-c{color:var(--candle-up)}.dn-c{color:var(--candle-dn)}
.sb-zone{font-size:10.5px;margin-left:auto;color:var(--sub2)}
.sb-zone.z0,.sb-zone.z1{color:var(--green-d)}.sb-zone.z4,.sb-zone.z5{color:var(--red-d)}.sb-zone.z2,.sb-zone.z3{color:var(--gold)}

/* ---- 中央区 ---- */
.center{display:flex;flex-direction:column;min-width:0;min-height:0;background:var(--bg)}
.hero-strip{display:flex;align-items:center;gap:18px;padding:8px 14px;background:var(--bg2);
  border-bottom:1px solid var(--hair);flex-wrap:wrap}
.hero-strip .hl{min-width:0;flex:1}
.hero-strip .eyebrow{font-size:10px;letter-spacing:.06em;color:var(--sub2);text-transform:uppercase}
.hero-strip h1{font-size:22px;font-weight:700;letter-spacing:-.02em;line-height:1.2}
.hero-strip .tick{font-size:11.5px;color:var(--sub);font-family:var(--mono)}
.hero-strip .pills{display:flex;gap:6px;flex-wrap:wrap;margin-top:3px}
.pill{display:inline-flex;align-items:center;gap:6px;border-radius:999px;padding:3px 10px;font-size:11px;
  border:1px solid var(--hair);background:var(--bg2)}
.pill .dot{width:6px;height:6px;border-radius:50%}
.hero-strip .hr{margin-left:auto;text-align:right;min-width:230px}
.hero-strip .price{font-size:var(--fs-jumbo);font-weight:600;font-family:var(--mono);font-variant-numeric:tabular-nums}
.hero-strip .pct{font-size:13px;font-family:var(--mono)}
.hero-strip .mos-wrap{margin-top:4px}
.mos-bar{display:flex;height:6px;border-radius:3px;overflow:hidden;background:#eee}
.mos-bar i{display:block;height:100%}
.mos-marker{position:relative;height:0}
.mos-dot{position:absolute;top:-8px;width:9px;height:9px;border-radius:50%;background:var(--blue);
  border:2px solid #fff;transform:translateX(-50%);box-shadow:0 0 0 1px var(--hair2)}
.mos-txt{font-size:10px;color:var(--sub2);margin-top:7px}

/* ---- K线主画布 ---- */
.chart-zone{flex:1;display:flex;flex-direction:column;min-height:0;padding:8px 10px 6px}
.chart-toolbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:6px}
.chart-toolbar h3{font-size:13px;font-weight:600}
.chart-toolbar .info{font-size:var(--fs-meta);color:var(--meta)}
.range-btns{display:flex;gap:4px}
.range-btn{font-size:10px;padding:3px 9px;border-radius:999px;border:1px solid var(--hair);
  background:var(--bg2);color:var(--sub2)}
.range-btn:hover{border-color:var(--blue);color:var(--blue)}
.range-btn.on{background:var(--blue);border-color:var(--blue);color:#fff;font-weight:600}
.ma-legend{margin-left:auto;display:flex;gap:6px}
.ma-chip{display:inline-flex;align-items:center;gap:4px;font-size:10px;border:1px solid var(--hair);
  border-radius:999px;padding:2px 8px;background:var(--bg2);color:var(--sub2)}
.ma-chip i{width:8px;height:2px;display:inline-block;border-radius:1px}
.ma-chip.off{opacity:.35;text-decoration:line-through}
.chart-wrap{flex:1;position:relative;min-height:0;border:1px solid var(--hair);border-radius:var(--r-card);
  background:var(--bg2);overflow:hidden}
.chart-wrap svg{display:block;width:100%;height:100%}
.chart-foot{display:flex;gap:14px;font-size:var(--fs-meta);color:var(--meta);padding:4px 2px 0;flex-wrap:wrap}
.legend-mini{display:inline-flex;align-items:center;gap:4px}
.legend-mini i{width:9px;height:3px;border-radius:2px;display:inline-block}
.ktip{position:absolute;top:8px;right:8px;background:rgba(255,255,255,.96);border:1px solid var(--hair2);
  border-radius:8px;padding:8px 12px;font-family:var(--mono);font-size:11px;line-height:1.7;color:var(--ink);
  box-shadow:0 4px 16px rgba(0,0,0,.08);pointer-events:none;opacity:0;min-width:176px;z-index:6;
  font-variant-numeric:tabular-nums;white-space:pre}
.ktip.show{opacity:1}
.ktip .tk{color:var(--sub2)}
.ov-wrap{flex:1;overflow-y:auto;min-height:0;padding:12px}
.ov-table{width:100%;border-collapse:collapse;font-size:12.5px;background:var(--bg2);
  border:1px solid var(--hair);border-radius:var(--r-card)}
.ov-table th{text-align:left;padding:7px 10px;font-size:10px;letter-spacing:.05em;text-transform:uppercase;
  color:var(--sub);border-bottom:1px solid var(--hair)}
.ov-table td{padding:7px 10px;border-bottom:1px solid var(--hair);font-family:var(--mono)}
.ov-table tr{cursor:pointer}
.ov-table tr:hover{background:var(--blue-lt)}

/* ---- 右数据墙 380px ---- */
.wall{background:var(--bg);border-left:1px solid var(--hair);overflow-y:auto;padding:8px;min-height:0}
.w-card{background:var(--bg2);border:1px solid var(--hair);border-radius:var(--r-card);
  padding:12px;margin-bottom:8px;box-shadow:var(--shadow-card)}
.w-title{font-size:var(--fs-title);font-weight:600;letter-spacing:.05em;text-transform:uppercase;
  color:var(--sub);margin-bottom:8px;display:flex;align-items:center;gap:6px}
.w-title .sp{margin-left:auto;font-size:10px;color:var(--meta);text-transform:none;letter-spacing:0}
.jumbo{font-size:var(--fs-jumbo);font-weight:600;font-family:var(--mono);font-variant-numeric:tabular-nums;line-height:1.1}
.jumbo.green{color:var(--green-d)}.jumbo.blue{color:var(--blue)}.jumbo.red{color:var(--red-d)}
.micro-row{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;border-top:1px solid var(--hair);padding-top:8px}
.micro{min-width:0}
.micro .k{font-size:var(--fs-title);color:var(--sub);letter-spacing:.04em;text-transform:uppercase}
.micro .v{font-size:14px;font-weight:600;font-family:var(--mono);font-variant-numeric:tabular-nums;margin-top:2px}
.micro .m{font-size:var(--fs-meta);color:var(--meta);margin-top:1px}
.tri-v{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:8px}
.tri-v .cell .k{font-size:var(--fs-title);color:var(--sub);letter-spacing:.04em;text-transform:uppercase;margin-bottom:2px}
.band-track{position:relative;height:8px;border-radius:4px;overflow:visible;background:linear-gradient(90deg,
  rgba(48,209,88,.55) 0 25%, rgba(0,113,227,.45) 25% 75%, rgba(255,59,48,.55) 75% 100%)}
.band-track .dot{position:absolute;top:-3px;width:14px;height:14px;border-radius:50%;background:#fff;
  border:3px solid var(--blue);transform:translateX(-50%);box-shadow:0 0 0 1px var(--hair2)}
.band-labels{display:flex;justify-content:space-between;font-size:var(--fs-meta);color:var(--meta);margin-top:3px}
.formula-mini{font-size:var(--fs-meta);color:var(--sub2);margin-top:8px;border-top:1px solid var(--hair);padding-top:6px;line-height:1.6}
.calc-toggle{width:100%;display:flex;justify-content:space-between;align-items:center;border:none;background:none;
  font-size:var(--fs-title);font-weight:600;letter-spacing:.04em;color:var(--sub);padding:6px 0 0;
  border-top:1px solid var(--hair);margin-top:6px;text-transform:uppercase}
.calc-body{display:none;padding-top:8px}
.calc-card.open .calc-body{display:block}
.calc-body .row{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:6px}
.calc-body label{font-size:var(--fs-meta);color:var(--sub2);display:block;margin-bottom:2px}
.calc-body input{width:100%;border:1px solid var(--hair);border-radius:4px;padding:4px 6px;font-size:12px;
  font-family:var(--mono)}
.calc-out{font-size:12px;line-height:1.8;font-family:var(--mono);border-top:1px solid var(--hair);padding-top:6px}
/* 订单簿阶梯 */
.book{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.book .side .hd{font-size:var(--fs-title);font-weight:600;letter-spacing:.04em;text-transform:uppercase;margin-bottom:4px}
.book .side.b .hd{color:var(--green-d)}.book .side.s .hd{color:var(--red-d)}
.book .lvl{display:flex;justify-content:space-between;font-family:var(--mono);font-size:12px;padding:4px 0;
  border-bottom:1px solid var(--hair)}
.book .lvl:last-child{border-bottom:none}
.book .lvl .lab{font-family:var(--sans);color:var(--sub2);font-size:11px}
.sr-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.sr-grid .cell{font-family:var(--mono);font-size:12px;border-top:1px solid var(--hair);padding-top:6px}
.sr-grid .cell .lv{font-weight:600}
.sr-grid .cell .mt{font-family:var(--sans);font-size:var(--fs-meta);color:var(--sub2);margin-top:2px}
.sr-grid .cell.s .lv{color:var(--green-d)}
.sr-grid .cell.r .lv{color:var(--red-d)}
.trigger-line{font-size:var(--fs-meta);color:var(--sub2);margin-top:8px;border-top:1px solid var(--hair);padding-top:6px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pos-bar{display:flex;height:14px;border-radius:3px;overflow:hidden}
.pos-bar i{display:block;height:100%}
.pos-legend{display:flex;gap:10px;flex-wrap:wrap;font-size:var(--fs-meta);color:var(--sub2);margin-top:6px}
.pos-legend b{font-family:var(--mono);font-weight:600;color:var(--ink)}
.badge-wall{display:flex;flex-wrap:wrap;gap:6px}
.badge{display:inline-flex;align-items:center;gap:5px;font-size:10px;border:1px solid var(--hair);
  border-radius:999px;padding:2px 8px;background:var(--bg2);color:var(--sub2);cursor:default}
.badge b{color:var(--ink);font-weight:600}
.badge .g{font-weight:700}
.badge .gA{color:var(--blue)}.badge .gB{color:var(--green-d)}.badge .gC{color:var(--gold)}.badge .gD{color:var(--sub2)}
.warn-line{font-size:11px;color:var(--gold);line-height:1.5;margin-top:6px}
.blocker-line{font-size:11px;color:var(--red-d);line-height:1.5;margin-top:6px}

/* ---- Modal ---- */
.mask{position:fixed;inset:0;background:rgba(0,0,0,.25);display:none;z-index:100;align-items:center;justify-content:center}
.mask.on{display:flex}
.modal{background:var(--bg2);border-radius:12px;width:min(620px,92vw);max-height:80vh;display:flex;flex-direction:column;
  box-shadow:0 20px 60px rgba(0,0,0,.18)}
.modal-hd{display:flex;justify-content:space-between;align-items:center;padding:14px 18px;border-bottom:1px solid var(--hair)}
.modal-hd h3{font-size:15px;font-weight:600}
.modal-hd .close{border:none;background:none;font-size:15px;color:var(--sub2)}
.modal-bd{padding:14px 18px;overflow-y:auto;font-size:13px;line-height:1.7}
.formula-box{background:var(--bg);border:1px solid var(--hair);border-radius:8px;padding:10px 12px;
  margin-bottom:10px;font-size:12.5px;white-space:pre-wrap}
.step-item{display:flex;gap:10px;padding:6px 0;border-bottom:1px solid var(--hair);font-size:12.5px}
.step-item:last-child{border-bottom:none}
.step-item .step-no{color:var(--sub2);font-family:var(--mono)}
.eq{font-family:var(--mono);color:var(--blue);display:block;margin-top:3px}
.src{font-size:var(--fs-meta);color:var(--meta);display:block;margin-top:2px}
.src-badge{display:inline-block;font-size:10px;border:1px solid var(--hair);border-radius:999px;
  padding:1px 8px;color:var(--sub2);margin:4px 4px 0 0}

/* ============ 响应式 ============ */
@media(max-width:1399px){
  .shell{grid-template-columns:80px minmax(0,1fr) 320px}
  .sb-hd span:last-child,.sb-search{display:none}
  .sb-item .nm,.sb-item .cd,.sb-item .px{display:none}
  .sb-item{padding:10px 4px;text-align:center}
  .sb-item .l1{flex-direction:column;gap:2px;align-items:center}
  .sb-item .code{display:block;font-family:var(--mono);font-size:11px}
  .sb-item .bar{left:6px;right:6px}
}
@media(max-width:1099px){
  html,body{overflow:auto}
  .shell{grid-template-columns:1fr;grid-template-rows:auto;height:auto;display:block}
  .sidebar{border-right:none;border-bottom:1px solid var(--hair)}
  .sb-list{display:flex;overflow-x:auto;flex:none}
  .sb-item{min-width:110px;border-right:1px solid var(--hair);border-bottom:none}
  .center{min-height:0}
  .chart-zone{height:50vh;position:sticky;top:0;z-index:10;background:var(--bg2);border-bottom:1px solid var(--hair)}
  .hero-strip .hr{margin-left:0}
  .wall{max-height:none;overflow:visible;display:grid;grid-template-columns:1fr 1fr;gap:8px}
  .w-card{margin-bottom:0}
  .popover{left:6px;right:6px;width:auto}
}
@media(max-width:640px){
  .wall{grid-template-columns:1fr}
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
    <input class="pop-search" id="popSearch" placeholder="搜索代码 / 名称…（Ctrl+K）" oninput="filterPop(this.value)">
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
          <div class="mos-bar">
            <i style="width:25%;background:rgba(48,209,88,.55)"></i>
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
        <h3 id="chartTitle">估值决策主图 · 日K</h3>
        <span class="info" id="chartInfo">—</span>
        <div class="range-btns" id="rangeBtns">
          <button class="range-btn" data-n="60">60日</button>
          <button class="range-btn" data-n="120">120日</button>
          <button class="range-btn on" data-n="250">250日</button>
          <button class="range-btn" data-n="0">全部</button>
        </div>
        <div class="ma-legend" id="maLegend">
          <button class="ma-chip" data-ma="5"><i style="background:#0071e3"></i>MA5</button>
          <button class="ma-chip" data-ma="10"><i style="background:#5e5ce6"></i>MA10</button>
          <button class="ma-chip" data-ma="20"><i style="background:#b8956a"></i>MA20</button>
          <button class="ma-chip" data-ma="60"><i style="background:#86868b"></i>MA60</button>
        </div>
      </div>
      <div class="chart-wrap" id="chartWrap">
        <svg id="mainChart" role="img" aria-label="K线估值主图"></svg>
        <div class="ktip" id="chartTip"></div>
      </div>
      <div class="chart-foot">
        <span class="legend-mini"><i style="background:rgba(48,209,88,.4)"></i>低估区</span>
        <span class="legend-mini"><i style="background:rgba(0,113,227,.35)"></i>合理区</span>
        <span class="legend-mini"><i style="background:rgba(255,59,48,.4)"></i>高估区</span>
        <span class="legend-mini"><i style="background:var(--candle-up)"></i>上涨</span>
        <span class="legend-mini"><i style="background:var(--candle-dn)"></i>下跌</span>
      </div>
    </div>

    <div class="ov-wrap" id="ovWrap" style="display:none">
      <table class="ov-table" id="ovTable"></table>
    </div>
  </main>

  <aside class="wall" id="wall">
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
    <div class="modal-hd"><h3 id="m-title">计算过程</h3><button class="close" onclick="closeModal()">✕</button></div>
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

/* ============ 工具 ============ */
const fmt2 = v => v==null ? '—' : (+v).toLocaleString('zh-CN',{maximumFractionDigits:2});
const fmt0 = v => v==null ? '—' : (+v).toLocaleString('zh-CN',{maximumFractionDigits:0});
const pctCol = p => p > 0 ? 'up-c' : (p < 0 ? 'dn-c' : '');
const phDetail = ph => ph && ph.ok ? ((ph.metric||'PE') + ' ' + (ph.pe!=null?fmt2(ph.pe):'—') + (ph.pe_min!=null?' · 5年区间 '+fmt2(ph.pe_min)+'~'+fmt2(ph.pe_max):'') + (ph.source?' · '+ph.source:'')) : '—';
function maVal(rows, i, win){ if(i < win-1) return null; let s=0; for(let j=i-win+1;j<=i;j++) s+=rows[j].c; return s/win; }
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

/* ============ 左导航列表 ============ */
function renderList(filter){
  const el = document.getElementById('sbList');
  const q = (filter||'').trim().toLowerCase();
  el.innerHTML = DATA.stocks.filter(s => !q || s.name.toLowerCase().includes(q) || s.ticker.includes(q))
    .map(s => {
      const zm = zmeta(s);
      const zc = ['z0','z0','z2','z2','z4','z4','z6'][zm.c] || 'z6';
      return '<button class="sb-item '+(s.ticker===CUR?.ticker&&VIEW==='stock'?'on':'')+'" onclick="switchStock(\''+s.ticker+'\')">'
        + '<div class="l1"><span class="nm">'+s.name+'</span><span class="cd">'+s.ticker+'</span>'
        + '<span class="px">¥'+fmt2(s.price)+'</span>'
        + '<span class="chg '+pctCol(s.pct)+'">'+(s.pct>0?'+':'')+fmt2(s.pct)+'%</span></div>'
        + '<div class="l1"><span class="code">'+s.ticker+'</span>'
        + '<span class="sb-zone '+zc+'">'+zm.label+'</span></div>'
        + '<div class="bar"><i style="width:'+Math.round((s.pctile!=null?s.pctile:0.5)*100)+'%"></i></div>'
        + '</button>';
    }).join('');
  document.getElementById('sbCnt').textContent = DATA.stocks.length + ' 只';
}
function filterList(v){ renderList(v); }

/* ============ 弹出选股器 ============ */
function togglePop(){ const p = document.getElementById('popover'); p.classList.toggle('on'); if(p.classList.contains('on')) renderPop(); }
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
}
function filterPop(v){ renderPop(v); }
document.addEventListener('keydown', e => {
  if((e.ctrlKey||e.metaKey) && e.key.toLowerCase()==='k'){ e.preventDefault(); togglePop(); }
  if(e.key==='Escape'){ document.getElementById('popover').classList.remove('on'); closeModal(); }
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
        + '<td>'+s.name+'<br><span style="color:var(--meta);font-size:10px">'+s.ticker+'</span></td>'
        + '<td>'+fmt2(s.price)+'</td><td>'+zm.label+'</td><td>'+g+'</td>'
        + '<td>'+(s.v_low!=null?fmt2(s.v_low)+' ~ '+fmt2(s.v_high):'—')+'</td><td>'+sig+'</td></tr>'; }).join('');
  renderList();
  const w = document.getElementById('wall');
  w.innerHTML = '<div class="w-card"><div class="w-title">市场估值环境（格雷厄姆指数 · 仅背景）</div>'
    + (DATA.market.graham_metrics||[]).map(x=>'<div class="micro-row" style="border-top:none;padding-top:0;margin-bottom:6px">'
      + '<div class="micro"><div class="k">'+x.label+'</div><div class="v">'+x.pe+'</div><div class="m">PE</div></div>'
      + '<div class="micro"><div class="k">格雷厄姆</div><div class="v">'+x.graham+'</div><div class="m">'+x.band+'</div></div>'
      + '<div class="micro"><div class="k">公式</div><div class="v" style="font-size:11px">(1/PE)÷10Y国债</div><div class="m">'+fmt2(((DATA.market.bond_10y||{}).value||0)*100)+'%</div></div>'
      + '</div>').join('')
    + '<div class="formula-mini">v2 定位：仅市场背景参考，不构成仓位硬闸门；不生成个股动作、清仓命令或总仓上限。</div></div>';
}

/* ============ 切换股票 ============ */
function switchStock(ticker){
  const st = DATA.stocks.find(s=>s.ticker===ticker);
  if(!st) return;
  CUR = st; VIEW = 'stock'; PIN = null;
  localStorage.setItem('valuation-radar_last', ticker);
  document.getElementById('chartZone').style.display = '';
  document.getElementById('ovWrap').style.display = 'none';
  document.getElementById('trigName').textContent = st.name + ' ' + st.ticker;
  renderList();
  renderHero(st);
  renderWall(st);
  renderKline();
}

/* ============ Hero 条 ============ */
function renderHero(st){
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
  document.getElementById('hPrice').textContent = '¥' + fmt2(st.price);
  document.getElementById('hPrice').style.color = pcol;
  document.getElementById('hPct').textContent = (st.pct>0?'+':'') + fmt2(st.pct) + '%';
  document.getElementById('hPct').style.color = pcol;
  const dot = document.getElementById('mosDot');
  if(st.v_low!=null && st.v_high!=null && st.v_low<st.v_high){
    const raw = (st.price-st.v_low)/(st.v_high-st.v_low);
    dot.style.left = Math.max(0,Math.min(100,raw*100)) + '%';
    dot.style.display = '';
    document.getElementById('mosTxt').textContent =
      '估值带 V_low ¥'+fmt2(st.v_low)+' / V_mid ¥'+fmt2(st.v_mid)+' / V_high ¥'+fmt2(st.v_high) +
      (st.decision_usable ? '' : '（参考级）');
  } else {
    dot.style.display = 'none';
    document.getElementById('mosTxt').textContent = '无估值区间（路由拦截/观察）';
  }
}

/* ============ 数据墙 ============ */
function renderWall(st){
  const model = st.valuation_model || {};
  const isBank = model.code==='bank_pb_roe', isInfra = model.code==='infrastructure_cashflow';
  const isIns = model.code==='insurance_pev', isNorm = st.forecast_basis==='NORMALIZED';

  /* Card 1 市场与模型 */
  const g = (DATA.market.graham_metrics||[]).find(x=>x.key==='cs985') || (DATA.market.graham_metrics||[])[0] || {};
  const grade = (st.data_quality||{}).grade || '—';
  const gCol = g.graham>=2.3?'var(--green-d)':(g.graham>=1.8?'var(--gold)':'var(--red-d)');
  document.getElementById('c1Body').innerHTML =
    '<div class="micro-row" style="border-top:none;padding-top:0">'
    + '<div class="micro"><div class="k">格雷厄姆指数</div><div class="v">'+(g.graham||'—')+'</div>'
    + '<div class="m" style="color:'+gCol+'">'+(g.band||'—')+((DATA.market.cs985||{}).stale?' · 滞后':'')+'</div></div>'
    + '<div class="micro"><div class="k">估值模型</div><div class="v" style="font-size:13px">'+(model.code||'—')+'</div>'
    + '<div class="m" style="cursor:pointer" onclick="openModal(\'质量门检查\', detailBody(CUR,\'quality\'))">'+((model.label||'').split('·')[0]||'')+'</div></div>'
    + '<div class="micro"><div class="k">数据质量</div><div class="v" style="color:'+(grade==='B'?'var(--green-d)':(grade==='C'?'var(--gold)':'var(--red-d)'))+'">'+grade+'</div>'
    + '<div class="m" style="cursor:pointer" onclick="openModal(\'质量门检查\', detailBody(CUR,\'quality\'))">查看检查项</div></div>'
    + '</div>';

  /* Card 2 三档估值 */
  let c2 = '', c2src = '';
  const usable = st.decision_usable;
  if(st.decision_status==='blocked'){
    const ph = (DATA.pe_history||{})[st.ticker];
    c2 = '<div class="blocker-line">' + ((st._blockers||[])[0]||'路由拦截：模型输入不完整') + '</div>'
      + (ph && ph.ok ? '<div class="micro-row">'
        + '<div class="micro"><div class="k">PE/PB 历史分位</div><div class="v">'+(ph.pctile!=null?Math.round(ph.pctile*100)+'%':'—')+'</div><div class="m">'+phDetail(ph)+'</div></div>'
        + '<div class="micro"><div class="k">分位判断</div><div class="v" style="font-size:13px">'+(ph.signal||'—')+'</div><div class="m">'+(ph.note||'')+'</div></div>'
        + '<div class="micro"><div class="k">TTM PE/PB</div><div class="v">'+fmt2(st.pe_ttm)+'/'+fmt2(st.pb)+'</div><div class="m">行情源</div></div>'
        + '</div>' : '');
  } else {
    let k1='EPS', k2='PE档';
    if(isIns){ k1='每股EV'; k2='P/EV档'; }
    else if(isBank||isInfra){ k1='BVPS'; k2='PB分位'; }
    else if(isNorm){ k1='正常化EPS'; k2='PE档'; }
    const v1 = isIns?fmt2(st.ev_per_share):(isBank||isInfra?fmt2(st.bvps):fmt2(st.eps_base));
    const v2 = isIns?st.pev_low+'/'+st.pev_mid+'/'+st.pev_high:(isBank||isInfra?st.pb_low+'/'+st.pb_mid+'/'+st.pb_high:st.pe_low+'/'+st.pe_mid+'/'+st.pe_high);
    c2 =
      '<div class="tri-v">'
      + '<div class="cell"><div class="k">'+(usable?'V_low 买入启动':'V_low 保守')+'</div><div class="jumbo green">¥'+fmt2(st.v_low)+'</div></div>'
      + '<div class="cell"><div class="k">'+(usable?'V_mid 价值中枢':'V_mid 基准')+'</div><div class="jumbo blue">¥'+fmt2(st.v_mid)+'</div></div>'
      + '<div class="cell"><div class="k">'+(usable?'V_high 卖出启动':'V_high 乐观')+'</div><div class="jumbo red">¥'+fmt2(st.v_high)+'</div></div>'
      + '</div>'
      + '<div class="band-track"><div class="dot" style="left:'+(st.v_low!=null&&st.v_high!=null&&st.v_high>st.v_low?Math.max(0,Math.min(100,(st.price-st.v_low)/(st.v_high-st.v_low)*100)):50)+'%"></div></div>'
      + '<div class="band-labels"><span>低估 ¥'+fmt2(st.v_low)+'</span><span>现价 ¥'+fmt2(st.price)+'</span><span>高估 ¥'+fmt2(st.v_high)+'</span></div>'
      + '<div class="formula-mini">'+k1+' '+v1+' × '+k2+' '+v2+' → V_low/V_mid/V_high'
      + (isNorm?'（周期ROE分位 '+(st.norm||{}).roe_low+'/'+(st.norm||{}).roe_mid+'/'+(st.norm||{}).roe_high+'% × BPS '+fmt2((st.norm||{}).bps)+'）':'')
      + (isBank&&st.diagnostics?'｜ PB-ROE理论中枢 '+st.diagnostics.pb_theo_mid+'×（Ke '+(st.diagnostics.ke*100).toFixed(0)+'%/g '+(st.diagnostics.g*100).toFixed(0)+'%，D级）':'')
      + (isInfra&&st.diagnostics?'｜ OCF '+st.diagnostics.ocf_latest+' · 应收'+st.diagnostics.ar_days_latest+'天 · 负债'+st.diagnostics.debt_latest+'%':'')
      + '</div>'
      + (!usable?'<div class="warn-line">质量门未通过：参考级区间，不构成买卖动作。</div>':'');
    c2src = st.forecast_source || st.pb_source || st.pe_source || '';
  }
  /* 内嵌计算器（仅 decision_usable 稳定PE路由） */
  if(usable && !isIns && !isBank && !isInfra && !isNorm){
    c2 += '<div class="calc-card" id="calcCard"><button class="calc-toggle" onclick="this.parentElement.classList.toggle(\'open\')"><span>估值计算器</span><span>▾</span></button>'
      + '<div class="calc-body"><div class="row">'
      + '<div><label>现价 P</label><input id="i-price" type="number" step="0.01" value="'+st.price+'"></div>'
      + '<div><label>PE低/中/高</label><div style="display:flex;gap:4px"><input id="i-peL" type="number" step="0.5" value="'+st.pe_low+'"><input id="i-peM" type="number" step="0.5" value="'+st.pe_mid+'"><input id="i-peH" type="number" step="0.5" value="'+st.pe_high+'"></div></div>'
      + '<div><label>EPS保守/基准/乐观</label><div style="display:flex;gap:4px"><input id="i-epsB" type="number" step="0.01" value="'+st.eps_bear+'"><input id="i-epsM" type="number" step="0.01" value="'+st.eps_base+'"><input id="i-epsU" type="number" step="0.01" value="'+st.eps_bull+'"></div></div>'
      + '</div><div class="calc-out" id="calcOut">—</div></div></div>';
  }
  document.getElementById('c2Body').innerHTML = c2 || '<div class="formula-box">无数据</div>';
  document.getElementById('c2Src').textContent = c2src ? c2src.slice(0,26) : '';
  bindCalc();

  /* Card 3 买卖阶梯（订单簿） */
  const b1=st.v_low!=null?st.v_low*.7:null, b2=st.v_low!=null?st.v_low*.85:null;
  const s2=st.v_high!=null&&st.v_mid!=null?st.v_high+(st.v_high-st.v_mid)*.5:null, s3=st.v_high!=null?st.v_high*1.3:null;
  document.getElementById('c3Body').innerHTML =
    usable && st.v_low!=null && st.v_high!=null ?
      '<div class="book">'
      + '<div class="side b"><div class="hd">买入金字塔</div>'
      + '<div class="lvl"><span class="lab">深估 V×0.7</span><span>¥'+fmt2(b1)+'</span></div>'
      + '<div class="lvl"><span class="lab">2档 V×0.85</span><span>¥'+fmt2(b2)+'</span></div>'
      + '<div class="lvl"><span class="lab">3档 V_low</span><span>¥'+fmt2(st.v_low)+'</span></div></div>'
      + '<div class="side s"><div class="hd">卖出金字塔</div>'
      + '<div class="lvl"><span class="lab">1档 V_high</span><span>¥'+fmt2(st.v_high)+'</span></div>'
      + '<div class="lvl"><span class="lab">2档 V+0.5Δ</span><span>¥'+fmt2(s2)+'</span></div>'
      + '<div class="lvl"><span class="lab">3档 V×1.3</span><span>¥'+fmt2(s3)+'</span></div></div>'
      + '</div>' :
    (st.v_low!=null && st.v_high!=null ?
      '<div class="warn-line">参考区间 ¥'+fmt2(st.v_low)+' ~ ¥'+fmt2(st.v_high)+'（不可执行）：质量门未通过，不生成买卖阶梯。</div>' :
      '<div class="warn-line">质量门拦截 / 观察路由：补齐输入后由引擎自动恢复。</div>');

  /* Card 4 技术择时 */
  const srs = st.support||[], rrs = st.resistance||[];
  const srCell = (arr, cls, pre) => arr.slice(0,2).map((x,i)=>
    '<div class="cell '+cls+'"><div class="lv">'+pre+(i+1)+' ¥'+fmt2(x.level)+'</div><div class="mt">'+(x.method||'')+' '+(x.level_ev||'B')+'级</div></div>').join('')
    || '<div class="cell"><div class="lv">—</div><div class="mt">暂无</div></div>';
  document.getElementById('c4Body').innerHTML =
    '<div class="sr-grid">'
    + srCell(srs,'s','S') + srCell(rrs,'r','R')
    + '</div>'
    + '<div class="trigger-line" title="均线延长线/十周线=买点测试 · 强势股首阴回踩10均=短线买点 · 缺口不破是支撑、破则转弱 · 摸线30→60→90→120 · 黄金分割0.382/0.5/0.618">触发规则：均线延长线 · 首阴切十均 · 缺口 · 摸线 · 黄金分割（A级）</div>';

  /* Card 5 仓位 */
  const tpl = {底仓:.55, 活动仓:.25, 短线:.10, 现金:.10};
  let plan = {...tpl};
  if(st.vol){ const sc = Math.min(1, .15/Math.max(st.vol,.01)); plan['底仓']=+(plan['底仓']*sc).toFixed(2); plan['现金']=+(1-plan['底仓']-plan['活动仓']-plan['短线']).toFixed(2); }
  const cols = {底仓:'var(--blue)',活动仓:'var(--violet)',短线:'var(--gold)',现金:'#d2d2d7'};
  document.getElementById('c5Body').innerHTML =
    '<div class="pos-bar">'
    + Object.keys(plan).map(k=>'<i style="width:'+(plan[k]*100).toFixed(0)+'%;background:'+cols[k]+'"></i>').join('')
    + '</div>'
    + '<div class="pos-legend">'
    + Object.keys(plan).map(k=>'<span>'+k+' <b>'+Math.round(plan[k]*100)+'%</b></span>').join('')
    + '</div>'
    + '<div class="formula-mini">D级示例模板，不随格雷厄姆指数自动变动（其仅市场背景）；调整期底仓5-6成·进攻期+2成、活动仓2-3成、短线≤2成（A级原话）'+(st.vol?'｜ 波动率修正 σ='+(st.vol*100).toFixed(1)+'%（D级）':'')+(usable?'':'｜ 仅 ready 个股才可按此执行')+'</div>';

  /* Card 6 来源徽章墙 */
  const badges = [];
  (st.sources||[]).forEach(src => {
    const q = src.quality || src.grade || 'C';
    badges.push('<span class="badge" title="'+(src.provider||'')+' · '+(src.as_of||'')+' · '+(src.url||'')+'"><b>'+(src.provider||src.title||'来源').slice(0,12)+'</b><span class="g g'+q+'">'+q+'级</span></span>');
  });
  const ph = (DATA.pe_history||{})[st.ticker];
  if(ph && ph.ok) badges.push('<span class="badge" title="'+(ph.source||'')+' · '+(ph.hist_last_date||'')+'"><b>'+(ph.source||'').slice(0,12)+'</b><span class="g gD">D级</span></span>');
  if(st.pe_source) badges.push('<span class="badge" title="'+st.pe_source+'"><b>倍数分位</b><span class="g gB">B级</span></span>');
  if(st.pb_source) badges.push('<span class="badge" title="'+st.pb_source+'"><b>PB分位</b><span class="g gB">B级</span></span>');
  if(st.forecast_source) badges.push('<span class="badge" title="'+st.forecast_source+'"><b>盈利预测</b><span class="g g'+(usable?'A':'D')+'">'+(usable?'A':'D')+'级</span></span>');
  document.getElementById('c6Body').innerHTML =
    '<div class="badge-wall">'+(badges.join('')||'<span class="badge"><b>无结构化来源</b></span>')+'</div>'
    + (st._warnings&&st._warnings.length ? '<div class="warn-line">⚠ '+String(st._warnings[0]).slice(0,90)+'</div>' : '');
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
      ], 'D') + (evSrc && evSrc.url ? '<a href="'+evSrc.url+'" target="_blank" style="font-size:11.5px">数据源 ↗</a>' : '');
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

/* ============ K线主画布（估值决策主图） ============ */
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
  const AX = W < 560 ? 52 : 64;          /* 右侧价格轴（窄屏收紧） */
  const TL = 8;           /* 顶部留白 */
  const BX = 26;          /* 底部时间轴 */
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
  const vy = v => TL + priceH + 12 + (1 - v / vmax) * (volH - 20);

  let s = '';
  /* 图层1：背景估值色带（低绿/合蓝/高红） */
  if(hasV){
    const bands = [
      { t:y(pmax), b:y(V.high), c:'rgba(255,59,48,.08)' },
      { t:y(V.high), b:y(V.low), c:'rgba(0,113,227,.05)' },
      { t:y(V.low), b:y(pmin), c:'rgba(48,209,88,.08)' },
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
    const vh = Math.max(1.5, r.v / vmax * (volH - 20));
    s += '<rect x="'+(cx-cw/2).toFixed(1)+'" y="'+vy(r.v).toFixed(1)+'" width="'+cw.toFixed(1)+'" height="'+vh.toFixed(1)+'" fill="'+col+'" opacity=".35"/>';
  });
  /* 图层3：均线（图例可切换显隐） */
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
      { v:V.low, c:'#30d158', dash:'6 4', lab:'V_low ¥'+fmt0(V.low) },
      { v:V.mid, c:'#0071e3', dash:'', lab:'V_mid ¥'+fmt0(V.mid) },
      { v:V.high, c:'#ff3b30', dash:'6 4', lab:'V_high ¥'+fmt0(V.high) },
    ];
    anchors.forEach((a, idx) => {
      const yy = y(a.v);
      s += '<line x1="0" y1="'+yy.toFixed(1)+'" x2="'+px1+'" y2="'+yy.toFixed(1)+'" stroke="'+a.c+'" stroke-width="1.3"'+(a.dash?' stroke-dasharray="'+a.dash+'"':'')+' opacity=".9"/>'
         + '<rect x="'+(px1+3)+'" y="'+(yy-10)+'" width="'+(AX-6)+'" height="20" rx="4" fill="#ffffff" fill-opacity=".94"/>'
         + '<text x="'+(px1+7)+'" y="'+(yy+4)+'" font-size="11" font-weight="700" fill="'+a.c+'" font-family="SF Mono,monospace">'+a.lab+'</text>';
      if(!st.decision_usable && idx===0 && W >= 520){
        s += '<rect x="6" y="'+TL+'" width="128" height="20" rx="4" fill="#ffffff" fill-opacity=".92" stroke="rgba(0,0,0,.1)"/>'
           + '<text x="14" y="'+(TL+14)+'" font-size="10.5" fill="#6e6e73" font-weight="600">参考区间 · 不可执行</text>';
      }
    });
  }
  /* 图层5：支撑S绿实线 / 压力R红实线 + 左侧标签 */
  let sl = 0, rl = 0;
  (st.support||[]).forEach((sr,i) => {
    const vv = +sr.level; if(!isFinite(vv) || vv < pmin || vv > pmax) return;
    const yy = y(vv);
    s += '<line x1="0" y1="'+yy.toFixed(1)+'" x2="'+px1+'" y2="'+yy.toFixed(1)+'" stroke="#30d158" stroke-width="1.1" opacity=".8"/>'
       + '<rect x="6" y="'+(yy-10+sl*22)+'" width="88" height="18" rx="4" fill="#ffffff" fill-opacity=".94"/>'
       + '<text x="11" y="'+(yy+4+sl*22)+'" font-size="10.5" font-weight="700" fill="#1f9d4d" font-family="SF Mono,monospace">S'+(i+1)+' ¥'+fmt0(vv)+'</text>';
    sl++;
  });
  (st.resistance||[]).forEach((sr,i) => {
    const vv = +sr.level; if(!isFinite(vv) || vv < pmin || vv > pmax) return;
    const yy = y(vv);
    s += '<line x1="0" y1="'+yy.toFixed(1)+'" x2="'+px1+'" y2="'+yy.toFixed(1)+'" stroke="#ff3b30" stroke-width="1.1" opacity=".8"/>'
       + '<rect x="6" y="'+(yy-10+rl*22)+'" width="88" height="18" rx="4" fill="#ffffff" fill-opacity=".94"/>'
       + '<text x="11" y="'+(yy+4+rl*22)+'" font-size="10.5" font-weight="700" fill="#d70015" font-family="SF Mono,monospace">R'+(i+1)+' ¥'+fmt0(vv)+'</text>';
    rl++;
  });
  /* 图层6：当前价线 */
  const py = y(rows[rows.length-1].c);
  s += '<line x1="0" y1="'+py.toFixed(1)+'" x2="'+px1+'" y2="'+py.toFixed(1)+'" stroke="#0071e3" stroke-width=".8" opacity=".3"/>';
  /* 图层7：Y轴（右5档）与X轴（约6个日期） */
  [0,1,2,3,4].forEach(g => {
    const pv = pmax - (pmax - pmin) * g / 4, gy = TL + priceH * g / 4;
    s += '<text x="'+(px1+7)+'" y="'+(gy+3)+'" font-size="10" fill="#86868b" font-family="SF Mono,monospace">'+fmt2(pv)+'</text>';
  });
  const step = Math.max(1, Math.floor(rows.length / (W < 560 ? 3 : 6)));
  rows.forEach((r,i) => {
    if(i % step !== 0 && i !== rows.length-1) return;
    s += '<text x="'+x(i).toFixed(1)+'" y="'+(TL+priceH+volH+12)+'" font-size="9.5" fill="#86868b" text-anchor="middle" font-family="SF Mono,monospace">'+String(r.d).slice(2,10)+'</text>';
  });
  /* 图层8：十字光标 */
  s += '<line id="chx" x1="0" y1="0" x2="0" y2="0" stroke="#86868b" stroke-width=".8" stroke-dasharray="4 4" opacity="0"/>'
     + '<line id="chy" x1="0" y1="0" x2="0" y2="0" stroke="#86868b" stroke-width=".8" stroke-dasharray="4 4" opacity="0"/>';

  svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
  svg.innerHTML = s;
  document.getElementById('chartInfo').textContent =
    '数据截止 ' + DATA.data_date + ' · ' + rows.length + ' 根 · 前复权 · 红涨绿跌 · 悬停十字光标 · 点击固定';
  document.getElementById('chartTitle').textContent = st.name + ' · 估值决策主图（日K）';

  /* 十字光标 + Tooltip */
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
    let t = '<span class="tk">日期: </span>' + r.d + '\n'
      + '<span class="tk">开盘: </span>' + fmt2(r.o) + '  <span class="tk">最高: </span>' + fmt2(r.h) + '\n'
      + '<span class="tk">收盘: </span>' + fmt2(r.c) + '  <span class="tk">最低: </span>' + fmt2(r.l) + '\n'
      + '<span class="tk">成交量: </span>' + volTxt;
    [5,10,20,60].forEach(win => { const m = maVal(rows,i,win); if(m!=null) t += '\n<span class="tk">MA'+win+': </span>' + fmt2(m); });
    if(hasV){
      t += '\n<span class="tk">距V_low: </span>' + fmt2((r.c/V.low-1)*100) + '%'
         + '  <span class="tk">距V_high: </span>' + fmt2((r.c/V.high-1)*100) + '%';
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
    PIN = CHART_ROWS.length;  /* 固定当前十字光标 */
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
      renderKline();
    };
  });
  let resizeT = null;
  window.addEventListener('resize', () => { clearTimeout(resizeT); resizeT = setTimeout(renderKline, 150); });
  const last = localStorage.getItem('valuation-radar_last');
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
