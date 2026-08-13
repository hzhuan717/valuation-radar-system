# -*- coding: utf-8 -*-
"""强周期股正常化盈利数据抓取器（同花顺财务摘要）→ 写入 watchlist.json 配置

目标：为 normalized_pe 路由提供跨周期正常化 EPS 三档（bear/base/bull）。

数据源：同花顺 F10 财务摘要（按年度，经 akshare 采集）：
  · 净资产收益率（加权 ROE，%）：跨周期中位法
  · 每股净资产（BPS，元）：最新报告期
公式（数据契约 5.2 强周期/资源）：
  正常化 EPS = 周期 ROE 分位 × 最新每股净资产
  ROE_bear/base/bull = 最近 10 个年报 ROE 的 P25/P50/P75（覆盖至少一个完整周期）

护栏（fail-closed）：
  · 年度 ROE 序列 < 8 点 → 不写 normalized（引擎保持 blocked）
  · ROE 分位任一 ≤ 0 → 不写（周期亏损股禁止套 PE，如微利/亏损股）
  · 最新每股净资产缺失或非正 → 不写
输出等级：normalized_pe 引擎恒为 reference_only（周期盈利预测质量天然 L/M，
数据契约：缺完整周期模型时 reference/blocked，永不自动升级 decision）。
"""
import io
import json
import os
import sys
import datetime

# 仅作为主脚本运行时包装 stdout（被 update_daily import 时不包装，避免管道关闭）
if __name__ == '__main__':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

BASE = r"E:\财报解读\watchlist"
WATCHLIST = os.path.join(BASE, "watchlist.json")
ROUTE_CODE = "normalized_pe"
WINDOW_YEARS = 10
MIN_HISTORY = 8
THS_URL = "https://basic.10jqka.com.cn/{code}/finance.html"


def quantile(vals, q):
    vals = sorted(vals)
    idx = int(len(vals) * q)
    idx = max(0, min(len(vals) - 1, idx))
    return vals[idx]


def fetch_abstract(code: str) -> list:
    """同花顺财务摘要（按年度）：返回 [(year, roe, bps)]，按年份升序。"""
    import akshare as ak
    df = ak.stock_financial_abstract_ths(symbol=code, indicator="按年度")
    if df is None or df.empty:
        return []
    rows = []
    for _, r in df.iterrows():
        try:
            year = int(str(r["报告期"])[:4])
            roe = _num(str(r["净资产收益率"]).replace("%", ""))
            bps = _num(str(r["每股净资产"]))
        except (KeyError, TypeError, ValueError):
            continue
        if year is None or (roe is None and bps is None):
            continue
        rows.append((year, roe, bps))
    rows.sort(key=lambda x: x[0])
    return rows


def _num(s: str):
    s = s.strip().replace(",", "")
    if s in ("", "-", "--", "nan", "None", "—"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def main():
    with open(WATCHLIST, encoding="utf-8") as f:
        wl = json.load(f)

    changed = 0
    dirty = False
    for s in wl["stocks"]:
        vm = s.get("valuation_model")
        code = vm.get("code") if isinstance(vm, dict) else vm
        if code != ROUTE_CODE:
            continue
        ticker = s["ticker"]
        name = s.get("name", ticker)
        dirty = True
        try:
            rows = fetch_abstract(ticker)
        except Exception as e:
            _mark_failed(s, f"同花顺财务摘要抓取异常: {type(e).__name__}: {e}")
            print(f"{ticker} {name}: 正常化数据抓取失败（已标记）: {e}")
            continue
        if len(rows) < MIN_HISTORY:
            _mark_failed(s, f"年度ROE序列不足({len(rows)}<{MIN_HISTORY})，无法覆盖完整周期")
            print(f"{ticker} {name}: 年度ROE序列不足({len(rows)})，保持拦截")
            continue
        win = rows[-WINDOW_YEARS:]
        roes = [r[1] for r in win if r[1] is not None and r[1] == r[1]]
        if len(roes) < MIN_HISTORY:
            _mark_failed(s, f"有效ROE点数不足({len(roes)})")
            print(f"{ticker} {name}: 有效ROE点数不足({len(roes)})，保持拦截")
            continue
        p25, p50, p75 = quantile(roes, .25), quantile(roes, .50), quantile(roes, .75)
        latest = rows[-1]
        bps = latest[2]
        if bps is None or bps <= 0:
            _mark_failed(s, "最新每股净资产缺失或非正")
            print(f"{ticker} {name}: 每股净资产异常，保持拦截")
            continue
        if not (p25 > 0 and p50 > 0 and p75 > 0):
            _mark_failed(s, f"周期ROE分位含非正({p25}/{p50}/{p75})，亏损周期禁止套PE")
            print(f"{ticker} {name}: ROE分位含非正，保持拦截（亏损周期禁止套PE）")
            continue

        window_label = f"{win[0][0]}-{win[-1][0]}"
        eps_bear = round(p25 / 100 * bps, 4)
        eps_base = round(p50 / 100 * bps, 4)
        eps_bull = round(p75 / 100 * bps, 4)
        s["normalized"] = {
            "eps_bear": eps_bear,
            "eps_base": eps_base,
            "eps_bull": eps_bull,
            "roe_low": round(p25, 2), "roe_mid": round(p50, 2), "roe_high": round(p75, 2),
            "bps": round(bps, 4),
            "bps_as_of": str(latest[0]) + "-12-31",
            "hist_n": len(roes),
            "window": window_label,
            "formula": "正常化EPS = 周期ROE分位(P25/P50/P75) × 最新每股净资产",
            "source": {
                "id": f"ths-finance-normalized-{ticker}",
                "type": "normalized_earnings",
                "provider": "同花顺F10财务摘要",
                "title": f"{name} 年度ROE/BPS（{window_label}）",
                "url": THS_URL.format(code=ticker),
                "as_of": datetime.date.today().isoformat(),
                "retrieved_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
        }
        s["normalized_refresh"] = {"ok_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        changed += 1
        print(f"{ticker} {name}: 正常化EPS {eps_bear}/{eps_base}/{eps_bull}"
              f"（ROE {p25}/{p50}/{p75}% × BPS {bps}，窗口 {window_label}）")

    if dirty:
        with open(WATCHLIST, "w", encoding="utf-8") as f:
            json.dump(wl, f, ensure_ascii=False, indent=2)
    print(f"完成：{changed} 只周期股已写入正常化盈利参数")


def _mark_failed(s: dict, detail: str):
    s["normalized_refresh"] = {
        "failed_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "note": detail,
    }


if __name__ == "__main__":
    main()
