# -*- coding: utf-8 -*-
"""估值雷达估值区间 · 每日更新流水线

流程：交易日判断 → 大盘数据（中证全指000985加权/等权 + 上证 + 沪深300 + 中债10Y）
      → 个股实时行情 + 260日K线 + 同花顺结构化一致预期
      → 模型路由与质量门 → 可审计估值 → 信号diff
      → 写快照/state → 重建门户 HTML → 日志。

设计纪律：
  · watchlist.json 是模型/倍数配置；预测 EPS 每日从带来源的结构化页面刷新
  · 任一数据源失败 → 保留失败元数据；旧预测最多用于 reference_only，绝不 price/PE 回退
  · 模型不匹配或质量门失败 → fail-closed，不输出估值动作信号
  · 交易日历（新浪）失败时回退周一~周五

用法：
  python update_daily.py            # 常规：仅交易日且非节假日执行
  python update_daily.py --force    # 强制执行（引导/补跑用）
"""
import argparse
import datetime
import json
import os
import statistics
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_fetch import (fetch_spot, fetch_kline, fetch_csindex_pe,  # noqa: E402
                        fetch_bond_10y, fetch_trade_calendar,
                        fetch_ths_worth_forecast, now)
from valuation_engine_v2 import evaluate_stock  # noqa: E402

BASE = r"E:\财报解读\watchlist"
WATCHLIST = os.path.join(BASE, "watchlist.json")
STATE = os.path.join(BASE, "state.json")
SNAP_DIR = os.path.join(BASE, "snapshots")
LOG = os.path.join(BASE, "logs", "update.log")
PORTAL = os.path.join(BASE, "output", "估值雷达门户.html")
BUILD = os.path.join(BASE, "scripts", "build_dashboard.py")


def log(msg: str):
    line = f"[{now()}] {msg}"
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    try:
        print(line)
    except Exception:
        pass


def is_trading_day() -> bool:
    days, meta = fetch_trade_calendar()
    today = datetime.date.today().isoformat()
    if days is None:
        log(f"交易日历获取失败({meta.get('error')})，回退周一~周五判断")
        return datetime.date.today().weekday() < 5
    return today in days


def load_state() -> dict:
    if os.path.exists(STATE):
        try:
            with open(STATE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"meta": {}, "market": {}, "stocks": {}}


def save_state(state: dict):
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def ma(rows, win: int):
    if len(rows) < win:
        return None
    return round(sum(r["c"] for r in rows[-win:]) / win, 3)


def annual_vol(rows) -> float | None:
    if len(rows) < 30:
        return None
    closes = [r["c"] for r in rows[-61:]]
    rets = [(closes[i] / closes[i - 1] - 1) for i in range(1, len(closes))]
    if not rets:
        return None
    return round(statistics.stdev(rets) * (252 ** 0.5), 4)


def _forecast_summary(engine: dict, meta: dict) -> str:
    selected = engine.get("forecast") or {}
    if selected:
        if selected.get("basis") == "NORMALIZED":
            return (
                f"正常化盈利模型（周期ROE分位×最新每股净资产，窗口{selected.get('window') or '—'}，"
                f"{selected.get('count', 0)}个年报）：bear/base/bull="
                f"{selected.get('bear')}/{selected.get('base')}/{selected.get('bull')}，"
                f"as_of={selected.get('source_as_of') or '—'}"
            )
        if selected.get("basis") in ("BANK_PB_ROE", "INFRA_PB_BAND"):
            return f"{selected.get('label') or selected.get('basis')}（历史PB分位带 B 级校准，参考级）"
        label = selected.get("label") or selected.get("basis") or "明确年度"
        return (
            f"同花顺F10一致预期 {label}（{selected.get('count', 0)}家，"
            f"min/mean/max={selected.get('bear')}/{selected.get('base')}/{selected.get('bull')}），"
            f"as_of={selected.get('source_as_of') or '—'}"
        )
    if meta.get("status") == "not_applicable":
        return "该模型不使用盈利一致预期"
    if meta.get("error"):
        return f"同花顺预测抓取失败：{meta.get('error')}"
    return "未取得符合质量门的结构化预测"


def compute_stock(st: dict, prev: dict, forecast_data: dict | None,
                  forecast_meta: dict | None, as_of: str) -> dict:
    """行情/技术指标 + v2 估值引擎；blocked 时禁止产生动作信号。"""
    m = st.get("market", {})
    price = m.get("price")
    if price is None:
        return None

    engine = evaluate_stock(st, m, forecast_data, forecast_meta, as_of=as_of)
    valuation = engine.get("valuation") or {}
    decision = engine.get("decision") or {}
    selected = engine.get("forecast") or {}
    usable = bool(engine.get("decision_usable"))
    decision_status = engine.get("decision_status")
    v_low, v_mid, v_high = (valuation.get("v_low"), valuation.get("v_mid"),
                            valuation.get("v_high"))
    if usable:
        zone = decision.get("zone")
    elif decision_status == "reference_only":
        zone = "参考区间"
    elif decision_status == "observe":
        zone = "观察"
    else:
        zone = "待补充数据"
    action = decision.get("action") if usable else None
    # MOS/区间位置是动作层指标；reference/blocked 只在 decision_data 内保留审计值，
    # 不向旧门户顶层暴露，避免被误读为可执行结论。
    mos = decision.get("margin_of_safety") if usable else None
    pct = decision.get("band_position") if usable else None
    band_pos_raw = decision.get("band_position_raw") if usable else None
    blockers = [b.get("detail") for b in (engine.get("quality") or {}).get("blockers", [])]

    kline = m.get("kline") or []
    out = {
        "ticker": st["ticker"], "name": st["name"], "route": st.get("route", "equity"),
        "price": price, "pct": m.get("pct", 0.0), "pe_ttm": m.get("pe_ttm"),
        "pb": m.get("pb"), "total_mv": m.get("total_mv"),
        "v_low": v_low, "v_mid": v_mid, "v_high": v_high,
        "zone": zone, "action": action, "mos": mos, "pctile": pct,
        "band_pos_raw": band_pos_raw,
        "stop_reasons": blockers,
        "_blockers": blockers,
        "reference_zone": decision.get("reference_zone"),
        "ma5": ma(kline, 5), "ma10": ma(kline, 10), "ma20": ma(kline, 20),
        "ma60": ma(kline, 60), "ma120": ma(kline, 120), "ma250": ma(kline, 250),
        "vol": annual_vol(kline),
        "kline": kline, "kline_n": len(kline), "kline_stale": m.get("kline_stale", False),
        "kline_meta": m.get("kline_meta") or {},
        "spot_stale": m.get("spot_stale", False),
        "spot_meta": m.get("spot_meta") or {},
        "needs_review": engine.get("decision_status") != "ready",
        "notes": st.get("notes", ""),
        "support": st.get("support") or [],
        "resistance": st.get("resistance") or [],
        "eps_bear": selected.get("bear"), "eps_base": selected.get("base"),
        "eps_bull": selected.get("bull"),
        "ev_per_share": st.get("ev_per_share"),
        "ev_as_of": st.get("ev_as_of"),
        "pev_low": st.get("pev_low"), "pev_mid": st.get("pev_mid"), "pev_high": st.get("pev_high"),
        "pev_now": (engine.get("valuation") or {}).get("pev_now"),
        "norm": st.get("normalized") or {},
        "bvps": (st.get("bank") or {}).get("bps") or (st.get("infra") or {}).get("bps"),
        "pb_low": st.get("pb_low"), "pb_mid": st.get("pb_mid"), "pb_high": st.get("pb_high"),
        "pb_source": st.get("pb_source"),
        "diagnostics": engine.get("diagnostics"),
        "pe_low": st.get("pe_low"), "pe_mid": st.get("pe_mid"), "pe_high": st.get("pe_high"),
        "pe_source": st.get("pe_source"),
        "multiple_source": (engine.get("multiple") or {}).get("source"),
        "multiple_source_method": ((engine.get("multiple") or {}).get("source") or {}).get("method"),
        "multiple_source_quality": ((engine.get("multiple") or {}).get("source") or {}).get("quality") or
                                   ((engine.get("multiple") or {}).get("source") or {}).get("grade"),
        "eps_source": _forecast_summary(engine, forecast_meta or {}),
        "forecast_source": _forecast_summary(engine, forecast_meta or {}),
        "forecast_year": selected.get("year"),
        "forecast_basis": selected.get("basis"),
        "actual_eps_history": selected.get("actual_eps_history") or
                              (forecast_data or {}).get("actual_eps_history") or [],
        "forecast_data": forecast_data,
        "forecast_meta": forecast_meta or {},
        "valuation_model": engine.get("model"),
        "decision_status": decision_status,
        "decision_usable": usable,
        "reference_usable": bool(engine.get("reference_usable")),
        "data_quality": engine.get("quality"),
        "calc_steps": valuation.get("calc_steps") or [],
        "sources": engine.get("sources") or [],
        "decision_data": engine,
        "growth_momentum": engine.get("growth_momentum"),
        "review_date": st.get("review_date"),
        "signals": [],
    }

    # 只有通过质量门的 ready 结果才允许产生估值/动作信号。
    pv = prev or {}
    prev_price = pv.get("price")
    prev_zone = pv.get("zone")
    prev_usable = bool(pv.get("decision_usable"))
    if usable and prev_usable and prev_price is not None and price != prev_price:
        for key, label in (("v_low", "V_low"), ("v_mid", "V_mid"), ("v_high", "V_high")):
            vv = out[key]
            if vv is None:
                continue
            if prev_price <= vv < price:
                out["signals"].append(f"上穿 {label}（{vv}）")
            elif prev_price >= vv > price:
                out["signals"].append(f"下破 {label}（{vv}）")
    if usable and prev_usable and prev_zone and prev_zone != zone:
        out["signals"].insert(0, f"区间变化：{prev_zone} → {zone}")
    if usable and isinstance(out["pct"], (int, float)) and abs(out["pct"]) >= 3:
        out["signals"].append(f"单日波动 {out['pct']:+.2f}%")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="强制执行（跳过交易日判断）")
    ap.add_argument("--as-of", default=None, metavar="YYYY-MM-DD",
                    help="按指定日期收盘计算：K线截断到该日、价格/涨跌幅取该日收盘，估值基准日=该日")
    args = ap.parse_args()

    log("=== 每日更新开始 ===")
    if args.as_of:
        log(f"估值基准日 as-of = {args.as_of}（K线与价格截断到该日收盘）")
    if not args.force and not is_trading_day():
        log("非交易日，跳过。")
        return

    with open(WATCHLIST, encoding="utf-8") as f:
        wl = json.load(f)
    stocks_cfg = {s["ticker"]: s for s in wl["stocks"]}
    prev_state = load_state()
    prev_map = prev_state.get("stocks", {})
    today = datetime.date.today().isoformat()
    as_of = args.as_of or today

    # ---- 保险股 EV/NBV 专项（insurance_pev 路由输入，每日刷新，须先于个股计算）----
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from fetch_insurance_ev import main as insurance_ev_main
        insurance_ev_main()
        log("保险 EV/NBV 更新完成（东财F10）")
        with open(WATCHLIST, encoding="utf-8") as f:
            wl = json.load(f)
        stocks_cfg = {s["ticker"]: s for s in wl["stocks"]}
    except Exception as e:
        log(f"保险 EV/NBV 更新失败: {e}")

    # ---- 周期股正常化盈利专项（normalized_pe 路由输入，每日刷新）----
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from fetch_normalized_eps import main as normalized_main
        normalized_main()
        with open(WATCHLIST, encoding="utf-8") as f:
            wl = json.load(f)
        stocks_cfg = {s["ticker"]: s for s in wl["stocks"]}
        log("周期股正常化盈利更新完成（同花顺财务摘要）")
    except Exception as e:
        log(f"周期股正常化盈利更新失败: {e}")

    # ---- 专项路由数据（银行PB-ROE / 建筑现金流，每日刷新）----
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from fetch_special_routes import main as special_main
        special_main()
        with open(WATCHLIST, encoding="utf-8") as f:
            wl = json.load(f)
        stocks_cfg = {s["ticker"]: s for s in wl["stocks"]}
        log("专项路由数据更新完成（银行/建筑）")
    except Exception as e:
        log(f"专项路由数据更新失败: {e}")

    # ---- 估值倍数历史分位校准（forward_pe/growth_pe，B级锚定）----
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from calibrate_multiples import main as calibrate_main
        calibrate_main()
        with open(WATCHLIST, encoding="utf-8") as f:
            wl = json.load(f)
        stocks_cfg = {s["ticker"]: s for s in wl["stocks"]}
        log("估值倍数校准完成（百度股市通5年分位）")
    except Exception as e:
        log(f"估值倍数校准失败: {e}")

    # ---- 大盘 ----
    market = dict(prev_state.get("market", {}))
    cs, cs_meta = fetch_csindex_pe("000985")
    sh, sh_meta = fetch_csindex_pe("000001")
    hs, hs_meta = fetch_csindex_pe("000300")
    bond, bond_meta = fetch_bond_10y()

    if cs:
        market["cs985"] = {"date": cs["date"], "pe_weighted": cs["pe_weighted"],
                           "pe_equal": cs["pe_equal"], "source": cs_meta["source"]}
    elif not market.get("cs985"):
        market["cs985"] = {"stale": True, "note": "采集失败，无历史值"}
    else:
        market["cs985"]["stale"] = True
        market["cs985"]["stale_note"] = "本次采集失败，沿用历史值（仅市场背景，不产生动作）"
    for key, obj, meta in (("sh", sh, sh_meta), ("hs300", hs, hs_meta)):
        if obj:
            market[key] = {"date": obj["date"], "pe": float(obj["pe_weighted"]), "source": meta["source"]}
        elif not market.get(key):
            market[key] = {"stale": True, "note": "采集失败，无历史值"}
        else:
            market[key]["stale"] = True
            market[key]["stale_note"] = "本次采集失败，沿用历史值（仅市场背景，不产生动作）"
    if bond:
        market["bond_10y"] = {"date": bond["date"], "value": bond["value"], "source": bond_meta["source"]}
    elif not market.get("bond_10y"):
        market["bond_10y"] = {"stale": True, "note": "采集失败，无历史值"}
    else:
        market["bond_10y"]["stale"] = True
        market["bond_10y"]["stale_note"] = "本次采集失败，沿用历史值（仅市场背景，不产生动作）"

    # 格雷厄姆指数（多口径）
    bv = market.get("bond_10y", {}).get("value")
    metrics = []
    if bv:
        for key, label, pe in (("cs985", "中证全指·加权", market.get("cs985", {}).get("pe_weighted")),
                               ("cs985e", "中证全指·等权", market.get("cs985", {}).get("pe_equal")),
                               ("sh", "上证指数", market.get("sh", {}).get("pe")),
                               ("hs300", "沪深300", market.get("hs300", {}).get("pe"))):
            if pe:
                g = round((1 / pe) / bv, 2)
                band = "市场估值极低" if g > 2.3 else ("市场估值偏低" if g >= 2 else
                       ("市场估值略偏低" if g >= 1.8 else ("市场估值中性" if g >= 1.5 else
                       ("市场估值偏高" if g >= 1 else "市场估值极高"))))
                metrics.append({
                    "key": key, "label": label, "pe": pe, "graham": g, "band": band,
                    "formula": "(1 / market_PE) / China_10Y_yield",
                    "thresholds": ">2.3 / 2.0 / 1.8 / 1.5 / 1.0",
                    "role": "market_context_only",
                    "not_position_instruction": True,
                })
    market["graham_metrics"] = metrics
    market["graham_role"] = "market_context_only"
    market["not_position_instruction"] = True
    market["collected_at"] = now()
    market["data_date"] = args.as_of or (cs or {}).get("date") or market.get("data_date", today)

    # ---- 个股 ----
    codes = list(stocks_cfg.keys())
    spot, spot_meta = fetch_spot(codes)
    out_stocks = {}
    for code, cfg in stocks_cfg.items():
        m = {}
        if spot and code in spot:
            m.update({"price": spot[code]["price"], "pct": spot[code]["pct"],
                      "pe_ttm": spot[code]["pe_ttm"], "pb": spot[code]["pb"],
                      "total_mv": spot[code]["total_mv"],
                      "shares": spot[code]["shares"]})
            m["spot_meta"] = dict(spot_meta or {})
        else:
            pv = prev_map.get(code) or {}
            m.update({"price": pv.get("price"), "pct": pv.get("pct", 0.0),
                      "pe_ttm": pv.get("pe_ttm"), "pb": pv.get("pb"),
                      "total_mv": pv.get("total_mv"), "spot_stale": True,
                      "spot_meta": {**dict(spot_meta or {}), "retained_previous": True}})

        kline, kline_meta = fetch_kline(code)
        if args.as_of and kline:
            filtered = [r for r in kline if str(r["d"]) <= args.as_of]
            if filtered:
                kline = filtered
                kline_meta = {**dict(kline_meta or {}), "as_of": args.as_of}
            else:
                kline, kline_meta = None, {**dict(kline_meta or {}),
                                           "as_of": args.as_of, "as_of_empty": True}
        if kline:
            m["kline"] = kline
            m["kline_meta"] = dict(kline_meta or {})
            # 现价统一以K线最新收盘为准（前复权最新一根收盘价==实际收盘价），
            # 保证 Hero/区间判定/买卖阶梯/K线 同源一致；无K线时才用行情价
            m["price"] = float(kline[-1]["c"])
            if args.as_of and len(kline) >= 2:
                m["pct"] = round((float(kline[-1]["c"]) / float(kline[-2]["c"]) - 1) * 100, 2)
        else:
            pv = prev_map.get(code) or {}
            m["kline"] = pv.get("kline", [])
            m["kline_stale"] = True
            m["kline_meta"] = {**dict(kline_meta or {}), "retained_previous": True}

        # 盈利一致预期每日抓取。失败时可保留旧的结构化数据供审阅，但 meta.stale
        # 会让引擎降为 reference_only；绝不使用 price/PE 生成替代 EPS。
        vm = cfg.get("valuation_model") or {}
        vm_code = vm.get("code") if isinstance(vm, dict) else vm
        if (cfg.get("route") in ("etf", "loss")
                or vm_code in ("normalized_pe", "bank_pb_roe", "infrastructure_cashflow")):
            forecast_data = None
            forecast_meta = {
                "source": "ths-worth", "status": "not_applicable", "stale": False,
                "collected_at": now(), "reason": f"route={cfg.get('route') or vm_code}",
            }
        else:
            forecast_data, forecast_meta = fetch_ths_worth_forecast(code)
            if forecast_data is None:
                previous_forecast = (prev_map.get(code) or {}).get("forecast_data")
                if previous_forecast:
                    forecast_data = previous_forecast
                    forecast_meta = {
                        **dict(forecast_meta or {}),
                        "stale": True,
                        "retained_previous": True,
                        "previous_as_of": previous_forecast.get("as_of"),
                        "previous_retrieved_at": previous_forecast.get("retrieved_at"),
                    }

        cfg2 = dict(cfg)
        cfg2["market"] = m
        res = compute_stock(cfg2, prev_map.get(code), forecast_data, forecast_meta, as_of)
        if res:
            out_stocks[code] = res

    # ---- 写快照 + state ----
    snap_name = f"{today}_asof{args.as_of}.json" if args.as_of else f"{today}.json"
    snap = {
        "date": today, "as_of": args.as_of, "market": market, "stocks": out_stocks,
        "spot_meta": spot_meta, "generated_at": now(),
    }
    with open(os.path.join(SNAP_DIR, snap_name), "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=2)

    state = {"meta": {"updated_at": now(), "last_data_date": market["data_date"],
                      "as_of": args.as_of},
             "market": market, "stocks": out_stocks}
    save_state(state)
    log(f"快照 {snap_name} 已写；{len(out_stocks)} 只股票计算完成")

    # ---- PE/PB 历史分位（每天收盘后重新爬取更新）----
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from fetch_pe_history import main as pe_history_main
        pe_history_main()
        log("PE/PB 历史分位更新完成（百度股市通5年历史）")
    except Exception as e:
        log(f"PE/PB 历史分位更新失败: {e}")

    # ---- 重建门户 ----
    try:
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        r = subprocess.run([sys.executable, BUILD], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env, timeout=600)
        tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        log("门户重建: " + tail)
        if r.returncode != 0:
            log("门户重建失败: " + (r.stderr or "")[-500:])
    except Exception as e:
        log(f"门户重建异常: {e}")

    # ---- 发布到永久公开网址（GitHub Pages，失败不影响本地门户）----
    try:
        deploy = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deploy_portal.py")
        r = subprocess.run([sys.executable, deploy], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=420)
        if r.returncode == 0:
            url = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
            log("公开网址发布: " + (url or "完成"))
        else:
            log("公开网址发布失败: " + ((r.stdout or r.stderr or "").strip())[-300:])
    except Exception as e:
        log(f"公开网址发布异常: {e}")

    # ---- 摘要 ----
    zones = {}
    for s in out_stocks.values():
        zones[s["zone"]] = zones.get(s["zone"], 0) + 1
    sig = [f"{s['ticker']} {s['name']}: {'; '.join(s['signals'])}"
           for s in out_stocks.values() if s["signals"]]
    log("区间分布: " + json.dumps(zones, ensure_ascii=False))
    for s_ in sig:
        log("信号: " + s_)
    log("=== 每日更新结束 ===")


if __name__ == "__main__":
    main()
