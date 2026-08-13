# -*- coding: utf-8 -*-
"""中国平安保险专项估值数据抓取器（东财F10）→ 写入 watchlist.json 配置

目标：为 insurance_pev 路由提供 EV/NBV/P/EV 三件套。
数据源：东财 F10 ZYZBAjaxNew type=1：
  · NHJZ_CURRENT_AMT  内含价值当期金额（元）
  · NBV_LIFE          新业务价值（元）
  · NBV_RATE          新业务价值率（%）
  · SOLVENCY_AR       偿付能力充足率（%）
  · BPS/EPS           每股净资产/每股收益
  · REPORT_DATE       报告期（每年12-31为年报 EV，as_of 用年报日）

P/EV 倍数档位（D级工程参数，按保险股行业惯例，需敏感性）：
  pev_low=0.6  买入启动区（P/EV<0.6 显著低估）
  pev_mid=0.9  价值中枢
  pev_high=1.2 卖出启动区
"""
import io
import json
import os
import sys
import datetime
import urllib.request

# 仅作为主脚本运行时包装 stdout（被 update_daily import 时不包装，避免管道关闭）
if __name__ == '__main__':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

BASE = r"E:\财报解读\watchlist"
WATCHLIST = os.path.join(BASE, "watchlist.json")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

SYMBOL = "601318"
PEV_LOW, PEV_MID, PEV_HIGH = 0.6, 0.9, 1.2
EM_URL = (f"https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/"
          f"ZYZBAjaxNew?type=1&code=SH{SYMBOL}")


def fetch_em_f10() -> list:
    req = urllib.request.Request(EM_URL, headers=UA)
    raw = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", errors="ignore")
    return json.loads(raw).get("data", [])


def fetch_quote() -> tuple:
    req = urllib.request.Request("http://qt.gtimg.cn/q=sh601318", headers=UA)
    raw = urllib.request.urlopen(req, timeout=10).read().decode("gbk", errors="ignore")
    parts = raw.split('"')[1].split("~")
    return float(parts[3]), float(parts[45])


def _mark_refresh_failed(detail: str):
    """EV 刷新失败时在配置里标记 failed_at；引擎据此硬停止（fail-closed）。"""
    try:
        with open(WATCHLIST, encoding="utf-8") as f:
            wl = json.load(f)
        for s in wl["stocks"]:
            if s["ticker"] == SYMBOL:
                s["ev_refresh"] = {
                    "failed_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "note": detail,
                }
                break
        with open(WATCHLIST, "w", encoding="utf-8") as f:
            json.dump(wl, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def main():
    try:
        rows = fetch_em_f10()
    except Exception as e:
        rows = None
        _mark_refresh_failed(f"东财F10抓取异常: {type(e).__name__}: {e}")
        print(f"东财 F10 抓取失败（已标记 ev_refresh 失败）: {e}")
        return
    if not rows:
        _mark_refresh_failed("东财F10返回空数据")
        print("东财 F10 抓取失败：无数据（已标记 ev_refresh 失败）")
        return

    # 取最近年报（12-31）与全部年报序列
    yearly = [r for r in rows if str(r.get("REPORT_DATE", "")).split(" ")[0].endswith("12-31")]
    yearly.sort(key=lambda r: str(r.get("REPORT_DATE", "")))
    if not yearly:
        print("无年报数据")
        return
    latest = yearly[-1]
    ev_yuan = latest.get("NHJZ_CURRENT_AMT")
    if not ev_yuan:
        print(f"最新年报 {latest.get('REPORT_DATE','')[:10]} 无内含价值字段")
        return

    price, total_mv_yi = fetch_quote()
    shares_yi = total_mv_yi / price
    ev_per_share = round(ev_yuan / shares_yi / 1e8, 3)
    pev_now = round(price / ev_per_share, 3)
    ev_as_of = str(latest.get("REPORT_DATE", ""))[:10]
    nbv = {str(r.get("REPORT_DATE", ""))[:4]: r.get("NBV_LIFE")
           for r in yearly if r.get("NBV_LIFE")}
    ev_as_of_date = ev_as_of

    cfg = {
        "ev_per_share": ev_per_share,
        "ev_as_of": ev_as_of,
        "ev_source": {
            "id": f"em-f10-ev-{SYMBOL}",
            "type": "insurance_ev",
            "provider": "东方财富F10",
            "title": f"中国平安{ev_as_of}年报内含价值",
            "url": EM_URL,
            "as_of": ev_as_of,
            "retrieved_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "pev_low": PEV_LOW, "pev_mid": PEV_MID, "pev_high": PEV_HIGH,
        "pev_method": "行业惯例区间（0.6/0.9/1.2），D级工程参数，需敏感性",
        "pev_source": {"quality": "D", "method": "industry_practice"},
        "nbv": nbv,
        "pev_now": pev_now,
        "ev_refresh": {"ok_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
        "price_check": {"price": price, "total_mv_yi": total_mv_yi,
                        "shares_yi": round(shares_yi, 2)},
    }

    with open(WATCHLIST, encoding="utf-8") as f:
        wl = json.load(f)
    for s in wl["stocks"]:
        if s["ticker"] == SYMBOL:
            vm = s.get("valuation_model")
            vm_code = vm.get("code") if isinstance(vm, dict) else vm
            if vm_code != "insurance_pev":
                print(f"警告：{SYMBOL} valuation_model 不是 insurance_pev，跳过写入")
                return
            for k, v in cfg.items():
                s[k] = v
            print(f"{SYMBOL} 已更新：每股EV={ev_per_share}（{ev_as_of}）P/EV={pev_now} "
                  f"股价={price} 总股本={shares_yi:.2f}亿股 NBV年报数={len(nbv)}")
            break
    else:
        print(f"{SYMBOL} 不在 watchlist")
        return

    with open(WATCHLIST, "w", encoding="utf-8") as f:
        json.dump(wl, f, ensure_ascii=False, indent=2)
    print("watchlist.json 已写")


if __name__ == "__main__":
    main()
