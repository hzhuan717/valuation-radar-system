# -*- coding: utf-8 -*-
"""大盘拥挤度（成交额前5%个股占比）历史序列 + 极值轮次（乐咕乐股 akshare）。

口径：成交额排名前5%个股成交额占全市场总成交额比重（大盘拥挤度，牛熊转换参考指标）。
- 历史源：ak.stock_a_congestion_lg()，2011-09 至今日频，官网滞后约 2 个月。
- 当日值：由 fetch_market_screener.py 用新浪全市场快照现算写入
  state.json["market_screen"]["congestion"]（当日即时，本地现算）。
- 本脚本：拉取历史序列 → 计算 ≥45% 连续极值轮次（峰值/起止）→ 合并当日现算值
  → 写回 state.json["market_screen"]["congestion"]。

仅研究标注（D级工程化），不构成仓位指令。
"""
import datetime
import json
import os
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(BASE, "state.json")
CACHE = os.path.join(BASE, "congestion_hist.json")

THRESHOLD = 0.45      # 历史公认拥挤警戒线
MIN_EPISODE = 1       # 连续≥1 个交易日即成一轮（峰值口径保留单日尖峰）
TOP_N = 7             # 展示历史极值轮次数量


def log(msg):
    line = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
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


def fetch_history():
    """乐咕历史序列 → [(date, close, congestion), ...]，失败返回 None"""
    try:
        import akshare as ak
        df = ak.stock_a_congestion_lg()
        out = []
        for _, r in df.iterrows():
            d = str(r.get("date", "")).strip()
            c = num(r.get("congestion"))
            if not d or c is None:
                continue
            out.append([d, num(r.get("close")), c])
        return out
    except Exception as e:
        log(f"乐咕历史抓取失败: {type(e).__name__}: {e}")
        return None


def load_cache():
    try:
        with open(CACHE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"points": [], "updated_at": None}


def save_cache(data):
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def compute_peaks(points):
    """连续 ≥45% 交易日聚合成一轮极值，返回 [{start, end, peak_date, peak}, ...] 按峰值降序"""
    episodes = []
    cur = None
    for d, _, c in points:
        if c >= THRESHOLD:
            if cur is None:
                cur = {"start": d, "end": d, "peak_date": d, "peak": c}
            else:
                cur["end"] = d
                if c > cur["peak"]:
                    cur["peak"] = c
                    cur["peak_date"] = d
        else:
            if cur is not None:
                episodes.append(cur)
                cur = None
    if cur is not None:
        episodes.append(cur)
    episodes.sort(key=lambda e: -e["peak"])
    return episodes


def main():
    hist = load_cache()
    points = fetch_history()
    if points is None:
        points = hist.get("points", [])
        log("回退本地缓存历史序列")
        if not points:
            log("无历史数据，跳过拥挤度极值更新")
            return
    hist["points"] = points
    hist["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_cache(hist)

    peaks = compute_peaks(points)
    top = peaks[:TOP_N]

    with open(STATE, encoding="utf-8") as f:
        state = json.load(f)
    con = state.setdefault("market_screen", {}).setdefault("congestion", {})
    last = points[-1] if points else None
    con["history"] = {
        "source": "legulegu-akshare",
        "updated_at": hist["updated_at"],
        "points": len(points),
        "first_date": points[0][0] if points else None,
        "last_date": last[0] if last else None,
        "last_value": round(last[2] * 100, 2) if last else None,
        "threshold": THRESHOLD * 100,
        "episodes_total": len(peaks),
        "peaks": [{"start": e["start"], "end": e["end"],
                   "peak_date": e["peak_date"], "peak": round(e["peak"] * 100, 1)}
                  for e in top],
    }
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    log(f"大盘拥挤度历史更新完成：{len(points)} 点（{points[0][0]}~{last[0]}），"
        f"≥45% 共 {len(peaks)} 轮，展示前 {len(top)} 轮；最高峰值 "
        f"{round(top[0]['peak'] * 100, 1)}% @ {top[0]['peak_date']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"大盘拥挤度历史更新失败: {type(e).__name__}: {e}")
        sys.exit(1)