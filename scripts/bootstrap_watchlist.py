# -*- coding: utf-8 -*-
"""watchlist.json 引导脚本（一次性 / 可按需重跑）。

行为：
  1. 实时行情采集 16 只股票（腾讯主源），核验名称与股本
  2. 抓取同花顺个股 worth 页的结构化年度 EPS；失败即留空并阻断，不做 price/PE 回退
  3. 写入显式估值模型路由；行业倍数仍为待校准配置，不直接构成决策信号
  4. ETF（515220）与亏损股（600844）走 manual_band / 观察通道
  产出：E:\\财报解读\\watchlist\\watchlist.json
  所有参数带 evidence 标签；needs_review=true 表示需人工校准。
"""
import json
import os
import sys
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_fetch import fetch_spot, fetch_profit_forecast, now  # noqa: E402

BASE = r"E:\财报解读\watchlist"
OUT = os.path.join(BASE, "watchlist.json")

CODES = ["600085", "002384", "002472", "300760", "601318", "605090", "601899",
         "002428", "000725", "000100", "601818", "600350", "601186", "515220",
         "002340", "600844"]

# 行业路由默认 PE 三档（D 级模板，可人工校准）
ROUTE_PE = {
    "600085": (25, 32, 42, "中药成熟龙头，稳定消费路由"),
    "002384": (20, 28, 38, "电子制造（PCB/精密），成长路由"),
    "002472": (22, 30, 42, "高端齿轮制造，成长路由"),
    "300760": (25, 33, 45, "医疗器械龙头，稳定消费+成长路由"),
    "601318": (8, 10, 13, "保险，P/EV 路由简化（PE 为辅助口径）"),
    "605090": (12, 15, 20, "燃气/能源服务，公用事业路由"),
    "601899": (14, 17, 22, "有色资源，强周期路由（正常化盈利）"),
    "002428": (35, 45, 60, "小金属/锗，高波动题材，安全边际要求更高"),
    "000725": (20, 28, 40, "面板，周期成长路由"),
    "000100": (15, 20, 28, "面板/光伏，周期成长路由"),
    "600350": (10, 13, 17, "高速公路，公用事业路由"),
    "002340": (15, 20, 28, "电池回收/材料，周期+成长路由"),
    # 601818 / 601186：人工分析参数（见旧报告）
    "601818": (4.0, 4.8, 5.6, "银行 PB-ROE 路由；沿用 2026-08-07 人工分析"),
    "601186": (4.0, 4.8, 6.0, "建筑央企，资产负债表路由；沿用 2026-08-07 人工分析"),
}

VALUATION_MODELS = {
    "600085": ("forward_pe", "稳定盈利，使用 FY1 结构化一致预期与有来源的目标 PE"),
    "002384": ("growth_pe", "成长制造，使用 FY1 一致预期；倍数必须单独校准"),
    "002472": ("growth_pe", "成长制造，使用 FY1 一致预期；倍数必须单独校准"),
    "300760": ("growth_pe", "医疗器械成长，使用 FY1 一致预期；倍数必须单独校准"),
    "601318": ("insurance_pev", "保险应使用 P/EV，禁止 PE 简化替代"),
    "605090": ("forward_pe", "盈利为正且相对稳定，可用 FY1 前瞻 PE"),
    "601899": ("normalized_pe", "强周期资源股必须使用正常化盈利"),
    "002428": ("normalized_pe", "小金属周期与题材波动，禁止当前 TTM PE 主估值"),
    "000725": ("normalized_pe", "面板强周期，必须使用跨周期正常化盈利"),
    "000100": ("normalized_pe", "面板/光伏周期，必须使用跨周期正常化盈利"),
    "601818": ("bank_pb_roe", "银行应使用 PB-ROE，禁止 PE 替代"),
    "600350": ("forward_pe", "公路经营现金流较稳定，可用 FY1 前瞻 PE"),
    "601186": ("infrastructure_cashflow", "基建央企应优先现金流与资产负债表"),
    "515220": ("etf_index", "ETF 使用跟踪指数估值分位"),
    "002340": ("growth_pe", "周期成长混合，仅使用显式 FY1 一致预期"),
    "600844": ("observe", "亏损企业观察，禁止 PE 估值"),
}

SPECIAL = {
    "515220": {"route": "etf", "manual_band": {"v_low": 1.00, "v_mid": 1.15, "v_high": 1.35},
               "notes": "煤炭ETF：不适用个股EPS×PE，锚定中证煤炭指数PE分位（待校准）"},
    "600844": {"route": "loss", "notes": "金煤科技 TTM 亏损（PE<0）：不适用PE估值法，仅观察，失败保护"},
}


def main():
    spot, meta = fetch_spot(CODES)
    if not spot:
        print("行情采集失败:", meta.get("error"))
        sys.exit(1)
    print(f"行情核验 {len(spot)}/16 · 来源 {meta['source']} · {meta['collected_at']}")

    stocks = []
    missing = []
    for code in CODES:
        s = spot.get(code)
        if not s:
            missing.append(code)
            continue
        entry = {
            "ticker": code,
            "name": s["name"],
            "route": "equity",
            "bootstrap_date": datetime.date.today().isoformat(),
            "needs_review": True,
            "notes": "",
        }
        model_code, model_reason = VALUATION_MODELS[code]
        entry["valuation_model"] = {
            "code": model_code,
            "label": model_code,
            "reason": model_reason,
            "rule_version": "2026.08-v2",
        }

        if code in SPECIAL:
            sp = SPECIAL[code]
            entry["route"] = sp["route"]
            entry["manual_band"] = sp.get("manual_band")
            entry["notes"] = sp["notes"]
            entry["needs_review"] = True
            entry["market"] = {"price": s["price"], "pe_ttm": s["pe_ttm"],
                               "pb": s["pb"], "shares": s["shares"],
                               "total_mv": s["total_mv"], "collected_at": meta["collected_at"],
                               "spot_source": meta["source"]}
            stocks.append(entry)
            continue

        # 同花顺结构化一致预期。FY1 以页面实际 EPS 历史的最新年度 + 1 定义。
        # 缺失即保持 None；禁止使用 price/PE 或 TTM EPS 伪装未来预测。
        fc, fc_meta = fetch_profit_forecast(code)
        actual_years = [int(x["year"]) for x in (fc or {}).get("actual_eps_history", [])
                        if x.get("year") is not None]
        last_actual_fy = max(actual_years) if actual_years else None
        forecast_year = last_actual_fy + 1 if last_actual_fy is not None else None
        forecast_row = next((x for x in (fc or {}).get("forecasts", [])
                             if int(x.get("year", -1)) == forecast_year), None)
        if forecast_row:
            eps_bear = float(forecast_row["min"])
            eps_base = float(forecast_row["mean"])
            eps_bull = float(forecast_row["max"])
            entry["forecast_source"] = (
                f"同花顺F10 {forecast_year}E/FY1（{forecast_row['count']}家，"
                f"min/mean/max={eps_bear}/{eps_base}/{eps_bull}），"
                f"as_of={(fc or {}).get('as_of')}"
            )
        else:
            eps_bear = eps_base = eps_bull = None
            entry["forecast_source"] = (
                "结构化 FY1 预测缺失；估值必须 blocked，禁止 price/PE 回退。"
                f"抓取状态={fc_meta.get('status')}，错误={fc_meta.get('error') or '—'}"
            )
        entry["last_actual_fy"] = last_actual_fy
        entry["forecast_year"] = forecast_year
        entry["forecast_basis"] = "FY1"
        entry["forecast_data"] = fc
        entry["forecast_meta"] = fc_meta

        pe_low, pe_mid, pe_high, route_note = ROUTE_PE[code]
        entry.update({
            "eps_bear": eps_bear, "eps_base": eps_base, "eps_bull": eps_bull,
            "pe_low": pe_low, "pe_mid": pe_mid, "pe_high": pe_high,
            "net_profit_fc": None, "shares": s["shares"],
            "pe_source": route_note + "（D级路由默认，可校准）",
            "eps_source": entry["forecast_source"],
            "notes": route_note,
        })
        if entry["notes"].startswith("；"):
            entry["notes"] = entry["notes"][1:]
        entry["market"] = {"price": s["price"], "pe_ttm": s["pe_ttm"],
                           "pb": s["pb"], "shares": s["shares"],
                           "total_mv": s["total_mv"], "collected_at": meta["collected_at"],
                           "spot_source": meta["source"]}
        stocks.append(entry)

    data = {
        "meta": {
            "created": now(),
            "count": len(stocks),
            "method": "valuation-radar",
            "disclaimer": "研究/教学/回测用途，不构成投资建议，不连接券商，不执行交易。",
        },
        "stocks": stocks,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"已写入 {OUT}：{len(stocks)} 只")
    if missing:
        print("缺失:", missing)
    for st in stocks:
        tag = "[需校准]" if st.get("needs_review") else "[OK]"
        print(f"  {st['ticker']} {st['name']} {tag} eps={st.get('eps_base')} pe={st.get('pe_low')}/{st.get('pe_mid')}/{st.get('pe_high')}")


if __name__ == "__main__":
    main()
