# -*- coding: utf-8 -*-
"""市场真实行业板块强弱（每日收盘后）· 同花顺行业板块。

数据源：akshare 同花顺行业汇总（90 个行业板块：涨跌幅/净流入/上涨家数/下跌家数/领涨股）
+ 同花顺板块指数历史（近 6 个月，并发拉取）→ 真实计算 5/20 日涨幅。

分类规则（D级工程化）：
  持续强势：20日涨幅>0 且 当日涨幅>0 且 上涨家数占比≥55%
  正在加强：20日涨幅>0 且（当日涨幅>0 且 占比<55% 或 5日涨幅>20日涨幅）
  走弱/观望：其余

展示：每类按 20日涨幅排序取前 12（组内总量在 stats.counts 中）。
输出：state.json["sector_strength"]
"""
import concurrent.futures
import datetime
import json
import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(BASE, "state.json")
TOP_PER_CLASS = 12
WORKERS = 8


def log(msg):
    line = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    with open(os.path.join(BASE, "logs", "sector.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")
    try:
        print(line)
    except Exception:
        pass


def num(v):
    try:
        f = float(str(v).replace("%", "").replace("--", "nan").replace(",", ""))
        return f if f == f else None
    except Exception:
        return None


def fetch_sector_hist(name):
    """板块指数近 6 个月日K → (r5, r20)"""
    import akshare as ak
    for attempt in range(2):
        try:
            df = ak.stock_board_industry_index_ths(symbol=name, start_date="20260301",
                                                   end_date=datetime.date.today().isoformat())
            if df is None or df.empty:
                return None
            closes = [float(r) for r in df["收盘价"]]
            if len(closes) < 25:
                return None
            r5 = (closes[-1] / closes[-6] - 1) * 100 if closes[-6] > 0 else None
            r20 = (closes[-1] / closes[-21] - 1) * 100 if len(closes) > 21 and closes[-21] > 0 else None
            return (r5, r20)
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    return None


def main():
    try:
        import akshare as ak
    except Exception as e:
        log(f"akshare 不可用: {e}")
        return

    try:
        df = ak.stock_board_industry_summary_ths()
    except Exception as e:
        log(f"同花顺行业汇总失败: {type(e).__name__}: {str(e)[:120]}")
        return
    if df is None or df.empty:
        log("行业汇总为空")
        return
    log(f"行业板块: {len(df)} 个")

    rows = []
    for _, r in df.iterrows():
        name = str(r.get("板块", "")).strip()
        if not name:
            continue
        up = num(r.get("上涨家数"))
        dn = num(r.get("下跌家数"))
        rows.append({
            "name": name,
            "chg": num(r.get("涨跌幅")),
            "net_inflow": num(r.get("净流入")),
            "up_cnt": up, "dn_cnt": dn,
            "leader": str(r.get("领涨股", "")).strip(),
            "leader_chg": num(r.get("领涨股-涨跌幅")),
        })
    log(f"清洗后 {len(rows)} 个板块")

    # 并发拉板块历史
    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(fetch_sector_hist, r["name"]): r for r in rows}
        done = 0
        for fut in concurrent.futures.as_completed(futs):
            r = futs[fut]
            done += 1
            try:
                h = fut.result()
                if h:
                    r["r5"], r["r20"] = h
            except Exception:
                pass
            if done % 30 == 0:
                log(f"  板块历史 {done}/{len(rows)}")
    log(f"板块历史完成，耗时 {time.time() - t0:.0f}s")

    # 分类
    classes = {"持续强势": [], "正在加强": [], "走弱/观望": []}
    for r in rows:
        r20, r5, chg = r.get("r20"), r.get("r5"), r.get("chg")
        up, dn = r.get("up_cnt"), r.get("dn_cnt")
        ratio = (up / (up + dn) * 100) if (up is not None and dn is not None and up + dn > 0) else None
        r["up_ratio"] = ratio
        if r20 is not None and r20 > 0 and chg is not None and chg > 0 and ratio is not None and ratio >= 55:
            classes["持续强势"].append(r)
        elif r20 is not None and r20 > 0 and ((chg is not None and chg > 0 and (ratio is None or ratio < 55))
                                              or (r5 is not None and r5 > r20)):
            classes["正在加强"].append(r)
        else:
            classes["走弱/观望"].append(r)

    out = {}
    for c, items in classes.items():
        items.sort(key=lambda x: -(x.get("r20") if x.get("r20") is not None else -999))
        out[c] = items[:TOP_PER_CLASS]
        log(f"  {c}: {len(items)} 个 → 展示前 {len(out[c])}")

    screen = {
        "as_of": datetime.date.today().isoformat(),
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stats": {"total": len(rows), "counts": {c: len(classes[c]) for c in classes}},
        "classes": out,
        "note": "同花顺 90 行业板块（涨跌幅/净流入/上涨家数/领涨股）+ 板块指数近6月历史算 5/20日涨幅（D级工程化）；每类按20日涨幅取前12",
    }
    with open(STATE, encoding="utf-8") as f:
        state = json.load(f)
    state["sector_strength"] = screen
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    log("已写入 state.json sector_strength")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"板块强弱更新失败: {type(e).__name__}: {e}")
        sys.exit(1)
