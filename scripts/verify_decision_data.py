# -*- coding: utf-8 -*-
"""离线验证决策数据 v2 的关键安全性质。

默认只跑内置夹具与静态守卫，不依赖网络，也不改业务 JSON。

可选：
  python verify_decision_data.py --live 002340
  python verify_decision_data.py --state E:\\财报解读\\watchlist\\state.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

from data_fetch import fetch_ths_worth_forecast, parse_ths_worth_html
from update_daily import compute_stock
from valuation_engine_v2 import ENGINE_VERSION, SCHEMA_VERSION, evaluate_stock, resolve_model


HERE = os.path.dirname(os.path.abspath(__file__))


class Audit:
    def __init__(self):
        self.passed = 0
        self.failed = []

    def check(self, condition, label, detail=""):
        if condition:
            self.passed += 1
        else:
            self.failed.append({"check": label, "detail": detail})


def fixture_forecast():
    page = """
    <html><head><title>测试公司(000001) 盈利预测_F10_同花顺金融服务网</title></head><body>
    <div id="forecast">
      <p class="tip">截至2026-08-08，6个月以内共有 <strong>3</strong> 家机构预测。</p>
      <div id="yjycData">[["2024","0.20","10.00","SJ"],["2025","0.31","15.80","SJ"],["2026","0.43","21.89","YC"],["2027","0.58","29.65","YC"]]</div>
      <table><caption><span>单位：元</span>汇总--预测年报每股收益</caption>
        <thead><tr><th>年度</th><th>预测机构数</th><th>最小值</th><th>均值</th><th>最大值</th><th>行业平均数</th></tr></thead>
        <tbody>
          <tr><td>2026</td><td>3</td><td>0.38</td><td>0.43</td><td>0.45</td><td>2.18</td></tr>
          <tr><td>2027</td><td>3</td><td>0.52</td><td>0.58</td><td>0.69</td><td>3.06</td></tr>
        </tbody>
      </table>
      <table><caption>汇总--预测年报净利润</caption></table>
    </div>
    <div id="forecastdetail"></div>
    </body></html>
    """
    return parse_ths_worth_html(
        page, "000001", "https://basic.10jqka.com.cn/000001/worth.html",
        "2026-08-09 10:00:00",
    )


def base_config():
    return {
        "ticker": "000001",
        "name": "测试公司",
        "route": "equity",
        "valuation_model": {
            "code": "forward_pe", "label": "稳定盈利·前瞻PE",
            "reason": "离线测试", "rule_version": ENGINE_VERSION,
        },
        "last_actual_fy": 2025,
        "forecast_policy": {"basis": "FY1"},
        "pe_low": 15.0, "pe_mid": 18.0, "pe_high": 24.0,
        "multiple_source": {
            "id": "fixture-multiple",
            "method": "historical_quantile",
            "title": "五年前瞻PE分位",
            "as_of": "2026-08-08",
            "url": "https://example.invalid/multiple-evidence",
            "quality": "B",
        },
        "needs_review": False,
    }


def run_offline(audit: Audit):
    payload = fixture_forecast()
    meta = {"source": "ths-worth", "status": "ok", "stale": False}
    audit.check(payload["as_of"] == "2026-08-08", "parser.as_of")
    audit.check(len(payload["forecasts"]) == 2, "parser.forecast_rows")
    audit.check(payload["forecasts"][0] == {
        "year": 2026, "count": 3, "min": 0.38, "mean": 0.43, "max": 0.45,
        "industry_mean": 2.18, "metric": "diluted_eps", "unit": "CNY/share",
    }, "parser.forecast_fields", repr(payload["forecasts"][0]))
    audit.check(payload["actual_eps_history"][-1]["year"] == 2025,
                "parser.actual_eps_history")

    cfg = base_config()
    result = evaluate_stock(cfg, {"price": 6.0}, payload, meta, "2026-08-09")
    audit.check(result["schema_version"] == SCHEMA_VERSION, "engine.schema_version")
    audit.check(result["decision_status"] == "ready" and result["decision_usable"],
                "engine.ready")
    # v2.1 方法论：forward_pe 稳定路由默认行业折扣 ×0.95 → EPS 0.38/0.43/0.45 → 0.361/0.4085/0.4275
    audit.check(result["valuation"]["v_low"] == 5.42 and
                result["valuation"]["v_mid"] == 7.35 and
                result["valuation"]["v_high"] == 10.26,
                "engine.transparent_values_haircut", repr(result["valuation"]))
    audit.check(len(result["valuation"]["calc_steps"]) == 3 and
                result["valuation"]["calc_steps"][1]["substitution"] == "0.4085 × 18",
                "engine.calc_steps_haircut", repr(result["valuation"]["calc_steps"]))
    audit.check(result["forecast"]["base"] == 0.43 and
                result["earnings_adjustment"]["raw_eps"]["base"] == 0.43 and
                result["earnings_adjustment"]["adjusted_eps"]["base"] == 0.4085,
                "engine.haircut_raw_preserved_audit")
    audit.check(any(x["id"] == "EARNINGS_CONSENSUS_HAIRCUT"
                    for x in result["quality"]["checks"]),
                "engine.haircut_info_check")

    cfg_string = base_config()
    cfg_string["valuation_model"] = "growth_pe"
    audit.check(resolve_model(cfg_string)["code"] == "growth_pe", "model.string_compat")
    audit.check(resolve_model(base_config())["code"] == "forward_pe", "model.object_compat")

    manual_cfg = base_config()
    manual_cfg["multiple_source"] = {
        "method": "manual_policy_assumption", "title": "政策假设",
        "as_of": "2026-08-08", "url": "https://example.invalid/manual", "quality": "D",
    }
    manual = evaluate_stock(manual_cfg, {"price": 6.0}, payload, meta, "2026-08-09")
    audit.check(manual["decision_status"] == "reference_only" and
                not manual["decision_usable"] and manual["reference_usable"],
                "engine.manual_multiple_never_ready")
    audit.check(any(x["code"] == "MULTIPLE_NOT_MANUAL_LOW_QUALITY"
                    for x in manual["quality"]["warnings"]),
                "engine.manual_multiple_warning")
    flat_cfg = dict(manual_cfg)
    flat_cfg["market"] = {
        "price": 6.0, "pct": 5.0, "kline": [{"c": 6.0}] * 260,
        "spot_meta": {"source": "fixture"}, "kline_meta": {"source": "fixture"},
    }
    flat = compute_stock(flat_cfg, {}, payload, meta, "2026-08-09")
    audit.check(flat["zone"] == "参考区间" and flat["mos"] is None and
                flat["pctile"] is None and flat["band_pos_raw"] is None and
                flat["action"] is None and not flat["signals"],
                "daily.reference_hides_action_mos_and_signals")

    # 估值带位置必须保留 <0 或 >1 原值（数据契约：不用 clamp 隐藏越界程度）
    hot = evaluate_stock(cfg, {"price": 30.0}, payload, meta, "2026-08-09")
    audit.check(hot["decision_usable"] and
                hot["decision"]["band_position_raw"] > 1.0 and
                0.0 <= hot["decision"]["band_position"] <= 1.0,
                "engine.band_position_raw_unclamped")
    cold = evaluate_stock(cfg, {"price": 2.0}, payload, meta, "2026-08-09")
    audit.check(cold["decision_usable"] and
                cold["decision"]["band_position_raw"] < 0.0,
                "engine.band_position_raw_negative")

    # ---- 方法论升级 v2.1：覆盖门槛 / 三尺互证 / 分歧降级 / 反向验证 ----
    thin_payload = {
        "provider": "同花顺F10", "url": "https://example.invalid/worth",
        "as_of": "2026-08-08", "retrieved_at": "2026-08-09 10:00:00",
        "forecasts": [{"year": 2026, "count": 1, "min": 0.40, "mean": 0.43, "max": 0.45}],
        "actual_eps_history": [{"year": 2025, "eps": 0.31}],
    }
    thin = evaluate_stock(base_config(), {"price": 6.0}, thin_payload, meta, "2026-08-09")
    audit.check(thin["decision_status"] == "blocked" and
                any(x["code"] == "FORECAST_COVERAGE_MIN" for x in thin["quality"]["blockers"]),
                "v21.coverage_min_blocks_decision", repr(thin["quality"]["blockers"]))

    tri_cfg = base_config()
    tri_cfg["dividend_payout_ratio"] = 0.60
    tri_cfg["peer_industry_pe"] = 12.0
    tri = evaluate_stock(tri_cfg, {"price": 6.0}, payload, meta, "2026-08-09")
    fus = tri.get("multiple_fusion") or {}
    audit.check(fus.get("n_rulers") == 3 and fus.get("quality") == "B" and
                not fus.get("divergent"),
                "v21.tri_ruler_fused_quality_b", repr(fus))
    audit.check(fus.get("effective", {}).get("mid") == 12.0,
                "v21.fusion_median_mid", repr(fus.get("effective")))
    audit.check(tri["multiple"]["low"] == 10.5 and tri["multiple"]["high"] == 16.0 and
                tri["multiple"]["source"]["method"] == "tri_ruler_consensus",
                "v21.fusion_band_guardrails", repr(tri["multiple"]))
    audit.check(tri["multiple"]["source"]["provenance"].get("method") == "historical_quantile",
                "v21.history_provenance_kept")
    audit.check(tri["decision_usable"] and abs(tri["valuation"]["v_mid"] - 4.9) < 0.01,
                "v21.fused_valuation_ready", repr(tri["valuation"]))
    ruler_mids = [r["mid"] for r in fus.get("rulers", [])]
    audit.check(len(ruler_mids) == 3 and abs(ruler_mids[1] - 11.1818) < 0.001,
                "v21.formula_ruler_value", repr(ruler_mids))

    div_cfg = base_config()
    div_cfg["dividend_payout_ratio"] = 0.60
    div_cfg["peer_industry_pe"] = 45.0
    div = evaluate_stock(div_cfg, {"price": 6.0}, payload, meta, "2026-08-09")
    audit.check(any(w["code"] == "MULTIPLE_SOURCE_DIVERGENCE"
                    for w in div["quality"]["warnings"]) and
                div["decision_status"] == "reference_only" and
                not div["decision_usable"],
                "v21.divergence_forces_reference_only", repr(div["quality"]["warnings"]))
    audit.check(abs(div["valuation"]["v_mid"] - 7.35) < 0.01,
                "v21.divergence_median_still_hist", repr(div["valuation"]))

    payload_g0 = {
        "provider": "同花顺F10", "url": "https://example.invalid/worth",
        "as_of": "2026-08-08", "retrieved_at": "2026-08-09 10:00:00",
        "forecasts": [{"year": 2026, "count": 6, "min": 0.38, "mean": 0.43, "max": 0.45}],
        "actual_eps_history": [{"year": 2024, "eps": 0.30}, {"year": 2025, "eps": 0.43}],
    }
    rev_cfg = base_config()
    rev_cfg["dividend_payout_ratio"] = 0.60
    rev = evaluate_stock(rev_cfg, {"price": 50.0, "pe_ttm": 80.0},
                         payload_g0, meta, "2026-08-09")
    rv = rev.get("reverse_valuation") or {}
    audit.check(rv.get("overheated") is True and abs(rv.get("g_implied", 0) - 0.072) < 0.002 and
                rv.get("g_expected_consensus") == 0.0,
                "v21.reverse_valuation_overheated", repr(rv))
    audit.check(any(w["code"] == "PRICE_EMBEDS_EXCESS_OPTIMISM"
                    for w in rev["quality"]["warnings"]) and
                rev["decision_status"] == "reference_only",
                "v21.reverse_warn_downgrades_only", repr(rev["quality"]["warnings"]))

    from valuation_methodology import justified_pe, implied_growth_from_pe, fuse_multiples
    audit.check(justified_pe(0.60, 0.14, 0.15) is None, "v21.justified_pe_r_minus_g_guard")
    audit.check(justified_pe(0.60, 0.05, 0.11) == 10.5, "v21.justified_pe_normal_case")
    audit.check(abs(implied_growth_from_pe(20.0, 0.50, 0.08) - 0.053659) < 0.0001,
                "v21.implied_growth_inversion")
    band_none, reason = fuse_multiples({"low": 15, "mid": 18, "high": 24}, [],
                                       dt.date(2026, 8, 9))
    audit.check(band_none is None and "insufficient" in reason, "v21.fusion_needs_two_rulers")

    missing = evaluate_stock(base_config(), {"price": 6.0}, None,
                             {"status": "error", "stale": True, "error": "fixture"},
                             "2026-08-09")
    audit.check(missing["decision_status"] == "blocked" and
                missing["valuation"]["v_mid"] is None and
                missing["decision"]["action"] is None,
                "engine.missing_forecast_fail_closed")

    mismatch_cfg = base_config()
    mismatch_cfg["valuation_model"] = {"code": "normalized_pe"}
    mismatch = evaluate_stock(mismatch_cfg, {"price": 6.0}, payload, meta, "2026-08-09")
    audit.check(mismatch["decision_status"] == "blocked" and
                mismatch["valuation"]["v_mid"] is None and
                mismatch["decision"]["action"] is None,
                "engine.model_mismatch_fail_closed")

    fy2_cfg = base_config()
    fy2_cfg["forecast_policy"] = {"basis": "FY1", "year": 2027}
    fy2 = evaluate_stock(fy2_cfg, {"price": 6.0}, payload, meta, "2026-08-09")
    audit.check(fy2["decision_status"] == "blocked" and
                any(x["code"] == "FORECAST_YEAR_IS_FY1" for x in fy2["quality"]["blockers"]),
                "engine.fy2_cannot_pose_as_fy1")

    ntm_cfg = base_config()
    ntm_cfg["forecast_policy"] = {"basis": "NTM"}
    ntm = evaluate_stock(ntm_cfg, {"price": 6.0}, payload, meta, "2026-08-09")
    audit.check(ntm["forecast"]["basis"] == "NTM" and
                set(ntm["forecast"]["weights"]) == {"2026", "2027"} and
                "NTM EPS" in ntm["forecast"]["formula"],
                "engine.ntm_is_explicit")

    norm_cfg = base_config()
    norm_cfg["valuation_model"] = {"code": "normalized_pe"}
    norm_cfg["normalized"] = {
        "eps_bear": 0.7875, "eps_base": 1.483, "eps_bull": 1.7501,
        "roe_low": 11.38, "roe_mid": 21.43, "roe_high": 25.29,
        "bps": 6.92, "bps_as_of": "2025-12-31", "hist_n": 10, "window": "2016-2025",
        "source": {
            "id": "fixture-norm", "type": "normalized_earnings",
            "provider": "同花顺F10财务摘要", "title": "fixture",
            "url": "https://example.invalid/norm", "as_of": "2026-08-12",
            "retrieved_at": "2026-08-13 10:00:00",
        },
    }
    norm = evaluate_stock(norm_cfg, {"price": 30.0}, None,
                          {"status": "not_applicable"}, "2026-08-12")
    audit.check(norm["decision_status"] == "reference_only" and norm["reference_usable"] and
                not norm["decision_usable"] and norm["decision"]["action"] is None,
                "engine.normalized_always_reference")
    audit.check(abs(norm["valuation"]["v_mid"] - 1.483 * 18.0) < 0.01,
                "engine.normalized_values", repr(norm["valuation"]))
    audit.check(norm["forecast"]["basis"] == "NORMALIZED",
                "engine.normalized_forecast_basis")

    short_cfg = base_config()
    short_cfg["valuation_model"] = {"code": "normalized_pe"}
    short_cfg["normalized"] = {**norm_cfg["normalized"], "hist_n": 5}
    short = evaluate_stock(short_cfg, {"price": 30.0}, None,
                           {"status": "not_applicable"}, "2026-08-12")
    audit.check(short["decision_status"] == "blocked" and
                short["valuation"]["v_mid"] is None,
                "engine.normalized_short_history_fail_closed")

    bank_cfg = base_config()
    bank_cfg["valuation_model"] = {"code": "bank_pb_roe"}
    bank_cfg["multiple"] = {"low": 0.4, "mid": 0.42, "high": 0.47,
                            "source": dict(base_config()["multiple_source"])}
    bank_cfg["bank"] = {
        "bps": 8.46, "bps_as_of": "2025-12-31",
        "roe_hist": [17.36, 15.5, 13.8, 12.75, 11.55, 11.77, 10.71, 10.64, 10.27, 8.38, 7.93, 7.0],
        "npl": 1.32, "npl_as_of": "2026-03-31", "provision": 2.22, "car": 12.77,
        "ke": 0.10, "g": 0.03,
        "source": {"id": "fixture-bank", "type": "special_route_financials",
                   "provider": "同花顺F10财务摘要", "title": "t",
                   "url": "https://example.invalid/bank", "as_of": "2026-08-12",
                   "retrieved_at": "2026-08-13 10:00:00"},
    }
    bank = evaluate_stock(bank_cfg, {"price": 3.0}, None,
                          {"status": "not_applicable"}, "2026-08-12")
    audit.check(bank["decision_status"] == "reference_only" and not bank["decision_usable"],
                "engine.bank_always_reference")
    audit.check(abs(bank["valuation"]["v_mid"] - 8.46 * 0.42) < 0.01,
                "engine.bank_values", repr(bank["valuation"]))
    audit.check(bank["diagnostics"]["pb_theo_mid"] > 0, "engine.bank_pb_roe_diag")
    audit.check(any(w["code"] == "BANK_ROE_DECLINE" for w in bank["quality"]["warnings"]),
                "engine.bank_roe_decline_warning")

    infra_cfg = base_config()
    infra_cfg["valuation_model"] = {"code": "infrastructure_cashflow"}
    infra_cfg["multiple"] = {"low": 0.41, "mid": 0.46, "high": 0.51,
                             "source": dict(base_config()["multiple_source"])}
    infra_cfg["infra"] = {
        "bps": 20.19, "bps_as_of": "2025-12-31", "ocf_latest": 0.22,
        "ocf_hist": [0.53, 3.71, 2.73, 1.87, 0.4, 2.95, 2.95, -0.54, 4.13, 1.5, -2.31, 0.22],
        "ar_days_latest": 77.92,
        "ar_days_hist": [61.79, 72.97, 74.78, 73.99, 60.62, 45.85, 47.03, 49.65, 48.75, 46.98, 60.82, 77.92],
        "debt_latest": 79.51, "debt_hist": [83.32, 81.49, 80.42, 78.26, 77.41, 75.77, 74.76, 74.39, 74.67, 74.92, 77.31, 79.51],
        "source": {"id": "fixture-infra", "type": "special_route_financials",
                   "provider": "同花顺F10财务摘要", "title": "t",
                   "url": "https://example.invalid/infra", "as_of": "2026-08-12",
                   "retrieved_at": "2026-08-13 10:00:00"},
    }
    infra = evaluate_stock(infra_cfg, {"price": 6.0}, None,
                           {"status": "not_applicable"}, "2026-08-12")
    audit.check(infra["decision_status"] == "reference_only" and not infra["decision_usable"],
                "engine.infra_always_reference")
    audit.check(abs(infra["valuation"]["v_mid"] - 20.19 * 0.46) < 0.01,
                "engine.infra_values", repr(infra["valuation"]))
    audit.check(any(w["code"] == "INFRA_AR_RISING" for w in infra["quality"]["warnings"]),
                "engine.infra_ar_warning")

    bank_missing = base_config()
    bank_missing["valuation_model"] = {"code": "bank_pb_roe"}
    no_bank = evaluate_stock(bank_missing, {"price": 3.0}, None,
                             {"status": "not_applicable"}, "2026-08-12")
    audit.check(no_bank["decision_status"] == "blocked" and
                no_bank["valuation"]["v_mid"] is None,
                "engine.bank_missing_data_fail_closed")

    bootstrap_path = os.path.join(HERE, "bootstrap_watchlist.py")
    data_fetch_path = os.path.join(HERE, "data_fetch.py")
    update_path = os.path.join(HERE, "update_daily.py")
    bootstrap_text = open(bootstrap_path, encoding="utf-8").read()
    fetch_text = open(data_fetch_path, encoding="utf-8").read()
    update_text = open(update_path, encoding="utf-8").read()
    forbidden = ("s[\"price\"] / pe_ttm", "price / pe_ttm", "price/pe_ttm")
    audit.check(not any(x in bootstrap_text for x in forbidden),
                "static.no_price_pe_forecast_fallback")
    audit.check("stock_profit_forecast_em" not in fetch_text,
                "static.no_wrong_akshare_forecast_api")
    audit.check("evaluate_stock" in update_text and "fetch_ths_worth_forecast" in update_text,
                "static.daily_uses_v2_engine_and_ths")
    audit.check('"graham_role"] = "market_context_only"' in update_text and
                '"not_position_instruction"] = True' in update_text,
                "static.graham_is_context_not_position")


def verify_state(path: str, audit: Audit):
    with open(path, encoding="utf-8") as f:
        state = json.load(f)
    stocks = list((state.get("stocks") or {}).values())
    audit.check(bool(stocks), "state.has_stocks")
    for stock in stocks:
        prefix = f"state.{stock.get('ticker')}"
        audit.check(stock.get("decision_status") in {"ready", "reference_only", "blocked", "observe"},
                    prefix + ".decision_status")
        audit.check(isinstance(stock.get("decision_usable"), bool),
                    prefix + ".decision_usable")
        if not stock.get("decision_usable"):
            audit.check(stock.get("action") in (None, ""), prefix + ".no_blocked_action")
            audit.check(not stock.get("signals"), prefix + ".no_blocked_signals")
        audit.check(stock.get("pe_source") is not None or
                    (stock.get("valuation_model") or {}).get("code") in {
                        "observe", "etf_index", "bank_pb_roe", "insurance_pev",
                        "normalized_pe", "infrastructure_cashflow",
                    }, prefix + ".pe_source_passthrough")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", metavar="TICKER", help="额外联网验证一只同花顺 worth 页面")
    ap.add_argument("--state", help="额外验证已由 v2 流水线生成的 state.json")
    args = ap.parse_args()

    audit = Audit()
    run_offline(audit)
    if args.live:
        data, meta = fetch_ths_worth_forecast(args.live)
        audit.check(data is not None and meta.get("status") in {"ok", "no_consensus"},
                    "live.fetch", json.dumps(meta, ensure_ascii=False))
        if data is not None:
            audit.check(data.get("symbol") == args.live and isinstance(data.get("forecasts"), list),
                        "live.schema")
    if args.state:
        verify_state(args.state, audit)

    print(json.dumps({
        "schema_version": SCHEMA_VERSION,
        "engine_version": ENGINE_VERSION,
        "passed": audit.passed,
        "failed": audit.failed,
    }, ensure_ascii=False, indent=2))
    if audit.failed:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
