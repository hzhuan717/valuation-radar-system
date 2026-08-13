# -*- coding: utf-8 -*-
"""专项路由数据抓取器 → 写入 watchlist.json 配置

1. infrastructure_cashflow（建筑央企，如中国铁建）：
   - 同花顺财务摘要（按年度）：每股经营现金流、应收账款周转天数、资产负债率、
     净资产收益率、每股净资产（最新）
   - 用途：现金流/应收/负债质量门 + 每股净资产×历史PB分位带

2. bank_pb_roe（银行，如光大银行）：
   - 同花顺财务摘要（按年度）：净资产收益率历史、每股净资产（最新）
   - 东财 F10 主要指标：不良率(NONPERLOAN)、拨备覆盖率(LOAN_PROVISION_RATIO)、
     核心一级资本充足率(NEWCAPITALADER)
   - 用途：PB-ROE 诊断（Ke=10%、g=3% 为 D 级工程参数）+ 资产质量门 +
     每股净资产×历史PB分位带

输出等级：两条路由引擎均恒为 reference_only（工程参数 D 级、现金流/资产质量
仅部分核验，数据契约：construction_cashflow_pb 缺完整核验时 blocked→reference，
bank_pb_roe 资产质量门完整才可 decision——本实现资产质量仅为公开快照级，不升级）。
"""
import io
import json
import os
import sys
import datetime
import urllib.request

if __name__ == '__main__':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

BASE = r"E:\财报解读\watchlist"
WATCHLIST = os.path.join(BASE, "watchlist.json")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
THS_URL = "https://basic.10jqka.com.cn/{code}/finance.html"
EM_URL = ("https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/"
          "ZYZBAjaxNew?type=0&code={mkt}")


def _num(s):
    s = str(s).strip().replace("%", "").replace(",", "")
    if s in ("", "-", "--", "nan", "None", "—"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def fetch_abstract(code: str) -> list:
    """同花顺财务摘要（按年度）→ [{year, ocf, ar_days, debt, roe, bps}]"""
    import akshare as ak
    df = ak.stock_financial_abstract_ths(symbol=code, indicator="按年度")
    rows = []
    for _, r in df.iterrows():
        try:
            year = int(str(r["报告期"])[:4])
        except (KeyError, TypeError, ValueError):
            continue
        rows.append({
            "year": year,
            "ocf": _num(r.get("每股经营现金流")),
            "ar_days": _num(r.get("应收账款周转天数")),
            "debt": _num(r.get("资产负债率")),
            "roe": _num(r.get("净资产收益率")),
            "bps": _num(r.get("每股净资产")),
        })
    rows.sort(key=lambda x: x["year"])
    return rows


def fetch_bank_f10(code: str) -> dict:
    mkt = ("SH" if code[0] in "69" else "SZ") + code
    req = urllib.request.Request(EM_URL.format(mkt=mkt), headers=UA)
    data = json.loads(urllib.request.urlopen(req, timeout=20).read().decode("utf-8"))
    rows = data.get("data") or []
    latest = max(rows, key=lambda r: str(r.get("REPORT_DATE", "")))
    provision = _num(latest.get("LOAN_PROVISION_RATIO"))
    if provision is None:
        for r in sorted(rows, key=lambda r: str(r.get("REPORT_DATE", "")), reverse=True):
            v = _num(r.get("LOAN_PROVISION_RATIO"))
            if v is not None:
                provision = v
                break
    return {
        "npl": _num(latest.get("NONPERLOAN")),
        "npl_as_of": str(latest.get("REPORT_DATE", ""))[:10],
        "provision": provision,
        "car": _num(latest.get("NEWCAPITALADER")),
    }


def _series(rows, key):
    return [r[key] for r in rows if r.get(key) is not None]


def main():
    with open(WATCHLIST, encoding="utf-8") as f:
        wl = json.load(f)
    dirty = False
    done = 0

    for s in wl["stocks"]:
        vm = s.get("valuation_model")
        code = vm.get("code") if isinstance(vm, dict) else vm
        ticker = s["ticker"]
        name = s.get("name", ticker)
        if code not in ("infrastructure_cashflow", "bank_pb_roe"):
            continue
        dirty = True
        try:
            rows = fetch_abstract(ticker)
            if len(rows) < 5:
                s["special_refresh"] = {"failed_at": _now(), "note": f"年度摘要不足({len(rows)})"}
                print(f"{ticker} {name}: 年度摘要不足({len(rows)})，保持拦截")
                continue
            latest = rows[-1]
            if code == "infrastructure_cashflow":
                blk = {
                    "bps": latest["bps"],
                    "bps_as_of": f"{latest['year']}-12-31",
                    "ocf_latest": latest["ocf"],
                    "ocf_hist": _series(rows, "ocf"),
                    "ar_days_latest": latest["ar_days"],
                    "ar_days_hist": _series(rows, "ar_days"),
                    "debt_latest": latest["debt"],
                    "debt_hist": _series(rows, "debt"),
                    "roe_hist": _series(rows, "roe"),
                    "source": _ths_source(ticker, name),
                }
                s["infra"] = blk
                s["special_refresh"] = {"ok_at": _now()}
                done += 1
                print(f"{ticker} {name}: 现金流质量数据已写入（OCF={latest['ocf']}、"
                      f"应收{latest['ar_days']}天、负债率{latest['debt']}%、BPS={latest['bps']}）")
            else:
                f10 = fetch_bank_f10(ticker)
                blk = {
                    "bps": latest["bps"],
                    "bps_as_of": f"{latest['year']}-12-31",
                    "roe_hist": _series(rows, "roe"),
                    "npl": f10["npl"],
                    "npl_as_of": f10["npl_as_of"],
                    "provision": f10["provision"],
                    "car": f10["car"],
                    "ke": 0.10, "g": 0.03,
                    "source": _ths_source(ticker, name),
                    "f10_source": {
                        "provider": "东方财富F10主要指标", "url": EM_URL.format(mkt=("SH" if ticker[0] in "69" else "SZ") + ticker),
                        "as_of": f10["npl_as_of"], "retrieved_at": _now(),
                    },
                }
                s["bank"] = blk
                s["special_refresh"] = {"ok_at": _now()}
                done += 1
                print(f"{ticker} {name}: 银行质量数据已写入（ROE最新{latest['roe']}%、"
                      f"不良{f10['npl']}%、拨备{f10['provision']}、核心一级{f10['car']}%、BPS={latest['bps']}）")
        except Exception as e:
            s["special_refresh"] = {"failed_at": _now(), "note": f"{type(e).__name__}: {e}"}
            print(f"{ticker} {name}: 专项数据抓取失败（已标记）: {e}")

    if dirty:
        with open(WATCHLIST, "w", encoding="utf-8") as f:
            json.dump(wl, f, ensure_ascii=False, indent=2)
    print(f"完成：{done} 只专项路由数据已写入")


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _ths_source(ticker, name):
    return {
        "id": f"ths-abstract-{ticker}",
        "type": "special_route_financials",
        "provider": "同花顺F10财务摘要",
        "title": f"{name} 年度财务摘要",
        "url": THS_URL.format(code=ticker),
        "as_of": datetime.date.today().isoformat(),
        "retrieved_at": _now(),
    }


if __name__ == "__main__":
    main()
