# -*- coding: utf-8 -*-
"""全市场趋势筛选（每日收盘后）· 多源：新浪全市场快照 + 新浪日K逐只真实计算。

东财全市场接口（stock_zh_a_spot_em）被封/限流时自动回退本方案；本方案不依赖东财，
用新浪快照粗筛活跃股（成交额>3亿，约 300-600 只），再逐只拉新浪日K（8线程并发），
真实计算 5/10/20/60日涨幅、MA20方向、量比（5日均量/20日均量）、ATR14、250日位置，
执行四层漏斗·第四层五类分类，每类取前 10（可含自选标记）。

分类规则（D级工程化，与自选池精确分类同规则）：
  排除   ：跌破MA20 且 20日跌幅>5% / K线<60
  回调观察：跌破MA20 且 20日跌幅≤5%
  高位观察：250日位置>80% 或 20日涨幅>25%
  启动观察：站上MA20、5日涨幅>0、20日涨幅<10%、10日涨幅<15%
  趋势观察：站上MA20 且 MA20上行（其余站上MA20者归此）

输出：state.json["market_screen"] = {as_of, updated_at, stats, classes:{类:[前10]}, note}
"""
import concurrent.futures
import datetime
import json
import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(BASE, "state.json")
WATCHLIST = os.path.join(BASE, "watchlist.json")

TOP_N = 10
MIN_TURNOVER = 8e8          # 粗筛：成交额 > 8 亿元（限流下控制候选量，约 250 只）
MAX_CANDIDATES = 300
WORKERS = 5                  # 腾讯限流敏感，并发过高会大量失败重试拖慢整体


def log(msg):
    line = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    with open(os.path.join(BASE, "logs", "screener.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")
    try:
        print(line)
    except Exception:
        pass


def num(v):
    try:
        f = float(v)
        return f if f == f else None
    except Exception:
        return None


def ts_ma(closes, w, end=None):
    if end is None:
        end = len(closes)
    if end < w:
        return None
    return sum(closes[end - w:end]) / w


def ts_ret(closes, n):
    if len(closes) <= n or not (closes[len(closes) - 1 - n] > 0):
        return None
    return (closes[-1] / closes[len(closes) - 1 - n] - 1) * 100


def ts_atr(rows):
    if len(rows) < 15:
        return None
    s = 0
    for i in range(1, 15):
        r = rows[-i]
        p = rows[-i - 1]
        s += max(r[2] - r[3], abs(r[2] - p[1]), abs(r[3] - p[1]))
    return s / 14


def fetch_daily(code):
    """日K（前复权，限 start_date 只拉近 ~14 个月 ≈ 290 根），腾讯主源/新浪备，返回 [(date, close, high, low, volume), ...] 或 None"""
    code = str(code).strip()
    if code[:2] in ("sh", "sz", "bj"):
        sym = code
        code = code[2:]
    else:
        prefix = "sh" if code.startswith("6") else ("bj" if code.startswith(("4", "8", "9")) else "sz")
        sym = prefix + code
    sd = "20240801"
    import akshare as ak
    for attempt in range(2):
        try:
            df = ak.stock_zh_a_hist_tx(symbol=sym, start_date=sd, end_date=datetime.date.today().isoformat(), adjust="qfq")
            if df is None or df.empty:
                raise RuntimeError("empty")
            rows = []
            for _, r in df.iterrows():
                rows.append((str(r["date"]), float(r["close"]), float(r["high"]),
                             float(r["low"]), float(r["volume"]) * 100))
            if len(rows) >= 60:
                return rows
            raise RuntimeError("too short")
        except RuntimeError:
            return None
        except Exception as e:
            if getattr(fetch_daily, "_dbg", 0) < 3:
                log(f"  DBG tx {sym} {type(e).__name__}: {str(e)[:150]}")
                fetch_daily._dbg = getattr(fetch_daily, "_dbg", 0) + 1
    try:
        df = ak.stock_zh_a_daily(symbol=sym, start_date=sd, adjust="qfq")
        if df is None or df.empty:
            return None
        rows = []
        for _, r in df.iterrows():
            rows.append((str(r["date"])[:10], float(r["close"]), float(r["high"]),
                         float(r["low"]), float(r["volume"])))
        if len(rows) >= 60:
            return rows
        return None
    except Exception as e:
        if getattr(fetch_daily, "_dbg", 0) < 6:
            log(f"  DBG sin {sym} {type(e).__name__}: {str(e)[:150]}")
            fetch_daily._dbg = getattr(fetch_daily, "_dbg", 0) + 1
    return None


def screen_candidate(code, name, rows):
    closes = [r[1] for r in rows]
    n = len(closes)
    if n < 60:
        return None
    price = closes[-1]
    m20, m60 = ts_ma(closes, 20), ts_ma(closes, 60)
    m20prev = ts_ma(closes, 20, n - 5)
    r5, r10, r20, r60 = ts_ret(closes, 5), ts_ret(closes, 10), ts_ret(closes, 20), ts_ret(closes, 60)
    v5 = sum(r[4] for r in rows[-5:]) / 5
    v20 = sum(r[4] for r in rows[-20:]) / 20
    vr = v5 / v20 if v20 > 0 else None
    atr = ts_atr(rows)
    atr_pct = atr / price * 100 if atr and price > 0 else None
    hi = max(r[2] for r in rows[-250:])
    lo = min(r[3] for r in rows[-250:])
    pos250 = (price - lo) / (hi - lo) * 100 if hi > lo else None
    dist20 = (price / m20 - 1) * 100 if m20 else None
    m20_up = m20 is not None and m20prev is not None and m20 > m20prev
    day_chg = (closes[-1] / closes[-2] - 1) * 100 if n > 1 else None
    above20 = m20 is not None and price > m20
    return dict(code=code, name=name, price=price, chg=day_chg, r5=r5, r10=r10, r20=r20, r60=r60,
                vr=vr, atr_pct=atr_pct, pos250=pos250, dist20=dist20, m20_up=m20_up, above20=above20,
                m20g60=(m20 is not None and m60 is not None and m20 > m60))


def classify(d):
    if not d["above20"]:
        if d["r20"] is not None and d["r20"] <= -5:
            return "排除", f"跌破MA20且20日跌{d['r20']:.1f}%"
        return "回调观察", f"跌破MA20{d['dist20']:+.1f}%，20日{d['r20']:+.1f}%"
    if d["pos250"] is not None and d["pos250"] > 80:
        return "高位观察", f"250日位置{d['pos250']:.0f}%（近高位）"
    if d["r20"] is not None and d["r20"] > 25:
        return "高位观察", f"20日涨幅{d['r20']:.1f}%>25%"
    if d["m20_up"]:
        return "趋势观察", f"站上MA20且MA20上行{d['dist20']:+.1f}%"
    if d["r5"] is not None and d["r5"] > 0 and d["r20"] is not None and d["r20"] < 10:
        if d["r10"] is not None and d["r10"] < 15:
            return "启动观察", f"刚站上MA20、5日{d['r5']:+.1f}%转正、20日{d['r20']:+.1f}%"
        return "趋势观察", f"站上MA20，10日{d['r10']:+.1f}%反弹"
    return "趋势观察", "站上MA20"


def main():
    # 禁用 akshare 内部 tqdm（多线程并发下 tqdm 非线程安全，会导致全部请求失败）
    try:
        import tqdm
        if not getattr(tqdm, '_radar_quiet', False):
            _orig_tqdm = tqdm.tqdm

            def _quiet(*a, **k):
                it = a[0] if a else k.get("iterable")
                return it if it is not None else _orig_tqdm(*a, **k)
            tqdm.tqdm = _quiet
            tqdm._radar_quiet = True
    except Exception:
        pass

    try:
        import akshare as ak
    except Exception as e:
        log(f"akshare 不可用: {e}")
        return

    try:
        with open(WATCHLIST, encoding="utf-8") as f:
            watch = {s["ticker"] for s in json.load(f)["stocks"]}
    except Exception:
        watch = set()

    # 1) 全市场快照（新浪，重试3次）
    df = None
    for attempt in range(3):
        try:
            df = ak.stock_zh_a_spot()
            break
        except Exception as e:
            log(f"新浪全市场快照第{attempt + 1}次失败: {type(e).__name__}: {str(e)[:100]}")
            time.sleep(6 * (attempt + 1))
    if df is None or df.empty:
        log("全市场快照抓取失败（3次），跳过本轮")
        return
    log(f"全市场快照: {len(df)} 行")

    # 2) 粗筛活跃股
    cands = []
    for _, row in df.iterrows():
        code = str(row.get("代码", "")).strip()
        name = str(row.get("名称", "")).strip()
        if not code or not name:
            continue
        if code[:2] in ("sh", "sz", "bj"):   # 新浪代码列带市场前缀，剥成 6 位
            code = code[2:]
        if len(code) != 6:
            continue
        if name.startswith("ST") or "退" in name:
            continue
        if code.startswith(("4", "8", "9")):
            continue
        amt = num(row.get("成交额"))
        if amt is None or amt < MIN_TURNOVER:
            continue
        cands.append((code, name, num(row.get("最新价")), num(row.get("涨跌幅")), amt))
    cands.sort(key=lambda x: -(x[4] or 0))
    cands = cands[:MAX_CANDIDATES]
    log(f"粗筛活跃股（成交额>{MIN_TURNOVER / 1e8:.0f}亿）: {len(cands)} 只，开始拉日K")

    # 3) 并发拉日K并计算
    results = []
    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(fetch_daily, c[0]): c for c in cands}
        done = 0
        for fut in concurrent.futures.as_completed(futs):
            c = futs[fut]
            done += 1
            try:
                rows = fut.result()
                if rows:
                    d = screen_candidate(c[0], c[1], rows)
                    if d:
                        d["watch"] = c[0] in watch
                        results.append(d)
            except Exception as e:
                if getattr(main, "_dbg", 0) < 5:
                    log(f"  DBG screen {c[0]} {type(e).__name__}: {str(e)[:200]}")
                    main._dbg = getattr(main, "_dbg", 0) + 1
            if done % 100 == 0:
                log(f"  日K {done}/{len(cands)}")
    log(f"日K完成 {len(results)} 只，耗时 {time.time() - t0:.0f}s")

    # 4) 五类分类 + 前10
    classes = {k: [] for k in ("启动观察", "趋势观察", "高位观察", "回调观察", "排除")}
    for d in results:
        c, why = classify(d)
        d["why"] = why
        classes[c].append(d)
    order = {"启动观察": lambda d: -(d["chg"] or 0),
             "趋势观察": lambda d: -(d["r20"] or 0),
             "高位观察": lambda d: -(d["r20"] or 0),
             "回调观察": lambda d: -(d["chg"] or 0),
             "排除": lambda d: (d["r20"] or 0)}
    out = {}
    for c, items in classes.items():
        items.sort(key=order[c])
        slim = []
        for it in items[:TOP_N]:
            slim.append({k: it.get(k) for k in
                         ("code", "name", "price", "chg", "r5", "r10", "r20", "r60",
                          "vr", "atr_pct", "pos250", "dist20", "watch", "why")})
        out[c] = slim
        log(f"  {c}: {len(items)} 只 → 展示前 {len(slim)}")

    screen = {
        "as_of": datetime.date.today().isoformat(),
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stats": {"total": len(results), "candidates": len(cands),
                  "counts": {c: len(classes[c]) for c in classes}},
        "classes": out,
        "note": "新浪全市场快照粗筛（成交额>3亿）→ 新浪日K真实计算 5/10/20/60日涨幅/MA20/量比/ATR/250日位置（D级工程化）；前10按类内排序",
    }
    with open(STATE, encoding="utf-8") as f:
        state = json.load(f)
    state["market_screen"] = screen
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    log(f"已写入 state.json market_screen（分类 {len(results)} 只）")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"全市场趋势筛选失败: {type(e).__name__}: {e}")
        sys.exit(1)
