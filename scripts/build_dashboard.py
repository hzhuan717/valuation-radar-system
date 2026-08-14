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
.shell{display:grid;grid-template-columns:210px minmax(0,1fr) 6px var(--wall-w,340px);grid-template-rows:minmax(0,1fr);
  height:calc(100vh - 44px);overflow:hidden}

/* ---- 左导航 210px ---- */
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
.sb-item.on{background:var(--blue-lt);box-shadow:inset 3px 0 0 var(--blue)}
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
/* 估值位置条：抬高 + mark 垂直居中 */
.sb-item .bar{position:absolute;left:12px;right:12px;bottom:4px;height:4px;border-radius:2px;overflow:hidden;
  background:linear-gradient(90deg,rgba(52,199,89,.55) 0 25%,rgba(0,113,227,.45) 25% 75%,rgba(255,59,48,.55) 75% 100%)}
.sb-item .bar i{display:none}
.sb-item .bar .mark{
  position:absolute;
  top:50%;
  transform:translate(-50%,-50%);
  width:2px;
  height:5px;
  background:var(--ink);
  border-radius:1px;
}
.up-c{color:var(--candle-up)}.dn-c{color:var(--candle-dn)}
/* 估值区域标签 */
.sb-zone{font-size:12px;color:var(--sub2)}
.sb-zone.z0,.sb-zone.z1{color:var(--green-d)}.sb-zone.z4,.sb-zone.z5{color:var(--red-d)}.sb-zone.z2,.sb-zone.z3{color:var(--gold)}

/* ---- 中央区 ---- */
.center{display:flex;flex-direction:column;min-width:0;min-height:0;background:var(--bg)}
.hero-strip{display:flex;align-items:center;gap:18px;padding:10px 16px;background:var(--bg2);
  border-bottom:1px solid var(--hair);flex-wrap:wrap}
.hero-strip .hl{min-width:0;flex:1}
.hero-strip .eyebrow{font-size:12px;letter-spacing:.05em;color:var(--sub2);text-transform:uppercase}
.hero-strip h1{font-size:23px;font-weight:700;letter-spacing:0;line-height:1.3}
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
.chart-toolbar .info{font-size:12px;color:var(--sub2);min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.range-btns{display:flex;gap:4px}
.range-btn{font-size:12px;padding:4px 11px;border-radius:999px;border:1px solid var(--hair);
  background:var(--bg2);color:var(--sub2);transition:all .15s}
.range-btn:hover{border-color:var(--blue);color:var(--blue)}
.range-btn.on{background:var(--blue);border-color:var(--blue);color:#fff;font-weight:600}
.ma-legend{margin-left:auto;display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end;max-width:100%}
.ma-chip{display:inline-flex;align-items:center;gap:4px;font-size:12px;border:1px solid var(--hair);
  border-radius:999px;padding:3px 10px;background:var(--bg2);color:var(--sub2);transition:transform .15s,box-shadow .15s}
.ma-chip:hover{transform:scale(1.05)}
.ma-chip.on{box-shadow:0 2px 6px rgba(0,0,0,.12)}
.ma-chip i{width:9px;height:3px;display:inline-block;border-radius:1px}
.ma-chip.off{opacity:.4;text-decoration:line-through}
.chart-wrap{flex:1;position:relative;min-height:200px;border:1px solid var(--hair);border-radius:var(--r-card);
  background:var(--bg2);overflow:hidden;user-select:none;transition:opacity .2s ease}
.chart-wrap.fade{opacity:.6}
.chart-wrap canvas{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
.chart-wrap svg{position:absolute;inset:0;width:100%;height:100%;display:block;cursor:crosshair;touch-action:none}
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
.ktip{position:absolute;left:8px;top:8px;right:auto;background:rgba(255,255,255,.97);backdrop-filter:blur(12px);
  border:1px solid var(--hair2);
  border-radius:10px;padding:10px 14px;font-family:var(--font-mono);font-size:12px;line-height:1.7;color:var(--ink);
  box-shadow:0 4px 16px rgba(0,0,0,.1);pointer-events:none;opacity:0;min-width:186px;max-width:280px;z-index:6;
  font-variant-numeric:tabular-nums;white-space:pre;transition:opacity .2s}
.ktip.show{opacity:1}
.ktip.mobile{left:6px !important;right:6px !important;top:auto !important;bottom:6px !important;max-width:none}
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

/* ---- 右数据墙 var(--wall-w) 可拖拽 ---- */
.wall{background:var(--bg);border-left:1px solid var(--hair);overflow-y:auto;padding:10px;min-height:0}
.wall-grip{cursor:col-resize;position:relative;z-index:5;background:transparent;transition:background .15s}
.wall-grip:hover,.wall-grip.dragging{background:rgba(0,113,227,.25)}
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
.wfall .step .st{font-family:var(--font-base);font-size:12px;color:var(--meta);margin-left:8px}
.kelly-line{margin-top:8px;padding:6px 10px;border-radius:6px;background:var(--hair);
  font-size:12px;color:var(--sub2);font-family:var(--font-mono)}
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
@media(max-width:1399px){
  .shell{grid-template-columns:84px minmax(0,1fr) 6px var(--wall-w,340px)}
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
  .wall-grip{display:none}
  .mos-track{display:none}   /* 窄屏省 hero-strip 垂直空间 */
  .sidebar{border-right:none;border-bottom:1px solid var(--hair)}
  .sb-list{display:flex;overflow-x:auto;flex:none}
  .sb-item{min-width:120px;border-right:1px solid var(--hair);border-bottom:none}
  .center{min-height:0}
  .chart-zone{height:auto;min-height:45vh;position:sticky;top:0;z-index:10;background:var(--bg2);border-bottom:1px solid var(--hair)}
  .chart-wrap{min-height:220px}
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
          <button class="ma-chip on" data-ma="120"><i style="background:#af52de"></i>MA120</button>
          <button class="ma-chip on" data-ma="250"><i style="background:#34c759"></i>MA250</button>
          <button class="ma-chip on" id="bandChip" title="显隐 V_low/V_mid/V_high 估值色带与锚线"><i style="background:rgba(0,113,227,.55)"></i>估值带</button>
          <button class="ma-chip" id="hollowChip" title="色觉友好：上涨空心/下跌实心，颜色+形状双区分"><i style="background:#d94a47"></i>空心/实心</button>
        </div>
      </div>
      <div class="chart-wrap" id="chartWrap">
        <canvas id="klineCv"></canvas>
        <svg id="klineSvg" role="img" aria-label="K线估值主图"></svg>
        <div class="ktip" id="chartTip"></div>
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

    <div class="ov-wrap" id="ovWrap" style="display:none">
      <table class="ov-table" id="ovTable"></table>
    </div>
  </main>

  <div class="wall-grip" id="wallGrip" title="拖拽调整右栏宽度"></div>

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

/* ============ 左导航列表 ============ */
function renderList(filter){
  const el = document.getElementById('sbList');
  const q = (filter||'').trim().toLowerCase();
  el.innerHTML = DATA.stocks.filter(s => !q || s.name.toLowerCase().includes(q) || s.ticker.includes(q))
    .map(s => {
      const zm = zmeta(s);
      const zc = ['z0','z0','z2','z2','z4','z4','z6'][zm.c] || 'z6';
      const rawPos = bandPosPct(s.price, s.v_low, s.v_mid, s.v_high);
      const barTitle = (s.v_low!=null && s.v_high!=null && s.v_high>s.v_low)
        ? '估值带位置 ' + rawPos.toFixed(0) + '%（' + fmt2(s.v_low) + ' ~ ' + fmt2(s.v_high) + '）'
        : '无估值区间';
      return '<button class="sb-item '+(s.ticker===CUR?.ticker&&VIEW==='stock'?'on':'')+'" onclick="switchStock(\''+s.ticker+'\')">'
        + '<div class="sb-row-top">'
        + '<div class="sb-name-group"><span class="nm">'+s.name+'</span><span class="cd">'+s.ticker+'</span><span class="code">'+s.ticker+'</span></div>'
        + '<div class="sb-price-group"><span class="px">¥'+fmt2(s.price)+'</span></div>'
        + '</div>'
        + '<div class="sb-row-btm">'
        + '<div class="sb-change-group"><span class="chg '+pctCol(s.pct)+'">'+(s.pct>0?'+':'')+fmt2(s.pct)+'%</span></div>'
        + '<div class="sb-zone-group"><span class="sb-zone '+zc+'">'+zm.label+'</span></div>'
        + '</div>'
        + '<div class="bar" title="'+barTitle+'"><span class="mark" style="left:'+rawPos+'%"></span></div>'
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
  document.getElementById('gateTxt').textContent = '市场温度 ' + g.graham + ' · ' + g.band
    + (g.erp_pct!=null ? ' · ERP ' + g.erp_pct + '%' : '') + stale;
  document.getElementById('updAt').textContent = (DATA.updated_at||'').slice(5,16);
  document.getElementById('dataDate').textContent = DATA.data_date || '—';
}

/* ============ 总览 ============ */
function showOverview(){
  VIEW = 'overview'; CUR = null;
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
      + '<div class="micro"><div class="k">ERP</div><div class="v">'+(x.erp_pct!=null?x.erp_pct+'%':'—')+'</div><div class="m">1/PE−10Y国债（D级）</div></div>'
      + '<div class="micro"><div class="k">公式</div><div class="v" style="font-size:13px">(1/PE)÷10Y国债</div><div class="m">'+fmt2(((DATA.market.bond_10y||{}).value||0)*100)+'%</div></div>'
      + '</div>').join('')
    + '<div class="formula-mini">v2 定位：仅市场背景参考，不构成仓位硬闸门；不生成个股动作、清仓命令或总仓上限。格雷厄姆比值在低利率（10Y国债<2%）下分母趋零会乘数放大，故并列显示 ERP=1/PE−10Y国债（减法模型，D级补充，无历史序列不给分档）。指数 PE(TTM) 在周期顶/底部反向失真、成分股结构逐年漂移，仅作背景不逐日交易。</div></div>';
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
  document.getElementById('trigName').textContent = st.name + ' ' + st.ticker;
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
  const raw = bandPosRaw(st.price, st.v_low, st.v_mid, st.v_high);
  if(raw != null && (st.decision_usable || st.reference_zone)){
    dot.style.left = Math.max(0,Math.min(100,raw*100)) + '%';
    dot.style.display = '';
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
  let html =
    '<div class="v3-blocks">'
    + '<div class="v3b low"><div class="k">保守 V_low'+(usable?' · 买入启动':'')+'</div><div class="v">¥'+fmt2(st.v_low)+'</div><div class="f">'+e1+' × '+m1+'×</div></div>'
    + '<div class="v3b mid"><div class="k">基准 V_mid · 价值中枢</div><div class="v">¥'+fmt2(st.v_mid)+'</div><div class="f">'+e2+' × '+m2+'×</div></div>'
    + '<div class="v3b high"><div class="k">乐观 V_high'+(usable?' · 卖出启动':'')+'</div><div class="v">¥'+fmt2(st.v_high)+'</div><div class="f">'+e3+' × '+m3+'×</div></div>'
    + '</div>'
    + '<div class="band-track"><div class="dot" style="left:'+bandPosPct(st.price, st.v_low, st.v_mid, st.v_high)+'%"></div></div>'
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

/* ============ K线图引擎（Canvas 蜡烛/均线/成交量 + SVG 标注/十字光标） ============ */
const KCOL = { up:'#d94a47', dn:'#178a59' };
const MACOL = {5:'#0071e3', 10:'#5e5ce6', 20:'#b8956a', 60:'#86868b', 120:'#af52de', 250:'#34c759'};
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
    this._yShift = 0; this._yAnim = null; this._bandAnim = null;
    this._loopOn = false; this._hoverOn = false; this._hoverT = null; this._flashT = null; this._hl = [];
    this._isMobile = window.matchMedia ? window.matchMedia('(max-width:699px)').matches : false;
    if(this.tip) this.tip.classList.toggle('mobile', this._isMobile);
    this._bind();
    if(stockData) this.setData(stockData);
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
    if(window.ResizeObserver){
      this._ro = new ResizeObserver(() => {
        clearTimeout(this._resT);
        this._resT = setTimeout(() => { this.resize(); }, 200);
      });
      this._ro.observe(this.wrap);
    }
  }

  /* ---- 布局与比例 ---- */
  layout(){
    const w = Math.max(260, this.wrap.clientWidth || 800);
    const h = Math.max(180, this.wrap.clientHeight || 540);
    this.W = w; this.H = h;
    this.dpr = Math.min(2, window.devicePixelRatio || 1);
    this.AX = w < 560 ? 62 : 72;
    this.GUT = w < 560 ? 72 : 96;   /* 右缘标签槽：锚/MA/斐波标签专用，K线不进入 */
    this.TL = 12; this.BX = 26;
    this.px0 = 8; this.px1 = w - this.AX - this.GUT;
    this.axX = w - this.AX;
    this.hideVol = w < 600;   /* 窄屏隐藏成交量副图，释放垂直空间 */
    this.priceH = (h - this.TL - this.BX) * (this.hideVol ? 0.9 : 0.75);
    this.volTop = this.TL + this.priceH + 6;
    this.volBot = this.hideVol ? this.volTop : h - this.BX;
    this.volH = this.volBot - this.volTop;
    const wpx = Math.round(w * this.dpr), hpx = Math.round(h * this.dpr);
    if(this.cv.width !== wpx || this.cv.height !== hpx){ this.cv.width = wpx; this.cv.height = hpx; }
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
    /* scrollToPrice 居中动画（_yAnim/_yShift） */
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

  /* ---- Canvas 绘制 ---- */
  _drawBands(ctx){
    const pr = this._pr;
    if(!pr.hasV) return;
    const yLow = this.yOf(pr.vlow), yHigh = this.yOf(pr.vhigh);
    const w = this.px1 - this.px0;
    /* 入场动画：色带从顶部向下展开（0.5s） */
    let p = 1;
    if(this._bandAnim){
      const e = Math.min(1, (performance.now() - this._bandAnim.t0) / this._bandAnim.dur);
      p = 1 - Math.pow(1 - e, 3);
      if(e >= 1) this._bandAnim = null;
    }
    ctx.save();
    ctx.beginPath();
    ctx.rect(this.px0, this.TL, w, Math.max(1, this.priceH * p));
    ctx.clip();
    /* 基础色带（当前所在区间更浓，增强区间感知） */
    const lastClose = this.N >= 2 ? this.rows[this.N-1].c : null;
    const curZone = lastClose == null ? null : (lastClose < pr.vlow ? 'low' : (lastClose <= pr.vhigh ? 'mid' : 'high'));
    ctx.fillStyle = curZone === 'low' ? 'rgba(48,209,88,.20)' : 'rgba(48,209,88,.11)';
    ctx.fillRect(this.px0, yLow, w, this.TL + this.priceH - yLow);
    ctx.fillStyle = curZone === 'mid' ? 'rgba(0,113,227,.18)' : 'rgba(0,113,227,.10)';
    ctx.fillRect(this.px0, yHigh, w, yLow - yHigh);
    ctx.fillStyle = curZone === 'high' ? 'rgba(255,59,48,.20)' : 'rgba(255,59,48,.11)';
    ctx.fillRect(this.px0, this.TL, w, yHigh - this.TL);
    /* 横向纹理虚线（20px 步长 · 极度缩小时跳过） */
    if(this.slot >= 2){
      const bands = [
        {y0: yLow, y1: this.TL + this.priceH, col: 'rgba(48,209,88,.08)', dash: [2, 6]},
        {y0: yHigh, y1: yLow, col: 'rgba(0,113,227,.07)', dash: [2, 8]},
        {y0: this.TL, y1: yHigh, col: 'rgba(255,59,48,.08)', dash: [2, 6]},
      ];
      bands.forEach(bd => {
        if(bd.y1 - bd.y0 < 4) return;
        ctx.strokeStyle = bd.col;
        ctx.lineWidth = 1;
        ctx.setLineDash(bd.dash);
        ctx.beginPath();
        for(let yy = bd.y0 + 20; yy < bd.y1; yy += 20){
          ctx.moveTo(this.px0, yy);
          ctx.lineTo(this.px1, yy);
        }
        ctx.stroke();
        ctx.setLineDash([]);
      });
    }
    /* 边界发光带（4px/3px 渐变过渡 · 当前区间边界更亮） */
    const glow = (y0, y1, c0, c1) => {
      const g = ctx.createLinearGradient(0, y0, 0, y1);
      g.addColorStop(0, c0); g.addColorStop(1, c1);
      ctx.fillStyle = g;
      ctx.fillRect(this.px0, Math.min(y0, y1), w, Math.abs(y1 - y0));
    };
    if(yLow < this.TL + this.priceH) glow(yLow + 2, yLow + 6, 'rgba(48,209,88,.30)', 'rgba(48,209,88,0)');
    if(yLow > this.TL) glow(yLow - 3, yLow, 'rgba(0,113,227,0)', 'rgba(0,113,227,.22)');
    if(yHigh < this.TL + this.priceH) glow(yHigh, yHigh + 3, 'rgba(0,113,227,.22)', 'rgba(0,113,227,0)');
    if(yHigh > this.TL) glow(yHigh - 4, yHigh, 'rgba(255,59,48,0)', 'rgba(255,59,48,.30)');
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
    if(!pr || !pr.hasV) return '#0071e3';
    if(c < pr.vlow) return '#34c759';
    if(c < pr.vhigh) return '#0071e3';
    return '#ff3b30';
  }

  _zoneCard(c, pr){
    if(!pr.hasV) return null;
    const mob = this._isMobile;
    let name, col, dist;
    if(c < pr.vlow){ name = '深度低估'; col = '#1f9d4d'; dist = '低于保守线'; }
    else if(c < pr.vmid){ name = '低估区'; col = '#1f9d4d'; dist = '距基准线 ' + ((pr.vmid / c - 1) * 100).toFixed(1) + '%'; }
    else if(c <= pr.vhigh){ name = '合理区'; col = '#0071e3'; dist = '距乐观线 ' + ((pr.vhigh / c - 1) * 100).toFixed(1) + '%'; }
    else { name = '高估区'; col = '#d70015'; dist = '高于乐观线'; }
    const w = mob ? 110 : 140, h = mob ? 34 : 52;
    const x0 = this.px0 + 8;
    const svg = y0 => {
      let t = '<rect x="' + x0 + '" y="' + y0.toFixed(1) + '" width="' + w + '" height="' + h + '" rx="6" fill="#ffffff" fill-opacity=".96" stroke="rgba(0,0,0,.08)"/>';
      if(mob){
        t += '<text x="' + (x0 + 8) + '" y="' + (y0 + 14).toFixed(1) + '" font-size="10" font-weight="700" fill="' + col + '" font-family="SF Mono,monospace">¥' + fmt2(c) + '</text>'
           + '<text x="' + (x0 + 8) + '" y="' + (y0 + 27).toFixed(1) + '" font-size="10" fill="' + col + '" font-family="SF Mono,monospace">' + name + '</text>';
      } else {
        t += '<text x="' + (x0 + 8) + '" y="' + (y0 + 17).toFixed(1) + '" font-size="11" font-weight="700" fill="' + col + '" font-family="SF Mono,monospace">现价 ¥' + fmt2(c) + '</text>'
           + '<text x="' + (x0 + 8) + '" y="' + (y0 + 33).toFixed(1) + '" font-size="11" fill="' + col + '" font-family="SF Mono,monospace">处于 · ' + name + '</text>'
           + '<text x="' + (x0 + 8) + '" y="' + (y0 + 47).toFixed(1) + '" font-size="11" fill="#86868b" font-family="SF Mono,monospace">' + dist + '</text>';
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
    this._range();
    this._drawBands(ctx);
    this._drawCandles(ctx);
    this._drawVolume(ctx);
    this._drawMAs(ctx);
    this._drawBreath(ctx);
  }

  _drawCandles(ctx){
    const y = p => this.yOf(p);
    const bodyW = Math.max(1, Math.min(12, this.slot * 0.7));
    const thin = this.slot < 2.2;
    for(let i = this._pr.i0; i <= this._pr.i1; i++){
      const r = this.rows[i];
      const cx = this.xOf(i);
      if(cx < this.px0 - 4 || cx > this.px1 + 4) continue;
      const up = r.c >= r.o;
      const col = up ? KCOL.up : KCOL.dn;
      if(!thin){
        ctx.strokeStyle = col;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(cx, y(r.h));
        ctx.lineTo(cx, y(r.l));
        ctx.stroke();
      }
      const yo = y(Math.max(r.o, r.c));
      const bh = Math.max(1, Math.abs(y(r.o) - y(r.c)));
      if(this.hollow && up && !thin){
        /* 色觉友好：上涨空心描边 + 浅填充，下跌实心——颜色与形状双重区分 */
        ctx.strokeStyle = col;
        ctx.lineWidth = 1.2;
        ctx.strokeRect(cx - bodyW / 2, yo, bodyW, bh);
        ctx.fillStyle = 'rgba(217,74,71,.14)';
        ctx.fillRect(cx - bodyW / 2, yo, bodyW, bh);
      } else {
        ctx.fillStyle = col;
        ctx.fillRect(cx - bodyW / 2, yo, bodyW, bh);
      }
    }
  }

  _drawVolume(ctx){
    if(this.hideVol) return;   /* <600px 窄屏不画成交量副图 */
    const vmax = this._volMax();
    const bodyW = Math.max(1.5, Math.min(12, this.slot * 0.7));
    for(let i = this._pr.i0; i <= this._pr.i1; i++){
      const r = this.rows[i];
      const cx = this.xOf(i);
      if(cx < this.px0 - 4 || cx > this.px1 + 4) continue;
      const up = r.c >= r.o;
      const col = up ? KCOL.up : KCOL.dn;
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
      ctx.strokeStyle = w === 5 ? 'rgba(134,134,139,.55)' : 'rgba(134,134,139,.32)';
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
    [5,10,20,60,120,250].forEach(w => {
      if(!this.maVis[w]) return;
      const a = this.maC[w];
      if(!a) return;
      ctx.strokeStyle = MACOL[w];
      ctx.lineWidth = w <= 20 ? 1.6 : 1.2;
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
  }

  /* ---- SVG 覆盖层（锚线/S-R/斐波/标签/轴/徽章/十字光标） ---- */
  overlay(){
    const pr = this._pr;
    const s = [];
    const W = this.W, H = this.H, y = p => this.yOf(p);
    if(this.N < 2){
      s.push('<text x="' + (W/2).toFixed(1) + '" y="' + (H/2).toFixed(1) + '" text-anchor="middle" font-size="13" fill="#86868b">暂无足够K线数据</text>');
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
      A: {sw: 2.2, up: '#34c759', dn: '#ff3b30', op: .90, dash: ''},
      B: {sw: 1.6, up: '#30d158', dn: '#ff6b6b', op: .75, dash: '8 4'},
      C: {sw: 1.2, up: '#8ce8a8', dn: '#ffb3b3', op: .55, dash: '4 4'},
    };
    const mo = this._isMobile ? 0.3 : 0;
    let srSeq = 0;

    /* 两阶段：先画线（按等级排序 A 优先），再画标签（数量>8 时 C 级不画标签） */
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
      const labCol = touch ? col : (isSup ? '#1f9d4d' : '#d70015');
      const cls = [];
      if(this._animateSR) cls.push('srl');
      if(touch) cls.push('sr-pulse');
      const cattr = cls.length ? ' class="' + cls.join(' ') + '"' : '';
      const lineId = 'sr-' + (srSeq++);
      /* 左端标签徽章宽度（决定主线段起点） */
      const priceTxt = fmt0(vv);
      const methodTxt = (!this._isMobile && ev !== 'C') ? ((sr.method || '').slice(0, 8)) : '';
      const badgeW = this._isMobile ? 64 : (20 + 18 + priceTxt.length * 6.6 + (methodTxt ? methodTxt.length * 5.4 + 10 : 0) + 8);
      const x0 = Math.min(6 + badgeW + 30, this.px1 - 24);
      /* 主线段 */
      s.push('<line' + cattr + ' id="' + lineId + '" x1="' + x0.toFixed(0) + '" y1="' + yy.toFixed(1) + '" x2="' + this.px1 + '" y2="' + yy.toFixed(1) + '" stroke="' + col + '" stroke-width="' + lw.toFixed(1) + '"' + (stl.dash ? ' stroke-dasharray="' + stl.dash + '"' : '') + ' opacity="' + stl.op + '"/>');
      /* 连接虚线：徽章右缘 → 主线段起点 */
      s.push('<line x1="' + (6 + badgeW + 2).toFixed(0) + '" y1="' + yy.toFixed(1) + '" x2="' + x0.toFixed(0) + '" y2="' + yy.toFixed(1) + '" stroke="' + col + '" stroke-width="1" stroke-dasharray="2 3" opacity=".4"/>');
      /* 左端方向三角（支撑▲ / 压力▼） */
      if(isSup){
        s.push('<polygon points="' + (x0 - 3).toFixed(0) + ',' + (yy - 2).toFixed(1) + ' ' + (x0 + 3).toFixed(0) + ',' + (yy - 2).toFixed(1) + ' ' + x0.toFixed(0) + ',' + (yy - 7).toFixed(1) + '" fill="' + col + '"/>');
      } else {
        s.push('<polygon points="' + (x0 - 3).toFixed(0) + ',' + (yy + 2).toFixed(1) + ' ' + (x0 + 3).toFixed(0) + ',' + (yy + 2).toFixed(1) + ' ' + x0.toFixed(0) + ',' + (yy + 7).toFixed(1) + '" fill="' + col + '"/>');
      }
      /* 触碰同心圆（桌面端） */
      if(touch && !this._isMobile){
        s.push('<circle cx="' + (this.px1 - 4).toFixed(0) + '" cy="' + yy.toFixed(1) + '" r="8" fill="' + col + '" opacity=".15"/>'
             + '<circle cx="' + (this.px1 - 4).toFixed(0) + '" cy="' + yy.toFixed(1) + '" r="4" fill="' + col + '" opacity=".8"/>');
      }
      hl.push({id: lineId, yy, price: vv, name: sr.method || '', ev, isSup, sw: lw, op: stl.op, kind: 'sr'});
      /* 标签（>8 时仅 A/B；C 级仅价格无方法） */
      if(inViewRows.length > 8 && ev === 'C') return;
      srLbls.push({y: yy, type: (isSup?'S':'R') + (rr.idx + 1), price: priceTxt, methodTxt, ev, isSup, col: labCol});
    });

    /* 越界 S/R 边缘提示 */
    srRows.forEach(rr => {
      const vv = +rr.sr.level;
      const yy = y(vv);
      if(isFinite(yy) && yy >= this.TL - 6 && yy <= priceB + 6) return;
      const isSup = rr.isSup;
      const col = isSup ? '#1f9d4d' : '#d70015';
      if(vv > pr.pmax) edgeTop.push({lab: (isSup?'S':'R') + (rr.idx + 1) + ' ¥' + fmt0(vv), col, method: rr.sr.method || '', up: true, sup: isSup});
      else if(vv < pr.pmin) edgeBot.push({lab: (isSup?'S':'R') + (rr.idx + 1) + ' ¥' + fmt0(vv), col, method: rr.sr.method || '', up: false, sup: isSup});
    });

    /* S/R 左侧胶囊标签（强度图标 + 类型 + 价格 + 方法缩写 + 连接虚线，间距 22px） */
    packLbl(srLbls, 22).forEach(it => {
      if(it.yy < this.TL + 11 || it.yy > priceB - 11) return;
      const ev = it.ev;
      const bgA = it.isSup ? 'rgba(52,199,89,.12)' : 'rgba(255,59,48,.12)';
      const bgB = it.isSup ? 'rgba(52,199,89,.08)' : 'rgba(255,59,48,.08)';
      const badgeW = this._isMobile ? 64 : (20 + 18 + it.price.length * 6.6 + (it.methodTxt ? it.methodTxt.length * 5.4 + 10 : 0) + 8);
      const gOpen = this._animateSR ? '<g class="srlbl">' : '<g>';
      s.push(gOpen);
      if(ev === 'C'){
        s.push('<rect x="6" y="' + (it.yy - 10).toFixed(1) + '" width="' + badgeW.toFixed(0) + '" height="20" rx="10" fill="#ffffff" fill-opacity=".95" stroke="' + it.col + '" stroke-width="1"/>');
      } else {
        s.push('<rect x="6" y="' + (it.yy - 10).toFixed(1) + '" width="' + badgeW.toFixed(0) + '" height="20" rx="10" fill="' + (ev === 'A' ? bgA : bgB) + '"/>');
      }
      if(ev === 'A') s.push('<circle cx="16" cy="' + it.yy.toFixed(1) + '" r="4" fill="' + it.col + '"/>');
      else if(ev === 'B') s.push('<circle cx="16" cy="' + it.yy.toFixed(1) + '" r="4" fill="' + it.col + '" opacity=".35"/><circle cx="16" cy="' + it.yy.toFixed(1) + '" r="2.2" fill="' + it.col + '"/>');
      else s.push('<circle cx="16" cy="' + it.yy.toFixed(1) + '" r="3.5" fill="none" stroke="' + it.col + '" stroke-width="1.2"/>');
      s.push('<text x="24" y="' + (it.yy + 3.5).toFixed(1) + '" font-size="10" font-weight="700" fill="' + it.col + '" font-family="SF Mono,monospace">' + it.type + '</text>');
      s.push('<text x="46" y="' + (it.yy + 4).toFixed(1) + '" font-size="11" font-weight="600" fill="' + it.col + '" font-family="SF Mono,monospace">¥' + it.price + '</text>');
      if(it.methodTxt){
        s.push('<text x="' + (52 + it.price.length * 6.6).toFixed(0) + '" y="' + (it.yy + 4).toFixed(1) + '" font-size="9" fill="#86868b" font-family="SF Mono,monospace">' + it.methodTxt + '</text>');
      }
      s.push('</g>');
    });

    /* 估值锚边界线（1.6px + 左端圆点 + 入场动画）+ 右缘标签 + 参考级提示 */
    const rightItems = [];
    let zoneY = this.TL + 14;
    if(pr.hasV){
      [['low', pr.vlow, '#1f9d4d', 'rgba(52,199,89,.22)', '保守', '#34c759', '6 4'],
       ['mid', pr.vmid, '#0071e3', 'rgba(0,113,227,.22)', '基准', '#0071e3', ''],
       ['high', pr.vhigh, '#d70015', 'rgba(255,59,48,.22)', '乐观', '#ff3b30', '6 4']].forEach(a => {
        const yy = y(a[1]);
        if(isFinite(yy) && yy >= this.TL && yy <= priceB){
          const cls = this._animateSR ? ' class="srl"' : '';
          const dashAttr = a[6] ? ' stroke-dasharray="' + a[6] + '"' : '';
          s.push('<line' + cls + ' id="anchor-' + a[0] + '" x1="0" y1="' + yy.toFixed(1) + '" x2="' + this.px1 + '" y2="' + yy.toFixed(1) + '" stroke="' + a[2] + '" stroke-width="1.6" stroke-linecap="round"' + dashAttr + ' opacity=".8"/>'
               + '<circle cx="8" cy="' + yy.toFixed(1) + '" r="2.5" fill="' + a[2] + '"/>');
          rightItems.push({y: yy, lab: a[4] + ' ¥' + fmt2(a[1]), col: a[2], bg: a[3], bar: a[5]});
          hl.push({id: 'anchor-' + a[0], yy, price: a[1], name: '估值锚 V_' + a[0] + '（' + a[4] + '）', ev: 'A', isSup: a[0] !== 'high', sw: 1.6, op: .7, kind: 'anchor'});
        }
      });
      /* 区间定位卡片（左上角，与 S/R 标签避让） */
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
      /* 三区间中文水印（区顶部右对齐 · 当前区间更亮） */
      const zCur = lastClose < pr.vlow ? 'low' : (lastClose <= pr.vhigh ? 'mid' : 'high');
      const zLabels = [
        {key: 'high', t: '高估区', col: '#d70015', y0: this.TL, y1: y(pr.vhigh)},
        {key: 'mid', t: '合理区', col: '#0071e3', y0: y(pr.vhigh), y1: y(pr.vlow)},
        {key: 'low', t: '低估区', col: '#1f9d4d', y0: y(pr.vlow), y1: priceB},
      ];
      const zFs = this.W < 560 ? 10 : 12;
      zLabels.forEach(z => {
        if(z.y1 - z.y0 < 26) return;
        const yy = z.y0 + 15;
        s.push('<text x="' + (this.px1 - 8) + '" y="' + yy.toFixed(1) + '" text-anchor="end" font-size="' + zFs + '" font-weight="700" fill="' + z.col + '" opacity="' + (z.key === zCur ? '.9' : '.55') + '" font-family="PingFang SC,Microsoft YaHei,sans-serif">' + z.t + '</text>');
      });
      if(!st.decision_usable && W >= 560 && (zoneY > this.TL + 80 || !zoneCard)){
        s.push('<rect x="6" y="' + this.TL + '" width="150" height="22" rx="4" fill="#ffffff" fill-opacity=".94" stroke="rgba(0,0,0,.12)"/>'
             + '<text x="14" y="' + (this.TL + 15) + '" font-size="12" fill="#48484a" font-weight="600">参考区间 · 不可执行</text>');
      }
    } else if(isFinite(+st.v_low) && isFinite(+st.v_high)){
      edgeBot.push({lab: 'V_low ¥' + fmt0(+st.v_low), col: '#1f9d4d', method: '', up: false, sup: true});
      edgeTop.push({lab: 'V_high ¥' + fmt0(+st.v_high), col: '#d70015', method: '', up: true, sup: false});
    }

    /* 斐波那契回撤（250日高低点 · 仅在接近全量视图显示） */
    if(this.N >= 60 && this.barsPerView() >= Math.min(this.N, 240)){
      const seg = this.rows.slice(-250);
      const lo = Math.min.apply(null, seg.map(r => r.l));
      const hi = Math.max.apply(null, seg.map(r => r.h));
      if(hi - lo > 0){
        [0.382, 0.5, 0.618].forEach(rt => {
          const p = lo + (hi - lo) * rt;
          const yy = y(p);
          if(isFinite(yy) && yy >= this.TL && yy <= priceB){
            s.push('<line x1="0" y1="' + yy.toFixed(1) + '" x2="' + this.px1 + '" y2="' + yy.toFixed(1) + '" stroke="#a0742f" stroke-width="1" stroke-dasharray="2 4" opacity=".5"/>');
            if(this.W >= 560) rightItems.push({y: yy, lab: rt + ' ¥' + fmt2(p), col: '#a0742f', bg: 'rgba(255,255,255,.9)'});
          }
        });
      }
    }

    /* MA 端点标签（末端圆点 + 价格） */
    [5,10,20,60,120,250].forEach(w => {
      if(!this.maVis[w] || !this.maC[w]) return;
      const v = this.maC[w][this._pr.i1];
      if(!isFinite(v)) return;
      const yy = y(v);
      if(!isFinite(yy) || yy < this.TL - 4 || yy > priceB + 4) return;
      s.push('<circle cx="' + (this.px1 - 2).toFixed(1) + '" cy="' + yy.toFixed(1) + '" r="2.4" fill="' + MACOL[w] + '"/>');
      if(this.W >= 560) rightItems.push({y: yy, lab: 'MA' + w + ' ' + fmt2(v), col: MACOL[w], bg: 'rgba(255,255,255,.92)'});
    });

    /* 右缘标签槽（锚/斐波/MA 联合防重叠；标签在 K 线区右侧专用槽内，不遮挡蜡烛） */
    const chW = this.W < 560 ? 5.2 : 6.3;
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
           + '<text x="' + (xR - wdt + 5).toFixed(0) + '" y="' + (it.yy + 3.5).toFixed(1) + '" font-size="' + (this.W < 560 ? 10 : 11) + '" font-weight="600" fill="' + it.col + '" font-family="SF Mono,monospace">' + lab + '</text>');
    });

    /* 金叉/死叉标注 */
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
      s.push('<text x="' + k.x.toFixed(1) + '" y="' + k.yy.toFixed(1) + '" text-anchor="middle" font-size="9" fill="' + (k.up ? '#1f9d4d' : '#d70015') + '">' + (k.up ? '▲金叉' : '▼死叉') + '</text>');
    });

    /* 涨停/跌停徽章 */
    const lm = [];
    for(let i = this._pr.i0; i <= this._pr.i1; i++){
      const r = this.rows[i];
      if(!(r.o > 0)) continue;
      const x = this.xOf(i);
      if(x < this.px0 + 12 || x > this.px1 - 12) continue;
      const chg = (r.c - r.o) / r.o;
      if(chg > 0.095) lm.push({x, yy: y(r.h) - 16, t: '涨', col: KCOL.up});
      else if(chg < -0.095) lm.push({x, yy: y(r.h) - 16, t: '跌', col: KCOL.dn});
    }
    if(lm.length > 6) lm.splice(0, lm.length - 6);
    lm.forEach(k => {
      s.push('<rect x="' + (k.x - 8).toFixed(1) + '" y="' + k.yy.toFixed(1) + '" width="16" height="16" rx="3" fill="' + k.col + '"/>'
           + '<text x="' + k.x.toFixed(1) + '" y="' + (k.yy + 11).toFixed(1) + '" text-anchor="middle" font-size="11" fill="#ffffff">' + k.t + '</text>');
    });

    /* 放量 / 放量突破标注 */
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
      s.push('<text x="' + k.x.toFixed(1) + '" y="' + k.yy.toFixed(1) + '" text-anchor="middle" font-size="9" fill="#a0742f">放量</text>');
    });
    if(brk.length > 3) brk.splice(0, brk.length - 3);
    brk.forEach(k => {
      s.push('<text x="' + k.x.toFixed(1) + '" y="' + k.yy.toFixed(1) + '" text-anchor="middle" font-size="9" fill="#a0742f" font-weight="700">突破</text>');
    });

    /* 当前价线 + 三角标记（gutter 左缘，指向 K 线区）+ 估值带滑轨 */
    const yc = y(lastClose);
    if(isFinite(yc) && yc >= this.TL && yc <= priceB){
      s.push('<line x1="0" y1="' + yc.toFixed(1) + '" x2="' + this.px1 + '" y2="' + yc.toFixed(1) + '" stroke="#0071e3" stroke-width="1" opacity=".35"/>'
           + '<polygon points="' + (this.px1 + 7) + ',' + (yc - 3.5).toFixed(1) + ' ' + (this.px1 + 7) + ',' + (yc + 3.5).toFixed(1) + ' ' + (this.px1 + 2) + ',' + yc.toFixed(1) + '" fill="#0071e3"/>');
    }
    if(pr.hasV){
      const yLow = y(pr.vlow), yHigh = y(pr.vhigh);
      s.push('<defs><linearGradient id="vGauge" x1="0" y1="0" x2="0" y2="1">'
           + '<stop offset="0" stop-color="#ff3b30"/><stop offset=".5" stop-color="#0071e3"/><stop offset="1" stop-color="#34c759"/>'
           + '</linearGradient></defs>'
           + '<rect x="' + (this.axX - 8) + '" y="' + yHigh.toFixed(1) + '" width="5" height="' + Math.max(1, yLow - yHigh).toFixed(1) + '" rx="2.5" fill="url(#vGauge)" opacity=".55"/>');
      if(isFinite(yc) && yc >= yHigh - 1 && yc <= yLow + 1){
        s.push('<circle cx="' + (this.axX - 5.5).toFixed(1) + '" cy="' + yc.toFixed(1) + '" r="3" fill="#0071e3" stroke="#ffffff" stroke-width="1.5"/>');
      }
    }

    /* 价格轴（自适应步长） */
    const step = niceStep(pr.pmax - pr.pmin, 5);
    for(let p = Math.ceil(pr.pmin / step) * step; p <= pr.pmax + 1e-9; p += step){
      const yy = y(p);
      if(!isFinite(yy) || yy < this.TL - 2 || yy > priceB + 2) continue;
      s.push('<text x="' + (this.axX + 7) + '" y="' + (yy + 3.5).toFixed(1) + '" font-size="11" fill="#48484a" font-family="SF Mono,monospace">' + fmt2(p) + '</text>');
    }

    /* 时间轴（密度抽稀） */
    const dstep = Math.max(1, Math.ceil(88 / Math.max(this.slot, 0.5)));
    let lastDx = -Infinity;
    for(let i = this._pr.i0; i <= this._pr.i1; i++){
      if(i % dstep !== 0 && i !== this.N - 1) continue;
      const x = this.xOf(i);
      if(x < this.px0 || x > this.px1) continue;
      if(x - lastDx < 80) continue;
      lastDx = x;
      const d = String(this.rows[i].d || '').slice(2, 10);
      s.push('<text x="' + x.toFixed(1) + '" y="' + (this.volBot + 16) + '" font-size="11" fill="#48484a" text-anchor="middle" font-family="SF Mono,monospace">' + d + '</text>');
    }

    /* 越界 S/R 边缘提示（箭头 + 价格徽章 + 原生 title） */
    const edge = (arr, yTop) => {
      let ex = 6;
      arr.slice(0, 3).forEach(x => {
        const yy = yTop ? this.TL + 4 : priceB - 20;
        const lab = (x.up ? '↑ ' : '↓ ') + x.lab;
        const wdt = 16 + lab.length * 6.2;
        s.push('<rect x="' + ex + '" y="' + yy + '" width="' + wdt.toFixed(0) + '" height="16" rx="4" fill="#ffffff" fill-opacity=".92" stroke="rgba(0,0,0,.1)" opacity=".85">'
             + '<title>' + x.method + '</title></rect>'
             + '<text x="' + (ex + 8) + '" y="' + (yy + 11.5) + '" font-size="11" fill="' + x.col + '" font-family="SF Mono,monospace">' + lab + '</text>');
        ex += wdt + 6;
      });
    };
    if(edgeTop.length) edge(edgeTop, true);
    if(edgeBot.length) edge(edgeBot, false);

    /* hover 高亮浮动标签（独立于 chartTip） */
    s.push('<g id="hoverHl" opacity="0">'
      + '<rect id="hoverHlR" x="0" y="0" width="120" height="38" rx="6" fill="#ffffff" fill-opacity=".96" stroke="rgba(0,0,0,.08)"/>'
      + '<text id="hoverHlT1" x="8" y="0" font-size="11" font-weight="700" fill="#1d1d1f" font-family="SF Mono,monospace"></text>'
      + '<text id="hoverHlT2" x="8" y="0" font-size="10" fill="#86868b" font-family="SF Mono,monospace"></text>'
      + '</g>');

    /* 十字光标组 */
    s.push('<g id="chG" opacity="0">'
      + '<line id="chV" x1="0" y1="0" x2="0" y2="0" stroke="rgba(29,29,31,.35)" stroke-width="1" stroke-dasharray="4 4"/>'
      + '<line id="chH" x1="0" y1="0" x2="0" y2="0" stroke="rgba(29,29,31,.35)" stroke-width="1" stroke-dasharray="4 4"/>'
      + '<rect id="chYpill" x="0" y="0" width="' + (this.AX - 4) + '" height="16" rx="4" fill="#1d1d1f" opacity="0"/>'
      + '<text id="chYtxt" x="0" y="0" font-size="11" fill="#ffffff" font-family="SF Mono,monospace"></text>'
      + '<rect id="chXpill" x="0" y="0" width="78" height="16" rx="4" fill="#1d1d1f" opacity="0"/>'
      + '<text id="chXtxt" x="0" y="0" font-size="11" fill="#ffffff" text-anchor="middle" font-family="SF Mono,monospace"></text>'
      + '<circle id="chDot" r="3" fill="none" stroke="#0071e3" stroke-width="1.5" opacity="0"/>'
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
    const ccol = chg > 0 ? '#d94a47' : (chg < 0 ? '#178a59' : '#6e6e73');
    const volTxt = r.v >= 1e8 ? (r.v / 1e8).toFixed(2) + '亿' : (r.v / 1e4).toFixed(1) + '万';
    const zm = zmeta(st);
    const zoneCol = ['#1f9d4d','#1f9d4d','#a0742f','#a0742f','#d70015','#d70015','#6e6e73'][zm.c] || '#6e6e73';
    let t = '<span class="zone-badge" style="background:rgba(110,110,115,.12);color:' + zoneCol + '">' + (st.decision_usable ? zm.label : (st.reference_zone ? '参考 ' + st.reference_zone : zm.label)) + '</span>\n'
      + '<span class="tk">日期: </span>' + r.d + '\n'
      + '<span class="tk">开盘: </span>' + fmt2(r.o) + '  <span class="tk">最高: </span>' + fmt2(r.h) + '\n'
      + '<span class="tk">收盘: </span>' + fmt2(r.c) + '  <span class="tk">最低: </span>' + fmt2(r.l) + '\n'
      + '<span class="tk">涨跌: </span><b style="color:' + ccol + '">' + (chg >= 0 ? '+' : '') + fmt2(chg) + ' (' + (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%)</b>\n'
      + '<span class="tk">成交量: </span>' + volTxt;
    const va5 = this.volC[5] && isFinite(this.volC[5][bi]) && this.volC[5][bi] > 0 ? this.volC[5][bi] : null;
    if(va5) t += '  <span class="tk">VOL5比 </span>' + (r.v / va5).toFixed(2) + '×';
    let mline = '';
    [5,10,20,60,120,250].forEach(w => {
      if(this.maVis[w] && this.maC[w] && isFinite(this.maC[w][bi])) mline += ' <span class="tk">MA' + w + ':</span> ' + fmt2(this.maC[w][bi]);
    });
    if(mline) t += '\n' + mline.trim();
    if(pr.hasV){
      let z = null;
      if(r.c < pr.vlow) z = {t: '深度低估', c: '#1f9d4d'};
      else if(r.c < pr.vmid) z = {t: '低估区', c: '#1f9d4d'};
      else if(r.c <= pr.vhigh) z = {t: '合理区', c: '#0071e3'};
      else z = {t: '高估区', c: '#d70015'};
      const dv = (r.c / pr.vlow - 1) * 100;
      t += '\n<span class="tk">估值位置: </span><b style="color:' + z.c + '">' + z.t + '</b>（距保守 ¥' + fmt2(pr.vlow) + ' ' + (dv >= 0 ? '+' : '') + dv.toFixed(1) + '%）';
    }
    const supLv = (st.support || []).map(x => ({v: +x.level, m: x.method || ''})).filter(x => isFinite(x.v) && x.v > 0);
    const resLv = (st.resistance || []).map(x => ({v: +x.level, m: x.method || ''})).filter(x => isFinite(x.v) && x.v > 0);
    const nearS = supLv.filter(x => x.v < r.c).sort((a,b) => b.v - a.v)[0];
    const nearR = resLv.filter(x => x.v > r.c).sort((a,b) => a.v - b.v)[0];
    const mShort = m => m ? (m.length > 10 ? m.slice(0, 10) + '…' : m) : '';
    if(nearS || nearR){
      const inS = nearS && Math.abs(r.c / nearS.v - 1) <= 0.02;
      const inR = nearR && Math.abs(r.c / nearR.v - 1) <= 0.02;
      t += '\n<span class="tk">最近: </span>'
        + (nearS ? '<span class="' + (inS ? 'near-s' : '') + '">支撑 ¥' + fmt2(nearS.v) + '</span>' + (mShort(nearS.m) ? '（' + mShort(nearS.m) + '）' : '') : '')
        + (nearS && nearR ? '  ' : '')
        + (nearR ? '<span class="' + (inR ? 'near-r' : '') + '">阻力 ¥' + fmt2(nearR.v) + '</span>' + (mShort(nearR.m) ? '（' + mShort(nearR.m) + '）' : '') : '');
    }
    this.tip.innerHTML = t;
  }

  _positionTip(mx, my){
    if(this._isMobile) return;
    const tw = this.tip.offsetWidth || 200, th = this.tip.offsetHeight || 120;
    let lx = mx + 18, ty = my + 18;
    if(lx + tw > this.W - 6) lx = mx - tw - 18;
    if(ty + th > this.H - 6) ty = my - th - 18;
    this.tip.style.left = Math.max(2, lx) + 'px';
    this.tip.style.top = Math.max(2, ty) + 'px';
  }

  /* ---- hover 高亮：S/R 线与估值锚线（≤6px）聚焦 ---- */
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
      /* 浮动详情标签 */
      const g = document.getElementById('hoverHl');
      if(g){
        const name = hit.kind === 'anchor' ? hit.name : (hit.name || ((hit.isSup ? '支撑' : '压力') + '位'));
        const t1 = (hit.kind === 'anchor' ? '' : (hit.ev + '级 ')) + name.slice(0, 14) + ' ¥' + fmt2(hit.price);
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

  /* ---- 交互：拖拽平移 / 点击固定 / 滚轮缩放 ---- */
  _onDown(e){
    if(e.button !== 0 || this.N < 2) return;
    this._drag = { startX: e.clientX, startY: e.clientY, vs: this.viewStart };
    try{ this.sv.setPointerCapture(e.pointerId); }catch(err){}
  }

  _onUp(e){
    const d = this._drag; this._drag = null;
    if(!d) return;
    if(Math.hypot(e.clientX - d.startX, e.clientY - d.startY) < 5){
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
    }
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
    const minSlot = (this.px1 - this.px0) / 10;
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
    this._animateTo(tSlot, tVS);
  }

  _animateTo(tSlot, tVS){
    if(this._anim) cancelAnimationFrame(this._anim);
    const fSlot = this.slot, fVS = this.viewStart;
    const t0 = performance.now(), dur = 300;
    const step = now => {
      const p = Math.min(1, (now - t0) / dur);
      const e = 1 - Math.pow(1 - p, 3);
      this.slot = fSlot + (tSlot - fSlot) * e;
      this.viewStart = fVS + (tVS - fVS) * e;
      this.draw();
      if(p < 1) this._anim = requestAnimationFrame(step);
    };
    this._anim = requestAnimationFrame(step);
  }

  toggleMA(w){
    this.maVis[w] = !this.maVis[w];
    const chip = document.querySelector('.ma-chip[data-ma="' + w + '"]');
    if(chip) chip.classList.toggle('off', !this.maVis[w]);
    this._scheduleDraw();
  }

  toggleBand(){
    this.bandVis = !this.bandVis;
    const chip = document.getElementById('bandChip');
    if(chip) chip.classList.toggle('off', !this.bandVis);
    this._scheduleDraw();
  }

  toggleHollow(){
    this.hollow = !this.hollow;
    const chip = document.getElementById('hollowChip');
    if(chip) chip.classList.toggle('on', this.hollow);
    this._scheduleDraw();
    try{ localStorage.setItem('radar_hollow', this.hollow ? '1' : '0'); }catch(e){}
  }

  setData(st){
    if(!st){ return; }
    if(this._anim){ cancelAnimationFrame(this._anim); this._anim = null; }
    if(this._yAnim){ cancelAnimationFrame(this._yAnim); this._yAnim = null; }
    this._loopOn = false;   /* 停掉旧数据残留渲染循环，setData 尾部重新启动 */
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
    document.getElementById('chartInfo').textContent = this.N < 2
      ? '暂无足够K线数据'
      : '数据截止 ' + DATA.data_date + ' · ' + this.N + ' 根 · 前复权 · 红涨绿跌 · 滚轮缩放 · 拖拽平移 · 双击复位';
    document.getElementById('chartTitle').textContent = st.name + ' · 估值雷达主图（日K）';
    this.tip.classList.remove('show');
    this.wrap.classList.add('fade');
    setTimeout(() => {
      if(tok !== this._dataTok) return;
      this.layout();
      this._fitRange();
      this.draw();
      this._updateSrFoot(st);
      this.wrap.classList.remove('fade');
      this._startLoop();
    }, 130);
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
      '<button class="cap ' + (x.s ? 's' : 'r') + '" title="' + (x.method || '') + ' ¥' + fmt2(+x.level) + '" onclick="KENGINE.scrollToPrice(' + (+x.level) + ')">'
      + '<i></i><span class="v">' + (x.s ? 'S' : 'R') + (i + 1) + ' ¥' + fmt2(+x.level) + '</span></button>').join('');
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
      const need = (this._bandAnim != null) || (this._yAnim != null) || (!this.pinned && this.N >= 2);
      if(need) this._redrawCanvas();
      if(this._bandAnim != null || this._yAnim != null || (!this.pinned && this.N >= 2)){
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
  }
}

const KENGINE = new ValuationChartEngine('chartWrap');

/* ============ 初始化 ============ */
function init(){
  grahamPill();
  renderList();
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
      const w = Math.max(260, Math.min(560, shell.right - e.clientX - 3));
      document.documentElement.style.setProperty('--wall-w', w + 'px');
    });
    const endDrag = () => {
      if(!dragging) return;
      dragging = false;
      grip.classList.remove('dragging');
      document.body.style.cursor = '';
      try{ localStorage.setItem('radar_wall_w', document.documentElement.style.getPropertyValue('--wall-w')); }catch(e){}
    };
    grip.addEventListener('pointerup', endDrag);
    grip.addEventListener('pointercancel', endDrag);
    try{
      const saved = localStorage.getItem('radar_wall_w');
      if(saved) document.documentElement.style.setProperty('--wall-w', saved);
    }catch(e){}
  })();
  let resizeT = null;
  window.addEventListener('resize', () => { clearTimeout(resizeT); resizeT = setTimeout(() => KENGINE.resize(), 150); });
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
