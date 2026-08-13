# -*- coding: utf-8 -*-
"""可审计、失败关闭的估值引擎 v2。

本模块只把有明确模型路由、明确预测年度、结构化预测来源和结构化倍数来源的
输入变成估值结果。它不抓数据、不猜缺失值，也绝不使用 ``price / PE`` 反推
未来 EPS。

当前已实现：``forward_pe``、``growth_pe``（decision 级）、``insurance_pev``、
``normalized_pe``（后者恒为 reference 级，周期股盈利预测质量 L/M）。
其余模型路由在专用输入和公式落地前返回 ``blocked`` 或 ``observe``，不会偷用
PE 公式替代。
"""
from __future__ import annotations

import calendar
import datetime as dt
import math
from typing import Any


SCHEMA_VERSION = "decision-data-v2"
ENGINE_VERSION = "2026.08-v2"

MODEL_LABELS = {
    "forward_pe": "稳定盈利·前瞻 PE",
    "growth_pe": "成长股·前瞻 PE",
    "normalized_pe": "强周期·正常化盈利",
    "bank_pb_roe": "银行·PB-ROE",
    "insurance_pev": "保险·P/EV",
    "infrastructure_cashflow": "基建·现金流/资产负债表",
    "etf_index": "ETF·指数估值分位",
    "observe": "观察路由",
    "unknown": "未声明模型",
}

IMPLEMENTED_PE_ROUTES = {"forward_pe", "growth_pe"}
IMPLEMENTED_INSURANCE_ROUTES = {"insurance_pev"}
IMPLEMENTED_NORMALIZED_ROUTES = {"normalized_pe"}
IMPLEMENTED_SPECIAL_ROUTES = {"bank_pb_roe", "infrastructure_cashflow"}
UNIMPLEMENTED_ROUTES = {
    "etf_index": "缺少对应指数估值历史、当前分位与跟踪误差输入",
}


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _iso_date(value: Any) -> dt.date | None:
    if not value:
        return None
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def resolve_model(config: dict) -> dict:
    """兼容 ``valuation_model`` 为对象或字符串，优先对象的 ``code``。"""
    raw = config.get("valuation_model")
    if isinstance(raw, dict):
        model = dict(raw)
        code = str(model.get("code") or "unknown").strip()
    elif isinstance(raw, str) and raw.strip():
        code = raw.strip()
        model = {"code": code}
    elif config.get("route") == "loss":
        code, model = "observe", {"code": "observe"}
    elif config.get("route") == "etf":
        code, model = "etf_index", {"code": "etf_index"}
    else:
        code, model = "unknown", {"code": "unknown"}
    model["code"] = code
    model.setdefault("label", MODEL_LABELS.get(code, code))
    model.setdefault("reason", "配置未提供模型选择理由")
    model.setdefault("rule_version", ENGINE_VERSION)
    model["implemented"] = (code in IMPLEMENTED_PE_ROUTES or
                            code in IMPLEMENTED_INSURANCE_ROUTES or
                            code in IMPLEMENTED_NORMALIZED_ROUTES or
                            code in IMPLEMENTED_SPECIAL_ROUTES)
    return model


def _base_result(config: dict) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "engine_version": ENGINE_VERSION,
        "ticker": config.get("ticker"),
        "model": resolve_model(config),
        "decision_status": "blocked",
        "decision_usable": False,
        "reference_usable": False,
        "quality": {"grade": "D", "checks": [], "warnings": [], "blockers": []},
        "forecast": None,
        "multiple": None,
        "valuation": {
            "v_low": None, "v_mid": None, "v_high": None,
            "formula": None, "calc_steps": [],
        },
        "decision": {
            "zone": None, "action": None, "reference_zone": None,
            "margin_of_safety": None, "band_position": None,
        },
        "sources": [],
    }


def _add_check(result: dict, check_id: str, passed: bool, severity: str, detail: str):
    result["quality"]["checks"].append({
        "id": check_id, "passed": bool(passed), "severity": severity, "detail": detail,
    })
    if not passed:
        if severity == "block":
            result["quality"]["blockers"].append({"code": check_id, "detail": detail})
        elif severity == "warn":
            result["quality"]["warnings"].append({"code": check_id, "detail": detail})
        # info 级仅记录在 checks 供展示（认知补偿提示），不参与决策降级


def _forecast_rows(payload: dict | None) -> list[dict]:
    rows = []
    for raw in (payload or {}).get("forecasts") or []:
        try:
            row = {
                "year": int(raw["year"]),
                "count": int(raw["count"]),
                "min": float(raw["min"]),
                "mean": float(raw["mean"]),
                "max": float(raw["max"]),
                "industry_mean": raw.get("industry_mean"),
                "metric": raw.get("metric", "diluted_eps"),
                "unit": raw.get("unit", "CNY/share"),
            }
        except (KeyError, TypeError, ValueError):
            continue
        rows.append(row)
    return sorted(rows, key=lambda x: x["year"])


def _actual_history(payload: dict | None) -> list[dict]:
    out = []
    for raw in (payload or {}).get("actual_eps_history") or []:
        try:
            out.append({"year": int(raw["year"]), "eps": float(raw["eps"])})
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(out, key=lambda x: x["year"])


def _forecast_policy(config: dict) -> dict:
    policy = config.get("forecast_policy")
    policy = dict(policy) if isinstance(policy, dict) else {}
    basis = str(policy.get("basis") or config.get("forecast_basis") or "FY1").upper()
    policy["basis"] = basis
    if policy.get("year") is None and config.get("forecast_year") is not None:
        policy["year"] = config.get("forecast_year")
    return policy


def _select_forecast(config: dict, payload: dict | None, as_of: dt.date,
                     result: dict) -> dict | None:
    rows = _forecast_rows(payload)
    history = _actual_history(payload)
    _add_check(result, "FORECAST_ROWS_PRESENT", bool(rows), "block",
               "同花顺页面必须包含结构化年度 EPS 预测行")
    _add_check(result, "ACTUAL_EPS_HISTORY_PRESENT", bool(history), "block",
               "必须有实际 EPS 历史，才能明确定义 FY1/T+1")
    if not rows or not history:
        return None

    last_actual_fy = max(x["year"] for x in history)
    configured_actual = config.get("last_actual_fy")
    if configured_actual is not None:
        try:
            configured_actual = int(configured_actual)
        except (TypeError, ValueError):
            configured_actual = None
        _add_check(result, "LAST_ACTUAL_FY_MATCH", configured_actual == last_actual_fy, "block",
                   f"配置 last_actual_fy={configured_actual}，来源历史最新实际年={last_actual_fy}")

    policy = _forecast_policy(config)
    basis = policy["basis"]
    by_year = {x["year"]: x for x in rows}
    if basis == "NTM":
        current_year, next_year = as_of.year, as_of.year + 1
        current, nxt = by_year.get(current_year), by_year.get(next_year)
        _add_check(result, "NTM_EXPLICIT", True, "info", "配置显式选择 NTM，不会伪装成单一财年")
        _add_check(result, "NTM_TWO_YEARS_PRESENT", bool(current and nxt), "block",
                   f"NTM 需要 {current_year}E 与 {next_year}E 两个年度预测")
        if not current or not nxt:
            return None
        year_days = 366 if calendar.isleap(current_year) else 365
        next_year_start = dt.date(next_year, 1, 1)
        current_weight = max(0.0, min(1.0, (next_year_start - as_of).days / year_days))
        next_weight = 1.0 - current_weight
        selected = {
            "basis": "NTM",
            "label": f"NTM@{as_of.isoformat()}",
            "year": None,
            "years": [current_year, next_year],
            "horizon": "NTM",
            "last_actual_fy": last_actual_fy,
            "count": min(current["count"], nxt["count"]),
            "bear": current["min"] * current_weight + nxt["min"] * next_weight,
            "base": current["mean"] * current_weight + nxt["mean"] * next_weight,
            "bull": current["max"] * current_weight + nxt["max"] * next_weight,
            "weights": {str(current_year): round(current_weight, 6),
                        str(next_year): round(next_weight, 6)},
            "formula": (
                f"NTM EPS = {current_year}E EPS × {current_weight:.6f} + "
                f"{next_year}E EPS × {next_weight:.6f}"
            ),
            "raw_rows": [current, nxt],
        }
    elif basis == "FY1":
        fy1 = last_actual_fy + 1
        requested = policy.get("year", fy1)
        try:
            requested = int(requested)
        except (TypeError, ValueError):
            requested = -1
        _add_check(result, "FORECAST_YEAR_IS_FY1", requested == fy1, "block",
                   f"主估值年度必须是 FY1={fy1}，当前请求={requested}")
        row = by_year.get(requested)
        _add_check(result, "FY1_ROW_PRESENT", row is not None, "block",
                   f"来源必须包含 {requested}E 结构化预测")
        if requested != fy1 or row is None:
            return None
        selected = {
            "basis": "FY1",
            "label": f"{requested}E/FY1",
            "year": requested,
            "years": [requested],
            "horizon": 1,
            "last_actual_fy": last_actual_fy,
            "count": row["count"],
            "bear": row["min"], "base": row["mean"], "bull": row["max"],
            "weights": {str(requested): 1.0},
            "formula": f"FY1 EPS 使用同花顺 {requested}E 机构预测最小值/均值/最大值",
            "raw_rows": [row],
        }
    else:
        _add_check(result, "FORECAST_BASIS_SUPPORTED", False, "block",
                   f"仅支持显式 FY1 或 NTM，收到 {basis!r}")
        return None

    ordered = all(_finite_number(selected[k]) for k in ("bear", "base", "bull")) and \
        0 < selected["bear"] <= selected["base"] <= selected["bull"]
    _add_check(result, "FORECAST_VALUES_POSITIVE_ORDERED", ordered, "block",
               "EPS 必须为正，且 min ≤ mean ≤ max；亏损/反转股不得套用 PE")
    _add_check(result, "FORECAST_SAMPLE_COUNT", selected["count"] >= 3, "warn",
               f"有效预测机构数={selected['count']}；少于 3 家信号偏弱")
    _add_check(result, "FORECAST_COVERAGE_SUFFICIENT", selected["count"] >= 5, "info",
               f"机构覆盖={selected['count']} 家；少于 5 家时结论可信度下降，建议人工核对同花顺F10是否遗漏机构")
    return selected if ordered else None


def _multiple_inputs(config: dict, result: dict) -> dict | None:
    block = config.get("multiple")
    block = dict(block) if isinstance(block, dict) else {}
    values = {
        "low": block.get("low", config.get("pe_low")),
        "mid": block.get("mid", config.get("pe_mid")),
        "high": block.get("high", config.get("pe_high")),
    }
    numeric = all(_finite_number(v) and float(v) > 0 for v in values.values())
    if numeric:
        values = {k: float(v) for k, v in values.items()}
    ordered = numeric and values["low"] <= values["mid"] <= values["high"]
    _add_check(result, "MULTIPLES_POSITIVE_ORDERED", ordered, "block",
               "目标 PE 必须为正且 low ≤ mid ≤ high")

    source = block.get("source") or config.get("multiple_source") or config.get("pe_source")
    structured = isinstance(source, dict)
    if structured:
        source = dict(source)
        has_method = bool(source.get("method") or source.get("title"))
        has_time = bool(source.get("as_of") or source.get("published_at"))
        has_locator = bool(source.get("url") or source.get("source_id"))
        structured = has_method and has_time and has_locator
    _add_check(result, "MULTIPLE_SOURCE_STRUCTURED", structured, "block",
               "倍数来源必须是含 method/title、as_of/published_at、url/source_id 的对象；自由文本不通过")
    if not ordered or not structured:
        return None
    source_quality = str(source.get("quality") or source.get("grade") or "").upper()
    source_method = str(source.get("method") or "").lower()
    manual_assumption = source_method == "manual_policy_assumption" or source_quality[:1] in {"C", "D"}
    _add_check(result, "MULTIPLE_NOT_MANUAL_LOW_QUALITY", not manual_assumption, "warn",
               f"倍数 method={source_method or '—'}、quality={source_quality or '—'}；"
               "人工政策假设或 C/D 级倍数只能 reference_only，永远不得升级为动作")
    source.setdefault("id", f"multiple-{config.get('ticker', 'unknown')}")
    source.setdefault("type", "valuation_multiple")
    source.setdefault("metric", "forward_pe")
    source.setdefault("unit", "x")
    return {**values, "source": source}


def _zone(price: float, low: float, mid: float, high: float) -> dict:
    if price <= 0.9 * low:
        zone, action = "深度低估", "进入研究清单；通过基本面复核后才可分批建仓"
    elif price <= low:
        zone, action = "低估", "研究通过后分批建仓，不以估值信号替代止跌确认"
    elif price <= mid:
        zone, action = "合理下沿", "持有或等待更高安全边际"
    elif price <= high:
        zone, action = "合理上沿", "持有，避免追高"
    elif price <= 1.3 * high:
        zone, action = "高估", "复核增长兑现度并分批控制风险"
    else:
        zone, action = "泡沫", "停止新增风险暴露，复核退出纪律"
    raw_pos = (price - low) / (high - low) if high != low else None
    return {
        "zone": zone,
        "action": action,
        "margin_of_safety": round(1 - price / mid, 3),
        # 估值带线性位置：保留 <0 或 >1 的原值（数据契约要求，不用 clamp 隐藏越界）
        "band_position_raw": round(raw_pos, 3) if raw_pos is not None else None,
        # 可视化用夹取值（进度条宽度），不代表统计百分位
        "band_position": round(max(0.0, min(1.0, raw_pos)), 3) if raw_pos is not None else None,
    }


def _evaluate_insurance_pev(config: dict, market: dict, result: dict) -> dict:
    """保险·P/EV 路由：V = 每股内含价值(EV) × 目标 P/EV。

    输入（配置侧，每日由 fetch_insurance_ev.py 刷新）：
      · ev_per_share：每股内含价值（元）
      · ev_source：结构化来源（provider/url/as_of/retrieved_at）
      · pev_low / pev_mid / pev_high：目标 P/EV 三档（D级可配置，需敏感性）
      · nbv：新业务价值（增长质量参考，不直接入公式）
    禁止用 PE 或价格反推。
    """
    _add_check(result, "MODEL_IMPLEMENTED", True, "info", "已启用 insurance_pev 透明 P/EV 路由")

    ev = config.get("ev_per_share")
    if not _finite_number(ev) or ev <= 0:
        _add_check(result, "EV_PRESENT", False, "block",
                   "缺少每股内含价值 EV，禁止用 PE 替代")
        return result
    _add_check(result, "EV_PRESENT", True, "info",
               f"每股内含价值 EV={ev:.2f} 元（{config.get('ev_as_of') or '—'}）")

    src = config.get("ev_source") or {}
    src_ok = bool(src.get("provider") and src.get("url") and src.get("as_of"))
    _add_check(result, "EV_SOURCE_STRUCTURED", src_ok, "block",
               "EV 来源必须含 provider/url/as_of 的结构化对象")
    if not src_ok:
        return result
    ev_refresh = config.get("ev_refresh") or {}
    _add_check(result, "EV_REFRESH_CURRENT", not ev_refresh.get("failed_at"), "block",
               f"今日 EV 刷新失败（{ev_refresh.get('note', '—')}）：无法确认与最新年报一致，"
               "沿用旧值即硬停止，不得继续输出估值区间")
    if ev_refresh.get("failed_at"):
        return result
    result["sources"].append(dict(src))

    low, mid, high = (config.get("pev_low"), config.get("pev_mid"), config.get("pev_high"))
    if not all(_finite_number(v) and v > 0 for v in (low, mid, high)):
        _add_check(result, "PEV_MULTIPLES_PRESENT", False, "block",
                   "缺少目标 P/EV 三档倍数（pev_low/mid/high）")
        return result
    if not (0 < low <= mid <= high):
        _add_check(result, "PEV_MULTIPLES_ORDERED", False, "block",
                   "目标 P/EV 必须满足 0 < low ≤ mid ≤ high")
        return result
    pev_method = str(config.get("pev_method") or config.get("pev_source", {}).get("method") or "industry_practice")
    pev_q = str(config.get("pev_source", {}).get("quality") or "C").upper()
    _add_check(result, "PEV_MULTIPLE_QUALITY", pev_q in {"A", "B"}, "warn",
               f"目标 P/EV 为 {pev_q} 级来源（{pev_method}）；D/C 级倍数仅参考")
    if pev_q in {"C", "D"}:
        result["quality"]["warnings"].append({
            "code": "PEV_MULTIPLE_LOW_QUALITY",
            "detail": f"目标 P/EV 为 {pev_q} 级工程参数，区间仅供参考",
        })

    v_low = round(ev * low, 2)
    v_mid = round(ev * mid, 2)
    v_high = round(ev * high, 2)
    steps = []
    for key, pev_key, value, label in (
        ("v_low", "low", v_low, "保守"),
        ("v_mid", "mid", v_mid, "基准"),
        ("v_high", "high", v_high, "乐观"),
    ):
        steps.append({
            "id": key, "label": label,
            "formula": f"{key} = 每股EV × P/EV_{pev_key}",
            "substitution": f"{ev:.4g} × {locals()['low' if pev_key=='low' else ('mid' if pev_key=='mid' else 'high')]:.4g}",
            "result": value, "unit": "CNY/share",
            "source_ids": [src.get("id") or f"ev-{config.get('ticker')}"],
        })
    result["valuation"] = {
        "v_low": v_low, "v_mid": v_mid, "v_high": v_high,
        "formula": "V = 每股EV × 目标P/EV",
        "calc_steps": steps,
        "pev_now": round((market.get("price") or 0) / ev, 3) if _finite_number(market.get("price")) else None,
        "ev_as_of": config.get("ev_as_of"),
        "nbv": config.get("nbv"),
    }
    result["reference_usable"] = True

    price = market.get("price")
    if not _finite_number(price) or price <= 0:
        result["quality"]["warnings"].append({
            "code": "PRICE_MISSING", "detail": "缺少有效价格，无法判断估值区间",
        })
        result["decision_status"] = "reference_only"
        result["quality"]["grade"] = "C"
        return result

    reference = _zone(float(price), v_low, v_mid, v_high)
    result["decision"]["reference_zone"] = reference["zone"]
    result["decision"]["margin_of_safety"] = reference["margin_of_safety"]
    result["decision"]["band_position"] = reference["band_position"]

    caution = bool(result["quality"]["warnings"]) or bool(config.get("needs_review"))
    if caution:
        result["decision_status"] = "reference_only"
        result["quality"]["grade"] = "C"
        return result
    result["decision_status"] = "ready"
    result["decision_usable"] = True
    result["quality"]["grade"] = "B"
    result["decision"].update(_zone(float(price), v_low, v_mid, v_high))
    return result


def _evaluate_normalized_pe(config: dict, market: dict, result: dict) -> dict:
    """强周期·正常化盈利路由：正常化 EPS = 周期 ROE 分位 × 最新每股净资产。

    输入（配置侧，每日由 fetch_normalized_eps.py 刷新）：
      · normalized.eps_bear/base/bull：正常化 EPS 三档
      · normalized.roe_low/mid/high、bps、bps_as_of、hist_n、window
      · normalized.source：结构化来源（provider/url/as_of/retrieved_at）
    周期股盈利预测质量天然 L/M，本路由恒为 reference_only，永不自动升级
    decision（数据契约：cyclical_normalized 缺完整周期模型时 reference/blocked）。
    """
    _add_check(result, "MODEL_IMPLEMENTED", True, "info",
               "已启用 normalized_pe 透明正常化盈利路由（周期股）")

    norm = config.get("normalized") or {}
    eps_bear, eps_base, eps_bull = (norm.get("eps_bear"), norm.get("eps_base"), norm.get("eps_bull"))
    present = all(_finite_number(v) and v > 0 for v in (eps_bear, eps_base, eps_bull))
    _add_check(result, "NORM_FIELDS_PRESENT", present, "block",
               "缺少正常化 EPS 三档（fetch_normalized_eps.py 每日写入）")
    if not present:
        return result
    ordered = eps_bear <= eps_base <= eps_bull
    _add_check(result, "NORM_VALUES_ORDERED", ordered, "block",
               "正常化 EPS 必须满足 bear ≤ base ≤ bull")
    if not ordered:
        return result

    hist_n = norm.get("hist_n")
    _add_check(result, "NORM_HISTORY_LONG_ENOUGH", isinstance(hist_n, (int, float)) and hist_n >= 8,
               "block", f"年度 ROE 序列需 ≥8 点覆盖至少一个完整周期，当前={hist_n}")
    if not isinstance(hist_n, (int, float)) or hist_n < 8:
        return result

    src = norm.get("source") or {}
    src_ok = bool(src.get("provider") and src.get("url") and src.get("as_of") and src.get("retrieved_at"))
    _add_check(result, "NORM_SOURCE_STRUCTURED", src_ok, "block",
               "正常化来源必须含 provider/url/as_of/retrieved_at 的结构化对象")
    if not src_ok:
        return result
    result["sources"].append(dict(src))

    refresh = config.get("normalized_refresh") or {}
    _add_check(result, "NORM_REFRESH_CURRENT", not refresh.get("failed_at"), "warn",
               f"今日正常化数据刷新失败（{refresh.get('note', '—')}），沿用旧值仅作参考")

    bps = norm.get("bps")
    _add_check(result, "NORM_BPS_PRESENT", _finite_number(bps) and float(bps) > 0, "block",
               "缺少最新每股净资产 BPS")
    if not (_finite_number(bps) and float(bps) > 0):
        return result

    multiple = _multiple_inputs(config, result)
    result["multiple"] = multiple
    if multiple:
        result["sources"].append(dict(multiple["source"]))

    # 周期股恒为参考级：即使倍数 B 级、数据齐全，盈利预测（中位ROE假设）质量 L/M
    result["reference_usable"] = True
    result["forecast"] = {
        "basis": "NORMALIZED",
        "label": f"正常化ROE@{norm.get('window') or '—'}",
        "year": None,
        "horizon": "NORMALIZED",
        "count": int(hist_n),
        "bear": eps_bear, "base": eps_base, "bull": eps_bull,
        "provider": src.get("provider"),
        "url": src.get("url"),
        "source_as_of": src.get("as_of"),
        "retrieved_at": src.get("retrieved_at"),
        "formula": "正常化EPS = 周期ROE分位(P25/P50/P75) × 最新每股净资产",
        "roe_low": norm.get("roe_low"), "roe_mid": norm.get("roe_mid"), "roe_high": norm.get("roe_high"),
        "bps": bps, "bps_as_of": norm.get("bps_as_of"), "window": norm.get("window"),
    }
    _add_check(result, "NORMALIZED_REFERENCE_ONLY", False, "info",
               "周期股正常化盈利恒为参考级（预测质量 L/M），不输出可执行动作")

    if not multiple or result["quality"]["blockers"]:
        return result

    low = round(eps_bear * multiple["low"], 2)
    mid = round(eps_base * multiple["mid"], 2)
    high = round(eps_bull * multiple["high"], 2)
    if not (0 < low <= mid <= high):
        _add_check(result, "VALUATION_ANCHORS_ORDERED", False, "block",
                   "计算后必须满足 0 < V_low ≤ V_mid ≤ V_high")
        return result
    _add_check(result, "VALUATION_ANCHORS_ORDERED", True, "info", "正常化估值锚有序")

    source_ids = [x.get("id") for x in result["sources"] if x.get("id")]
    eps_map = {"bear": eps_bear, "base": eps_base, "bull": eps_bull}
    steps = []
    for key, eps_key, pe_key, value, label in (
        ("v_low", "bear", "low", low, "保守"),
        ("v_mid", "base", "mid", mid, "基准"),
        ("v_high", "bull", "high", high, "乐观"),
    ):
        steps.append({
            "id": key,
            "label": label,
            "formula": f"{key} = 正常化EPS_{eps_key} × 周期PE_{pe_key}",
            "substitution": f"{eps_map[eps_key]:.6g} × {multiple[pe_key]:.6g}",
            "result": value,
            "unit": "CNY/share",
            "source_ids": source_ids,
        })
    result["valuation"] = {
        "v_low": low, "v_mid": mid, "v_high": high,
        "formula": "V = 正常化EPS × 周期PE（历史分位校准）",
        "calc_steps": steps,
    }

    price = market.get("price")
    if _finite_number(price) and float(price) > 0:
        reference = _zone(float(price), low, mid, high)
        result["decision"]["reference_zone"] = reference["zone"]
        result["decision"]["margin_of_safety"] = reference["margin_of_safety"]
        result["decision"]["band_position"] = reference["band_position"]
        result["decision"]["band_position_raw"] = reference["band_position_raw"]
    result["decision_status"] = "reference_only"
    result["quality"]["grade"] = "C"
    return result


def _quantile(vals, q):
    vals = sorted(vals)
    idx = int(len(vals) * q)
    idx = max(0, min(len(vals) - 1, idx))
    return vals[idx]


def _special_common(config, result, block_key, label):
    """bank/infra 路由共用输入检查；返回 (blk, bps, multiple) 或 None。"""
    blk = config.get(block_key) or {}
    bps = blk.get("bps")
    _add_check(result, f"{label}_BVPS_PRESENT", _finite_number(bps) and float(bps) > 0, "block",
               f"缺少最新每股净资产（{label} 数据块）")
    if not (_finite_number(bps) and float(bps) > 0):
        return None
    src = blk.get("source") or {}
    src_ok = bool(src.get("provider") and src.get("url") and src.get("as_of") and src.get("retrieved_at"))
    _add_check(result, f"{label}_SOURCE_STRUCTURED", src_ok, "block",
               f"{label} 数据来源必须含 provider/url/as_of/retrieved_at")
    if not src_ok:
        return None
    result["sources"].append(dict(src))
    refresh = config.get("special_refresh") or {}
    _add_check(result, f"{label}_REFRESH_CURRENT", not refresh.get("failed_at"), "warn",
               f"今日{label}数据刷新失败（{refresh.get('note', '—')}），沿用旧值仅作参考")
    multiple = _multiple_inputs(config, result)
    result["multiple"] = multiple
    if multiple:
        result["sources"].append(dict(multiple["source"]))
    return blk, float(bps), multiple


def _finish_special(result, bps, multiple, price, basis, label, diag=None):
    """两条特殊路由共用收尾：V = 每股净资产 × 历史PB分位带，恒为 reference_only。"""
    result["reference_usable"] = True
    result["forecast"] = {
        "basis": basis, "label": label, "year": None, "horizon": "PB_BAND",
        "bear": None, "base": None, "bull": None,
        "provider": (result["sources"][0] if result["sources"] else {}).get("provider"),
    }
    if diag:
        result["diagnostics"] = diag
    _add_check(result, f"{basis}_REFERENCE_ONLY", False, "info",
               "工程参数（Ke/g、历史分位带）与部分核验的财务质量门：恒为参考级，不输出可执行动作")
    if not multiple or result["quality"]["blockers"]:
        return result
    low = round(bps * multiple["low"], 2)
    mid = round(bps * multiple["mid"], 2)
    high = round(bps * multiple["high"], 2)
    if not (0 < low <= mid <= high):
        _add_check(result, "VALUATION_ANCHORS_ORDERED", False, "block",
                   "计算后必须满足 0 < V_low ≤ V_mid ≤ V_high")
        return result
    _add_check(result, "VALUATION_ANCHORS_ORDERED", True, "info", "估值锚有序")
    steps = []
    for key, pe_key, value, lbl in (("v_low", "low", low, "保守"), ("v_mid", "mid", mid, "基准"),
                                    ("v_high", "high", high, "乐观")):
        steps.append({
            "id": key, "label": lbl,
            "formula": f"{key} = 每股净资产 × 历史PB分位_{pe_key}",
            "substitution": f"{bps:.6g} × {multiple[pe_key]:.6g}",
            "result": value, "unit": "CNY/share", "source_ids": [],
        })
    result["valuation"] = {
        "v_low": low, "v_mid": mid, "v_high": high,
        "formula": "V = 每股净资产 × 历史PB分位带（B级校准）",
        "calc_steps": steps,
    }
    if _finite_number(price) and float(price) > 0:
        reference = _zone(float(price), low, mid, high)
        result["decision"]["reference_zone"] = reference["zone"]
        result["decision"]["margin_of_safety"] = reference["margin_of_safety"]
        result["decision"]["band_position"] = reference["band_position"]
        result["decision"]["band_position_raw"] = reference["band_position_raw"]
    result["decision_status"] = "reference_only"
    result["quality"]["grade"] = "C"
    return result


def _evaluate_bank_pb_roe(config, market, result):
    """银行·PB-ROE 路由：每股净资产 × 历史PB分位带为主，PB-ROE 理论值为诊断。

    输入（fetch_special_routes.py 每日刷新）：bank.bps/roe_hist/npl/provision/car/ke/g。
    质量门：BVPS、ROE 历史≥8点、Ke>g、不良率/拨备/核心一级数据齐（缺失仅降级不硬停，
    但恒为 reference_only；数据契约：银行资产质量门完整才可 decision，本实现为公开
    快照级核验，永不自动升级）。
    """
    _add_check(result, "MODEL_IMPLEMENTED", True, "info", "已启用 bank_pb_roe 透明 PB-ROE/资产质量路由（银行）")
    base = _special_common(config, result, "bank", "BANK")
    if base is None:
        return result
    blk, bps, multiple = base

    roe_chron = [v for v in (blk.get("roe_hist") or []) if isinstance(v, (int, float)) and v > 0]
    roe_hist = sorted(roe_chron)
    _add_check(result, "BANK_ROE_HISTORY", len(roe_hist) >= 8, "block",
               f"年度 ROE 序列需 ≥8 点（当前 {len(roe_hist)}），否则无法估计可持续 ROE")
    if len(roe_hist) < 8:
        return result

    ke = float(blk.get("ke") or 0.10)
    g = float(blk.get("g") or 0.03)
    _add_check(result, "BANK_KE_GT_G", ke > g, "block",
               f"股权成本 Ke={ke:.2f} 必须大于永续增速 g={g:.2f}（均为 D 级工程参数）")
    if not (ke > g):
        return result

    npl, provision, car = blk.get("npl"), blk.get("provision"), blk.get("car")
    _add_check(result, "BANK_NPL_PRESENT", _finite_number(npl), "warn",
               "不良率缺失：资产质量无法核验")
    if _finite_number(npl) and float(npl) > 3:
        result["quality"]["warnings"].append({"code": "BANK_NPL_HIGH",
                                              "detail": f"不良率 {npl}% 偏高（>3%）"})
    _add_check(result, "BANK_CAR_PRESENT", _finite_number(car), "warn",
               "核心一级资本充足率缺失")
    if _finite_number(car) and float(car) < 11.5:
        result["quality"]["warnings"].append({"code": "BANK_CAR_THIN",
                                              "detail": f"核心一级资本充足率 {car}% 缓冲偏薄（<11.5%）"})

    r25, r50, r75 = _quantile(roe_hist, .25), _quantile(roe_hist, .50), _quantile(roe_hist, .75)
    roe_first5 = min(roe_chron[:5]) if len(roe_chron) >= 5 else r50
    roe_latest = roe_chron[-1]
    if roe_first5 > 0 and roe_latest < roe_first5 * 0.7:
        result["quality"]["warnings"].append({
            "code": "BANK_ROE_DECLINE",
            "detail": f"ROE 长期下行（早年 {roe_first5}% → 最新 {roe_latest}%），PB-ROE 理论价值下修",
        })

    pb_low = max(0.0, (r25 / 100 - g) / (ke - g))
    pb_mid = max(0.0, (r50 / 100 - g) / (ke - g))
    pb_high = max(0.0, (r75 / 100 - g) / (ke - g))
    diag = {
        "roe_p25": round(r25, 2), "roe_p50": round(r50, 2), "roe_p75": round(r75, 2),
        "ke": ke, "g": g,
        "pb_theo_low": round(pb_low, 2), "pb_theo_mid": round(pb_mid, 2), "pb_theo_high": round(pb_high, 2),
        "formula": "合理PB = (可持续ROE − g) ÷ (Ke − g)",
        "note": "Ke=10%、g=3% 为 D 级工程参数；A股银行市场定价长期低于理论PB，"
                "以历史PB分位带为主、理论值为诊断，不据此自动升级决策",
    }
    return _finish_special(result, bps, multiple, market.get("price"), "BANK_PB_ROE",
                           "银行·历史PB分位带×每股净资产", diag)


def _evaluate_infrastructure(config, market, result):
    """建筑现金流/调整PB 路由：每股净资产 × 历史PB分位带 + 现金流质量门。

    输入（fetch_special_routes.py 每日刷新）：infra.bps/ocf_latest/ar_days_latest/
    debt_latest 及各自历史。质量门：经营现金流为正、应收周转天数趋势、资产负债率；
    任一恶化仅 warn（恒为 reference_only）。数据契约：construction_cashflow_pb 应收、
    减值和现金流未完整核验时 blocked→reference（本实现为摘要级核验，参考级）。
    """
    _add_check(result, "MODEL_IMPLEMENTED", True, "info",
               "已启用 infrastructure_cashflow 现金流质量/调整PB路由（建筑）")
    base = _special_common(config, result, "infra", "INFRA")
    if base is None:
        return result
    blk, bps, multiple = base

    ocf = blk.get("ocf_latest")
    _add_check(result, "INFRA_OCF_POSITIVE", _finite_number(ocf) and float(ocf) > 0, "warn",
               f"最新年报每股经营现金流={ocf}（{'为负/近零，现金转化存疑' if not (_finite_number(ocf) and float(ocf) > 0) else '为正'}）")

    ar = blk.get("ar_days_latest")
    ar_hist = [v for v in (blk.get("ar_days_hist") or []) if isinstance(v, (int, float))]
    if _finite_number(ar) and len(ar_hist) >= 5:
        med5 = sorted(ar_hist[-5:])[2]
        if med5 > 0 and float(ar) > med5 * 1.2:
            result["quality"]["warnings"].append({
                "code": "INFRA_AR_RISING",
                "detail": f"应收账款周转天数 {ar} 天，较近5年中位 {med5} 天抬升 >20%（回款质量恶化）",
            })
        else:
            _add_check(result, "INFRA_AR_STABLE", True, "info", f"应收周转 {ar} 天（近5年中位 {med5} 天）")
    else:
        _add_check(result, "INFRA_AR_PRESENT", _finite_number(ar), "warn", "应收账款周转天数缺失")

    debt = blk.get("debt_latest")
    _add_check(result, "INFRA_DEBT_PRESENT", _finite_number(debt), "warn", "资产负债率缺失")
    if _finite_number(debt) and float(debt) > 80:
        result["quality"]["warnings"].append({
            "code": "INFRA_DEBT_HIGH",
            "detail": f"资产负债率 {debt}% 高杠杆（>80%）",
        })

    diag = {
        "ocf_latest": ocf,
        "ar_days_latest": ar,
        "debt_latest": debt,
        "formula": "V = 每股净资产 × 历史PB分位带；现金流质量门仅作降级诊断",
        "note": "低PB不构成独立买入理由（数据契约），需政策周期与现金流改善确认",
    }
    return _finish_special(result, bps, multiple, market.get("price"), "INFRA_PB_BAND",
                           "建筑·调整PB×每股净资产（现金流质量门）", diag)


def evaluate_stock(config: dict, market: dict, forecast_data: dict | None,
                   forecast_meta: dict | None = None, as_of: str | dt.date | None = None) -> dict:
    """对单只股票执行透明估值与质量门。

    ``decision_status`` 取值：``ready``、``reference_only``、``blocked``、
    ``observe``。只有 ``ready`` 的 ``decision_usable`` 为 true，才会输出动作。
    """
    result = _base_result(config)
    model = result["model"]
    code = model["code"]
    as_of_date = as_of if isinstance(as_of, dt.date) else _iso_date(as_of)
    as_of_date = as_of_date or dt.date.today()

    if code == "observe":
        result["decision_status"] = "observe"
        result["quality"]["grade"] = "N/A"
        _add_check(result, "OBSERVE_ROUTE", True, "info",
                   "观察路由不输出估值锚、区间动作或仓位信号")
        return result
    if code in UNIMPLEMENTED_ROUTES:
        _add_check(result, "MODEL_IMPLEMENTED", False, "block", UNIMPLEMENTED_ROUTES[code])
        return result
    if code in IMPLEMENTED_INSURANCE_ROUTES:
        return _evaluate_insurance_pev(config, market, result)
    if code in IMPLEMENTED_NORMALIZED_ROUTES:
        return _evaluate_normalized_pe(config, market, result)
    if code in IMPLEMENTED_SPECIAL_ROUTES:
        if code == "bank_pb_roe":
            return _evaluate_bank_pb_roe(config, market, result)
        return _evaluate_infrastructure(config, market, result)
    if code not in IMPLEMENTED_PE_ROUTES:
        _add_check(result, "MODEL_DECLARED", False, "block",
                   "必须显式声明 valuation_model；未知模型不得回退到 PE")
        return result
    _add_check(result, "MODEL_IMPLEMENTED", True, "info", f"已启用 {code} 透明前瞻 PE 路由")

    meta = dict(forecast_meta or {})
    source_ok = bool(forecast_data and forecast_data.get("provider") and
                     forecast_data.get("url") and forecast_data.get("retrieved_at") and
                     forecast_data.get("as_of"))
    _add_check(result, "FORECAST_SOURCE_STRUCTURED", source_ok, "block",
               "预测来源必须包含 provider/url/as_of/retrieved_at")
    stale = bool(meta.get("stale"))
    _add_check(result, "FORECAST_FETCH_CURRENT", not stale, "warn",
               "本次预测抓取失败或沿用旧值时只允许参考，不可生成动作")

    selected = _select_forecast(config, forecast_data, as_of_date, result)
    multiple = _multiple_inputs(config, result)
    result["forecast"] = selected
    if selected:
        result["forecast"].update({
            "provider": (forecast_data or {}).get("provider"),
            "url": (forecast_data or {}).get("url"),
            "source_as_of": (forecast_data or {}).get("as_of"),
            "retrieved_at": (forecast_data or {}).get("retrieved_at"),
            "actual_eps_history": _actual_history(forecast_data),
        })

    # ---- 成长修正认知补偿（隐患：历史 TTM 分位 × 前瞻 EPS 的混合失真）----
    # 对 growth_pe 路由且 FY1 增速 >30% 的股票，历史 TTM 分位倍数可能系统性低估
    # 成长溢价。不硬改倍数（保持客观），但按 PEG≈1 给出交叉参考并显著提示。
    if selected and code == "growth_pe":
        hist_eps = _actual_history(forecast_data)
        if hist_eps:
            last_actual = hist_eps[-1]
            if last_actual["eps"] and last_actual["eps"] > 0:
                growth = selected["base"] / last_actual["eps"] - 1
                if growth > 0.30:
                    peg_pe = round(growth * 100, 1)  # PEG≈1 → 合理PE≈增速%
                    result["growth_momentum"] = {
                        "last_fy": last_actual["year"],
                        "last_eps": last_actual["eps"],
                        "base_eps": selected["base"],
                        "growth": round(growth, 4),
                        "peg_pe": peg_pe,
                        "note": "历史TTM分位倍数可能低估成长溢价（PEG交叉检查）",
                    }
                    _add_check(
                        result, "GROWTH_MOMENTUM", True, "info",
                        f"FY1 盈利增速 {growth*100:.0f}%（{last_actual['year']} EPS "
                        f"{last_actual['eps']} → 基准 {selected['base']}）；历史TTM分位倍数可能保守，"
                        f"PEG≈1 参考合理PE≈{peg_pe:.0f}×（A级：合理倍数结合基本面修正）",
                    )
    result["multiple"] = multiple

    if source_ok:
        result["sources"].append({
            "id": f"ths-worth-{config.get('ticker')}-{forecast_data.get('as_of')}",
            "type": "consensus_forecast",
            "provider": forecast_data.get("provider"),
            "title": forecast_data.get("title"),
            "url": forecast_data.get("url"),
            "as_of": forecast_data.get("as_of"),
            "retrieved_at": forecast_data.get("retrieved_at"),
            "raw_sha256": forecast_data.get("raw_sha256"),
            "metric": "diluted_eps",
            "unit": "CNY/share",
        })
    if multiple:
        result["sources"].append(dict(multiple["source"]))

    if result["quality"]["blockers"] or not selected or not multiple:
        return result

    low = round(selected["bear"] * multiple["low"], 2)
    mid = round(selected["base"] * multiple["mid"], 2)
    high = round(selected["bull"] * multiple["high"], 2)
    anchors_ordered = 0 < low <= mid <= high
    _add_check(result, "VALUATION_ANCHORS_ORDERED", anchors_ordered, "block",
               "计算后必须满足 0 < V_low ≤ V_mid ≤ V_high")
    if not anchors_ordered:
        return result

    source_ids = [x.get("id") for x in result["sources"] if x.get("id")]
    steps = []
    for key, eps_key, pe_key, value, label in (
        ("v_low", "bear", "low", low, "保守"),
        ("v_mid", "base", "mid", mid, "基准"),
        ("v_high", "bull", "high", high, "乐观"),
    ):
        steps.append({
            "id": key,
            "label": label,
            "formula": f"{key} = EPS_{eps_key} × PE_{pe_key}",
            "substitution": f"{selected[eps_key]:.6g} × {multiple[pe_key]:.6g}",
            "result": value,
            "unit": "CNY/share",
            "source_ids": source_ids,
        })
    result["valuation"] = {
        "v_low": low, "v_mid": mid, "v_high": high,
        "formula": "V = structured forward EPS × sourced target PE",
        "calc_steps": steps,
    }
    result["reference_usable"] = True

    caution = stale or bool(result["quality"]["warnings"]) or bool(config.get("needs_review"))
    if config.get("needs_review"):
        result["quality"]["warnings"].append({
            "code": "CONFIG_NEEDS_REVIEW",
            "detail": "配置仍标记 needs_review，仅允许参考估值",
        })
    price = market.get("price")
    if _finite_number(price) and float(price) > 0:
        reference = _zone(float(price), low, mid, high)
        result["decision"]["reference_zone"] = reference["zone"]
        result["decision"]["margin_of_safety"] = reference["margin_of_safety"]
        result["decision"]["band_position"] = reference["band_position"]
    else:
        caution = True
        result["quality"]["warnings"].append({
            "code": "PRICE_MISSING", "detail": "缺少有效价格，无法判断估值区间",
        })

    if caution:
        result["decision_status"] = "reference_only"
        result["quality"]["grade"] = "C"
        return result

    result["decision_status"] = "ready"
    result["decision_usable"] = True
    result["quality"]["grade"] = "B"
    if _finite_number(price) and float(price) > 0:
        ready = _zone(float(price), low, mid, high)
        result["decision"].update(ready)
    return result


__all__ = [
    "ENGINE_VERSION", "SCHEMA_VERSION", "evaluate_stock", "resolve_model",
]
