# -*- coding: utf-8 -*-
"""一次性迁移：用 spec 合规后的估值引擎重算 state.json 决策数据（无需网络）。

复用 state.json 中已存储的 forecast_data / 行情 / K 线，重新执行
update_daily.compute_stock，使 TTM 基数错配降级、model_confidence、
PEG 交叉检查等 spec 修正立即生效。
"""
import io
import json
import os
import sys
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE = r"E:\财报解读\watchlist"
WATCHLIST = os.path.join(BASE, "watchlist.json")
STATE = os.path.join(BASE, "state.json")

import update_daily  # noqa: E402


def main():
    with open(WATCHLIST, encoding="utf-8") as f:
        wl = json.load(f)
    with open(STATE, encoding="utf-8") as f:
        state = json.load(f)

    old = state.get("stocks") or {}
    new = {}
    as_of = datetime.date.today().isoformat()
    migrated = 0

    for s in wl["stocks"]:
        tk = s["ticker"]
        prev = old.get(tk) or {}
        if not prev.get("price"):
            continue
        market = {
            "price": prev.get("price"),
            "pct": prev.get("pct", 0.0),
            "pe_ttm": prev.get("pe_ttm"),
            "pb": prev.get("pb"),
            "total_mv": prev.get("total_mv"),
            "kline": prev.get("kline") or [],
            "kline_stale": prev.get("kline_stale", False),
            "kline_meta": prev.get("kline_meta") or {},
            "spot_stale": prev.get("spot_stale", False),
            "spot_meta": prev.get("spot_meta") or {},
        }
        cfg = dict(s)
        cfg["market"] = market
        out = update_daily.compute_stock(
            cfg, prev, prev.get("forecast_data"), prev.get("forecast_meta"), as_of
        )
        if out is None:
            continue
        out["support"] = prev.get("support") or []
        out["resistance"] = prev.get("resistance") or []
        new[tk] = out
        migrated += 1
        print(
            f"{tk} {s.get('name')}: {out['decision_status']} grade={ (out.get('data_quality') or {}).get('grade') }"
            f" confidence={out.get('model_confidence')}"
            f" msq={out.get('multiple_source_quality')}"
        )

    state["stocks"] = new
    state.setdefault("meta", {})["updated_at"] = (
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " (spec-migration)"
    )
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"\n迁移完成：{migrated} 只股票已用新引擎重算并写回 state.json")


if __name__ == "__main__":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    main()
