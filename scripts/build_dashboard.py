# -*- coding: utf-8 -*-
"""估值雷达 · 终端仪表盘生成器 v10（自选池列表双行 Flex 重构）

v10 重构（2026-08-13 用户需求：左侧自选池列表对齐优化）：
  · 结构重构：.l1 baseline 平铺 → 双行 Flex（.sb-row-top：名称+代码组 | 价格组；
    .sb-row-btm：涨跌幅组 | 估值区域组），space-between 稳定右对齐列
  · 删除 align-items:baseline 与 margin-left:auto 双重抢位；涨跌幅并入 flex 组，
    与价格形成垂直扫描线；全部文本 nowrap+ellipsis，价格/涨跌 tabular-nums 防抖动
  · 底部估值条 bar：bottom 0→4px 抬升、padding 底部 8→12px 呼吸空间、
    mark 改 top:50%+translate 居中（5px 高），不再侵入文字安全区
  · 窄屏（≤1399px）：隐藏 nm/cd/px、显示 code 居中；双行居中对齐、chg/zone 缩至 11px

v9 重设计（2026-08-13 用户需求：估值区间与支撑压力位视觉增强）：
  · 色带系统：透明度 .06/.04/.06 → .10/.08/.10；边界 3px/2px 渐变发光带（createLinearGradient）；
    区内 20px 步长横向虚线纹理（slot<2 跳过）；切换股票时色带从顶部向下 0.5s 展开（clip 动画）
  · 估值锚线：1px→1.6px（低 #1f9d4d 虚 6 4 / 中 #0071e3 实线 / 高 #d70015 虚 6 4，round 线帽），
    左端 5px 圆点；与 S/R 同步 0.8s stroke-dashoffset 入场动画
  · 区间定位卡片：左上角 140×52 白卡（现价区间色加粗 / 处于·区间名 / 距最近边界%），
    与 S/R 标签 packLbl 避让下移；移动端 110×34 仅价格+区间名
  · S/R 线条分级：A 2.2px 实线 .90 / B 1.6px 虚 8 4 .75 / C 1.2px 虚 4 4 .55（支撑 #34c759/#30d158/#8ce8a8，
    压力 #ff3b30/#ff6b6b/#ffb3b3）；移动端线宽 -0.3px
  · 触碰反馈：|close/level-1|≤0.8% → 深色（#0a5c28/#8b0000）+线宽+1 + sr-pulse 1.2s 呼吸动画 +
    右侧同心圆标记（r8/r4，移动端取消）；左端 ▲/▼ 方向三角 + 徽章→线连接虚线
  · S/R 左侧标签：16px 矩形 → 20px 全圆角胶囊（强度圆点 A实/B半实/C空心 + 类型 + 价格 + 8字方法缩写），
    A 级淡色底、C 级白底描边；>8 条仅 A/B 标签；packLbl 间距 17→22px；入场滑入动画
  · 越界提示：文字 → ↑/↓ 箭头+价格徽章（横向排列，<title> 原生 tooltip）
  · hover 聚焦：鼠标距 S/R/锚线 ≤6px → 该线 +1.5px/opacity1，其余 0.3，右侧浮动详情卡，
    移开 200ms 恢复；pointerleave 立即恢复
  · 呼吸点：最新收盘价处三圆呼吸（外 r10 内 r3，当前区间色，正弦 400ms 相位），
    pinned 时暂停；rAF 统一渲染循环（_redrawCanvas 只重绘 Canvas 不重建 SVG）
  · chart-foot S/R 迷你图例：视窗内 A/B 优先胶囊列表，点击 scrollToPrice ——
    视内闪烁 sr-pulse，视外 Y 轴平移居中动画（0.4s 缓动，缩放/平移/换股自动复位）
  · 性能：呼吸/动画共用单一 rAF 循环；纹理线 slot<2 跳过；overlay 保持字符串拼接零 DOM 节点

v8 重构（2026-08-13 用户需求：专业级 K 线图引擎）：
  · 渲染架构：Canvas（蜡烛/影线/成交量/均线/估值色带）+ SVG（锚线/S-R/斐波/标签/轴/十字光标）
    + HTML（悬浮信息卡 ktip）三层混合；devicePixelRatio 高分屏适配
  · 交互：十字光标磁吸最近 K 线（价格轴反色胶囊 + 日期胶囊 + 收盘圆点）、
    滚轮以鼠标为中心 1.1x 缩放（10 根~全部）、拖拽平移、双击复位 250 日、
    点击固定/取消固定 Tooltip、300ms 缓动范围切换
  · 标注：估值锚边界虚线+右缘彩色标签（保守/基准/乐观）、估值带滑轨（右缘渐变+现价蓝点）、
    估值带显隐芯片、S/R 左缘强度标签（A/B/C 圆点）、MA120/MA250 及端点价格标签、
    斐波那契 0.382/0.5/0.618、金叉/死叉、涨停/跌停、放量、放量突破
  · Tooltip：OHLCV + 涨跌 + VOL5 倍数 + 六条 MA + 逐日估值位置徽章（深度低估/低估/合理/高估）
    + 最近支撑/阻力（±2% 高亮）+ 右/下边缘翻转
  · 性能：>300 根自动减细影线；缩放/平移 Canvas 重绘经 rAF 调度；ResizeObserver 200ms debounce
  · 数据契约：S/R 仅读 level 字段、NaN/除零/空数据兜底、红涨绿跌、移动端 tooltip 固定底部

v7 优化（2026-08-13 用户验收标准）：
  · 字体系统重构：全局无低于 12px 的数据文本，正文 13px、卡片标题 14px、行高 ≥1.5；
    辅助色对比度达 WCAG AA（--sub/--meta 均 #6e6e73 及以上）
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
            "sectors": state.get("meta", {}).get("sectors", []),
            "sector_note": state.get("meta", {}).get("sector_note", ""),
            "pe_history": state.get("pe_history", {}),
            "market_screen": state.get("market_screen", {}),
            "sector_strength": state.get("sector_strength", {})}
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
/* ============ Design Tokens v8 ============
   三级变量分层：基础 / 语义 / 组件；暗色模式 html[data-theme="dark"] 切换 */
:root{
  /* --- Tier 1 · 基础 --- */
  --space-unit:4px;
  --r-card:8px;
  --text-xs:12px; --text-sm:13px; --text-base:14px; --text-lg:24px; --text-xl:32px;
  --fs-title:12px; --fs-data:13px; --fs-meta:12px;
  /* 字体栈（含 Windows 回退 Segoe UI Variable，等宽含 DIN Alternate） */
  --font-base:-apple-system,BlinkMacSystemFont,"SF Pro Display","PingFang SC","Hiragino Sans GB","Microsoft YaHei","Segoe UI Variable","Noto Sans SC",sans-serif;
  --font-mono:"SF Mono",SFMono-Regular,"DIN Alternate","SF Pro Display","Helvetica Neue","Segoe UI Variable",ui-monospace,Menlo,Consolas,monospace;
  /* --- Tier 2 · 语义：文字层 / 品牌 / 涨跌 --- */
  --bg:#f5f5f7; --bg2:#ffffff; --bg3:#ebebee;
  --hair:rgba(0,0,0,.08); --hair2:rgba(0,0,0,.14);
  --ink:#1d1d1f; --sub:#6e6e73; --sub2:#48484a; --meta:#6e6e73;
  --blue:#0071e3; --blue-d:#005bb8; --blue-lt:rgba(0,113,227,.08);
  --green:#34c759; --green-d:#1f9d4d; --red:#ff3b30; --red-d:#d70015; --gold:#a0742f; --violet:#5e5ce6;
  --candle-up:#d94a47; --candle-dn:#178a59;
  --color-support:#34c759; --color-resist:#ff3b30;
  --color-support-bg:rgba(52,199,89,.08); --color-resist-bg:rgba(255,59,48,.08);
  /* --- Tier 3 · 组件：阴影 / 圆角 / 焦点 / 动效曲线 --- */
  --shadow-card:0 2px 8px rgba(0,0,0,.06),0 1px 2px rgba(0,0,0,.04);
  --shadow-lift:0 8px 24px rgba(0,0,0,.12),0 2px 6px rgba(0,0,0,.06);
  --focus-ring:0 0 0 3px rgba(0,113,227,.18);
  /* 金融级动效曲线库 */
  --ease-instant:cubic-bezier(.25,.1,.25,1);   /* 点击/切换 150ms */
  --ease-spring:cubic-bezier(.32,.72,0,1);     /* 折叠/展开/拖拽 300-400ms */
  --dur-instant:150ms; --dur-layout:320ms; --dur-change:200ms;
  /* 暗色模式（手动覆盖，非媒体查询） */
}
html[data-theme="dark"]{
  --bg:#1c1c1e; --bg2:#2c2c2e; --bg3:#3a3a3c;
  --hair:rgba(255,255,255,.12); --hair2:rgba(255,255,255,.2);
  --ink:#f5f5f7; --sub:#98989d; --sub2:#c7c7cc; --meta:#8e8e93;
  --blue:#0a84ff; --blue-d:#409cff; --blue-lt:rgba(10,132,255,.14);
  --green:#30d158; --green-d:#32d74b; --red:#ff453a; --red-d:#ff6961;
  --gold:#d0a94e; --violet:#bf5af2;
  --candle-up:#ff5f57; --candle-dn:#28d99b;
  --shadow-card:0 2px 8px rgba(0,0,0,.4); --shadow-lift:0 8px 24px rgba(0,0,0,.5);
}
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%;overflow:hidden}
body{font-family:var(--font-base);background:var(--bg);color:var(--ink);font-size:var(--text-sm);line-height:1.5}
button{font-family:var(--font-base);cursor:pointer}
a{color:var(--blue)}
b{font-weight:600}
/* 金融数据强制等宽数字纵向对齐 */
.price,.pct,.px,.chg,.v,.v3b .v,.gauge-num,.jumbo,.b-num,.cong-num,.sr-list .v,.vol-meta,
.sb-item .px,.sb-item .chg,.sector-item .s-pe,.sector-item .s-pct,.ts-row .t-r,.ts-row .t-m,
.sec-row .t-r,.sec-row .t-m,.micro .v,.micro .m,.formula-mini,.src-foot,.kelly-line,.w-ctrl-cnt,
.calc-out,.eq,.s-pe,.t-r b,.env-ev{font-variant-numeric:tabular-nums}
/* 字重规范：标签 500 · 标题 600 · 实时价格 700（取消负 letter-spacing 防粘连） */
.w-title,.w-ctrl-btn,.env-badge,.ts-badge,.badge b{font-weight:600}
.price,.jumbo,.gauge-num{font-weight:700;letter-spacing:0}
.b-lab,.cong-lab,.b-line,.cong-line,.ts-mean,.t-why,.s-why,.micro .k{font-weight:500}
/* 键盘焦点环（仅键盘导航显示） */
:focus-visible{outline:2px solid var(--blue);outline-offset:2px;border-radius:6px}
/* 减少动效：尊重系统设置 */
@media (prefers-reduced-motion: reduce){
  *,*::before,*::after{animation-duration:.01ms !important;animation-iteration-count:1 !important;transition-duration:.01ms !important}
  .mos-dot,.dot-ok,.dot-warn,.dot-bad{animation:none !important}
}

/* ============ 顶栏 38px（紧凑·触摸目标≥40px 由内边距保证） ============ */
.topbar{height:38px;display:flex;align-items:center;gap:10px;padding:0 12px;background:var(--bg2);
  border-bottom:1px solid var(--hair);position:relative;z-index:30}
.brand{display:flex;align-items:center;gap:7px;border:none;background:none;font-size:14px;font-weight:600;color:var(--ink);padding:5px 9px;border-radius:6px;transition:background var(--dur-instant) var(--ease-instant)}
.brand:hover{background:var(--blue-lt);color:var(--blue)}
.brand i{width:15px;height:15px;border-radius:5px;background:linear-gradient(135deg,var(--blue),var(--violet));display:inline-block}
.top-tabs{display:flex;gap:4px;margin:0 6px}
.top-tabs .tab{border:1px solid var(--hair);background:none;color:var(--sub2);font-size:13px;font-weight:600;
  border-radius:7px;padding:5px 12px;transition:all var(--dur-instant) var(--ease-instant);line-height:1.5;white-space:nowrap;min-height:32px}
.top-tabs .tab:hover{border-color:var(--blue);color:var(--blue)}
.top-tabs .tab.on{background:var(--blue-lt);color:var(--blue);border-color:rgba(0,113,227,.35)}
/* 选股触发器：弹性宽度 clamp(180px,20vw,280px) + 内嵌 11px 涨跌色块 */
.stock-trig{display:flex;align-items:center;gap:8px;border:1px solid var(--hair);background:var(--bg2);
  border-radius:var(--r-card);padding:4px 10px;font-size:13px;width:clamp(180px,20vw,280px);min-width:0;height:30px}
.stock-trig:hover{border-color:var(--blue)}
.stock-trig .nm{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:600}
.stock-trig .px-block{flex:none;display:inline-flex;align-items:center;gap:3px;font-size:11px;font-family:var(--font-mono);
  font-variant-numeric:tabular-nums;padding:2px 5px;border-radius:4px;background:var(--blue-lt);color:var(--blue-d);line-height:1.4}
.stock-trig .px-block.up{background:rgba(217,74,71,.1);color:var(--candle-up)}
.stock-trig .px-block.dn{background:rgba(23,138,89,.1);color:var(--candle-dn)}
.stock-trig .arr{margin-left:auto;color:var(--sub);flex:none;font-size:11px}
/* 顶栏右侧：行情日期 / 数据日期 微标签 + 预警状态呼吸灯 */
.top-gate{margin-left:auto;display:flex;align-items:center;gap:10px;font-size:13px;color:var(--sub2)}
.top-gate .dot{width:8px;height:8px;border-radius:50%;flex:none}
.dot-ok{background:var(--green);animation:gatePulse .8s ease-out infinite;--gate-glow:rgba(52,199,89,.45)}
.dot-warn{background:var(--gold);animation:gatePulse .8s ease-out infinite;--gate-glow:rgba(160,116,47,.45)}
.dot-bad{background:var(--red);animation:gateBlink 1.2s steps(1,end) infinite;--gate-glow:rgba(255,59,48,.5)}
@keyframes gatePulse{0%{box-shadow:0 0 0 0 var(--gate-glow)}70%{box-shadow:0 0 0 6px transparent}100%{box-shadow:0 0 0 0 transparent}}
@keyframes gateBlink{0%,55%{opacity:1}56%,100%{opacity:.25}}
.top-upd{font-size:var(--text-xs);color:var(--meta)}
.top-upd b{color:var(--sub2);font-weight:600}
/* 数据日期微标签 */
.micro-date{display:inline-flex;align-items:center;gap:4px;font-size:11px;color:var(--meta);
  border:1px solid var(--hair);border-radius:4px;padding:1px 6px;font-family:var(--font-mono);font-variant-numeric:tabular-nums}
.micro-date b{color:var(--blue-d);font-weight:600}

/* ============ 弹出选股器 ============ */
.popover{position:absolute;top:42px;left:12px;width:440px;background:var(--bg2);border:1px solid var(--hair);
  border-radius:10px;box-shadow:var(--shadow-lift);display:none;z-index:50;padding:8px}
.popover.on{display:block}
.pop-search{width:100%;border:1px solid var(--hair);border-radius:6px;padding:8px 10px;font-size:13px;margin-bottom:6px;
  transition:border-color var(--dur-instant) var(--ease-instant),box-shadow var(--dur-instant) var(--ease-instant)}
.pop-search:focus{outline:none;border-color:var(--blue);box-shadow:0 0 0 3px rgba(0,113,227,.12);width:calc(100% + 4%)}
.pop-list{max-height:440px;overflow-y:auto}
.pop-item{display:flex;align-items:center;gap:10px;width:100%;text-align:left;border:none;background:none;
  padding:8px 10px;border-radius:6px;font-size:13px;transition:background var(--dur-instant) var(--ease-instant),transform var(--dur-instant) var(--ease-instant);
  position:relative}
.pop-item:hover,.pop-item.sel{background:var(--blue-lt)}
.pop-item:hover{transform:translateX(2px)}
/* 键盘导航指示条：左侧 2px 蓝色竖线 */
.pop-item.sel::before{content:'';position:absolute;left:2px;top:8px;bottom:8px;width:2px;border-radius:1px;background:var(--blue)}
.pop-item .nm{font-weight:600}
.pop-item .cd{color:var(--meta);font-family:var(--font-mono)}
.pop-item .st{margin-left:auto;font-size:12px}

/* ============ 主体三栏 Grid（100vh 单屏） ============ */
.shell{display:grid;grid-template-columns:minmax(200px,14vw) minmax(0,1fr) 8px var(--wall-w,340px);grid-template-rows:minmax(0,1fr);
  height:calc(100vh - 38px);overflow:hidden}

/* ---- 左导航 minmax(200px,14vw) ---- */
.sidebar{border-right:1px solid var(--hair);background:var(--bg2);display:flex;flex-direction:column;min-height:0;min-width:0}
.sb-hd{display:flex;justify-content:space-between;align-items:baseline;padding:12px 12px 8px;
  font-size:var(--fs-title);font-weight:600;letter-spacing:.05em;color:var(--sub);text-transform:uppercase}
.sb-search{margin:0 10px 8px;border:1px solid var(--hair);border-radius:6px;padding:7px 10px;font-size:13px}
.sb-list{flex:1;overflow-y:auto;min-height:0}
/* ============ 左导航 — 自选池列表（双行 Flex） ============ */
.sb-item{
  display:flex;
  flex-direction:column;
  gap:2px;
  width:100%;
  text-align:left;
  border:none;
  background:none;
  padding:8px 12px 12px;        /* 底部 +4px 给 bar 留呼吸空间 */
  border-bottom:1px solid var(--hair);
  font-size:13px;
  position:relative;
  transition:background .15s,transform .15s;
  min-height:0;
}
.sb-item:hover{background:var(--blue-lt);transform:translateX(2px)}
.sb-item.on{background:var(--blue-lt);box-shadow:inset 3px 0 0 0 var(--blue), -4px 0 12px rgba(0,113,227,.08)}
.sb-item.on .bar{border:1px solid rgba(0,113,227,.35)}
/* ---- 板块分组：横向滚动板块筛选条 + 分组标题 ---- */
.sb-sectors{display:flex;gap:4px;overflow-x:auto;padding:0 10px 8px;scrollbar-width:none}
.sb-sectors::-webkit-scrollbar{display:none}
.sb-sec{border:1px solid var(--hair);background:none;color:var(--sub2);font-size:12px;font-weight:600;
  border-radius:999px;padding:3px 10px;white-space:nowrap;line-height:1.5;transition:all .15s;flex:0 0 auto}
.sb-sec:hover{border-color:var(--blue);color:var(--blue)}
.sb-sec.on{background:var(--blue-lt);color:var(--blue);border-color:rgba(0,113,227,.35)}
.sb-grp{position:sticky;top:0;z-index:3;display:flex;align-items:center;justify-content:space-between;gap:8px;
  padding:8px 12px 4px;background:var(--bg2);font-size:11px;font-weight:700;letter-spacing:.06em;
  color:var(--meta);text-transform:uppercase}
.sb-grp .n{font-family:var(--font-mono);font-weight:600;letter-spacing:0}
.sb-grp.focus{color:var(--blue)}
/* 双行容器：左标识 / 右数据 */
.sb-row-top,.sb-row-btm{
  display:flex;
  align-items:center;
  justify-content:space-between;
  min-width:0;
  gap:8px;
}
.sb-name-group,.sb-price-group,
.sb-change-group,.sb-zone-group{
  display:flex;
  align-items:center;
  gap:4px;
  min-width:0;
}
.sb-price-group,.sb-zone-group{justify-content:flex-end}
/* 文本统一截断，防止长名撑破 */
.sb-item .nm,.sb-item .cd,.sb-item .px,.sb-item .chg,.sb-item .sb-zone{
  white-space:nowrap;
  overflow:hidden;
  text-overflow:ellipsis;
}
.sb-item .nm{font-weight:600;font-size:13px;color:var(--ink)}
.sb-item .cd{color:var(--meta);font-family:var(--font-mono);font-size:12px}
.sb-item .px{
  font-family:var(--font-mono);
  font-weight:600;
  font-size:13px;
  color:var(--ink);
  font-variant-numeric:tabular-nums;
  text-align:right;
}
.sb-item .chg{
  font-size:12px;
  font-family:var(--font-mono);
  font-variant-numeric:tabular-nums;
}
.sb-item .code{display:none}
/* 估值位置条：4px→5px 胶囊端头 + mark 垂直居中 */
.sb-item .bar{position:absolute;left:12px;right:12px;bottom:4px;height:5px;border-radius:999px;overflow:hidden;
  background:linear-gradient(90deg,rgba(52,199,89,.55) 0 25%,rgba(0,113,227,.45) 25% 75%,rgba(255,59,48,.55) 75% 100%)}
.sb-item .bar i{display:none}
.sb-item .bar .mark{
  position:absolute;
  top:50%;
  transform:translate(-50%,-50%);
  width:2px;
  height:6px;
  background:var(--ink);
  border-radius:1px;
}
.up-c{color:var(--candle-up)}.dn-c{color:var(--candle-dn)}
/* 估值区域标签 */
.sb-zone{font-size:12px;color:var(--sub2)}
.sb-zone.z0,.sb-zone.z1{color:var(--green-d)}.sb-zone.z4,.sb-zone.z5{color:var(--red-d)}.sb-zone.z2,.sb-zone.z3{color:var(--gold)}

/* ---- 中央区 ---- */
.center{display:flex;flex-direction:column;min-width:0;min-height:0;background:var(--bg)}
.hero-strip{display:flex;align-items:center;gap:18px;padding:12px 20px;background:var(--bg2);position:relative;flex-wrap:wrap}
/* hairline 渐变分隔：从左到右由实到虚 */
.hero-strip::after{content:'';position:absolute;left:0;right:0;bottom:-1px;height:1px;
  background:linear-gradient(90deg,var(--hair2),var(--hair) 60%,transparent)}
.hero-strip .hl{min-width:0;flex:1}
.hero-strip .eyebrow{font-size:12px;letter-spacing:.05em;color:var(--sub2);text-transform:uppercase}
.hero-strip h1{font-size:23px;font-weight:700;letter-spacing:0;line-height:1.3}
.hero-strip .tick{font-size:12px;color:var(--sub2);font-family:var(--font-mono)}
.hero-strip .pills{display:flex;gap:6px;flex-wrap:wrap;margin-top:4px}
.pill{display:inline-flex;align-items:center;gap:6px;border-radius:999px;padding:4px 12px;font-size:12px;
  border:1px solid var(--hair);background:var(--bg2);line-height:1.5}
.pill .dot{width:7px;height:7px;border-radius:50%}
.hero-strip .hr{margin-left:auto;text-align:right;min-width:250px}
.hero-strip .price{font-size:var(--text-xl);font-weight:700;font-family:var(--font-mono);font-variant-numeric:tabular-nums;
  letter-spacing:0;line-height:1.2;transition:border-color var(--dur-change) var(--ease-instant);position:relative;z-index:6}
/* 价格更新闪烁（200ms 边框高亮） */
.hero-strip .price.flash{box-shadow:0 0 0 2px rgba(0,113,227,.25);border-radius:6px}
.hero-strip .price.flash-red{box-shadow:0 0 0 2px rgba(255,59,48,.3);border-radius:6px}
.hero-strip .price.flash-green{box-shadow:0 0 0 2px rgba(52,199,89,.3);border-radius:6px}
/* 跌破 V_low / 突破 V_high 边缘警示条（2px 红渐变，3s 淡出；z-index 5 位于价格之下，不截断价格闪烁） */
.edge-alert{position:absolute;left:0;right:0;top:0;height:2px;background:linear-gradient(90deg,transparent,var(--red),transparent);
  opacity:0;pointer-events:none;z-index:5;transition:opacity .3s}
.edge-alert.on{opacity:1;animation:edgeFade 3s ease forwards}
@keyframes edgeFade{0%{opacity:1}70%{opacity:1}100%{opacity:0}}
.hero-strip .pct{font-size:16px;font-family:var(--font-mono);font-variant-numeric:tabular-nums}
.hero-strip .mos-wrap{margin-top:5px}
.mos-track{display:flex;justify-content:space-between;font-size:12px;color:var(--sub2);margin-bottom:3px}
/* MOS：连续渐变轨道（绿→蓝→红 平滑过渡），非三段拼接 */
.mos-bar{position:relative;height:8px;border-radius:4px;overflow:visible;background:linear-gradient(90deg,#34c759 0%,#0071e3 50%,#ff3b30 100%)}
.mos-bar i{display:block;height:100%;background:transparent}
.mos-marker{position:relative;height:0}
.mos-dot{position:absolute;top:-9px;width:12px;height:12px;border-radius:50%;background:var(--blue);
  border:2px solid #fff;transform:translateX(-50%);box-shadow:0 0 0 1px var(--hair2);
  animation:pulseRing 2s ease-out infinite;z-index:2}
/* 常驻价格微标：始终显示当前 MOS 数值，随圆点吸附 */
.mos-val{position:absolute;top:-24px;transform:translateX(-50%);white-space:nowrap;font-size:11px;
  font-family:var(--font-mono);font-variant-numeric:tabular-nums;font-weight:600;color:#fff;
  background:var(--blue);border-radius:4px;padding:1px 6px;line-height:1.6;pointer-events:none;z-index:3}
.mos-val::after{content:'';position:absolute;left:50%;bottom:-4px;transform:translateX(-50%);
  border:4px solid transparent;border-top-color:var(--blue);border-bottom-width:0}
@keyframes pulseRing{0%{box-shadow:0 0 0 1px var(--hair2),0 0 0 0 rgba(0,113,227,.35)}
  70%{box-shadow:0 0 0 1px var(--hair2),0 0 0 8px rgba(0,113,227,0)}100%{box-shadow:0 0 0 1px var(--hair2),0 0 0 0 rgba(0,113,227,0)}}
.mos-txt{font-size:13px;color:var(--sub2);margin-top:7px;line-height:1.5}

/* ---- K线主画布 ---- */
.chart-zone{flex:1;display:flex;flex-direction:column;min-height:0;padding:8px 10px 6px}
.chart-toolbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:6px}
.chart-toolbar h3{font-size:14px;font-weight:600}
.chart-toolbar .info{font-size:12px;color:var(--sub2);min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.range-btns{display:flex;gap:4px}
.range-btn{font-size:12px;padding:4px 11px;border-radius:999px;border:1px solid var(--hair);
  background:var(--bg2);color:var(--sub2);transition:all var(--dur-layout) var(--ease-spring);position:relative}
.range-btn:hover{border-color:var(--blue);color:var(--blue);transform:translateY(-1px)}
.range-btn.on{background:linear-gradient(180deg,var(--blue),var(--blue-d));border-color:var(--blue-d);color:#fff;font-weight:600;box-shadow:0 2px 6px rgba(0,113,227,.3)}
.ma-legend{margin-left:auto;display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end;max-width:100%}
.ma-chip{display:inline-flex;align-items:center;gap:4px;font-size:12px;border:1px solid var(--hair);
  border-radius:999px;padding:3px 10px;background:var(--bg2);color:var(--sub2);transition:transform var(--dur-instant) var(--ease-instant),box-shadow var(--dur-instant) var(--ease-instant),opacity var(--dur-change) var(--ease-instant)}
.ma-chip:hover{transform:translateY(-1px);box-shadow:0 2px 8px rgba(0,0,0,.10)}
.ma-chip.on{box-shadow:0 2px 6px rgba(0,0,0,.12)}
.ma-chip i{width:9px;height:3px;display:inline-block;border-radius:1px}
.ma-chip.off{opacity:.4;text-decoration:line-through}
.chart-wrap{flex:1;position:relative;min-height:200px;border:1px solid var(--hair);border-radius:var(--r-card);
  background:var(--bg2);overflow:hidden;user-select:none;transition:opacity .2s ease}
.chart-wrap.fade{opacity:.6}
/* 无障碍：屏幕阅读器专用实时区（视觉隐藏） */
.visually-hidden{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;
  clip:rect(0 0 0 0);white-space:nowrap;border:0}
.chart-wrap canvas{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:0}
/* 右侧 Y 轴毛玻璃面板：56px 半透明 + 背景模糊，位于 canvas 之上、svg 覆盖层之下 */
.axis-panel{position:absolute;top:12px;right:0;bottom:24px;width:56px;z-index:1;pointer-events:none;
  background:color-mix(in srgb,var(--bg2) 85%,transparent);
  backdrop-filter:blur(16px) saturate(180%);-webkit-backdrop-filter:blur(16px) saturate(180%);
  border-left:1px solid var(--hair)}
.chart-wrap svg{position:absolute;inset:0;width:100%;height:100%;display:block;cursor:crosshair;touch-action:none;z-index:2}
.chart-foot{display:flex;gap:16px;font-size:12px;color:var(--sub2);padding:5px 2px 0;flex-wrap:wrap;line-height:1.5}
.legend-mini{display:inline-flex;align-items:center;gap:5px}
.legend-mini i{width:10px;height:3px;border-radius:2px;display:inline-block}
.srfoot{margin-left:auto;display:flex;gap:6px;flex-wrap:wrap;max-width:100%;justify-content:flex-end}
.srfoot .cap{display:inline-flex;align-items:center;gap:4px;font-family:var(--font-mono);font-size:12px;
  border:1px solid var(--hair);border-radius:999px;padding:2px 10px;background:var(--bg2);cursor:pointer;
  white-space:nowrap;line-height:1.5;transition:border-color .15s,transform .15s}
.srfoot .cap:hover{border-color:var(--blue);transform:translateY(-1px)}
.srfoot .cap i{width:6px;height:6px;border-radius:50%;display:inline-block;flex:none}
.srfoot .cap.s i{background:var(--color-support)}
.srfoot .cap.r i{background:var(--color-resist)}
.srfoot .cap .v{color:var(--sub2);font-variant-numeric:tabular-nums}
.ktip{position:absolute;background:color-mix(in srgb,var(--bg2) 86%,transparent);
  backdrop-filter:blur(16px) saturate(180%);-webkit-backdrop-filter:blur(16px) saturate(180%);
  border:1px solid var(--hair);
  border-radius:10px;padding:10px 14px;font-family:var(--font-mono);font-size:12px;line-height:1.7;color:var(--ink);
  box-shadow:var(--shadow-lift);pointer-events:none;opacity:0;min-width:186px;max-width:280px;z-index:24;
  font-variant-numeric:tabular-nums;white-space:pre;transition:opacity var(--dur-instant) var(--ease-instant)}
.ktip.show{opacity:1}
.ktip.mobile{left:6px !important;right:6px !important;top:auto !important;bottom:6px !important;max-width:none}
.ktip .tk{color:var(--sub2)}
.ktip .kdate{color:var(--ink);font-weight:700}
.ktip .ztip{display:flex;align-items:center;gap:8px;margin-bottom:4px}
.ktip .krow{display:flex;align-items:baseline;gap:8px;white-space:nowrap}
.ktip .krow .tk{min-width:3.2em}
.ktip .krow.ma{flex-wrap:wrap;row-gap:2px}
.ktip .krow .mma{display:inline-flex;align-items:center;gap:4px}
.ktip .krow .mma i{width:9px;height:3px;border-radius:1px}
.ktip .near-s{color:var(--green-d);font-weight:700}
.ktip .near-r{color:var(--red-d);font-weight:700}
.ktip .zone-badge{display:inline-block;border-radius:4px;padding:1px 8px;font-size:12px;font-weight:700}
/* 3日迷你走势（Sparkline） */
.ktip .spark{margin-top:6px;height:24px;display:block}
.ktip .spark polyline{fill:none;stroke-width:1.5;stroke-linecap:round;stroke-linejoin:round}
.ktip .spark .last-dot{fill:var(--candle-dn)}
.ov-wrap{flex:1;overflow-y:auto;min-height:0;padding:16px;background:var(--bg);height:calc(100vh - 38px);box-sizing:border-box}
.ov-cards{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px}
/* 板块水位行 */
.sector-item{display:grid;grid-template-columns:minmax(0,1.2fr) auto minmax(80px,1fr) auto auto minmax(0,1fr);gap:10px;align-items:center;
  padding:9px 4px;border-bottom:1px solid var(--hair);font-size:13px;line-height:1.5;cursor:pointer;
  border-radius:6px;transition:background .15s,transform .15s}
.sector-item:hover{background:var(--blue-lt);transform:translateX(2px)}
.sector-item .s-name{font-weight:600;color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sector-item .s-pe{font-family:var(--font-mono);color:var(--sub2);font-variant-numeric:tabular-nums;white-space:nowrap;font-size:12px}
.sector-item .s-pe b{font-weight:600}
.sector-item .s-bar{height:6px;border-radius:3px;background:var(--hair);overflow:hidden;min-width:60px}
.sector-item .s-bar i{display:block;height:100%;border-radius:3px}
.sector-item .s-pct{font-family:var(--font-mono);font-weight:600;font-variant-numeric:tabular-nums;white-space:nowrap;font-size:12px}
.sector-item .s-sig{font-size:12px;font-weight:600;white-space:nowrap}
.sector-item .s-why{font-size:12px;color:var(--meta);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
@media(max-width:1099px){
  .ov-cards{grid-template-columns:1fr}
  .sector-item{grid-template-columns:1fr auto 1fr;grid-template-areas:"n sig" "pe pe" "bar bar" "pct why";row-gap:3px}
  .sector-item .s-name{grid-area:n}.sector-item .s-sig{grid-area:sig;text-align:right}
  .sector-item .s-pe{grid-area:pe}.sector-item .s-bar{grid-area:bar}
  .sector-item .s-pct{grid-area:pct}.sector-item .s-why{grid-area:why;text-align:right}
}
/* 第一层：大盘环境横幅 */
.env-banner{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:10px}
.env-badge{font-size:15px;font-weight:700;border:1px solid;border-radius:999px;padding:6px 16px;line-height:1.5;white-space:nowrap}
.env-ev{font-family:var(--font-mono);font-size:12px;color:var(--sub2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
/* 市场宽度 */
.breadth-box{margin:8px 0;padding:10px 12px;border-radius:8px;background:var(--bg2);border:1px solid var(--hair)}
.b-line{display:flex;align-items:center;gap:12px;flex-wrap:wrap;font-size:12px;line-height:1.6}
.b-lab{font-weight:700;color:var(--ink)}
.b-num{font-family:var(--font-mono);color:var(--sub2);white-space:nowrap}
.b-num b{font-weight:600}
.b-bar{position:relative;height:6px;border-radius:3px;background:var(--hair);margin:8px 0 4px;overflow:hidden}
.b-bar i{position:absolute;top:0;bottom:0;left:0}
.b-bar i:last-child{right:0;left:auto}
.b-note{font-size:12px;line-height:1.5}
/* 大盘拥挤度（成交额前5%个股占比 · 牛熊转换观察） */
.cong-box{margin:8px 0;padding:10px 12px;border-radius:8px;background:var(--bg2);border:1px solid var(--hair)}
.cong-line{display:flex;align-items:center;gap:12px;flex-wrap:wrap;font-size:12px;line-height:1.6}
.cong-lab{font-weight:700;color:var(--ink)}
.cong-num{font-family:var(--font-mono);white-space:nowrap}
.cong-num b{font-weight:600}
.cong-bar{position:relative;height:7px;border-radius:4px;margin:9px 0 5px;
  background:linear-gradient(90deg,var(--green-d) 0 33%,var(--gold) 33% 50%,var(--red-d) 50% 100%)}
.cong-bar .g{position:absolute;top:-3px;height:13px;width:2px;background:var(--sub2);border-radius:1px;transform:translateX(-50%)}
.cong-bar .mk{position:absolute;top:50%;transform:translate(-50%,-50%);width:11px;height:11px;border-radius:50%;
  background:var(--bg2);border:2px solid var(--ink);box-shadow:0 0 0 1px var(--hair2)}
.cong-labels{display:flex;justify-content:space-between;font-size:11px;color:var(--meta);font-family:var(--font-mono)}
.cong-peaks{display:flex;flex-wrap:wrap;gap:5px 10px;font-size:12px;line-height:1.6;margin-top:7px}
.cong-peaks .pk{display:inline-flex;align-items:center;gap:5px}
.cong-peaks .pk i{width:7px;height:7px;border-radius:50%;background:var(--red-d);flex:none}
.cong-peaks .pk b{font-family:var(--font-mono);font-weight:600}
.cong-peaks .pk em{font-style:normal;color:var(--meta)}
/* 量能趋势柱状图 */
.vol-bars{display:flex;align-items:flex-end;gap:3px;height:44px;margin:8px 0 4px}
.vol-bars .vb{flex:1;min-width:3px;border-radius:2px 2px 0 0;cursor:default}
.vol-meta{font-size:12px;color:var(--sub2);font-family:var(--font-mono);line-height:1.6}
/* 第三层：五类状态分组 */
.filter-row{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:8px}
.filter-row .f-tabs{display:flex;gap:4px;margin-left:auto}
.filter-row .f-tab{border:1px solid var(--hair);background:none;color:var(--sub2);font-size:12px;font-weight:600;
  border-radius:6px;padding:4px 10px;transition:all .15s;line-height:1.5;white-space:nowrap}
.filter-row .f-tab:hover{border-color:var(--blue);color:var(--blue)}
.filter-row .f-tab.on{background:var(--blue-lt);color:var(--blue);border-color:rgba(0,113,227,.35)}
.ts-group{margin-bottom:14px}
.ts-head{display:flex;align-items:center;gap:10px;margin:10px 0 6px}
.ts-badge{font-size:13px;font-weight:700;border:1px solid;border-radius:999px;padding:3px 12px;line-height:1.5;white-space:nowrap}
.ts-mean{font-size:12px;color:var(--meta);line-height:1.5}
.ts-row{display:grid;grid-template-columns:minmax(90px,auto) auto 1fr minmax(140px,auto);gap:12px;align-items:center;
  padding:8px 6px;border-bottom:1px solid var(--hair);font-size:13px;cursor:pointer;border-radius:6px;
  transition:background .15s,transform .15s}
.ts-row:hover{background:var(--blue-lt);transform:translateX(2px)}
.ts-row .t-nm{font-weight:600;color:var(--ink);white-space:nowrap}
.ts-row .t-nm i{display:block;font-style:normal;font-size:11px;color:var(--meta);font-family:var(--font-mono)}
.ts-row .t-r{display:flex;gap:10px;white-space:nowrap;font-family:var(--font-mono);font-variant-numeric:tabular-nums}
.ts-row .t-r b{font-weight:600;font-size:12px}
.ts-row .t-m{font-size:12px;color:var(--sub2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-family:var(--font-mono)}
.ts-row .t-why{font-size:12px;color:var(--meta);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
/* 行业板块行 */
.sec-row{display:grid;grid-template-columns:minmax(80px,auto) auto 1fr minmax(120px,auto);gap:12px;align-items:center;
  padding:8px 6px;border-bottom:1px solid var(--hair);font-size:13px;border-radius:6px;line-height:1.5}
.sec-row .t-nm{font-weight:600;color:var(--ink);white-space:nowrap}
.sec-row .t-r{display:flex;gap:10px;white-space:nowrap;font-family:var(--font-mono);font-variant-numeric:tabular-nums}
.sec-row .t-r b{font-weight:600;font-size:12px}
.sec-row .t-m{font-size:12px;color:var(--sub2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-family:var(--font-mono)}
.sec-row .t-m b{font-weight:600}
.sec-row .t-why{font-size:12px;color:var(--meta);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sec-row .t-why b{font-weight:600}
/* ---- 自选池板块聚合卡（研究分组，非行业指数）---- */
.my-sec-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px}
.my-sec{border:1px solid var(--hair);border-radius:10px;padding:12px 12px 8px;background:var(--bg3)}
.my-sec.focus{border-color:rgba(0,113,227,.35);box-shadow:0 0 0 2px var(--blue-lt)}
.my-sec-hd{display:flex;align-items:baseline;justify-content:space-between;gap:8px;margin-bottom:6px}
.my-sec-nm{font-size:15px;font-weight:700;color:var(--ink)}
.my-sec-nm .tag{font-size:11px;font-weight:600;color:var(--blue);border:1px solid rgba(0,113,227,.35);
  border-radius:999px;padding:1px 7px;margin-left:6px;vertical-align:1px}
.my-sec-chg{font-family:var(--font-mono);font-size:15px;font-weight:700;font-variant-numeric:tabular-nums}
.my-sec-stat{font-size:12px;color:var(--sub2);font-family:var(--font-mono);font-variant-numeric:tabular-nums;
  margin-bottom:6px;display:flex;gap:12px;flex-wrap:wrap}
.my-sec-note{font-size:12px;color:var(--meta);line-height:1.7;margin-bottom:6px}
.my-sec-row{display:grid;grid-template-columns:minmax(72px,auto) auto 1fr auto;gap:10px;align-items:center;
  padding:5px 4px;border-top:1px solid var(--hair);font-size:12px;cursor:pointer;border-radius:6px;
  transition:background .15s,transform .15s}
.my-sec-row:hover{background:var(--blue-lt);transform:translateX(2px)}
.my-sec-row .m-nm{font-weight:600;color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.my-sec-row .m-nm i{font-style:normal;font-size:11px;color:var(--meta);font-family:var(--font-mono)}
.my-sec-row .m-px{font-family:var(--font-mono);font-variant-numeric:tabular-nums;white-space:nowrap}
.my-sec-row .m-why{font-size:11px;color:var(--meta);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.my-sec-row .m-st{font-size:11px;font-weight:600;white-space:nowrap}
@media(max-width:1099px){
  .sec-row{grid-template-columns:1fr auto;grid-template-areas:"nm r" "m m" "w w";gap:4px 10px}
  .sec-row .t-nm{grid-area:nm}.sec-row .t-r{grid-area:r}
  .sec-row .t-m{grid-area:m}.sec-row .t-why{grid-area:w}
}
@media(max-width:1099px){
  .ts-row{grid-template-columns:1fr auto;grid-template-areas:"nm r" "m m" "w w";gap:4px 10px}
  .ts-row .t-nm{grid-area:nm}.ts-row .t-r{grid-area:r}
  .ts-row .t-m{grid-area:m}.ts-row .t-why{grid-area:w}
}
.ov-table{width:100%;border-collapse:collapse;font-size:13px;background:var(--bg2);
  border:1px solid var(--hair);border-radius:var(--r-card)}
.ov-table th{text-align:left;padding:8px 10px;font-size:12px;letter-spacing:.05em;text-transform:uppercase;
  color:var(--sub);border-bottom:1px solid var(--hair)}
.ov-table td{padding:8px 10px;border-bottom:1px solid var(--hair);font-family:var(--font-mono)}
.ov-table tr{cursor:pointer;transition:background .15s,transform .15s}
.ov-table tr:hover{background:var(--blue-lt);transform:translateX(2px)}

/* ---- 右数据墙 var(--wall-w) 可拖拽 ---- */
.wall{background:var(--bg);border-left:1px solid var(--hair);overflow-y:auto;padding:10px;min-height:0;
  min-width:280px;max-width:480px;width:var(--wall-w,340px);container-type:inline-size}
/* 拖拽手柄：8px 轨道，hover 双竖线图标 */
.wall-grip{cursor:col-resize;position:relative;z-index:5;background:transparent;transition:background .15s;
  width:8px;flex:none}
.wall-grip::after{content:'';position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
  width:3px;height:22px;background:var(--hair2);border-radius:3px;opacity:0;transition:opacity .15s}
.wall-grip:hover::after,.wall-grip.dragging::after{opacity:1;background:var(--blue)}
.wall-grip:hover,.wall-grip.dragging{background:rgba(0,113,227,.25)}
/* 整墙收起：K 线图占满右侧 */
body.wall-hidden .shell{grid-template-columns:minmax(200px,14vw) minmax(0,1fr) 0 0}
body.wall-hidden .wall{min-width:0;max-width:0;width:0;border-left:none;padding:0;overflow:hidden}
body.wall-hidden .wall-grip{display:none}
.wall-toggle-btn{border:1px solid var(--hair);background:var(--bg2);color:var(--sub2);font-size:12px;
  border-radius:7px;padding:5px 10px;transition:all var(--dur-instant) var(--ease-instant);line-height:1.5;white-space:nowrap}
.wall-toggle-btn:hover{border-color:var(--blue);color:var(--blue)}
/* 折叠控制条（sticky，滚动时始终可见） */
.wall-ctrl{position:sticky;top:0;z-index:8;display:flex;align-items:center;gap:10px;padding:6px 4px 10px;
  margin:-6px -4px 4px;background:rgba(245,245,247,.82);backdrop-filter:blur(12px) saturate(180%);
  -webkit-backdrop-filter:blur(12px) saturate(180%)}
.w-ctrl-btn{border:1px solid var(--hair);background:var(--bg2);color:var(--blue);font-size:12px;font-weight:600;
  border-radius:7px;padding:5px 12px;transition:all var(--dur-instant) var(--ease-instant);line-height:1.5}
.w-ctrl-btn:hover{border-color:var(--blue);box-shadow:0 2px 8px rgba(0,113,227,.15)}
.w-ctrl-cnt{margin-left:auto;font-size:12px;color:var(--meta);font-family:var(--font-mono);font-variant-numeric:tabular-nums}
/* 折叠：FLIP 思路（transform + opacity 复合动画，GPU 友好） */
.w-card{background:var(--bg2);border:1px solid var(--hair);border-radius:var(--r-card);
  padding:14px 16px;margin-bottom:12px;box-shadow:var(--shadow-card);
  animation:cardIn .4s var(--ease-instant) both;
  display:grid;grid-template-rows:auto 1fr;transition:grid-template-rows var(--dur-layout) var(--ease-spring),
    opacity var(--dur-instant) var(--ease-instant),transform var(--dur-instant) var(--ease-instant)}
.w-card.collapsed{grid-template-rows:auto 0fr;opacity:.92}
@keyframes cardIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.w-title{font-size:var(--fs-title);font-weight:600;letter-spacing:.05em;text-transform:uppercase;
  color:var(--sub);margin-bottom:12px;display:flex;align-items:center;gap:6px;line-height:1.5;min-width:0}
.w-card.collapsed .w-title{color:var(--sub2);margin-bottom:0}
.w-title .sp{margin-left:auto;font-size:12px;color:var(--meta);text-transform:none;letter-spacing:0}
/* 折叠态关键数据微标（折叠后仍可见核心数值） */
.w-micro{display:none;margin-left:auto;font-size:11px;font-family:var(--font-mono);font-variant-numeric:tabular-nums;
  color:var(--sub2);background:var(--bg);border:1px solid var(--hair);border-radius:4px;padding:1px 6px;white-space:nowrap;line-height:1.6}
.w-card.collapsed .w-micro{display:inline-flex;align-items:center}
.w-fold{flex:none;width:22px;height:22px;border:1px solid var(--hair);border-radius:6px;background:var(--bg);
  color:var(--sub2);font-size:11px;line-height:1;transition:all var(--dur-instant) var(--ease-instant)}
.w-fold:hover{border-color:var(--blue);color:var(--blue);background:var(--blue-lt)}
.w-card.collapsed .w-fold{color:var(--meta)}
.w-body{overflow:hidden;min-width:0;min-height:0;overflow-wrap:break-word}
.w-card.collapsed .w-body{overflow:hidden;visibility:hidden}
.w-body > *{min-width:0}
/* 等宽数据防溢出：单行截断 + hover 原生 title 兜底 */
.w-body .v,.w-body .px,.w-body .gauge-num,.w-body .micro .v{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.src-foot{font-size:11px;color:var(--meta);margin-top:8px;border-top:1px solid var(--hair);padding-top:6px;
  line-height:1.5;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
/* 折叠区 */
.fold-toggle{display:block;width:100%;text-align:center;border:none;background:none;color:var(--blue);
  font-size:12px;padding:8px 0 2px;margin-top:8px;border-top:1px solid var(--hair);line-height:1.5}
.fold{display:none}
.fold.open{display:block}
/* 关键价位：价格轨道（顶部预留标签错开区） */
.sr-track{position:relative;height:44px;border-radius:17px;margin:14px 0 10px;
  background:linear-gradient(90deg,var(--color-support-bg),rgba(0,113,227,.05) 50%,var(--color-resist-bg))}
.sr-track .tick{position:absolute;top:14px;bottom:0;width:1px;background:var(--hair2)}
.sr-dot{position:absolute;top:28px;transform:translate(-50%,-50%);border-radius:50%;cursor:default}
/* 轨道标签：tier2 下沉一行错开；✦ = 250日内价格触及过该位 */
.sr-lbl{position:absolute;top:2px;transform:translateX(-50%);white-space:nowrap;font-size:10px;
  font-family:var(--font-mono);font-variant-numeric:tabular-nums;color:var(--sub2);
  background:var(--bg2);border:1px solid var(--hair);border-radius:3px;padding:0 4px;line-height:1.7;pointer-events:none}
.sr-lbl.tier2{top:16px}
.sr-lbl:hover{color:var(--blue)}
.sr-dot.cur{width:14px;height:14px;background:var(--blue);border:2.5px solid #fff;box-shadow:0 0 0 1px var(--hair2),0 0 0 5px rgba(0,113,227,.15)}
.sr-dot.sA{width:12px;height:12px;background:var(--green-d);border:2px solid #fff;box-shadow:0 0 0 1px rgba(31,157,77,.5)}
.sr-dot.rA{width:12px;height:12px;background:var(--red-d);border:2px solid #fff;box-shadow:0 0 0 1px rgba(215,0,21,.5)}
.sr-dot.sB{width:11px;height:11px;background:#fff;border:2px dashed var(--green-d)}
.sr-dot.rB{width:11px;height:11px;background:#fff;border:2px dashed var(--red-d)}
.sr-dot.sC{width:9px;height:9px;background:#fff;border:2px solid rgba(31,157,77,.45)}
.sr-dot.rC{width:9px;height:9px;background:#fff;border:2px solid rgba(215,0,21,.45)}
.sr-list{display:grid;grid-template-columns:1fr 1fr;gap:4px 14px;font-size:13px;line-height:1.5}
.sr-list .row{display:flex;justify-content:space-between;gap:8px;border-bottom:1px solid var(--hair);padding:3px 0;font-family:var(--font-mono)}
.sr-list .row .m{font-family:var(--font-base);color:var(--sub2);font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sr-list .row .v{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:none}
.sr-list .row.s .v{color:var(--green-d);font-weight:600}
.sr-list .row.r .v{color:var(--red-d);font-weight:600}
/* 三色块（块内进度条：现价在对应段内的位置） */
.v3-blocks{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:10px}
.v3b{border-radius:8px;padding:12px 8px;text-align:center;border:1px solid;min-width:0}
.v3b .k{font-size:12px;color:var(--sub2);letter-spacing:.03em;line-height:1.5;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.v3b .v{font-size:22px;font-weight:600;font-family:var(--font-mono);font-variant-numeric:tabular-nums;line-height:1.3}
.v3b .f{font-size:12px;color:var(--sub2);margin-top:2px;line-height:1.5;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.v3b .pbar{height:3px;border-radius:2px;background:rgba(128,128,132,.15);margin-top:6px;overflow:hidden}
.v3b .pbar i{display:block;height:100%;border-radius:2px;transition:width .3s ease}
.v3b.low{background:rgba(52,199,89,.07);border-color:rgba(52,199,89,.35)}.v3b.low .v{color:var(--green-d)}
.v3b.low .pbar i{background:var(--green-d)}
.v3b.mid{background:rgba(0,113,227,.06);border-color:rgba(0,113,227,.3)}.v3b.mid .v{color:var(--blue)}
.v3b.mid .pbar i{background:var(--blue)}
.v3b.high{background:rgba(175,82,222,.06);border-color:rgba(175,82,222,.3)}.v3b.high .v{color:#8940ab}
.v3b.high .pbar i{background:#8940ab}
/* 阶梯瀑布 */
.wfall{display:flex;flex-direction:column;gap:2px;font-size:13px;line-height:1.5}
.wfall .step{display:flex;justify-content:space-between;align-items:center;border-radius:6px;padding:4px 8px;font-family:var(--font-mono);gap:6px}
.wfall .step .lab{font-family:var(--font-base);color:var(--sub2);font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
.wfall .step > span:last-child{white-space:nowrap;flex:none}
.wfall .step.buy{background:var(--color-support-bg);border-left:3px solid var(--green)}
.wfall .step.buy.touched{background:rgba(52,199,89,.16);font-weight:700;color:var(--green-d)}
.wfall .step.sell{background:var(--color-resist-bg);border-left:3px solid var(--red)}
.wfall .step.sell.touched{background:rgba(255,59,48,.14);font-weight:700;color:var(--red-d)}
.wfall .divider{display:flex;justify-content:space-between;padding:4px 10px;background:var(--blue-lt);
  border-radius:6px;font-weight:700;color:var(--blue);font-family:var(--font-mono)}
.wfall .step .st{font-family:var(--font-base);font-size:12px;color:var(--meta);margin-left:8px}
.kelly-line{margin-top:8px;padding:6px 10px;border-radius:6px;background:var(--hair);
  font-size:12px;color:var(--sub2);font-family:var(--font-mono);overflow-x:auto;white-space:nowrap;line-height:1.6}
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
/* 质检列表（20px 图标列 + 自适应文字列；警告/阻断左边框高亮） */
.checks{font-size:12px;line-height:1.6}
.checks .row{display:grid;grid-template-columns:20px 1fr;gap:8px;padding:4px 0;border-bottom:1px solid var(--hair);align-items:baseline}
.checks .row.warn{border-left:3px solid var(--gold);padding-left:6px}
.checks .row.block{border-left:3px solid var(--red-d);padding-left:6px}
.checks .ic{flex:none;font-weight:700;font-size:12px}
.checks .row.block .ic{color:var(--red-d)}.checks .row.warn .ic{color:var(--gold)}.checks .row.pass .ic{color:var(--green-d)}
.checks .row .tx{color:var(--sub2);min-width:0;overflow-wrap:break-word}
.warn-line{font-size:12px;color:var(--gold);line-height:1.6;margin-top:6px}
.blocker-line{font-size:12px;color:var(--red-d);line-height:1.6;margin-top:6px}
.jumbo{font-size:22px;font-weight:600;font-family:var(--font-mono);font-variant-numeric:tabular-nums;line-height:1.3}
.jumbo.green{color:var(--green-d)}.jumbo.blue{color:var(--blue)}.jumbo.red{color:var(--red-d)}
.micro-row{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;border-top:1px solid var(--hair);padding-top:10px}
.micro{min-width:0}
.micro .k{font-size:12px;color:var(--sub2);letter-spacing:.02em;line-height:1.5}
.micro .v{font-size:16px;font-weight:600;font-family:var(--font-mono);font-variant-numeric:tabular-nums;margin-top:3px;line-height:1.4}
.micro .m{font-size:12px;color:var(--meta);margin-top:2px;line-height:1.5}
.formula-mini{font-size:12px;color:var(--sub2);margin-top:8px;border-top:1px solid var(--hair);padding-top:8px;line-height:1.7}
.calc-body .row{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:8px}
.sens-btn-row{margin:10px 0 4px}
.sens-btn{width:100%;padding:7px 12px;border-radius:8px;border:1px solid rgba(0,113,227,.35);background:rgba(0,113,227,.08);
  color:var(--blue);font-size:13px;font-weight:600;cursor:pointer;transition:background .15s}
.sens-btn:hover{background:rgba(0,113,227,.16)}
.sens-v{font-size:12px;color:var(--sub2);margin-top:2px;font-family:var(--font-mono)}
.calc-body label{font-size:12px;color:var(--sub2);display:block;margin-bottom:3px;line-height:1.5}
.calc-body input{width:100%;border:1px solid var(--hair);border-radius:5px;padding:5px 7px;font-size:13px;
  font-family:var(--font-mono)}
.calc-out{font-size:13px;line-height:1.8;font-family:var(--font-mono);border-top:1px solid var(--hair);padding-top:8px}
.pos-legend{display:flex;gap:12px;flex-wrap:wrap;font-size:12px;color:var(--sub2);margin-top:8px;line-height:1.5}
.pos-legend b{font-family:var(--font-mono);font-weight:600;color:var(--ink)}
.trigger-line{font-size:12px;color:var(--sub2);margin-top:8px;border-top:1px solid var(--hair);padding-top:8px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:1.5}

/* ---- 数据墙容器查询：窄墙时降级为单列/纵向（以墙宽为准，非视口） ---- */
@container (max-width:360px){
  .sr-list{grid-template-columns:1fr}
  .v3-blocks{grid-template-columns:1fr}
  .micro-row{grid-template-columns:1fr}
  .calc-body .row{grid-template-columns:1fr}
  .gauge-wrap{flex-direction:column;align-items:flex-start;gap:6px}
  .wfall .step{padding:4px 8px}
  .badge-wall{flex-direction:column;align-items:flex-start}
}
@container (min-width:401px){
  .v3-blocks{grid-template-columns:repeat(3,1fr)}
  .sr-list{grid-template-columns:1fr 1fr}
}

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
.src-link{color:var(--blue);text-decoration:none;border-bottom:1px dashed rgba(0,113,227,.4);margin-right:8px}
.src-link:hover{color:#005bb8;border-bottom-style:solid}
.src-badge{display:inline-block;font-size:12px;border:1px solid var(--hair);border-radius:999px;
  padding:2px 10px;color:var(--sub2);margin:4px 4px 0 0;line-height:1.5}

/* ============ 响应式 ============ */
@media(min-width:1601px){
  /* 大屏：侧栏 14vw，数据墙 300px，K线主画布占满 */
  .shell{grid-template-columns:14vw minmax(0,1fr) 8px 300px}
  body.wall-hidden .shell{grid-template-columns:14vw minmax(0,1fr) 0 0}
}
@media(min-width:1400px) and (max-width:1600px){
  .shell{grid-template-columns:minmax(200px,14vw) minmax(0,1fr) 8px 300px}
  body.wall-hidden .shell{grid-template-columns:minmax(200px,14vw) minmax(0,1fr) 0 0}
}
@media(max-width:1399px){
  .shell{grid-template-columns:minmax(200px,14vw) minmax(0,1fr) 8px var(--wall-w,340px)}
  body.wall-hidden .shell{grid-template-columns:minmax(200px,14vw) minmax(0,1fr) 0 0}
  .sb-hd span:last-child,.sb-search{display:none}
  .sb-item{padding:10px 6px 12px;gap:3px}
  .sb-item .nm,.sb-item .cd,.sb-item .px{display:none}   /* 保持原产品决策：窄屏隐藏价格与名称 */
  .sb-item .code{display:block;font-family:var(--font-mono);font-size:12px;text-align:center;width:100%}
  .sb-row-top,.sb-row-btm{justify-content:center;gap:4px}
  .sb-row-btm{flex-wrap:wrap;gap:1px 4px}   /* 84px 内涨跌/估值换行堆叠，避免截断 */
  .sb-change-group .chg{font-size:11px}
  .sb-zone-group .sb-zone{font-size:11px}
  .sb-item .bar{left:6px;right:6px}
}
@media(max-width:1099px){
  html,body{overflow:auto}
  .shell{grid-template-columns:1fr;grid-template-rows:auto;height:auto;display:block}
  body.wall-hidden .shell{grid-template-columns:1fr;grid-template-rows:auto;height:auto;display:block}
  body.wall-hidden .wall{width:auto;min-width:0;max-width:none;overflow:visible;padding:10px;border-left:none;display:block}
  .wall-toggle-btn{display:none}   /* 数据墙在下方非右侧，收起无意义 */
  .wall-grip{display:none}
  .mos-track{display:none}   /* 窄屏省 hero-strip 垂直空间 */
  .sidebar{border-right:none;border-bottom:1px solid var(--hair)}
  .sb-list{display:flex;overflow-x:auto;flex:none}
  .sb-item{min-width:120px;border-right:1px solid var(--hair);border-bottom:none}
  .center{min-height:0}
  .chart-zone{height:auto;min-height:45vh;position:sticky;top:0;z-index:10;background:var(--bg2);border-bottom:1px solid var(--hair)}
  .chart-wrap{min-height:220px}
  .hero-strip .hr{margin-left:0}
  /* 平板：图表/数据墙 Tab 切换（默认图表；数据墙为独立视图） */
  .tablet-tabs{display:inline-flex;gap:4px;margin-left:auto}
  .tablet-tabs .tab{border:1px solid var(--hair);background:var(--bg2);color:var(--sub2);font-size:12px;font-weight:600;
    border-radius:6px;padding:5px 12px;transition:all var(--dur-instant) var(--ease-instant);line-height:1.5}
  .tablet-tabs .tab:hover{border-color:var(--blue);color:var(--blue)}
  .tablet-tabs .tab.on{background:var(--blue-lt);color:var(--blue);border-color:rgba(0,113,227,.35)}
  body.tablet-wall .chart-zone{display:none}
  body.tablet-wall .wall{display:block;position:sticky;top:0;min-height:70vh}
  .wall{display:flex;flex-direction:row;overflow-x:auto;overflow-y:hidden;align-items:stretch;padding:8px;gap:12px;
    min-width:0;max-width:none;width:auto}
  .wall-ctrl{position:static;margin:0 0 8px;flex:none;width:100%;min-width:280px}
  .w-card{min-width:300px;flex:1 0 300px;max-width:420px;height:420px;margin-bottom:0;
    grid-template-rows:auto 1fr;overflow:hidden}
  .w-card.collapsed{grid-template-rows:auto 1fr}
  .w-card .w-body{overflow-y:auto}
  .popover{left:6px;right:6px;width:auto}
}
@media(max-width:767px){
  /* 移动：hero 堆叠 + 数据墙底部 Sheet（手势优先） */
  .tablet-tabs{display:none}
  .hero-strip{flex-direction:column;align-items:stretch;gap:8px;padding:10px 14px}
  .hero-strip .hl{width:100%}
  .hero-strip .hr{margin-left:0;text-align:left;min-width:0;width:100%}
  .hero-strip h1{font-size:20px}
  .hero-strip .price{font-size:26px}
  .sr-lbl{display:none}   /* 触摸屏取消轨道文字标签，保留✦星标 */
  .wall{display:flex;flex-direction:column;overflow:visible}
  .wall-ctrl{min-width:0}
  .w-card{min-width:0;max-width:none;height:auto;flex:none}
  .w-card .w-body{overflow:hidden}
  .jumbo,.v3b .v{font-size:20px}
}
@media(max-width:640px){
  .v3-blocks{grid-template-columns:1fr}
  .sr-list{grid-template-columns:1fr}
  .micro-row{grid-template-columns:1fr}
  .top-upd{display:none}
  .top-gate{max-width:130px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
  .stock-trig{max-width:150px}
  .stock-trig .px-block{display:none}   /* 极窄屏隐藏价格块，保住名称 */
}
</style>
</head>
<body>

<header class="topbar">
  <button class="brand" onclick="showTab('overview')"><i></i>估值雷达</button>
  <div class="top-tabs">
    <button class="tab on" id="tabOverview" onclick="showTab('overview')">大盘总览</button>
    <button class="tab" id="tabStock" onclick="showTab('stock')">个股估值</button>
  </div>
  <button class="stock-trig" id="stockTrig" onclick="togglePop()">
    <span class="nm" id="trigName">—</span>
    <span class="px-block" id="trigPx">—</span>
    <span class="arr">▾</span>
  </button>
  <div class="top-gate"><span class="dot" id="gateDot"></span><span id="gateTxt">市场数据加载中…</span></div>
  <div class="top-upd">更新 <span id="updAt">—</span>
    <span class="micro-date" id="dataDateBadge">数据 <b id="dataDate">—</b></span>
  </div>
  <button class="wall-toggle-btn" id="wallToggle" onclick="toggleWallHidden()" title="收起/显示右侧数据墙，K线图占满">⮜ 收起右侧</button>
  <div class="popover" id="popover">
    <input class="pop-search" id="popSearch" placeholder="搜索代码 / 名称…（Ctrl+K，↑↓ 选择，Enter 确认）" oninput="filterPop(this.value)">
    <div class="pop-list" id="popList"></div>
  </div>
</header>

<div class="shell" id="shellMain">
  <aside class="sidebar">
    <div class="sb-hd"><span>自选池</span><span id="sbCnt">0</span></div>
    <input class="sb-search" id="sbSearch" placeholder="搜索…" oninput="filterList(this.value)">
    <div class="sb-sectors" id="sbSectors"></div>
    <div class="sb-list" id="sbList"></div>
  </aside>

  <main class="center" id="center">
    <div class="hero-strip" id="heroStrip">
      <div class="edge-alert" id="edgeAlert" role="status" aria-live="polite"></div>
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
          <div class="mos-marker">
            <div class="mos-val" id="mosVal">—</div>
            <div class="mos-dot" id="mosDot" style="left:50%"></div>
          </div>
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
          <button class="ma-chip on" data-ma="5"><i style="background:var(--blue)"></i>MA5</button>
          <button class="ma-chip on" data-ma="10"><i style="background:var(--violet)"></i>MA10</button>
          <button class="ma-chip on" data-ma="20"><i style="background:var(--gold)"></i>MA20</button>
          <button class="ma-chip on" data-ma="60"><i style="background:var(--sub)"></i>MA60</button>
          <button class="ma-chip on" data-ma="120"><i style="background:var(--violet)"></i>MA120</button>
          <button class="ma-chip on" data-ma="250"><i style="background:var(--green)"></i>MA250</button>
          <button class="ma-chip on" id="bandChip" title="显隐 V_low/V_mid/V_high 估值色带与锚线"><i style="background:rgba(0,113,227,.55)"></i>估值带</button>
          <button class="ma-chip" id="hollowChip" title="色觉友好：上涨空心/下跌实心，颜色+形状双区分"><i style="background:#d94a47"></i>空心/实心</button>
        </div>
        <div class="tablet-tabs" id="tabletTabs" role="tablist">
          <button class="tab on" id="ttChart" onclick="tabletTab('chart')">图表</button>
          <button class="tab" id="ttWall" onclick="tabletTab('wall')">数据墙</button>
        </div>
      </div>
      <div class="chart-wrap" id="chartWrap">
        <canvas id="klineCv"></canvas>
        <div class="axis-panel" id="axisPanel" aria-hidden="true"></div>
        <svg id="klineSvg" role="img" aria-label="K线估值主图"></svg>
        <div class="ktip" id="chartTip"></div>
        <div class="visually-hidden" id="chartLive" aria-live="polite" aria-atomic="true"></div>
      </div>
      <div class="chart-foot">
        <span class="legend-mini"><i style="background:rgba(52,199,89,.45)"></i>低估区</span>
        <span class="legend-mini"><i style="background:rgba(0,113,227,.4)"></i>合理区</span>
        <span class="legend-mini"><i style="background:rgba(255,59,48,.45)"></i>高估区</span>
        <span class="legend-mini"><i style="background:var(--color-support)"></i>支撑 S</span>
        <span class="legend-mini"><i style="background:var(--color-resist)"></i>压力 R</span>
        <span class="legend-mini"><i style="background:#a0742f"></i>斐波那契回撤</span>
        <span class="legend-mini"><i style="background:var(--candle-up)"></i>上涨</span>
        <span class="legend-mini"><i style="background:var(--candle-dn)"></i>下跌</span>
        <div class="srfoot" id="srFoot" title="点击定位到对应价格"></div>
      </div>
    </div>
  </main>

  <div class="wall-grip" id="wallGrip" title="拖拽调整右栏宽度"></div>

  <aside class="wall" id="wall">
    <div class="wall-ctrl">
      <button class="w-ctrl-btn" id="wallToggleAll" onclick="toggleAllFold()">全部折叠 ▾</button>
      <span class="w-ctrl-cnt" id="wallCnt">—</span>
    </div>
    <div class="w-card" data-wid="c0"><div class="w-title"><span>关键价位 · 支撑压力</span><span class="w-micro" id="c0Micro">—</span><button class="w-fold" title="折叠/展开" onclick="toggleCardFold('c0',event)">▾</button></div><div class="w-body" id="c0Body">—</div></div>
    <div class="w-card" data-wid="c1"><div class="w-title"><span>Step 1 · 市场与模型</span><span class="w-micro" id="c1Micro">—</span><button class="w-fold" title="折叠/展开" onclick="toggleCardFold('c1',event)">▾</button></div><div class="w-body" id="c1Body">—</div></div>
    <div class="w-card" data-wid="c2"><div class="w-title"><span>Step 2 · 三档估值</span><span class="w-micro" id="c2Micro">—</span><button class="w-fold" title="折叠/展开" onclick="toggleCardFold('c2',event)">▾</button></div><div class="w-body" id="c2Body">—</div><div class="src-foot" id="c2Src">—</div></div>
    <div class="w-card" data-wid="c3"><div class="w-title"><span>Step 3 · 买卖阶梯</span><span class="w-micro" id="c3Micro">—</span><button class="w-fold" title="折叠/展开" onclick="toggleCardFold('c3',event)">▾</button></div><div class="w-body" id="c3Body">—</div></div>
    <div class="w-card" data-wid="c4"><div class="w-title"><span>Step 4 · 技术择时</span><span class="w-micro" id="c4Micro">—</span><button class="w-fold" title="折叠/展开" onclick="toggleCardFold('c4',event)">▾</button></div><div class="w-body" id="c4Body">—</div></div>
    <div class="w-card" data-wid="c5"><div class="w-title"><span>Step 5 · 仓位管理</span><span class="w-micro" id="c5Micro">—</span><button class="w-fold" title="折叠/展开" onclick="toggleCardFold('c5',event)">▾</button></div><div class="w-body" id="c5Body">—</div></div>
    <div class="w-card" data-wid="c6"><div class="w-title"><span>Step 6 · 数据依据</span><span class="w-micro" id="c6Micro">—</span><button class="w-fold" title="折叠/展开" onclick="toggleCardFold('c6',event)">▾</button></div><div class="w-body" id="c6Body">—</div></div>
  </aside>
</div>

<div class="ov-wrap" id="ovWrap" style="display:none">
  <div class="ov-cards">
    <div class="w-card"><div class="w-title"><span>第一层 · 大盘环境</span><span class="sp">趋势判定 + 估值背景</span></div><div class="w-body" id="ovMarket">—</div></div>
    <div class="w-card"><div class="w-title"><span>第二层 · 板块强弱</span><span class="sp">同花顺 90 真实行业板块</span></div><div class="w-body" id="ovSectors">—</div></div>
  </div>
  <div class="w-card"><div class="w-title"><span>自选池板块</span><span class="sp">研究分组聚合 · 点击成员进入个股估值</span></div><div class="w-body" id="ovMySectors">—</div></div>
  <div class="w-card"><div class="w-title"><span>第三层 · 全市场趋势筛选</span><span class="sp">全A 5000+ 只 · 每类前10 · 可分自选/非自选</span></div><div class="w-body" id="ovScreenAll">—</div></div>
  <div class="w-card"><div class="w-title"><span>自选池趋势筛选</span><span class="sp">精确 5/10/20日分类（19 只）</span></div><div class="w-body" id="ovScreen">—</div></div>
  <div class="w-card"><div class="w-title"><span>全池总览</span><span class="sp">点击行进入个股估值</span></div><div class="w-body"><table class="ov-table" id="ovTable"></table></div></div>
</div>

<div class="mask" id="mask" onclick="if(event.target===this)closeModal()">  <div class="modal">
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
let CUR = null;
let VIEW = 'stock';
let POP_IDX = -1;
const PREV = { price:null, pct:null, vLow:null, vMid:null, vHigh:null, base:null };

/* ============ 工具 ============ */
const fmt2 = v => v==null ? '—' : (+v).toLocaleString('zh-CN',{maximumFractionDigits:2});
/* 估值带位置：双段线性映射（以 V_mid 为 50% 视觉轴心，避免右偏倍数带线性映射失真）
   P<=mid: 0.5×(P-low)/(mid-low)；P>mid: 0.5+0.5×(P-mid)/(high-mid)。返回 null=无有效区间。 */
function bandPosRaw(p, lo, mid, hi){
  if(lo==null || hi==null || !isFinite(+lo) || !isFinite(+hi) || !(hi>lo)) return null;
  if(mid==null || !isFinite(+mid)) return (p-lo)/(hi-lo);
  if(p<=mid) return mid>lo ? 0.5*(p-lo)/(mid-lo) : 0.5;
  return 0.5 + (hi>mid ? 0.5*(p-mid)/(hi-mid) : 0);
}
function bandPosPct(p, lo, mid, hi){
  const r = bandPosRaw(p, lo, mid, hi);
  return r==null ? 50 : Math.max(0, Math.min(100, r*100));
}
const fmt0 = v => v==null ? '—' : (+v).toLocaleString('zh-CN',{maximumFractionDigits:0});
const pctCol = p => p > 0 ? 'up-c' : (p < 0 ? 'dn-c' : '');
const csym = st => ((st && st.currency === 'HKD') ? 'HK$' : '\u00a5');
const phDetail = ph => ph && ph.ok ? ((ph.metric||'PE') + ' ' + (ph.pe!=null?fmt2(ph.pe):'—') + (ph.pe_min!=null?' · 5年区间 '+fmt2(ph.pe_min)+'~'+fmt2(ph.pe_max):'') + (ph.source?' · '+ph.source:'')) : '—';
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

/* ============ 左导航列表（按板块分组）============ */
let SEC_FILTER = '全部';
function sectorMeta(k){ return (DATA.sectors||[]).find(s => s.key === k) || null; }
function sectorKeys(){
  const declared = (DATA.sectors||[]).map(s => s.key).filter((k,i,a) => k && a.indexOf(k) === i);
  const used = DATA.stocks.map(s => s.sector || '未分组').filter((k,i,a) => a.indexOf(k) === i);
  return ['全部'].concat(declared, used.filter(k => declared.indexOf(k) < 0));
}
function renderSbSectors(){
  const el = document.getElementById('sbSectors');
  if(!el) return;
  el.innerHTML = sectorKeys().map(k =>
    '<button class="sb-sec'+(SEC_FILTER===k?' on':'')+'" onclick="setSecFilter(\''+k+'\')">'+k+'</button>'
  ).join('');
}
function setSecFilter(k){
  SEC_FILTER = (SEC_FILTER === k && k !== '全部') ? '全部' : k;
  renderSbSectors(); renderList();
}
function sectorGroups(filter){
  const q = (filter||'').trim().toLowerCase();
  const list = DATA.stocks.filter(s => !q || s.name.toLowerCase().includes(q) || s.ticker.includes(q))
    .filter(s => SEC_FILTER === '全部' || (s.sector || '未分组') === SEC_FILTER);
  const map = {};
  list.forEach(s => { const k = s.sector || '未分组'; (map[k] = map[k] || []).push(s); });
  const order = (DATA.sectors||[]).map(s => s.key);
  const keys = order.filter(k => map[k] && map[k].length);
  Object.keys(map).forEach(k => { if(keys.indexOf(k) < 0) keys.push(k); });
  return keys.map(k => ({ key: k, items: map[k], focus: !!(sectorMeta(k) || {}).focus }));
}
function renderList(filter){
  const el = document.getElementById('sbList');
  const groups = sectorGroups(filter);
  el.innerHTML = groups.map(g => {
      const meta = sectorMeta(g.key);
      const tip = meta && meta.note ? ' title="' + String(meta.note).replace(/"/g, '') + '"' : '';
      return '<div class="sb-grp'+(g.focus?' focus':'')+'"'+tip+'><span>'+g.key+'</span>'
             + '<span class="n">'+g.items.length+'</span></div>'
             + g.items.map(s => {
      const zm = zmeta(s);
      const zc = ['z0','z0','z2','z2','z4','z4','z6'][zm.c] || 'z6';
      const rawPos = bandPosPct(s.price, s.v_low, s.v_mid, s.v_high);
      const barTitle = (s.v_low!=null && s.v_high!=null && s.v_high>s.v_low)
        ? '估值带位置 ' + rawPos.toFixed(0) + '%（' + fmt2(s.v_low) + ' ~ ' + fmt2(s.v_high) + '）'
        : '无估值区间';
      return '<button class="sb-item '+(s.ticker===CUR?.ticker&&VIEW==='stock'?'on':'')+'" onclick="switchStock(\''+s.ticker+'\')">'
        + '<div class="sb-row-top">'
        + '<div class="sb-name-group"><span class="nm">'+s.name+'</span><span class="cd">'+s.ticker+'</span><span class="code">'+s.ticker+'</span></div>'
        + '<div class="sb-price-group"><span class="px">'+csym(s)+fmt2(s.price)+'</span></div>'
        + '</div>'
        + '<div class="sb-row-btm">'
        + '<div class="sb-change-group"><span class="chg '+pctCol(s.pct)+'">'+(s.pct>0?'+':'')+fmt2(s.pct)+'%</span></div>'
        + '<div class="sb-zone-group"><span class="sb-zone '+zc+'">'+zm.label+'</span></div>'
        + '</div>'
        + '<div class="bar" title="'+barTitle+'"><span class="mark" style="left:'+rawPos+'%"></span></div>'
        + '</button>';
    }).join('');
  }).join('');
  const n = groups.reduce((a, g) => a + g.items.length, 0);
  document.getElementById('sbCnt').textContent = n + ' 只';
}
function filterList(v){ renderList(v); }

/* ============ 自选池板块聚合（大盘页）============ */
function secStat(items){
  let sum = 0, up = 0, dn = 0, flat = 0, bp = [], pp = [], zones = {};
  items.forEach(s => {
    if(typeof s.pct === 'number' && isFinite(s.pct)){ sum += s.pct; if(s.pct > 0) up++; else if(s.pct < 0) dn++; else flat++; }
    const zm = zmeta(s);
    zones[zm.label] = (zones[zm.label] || 0) + 1;
    if(s.decision_usable && s.band_pos_raw != null) bp.push(s.band_pos_raw);
    const ph = (DATA.pe_history||{})[s.ticker];
    if(ph && ph.ok && ph.pctile != null) pp.push(ph.pctile);
  });
  const avg = xs => xs.length ? xs.reduce((a,b) => a+b, 0) / xs.length : null;
  return { n: items.length, chg: items.length ? sum / items.length : null, up, dn, flat,
           bpAvg: avg(bp), bpN: bp.length, ppAvg: avg(pp), ppN: pp.length, zones };
}
function secVerdict(st){
  if(st.bpAvg != null){
    const p = st.bpAvg;
    return { text: p < 0.25 ? '板块整体处估值带下沿（偏低）' : p < 0.5 ? '板块整体合理偏低' :
                   p < 0.75 ? '板块整体合理偏高' : '板块整体处估值带上沿（偏高）',
             col: p < 0.25 ? 'var(--green-d)' : p < 0.5 ? 'var(--green-d)' :
                  p < 0.75 ? 'var(--gold)' : 'var(--red-d)' };
  }
  if(st.ppAvg != null){
    const p = st.ppAvg;
    return { text: p < 0.3 ? '板块 PE 历史分位偏低' : p <= 0.7 ? '板块 PE 历史分位居中' : '板块 PE 历史分位偏高',
             col: p < 0.3 ? 'var(--green-d)' : p <= 0.7 ? 'var(--gold)' : 'var(--red-d)' };
  }
  return { text: '板块内无可用估值锚，按分位与质量门逐只判断', col: 'var(--sub2)' };
}
function renderMySectors(){
  const el = document.getElementById('ovMySectors');
  if(!el) return;
  const groups = sectorGroups();
  if(!groups.length){ el.innerHTML = '<div class="formula-mini">暂无板块数据。</div>'; return; }
  el.innerHTML = (DATA.sector_note ? '<div class="formula-mini" style="border:none;padding:0;margin-bottom:8px">'
      + DATA.sector_note + '</div>' : '')
    + '<div class="my-sec-grid">' + groups.map(g => {
      const meta = sectorMeta(g.key) || {};
      const st = secStat(g.items);
      const vd = secVerdict(st);
      const zs = Object.keys(st.zones).sort((a,b) => st.zones[b] - st.zones[a])
        .map(k => k + ' ' + st.zones[k]).join(' / ');
      const cChg = st.chg != null ? pctCol(st.chg) : '';
      return '<div class="my-sec'+(meta.focus?' focus':'')+'">'
        + '<div class="my-sec-hd"><span class="my-sec-nm">'+g.key
        + (meta.focus ? '<span class="tag">重点跟踪</span>' : '')
        + '</span><span class="my-sec-chg '+cChg+'">'+(st.chg != null ? (st.chg>0?'+':'')+st.chg.toFixed(2)+'%' : '—')+'</span></div>'
        + '<div class="my-sec-stat"><span>成员 '+st.n+'</span><span>涨 '+st.up+' / 跌 '+st.dn+'</span>'
        + (st.ppAvg != null ? '<span>平均 PE 分位 '+Math.round(st.ppAvg*100)+'%（'+st.ppN+'只）</span>' : '')
        + (st.bpAvg != null ? '<span>估值带位置 '+Math.round(st.bpAvg*100)+'%（'+st.bpN+'只决策级）</span>' : '')
        + '</div>'
        + '<div class="my-sec-note">'+(meta.note || '')+'<br><b style="color:'+vd.col+'">'+vd.text+'</b>｜状态分布：'+zs+'</div>'
        + g.items.slice().sort((a,b) => (b.pct||0) - (a.pct||0)).map(s => {
            const zm = zmeta(s);
            const col = (zm.c===0||zm.c===1) ? 'var(--green-d)' : (typeof zm.c === 'number' && zm.c>=4 ? 'var(--red-d)' : 'var(--sub2)');
            const epsLbl = s.forecast_basis === 'NTM' ? 'NTM EPS'
              : (s.forecast_basis === 'NORMALIZED' ? '正常化 EPS'
                 : ('FY' + (s.forecast_year || '') + ' EPS'));
            const why = s.v_low != null
              ? (s.decision_usable ? '估值带 ' : '参考带 ') + fmt2(s.v_low) + '~' + fmt2(s.v_high)
              : (s.eps_base != null ? epsLbl + ' ' + fmt2(s.eps_base) : (zm.label || '—'));
            return '<div class="my-sec-row" onclick="switchStock(\''+s.ticker+'\')" title="点击进入 '+s.name+' 估值">'
              + '<span class="m-nm">'+s.name+'<br><i>'+s.ticker+'</i></span>'
              + '<span class="m-px">'+csym(s)+fmt2(s.price)+'<br><i style="font-style:normal;color:'
              + (s.pct>0?'var(--candle-up)':(s.pct<0?'var(--candle-dn)':'var(--sub2)'))+'">'
              + (s.pct>0?'+':'')+fmt2(s.pct)+'%</i></span>'
              + '<span class="m-why">'+why+'</span>'
              + '<span class="m-st" style="color:'+col+'">'+zm.label+'</span>'
              + '</div>';
          }).join('')
        + '</div>';
    }).join('') + '</div>';
}

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
    '<button class="pop-item" onclick="showTab(\'overview\');togglePop()"><span class="nm">大盘总览（首页）</span><span class="st">市场 + 板块 + 全池</span></button>' +
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
  document.getElementById('gateTxt').textContent = '市场温度 ' + g.graham + ' · ' + g.band
    + (g.erp_pct!=null ? ' · ERP ' + g.erp_pct + '%' : '') + stale;
  document.getElementById('updAt').textContent = (DATA.updated_at||'').slice(5,16);
  document.getElementById('dataDate').textContent = DATA.data_date || '—';
}

/* ============ 双视图：大盘总览（首页封面） / 个股估值 ============ */
function setTabUI(name){
  const t1 = document.getElementById('tabOverview'), t2 = document.getElementById('tabStock');
  if(t1) t1.classList.toggle('on', name === 'overview');
  if(t2) t2.classList.toggle('on', name === 'stock');
}
function showTab(name){
  const shell = document.getElementById('shellMain');
  const ov = document.getElementById('ovWrap');
  if(name === 'overview'){
    VIEW = 'overview'; CUR = null;
    if(shell) shell.style.display = 'none';
    if(ov){ ov.style.display = 'block'; ov.style.height = 'calc(100vh - 38px)'; }
    renderOvMarket();
    renderOvSectors();
    renderMySectors();
    renderOvScreenAll();
    renderOvScreen();
    renderOvTable();
    renderList();
  } else {
    if(ov) ov.style.display = 'none';
    if(shell) shell.style.display = '';
    if(!CUR){
      const last = (() => { try{ return localStorage.getItem('radar_last'); }catch(e){ return null; } })();
      const st = DATA.stocks.find(s => s.ticker === last) || DATA.stocks[0];
      if(st) switchStock(st.ticker);
    }
  }
  setTabUI(name);
  try{ localStorage.setItem('radar_view', name); }catch(e){}
}

/* ============ 趋势筛选工作台（四层漏斗，不荐股只分类+原因） ============ */
function tsMa(closes, w, end){
  if(end == null) end = closes.length;
  if(end < w) return null;
  let s = 0;
  for(let i = end - w; i < end; i++) s += closes[i];
  return s / w;
}
function tsRet(closes, n){
  if(closes.length <= n || !(closes[closes.length-1-n] > 0)) return null;
  return (closes[closes.length-1] / closes[closes.length-1-n] - 1) * 100;
}
function tsAtr(rows){
  if(rows.length < 15) return null;
  let s = 0;
  for(let i = 1; i < 15; i++){
    const r = rows[rows.length - i], p = rows[rows.length - i - 1];
    s += Math.max(r.h - r.l, Math.abs(r.h - p.c), Math.abs(r.l - p.c));
  }
  return s / 14;
}
function tsScreen(st){
  const k = (st.kline||[]).filter(r => r && isFinite(+r.c));
  if(k.length < 40) return null;
  const closes = k.map(r => +r.c);
  const vols = k.map(r => +r.v);
  const price = closes[closes.length-1];
  const m20 = tsMa(closes, 20), m60 = tsMa(closes, 60);
  const m20Prev = tsMa(closes, 20, closes.length - 5);
  const r5 = tsRet(closes, 5), r10 = tsRet(closes, 10), r20 = tsRet(closes, 20);
  const v5 = vols.slice(-5).reduce((a,b)=>a+b,0) / 5;
  const v20 = vols.slice(-20).reduce((a,b)=>a+b,0) / 20;
  const vr = v20 > 0 ? v5 / v20 : null;
  const atr = tsAtr(k);
  const atrPct = atr && price > 0 ? atr / price * 100 : null;
  const hi250 = Math.max(...k.slice(-250).map(r => +r.h));
  const lo250 = Math.min(...k.slice(-250).map(r => +r.l));
  const pos250 = hi250 > lo250 ? (price - lo250) / (hi250 - lo250) * 100 : null;
  const dist20 = m20 ? (price / m20 - 1) * 100 : null;
  const m20Up = m20 != null && m20Prev != null && m20 > m20Prev;
  const dayChg = closes.length > 1 ? (closes[closes.length-1] / closes[closes.length-2] - 1) * 100 : null;
  let atrFlag = '';
  if(atrPct){
    if(dayChg != null && Math.abs(dayChg) > 2 * atrPct) atrFlag = '单日异动 ' + dayChg.toFixed(1) + '% > 2×ATR';
    else if(r5 != null && r5 > 2.5 * atrPct) atrFlag = '5日涨幅 ' + r5.toFixed(1) + '% > 2.5×ATR';
  }
  return {price, m20, m60, m20Up, r5, r10, r20, vr, atrPct, pos250, dist20, dayChg, atrFlag,
          above20: m20 != null && price > m20, m20g60: m20 != null && m60 != null && m20 > m60};
}

/* 第一层：大盘环境（市场宽度 + 上证指数趋势 + 市场估值背景） */
function renderOvMarket(){
  const el = document.getElementById('ovMarket');
  if(!el) return;
  const m = DATA.market;
  const ms = DATA.market_screen || {};
  const bd = ms.breadth || {};
  const idx = DATA.stocks.find(s => s.ticker === '000001');
  let head = '', evidence = [], envGrade = null, tech = '';
  if(idx){
    const d = tsScreen(idx);
    if(d){
      envGrade = (d.above20 && d.m20g60 && d.r20 != null && d.r20 > 2) ? '强'
        : ((!d.above20 || !d.m20g60) && d.r20 != null && d.r20 < 0) ? '偏弱' : '正常';
      evidence = ['上证 20日 ' + (d.r20!=null?(d.r20>=0?'+':'')+d.r20.toFixed(1)+'%':'—'),
                  '价 vs MA20 ' + (d.dist20!=null?(d.dist20>=0?'+':'')+d.dist20.toFixed(1)+'%':'—'),
                  'MA20 ' + (d.m20g60 ? '>' : '≤') + ' MA60',
                  '5日 ' + (d.r5!=null?(d.r5>=0?'+':'')+d.r5.toFixed(1)+'%':'—')];
      const tc = v => v!=null ? (v>=0?'up-c':'dn-c') : '';
      const tf = v => v!=null ? ((v>=0?'+':'')+v.toFixed(1)+'%') : '—';
      tech = '<div class="micro-row" style="border-top:none;padding-top:0">'
        + '<div class="micro"><div class="k">上证 5日</div><div class="v" style="font-size:14px;color:' + (d.r5>=0?'var(--green-d)':'var(--red-d)') + '">' + tf(d.r5) + '</div></div>'
        + '<div class="micro"><div class="k">上证 10日</div><div class="v" style="font-size:14px;color:' + (d.r10>=0?'var(--green-d)':'var(--red-d)') + '">' + tf(d.r10) + '</div></div>'
        + '<div class="micro"><div class="k">上证 20日</div><div class="v" style="font-size:14px;color:' + (d.r20>=0?'var(--green-d)':'var(--red-d)') + '">' + tf(d.r20) + '</div></div>'
        + '<div class="micro"><div class="k">上证 60日</div><div class="v" style="font-size:14px;color:' + (d.r60>=0?'var(--green-d)':'var(--red-d)') + '">' + tf(d.r60) + '</div></div>'
        + '<div class="micro"><div class="k">量比(5/20日)</div><div class="v" style="font-size:14px">' + (d.vr!=null?d.vr.toFixed(2):'—') + '</div></div>'
        + '<div class="micro"><div class="k">250日位置</div><div class="v" style="font-size:14px">' + (d.pos250!=null?d.pos250.toFixed(0)+'%':'—') + '</div></div>'
        + '<div class="micro"><div class="k">ATR(14日)</div><div class="v" style="font-size:14px">' + (d.atrPct!=null?d.atrPct.toFixed(1)+'%':'—') + '</div></div>'
        + '<div class="micro"><div class="k">MA排列</div><div class="v" style="font-size:14px;font-family:var(--font-base)">' + (d.m20g60?'多':'空') + '头</div></div>'
        + '</div>';
    }
  }
  const g = (m.graham_metrics||[]).find(x => x.key === 'cs985') || (m.graham_metrics||[])[0] || {};
  const rows = (m.graham_metrics||[]).map(x =>
    '<tr><td>' + x.label + '</td><td>' + fmt2(x.pe) + '</td><td style="color:'
    + (x.graham>=2.3?'var(--green-d)':(x.graham>=1.8?'var(--gold)':'var(--red-d)')) + '">' + x.graham
    + '</td><td>' + (x.erp_pct!=null ? x.erp_pct + '%' : '—') + '</td><td>' + x.band + '</td></tr>').join('');
  const gCol = envGrade === '强' ? 'var(--green-d)' : (envGrade === '偏弱' ? 'var(--red-d)' : 'var(--blue)');
  const upCol = bd.up_ratio != null ? (bd.up_ratio >= 55 ? 'var(--green-d)' : (bd.up_ratio >= 40 ? 'var(--gold)' : 'var(--red-d)')) : 'var(--sub2)';
  /* 指数深度技术：全均线 + 250日高低 + 最新量能 */
  let depth = '';
  if(idx){
    const d = tsScreen(idx);
    const k = (idx.kline||[]).filter(r => r && isFinite(+r.c));
    const closes = k.map(r => +r.c);
    if(d && closes.length){
      const maV = [5,10,20,60,120,250].map(w => {
        const v = tsMa(closes, w);
        return {w, v, above: v != null && d.price >= v};
      }).filter(x => x.v != null);
      const maCell = x => '<div class="micro"><div class="k">MA' + x.w + '</div><div class="v" style="font-size:13px;color:' + (x.above?'var(--green-d)':'var(--red-d)') + '">' + fmt2(x.v) + '</div></div>';
      const hi250 = Math.max(...k.slice(-250).map(r => +r.h));
      const lo250 = Math.min(...k.slice(-250).map(r => +r.l));
      const last = k[k.length-1];
      const amtTxt = last && last.v != null ? (last.v >= 1e8 ? (last.v/1e8).toFixed(0)+'亿' : (last.v/1e4).toFixed(0)+'万') : '—';
      depth = '<div class="micro-row" style="border-top:1px solid var(--hair);padding-top:8px">'
        + '<div class="micro"><div class="k">最新点位</div><div class="v" style="font-size:15px">' + fmt2(d.price) + '</div></div>'
        + '<div class="micro"><div class="k">当日涨跌</div><div class="v" style="font-size:15px;color:' + (d.chg>=0?'var(--green-d)':'var(--red-d)') + '">' + (d.chg!=null?(d.chg>=0?'+':'')+d.chg.toFixed(2)+'%':'—') + '</div></div>'
        + '<div class="micro"><div class="k">当日成交</div><div class="v" style="font-size:15px">' + amtTxt + '</div></div>'
        + '<div class="micro"><div class="k">250日高</div><div class="v" style="font-size:15px;color:var(--red-d)">' + fmt2(hi250) + '</div></div>'
        + '<div class="micro"><div class="k">250日低</div><div class="v" style="font-size:15px;color:var(--green-d)">' + fmt2(lo250) + '</div></div>'
        + '<div class="micro"><div class="k">距高点</div><div class="v" style="font-size:15px;color:var(--red-d)">' + (hi250>0?((d.price/hi250-1)*100).toFixed(1)+'%':'—') + '</div></div>'
        + '<div class="micro"><div class="k">距低点</div><div class="v" style="font-size:15px;color:var(--green-d)">' + (lo250>0?((d.price/lo250-1)*100).toFixed(1)+'%':'—') + '</div></div>'
        + '<div class="micro"><div class="k">5日量比</div><div class="v" style="font-size:15px">' + (d.vr!=null?d.vr.toFixed(2):'—') + '</div></div>'
        + '</div>'
        + '<div class="micro-row" style="border-top:1px solid var(--hair);padding-top:8px">' + maV.map(maCell).join('') + '</div>';
    }
  }
  /* 量能趋势对比：上证近 20 日成交额柱状图 + 5/20日均量 + 放缩量判定 */
  let volTrend = '';
  if(idx){
    const k = (idx.kline||[]).filter(r => r && isFinite(+r.c) && isFinite(+r.v));
    if(k.length >= 20){
      const win = k.slice(-20);
      const vs = win.map(r => +r.v);
      const vmax = Math.max(...vs);
      const v5 = vs.slice(-5).reduce((a,b)=>a+b,0) / 5;
      const v20 = vs.reduce((a,b)=>a+b,0) / 20;
      const vr = v20 > 0 ? v5 / v20 : null;
      const todayV = vs[vs.length-1];
      const verdict = vr == null ? '—' : (vr >= 1.2 ? '放量' : (vr <= 0.8 ? '缩量' : '平量'));
      const vCol = verdict === '放量' ? 'var(--red-d)' : (verdict === '缩量' ? 'var(--green-d)' : 'var(--gold)');
      const fmtV = x => x >= 1e8 ? (x/1e8).toFixed(1)+'亿' : (x/1e4).toFixed(0)+'万';
      const bars = win.map((r, i) => {
        const h = Math.max(3, vs[i] / vmax * 42);
        const up = +r.c >= +r.o;
        const col = up ? 'var(--candle-up)' : 'var(--candle-dn)';
        const isLast = i === win.length - 1;
        return '<div class="vb" title="' + r.d + ' 量 ' + fmtV(vs[i]) + '" style="height:' + h.toFixed(1) + 'px;background:' + col + ';' + (isLast?'opacity:1;':'opacity:.55') + '"></div>';
      }).join('');
      volTrend = '<div class="micro-row" style="border-top:1px solid var(--hair);padding-top:8px">'
        + '<div class="micro" style="grid-column:1/-1"><div class="k">量能趋势（上证近20日成交）· <b style="color:' + vCol + '">' + verdict + ' ' + (vr!=null?vr.toFixed(2)+'×':'—') + '</b></div>'
        + '<div class="vol-bars">' + bars + '</div>'
        + '<div class="vol-meta">今日 ' + fmtV(todayV) + '｜5日均 ' + fmtV(v5) + '｜20日均 ' + fmtV(v20) + '｜量比 ' + (vr!=null?vr.toFixed(2):'—') + '（5日均/20日均，≥1.2 放量、≤0.8 缩量，D级）</div></div>'
        + '</div>';
    }
  }
  /* 今日强势/弱势板块方向（Top5） */
  const ss = DATA.sector_strength || {};
  const scls = ss.classes || {};
  const strong = (scls['持续强势']||[]).slice(0,5);
  const weak = ((scls['走弱/观望']||[]).slice()).sort((a,b) => (a.r20==null?0:a.r20) - (b.r20==null?0:b.r20)).slice(0,5);
  const dirHTML = (strong.length || weak.length ?
    '<div class="micro-row" style="border-top:1px solid var(--hair);padding-top:8px">'
    + '<div class="micro" style="grid-column:1/-1"><div class="k" style="color:var(--green-d)">今日强势方向（20日涨幅前5板块）</div><div class="v" style="font-size:13px;font-family:var(--font-base);line-height:1.8">'
    + (strong.map(x => x.name + ' <b class="up-c">' + (x.r20!=null?('+' + x.r20.toFixed(1) + '%'):'—') + '</b>').join('　') || '—') + '</div></div>'
    + '<div class="micro" style="grid-column:1/-1"><div class="k" style="color:var(--red-d)">今日弱势方向（20日涨幅后5板块）</div><div class="v" style="font-size:13px;font-family:var(--font-base);line-height:1.8">'
    + (weak.map(x => x.name + ' <b class="dn-c">' + (x.r20!=null?('' + x.r20.toFixed(1) + '%'):'—') + '</b>').join('　') || '—') + '</div></div>'
    + '</div>'
    : '');
  const breadthHTML = (bd.total ? 
    '<div class="breadth-box">'
    + '<div class="b-line"><span class="b-lab">市场宽度</span>'
    + '<span class="b-num" style="color:var(--green-d)">涨 ' + bd.up + '</span>'
    + '<span class="b-num" style="color:var(--red-d)">跌 ' + bd.down + '</span>'
    + '<span class="b-num" style="color:var(--sub2)">平 ' + (bd.flat||0) + '</span>'
    + '<span class="b-num">涨停 ' + (bd.limit_up||0) + ' / 跌停 ' + (bd.limit_dn||0) + '</span>'
    + '<span class="b-num">中位涨幅 <b style="color:' + (bd.median_chg!=null && bd.median_chg>=0?'var(--green-d)':'var(--red-d)') + '">' + (bd.median_chg!=null?(bd.median_chg>=0?'+':'')+bd.median_chg.toFixed(2)+'%':'—') + '</b></span>'
    + '<span class="b-num">两市成交 <b style="color:var(--ink)">' + (bd.total_amount!=null?(bd.total_amount/1e4).toFixed(2)+'万亿':'—') + '</b></span></div>'
    + '<div class="b-bar"><i style="width:' + bd.up_ratio + '%;background:var(--green-d)"></i><i style="left:' + bd.up_ratio + '%;background:var(--red-d)"></i></div>'
    + '<div class="b-note" style="color:' + upCol + '">上涨占比 ' + bd.up_ratio + '%（' + (bd.up_ratio>=55?'普涨·环境偏强':bd.up_ratio>=40?'分化·中性':'普跌·环境偏弱') + '，全市场 ' + bd.total + ' 只）</div>'
    + '</div>'
    : '');
  /* 大盘拥挤度：当日现算值 + 乐咕历史极值对照（牛熊转换观察，仅标注） */
  const cg = ms.congestion || {};
  const cgHist = cg.history || {};
  let congestionHTML = '';
  if(cg.value != null){
    const v = +cg.value;
    const cgPos = x => Math.max(0, Math.min(100, (x - 30) / 30 * 100));  /* 映射 30%~60% → 0~100% */
    const cgStat = v >= 45 ? {t:'拥挤·历史警戒', c:'var(--red-d)'} : (v >= 40 ? {t:'集中上升·关注', c:'var(--gold)'} : {t:'分散·健康', c:'var(--green-d)'});
    const peaks = (cgHist.peaks||[]).slice(0, 7);
    const cgNote = v >= 45
      ? '成交高度集中于前5%个股，微观结构失衡。历史上 >45% 后多伴随剧烈震荡/热点切换（7轮极值后常阶段见顶），当前需警惕追高'
      : (v >= 40
        ? '交易集中度上升、局部过热风险显现，结构行情下资金抱团主线，留意风格切换'
        : '市场交易分散、微观结构健康，普涨/普跌特征，未现极端抱团');
    congestionHTML = '<div class="cong-box">'
      + '<div class="cong-line"><span class="cong-lab">大盘拥挤度</span>'
      + '<span class="cong-num">当前 <b style="color:' + cgStat.c + '">' + v.toFixed(2) + '%</b></span>'
      + '<span class="cong-num" style="color:' + cgStat.c + '">' + cgStat.t + '</span>'
      + '<span class="cong-num" style="color:var(--meta)">成交额前5% ' + (cg.top5_count||'—') + ' 只 / ' + (cg.total_count||'—') + ' 只（当日现算）</span></div>'
      + '<div class="cong-bar">'
      + '<span class="g" style="left:' + cgPos(40) + '%"></span>'
      + '<span class="g" style="left:' + cgPos(45) + '%"></span>'
      + '<span class="mk" style="left:' + cgPos(v) + '%"></span></div>'
      + '<div class="cong-labels"><span>30%</span><span>40% 关注</span><span>45% 警戒</span><span>60%</span></div>'
      + '<div class="b-note" style="color:' + cgStat.c + '">' + cgNote + '</div>'
      + (peaks.length ? '<div class="cong-peaks"><span style="color:var(--sub2)">历史极值（乐咕 ' + (cgHist.points||0) + ' 点 · ' + (cgHist.first_date||'—') + '~' + (cgHist.last_date||'—') + '）≥45% 前7轮：</span>'
          + peaks.map(p => '<span class="pk"><i></i><em>' + p.peak_date + '</em><b>' + p.peak.toFixed(1) + '%</b></span>').join('')
          + '</div>' : '')
      + '</div>';
  }
  head = '<div class="env-banner"><span class="env-badge" style="color:' + gCol + ';border-color:' + gCol + '">大盘环境：' + (envGrade || '—') + '</span>'
    + '<span class="env-ev">' + (evidence.join(' · ') || '指数K线不足') + '</span></div>'
    + breadthHTML
    + congestionHTML
    + tech
    + depth
    + volTrend
    + dirHTML
    + '<div class="formula-mini">大盘强弱 = 上证价 vs MA20 + MA20 vs MA60 + 20日涨幅（D级工程化）；市场宽度 = 全市场涨跌家数/涨停跌停/中位涨幅/两市成交额（新浪快照，当日）；大盘拥挤度 = 成交额前5%个股占全市场成交额比重（当日新浪现算 + 乐咕历史极值，牛熊转换观察，仅标注不构成仓位闸门）；强势/弱势方向 = 同花顺 90 板块 20日涨幅前/后 5。估值背景（格雷厄姆=' + (g.graham||'—') + ' ' + (g.band||'') + '，ERP=' + (g.erp_pct!=null?g.erp_pct+'%':'—') + '）：仅标注，不构成仓位闸门。</div>';
  el.innerHTML = head
    + '<table class="ov-table">'
    + '<tr><th>口径</th><th>PE(TTM)</th><th>格雷厄姆</th><th>ERP</th><th>分档</th></tr>' + rows
    + '</table>'
    + '<div class="formula-mini">10Y 国债 ' + fmt2(((m.bond_10y||{}).value||0)*100) + '%（' + ((m.bond_10y||{}).date||'—') + '）｜ 格雷厄姆 = (1/PE)÷10Y；ERP = 1/PE − 10Y（D级减法模型防低利率乘数失真）。</div>';
}

/* 第二层：真实行业板块强弱（同花顺 90 行业板块，非自选池） */
function renderOvSectors(){
  const el = document.getElementById('ovSectors');
  if(!el) return;
  const ss = DATA.sector_strength || {};
  const classes = ss.classes || {};
  const stats = ss.stats || {};
  const order = ['持续强势', '正在加强', '走弱/观望'];
  const col = {'持续强势':'var(--green-d)','正在加强':'var(--blue)','走弱/观望':'var(--sub2)'};
  const tot = order.reduce((a, g) => a + ((classes[g]||[]).length), 0);
  if(!tot){
    el.innerHTML = '<div class="formula-mini">暂无行业板块数据（每日收盘后自动生成）。</div>';
    return;
  }
  el.innerHTML = '<div class="formula-mini" style="border:none;padding:0;margin-bottom:6px">数据源：同花顺 90 个真实行业板块（涨跌幅/净流入/上涨家数/领涨股）+ 板块指数近 6 月历史计算 5/20 日涨幅（D级工程化）。更新 ' + (ss.updated_at||'—') + '｜ 仅筛选观察，不构成买卖建议。</div>'
    + order.map(g => {
      const items = classes[g] || [];
      if(!items.length) return '';
      return '<div class="ts-group"><div class="ts-head"><span class="ts-badge" style="color:' + col[g] + ';border-color:' + col[g] + '">' + g + ' ' + (stats.counts||{})[g] + ' 个板块</span><span class="ts-mean">' + (g==='持续强势'?'20日涨幅>0、当日上涨、上涨家数占比≥55%':g==='正在加强'?'20日涨幅>0、当日上涨或5日加速': '其余（20日走弱或当日回调）') + '</span></div>'
        + items.map(it => {
          const c0 = (it.chg||0) >= 0 ? 'up-c' : 'dn-c';
          const c5 = (it.r5||0) >= 0 ? 'up-c' : 'dn-c';
          const c20 = (it.r20||0) >= 0 ? 'up-c' : 'dn-c';
          const inflow = it.net_inflow;
          const ic = inflow != null ? (inflow >= 0 ? 'up-c' : 'dn-c') : '';
          return '<div class="sec-row" title="' + it.name + '：上涨 ' + (it.up_cnt!=null?it.up_cnt:'—') + ' / 下跌 ' + (it.dn_cnt!=null?it.dn_cnt:'—') + ' 家">'
            + '<span class="t-nm">' + it.name + '</span>'
            + '<span class="t-r"><b class="' + c0 + '">当日 ' + (it.chg!=null?(it.chg>=0?'+':'')+it.chg.toFixed(2)+'%':'—') + '</b><b class="' + c5 + '">5日 ' + (it.r5!=null?(it.r5>=0?'+':'')+it.r5.toFixed(1)+'%':'—') + '</b><b class="' + c20 + '">20日 ' + (it.r20!=null?(it.r20>=0?'+':'')+it.r20.toFixed(1)+'%':'—') + '</b></span>'
            + '<span class="t-m">上涨 ' + (it.up_cnt!=null?it.up_cnt:'—') + '/' + (it.dn_cnt!=null?it.dn_cnt:'—') + ' 家' + (it.up_ratio!=null?'（' + it.up_ratio.toFixed(0) + '%）':'') + (inflow!=null?'｜净流入 <b class="' + ic + '">' + (inflow>=0?'+':'') + (inflow/1e8).toFixed(1) + '亿</b>':'') + '</span>'
            + '<span class="t-why">领涨 ' + (it.leader||'—') + (it.leader_chg!=null?' <b class="' + (it.leader_chg>=0?'up-c':'dn-c') + '">' + (it.leader_chg>=0?'+':'') + it.leader_chg.toFixed(2) + '%</b>':'') + '</span>'
            + '</div>';
        }).join('') + '</div>';
    }).join('');
}

/* 第三层·全市场趋势筛选：全A 5000+ 只，每类前 10，可按自选/非自选过滤 */
let OV_SCREEN_FILTER = 'all';
function renderOvScreenAll(){
  const el = document.getElementById('ovScreenAll');
  if(!el) return;
  const ms = DATA.market_screen || {};
  const classes = ms.classes || {};
  const stats = ms.stats || {};
  const f = OV_SCREEN_FILTER;
  const tot = Object.values(classes).reduce((a, c) => a + (c||[]).length, 0);
  el.innerHTML =
    '<div class="filter-row"><span class="ts-mean">筛选口径：当日涨跌幅/量比 + 5/10/20/60日真实涨幅（新浪日K逐只计算）+ MA20/ATR/250日位置，粗筛成交额>8亿、剔除 ST/退市/北交所。仅状态分类与前10展示，<b>不构成买入建议</b>。</span>'
    + '<span class="f-tabs">'
    + '<button class="f-tab ' + (f==='all'?'on':'') + '" onclick="setScreenFilter(\'all\')">全部</button>'
    + '<button class="f-tab ' + (f==='watch'?'on':'') + '" onclick="setScreenFilter(\'watch\')">仅自选</button>'
    + '<button class="f-tab ' + (f==='other'?'on':'') + '" onclick="setScreenFilter(\'other\')">仅非自选</button>'
    + '</span></div>'
    + '<div class="formula-mini" style="border:none;padding:0;margin-bottom:4px">更新 ' + (ms.updated_at||'—') + '｜ 覆盖 ' + (stats.total||0) + ' 只活跃股（成交额>8亿）</div>'
    + (tot ? TS_ORDER.map(g => {
        const items = (classes[g]||[]).filter(it => f==='all' || (f==='watch' ? it.watch : !it.watch));
        if(!items.length) return '';
        const gCol = {'启动观察':'var(--blue)','趋势观察':'var(--green-d)','高位观察':'var(--red-d)','回调观察':'var(--gold)','排除':'var(--sub2)'}[g];
        return '<div class="ts-group"><div class="ts-head"><span class="ts-badge" style="color:' + gCol + ';border-color:' + gCol + '">' + g + ' ' + (stats.counts||{})[g] + '只 → 前' + items.length + '</span><span class="ts-mean">' + TS_MEAN[g] + '</span></div>'
          + items.map(it => {
            const c1 = (it.chg||0) >= 0 ? 'up-c' : 'dn-c';
            const c5 = (it.r5||0) >= 0 ? 'up-c' : 'dn-c';
            const c20 = (it.r20||0) >= 0 ? 'up-c' : 'dn-c';
            return '<div class="ts-row" onclick="switchStock(\'' + it.code + '\')" title="点击进入 ' + it.name + ' 估值">'
              + '<span class="t-nm">' + (it.watch?'★':'') + it.name + '<i>' + it.code + (it.watch?' · 自选':'') + '</i></span>'
              + '<span class="t-r"><b class="' + c1 + '">当日 ' + (it.chg!=null?(it.chg>=0?'+':'')+it.chg.toFixed(2)+'%':'—') + '</b><b class="' + c5 + '">5日 ' + (it.r5!=null?(it.r5>=0?'+':'')+it.r5.toFixed(1)+'%':'—') + '</b><b class="' + c20 + '">20日 ' + (it.r20!=null?(it.r20>=0?'+':'')+it.r20.toFixed(1)+'%':'—') + '</b></span>'
              + '<span class="t-m">量比 ' + (it.vr!=null?it.vr.toFixed(2):'—') + (it.atr_pct!=null?'｜ATR '+it.atr_pct.toFixed(1)+'%':'') + (it.pos250!=null?'｜位置 '+it.pos250.toFixed(0)+'%':'') + (it.r60!=null?'｜60日 '+(it.r60>=0?'+':'')+it.r60.toFixed(1)+'%':'') + '</span>'
              + '<span class="t-why">' + (it.why||'—') + '</span>'
              + '</div>';
          }).join('') + '</div>';
      }).join('') : '<div class="formula-mini">暂无全市场筛选数据（每日收盘后自动生成；自选池内个股请查看下方精确分类）。</div>');
}
function setScreenFilter(f){
  OV_SCREEN_FILTER = f;
  renderOvScreenAll();
}

/* 第三/四层：个股五类状态分类（启动/趋势/高位/回调/排除，附触发原因） */
const TS_ORDER = ['启动观察', '趋势观察', '高位观察', '回调观察', '排除'];
const TS_MEAN = {
  '启动观察': '刚站上 MA20、短期动能转正、20日涨幅尚小——观察放量确认',
  '趋势观察': '站上 MA20 且 MA20 上行/多头结构——趋势延续观察',
  '高位观察': '接近 250 日高位或短期涨幅过大——警惕追高',
  '回调观察': '跌破 MA20 但未深跌——等待止跌企稳',
  '排除': '破位或数据不足——排除出观察池',
};
function renderOvScreen(){
  const el = document.getElementById('ovScreen');
  if(!el) return;
  const groups = {};
  TS_ORDER.forEach(g => groups[g] = []);
  DATA.stocks.forEach(s => {
    if(s.route === 'etf') return;
    const d = tsScreen(s);
    if(!d){ groups['排除'].push({s, d, rs: ['K线不足40根']}); return; }
    const rs = [];
    let g = null;
    if(!d.above20){
      if(d.r20 != null && d.r20 <= -5){ g = '排除'; rs.push('跌破MA20且20日跌' + d.r20.toFixed(1) + '%'); }
      else { g = '回调观察'; rs.push('跌破MA20' + (d.dist20!=null?(d.dist20>=0?'+':'')+d.dist20.toFixed(1)+'%':'') + '，20日' + (d.r20!=null?(d.r20>=0?'+':'')+d.r20.toFixed(1)+'%':'—')); }
    } else {
      if(d.pos250 != null && d.pos250 > 80){ g = '高位观察'; rs.push('250日位置' + d.pos250.toFixed(0) + '%（近高位）'); }
      else if(d.r20 != null && d.r20 > 25){ g = '高位观察'; rs.push('20日涨幅' + d.r20.toFixed(1) + '% > 25%'); }
      else if(d.m20Up){ g = '趋势观察'; rs.push('站上MA20且MA20上行'); }
      else if(d.r5 != null && d.r5 > 0 && d.r20 != null && d.r20 < 10){
        if(d.r10 != null && d.r10 < 15){ g = '启动观察'; rs.push('刚站上MA20、5日' + (d.r5>=0?'+':'') + d.r5.toFixed(1) + '%转正、20日' + (d.r20>=0?'+':'') + d.r20.toFixed(1) + '%'); }
        else { g = '趋势观察'; rs.push('站上MA20，10日' + (d.r10>=0?'+':'') + d.r10.toFixed(1) + '%反弹'); }
      } else { g = '趋势观察'; rs.push('站上MA20'); }
    }
    if(d.atrFlag){ rs.push(d.atrFlag); if(g === '趋势观察' && d.r20 != null && d.r20 > 15){ g = '高位观察'; } }
    groups[g || '排除'].push({s, d, rs});
  });
  el.innerHTML = '<div class="formula-mini" style="border:none;padding:0;margin-bottom:6px">筛选口径：5/10/20日涨跌幅 + 价格 vs MA20 + MA20 方向 + 250日位置 + ATR 波动检查（D级工程化）。以下仅为状态分类与触发原因，<b>不构成任何买入建议</b>，请结合估值与基本面自行判断。点击行进入个股估值。</div>'
    + TS_ORDER.map(g => {
      const items = groups[g];
      if(!items.length) return '';
      const gCol = {'启动观察':'var(--blue)','趋势观察':'var(--green-d)','高位观察':'var(--red-d)','回调观察':'var(--gold)','排除':'var(--sub2)'}[g];
      return '<div class="ts-group"><div class="ts-head"><span class="ts-badge" style="color:' + gCol + ';border-color:' + gCol + '">' + g + ' ' + items.length + '只</span><span class="ts-mean">' + TS_MEAN[g] + '</span></div>'
        + items.map(it => {
          const d = it.d;
          const c5 = d.r5!=null ? (d.r5>=0?'up-c':'dn-c') : '';
          const c10 = d.r10!=null ? (d.r10>=0?'up-c':'dn-c') : '';
          const c20 = d.r20!=null ? (d.r20>=0?'up-c':'dn-c') : '';
          return '<div class="ts-row" onclick="switchStock(\'' + it.s.ticker + '\')" title="点击进入 ' + it.s.name + ' 估值">'
            + '<span class="t-nm">' + it.s.name + '<i>' + it.s.ticker + '</i></span>'
            + '<span class="t-r"><b class="' + c5 + '">5日 ' + (d.r5!=null?(d.r5>=0?'+':'')+d.r5.toFixed(1)+'%':'—') + '</b><b class="' + c10 + '">10日 ' + (d.r10!=null?(d.r10>=0?'+':'')+d.r10.toFixed(1)+'%':'—') + '</b><b class="' + c20 + '">20日 ' + (d.r20!=null?(d.r20>=0?'+':'')+d.r20.toFixed(1)+'%':'—') + '</b></span>'
            + '<span class="t-m">距MA20 ' + (d.dist20!=null?(d.dist20>=0?'+':'')+d.dist20.toFixed(1)+'%':'—') + (d.atrPct!=null?'｜ATR '+d.atrPct.toFixed(1)+'%':'') + (d.vr!=null?'｜量比 '+d.vr.toFixed(2):'') + (d.pos250!=null?'｜位置 '+d.pos250.toFixed(0)+'%':'') + '</span>'
            + '<span class="t-why">' + it.rs.join('；') + '</span>'
            + '</div>';
        }).join('') + '</div>';
    }).join('')
    + '<div class="formula-mini">分类规则：排除（跌破MA20且20日跌幅>5% / K线不足）；回调观察（跌破MA20但20日跌幅≤5%）；高位观察（250日位置>80% 或 20日涨幅>25%）；启动观察（刚站上MA20、5日转正、20日<10%、10日<15%）；趋势观察（站上MA20且MA20上行）。ATR 检查：单日异动>2×ATR 或 5日涨幅>2.5×ATR 时标注。</div>';
}

/* 大盘：全池总览表 */
function renderOvTable(){
  const el = document.getElementById('ovTable');
  if(!el) return;
  el.innerHTML =
    '<tr><th>股票</th><th>板块</th><th>现价</th><th>状态</th><th>质量</th><th>估值带</th><th>今日信号</th></tr>' +
    DATA.stocks.map(s => { const zm = zmeta(s);
      const g = ((s.decision_data||{}).quality||{}).grade || '—';
      const sig = (s.signals||[]).join('；') || '—';
      return '<tr onclick="switchStock(\''+s.ticker+'\')">'
        + '<td>'+s.name+'<br><span style="color:var(--meta);font-size:12px">'+s.ticker+'</span></td>'
        + '<td style="font-family:inherit">'+(s.sector||'未分组')+'</td>'
        + '<td>'+csym(s)+fmt2(s.price)+'</td><td>'+zm.label+'</td><td>'+g+'</td>'
        + '<td>'+(s.v_low!=null?fmt2(s.v_low)+' ~ '+fmt2(s.v_high):'—')+'</td><td>'+sig+'</td></tr>'; }).join('');
}

/* ============ 切换股票（数字滚动过渡） ============ */
function switchStock(ticker){
  const st = DATA.stocks.find(s=>s.ticker===ticker);
  if(!st) return;
  const prevPrice = PREV.price, prevPct = PREV.pct;
  CUR = st; VIEW = 'stock';
  localStorage.setItem('radar_last', ticker);
  document.getElementById('chartZone').style.display = '';
  document.getElementById('ovWrap').style.display = 'none';
  document.getElementById('shellMain').style.display = '';
  setTabUI('stock');
  document.getElementById('trigName').textContent = st.name + ' ' + st.ticker;
  const tp = document.getElementById('trigPx');
  if(tp){
    tp.textContent = csym(st) + fmt2(st.price);
    tp.className = 'px-block' + (st.pct>0?' up':(st.pct<0?' dn':''));
  }
  renderList();
  renderHero(st, prevPrice, prevPct);
  renderWall(st);
  KENGINE.setData(st);
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
  const pills = [];
  if(st.sector) pills.push('<span class="pill">板块 · '+st.sector+'</span>');
  pills.push('<span class="pill"><span class="dot" style="background:'+zcol+'"></span>'+zm.label+'</span>');
  if(st.decision_usable && st.band_pos_raw!=null) pills.push('<span class="pill num">估值带位置 '+fmt2(st.band_pos_raw*100)+'%</span>');
  if(st.decision_usable && st.mos!=null) pills.push('<span class="pill num">安全边际 '+(st.mos>=0?'+':'')+(st.mos*100).toFixed(1)+'%</span>');
  if(!st.decision_usable && st.reference_usable && st.reference_zone) pills.push('<span class="pill num">参考区间 '+st.reference_zone+'</span>');
  if(st.pe_ttm!=null && st.pe_ttm>0){ const ph=(DATA.pe_history||{})[st.ticker];
    if(ph && ph.ok && ph.pctile!=null) pills.push('<span class="pill num">PE分位 '+Math.round(ph.pctile*100)+'%</span>'); }
  document.getElementById('hPills').innerHTML = pills.join('');
  const pcol = st.pct>0?'var(--candle-up)':(st.pct<0?'var(--candle-dn)':'var(--sub2)');
  const priceEl = document.getElementById('hPrice');
  animateNum(priceEl, prevPrice, st.price, v => csym(st) + fmt2(v));
  priceEl.style.color = pcol;
  /* 价格更新闪烁（200ms） */
  if(prevPrice != null && isFinite(+prevPrice) && +prevPrice !== +st.price){
    const dir = +st.price > +prevPrice ? 'flash-red' : 'flash-green';
    priceEl.classList.add(dir);
    clearTimeout(priceEl._ft);
    priceEl._ft = setTimeout(() => priceEl.classList.remove(dir), 200);
  }
  /* 跌破 V_low / 突破 V_high：顶部边缘警示条（3s 淡出） */
  const alertEl = document.getElementById('edgeAlert');
  if(alertEl && isFinite(+st.v_low) && isFinite(+st.v_high) && +st.price > 0 && st.decision_usable){
    const below = +st.price < +st.v_low, above = +st.price > +st.v_high;
    if(below || above){
      alertEl.classList.remove('on'); void alertEl.offsetWidth;
      alertEl.classList.add('on');
    }
  }
  const arrow = st.pct>0?'▲':(st.pct<0?'▼':'◆');
  const pctEl = document.getElementById('hPct');
  animateNum(pctEl, prevPct, st.pct, v => arrow + ' ' + (v>0?'+':'') + fmt2(v) + '%');
  pctEl.style.color = pcol;
  const dot = document.getElementById('mosDot');
  const val = document.getElementById('mosVal');
  const raw = bandPosRaw(st.price, st.v_low, st.v_mid, st.v_high);
  if(raw != null && (st.decision_usable || st.reference_zone)){
    const pct = Math.max(0,Math.min(100,raw*100));
    dot.style.left = pct + '%';
    dot.style.display = '';
    if(val){
      val.textContent = '当前 ' + fmt2(st.price);
      val.style.left = pct + '%';
      val.style.display = '';
      if(pct > 88) val.style.left = (pct - 16) + '%';
      else if(pct < 10) val.style.left = (pct + 4) + '%';
    }
    let concl;
    if(st.decision_usable){
      concl = '当前处于' + st.zone + '区，安全边际 ' + (st.mos>=0?'+':'') + (st.mos*100).toFixed(1) + '%';
    } else {
      concl = '参考区间：' + st.reference_zone + '（质量门未通过，不可执行）';
    }
    document.getElementById('mosTxt').textContent = concl;
  } else {
    /* blocked / observe：质量门硬拦截，不显示任何 V 带数值，只给原因与分位信号 */
    dot.style.display = 'none';
    if(val) val.style.display = 'none';
    const ph = (DATA.pe_history||{})[st.ticker];
    let concl;
    if(st.decision_status === 'blocked'){
      concl = '数据不可用 / 无法估值：' + ((st._blockers||[])[0] || '路由拦截');
    } else if(st.decision_status === 'observe' && ph && ph.ok && ph.pctile!=null){
      concl = (ph.metric||'PE') + ' 历史分位 ' + Math.round(ph.pctile*100) + '%（' + (ph.signal||'观察') + '）';
    } else if(ph && ph.ok && ph.pctile!=null){
      concl = '当前 ' + (ph.metric||'PE') + ' 处于历史 ' + Math.round(ph.pctile*100) + '% 分位（' + (ph.signal||'—') + '）';
    } else if(st.decision_status === 'observe'){
      concl = '观察路由：无估值锚，等待盈利/指数数据补齐';
    } else {
      concl = '数据不可用 / 无法估值（路由拦截）';
    }
    document.getElementById('mosTxt').textContent = concl;
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
  const srcMap = {};
  ((st.decision_data||{}).sources||[]).forEach(x => { srcMap[x.id] = x; });
  let html = steps.map(s => {
    const links = (s.source_ids||[]).map(id => {
      const so = srcMap[id];
      return so ? '<a class="src-link" href="' + (so.url||'#') + '" target="_blank" rel="noreferrer" title="' + (so.title||so.provider||id) + '">' + (so.provider||'来源') + '</a>' : '';
    }).join(' ');
    return '<div class="step-item"><div class="step-no">' + (s.id==='v_low'?'低':(s.id==='v_mid'?'中':'高')) + '</div><div>'
      + '<b>' + (s.label||s.id) + '</b>：' + (s.formula||'')
      + '<span class="eq">' + (s.substitution||'') + ' = ' + fmt2(s.result) + ' 元</span>'
      + (links ? '<span class="src">' + links + '</span>' : '')
      + '</div></div>';
  }).join('');
  const gm = st.growth_momentum;
  if(gm && gm.growth > 0.30){
    html += '<div class="step-item"><div class="step-no">P</div><div><b>成长修正（PEG 交叉检查）</b>：FY1 增速 ' + (gm.growth*100).toFixed(0) + '% → PEG≈1 参考 PE ' + gm.peg_pe + '×；'
      + '<span class="eq">原历史分位 PE ' + fmt2(st.pe_mid) + '× → 修正参考 ' + gm.peg_pe + '×（不自动替换倍数，仅供认知补偿）</span></div></div>';
  }
  return html;
}

/* ============ Card2 渲染器（按路由分派，逻辑隔离） ============ */
function renderC2(st){
  if(st.decision_status === 'blocked' || st.decision_status === 'observe') return renderC2Blocked(st);
  return renderC2V3(st);
}

/* 被拦截/观察标的：仅 blocker 原因 + 分位信号（ETF 水位计），无价格锚 */
function renderC2Blocked(st){
  const ph = (DATA.pe_history||{})[st.ticker];
  const isETF = st.route==='etf' || st.ticker==='000001';
  const html = '<div class="blocker-line">' + ((st._blockers||[])[0]||'路由拦截：模型输入不完整') + '</div>'
    + (isETF && ph && ph.ok && ph.pctile!=null ?
        '<div class="band-track" style="margin-top:8px"><div class="dot" style="left:'+Math.max(0,Math.min(100,ph.pctile*100))+'%"></div></div>'
        + '<div class="band-labels" style="display:flex;justify-content:space-between;font-size:12px;color:var(--sub2);margin-top:4px"><span>低估 &lt;30%</span><span>合理 30~70%</span><span>高估 &gt;70%</span></div>'
        + '<div class="formula-mini" style="color:'+(ph.pctile<0.3?'var(--green-d)':(ph.pctile>0.7?'var(--red-d)':'var(--sub2)'))+'">指数估值水位计：当前 '+(ph.metric||'PE')+' 处于历史 '+Math.round(ph.pctile*100)+'% 分位（'+(ph.signal||'—')+'）。该模型无需盈利预测，仅参考指数历史水位（D级）。</div>'
        : '')
    + (ph && ph.ok ? '<div class="micro-row">'
      + '<div class="micro"><div class="k">PE/PB 历史分位</div><div class="v">'+(ph.pctile!=null?Math.round(ph.pctile*100)+'%':'—')+'</div><div class="m">'+phDetail(ph)+'</div></div>'
      + '<div class="micro"><div class="k">分位判断</div><div class="v" style="font-size:14px">'+(ph.signal||'—')+'</div><div class="m">'+(ph.note||'')+'</div></div>'
      + '<div class="micro"><div class="k">TTM PE/PB</div><div class="v">'+fmt2(st.pe_ttm)+'/'+fmt2(st.pb)+'</div><div class="m">行情源</div></div>'
      + '</div>' : '');
  return {html, src: ''};
}

/* 有估值带的路由：三档 V 块 + 位置条 + 计算过程 + 敏感性按钮（equity 加计算器） */
function renderC2V3(st){
  const model = st.valuation_model || {};
  const isBank = model.code==='bank_pb_roe', isInfra = model.code==='infrastructure_cashflow';
  const isIns = model.code==='insurance_pev', isNorm = st.forecast_basis==='NORMALIZED';
  const usable = st.decision_usable;
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
  /* 现价在 low/mid/high 各段内的位置（0~100%），作块内进度条 */
  const seg = (lo, hi) => (isFinite(+lo) && isFinite(+hi) && hi > lo)
    ? Math.max(0, Math.min(100, (+st.price - +lo) / (+hi - +lo) * 100)) : 50;
  const pbar = p => '<div class="pbar"><i style="width:' + p.toFixed(0) + '%"></i></div>';
  const pLow = seg(+st.v_low * 0.9, +st.v_low), pMid = seg(+st.v_low, +st.v_mid), pHigh = seg(+st.v_mid, +st.v_high);
  let html =
    '<div class="v3-blocks">'
    + '<div class="v3b low"><div class="k">保守 V_low'+(usable?' · 买入启动':'')+'</div><div class="v">'+csym(st)+fmt2(st.v_low)+'</div><div class="f">'+e1+' × '+m1+'×</div>'+pbar(pLow)+'</div>'
    + '<div class="v3b mid"><div class="k">基准 V_mid · 价值中枢</div><div class="v">'+csym(st)+fmt2(st.v_mid)+'</div><div class="f">'+e2+' × '+m2+'×</div>'+pbar(pMid)+'</div>'
    + '<div class="v3b high"><div class="k">乐观 V_high'+(usable?' · 卖出启动':'')+'</div><div class="v">'+csym(st)+fmt2(st.v_high)+'</div><div class="f">'+e3+' × '+m3+'×</div>'+pbar(pHigh)+'</div>'
    + '</div>'
    + '<div class="band-track"><div class="dot" style="left:'+bandPosPct(st.price, st.v_low, st.v_mid, st.v_high)+'%"></div></div>'
    + '<div class="band-labels" style="display:flex;justify-content:space-between;font-size:12px;color:var(--sub2);margin-top:4px"><span>低估 '+csym(st)+fmt2(st.v_low)+'</span><span>现价 ¥'+fmt2(st.price)+'</span><span>高估 ¥'+fmt2(st.v_high)+'</span></div>'
    + (!usable?'<div class="warn-line">质量门未通过：参考级区间，不构成买卖动作。</div>':'');
  let foldInner = calcStepsHTML(st);
  if(usable && !isIns && !isBank && !isInfra && !isNorm){
    foldInner += '<div class="calc-body" style="display:block;padding-top:10px"><div class="row">'
      + '<div><label>现价 P</label><input id="i-price" type="number" step="0.01" value="'+st.price+'"></div>'
      + '<div><label>PE低/中/高</label><div style="display:flex;gap:4px"><input id="i-peL" type="number" step="0.5" value="'+st.pe_low+'"><input id="i-peM" type="number" step="0.5" value="'+st.pe_mid+'"><input id="i-peH" type="number" step="0.5" value="'+st.pe_high+'"></div></div>'
      + '<div><label>EPS保守/基准/乐观</label><div style="display:flex;gap:4px"><input id="i-epsB" type="number" step="0.01" value="'+st.eps_bear+'"><input id="i-epsM" type="number" step="0.01" value="'+st.eps_base+'"><input id="i-epsU" type="number" step="0.01" value="'+st.eps_bull+'"></div></div>'
      + '</div><div class="calc-out" id="calcOut">—</div></div>';
  }
  html += '<div class="sens-btn-row"><button class="sens-btn" onclick="openSensitivity(\'' + st.ticker + '\')">⚡ 敏感性测试（压力测试，不保存）</button></div>'
    + foldHTML('fold2', foldInner);
  return {html, src: st.forecast_source || st.pb_source || st.pe_source || ''};
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
  srs.forEach((x,i) => dots.push({cls:'s'+(x.level_ev==='A'?'A':(x.level_ev==='C'?'C':'B')), v:+x.level, t:'S'+(i+1), touched: k.length ? k.some(r=>r.l<=+x.level && r.h>=+x.level) : false}));
  rrs.forEach((x,i) => dots.push({cls:'r'+(x.level_ev==='A'?'A':(x.level_ev==='C'?'C':'B')), v:+x.level, t:'R'+(i+1), touched: k.length ? k.some(r=>r.l<=+x.level && r.h>=+x.level) : false}));
  dots.sort((a,b)=>a.v-b.v);
  /* 标签错开：相邻价差 <5% 时次位下沉一行，避免重叠 */
  const pct = dots.map(d=>({d, p: pos(d.v), t: d.t}));
  const labelTier = pct.map(()=>0);
  for(let i=1;i<pct.length;i++){
    if(pct[i].p - pct[i-1].p < 14 && labelTier[i-1]===0) labelTier[i] = 1;
    else if(pct[i].p - pct[i-1].p < 14) labelTier[i] = 0;
  }
  let c0 = '<div class="sr-track">';
  [20,40,60,80].forEach(p => { c0 += '<span class="tick" style="left:'+p+'%"></span>'; });
  pct.forEach((pd,i) => {
    const d = pd.d;
    c0 += '<span class="sr-dot '+d.cls+'" style="left:'+pd.p+'%" title="'+d.t+' '+csym(st)+fmt2(d.v)+'"></span>'
      + '<span class="sr-lbl '+(labelTier[i]?'tier2':'')+'" style="left:'+pd.p+'%" title="'+d.t+' '+csym(st)+fmt2(d.v)+'">'
      + (d.touched?'✦':'')+pd.t+' '+csym(st)+fmt2(d.v)+'</span>';
  });
  c0 += '<span class="sr-dot cur" style="left:'+pos(st.price)+'%" title="现价 '+csym(st)+fmt2(st.price)+'"></span>';
  c0 += '</div>';
  c0 += '<div class="sr-list">';
  srs.forEach((x,i) => { c0 += '<div class="row s"><span class="m">S'+(i+1)+' · '+(x.method||'')+' <b class="g">'+x.level_ev+'级</b></span><span class="v">'+csym(st)+fmt2(x.level)+'</span></div>'; });
  rrs.forEach((x,i) => { c0 += '<div class="row r"><span class="m">R'+(i+1)+' · '+(x.method||'')+' <b class="g">'+x.level_ev+'级</b></span><span class="v">'+csym(st)+fmt2(x.level)+'</span></div>'; });
  c0 += '</div>';
  if(!srs.length && !rrs.length) c0 = '<div class="formula-mini">暂无支撑/压力数据（K线不足或未配置）。</div>';
  c0 += '<div class="formula-mini">轨道区间：'+csym(st)+fmt2(tMin)+' ~ '+csym(st)+fmt2(tMax)+'（250日高低点）；蓝点=现价，实心=A级技术位，虚线=B级，细边=C级（估值锚/贴线/转换位）。</div>';
  document.getElementById('c0Body').innerHTML = c0;

  /* ---- Card 1：市场与模型 + 质检折叠 ---- */
  const g = (DATA.market.graham_metrics||[]).find(x=>x.key==='cs985') || (DATA.market.graham_metrics||[])[0] || {};
  const grade = q.grade || '—';
  const gCol = g.graham>=2.3?'var(--green-d)':(g.graham>=1.8?'var(--gold)':'var(--red-d)');
  document.getElementById('c1Body').innerHTML =
    '<div class="micro-row" style="border-top:none;padding-top:0">'
    + '<div class="micro"><div class="k">格雷厄姆指数</div><div class="v">'+(g.graham||'—')+'</div>'
    + '<div class="m" style="color:'+gCol+'">'+(g.band||'—')+(g.erp_pct!=null?' · ERP '+g.erp_pct+'%':'')+((DATA.market.cs985||{}).stale?' · 滞后':'')+'</div></div>'
    + '<div class="micro"><div class="k">估值模型</div><div class="v" style="font-size:14px">'+(model.code||'—')+'</div>'
    + '<div class="m">'+((model.label||'').split('·')[0]||'')+'</div></div>'
    + '<div class="micro"><div class="k">数据质量</div><div class="v" style="color:'+(grade==='B'?'var(--green-d)':(grade==='C'?'var(--gold)':'var(--red-d)'))+'">'+grade+'</div>'
    + '<div class="m">'+checks.filter(c=>!c.passed&&c.severity!=='info').length+' 项未通过</div></div>'
    + '</div>'
    + foldChecks('fold1');

  /* ---- Card 2：三档估值（按路由分派独立渲染器） ---- */
  const c2 = renderC2(st);
  document.getElementById('c2Body').innerHTML = c2.html || '<div class="formula-box">无数据</div>';
  document.getElementById('c2Src').textContent = c2.src ? c2.src.slice(0,26) : '';
  bindCalc();

  /* ---- Card 3：买卖阶梯（瀑布，spec 5.2/5.3：Kelly + 档位仓位 + 止损） ---- */
  if(usable && st.v_low!=null && st.v_high!=null){
    const mos = st.mos!=null ? st.mos : (st.v_mid!=null && st.v_mid>0 ? (st.v_mid-st.price)/st.v_mid : 0);
    const kellyRaw = st.v_high>st.v_low ? mos/(st.v_high-st.v_low) : 0;
    let kelly = Math.max(0, Math.min(kellyRaw*0.5, 0.20));
    const mc = st.model_confidence!=null && isFinite(+st.model_confidence) ? +st.model_confidence : null;
    let kellyNote = '';
    if(mc != null){
      kelly = kelly * mc;
      if(mc < 0.6){ kelly = kelly * 0.5; kellyNote = '｜ 低置信度（'+mc.toFixed(2)+'），仓位减半'; }
    }
    const k = st.kline||[];
    const lo60 = k.length>=60 ? Math.min(...k.slice(-60).map(r=>r.l)) : null;
    const stop1 = st.ma250!=null ? st.ma250*0.97 : null;
    const b1=st.v_low*1.05, b2=st.v_low, b3=st.v_low*0.95;
    const sellRows = [
      {lab:'止盈2档 · ≥V_high 清仓50%', v:st.v_high, stop:''},
      {lab:'止盈1档 · ≥V_mid 减仓30%', v:st.v_mid, stop:''},
    ];
    const buyRows = [
      {lab:'试探仓 5% · ≤V_low×1.05', v:b1, stop: stop1!=null ? ('止损 MA250×0.97 ¥'+fmt2(stop1)) : '止损 待MA250'},
      {lab:'主力仓 10% · ≤V_low', v:b2, stop:'止损 V_low×0.95 ¥'+fmt2(st.v_low*0.95)},
      {lab:'加仓 5% · ≤V_low×0.95', v:b3, stop: lo60!=null ? ('止损 近60日低点 ¥'+fmt2(lo60)) : '止损 近期低点'},
    ];
    document.getElementById('c3Body').innerHTML = '<div class="wfall">'
      + sellRows.map(r=>'<div class="step sell'+(st.price>=r.v?' touched':'')+'"><span class="lab">'+r.lab+'</span><span>¥'+fmt2(r.v)+'</span></div>').join('')
      + '<div class="divider"><span>现价</span><span>¥'+fmt2(st.price)+'</span></div>'
      + buyRows.map(r=>'<div class="step buy'+(st.price<=r.v?' touched':'')+'"><span class="lab">'+r.lab+'</span><span>¥'+fmt2(r.v)+'</span><small class="st">'+r.stop+'</small></div>').join('')
      + '</div>'
      + '<div class="kelly-line">Kelly 单票上限 '+(kelly*100).toFixed(1)+'%（cap 20% × conf '+(mc!=null?mc.toFixed(2):'—')+'）'+kellyNote+'｜ MOS '+(mos*100).toFixed(1)+'%</div>'
      + '<div class="kelly-line">触发确认：估值定方向（档位+上限），技术定时机——试探仓须待止跌确认/站上MA5 再执行，估值触档不单独满仓（防左侧接飞刀）。</div>'
      + foldHTML('fold3','<div class="formula-mini">'
      + 'Kelly_fraction = MOS ÷ (V_high − V_low) × 0.5（保守系数，分数凯利）× model_confidence，cap 20%（D级可配置，spec 5.2；置信度<0.6 再减半）；'
      + '买入金字塔：试探 5% ≤V_low×1.05（止损 MA250×0.97）→ 主力 10% ≤V_low（止损 V_low×0.95）→ 加仓 5% ≤V_low×0.95（止损近60日低点）；'
      + '止盈倒金字塔：≥V_mid 减仓30%、≥V_high 清仓50%（spec 5.3）。触达档位自动高亮。</div>');
  } else if(st.v_low!=null && st.v_high!=null){
    document.getElementById('c3Body').innerHTML =
      '<div class="warn-line">参考区间 '+csym(st)+fmt2(st.v_low)+' ~ '+csym(st)+fmt2(st.v_high)+'（不可执行）：质量门未通过，不生成买卖阶梯。</div>';
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
    '<div class="sr-list"><div class="row '+cls+'"><span class="m">'+pre+(i+1)+' · '+(x.method||'')+'</span><span class="v">'+csym(st)+fmt2(x.level)+'</span></div></div>').join('');
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

  /* ---- 折叠态关键数据微标（各卡核心一屏数值） ---- */
  const setMicro = (id, txt) => {
    const el = document.getElementById(id);
    if(el) el.textContent = txt;
  };
  const s1 = srs[0] ? 'S1 '+csym(st)+fmt2(srs[0].level) : (rrs[0] ? 'R1 '+csym(st)+fmt2(rrs[0].level) : '');
  const sTop = rrs.length ? 'R1 '+csym(st)+fmt2(rrs[rrs.length-1].level) : '';
  setMicro('c0Micro', (s1 ? s1 + ' → ' : '') + (sTop ? sTop : '现价 '+csym(st)+fmt2(st.price)));
  setMicro('c1Micro', '模型 '+(model.code||'—') + ' · 质量 '+(q.grade||'—'));
  setMicro('c2Micro', 'V_low '+csym(st)+fmt2(st.v_low)+' / 中枢 '+csym(st)+fmt2(st.v_mid)+' / V_high '+csym(st)+fmt2(st.v_high));
  setMicro('c3Micro', st.v_low!=null && st.v_high!=null ? '+csym(st)+fmt2(st.v_low)+'~'+csym(st)+fmt2(st.v_high) : '—');
  const b3 = document.querySelector('.pos-legend');
  const posTxt = b3 && b3.textContent ? b3.textContent.trim().replace(/\s+/g,' ') : '';
  setMicro('c4Micro', st.ma250!=null ? 'MA250 '+fmt2(st.ma250) : '—');
  setMicro('c5Micro', posTxt ? '底仓 '+(plan['底仓']!=null ? Math.round(plan['底仓']*100)+'%' : '—') : '—');
  setMicro('c6Micro', badges.length + ' 项来源');
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

/* ============ 敏感性分析（压力测试，不保存、不改写冻结参数） ============ */
function openSensitivity(ticker){
  const st = DATA.stocks.find(s => s.ticker === ticker);
  if(!st || st.v_low==null || st.eps_base==null) return;
  const P = +st.price;
  const body = '<div class="formula-box">模拟压力测试：仅用于理解参数敏感度，<b>不保存、不影响正式决策与质量门</b>。'
    + '基准：EPS bear/base/bull = ' + fmt2(st.eps_bear) + '/' + fmt2(st.eps_base) + '/' + fmt2(st.eps_bull)
    + '，PE 档 = ' + st.pe_low + '/' + st.pe_mid + '/' + st.pe_high + '×</div>'
    + '<div class="row"><div><label>PE 倍数调整</label><input type="range" id="s-pe" min="80" max="120" step="5" value="100"><div class="sens-v" id="s-pe-v">×1.00</div></div></div>'
    + '<div class="row"><div><label>EPS 增速调整</label><input type="range" id="s-eps" min="-30" max="30" step="5" value="0"><div class="sens-v" id="s-eps-v">+0%</div></div></div>'
    + '<div id="sensOut" class="formula-box">—</div>'
    + '<span class="src-badge">D级：仅模拟，不改写冻结参数/来源账本/质量门</span>';
  openModal('⚡ 敏感性测试 · ' + st.name, body);
  const re = () => {
    const m = +document.getElementById('s-pe').value / 100;
    const g = +document.getElementById('s-eps').value / 100;
    document.getElementById('s-pe-v').textContent = '×' + m.toFixed(2);
    document.getElementById('s-eps-v').textContent = (g>=0?'+':'') + (g*100).toFixed(0) + '%';
    const e = b => (b==null ? null : +b * (1 + g));
    const vLow = e(st.eps_bear) * +st.pe_low * m;
    const vMid = e(st.eps_base) * +st.pe_mid * m;
    const vHigh = e(st.eps_bull) * +st.pe_high * m;
    if(![vLow, vMid, vHigh].every(v => isFinite(+v) && +v > 0)) return;
    const mos = 1 - P / vMid;
    const kellyRaw = vHigh > vLow ? mos / (vHigh - vLow) : 0;
    let kelly = Math.max(0, Math.min(kellyRaw * 0.5, 0.20));
    const mc = st.model_confidence!=null && isFinite(+st.model_confidence) ? +st.model_confidence : null;
    if(mc != null){ kelly = kelly * mc; if(mc < 0.6) kelly = kelly * 0.5; }
    const zone = P <= vLow ? (P <= 0.9*vLow ? '深度低估' : '低估')
      : (P <= vMid ? '合理下沿' : (P <= vHigh ? '合理上沿' : (P <= 1.3*vHigh ? '高估' : '泡沫')));
    document.getElementById('sensOut').innerHTML =
      '<div class="v3-blocks">'
      + '<div class="v3b low"><div class="k">V_low（模拟）</div><div class="v">¥' + fmt2(vLow) + '</div></div>'
      + '<div class="v3b mid"><div class="k">V_mid（模拟）</div><div class="v">¥' + fmt2(vMid) + '</div></div>'
      + '<div class="v3b high"><div class="k">V_high（模拟）</div><div class="v">¥' + fmt2(vHigh) + '</div></div>'
      + '</div>'
      + '<div>模拟区间：<b>' + zone + '</b>｜ MOS ' + (mos>=0?'+':'') + (mos*100).toFixed(1) + '%｜ Kelly 单票上限 ' + (kelly*100).toFixed(1) + '%</div>'
      + '<div class="formula-mini">V = EPS×(' + (g>=0?'+':'') + (g*100).toFixed(0) + '%) × PE×' + m.toFixed(2) + '（EPS 三档按同比例缩放）；现价 ' + fmt2(P) + '</div>';
  };
  setTimeout(() => {
    const e1 = document.getElementById('s-pe'), e2 = document.getElementById('s-eps');
    if(e1) e1.addEventListener('input', re);
    if(e2) e2.addEventListener('input', re);
    re();
  }, 0);
}
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
  const rows = (m.graham_metrics||[]).map(x=>'<div class="step-item"><div class="step-no">•</div><div>'+x.label+'：PE '+x.pe+' → 格雷厄姆 <b>'+x.graham+'</b>（'+x.band+'）｜ ERP <b>'+(x.erp_pct!=null?x.erp_pct+'%':'—')+'</b> = 1/PE − 10Y国债</div></div>').join('');
  openModal('市场估值温度（格雷厄姆指数 + ERP）',
    '<div class="formula-box"><b>公式：格雷厄姆指数 = (1÷全市场PE) ÷ 十年期国债收益率</b>\n分档：>2.3极低 / 2~2.3偏低 / 1.8~2略偏低 / 1.5~1.8中性 / 1~1.5偏高 / <1极高\n\n'
    + '<b>ERP（股权风险溢价）= 1÷PE − 10Y国债收益率</b>：减法模型，低利率下格雷厄姆比值分母趋零会乘数放大（如 10Y=1.7% 时指数达 3.98 显示"极低"），ERP 不随 rf→0 爆炸。无 10 年 ERP 历史序列，暂不给分档（D级工程补充）。\n\n'
    + '注意：指数 PE(TTM) 在周期顶部盈利放大显得"便宜"、周期底部亏损显得"昂贵"（反向失真）；成分股结构逐年漂移（银行/地产权重下降、消费/科技上升），长周期绝对值对比不可比。仅市场背景，不生成动作。\n\nv2 定位：仅作市场背景参考，不构成仓位硬闸门。</div>' + rows
    + '<span class="src-badge">A级公式与分档</span><span class="src-badge">D级：中证全指000985双口径</span><span class="src-badge">D级：ERP减法模型</span>');
}

/* 主题变量读取：Canvas/SVG 渲染颜色统一从 getComputedStyle 动态取 CSS 变量 */
function cssVar(name, fb){ try{ const v = getComputedStyle(document.documentElement).getPropertyValue(name); return (v && v.trim()) ? v.trim() : fb; }catch(e){ return fb; } }
/* ============ K线图引擎 v2（Canvas 分层渲染 + SVG 交互覆盖层） ============
   设计规则：
   1. 所有渲染颜色经 getComputedStyle 读取 CSS 变量（--candle-up/--candle-dn/--hair/--sub2…），
      暗色主题 html[data-theme="dark"] 自动适配；
   2. 物理像素 = CSS像素 × DPR，1px 线条统一对齐 0.5px 网格保证锐利；
   3. 分层渲染：网格(虚线) → 估值色带 → 成交量副图 → 蜡烛 → 均线 → 呼吸点；
   4. 布局：右侧 Y 轴 56px 毛玻璃面板（CSS axis-panel）、底部 24px 时间轴、
      成交量副图约占 24%（与主图共享 X 轴，1px --hair 分割线）；
   5. 动效：切换周期/股票时蜡烛自底部生长 + 均线从左向右裁剪（--dur-layout 320ms）；
   6. 交互：SVG 十字光标（主题蓝 .35 + 4px 白边圆点）、Tooltip 溢出自动翻转、
      滚轮指针居中缩放（最少 20 根）、拖拽平移 + 200ms 惯性、键盘 ←/→ 移动光标 ↑/↓ 聚焦MA。 */

const KCOL = { up: cssVar('--candle-up', '#d94a47'), dn: cssVar('--candle-dn', '#178a59') };

function hexA(hex, a){
  const h = String(hex).replace('#', '');
  if(h.length !== 6) return hex;
  const n = parseInt(h, 16);
  return 'rgba(' + ((n >> 16) & 255) + ',' + ((n >> 8) & 255) + ',' + (n & 255) + ',' + a + ')';
}

const MADASH = {5:[], 10:[], 20:[], 60:[6,5], 120:[6,5], 250:[2,5]};

function niceStep(range, ticks){
  if(!(range > 0) || !isFinite(range)) return 1;
  const raw = range / (ticks || 5);
  const mag = Math.pow(10, Math.floor(Math.log(raw) / Math.LN10));
  const norm = raw / mag;
  const s = norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 2.5 ? 2.5 : norm <= 5 ? 5 : 10;
  return s * mag;
}

function packLbl(items, gap){
  items.sort((a,b) => a.y - b.y);
  let last = -Infinity;
  for(const it of items){
    it.yy = Math.max(it.y, last + gap);
    last = it.yy;
  }
  return items;
}

/* 双列防重叠：右列（MA/斐波/锚标签）与左列（S/R 徽章）互检，
   冲突时右标签向下让位 6px，6 次仍冲突则隐藏（_hidden） */
function packLblMutual(left, right, gapL, gapR, crossGap){
  packLbl(left, gapL);
  packLbl(right, gapR);
  for(const it of right){
    let guard = 0;
    while(guard++ < 6){
      const clash = left.filter(l => Math.abs(l.yy - it.yy) < crossGap);
      if(!clash.length) break;
      it.yy = Math.max(it.y, clash[0].yy + crossGap + 2);
    }
    if(guard >= 6 && left.some(l => Math.abs(l.yy - it.yy) < crossGap)) it._hidden = true;
  }
  return right;
}

class ValuationChartEngine {
  constructor(containerId, stockData){
    this.wrap = document.getElementById(containerId);
    this.cv = document.getElementById('klineCv');
    this.sv = document.getElementById('klineSvg');
    this.tip = document.getElementById('chartTip');
    this.ctx = this.cv ? this.cv.getContext('2d') : null;
    this.st = null; this.rows = []; this.N = 0;
    this.maC = {}; this.volC = {}; this.crosses = [];
    this.slot = 6; this.viewStart = 0; this.rangeN = 250;
    this.maVis = {5:true, 10:true, 20:true, 60:true, 120:true, 250:true};
    this.bandVis = true;
    this.hollow = (() => { try{ return localStorage.getItem('radar_hollow') === '1'; }catch(e){ return false; } })();
    this.pinned = false; this.pinIdx = -1; this._pinY = null; this._tipIdx = -1;
    this._drag = null; this._raf = 0; this._anim = null; this._resT = null; this._ro = null;
    this._ch = null; this._animateSR = false; this._custom = false;
    this._dataTok = 0;
    this._yShift = 0; this._yAnim = null; this._bandAnim = null; this._dashShift = 0;
    this._growAnim = null;
    this._loopOn = false; this._hoverOn = false; this._hoverT = null; this._flashT = null; this._hl = [];
    this._isMobile = window.matchMedia ? window.matchMedia('(max-width:699px)').matches : false;
    if(this.tip) this.tip.classList.toggle('mobile', this._isMobile);
    this._theme();
    this._bind();
    if(stockData) this.setData(stockData);
  }

  /* ---- 主题取色：Canvas/SVG 全部颜色从 getComputedStyle 动态读取 ---- */
  _theme(){
    const V = (name, fb) => cssVar(name, fb);
    this.C = {
      up:   V('--candle-up',  '#d94a47'),
      dn:   V('--candle-dn',  '#178a59'),
      ink:  V('--ink',        '#1d1d1f'),
      sub:  V('--sub',        '#6e6e73'),
      sub2: V('--sub2',       '#48484a'),
      hair: V('--hair',       'rgba(0,0,0,.08)'),
      hair2:V('--hair2',      'rgba(0,0,0,.14)'),
      bg2:  V('--bg2',        '#ffffff'),
      blue: V('--blue',       '#0071e3'),
      green:V('--green',      '#34c759'),
      red:  V('--red',        '#ff3b30'),
      gold: V('--gold',       '#a0742f'),
      violet:V('--violet',    '#5e5ce6'),
    };
    this._maCol = {5:this.C.blue, 10:this.C.violet, 20:this.C.gold, 60:this.C.sub, 120:this.C.violet, 250:this.C.green};
  }

  /* ---- 事件绑定 ---- */
  _bind(){
    const sv = this.sv;
    sv.addEventListener('pointermove', e => this._onMove(e));
    sv.addEventListener('pointerdown', e => this._onDown(e));
    sv.addEventListener('pointerup', e => this._onUp(e));
    sv.addEventListener('pointercancel', () => { this._drag = null; });
    sv.addEventListener('pointerleave', () => {
      this._hoverReset();
      if(!this.pinned){ this._hideCross(); this.tip.classList.remove('show'); }
    });
    sv.addEventListener('wheel', e => { e.preventDefault(); this._zoom(e); }, {passive:false});
    sv.addEventListener('dblclick', e => { e.preventDefault(); this.setRange(250); });
    /* 键盘导航：←/→ 逐根移动十字光标，↑/↓ 在 MA 芯片间移动焦点 */
    document.addEventListener('keydown', e => this._onKey(e));
    /* 尺寸监听：ResizeObserver 防抖 100ms（替代 window.resize） */
    if(window.ResizeObserver){
      this._ro = new ResizeObserver(() => {
        clearTimeout(this._resT);
        this._resT = setTimeout(() => { this.resize(); }, 100);
      });
      this._ro.observe(this.wrap);
    }
  }

  _onKey(e){
    if(VIEW !== 'stock' || this.N < 2) return;
    const ae = document.activeElement;
    if(ae && (ae.tagName === 'INPUT' || ae.tagName === 'TEXTAREA' || ae.tagName === 'SELECT')) return;
    if(e.key === 'ArrowLeft' || e.key === 'ArrowRight'){
      e.preventDefault();
      const cur = (this.pinned && this.pinIdx >= 0) ? this.pinIdx : this.N - 1;
      const ni = Math.max(0, Math.min(this.N - 1, cur + (e.key === 'ArrowRight' ? 1 : -1)));
      this.pinned = true; this.pinIdx = ni; this._tipIdx = ni;
      const bars = this.barsPerView();
      if(ni < this.viewStart) this.viewStart = ni;
      else if(ni > this.viewStart + bars - 1) this.viewStart = Math.max(0, Math.min(this.N - bars, ni - Math.floor(bars / 2)));
      this._clampView();
      this._renderTip(ni);
      this._updateCross(ni, this.yOf(this.rows[ni].c));
      this._positionTip(this.xOf(ni), this.yOf(this.rows[ni].c));
      this.tip.classList.add('show');
      this._scheduleDraw();
    } else if(e.key === 'ArrowUp' || e.key === 'ArrowDown'){
      const chips = Array.from(document.querySelectorAll('.ma-chip[data-ma]:not(.off)'));
      if(!chips.length) return;
      const idx = chips.indexOf(document.activeElement);
      const nxt = chips[(idx < 0 ? 0 : (idx + (e.key === 'ArrowDown' ? 1 : chips.length - 1)) % chips.length)];
      e.preventDefault(); nxt.focus();
    }
  }

  /* ---- 布局与比例 ---- */
  layout(){
    const w = Math.max(260, this.wrap.clientWidth || 800);
    const h = Math.max(180, this.wrap.clientHeight || 540);
    this.W = w; this.H = h;
    this.dpr = Math.min(2, window.devicePixelRatio || 1);
    this.AX = 56;                      /* 右侧 Y 轴毛玻璃面板宽 */
    this.GUT = w < 560 ? 64 : 84;      /* 右缘标签槽：锚/MA/斐波标签专用，K线不进入 */
    this.TL = 12; this.BX = 24;        /* 顶部留白 12，底部时间轴 24 */
    this.px0 = 8; this.px1 = w - this.AX - this.GUT;
    this.axX = w - this.AX;
    this.hideVol = w < 600;            /* 窄屏隐藏成交量副图，释放垂直空间 */
    this.priceH = (h - this.TL - this.BX) * (this.hideVol ? 1 : 0.76);
    this.volTop = this.TL + this.priceH + 6;
    this.volBot = this.hideVol ? this.volTop : h - this.BX;
    this.volH = this.volBot - this.volTop;
    const wpx = Math.round(w * this.dpr), hpx = Math.round(h * this.dpr);
    if(this.cv.width !== wpx || this.cv.height !== hpx){ this.cv.width = wpx; this.cv.height = hpx; }
    this._theme();
  }

  barsPerView(){ return (this.px1 - this.px0) / Math.max(this.slot, 0.05); }
  xOf(i){ return this.px0 + (i - this.viewStart + 0.5) * this.slot; }

  _clampView(){
    const bars = this.barsPerView();
    if(bars >= this.N){
      this.slot = (this.px1 - this.px0) / Math.max(1, this.N);
      this.viewStart = 0;
    } else {
      this.viewStart = Math.max(0, Math.min(this.N - bars, this.viewStart));
    }
  }

  _range(){
    const bars = this.barsPerView();
    const i0 = Math.max(0, Math.floor(this.viewStart - 1));
    const i1 = Math.min(this.N - 1, Math.ceil(this.viewStart + bars + 1));
    let lo = Infinity, hi = -Infinity;
    for(let i = i0; i <= i1; i++){
      const r = this.rows[i];
      if(r.l < lo) lo = r.l;
      if(r.h > hi) hi = r.h;
    }
    if(!isFinite(lo)){ const c = this.rows[this.N-1].c; lo = c - 1; hi = c + 1; }
    const st = this.st;
    const vlow = +st.v_low, vmid = +st.v_mid, vhigh = +st.v_high;
    const hasV = this.bandVis && isFinite(vlow) && isFinite(vmid) && isFinite(vhigh) && vlow > 0 && vlow < vmid && vmid < vhigh;
    if(hasV){ lo = Math.min(lo, vlow); hi = Math.max(hi, vhigh); }
    (st.support||[]).concat(st.resistance||[]).forEach(sr => {
      const v = +sr.level;
      if(isFinite(v) && v > 0){ lo = Math.min(lo, v); hi = Math.max(hi, v); }
    });
    const pad = (hi - lo) * 0.08;
    if(this._yAnim){
      const e = Math.min(1, (performance.now() - this._yAnim.t0) / this._yAnim.dur);
      const p = 1 - Math.pow(1 - e, 3);
      this._yShift = this._yAnim.from + (this._yAnim.to - this._yAnim.from) * p;
      if(e >= 1) this._yAnim = null;
    }
    let ys = this._yShift || 0;
    this._pr = { pmin: lo - pad + ys, pmax: hi + pad + ys, hasV, vlow, vmid, vhigh, i0, i1, bars };
    return this._pr;
  }

  yOf(p){ const pr = this._pr; return this.TL + this.priceH - (p - pr.pmin) / (pr.pmax - pr.pmin) * this.priceH; }
  _volMax(){
    const vs = [];
    for(let i = this._pr.i0; i <= this._pr.i1; i++) vs.push(this.rows[i].v);
    vs.sort((a,b) => a - b);
    let vmax = vs.length ? vs[Math.min(vs.length - 1, Math.floor(vs.length * 0.98))] : 1;
    if(!isFinite(vmax) || vmax <= 0) vmax = 1;
    return vmax;
  }

  _growE(){
    if(!this._growAnim) return 1;
    const e = Math.min(1, (performance.now() - this._growAnim.t0) / this._growAnim.dur);
    if(e >= 1){ this._growAnim = null; return 1; }
    return 1 - Math.pow(1 - e, 3);   /* easeOutCubic，与 --ease-spring 一致 */
  }

  /* ---- Canvas 分层绘制 ---- */
  _drawGrid(ctx){
    const pr = this._pr, y = p => this.yOf(p);
    ctx.save();
    ctx.strokeStyle = this.C.hair;
    ctx.lineWidth = 1;
    ctx.setLineDash([2, 4]);   /* 虚线网格 */
    ctx.beginPath();
    ctx.rect(this.px0, this.TL, this.px1 - this.px0, this.priceH);
    ctx.clip();
    const step = niceStep(pr.pmax - pr.pmin, 5);
    for(let p = Math.ceil(pr.pmin / step) * step; p <= pr.pmax + 1e-9; p += step){
      const yy = Math.round(y(p)) + 0.5;
      ctx.beginPath(); ctx.moveTo(this.px0, yy); ctx.lineTo(this.px1, yy); ctx.stroke();
    }
    const dstep = Math.max(1, Math.ceil(60 / Math.max(this.slot, 0.5)));
    for(let i = pr.i0; i <= pr.i1; i += dstep){
      const x = Math.round(this.xOf(i)) + 0.5;
      ctx.beginPath(); ctx.moveTo(x, this.TL); ctx.lineTo(x, this.TL + this.priceH); ctx.stroke();
    }
    ctx.setLineDash([]);
    ctx.restore();
    /* 成交量副图分隔线（1px --hair） */
    if(!this.hideVol && this.volH > 8){
      ctx.strokeStyle = this.C.hair;
      ctx.lineWidth = 1;
      const yy = Math.round(this.volTop) + 0.5;
      ctx.beginPath(); ctx.moveTo(this.px0, yy); ctx.lineTo(this.px1, yy); ctx.stroke();
    }
  }

  _drawBands(ctx){
    const pr = this._pr;
    if(!pr.hasV) return;
    const yLow = this.yOf(pr.vlow), yMid = this.yOf(pr.vmid), yHigh = this.yOf(pr.vhigh);
    const w = this.px1 - this.px0;
    let hot = null;
    const hovered = this._tipIdx != null && this._tipIdx >= 0 && this._tipIdx < this.N ? this.rows[this._tipIdx] : null;
    if(hovered){
      const c = hovered.c;
      hot = c < pr.vlow ? 'low' : (c <= pr.vhigh ? 'mid' : 'high');
    }
    const A = {
      low:  hot === 'low' ? 0.12 : (hot ? 0.02 : 0.08),
      mid:  hot === 'mid' ? 0.12 : (hot ? 0.02 : 0.06),
      high: hot === 'high' ? 0.12 : (hot ? 0.02 : 0.06),
    };
    ctx.save();
    ctx.beginPath();
    ctx.rect(this.px0, this.TL, w, Math.max(1, this.priceH));
    ctx.clip();
    ctx.fillStyle = hexA(this.C.green, A.low);
    ctx.fillRect(this.px0, yLow, w, this.TL + this.priceH - yLow);
    ctx.fillStyle = hexA(this.C.blue, A.mid);
    ctx.fillRect(this.px0, yMid, w, yLow - yMid);
    ctx.fillStyle = hexA(this.C.red, A.high);
    ctx.fillRect(this.px0, this.TL, w, yMid - this.TL);
    ctx.setLineDash([6, 4]);
    ctx.lineWidth = 1;
    ctx.lineDashOffset = -this._dashShift || 0;
    ctx.strokeStyle = hot === 'low' ? hexA(this.C.green, .5) : hexA(this.C.green, .28);
    ctx.beginPath(); ctx.moveTo(this.px0, Math.round(yLow) + 0.5); ctx.lineTo(this.px1, Math.round(yLow) + 0.5); ctx.stroke();
    ctx.strokeStyle = hot === 'mid' ? hexA(this.C.blue, .5) : hexA(this.C.blue, .28);
    ctx.beginPath(); ctx.moveTo(this.px0, Math.round(yMid) + 0.5); ctx.lineTo(this.px1, Math.round(yMid) + 0.5); ctx.stroke();
    ctx.strokeStyle = hot === 'high' ? hexA(this.C.red, .5) : hexA(this.C.red, .28);
    ctx.beginPath(); ctx.moveTo(this.px0, Math.round(yHigh) + 0.5); ctx.lineTo(this.px1, Math.round(yHigh) + 0.5); ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();
  }

  _drawBreath(ctx){
    if(this.N < 2 || !this._pr) return;
    const x = this.xOf(this.N - 1);
    const yy = this.yOf(this.rows[this.N - 1].c);
    if(!isFinite(yy) || x < this.px0 - 4 || x > this.px1 + 4) return;
    const col = this._zoneColOf(this.rows[this.N - 1].c);
    const b = this.pinned ? 0.5 : (0.5 + 0.5 * Math.sin(Date.now() / 400));
    ctx.fillStyle = col;
    ctx.globalAlpha = 0.12 * b;
    ctx.beginPath(); ctx.arc(x, yy, 10, 0, Math.PI * 2); ctx.fill();
    ctx.globalAlpha = 0.25 * b;
    ctx.beginPath(); ctx.arc(x, yy, 6, 0, Math.PI * 2); ctx.fill();
    ctx.globalAlpha = 0.8;
    ctx.beginPath(); ctx.arc(x, yy, 3, 0, Math.PI * 2); ctx.fill();
    ctx.globalAlpha = 1;
  }

  _zoneColOf(c){
    const pr = this._pr;
    if(!pr || !pr.hasV) return this.C.blue;
    if(c < pr.vlow) return this.C.green;
    if(c < pr.vhigh) return this.C.blue;
    return this.C.red;
  }

  _zoneCard(c, pr){
    if(!pr.hasV) return null;
    const mob = this._isMobile;
    let name, col, dist;
    if(c < pr.vlow){ name = '深度低估'; col = this.C.green; dist = '低于保守线'; }
    else if(c < pr.vmid){ name = '低估区'; col = this.C.green; dist = '距基准线 ' + ((pr.vmid / c - 1) * 100).toFixed(1) + '%'; }
    else if(c <= pr.vhigh){ name = '合理区'; col = this.C.blue; dist = '距乐观线 ' + ((pr.vhigh / c - 1) * 100).toFixed(1) + '%'; }
    else { name = '高估区'; col = this.C.red; dist = '高于乐观线'; }
    const w = mob ? 110 : 140, h = mob ? 34 : 52;
    const x0 = this.px0 + 8;
    const svg = y0 => {
      let t = '<rect x="' + x0 + '" y="' + y0.toFixed(1) + '" width="' + w + '" height="' + h + '" rx="6" fill="' + this.C.bg2 + '" fill-opacity=".96" stroke="' + this.C.hair + '"/>';
      if(mob){
        t += '<text x="' + (x0 + 8) + '" y="' + (y0 + 14).toFixed(1) + '" font-size="10" font-weight="700" fill="' + col + '" font-family="SF Mono,monospace">' + csym(this.st) + fmt2(c) + '</text>'
           + '<text x="' + (x0 + 8) + '" y="' + (y0 + 27).toFixed(1) + '" font-size="10" fill="' + col + '" font-family="SF Mono,monospace">' + name + '</text>';
      } else {
        t += '<text x="' + (x0 + 8) + '" y="' + (y0 + 17).toFixed(1) + '" font-size="11" font-weight="700" fill="' + col + '" font-family="SF Mono,monospace">现价 ' + csym(this.st) + fmt2(c) + '</text>'
           + '<text x="' + (x0 + 8) + '" y="' + (y0 + 33).toFixed(1) + '" font-size="11" fill="' + col + '" font-family="SF Mono,monospace">处于 · ' + name + '</text>'
           + '<text x="' + (x0 + 8) + '" y="' + (y0 + 47).toFixed(1) + '" font-size="11" fill="' + this.C.sub + '" font-family="SF Mono,monospace">' + dist + '</text>';
      }
      return t;
    };
    return { w, h, svg };
  }

  _redrawCanvas(){
    this.layout();
    const ctx = this.ctx;
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.clearRect(0, 0, this.W, this.H);
    if(this.N < 2) return;
    this._dashShift = (this._dashShift + 0.5) % 10;
    this._range();
    this._drawGrid(ctx);
    this._drawBands(ctx);
    this._drawVolume(ctx);
    this._drawCandles(ctx);
    this._drawMAs(ctx);
    this._drawBreath(ctx);
  }

  _drawCandles(ctx){
    const y = p => this.yOf(p);
    const e = this._growE();
    const bodyW = Math.max(1, Math.min(12, this.slot * 0.72));
    const thin = this.slot < 2.2;
    if(this.slot < 1.2){ this._drawDense(ctx, y); return; }
    ctx.save();
    if(e < 1){
      ctx.translate(0, this.TL + this.priceH);
      ctx.scale(1, e);
      ctx.translate(0, -(this.TL + this.priceH));
    }
    for(let i = this._pr.i0; i <= this._pr.i1; i++){
      const r = this.rows[i];
      const cx = this.xOf(i);
      if(cx < this.px0 - 4 || cx > this.px1 + 4) continue;
      const up = r.c >= r.o;
      const col = up ? this.C.up : this.C.dn;
      if(!thin){
        ctx.strokeStyle = col;
        ctx.lineWidth = 1;
        const wx = Math.round(cx) + 0.5;
        ctx.beginPath();
        ctx.moveTo(wx, y(r.h));
        ctx.lineTo(wx, y(r.l));
        ctx.stroke();
      }
      const yo = y(Math.max(r.o, r.c));
      const bh = Math.max(1, Math.abs(y(r.o) - y(r.c)));
      const bw = Math.max(1, bodyW);
      if(this.hollow && up && !thin){
        ctx.strokeStyle = col;
        ctx.lineWidth = 1.2;
        ctx.strokeRect(cx - bw / 2, yo, bw, bh);
        ctx.fillStyle = hexA(this.C.up, .14);
        ctx.fillRect(cx - bw / 2, yo, bw, bh);
      } else {
        ctx.fillStyle = col;
        ctx.fillRect(cx - bw / 2, yo, bw, bh);
      }
    }
    ctx.restore();
  }

  _drawDense(ctx, y){
    ctx.save();
    ctx.beginPath();
    ctx.rect(this.px0, this.TL, this.px1 - this.px0, this.priceH);
    ctx.clip();
    ctx.fillStyle = hexA(this.C.blue, .08);
    ctx.beginPath();
    let started = false;
    for(let i = this._pr.i0; i <= this._pr.i1; i++){
      const cx = this.xOf(i), cy = y(this.rows[i].c);
      if(!started){ ctx.moveTo(cx, cy); started = true; }
      else ctx.lineTo(cx, cy);
    }
    ctx.lineTo(this.xOf(this._pr.i1), this.TL + this.priceH);
    ctx.lineTo(this.xOf(this._pr.i0), this.TL + this.priceH);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = this.C.blue;
    ctx.lineWidth = 1;
    ctx.beginPath();
    started = false;
    for(let i = this._pr.i0; i <= this._pr.i1; i++){
      const cx = this.xOf(i), cy = y(this.rows[i].c);
      if(!started){ ctx.moveTo(cx, cy); started = true; }
      else ctx.lineTo(cx, cy);
    }
    ctx.stroke();
    ctx.restore();
  }

  _drawVolume(ctx){
    if(this.hideVol) return;
    const vmax = this._volMax();
    const bodyW = Math.max(1.5, Math.min(12, this.slot * 0.7));
    for(let i = this._pr.i0; i <= this._pr.i1; i++){
      const r = this.rows[i];
      const cx = this.xOf(i);
      if(cx < this.px0 - 4 || cx > this.px1 + 4) continue;
      const up = r.c >= r.o;
      const col = up ? this.C.up : this.C.dn;
      const capped = r.v > vmax;
      const vh = Math.max(1.5, capped ? (this.volH - 8) : (r.v / vmax * (this.volH - 8)));
      ctx.globalAlpha = 0.32;
      ctx.fillStyle = col;
      ctx.fillRect(cx - bodyW / 2, this.volBot - vh, bodyW, vh);
      ctx.globalAlpha = 1;
      if(capped){ ctx.fillStyle = col; ctx.fillRect(cx - 1, this.volTop, 2, 2); }
    }
    [5,10].forEach(w => {
      const a = this.volC[w];
      if(!a) return;
      ctx.strokeStyle = w === 5 ? hexA(this.C.sub, .55) : hexA(this.C.sub, .32);
      ctx.lineWidth = 1;
      ctx.beginPath();
      let started = false;
      for(let i = this._pr.i0; i <= this._pr.i1; i++){
        const v = a[i];
        if(!isFinite(v)) continue;
        const cx = this.xOf(i);
        const cy = this.volBot - Math.max(1, v / vmax * (this.volH - 8));
        if(!started){ ctx.moveTo(cx, cy); started = true; }
        else ctx.lineTo(cx, cy);
      }
      ctx.stroke();
    });
  }

  _drawMAs(ctx){
    const y = p => this.yOf(p);
    const e = this._growE();
    ctx.save();
    if(e < 1){
      const cw = this.px0 + (this.px1 - this.px0) * e;
      ctx.beginPath();
      ctx.rect(this.px0, this.TL, Math.max(1, cw - this.px0), this.priceH);
      ctx.clip();
    }
    [5,10,20,60,120,250].forEach(w => {
      if(!this.maVis[w]) return;
      const a = this.maC[w];
      if(!a) return;
      ctx.strokeStyle = this._maCol[w];
      ctx.lineWidth = w <= 20 ? 1.5 : 1.2;
      ctx.setLineDash(MADASH[w]);
      ctx.beginPath();
      let started = false;
      for(let i = this._pr.i0; i <= this._pr.i1; i++){
        const m = a[i];
        if(!isFinite(m)) continue;
        const cx = this.xOf(i);
        const cy = y(m);
        if(!isFinite(cy)) continue;
        if(!started){ ctx.moveTo(cx, cy); started = true; }
        else ctx.lineTo(cx, cy);
      }
      ctx.stroke();
      ctx.setLineDash([]);
    });
    ctx.restore();
  }/* ---- SVG 覆盖层（锚线/S-R/斐波/标签/轴/徽章/十字光标） ---- */
  overlay(){
    const pr = this._pr;
    const s = [];
    const W = this.W, H = this.H, y = p => this.yOf(p);
    const small = W < 480;
    if(this.N < 2){
      s.push('<text x="' + (W/2).toFixed(1) + '" y="' + (H/2).toFixed(1) + '" text-anchor="middle" font-size="13" fill="' + this.C.sub + '">暂无足够K线数据</text>');
      this.sv.innerHTML = s.join('');
      this._ch = null;
      return;
    }
    s.push('<style>.srl{animation:srmarch .8s ease-out}@keyframes srmarch{to{stroke-dashoffset:-28}}.srtouch{animation:srflash .9s ease-out 1}@keyframes srflash{0%{stroke-width:2.6;opacity:1}100%{stroke-width:1;opacity:.55}}.sr-pulse{animation:srpulse 1.2s ease-in-out infinite}@keyframes srpulse{0%,100%{opacity:1}50%{opacity:.55}}.srlbl{animation:srlabel .4s ease-out}@keyframes srlabel{from{transform:translateX(-12px);opacity:0}to{transform:none;opacity:1}}</style>');
    const st = this.st;
    const priceB = this.TL + this.priceH;
    const lastClose = this.rows[this.N-1].c;
    const sup = (st.support||[]).filter(x => isFinite(+x.level) && (x.method||'').indexOf('估值锚') !== 0);
    const res = (st.resistance||[]).filter(x => isFinite(+x.level) && (x.method||'').indexOf('估值锚') !== 0);
    const edgeTop = [], edgeBot = [];
    const srLbls = [];
    const hl = [];
    const SR_STYLE = {
      A: {sw: 2.2, up: this.C.green, dn: this.C.red, op: .90, dash: ''},
      B: {sw: 1.6, up: hexA(this.C.green, .9), dn: hexA(this.C.red, .9), op: .75, dash: '8 4'},
      C: {sw: 1.2, up: hexA(this.C.green, .7), dn: hexA(this.C.red, .7), op: .55, dash: '4 4'},
    };
    const mo = this._isMobile ? 0.3 : 0;
    let srSeq = 0;

    const srRows = [];
    sup.forEach((sr, idx) => srRows.push({sr, isSup: true, idx}));
    res.forEach((sr, idx) => srRows.push({sr, isSup: false, idx}));
    const evOrder = {A: 0, B: 1, C: 2};
    const inViewRows = srRows.filter(rr => {
      const vv = +rr.sr.level;
      const yy = y(vv);
      return isFinite(yy) && yy >= this.TL - 6 && yy <= priceB + 6;
    });
    inViewRows.sort((a, b) => evOrder[a.sr.level_ev] - evOrder[b.sr.level_ev] || +a.sr.level - +b.sr.level);

    inViewRows.forEach(rr => {
      const sr = rr.sr, isSup = rr.isSup;
      const vv = +sr.level;
      const yy = y(vv);
      const ev = sr.level_ev === 'A' ? 'A' : (sr.level_ev === 'C' ? 'C' : 'B');
      const stl = SR_STYLE[ev];
      const touch = Math.abs(lastClose / vv - 1) <= 0.008;
      const lw = Math.max(0.9, stl.sw - mo + (touch ? 1 : 0));
      const col = touch ? (isSup ? '#0a5c28' : '#8b0000') : (isSup ? stl.up : stl.dn);
      const labCol = touch ? col : (isSup ? this.C.green : this.C.red);
      const cls = [];
      if(this._animateSR) cls.push('srl');
      if(touch) cls.push('sr-pulse');
      const cattr = cls.length ? ' class="' + cls.join(' ') + '"' : '';
      const lineId = 'sr-' + (srSeq++);
      const priceTxt = fmt0(vv);
      const methodTxt = (!this._isMobile && ev !== 'C') ? ((sr.method || '').slice(0, 8)) : '';
      const badgeW = this._isMobile ? 64 : (20 + 18 + priceTxt.length * 6.6 + (methodTxt ? methodTxt.length * 5.4 + 10 : 0) + 8);
      const x0 = Math.min(6 + badgeW + 30, this.px1 - 24);
      s.push('<line' + cattr + ' id="' + lineId + '" x1="' + x0.toFixed(0) + '" y1="' + yy.toFixed(1) + '" x2="' + this.px1 + '" y2="' + yy.toFixed(1) + '" stroke="' + col + '" stroke-width="' + lw.toFixed(1) + '"' + (stl.dash ? ' stroke-dasharray="' + stl.dash + '"' : '') + ' opacity="' + stl.op + '"/>');
      s.push('<line x1="' + (6 + badgeW + 2).toFixed(0) + '" y1="' + yy.toFixed(1) + '" x2="' + x0.toFixed(0) + '" y2="' + yy.toFixed(1) + '" stroke="' + col + '" stroke-width="1" stroke-dasharray="2 3" opacity=".4"/>');
      if(isSup){
        s.push('<polygon points="' + (x0 - 3).toFixed(0) + ',' + (yy - 2).toFixed(1) + ' ' + (x0 + 3).toFixed(0) + ',' + (yy - 2).toFixed(1) + ' ' + x0.toFixed(0) + ',' + (yy - 7).toFixed(1) + '" fill="' + col + '"/>');
      } else {
        s.push('<polygon points="' + (x0 - 3).toFixed(0) + ',' + (yy + 2).toFixed(1) + ' ' + (x0 + 3).toFixed(0) + ',' + (yy + 2).toFixed(1) + ' ' + x0.toFixed(0) + ',' + (yy + 7).toFixed(1) + '" fill="' + col + '"/>');
      }
      if(touch && !this._isMobile){
        s.push('<circle cx="' + (this.px1 - 4).toFixed(0) + '" cy="' + yy.toFixed(1) + '" r="8" fill="' + col + '" opacity=".15"/>'
             + '<circle cx="' + (this.px1 - 4).toFixed(0) + '" cy="' + yy.toFixed(1) + '" r="4" fill="' + col + '" opacity=".8"/>');
      }
      hl.push({id: lineId, yy, price: vv, name: sr.method || '', ev, isSup, sw: lw, op: stl.op, kind: 'sr'});
      if(inViewRows.length > 8 && ev === 'C') return;
      srLbls.push({y: yy, type: (isSup?'S':'R') + (rr.idx + 1), price: priceTxt, methodTxt, ev, isSup, col: labCol});
    });

    srRows.forEach(rr => {
      const vv = +rr.sr.level;
      const yy = y(vv);
      if(isFinite(yy) && yy >= this.TL - 6 && yy <= priceB + 6) return;
      const isSup = rr.isSup;
      const col = isSup ? this.C.green : this.C.red;
      if(vv > pr.pmax) edgeTop.push({lab: (isSup?'S':'R') + (rr.idx + 1) + ' ' + csym(this.st) + fmt0(vv), col, method: rr.sr.method || '', up: true, sup: isSup});
      else if(vv < pr.pmin) edgeBot.push({lab: (isSup?'S':'R') + (rr.idx + 1) + ' ' + csym(this.st) + fmt0(vv), col, method: rr.sr.method || '', up: false, sup: isSup});
    });

    packLbl(srLbls, 22).forEach(it => {
      if(it.yy < this.TL + 11 || it.yy > priceB - 11) return;
      const ev = it.ev;
      const bgA = hexA(it.isSup ? this.C.green : this.C.red, .12);
      const bgB = hexA(it.isSup ? this.C.green : this.C.red, .08);
      const badgeW = this._isMobile ? 64 : (20 + 18 + it.price.length * 6.6 + (it.methodTxt ? it.methodTxt.length * 5.4 + 10 : 0) + 8);
      const gOpen = this._animateSR ? '<g class="srlbl">' : '<g>';
      s.push(gOpen);
      if(ev === 'C'){
        s.push('<rect x="6" y="' + (it.yy - 10).toFixed(1) + '" width="' + badgeW.toFixed(0) + '" height="20" rx="10" fill="' + this.C.bg2 + '" fill-opacity=".95" stroke="' + it.col + '" stroke-width="1"/>');
      } else {
        s.push('<rect x="6" y="' + (it.yy - 10).toFixed(1) + '" width="' + badgeW.toFixed(0) + '" height="20" rx="10" fill="' + (ev === 'A' ? bgA : bgB) + '"/>');
      }
      if(ev === 'A') s.push('<circle cx="16" cy="' + it.yy.toFixed(1) + '" r="4" fill="' + it.col + '"/>');
      else if(ev === 'B') s.push('<circle cx="16" cy="' + it.yy.toFixed(1) + '" r="4" fill="' + it.col + '" opacity=".35"/><circle cx="16" cy="' + it.yy.toFixed(1) + '" r="2.2" fill="' + it.col + '"/>');
      else s.push('<circle cx="16" cy="' + it.yy.toFixed(1) + '" r="3.5" fill="none" stroke="' + it.col + '" stroke-width="1.2"/>');
      s.push('<text x="24" y="' + (it.yy + 3.5).toFixed(1) + '" font-size="10" font-weight="700" fill="' + it.col + '" font-family="SF Mono,monospace">' + it.type + '</text>');
      s.push('<text x="46" y="' + (it.yy + 4).toFixed(1) + '" font-size="11" font-weight="600" fill="' + it.col + '" font-family="SF Mono,monospace">' + csym(this.st) + it.price + '</text>');
      if(it.methodTxt){
        s.push('<text x="' + (52 + it.price.length * 6.6).toFixed(0) + '" y="' + (it.yy + 4).toFixed(1) + '" font-size="9" fill="' + this.C.sub + '" font-family="SF Mono,monospace">' + it.methodTxt + '</text>');
      }
      s.push('</g>');
    });

    const rightItems = [];
    let zoneY = this.TL + 14;
    if(pr.hasV){
      [['low', pr.vlow, this.C.green, hexA(this.C.green, .22), '保守', this.C.green, '6 4'],
       ['mid', pr.vmid, this.C.blue, hexA(this.C.blue, .22), '基准', this.C.blue, ''],
       ['high', pr.vhigh, this.C.red, hexA(this.C.red, .22), '乐观', this.C.red, '6 4']].forEach(a => {
        const yy = y(a[1]);
        if(isFinite(yy) && yy >= this.TL && yy <= priceB){
          const cls = this._animateSR ? ' class="srl"' : '';
          const dashAttr = a[6] ? ' stroke-dasharray="' + a[6] + '"' : '';
          s.push('<line' + cls + ' id="anchor-' + a[0] + '" x1="0" y1="' + yy.toFixed(1) + '" x2="' + this.px1 + '" y2="' + yy.toFixed(1) + '" stroke="' + a[2] + '" stroke-width="1.6" stroke-linecap="round"' + dashAttr + ' opacity=".8"/>'
               + '<circle cx="8" cy="' + yy.toFixed(1) + '" r="2.5" fill="' + a[2] + '"/>');
          rightItems.push({y: yy, lab: a[4] + ' ' + csym(this.st) + fmt2(a[1]), col: a[2], bg: a[3], bar: a[5]});
          hl.push({id: 'anchor-' + a[0], yy, price: a[1], name: '估值锚 V_' + a[0] + '（' + a[4] + '）', ev: 'A', isSup: a[0] !== 'high', sw: 1.6, op: .7, kind: 'anchor'});
        }
      });
      let guard = 0;
      while(guard++ < 12){
        const hit = srLbls.find(l => Math.abs(zoneY + 26 - l.yy) < 30);
        if(!hit) break;
        zoneY = hit.yy + 28;
      }
      const zoneCard = this._zoneCard(lastClose, pr);
      if(zoneCard && zoneY + zoneCard.h <= priceB - 4){
        s.push(zoneCard.svg(zoneY));
      }
      const zCur = lastClose < pr.vlow ? 'low' : (lastClose <= pr.vhigh ? 'mid' : 'high');
      const zLabels = [
        {key: 'high', t: '高估区', col: this.C.red, y0: this.TL, y1: y(pr.vhigh)},
        {key: 'mid', t: '合理区', col: this.C.blue, y0: y(pr.vhigh), y1: y(pr.vlow)},
        {key: 'low', t: '低估区', col: this.C.green, y0: y(pr.vlow), y1: priceB},
      ];
      const zFs = small ? 10 : 12;
      zLabels.forEach(z => {
        if(z.y1 - z.y0 < 26) return;
        const yy = z.y0 + 15;
        s.push('<text x="' + (this.px1 - 8) + '" y="' + yy.toFixed(1) + '" text-anchor="end" font-size="' + zFs + '" font-weight="700" fill="' + z.col + '" opacity="' + (z.key === zCur ? '.9' : '.55') + '" font-family="PingFang SC,Microsoft YaHei,sans-serif">' + z.t + '</text>');
      });
      if(!st.decision_usable && W >= 560 && (zoneY > this.TL + 80 || !zoneCard)){
        s.push('<rect x="6" y="' + this.TL + '" width="150" height="22" rx="4" fill="' + this.C.bg2 + '" fill-opacity=".94" stroke="' + this.C.hair + '"/>'
             + '<text x="14" y="' + (this.TL + 15) + '" font-size="12" fill="' + this.C.sub2 + '" font-weight="600">参考区间 · 不可执行</text>');
      }
    } else if(isFinite(+st.v_low) && isFinite(+st.v_high)){
      edgeBot.push({lab: 'V_low ' + csym(this.st) + fmt0(+st.v_low), col: this.C.green, method: '', up: false, sup: true});
      edgeTop.push({lab: 'V_high ' + csym(this.st) + fmt0(+st.v_high), col: this.C.red, method: '', up: true, sup: false});
    }

    if(this.N >= 60 && this.barsPerView() >= Math.min(this.N, 240)){
      const seg = this.rows.slice(-250);
      const lo = Math.min.apply(null, seg.map(r => r.l));
      const hi = Math.max.apply(null, seg.map(r => r.h));
      if(hi - lo > 0){
        [0.382, 0.5, 0.618].forEach(rt => {
          const p = lo + (hi - lo) * rt;
          const yy = y(p);
          if(isFinite(yy) && yy >= this.TL && yy <= priceB){
            s.push('<line x1="0" y1="' + yy.toFixed(1) + '" x2="' + this.px1 + '" y2="' + yy.toFixed(1) + '" stroke="' + this.C.gold + '" stroke-width="1" stroke-dasharray="2 4" opacity=".5"/>');
            if(W >= 560) rightItems.push({y: yy, lab: rt + ' ' + csym(this.st) + fmt2(p), col: this.C.gold, bg: hexA(this.C.bg2, .9)});
          }
        });
      }
    }

    [5,10,20,60,120,250].forEach(w => {
      if(!this.maVis[w] || !this.maC[w]) return;
      const v = this.maC[w][this._pr.i1];
      if(!isFinite(v)) return;
      const yy = y(v);
      if(!isFinite(yy) || yy < this.TL - 4 || yy > priceB + 4) return;
      s.push('<circle cx="' + (this.px1 - 2).toFixed(1) + '" cy="' + yy.toFixed(1) + '" r="2.4" fill="' + this._maCol[w] + '"/>');
      if(W >= 560) rightItems.push({y: yy, lab: 'MA' + w + ' ' + fmt2(v), col: this._maCol[w], bg: hexA(this.C.bg2, .92)});
    });

    const chW = small ? 5.2 : 6.3;
    const maxChars = Math.max(4, Math.floor((this.GUT - 14) / chW));
    packLblMutual(srLbls, rightItems, 22, 17, 18).forEach(it => {
      if(it._hidden) return;
      if(it.yy < this.TL + 9 || it.yy > priceB - 9) return;
      let lab = it.lab;
      if(lab.length > maxChars) lab = lab.slice(0, maxChars);
      const wdt = Math.min(this.GUT - 10, 12 + lab.length * chW);
      const xR = this.px1 + this.GUT - 6;
      s.push('<line x1="' + this.px1.toFixed(0) + '" y1="' + it.y.toFixed(1) + '" x2="' + (this.px1 + 4).toFixed(0) + '" y2="' + it.y.toFixed(1) + '" stroke="' + it.col + '" stroke-width="1" opacity=".45"/>');
      if(Math.abs(it.yy - it.y) > 3){
        s.push('<line x1="' + (this.px1 + 4).toFixed(0) + '" y1="' + it.y.toFixed(1) + '" x2="' + (this.px1 + 4).toFixed(0) + '" y2="' + it.yy.toFixed(1) + '" stroke="' + it.col + '" stroke-width="1" opacity=".45"/>');
      }
      if(it.bar){
        s.push('<rect x="' + (xR - wdt - 6).toFixed(0) + '" y="' + (it.yy - 8).toFixed(1) + '" width="3" height="16" rx="1.5" fill="' + it.bar + '"/>');
      }
      s.push('<rect x="' + (xR - wdt).toFixed(0) + '" y="' + (it.yy - 8).toFixed(1) + '" width="' + wdt.toFixed(0) + '" height="16" rx="4" fill="' + it.bg + '"/>'
           + '<text x="' + (xR - wdt + 5).toFixed(0) + '" y="' + (it.yy + 3.5).toFixed(1) + '" font-size="' + (small ? 10 : 11) + '" font-weight="600" fill="' + it.col + '" font-family="SF Mono,monospace">' + lab + '</text>');
    });

    const crossSeen = [];
    for(const c of this.crosses){
      if(c.i < this._pr.i0 || c.i > this._pr.i1) continue;
      const x = this.xOf(c.i);
      if(x < this.px0 + 20 || x > this.px1 - 20) continue;
      const r = this.rows[c.i];
      const yy = c.up ? y(r.h) - 10 : y(r.l) + 18;
      if(!isFinite(yy) || yy < this.TL + 9 || yy > priceB - 9) continue;
      crossSeen.push({x, yy, up: c.up});
    }
    if(crossSeen.length > 8) crossSeen.splice(0, crossSeen.length - 8);
    crossSeen.forEach(k => {
      s.push('<text x="' + k.x.toFixed(1) + '" y="' + k.yy.toFixed(1) + '" text-anchor="middle" font-size="9" fill="' + (k.up ? this.C.green : this.C.red) + '">' + (k.up ? '▲金叉' : '▼死叉') + '</text>');
    });

    const lm = [];
    for(let i = this._pr.i0; i <= this._pr.i1; i++){
      const r = this.rows[i];
      if(!(r.o > 0)) continue;
      const x = this.xOf(i);
      if(x < this.px0 + 12 || x > this.px1 - 12) continue;
      const chg = (r.c - r.o) / r.o;
      if(chg > 0.095) lm.push({x, yy: y(r.h) - 16, t: '涨', col: this.C.up});
      else if(chg < -0.095) lm.push({x, yy: y(r.h) - 16, t: '跌', col: this.C.dn});
    }
    if(lm.length > 6) lm.splice(0, lm.length - 6);
    lm.forEach(k => {
      s.push('<rect x="' + (k.x - 8).toFixed(1) + '" y="' + k.yy.toFixed(1) + '" width="16" height="16" rx="3" fill="' + k.col + '"/>'
           + '<text x="' + k.x.toFixed(1) + '" y="' + (k.yy + 11).toFixed(1) + '" text-anchor="middle" font-size="11" fill="#ffffff">' + k.t + '</text>');
    });

    const vmax = this._volMax();
    const va5 = this.volC[5];
    const fang = [], brk = [];
    const rmax = res.length ? Math.max.apply(null, res.map(x => +x.level)) : null;
    for(let i = this._pr.i0; i <= this._pr.i1; i++){
      const r = this.rows[i];
      const x = this.xOf(i);
      if(x < this.px0 + 10 || x > this.px1 - 10) continue;
      if(va5 && isFinite(va5[i]) && va5[i] > 0 && r.v > va5[i] * 2){
        fang.push({x, yy: Math.max(this.volTop + 10, this.volBot - Math.max(1.5, r.v / vmax * (this.volH - 8)) - 6)});
      }
      if(isFinite(rmax) && i > 0 && r.c > rmax && this.rows[i-1].c <= rmax && va5 && isFinite(va5[i]) && r.v > va5[i] * 1.5){
        brk.push({x, yy: y(r.h) - 26});
      }
    }
    if(fang.length > 6) fang.splice(0, fang.length - 6);
    fang.forEach(k => {
      s.push('<text x="' + k.x.toFixed(1) + '" y="' + k.yy.toFixed(1) + '" text-anchor="middle" font-size="9" fill="' + this.C.gold + '">放量</text>');
    });
    if(brk.length > 3) brk.splice(0, brk.length - 3);
    brk.forEach(k => {
      s.push('<text x="' + k.x.toFixed(1) + '" y="' + k.yy.toFixed(1) + '" text-anchor="middle" font-size="9" fill="' + this.C.gold + '" font-weight="700">突破</text>');
    });

    const yc = y(lastClose);
    if(isFinite(yc) && yc >= this.TL && yc <= priceB){
      s.push('<line x1="0" y1="' + yc.toFixed(1) + '" x2="' + this.px1 + '" y2="' + yc.toFixed(1) + '" stroke="' + this.C.blue + '" stroke-width="1" opacity=".35"/>'
           + '<polygon points="' + (this.px1 + 7) + ',' + (yc - 3.5).toFixed(1) + ' ' + (this.px1 + 7) + ',' + (yc + 3.5).toFixed(1) + ' ' + (this.px1 + 2) + ',' + yc.toFixed(1) + '" fill="' + this.C.blue + '"/>');
    }
    if(pr.hasV){
      const yLow = y(pr.vlow), yHigh = y(pr.vhigh);
      s.push('<defs><linearGradient id="vGauge" x1="0" y1="0" x2="0" y2="1">'
           + '<stop offset="0" stop-color="' + this.C.red + '"/><stop offset=".5" stop-color="' + this.C.blue + '"/><stop offset="1" stop-color="' + this.C.green + '"/>'
           + '</linearGradient></defs>'
           + '<rect x="' + (this.axX - 8) + '" y="' + yHigh.toFixed(1) + '" width="5" height="' + Math.max(1, yLow - yHigh).toFixed(1) + '" rx="2.5" fill="url(#vGauge)" opacity=".55"/>');
      if(isFinite(yc) && yc >= yHigh - 1 && yc <= yLow + 1){
        s.push('<circle cx="' + (this.axX - 5.5).toFixed(1) + '" cy="' + yc.toFixed(1) + '" r="3" fill="' + this.C.blue + '" stroke="#ffffff" stroke-width="1.5"/>');
      }
    }

    const step = niceStep(pr.pmax - pr.pmin, 5);
    const yFs = small ? 10 : 11;
    for(let p = Math.ceil(pr.pmin / step) * step; p <= pr.pmax + 1e-9; p += step){
      const yy = y(p);
      if(!isFinite(yy) || yy < this.TL - 2 || yy > priceB + 2) continue;
      s.push('<text x="' + (this.axX + 7) + '" y="' + (yy + 3.5).toFixed(1) + '" font-size="' + yFs + '" fill="' + this.C.sub2 + '" font-family="SF Mono,monospace">' + fmt2(p) + '</text>');
    }

    const dstep = Math.max(1, Math.ceil(88 / Math.max(this.slot, 0.5)));
    let lastDx = -Infinity;
    for(let i = this._pr.i0; i <= this._pr.i1; i++){
      if(i % dstep !== 0 && i !== this.N - 1) continue;
      const x = this.xOf(i);
      if(x < this.px0 || x > this.px1) continue;
      if(x - lastDx < (small ? 56 : 80)) continue;
      lastDx = x;
      const d = String(this.rows[i].d || '').slice(2, 10);
      const day = String(this.rows[i].d || '').slice(8, 10);
      if(small && day !== '01' && i !== this.N - 1) continue;
      s.push('<text x="' + x.toFixed(1) + '" y="' + (this.volBot + 16) + '" font-size="' + yFs + '" fill="' + this.C.sub2 + '" text-anchor="middle" font-family="SF Mono,monospace">' + d + '</text>');
    }

    const edge = (arr, yTop) => {
      let ex = 6;
      arr.slice(0, 3).forEach(x => {
        const yy = yTop ? this.TL + 4 : priceB - 20;
        const lab = (x.up ? '↑ ' : '↓ ') + x.lab;
        const wdt = 16 + lab.length * 6.2;
        s.push('<rect x="' + ex + '" y="' + yy + '" width="' + wdt.toFixed(0) + '" height="16" rx="4" fill="' + this.C.bg2 + '" fill-opacity=".92" stroke="' + this.C.hair + '" opacity=".85">'
             + '<title>' + x.method + '</title></rect>'
             + '<text x="' + (ex + 8) + '" y="' + (yy + 11.5) + '" font-size="11" fill="' + x.col + '" font-family="SF Mono,monospace">' + lab + '</text>');
        ex += wdt + 6;
      });
    };
    if(edgeTop.length) edge(edgeTop, true);
    if(edgeBot.length) edge(edgeBot, false);

    s.push('<g id="hoverHl" opacity="0">'
      + '<rect id="hoverHlR" x="0" y="0" width="120" height="38" rx="6" fill="' + this.C.bg2 + '" fill-opacity=".96" stroke="' + this.C.hair + '"/>'
      + '<text id="hoverHlT1" x="8" y="0" font-size="11" font-weight="700" fill="' + this.C.ink + '" font-family="SF Mono,monospace"></text>'
      + '<text id="hoverHlT2" x="8" y="0" font-size="10" fill="' + this.C.sub + '" font-family="SF Mono,monospace"></text>'
      + '</g>');

    const crossCol = hexA(this.C.blue, .35);
    s.push('<g id="chG" opacity="0">'
      + '<line id="chV" x1="0" y1="0" x2="0" y2="0" stroke="' + crossCol + '" stroke-width="1" stroke-dasharray="3 3"/>'
      + '<line id="chH" x1="0" y1="0" x2="0" y2="0" stroke="' + crossCol + '" stroke-width="1" stroke-dasharray="3 3"/>'
      + '<rect id="chYpill" x="0" y="0" width="' + (this.AX - 4) + '" height="16" rx="4" fill="' + this.C.ink + '" opacity="0"/>'
      + '<text id="chYtxt" x="0" y="0" font-size="11" fill="#ffffff" font-family="SF Mono,monospace"></text>'
      + '<rect id="chXpill" x="0" y="0" width="78" height="16" rx="4" fill="' + this.C.ink + '" opacity="0"/>'
      + '<text id="chXtxt" x="0" y="0" font-size="11" fill="#ffffff" text-anchor="middle" font-family="SF Mono,monospace"></text>'
      + '<circle id="chDot" r="4" fill="' + this.C.blue + '" stroke="#ffffff" stroke-width="2" opacity="0"/>'
      + '</g>');
    this.sv.innerHTML = s.join('');
    this._ch = {
      g: document.getElementById('chG'),
      v: document.getElementById('chV'), h: document.getElementById('chH'),
      ypill: document.getElementById('chYpill'), ytxt: document.getElementById('chYtxt'),
      xpill: document.getElementById('chXpill'), xtxt: document.getElementById('chXtxt'),
      dot: document.getElementById('chDot')
    };
    this._hl = hl;
    this._animateSR = false;
  }

  /* ---- 主绘制入口 ---- */
  draw(){
    this._redrawCanvas();
    this.overlay();
    if(this.pinned && this.pinIdx >= 0 && this._pinY != null) this._updateCross(this.pinIdx, this._pinY);
  }

  _scheduleDraw(){
    if(this._raf) return;
    this._raf = requestAnimationFrame(() => { this._raf = 0; this.draw(); });
  }

  /* ---- 十字光标与 Tooltip ---- */
  _barAt(mx){
    const bi = Math.round((mx - this.px0) / Math.max(this.slot, 0.05) + this.viewStart - 0.5);
    return Math.max(0, Math.min(this.N - 1, bi));
  }

  _hideCross(){
    if(this._ch) this._ch.g.setAttribute('opacity', '0');
    if(this._tipIdx !== -1){ this._tipIdx = -1; this._scheduleDraw(); }
  }

  _updateCross(bi, my){
    const ch = this._ch;
    if(!ch || bi < 0 || bi >= this.N){ if(ch) ch.g.setAttribute('opacity','0'); return; }
    const x = this.xOf(bi);
    const cy = Math.max(this.TL, Math.min(this.volBot, my));
    const inPrice = cy <= this.TL + this.priceH;
    ch.g.setAttribute('opacity', '1');
    ch.v.setAttribute('x1', x.toFixed(1)); ch.v.setAttribute('x2', x.toFixed(1));
    ch.v.setAttribute('y1', this.TL); ch.v.setAttribute('y2', this.volBot);
    const r = this.rows[bi];
    ch.dot.setAttribute('cx', x.toFixed(1)); ch.dot.setAttribute('cy', this.yOf(r.c).toFixed(1));
    ch.dot.setAttribute('opacity', '1');
    if(inPrice){
      const p = this._pr.pmin + (this._pr.pmax - this._pr.pmin) * (1 - (cy - this.TL) / this.priceH);
      ch.h.setAttribute('x1', this.px0); ch.h.setAttribute('x2', this.px1);
      ch.h.setAttribute('y1', cy.toFixed(1)); ch.h.setAttribute('y2', cy.toFixed(1));
      ch.h.setAttribute('opacity', '1');
      const ly = Math.max(this.TL, Math.min(this.TL + this.priceH - 16, cy - 8));
      ch.ypill.setAttribute('x', this.axX + 1); ch.ypill.setAttribute('y', ly.toFixed(1));
      ch.ypill.setAttribute('opacity', '1');
      ch.ytxt.setAttribute('x', this.axX + 5); ch.ytxt.setAttribute('y', (ly + 11.5).toFixed(1));
      ch.ytxt.textContent = fmt2(p);
    } else {
      ch.h.setAttribute('opacity', '0');
      ch.ypill.setAttribute('opacity', '0');
      ch.ytxt.textContent = '';
    }
    const lx = Math.max(this.px0, Math.min(this.px1 - 78, x - 39));
    ch.xpill.setAttribute('x', lx.toFixed(1)); ch.xpill.setAttribute('y', this.volBot + 2);
    ch.xpill.setAttribute('opacity', '1');
    ch.xtxt.setAttribute('x', (lx + 39).toFixed(1)); ch.xtxt.setAttribute('y', this.volBot + 13);
    ch.xtxt.textContent = String(r.d || '');
  }

  _renderTip(bi){
    if(bi < 0 || bi >= this.N){ this.tip.innerHTML = ''; return; }
    const r = this.rows[bi];
    const pr = this._pr;
    const st = this.st;
    const prev = bi > 0 ? this.rows[bi - 1].c : r.c;
    const chg = r.c - prev;
    const pct = prev ? chg / prev * 100 : 0;
    const ccol = chg > 0 ? this.C.up : (chg < 0 ? this.C.dn : this.C.sub);
    const volTxt = r.v >= 1e8 ? (r.v / 1e8).toFixed(2) + '亿' : (r.v / 1e4).toFixed(1) + '万';
    const amtTxt = (r.v * r.c) >= 1e8 ? ((r.v * r.c) / 1e8).toFixed(2) + '亿' : ((r.v * r.c) / 1e4).toFixed(1) + '万';
    const ampTxt = prev > 0 ? ((r.h - r.l) / prev * 100).toFixed(2) + '%' : '—';
    const wk = ['周日','周一','周二','周三','周四','周五','周六'][new Date(r.d + 'T00:00:00').getDay()] || '';
    const zm = zmeta(st);
    const zoneCol = [this.C.green, this.C.green, this.C.gold, this.C.gold, this.C.red, this.C.red, this.C.sub][zm.c] || this.C.sub;
    let t = '<div class="ztip"><span class="zone-badge" style="background:' + hexA(this.C.sub, .12) + ';color:' + zoneCol + '">' + (st.decision_usable ? zm.label : (st.reference_zone ? '参考 ' + st.reference_zone : zm.label)) + '</span>'
      + '<span class="kdate">' + r.d + ' ' + wk + '</span></div>'
      + '<div class="krow"><span class="tk">开盘</span><span>' + fmt2(r.o) + '</span><span class="tk">最高</span><span>' + fmt2(r.h) + '</span></div>'
      + '<div class="krow"><span class="tk">收盘</span><b style="color:' + ccol + '">' + fmt2(r.c) + '</b><span class="tk">最低</span><span>' + fmt2(r.l) + '</span></div>'
      + '<div class="krow"><span class="tk">涨跌</span><b style="color:' + ccol + '">' + (chg >= 0 ? '+' : '') + fmt2(chg) + ' (' + (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%)</b></div>'
      + '<div class="krow"><span class="tk">幅·量·额</span><span>' + ampTxt + ' / ' + volTxt + ' / ' + amtTxt + '</span></div>';
    const va5 = this.volC[5] && isFinite(this.volC[5][bi]) && this.volC[5][bi] > 0 ? this.volC[5][bi] : null;
    if(va5) t += '<div class="krow"><span class="tk">量比</span><span>VOL5 ' + (r.v / va5).toFixed(2) + '×</span></div>';
    let mline = '';
    [5,10,20,60,120,250].forEach(w => {
      if(this.maVis[w] && this.maC[w] && isFinite(this.maC[w][bi])) mline += '<span class="mma"><i style="background:' + this._maCol[w] + '"></i>MA' + w + ' ' + fmt2(this.maC[w][bi]) + '</span>';
    });
    if(mline) t += '<div class="krow ma">' + mline + '</div>';
    if(pr.hasV){
      let z = null;
      if(r.c < pr.vlow) z = {t: '深度低估', c: this.C.green};
      else if(r.c < pr.vmid) z = {t: '低估区', c: this.C.green};
      else if(r.c <= pr.vhigh) z = {t: '合理区', c: this.C.blue};
      else z = {t: '高估区', c: this.C.red};
      const dv = (r.c / pr.vlow - 1) * 100;
      t += '<div class="krow"><span class="tk">估值位置</span><b style="color:' + z.c + '">' + z.t + '</b><span>距保守 ' + csym(st) + fmt2(pr.vlow) + ' ' + (dv >= 0 ? '+' : '') + dv.toFixed(1) + '%</span></div>';
    }
    const supLv = (st.support || []).map(x => ({v: +x.level, m: x.method || ''})).filter(x => isFinite(x.v) && x.v > 0);
    const resLv = (st.resistance || []).map(x => ({v: +x.level, m: x.method || ''})).filter(x => isFinite(x.v) && x.v > 0);
    const nearS = supLv.filter(x => x.v < r.c).sort((a,b) => b.v - a.v)[0];
    const nearR = resLv.filter(x => x.v > r.c).sort((a,b) => a.v - b.v)[0];
    const mShort = m => m ? (m.length > 10 ? m.slice(0, 10) + '…' : m) : '';
    if(nearS || nearR){
      const inS = nearS && Math.abs(r.c / nearS.v - 1) <= 0.02;
      const inR = nearR && Math.abs(r.c / nearR.v - 1) <= 0.02;
      t += '<div class="krow"><span class="tk">最近</span>'
        + (nearS ? '<span class="' + (inS ? 'near-s' : '') + '">支撑 ' + csym(st) + fmt2(nearS.v) + '</span>' + (mShort(nearS.m) ? '<span>（' + mShort(nearS.m) + '）</span>' : '') : '')
        + (nearS && nearR ? '<span>　</span>' : '')
        + (nearR ? '<span class="' + (inR ? 'near-r' : '') + '">阻力 ' + csym(st) + fmt2(nearR.v) + '</span>' + (mShort(nearR.m) ? '<span>（' + mShort(nearR.m) + '）</span>' : '') : '')
        + '</div>';
    }
    this.tip.innerHTML = t;
    const live = document.getElementById('chartLive');
    if(live){
      const zmTxt = (st.decision_usable ? zm.label : (st.reference_zone ? '参考 ' + st.reference_zone : zm.label));
      live.textContent = r.d + ' 收盘 ' + fmt2(r.c) + ' 涨跌 ' + (chg>=0?'+':'') + fmt2(chg) + ' ' + (pct>=0?'+':'') + pct.toFixed(2) + '%，估值区 ' + zmTxt + '，成交量 ' + volTxt;
    }
    const spark = (() => {
      const pts = [];
      for(let k = 0; k < 3; k++){
        const j = bi - 2 + k;
        if(j >= 0 && j < this.N) pts.push({d: this.rows[j].d, c: this.rows[j].c});
      }
      if(pts.length < 2) return '';
      const min = Math.min.apply(null, pts.map(p => p.c)), max = Math.max.apply(null, pts.map(p => p.c));
      const rng = (max - min) || 1;
      const W = 120, H = 20, pad = 3;
      const x = i => pad + i * (W - pad * 2) / (pts.length - 1);
      const y = c => H - pad - (c - min) / rng * (H - pad * 2);
      const line = pts.map((p, i) => x(i).toFixed(1) + ',' + y(p.c).toFixed(1)).join(' ');
      const up = pts[pts.length - 1].c >= pts[0].c;
      const col = up ? 'var(--candle-up)' : 'var(--candle-dn)';
      return '<svg class="spark" width="' + W + '" height="' + H + '" aria-hidden="true" viewBox="0 0 ' + W + ' ' + H + '">'
        + '<polyline points="' + line + '" stroke="' + col + '"/>'
        + '<circle class="last-dot" cx="' + x(pts.length - 1).toFixed(1) + '" cy="' + y(pts[pts.length - 1].c).toFixed(1) + '" r="2"/>'
        + '</svg>';
    })();
    if(spark) this.tip.insertAdjacentHTML('beforeend', spark);
  }

  /* Tooltip 定位：默认右下方 12px，超出画布自动翻转（不写死 left/top） */
  _positionTip(mx, my){
    if(this._isMobile) return;
    const tw = this.tip.offsetWidth || 200, th = this.tip.offsetHeight || 120;
    let lx = mx + 12, ty = my + 12;
    if(lx + tw > this.W - 6) lx = mx - tw - 12;
    if(ty + th > this.H - 6) ty = my - th - 12;
    this.tip.style.left = Math.max(2, lx) + 'px';
    this.tip.style.top = Math.max(2, ty) + 'px';
  }/* ---- hover 高亮：S/R 线与估值锚线（≤6px）聚焦 ---- */
  _hoverCheck(mx, my){
    const hls = this._hl || [];
    let hit = null, best = 6;
    for(const h of hls){
      const d = Math.abs(my - h.yy);
      if(d < best){ best = d; hit = h; }
    }
    if(hit){
      clearTimeout(this._hoverT);
      this._hoverT = null;
      if(!this._hoverOn){ this._hoverOn = true; }
      for(const h of hls){
        const el = document.getElementById(h.id);
        if(!el) continue;
        if(h === hit){
          el.setAttribute('stroke-width', (h.sw + 1.5).toFixed(1));
          el.setAttribute('opacity', '1');
        } else {
          el.setAttribute('opacity', '0.3');
        }
      }
      const g = document.getElementById('hoverHl');
      if(g){
        const name = hit.kind === 'anchor' ? hit.name : (hit.name || ((hit.isSup ? '支撑' : '压力') + '位'));
        const t1 = (hit.kind === 'anchor' ? '' : (hit.ev + '级 ')) + name.slice(0, 14) + ' ' + csym(this.st) + fmt2(hit.price);
        const t2 = hit.kind === 'anchor' ? '估值锚边界' : ((hit.isSup ? '支撑 S' : '压力 R') + ' · ' + hit.ev + '级强度');
        const r1 = document.getElementById('hoverHlT1'), r2 = document.getElementById('hoverHlT2');
        if(r1){ r1.textContent = t1; }
        if(r2){ r2.textContent = t2; }
        const tw = Math.max(100, (t1.length > t2.length ? t1.length : t2.length) * 6.4 + 16);
        const rr = document.getElementById('hoverHlR');
        if(rr) rr.setAttribute('width', tw.toFixed(0));
        let gx = mx + 14, gy = my + 10;
        if(gx + tw > this.W - 6) gx = mx - tw - 14;
        if(gy + 38 > this.H - 6) gy = my - 48;
        g.setAttribute('transform', 'translate(' + Math.max(2, gx).toFixed(0) + ',' + Math.max(2, gy).toFixed(0) + ')');
        r1.setAttribute('y', '14'); r2.setAttribute('y', '30');
        g.setAttribute('opacity', '1');
      }
    } else {
      if(this._hoverOn){
        this._hoverOn = false;
        clearTimeout(this._hoverT);
        this._hoverT = setTimeout(() => { this._hoverReset(); }, 200);
      }
    }
  }

  _hoverReset(){
    const hls = this._hl || [];
    for(const h of hls){
      const el = document.getElementById(h.id);
      if(!el) continue;
      el.setAttribute('stroke-width', h.sw);
      el.setAttribute('opacity', h.op);
    }
    const g = document.getElementById('hoverHl');
    if(g) g.setAttribute('opacity', '0');
  }

  /* ---- scrollToPrice：图例点击 → 居中或闪烁 ---- */
  scrollToPrice(level){
    if(!this._pr || !isFinite(+level)) return;
    const pr = this._pr;
    if(level >= pr.pmin && level <= pr.pmax){
      this._flashSR(level);
      return;
    }
    this._centerOn(level);
  }

  _flashSR(level){
    const hit = (this._hl || []).find(h => h.kind === 'sr' && Math.abs(h.price - level) < 0.005);
    if(!hit) return;
    const el = document.getElementById(hit.id);
    if(!el) return;
    el.classList.add('sr-pulse');
    clearTimeout(this._flashT);
    this._flashT = setTimeout(() => {
      try{ el.classList.remove('sr-pulse'); }catch(err){}
    }, 2400);
  }

  _centerOn(level){
    const pr = this._pr;
    const mid = (pr.pmin + pr.pmax) / 2;
    this._yAnim = { from: this._yShift || 0, to: mid - level, t0: performance.now(), dur: 400 };
    this._startLoop();
  }

  _resetYShift(){
    this._yShift = 0;
    this._yAnim = null;
  }

  /* ---- 交互：拖拽平移（200ms 惯性） / 点击固定 / 滚轮缩放（指针居中，最少20根） ---- */
  _onDown(e){
    if(e.button !== 0 || this.N < 2) return;
    this._drag = { startX: e.clientX, startY: e.clientY, vs: this.viewStart, lastX: e.clientX, lastT: performance.now(), vx: 0 };
    try{ this.sv.setPointerCapture(e.pointerId); }catch(err){}
  }

  _onUp(e){
    const d = this._drag; this._drag = null;
    if(!d) return;
    const dist = Math.hypot(e.clientX - d.startX, e.clientY - d.startY);
    if(dist < 5){
      const rect = this.sv.getBoundingClientRect();
      if(rect.width < 2) return;
      const mx = (e.clientX - rect.left) * this.W / rect.width;
      const my = (e.clientY - rect.top) * this.H / rect.height;
      const bi = this._barAt(mx);
      if(this.pinned && bi === this.pinIdx){
        this.pinned = false; this.pinIdx = -1; this._pinY = null;
        this._hideCross(); this.tip.classList.remove('show');
        this._startLoop();
      } else {
        this.pinned = true; this.pinIdx = bi; this._pinY = my; this._tipIdx = bi;
        this._renderTip(bi);
        this._updateCross(bi, my);
        this._positionTip(mx, my);
        this.tip.classList.add('show');
      }
      return;
    }
    /* 平移惯性：按 200ms 的 easeOut 衰减继续滑动 */
    if(Math.abs(d.vx) > 0.6){
      this._glideTo(this.viewStart - d.vx * 220, 200);
    }
  }

  _glideTo(tVS, dur){
    if(this._anim) cancelAnimationFrame(this._anim);
    const fVS = this.viewStart;
    const t0 = performance.now(), D = dur || 200;
    const step = now => {
      const p = Math.min(1, (now - t0) / D);
      const e = 1 - Math.pow(1 - p, 3);
      this.viewStart = fVS + (tVS - fVS) * e;
      this._clampView();
      this.draw();
      if(p < 1) this._anim = requestAnimationFrame(step);
      else this._anim = null;
    };
    this._anim = requestAnimationFrame(step);
  }

  _onMove(e){
    if(this.N < 2) return;
    const rect = this.sv.getBoundingClientRect();
    if(rect.width < 2) return;
    const mx = (e.clientX - rect.left) * this.W / rect.width;
    const my = (e.clientY - rect.top) * this.H / rect.height;
    if(this._drag){
      const dx = e.clientX - this._drag.startX;
      this.viewStart = this._drag.vs - dx / Math.max(this.slot, 0.05);
      this._clampView();
      this._resetYShift();
      /* 记录滑动速度（px/ms），用于惯性 */
      const now = performance.now();
      const dt = Math.max(1, now - this._drag.lastT);
      this._drag.vx = (e.clientX - this._drag.lastX) / dt;
      this._drag.lastX = e.clientX; this._drag.lastT = now;
      this._scheduleDraw();
    }
    this._hoverCheck(mx, my);
    if(this.pinned) return;
    const bi = this._barAt(mx);
    this._updateCross(bi, my);
    if(bi !== this._tipIdx){
      this._tipIdx = bi;
      this._renderTip(bi);
    }
    this._positionTip(mx, my);
    this.tip.classList.add('show');
  }

  _zoom(e){
    if(this.N < 2) return;
    const rect = this.sv.getBoundingClientRect();
    if(rect.width < 2) return;
    const mx = (e.clientX - rect.left) * this.W / rect.width;
    const factor = e.deltaY > 0 ? 1.1 : 1 / 1.1;
    const bx = (mx - this.px0) / Math.max(this.slot, 0.05) + this.viewStart;
    const maxSlot = (this.px1 - this.px0) / Math.max(1, this.N);
    const minSlot = (this.px1 - this.px0) / 20;   /* 最少 20 根 */
    const newSlot = Math.max(maxSlot, Math.min(minSlot, this.slot * factor));
    if(Math.abs(newSlot - this.slot) < 1e-9) return;
    this.slot = newSlot;
    this.viewStart = bx - (mx - this.px0) / newSlot;
    this._clampView();
    this._resetYShift();
    this._custom = true;
    document.querySelectorAll('.range-btn').forEach(b => b.classList.remove('on'));
    this._scheduleDraw();
  }

  /* ---- 公共 API：setRange / toggleMA / setData / resize ---- */
  setRange(n){
    this.rangeN = n;
    this._custom = false;
    this._resetYShift();
    document.querySelectorAll('.range-btn').forEach(b => b.classList.toggle('on', +b.dataset.n === n));
    if(this.N < 2) return;
    this.layout();
    const bars = n > 0 ? Math.min(this.N, n) : this.N;
    const tSlot = (this.px1 - this.px0) / Math.max(1, bars);
    const tVS = Math.max(0, this.N - bars);
    this._growAnim = { t0: performance.now(), dur: 320 };   /* 周期切换：蜡烛自底部生长 */
    this._animateTo(tSlot, tVS);
  }

  _animateTo(tSlot, tVS){
    if(this._anim) cancelAnimationFrame(this._anim);
    const fSlot = this.slot, fVS = this.viewStart;
    const t0 = performance.now(), dur = 320;
    const step = now => {
      const p = Math.min(1, (now - t0) / dur);
      const e = 1 - Math.pow(1 - p, 3);
      this.slot = fSlot + (tSlot - fSlot) * e;
      this.viewStart = fVS + (tVS - fVS) * e;
      this.draw();
      if(p < 1) this._anim = requestAnimationFrame(step);
      else this._anim = null;
    };
    this._anim = requestAnimationFrame(step);
  }

  toggleMA(w){
    this.maVis[w] = !this.maVis[w];
    const chip = document.querySelector('.ma-chip[data-ma="' + w + '"]');
    if(chip) chip.classList.toggle('off', !this.maVis[w]);
    this._redrawCanvas();   /* 局部重绘：仅 Canvas，不重建 SVG 覆盖层 */
  }

  toggleBand(){
    this.bandVis = !this.bandVis;
    const chip = document.getElementById('bandChip');
    if(chip) chip.classList.toggle('off', !this.bandVis);
    this._redrawCanvas();
  }

  toggleHollow(){
    this.hollow = !this.hollow;
    const chip = document.getElementById('hollowChip');
    if(chip) chip.classList.toggle('on', this.hollow);
    this._redrawCanvas();
    try{ localStorage.setItem('radar_hollow', this.hollow ? '1' : '0'); }catch(e){}
  }

  setData(st){
    if(!st){ return; }
    if(this._anim){ cancelAnimationFrame(this._anim); this._anim = null; }
    if(this._yAnim){ cancelAnimationFrame(this._yAnim); this._yAnim = null; }
    this._loopOn = false;
    if(this._hoverT){ clearTimeout(this._hoverT); this._hoverT = null; }
    if(this._flashT){ clearTimeout(this._flashT); this._flashT = null; }
    const tok = ++this._dataTok;
    this.st = st;
    const all = (st.kline||[]).filter(r => r && [r.o, r.c, r.h, r.l, r.v].every(v => Number.isFinite(+v)));
    this.rows = all; this.N = all.length;
    this.maC = {}; this.volC = {}; this.crosses = [];
    [5,10,20,60,120,250].forEach(w => {
      if(this.N < w) return;
      const a = new Float64Array(this.N);
      let s = 0;
      for(let i = 0; i < this.N; i++){
        s += all[i].c;
        if(i >= w) s -= all[i - w].c;
        if(i >= w - 1) a[i] = s / w; else a[i] = NaN;
      }
      this.maC[w] = a;
    });
    [5,10].forEach(w => {
      if(this.N < w) return;
      const a = new Float64Array(this.N);
      let s = 0;
      for(let i = 0; i < this.N; i++){
        s += all[i].v;
        if(i >= w) s -= all[i - w].v;
        if(i >= w - 1) a[i] = s / w; else a[i] = NaN;
      }
      this.volC[w] = a;
    });
    [[5,20],[10,60]].forEach(pair => {
      const A = this.maC[pair[0]], B = this.maC[pair[1]];
      if(!A || !B) return;
      let prev = null;
      for(let i = Math.max(pair[0], pair[1]); i < this.N; i++){
        const d = A[i] - B[i];
        if(isFinite(d) && prev != null && isFinite(prev)){
          if((prev < 0 && d >= 0) || (prev > 0 && d <= 0)) this.crosses.push({i, up: d >= 0});
        }
        prev = d;
      }
    });
    this.pinned = false; this.pinIdx = -1; this._pinY = null; this._tipIdx = -1;
    this._animateSR = true;
    this._custom = false;
    this._resetYShift();
    this._bandAnim = { t0: performance.now(), dur: 500 };
    this._growAnim = { t0: performance.now(), dur: 320 };   /* 换股：蜡烛自底部生长 */
    document.getElementById('chartTitle').textContent = st.name + ' · 估值雷达主图（日K）';
    this._updateChartInfo();
    this.tip.classList.remove('show');
    this.wrap.classList.add('fade');
    setTimeout(() => {
      if(tok !== this._dataTok) return;
      this.layout();
      this._fitRange();
      this.draw();
      this._updateSrFoot(st);
      this._updateChartInfo();
      this.wrap.classList.remove('fade');
      this._startLoop();
    }, 130);
  }

  _updateChartInfo(){
    if(!this.N) return;
    const n = Math.max(1, Math.min(this.N, this.rangeN > 0 ? this.rangeN : this.N));
    let hi = -Infinity, lo = Infinity;
    for(let i = this.N - n; i < this.N; i++){
      const r = this.rows[i];
      if(r.h > hi) hi = r.h;
      if(r.l < lo) lo = r.l;
    }
    const amp = lo > 0 ? (hi - lo) / lo * 100 : 0;
    const vs = [];
    for(let i = Math.max(0, this.N - n); i < this.N; i++) vs.push(this.rows[i].v);
    const vavg = vs.length ? vs.reduce((a,b) => a + b, 0) / vs.length : 0;
    const vTxt = vavg >= 1e8 ? (vavg / 1e8).toFixed(2) + '亿' : (vavg / 1e4).toFixed(0) + '万';
    document.getElementById('chartInfo').textContent = this.N < 2
      ? '暂无足够K线数据'
      : '区间高 ' + fmt2(hi) + ' · 低 ' + fmt2(lo) + ' · 振幅 ' + amp.toFixed(1) + '% · 均量 ' + vTxt
        + '（' + DATA.data_date + ' · ' + this.N + ' 根 · 前复权）';
  }

  _updateSrFoot(st){
    const foot = document.getElementById('srFoot');
    if(!foot) return;
    const all = (st.support || []).map(x => Object.assign({}, x, {s: true}))
      .concat((st.resistance || []).map(x => Object.assign({}, x, {s: false})))
      .filter(x => isFinite(+x.level) && (x.method || '').indexOf('估值锚') !== 0);
    const pr = this._pr;
    const inView = all.filter(x => {
      if(!pr) return true;
      const yy = this.yOf(+x.level);
      return isFinite(yy) && yy >= this.TL - 6 && yy <= this.TL + this.priceH + 6;
    });
    const evOrder = {A: 0, B: 1, C: 2};
    inView.sort((a, b) => evOrder[a.level_ev] - evOrder[b.level_ev] || +a.level - +b.level);
    foot.innerHTML = inView.map((x, i) =>
      '<button class="cap ' + (x.s ? 's' : 'r') + '" title="' + (x.method || '') + ' ' + csym(this.st) + fmt2(+x.level) + '" onclick="KENGINE.scrollToPrice(' + (+x.level) + ')">'
      + '<i></i><span class="v">' + (x.s ? 'S' : 'R') + (i + 1) + ' ' + csym(this.st) + fmt2(+x.level) + '</span></button>').join('');
  }

  _fitRange(){
    const bars = this.rangeN > 0 ? Math.min(this.N, this.rangeN) : this.N;
    this.slot = (this.px1 - this.px0) / Math.max(1, bars);
    this.viewStart = Math.max(0, this.N - bars);
  }

  _startLoop(){
    if(this._loopOn) return;
    this._loopOn = true;
    const tick = () => {
      if(!this._loopOn) return;
      const need = (this._bandAnim != null) || (this._yAnim != null) || (this._growAnim != null) || (!this.pinned && this.N >= 2);
      if(need) this._redrawCanvas();
      if(this._bandAnim != null || this._yAnim != null || this._growAnim != null || (!this.pinned && this.N >= 2)){
        requestAnimationFrame(tick);
      } else {
        this._loopOn = false;
      }
    };
    requestAnimationFrame(tick);
  }

  resize(){
    this.layout();
    if(this.N < 2){ this.draw(); return; }
    const bars = Math.max(10, Math.min(this.N, this.barsPerView()));
    this.slot = (this.px1 - this.px0) / bars;
    this._clampView();
    this._resetYShift();
    this.draw();
    this._updateChartInfo();
  }
}

const KENGINE = new ValuationChartEngine('chartWrap');

/* 平板：图表/数据墙 Tab 切换 */
function tabletTab(v){
  const onWall = v === 'wall';
  document.body.classList.toggle('tablet-wall', onWall);
  const c = document.getElementById('ttChart'), w = document.getElementById('ttWall');
  if(c) c.classList.toggle('on', !onWall);
  if(w) w.classList.toggle('on', onWall);
  try{ localStorage.setItem('radar_tablet_tab', v); }catch(e){}
  if(onWall){
    /* 切到数据墙：恢复到左侧单列纵向排布（横向卡片带不适合整墙阅读） */
    setTimeout(() => KENGINE && KENGINE.resize(), 50);
  }
}
/* 初始化平板 Tab（仅 768-1099 生效，其余宽度隐藏） */
function initTabletTabs(){
  const mq = window.matchMedia('(min-width:768px) and (max-width:1099px)');
  const tt = document.getElementById('tabletTabs');
  const apply = () => {
    if(tt) tt.style.display = mq.matches ? 'inline-flex' : 'none';
    if(!mq.matches) document.body.classList.remove('tablet-wall');
  };
  apply();
  if(mq.addEventListener) mq.addEventListener('change', apply);
  try{
    const saved = localStorage.getItem('radar_tablet_tab');
    if(saved === 'wall' && mq.matches) tabletTab('wall');
  }catch(e){}
}
/* 整墙收起/展开（K线图占满右侧，状态记忆） */
function toggleWallHidden(){
  const hidden = document.body.classList.toggle('wall-hidden');
  try{ localStorage.setItem('wall_hidden', hidden ? '1' : '0'); }catch(e){}
  const b = document.getElementById('wallToggle');
  if(b) b.textContent = hidden ? '⮞ 显示右侧' : '⮜ 收起右侧';
}

/* ============ 数据墙折叠（仅 UI，不改数据；localStorage 记忆） ============ */
const WALL_FOLD_KEY = 'wall_fold_state';
function wallState(){ try{ return JSON.parse(localStorage.getItem(WALL_FOLD_KEY)||'{}'); }catch(e){ return {}; } }
function wallSave(s){ try{ localStorage.setItem(WALL_FOLD_KEY, JSON.stringify(s)); }catch(e){} }
function wallCards(){ return Array.from(document.querySelectorAll('#wall .w-card')); }
function applyWallState(){
  const s = wallState();
  const all = wallCards();
  all.forEach(card => {
    const id = card.dataset.wid;
    const collapsed = !!s[id];
    card.classList.toggle('collapsed', collapsed);
    const btn = card.querySelector('.w-fold');
    if(btn) btn.textContent = collapsed ? '▶' : '▾';
  });
  const open = all.filter(c => !c.classList.contains('collapsed')).length;
  const cnt = document.getElementById('wallCnt');
  if(cnt) cnt.textContent = open + '/' + all.length;
  const ta = document.getElementById('wallToggleAll');
  if(ta) ta.textContent = open > all.length / 2 ? '全部折叠 ▾' : '全部展开 ▴';
}
function toggleCardFold(id, ev){
  if(ev){ ev.stopPropagation(); }
  const card = document.getElementById('wall').querySelector('.w-card[data-wid="' + id + '"]');
  if(!card) return;
  const s = wallState();
  s[id] = !card.classList.contains('collapsed');
  wallSave(s);
  applyWallState();
}
function toggleAllFold(){
  const s = wallState();
  const all = wallCards();
  const openNow = all.filter(c => !c.classList.contains('collapsed')).length;
  const expand = openNow < all.length / 2;
  all.forEach(c => { s[c.dataset.wid] = !expand; });
  wallSave(s);
  applyWallState();
}
/* 移动端（<768px）手风琴：标题点击展开本卡并收起其余 */
function bindWallAccordion(){
  const mq = window.matchMedia('(max-width:767px)');
  const on = () => {
    wallCards().forEach(card => {
      const t = card.querySelector('.w-title');
      if(!t) return;
      t.style.cursor = mq.matches ? 'pointer' : '';
      t.onclick = mq.matches ? () => {
        const s = wallState();
        const id = card.dataset.wid;
        const willOpen = card.classList.contains('collapsed');
        wallCards().forEach(c => { s[c.dataset.wid] = true; });
        s[id] = !willOpen;
        wallSave(s);
        applyWallState();
      } : null;
    });
  };
  on();
  if(mq.addEventListener) mq.addEventListener('change', on);
}

/* ============ 初始化 ============ */
function init(){
  grahamPill();
  renderList();
  applyWallState();
  bindWallAccordion();
  initTabletTabs();
  try{
    if(localStorage.getItem('wall_hidden') === '1'){
      document.body.classList.add('wall-hidden');
      const b = document.getElementById('wallToggle');
      if(b) b.textContent = '⮞ 显示右侧';
    }
  }catch(e){}
  document.querySelectorAll('.range-btn').forEach(btn => {
    btn.onclick = function(){
      KENGINE.setRange(+this.dataset.n);
    };
  });
  document.querySelectorAll('.ma-chip[data-ma]').forEach(chip => {
    chip.onclick = function(){
      KENGINE.toggleMA(+this.dataset.ma);
    };
  });
  document.getElementById('bandChip').onclick = function(){
    KENGINE.toggleBand();
  };
  document.getElementById('hollowChip').onclick = function(){
    KENGINE.toggleHollow();
  };
  if(KENGINE.hollow) document.getElementById('hollowChip').classList.add('on');

  /* ---- 右栏宽度拖拽（默认 340px，持久化 localStorage） ---- */
  (function(){
    const grip = document.getElementById('wallGrip');
    if(!grip) return;
    let dragging = false;
    grip.addEventListener('pointerdown', e => {
      dragging = true;
      grip.classList.add('dragging');
      document.body.style.cursor = 'col-resize';
      grip.setPointerCapture(e.pointerId);
    });
    grip.addEventListener('pointermove', e => {
      if(!dragging) return;
      const shell = grip.parentElement.getBoundingClientRect();
      const w = Math.max(280, Math.min(560, shell.right - e.clientX - 3));
      document.documentElement.style.setProperty('--wall-w', w + 'px');
    });
    const endDrag = () => {
      if(!dragging) return;
      dragging = false;
      grip.classList.remove('dragging');
      document.body.style.cursor = '';
      /* 磁吸收起：拖到 <120px 自动整墙收起 */
      const cur = parseFloat(document.documentElement.style.getPropertyValue('--wall-w')) || 340;
      if(cur < 120 && !document.body.classList.contains('wall-hidden')){
        document.body.classList.add('wall-hidden');
        const b = document.getElementById('wallToggle');
        if(b) b.textContent = '⮞ 显示右侧';
        try{ localStorage.setItem('wall_hidden', '1'); }catch(e){}
        document.documentElement.style.removeProperty('--wall-w');
      } else {
        try{ localStorage.setItem('radar_wall_w', document.documentElement.style.getPropertyValue('--wall-w')); }catch(e){}
      }
    };
    grip.addEventListener('pointerup', endDrag);
    grip.addEventListener('pointercancel', endDrag);
    try{
      const saved = localStorage.getItem('radar_wall_w');
      if(saved) document.documentElement.style.setProperty('--wall-w', saved);
    }catch(e){}
  })();
  let resizeT = null;
  /* 尺寸自适应统一由 KENGINE 内部 ResizeObserver（100ms 防抖）接管，不再监听 window.resize */
  /* 默认打开首页（大盘总览）；记忆上次视图 */
  renderSbSectors();
  const lastView = (() => { try{ return localStorage.getItem('radar_view'); }catch(e){ return null; } })();
  const last = localStorage.getItem('radar_last');
  if(lastView === 'stock'){
    if(last && DATA.stocks.some(s=>s.ticker===last)) switchStock(last);
    else switchStock(DATA.stocks[0].ticker);
  } else {
    showTab('overview');   /* 首页 = 大盘总览（封面），个股视图待点击进入 */
  }
}
init();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    print(build())
