# -*- coding: utf-8 -*-
"""股息率(TTM)每日刷新：腾讯行情快照 → watchlist.json。

用途（方法论升级 v2.1）：
  · 公式尺 payout 推导：payout ≈ 股息率 × PE(TTM)
  · 反向验证：现价隐含增长 vs 一致预期增速的输入之一

纪律：
  · 仅采集公开行情页快照数值，不做任何推算回填；失败保留旧值并留 refresh 标记
  · 只写结构化来源对象（provider/url/as_of/retrieved_at/method），质量标 C 级
    （行情快照级，非财报审计级）
  · 幂等：每次运行覆盖写入最新值；被 import 时不执行任何 I/O

用法：python fetch_dividend_yield.py
"""
import io
import json
import os
import sys
import time
import random
import datetime
import urllib.request

# 仅作为主脚本运行时包装 stdout（被 import 时不包装，避免管道关闭）
if __name__ == '__main__':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

BASE = r"E:\财报解读\watchlist"
WATCHLIST = os.path.join(BASE, "watchlist.json")
PE_ROUTES = {"forward_pe", "growth_pe"}
QT_URL = "https://qt.gtimg.cn/q="
FIELD_DIVIDEND_YIELD = 64   # 腾讯协议 v_ 序列第64位 = 股息率(TTM)，单位 %
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def _symbol_prefix(ticker: str) -> str | None:
    t = str(ticker)
    if t.startswith(("6", "9", "5")):
        return "sh" + t
    if t.startswith(("0", "2", "3")):
        return "sz" + t
    return None


def fetch_dividend_yield(ticker: str, timeout: float = 8.0) -> tuple:
    """返回 (value_pct, meta)。失败时 (None, 失败元数据)。"""
    sym = _symbol_prefix(ticker)
    if not sym:
        return None, {"source": "tencent-quote", "status": "skipped",
                      "error": f"无法识别交易所前缀 {ticker}"}
    url = QT_URL + sym
    retrieved_at = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        req = urllib.request.Request(url, headers=UA)
        raw = urllib.request.urlopen(req, timeout=timeout).read().decode("gbk", errors="replace")
        payload = raw.split("=", 1)[1].strip().strip('"').strip(";")
        fields = payload.split("~")
        val = float(fields[FIELD_DIVIDEND_YIELD])
        if not (0 <= val < 25):
            raise ValueError(f"股息率越界 {val}%")
        return val, {
            "source": "tencent-quote",
            "provider": "腾讯行情",
            "url": url,
            "method": "spot_snapshot_dividend_yield_ttm",
            "status": "ok",
            "stale": False,
            "as_of": datetime.date.today().isoformat(),
            "retrieved_at": retrieved_at,
        }
    except Exception as exc:
        return None, {
            "source": "tencent-quote",
            "provider": "腾讯行情",
            "url": url,
            "method": "spot_snapshot_dividend_yield_ttm",
            "status": "error",
            "stale": True,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "collected_at": retrieved_at,
        }


def main() -> int:
    """刷新所有 PE 路由股票的股息率。返回成功数。"""
    with open(WATCHLIST, encoding="utf-8") as f:
        wl = json.load(f)
    ok = 0
    for s in wl["stocks"]:
        vm = s.get("valuation_model")
        code = vm.get("code") if isinstance(vm, dict) else vm
        if code not in PE_ROUTES:
            continue
        ticker = s["ticker"]
        val, meta = fetch_dividend_yield(ticker)
        prev = s.get("dividend_yield_ttm") or {}
        if val is None:
            # 失败：保留旧值供参考，但标记本次刷新失败（引擎侧按缺尺跳过处理）
            s["dividend_yield_refresh"] = {
                "failed_at": meta.get("collected_at"),
                "note": f"今日抓取失败({meta.get('error')})，沿用旧值仅作参考",
            }
            print(f"{ticker} {s.get('name')}: 股息率抓取失败({meta.get('error')})"
                  + (f"，沿用旧值 {prev.get('value_pct')}%" if prev.get("value_pct") else ""))
        else:
            s["dividend_yield_ttm"] = {
                "value_pct": round(val, 3),
                "as_of": meta["as_of"],
                "retrieved_at": meta["retrieved_at"],
                "quality": "C",
                "source": {
                    "id": f"tencent-divyield-{ticker}",
                    "provider": meta["provider"],
                    "url": meta["url"],
                    "method": meta["method"],
                    "as_of": meta["as_of"],
                    "retrieved_at": meta["retrieved_at"],
                },
            }
            s["dividend_yield_refresh"] = None
            ok += 1
            print(f"{ticker} {s.get('name')}: 股息率(TTM) = {val:.2f}%")
        time.sleep(random.uniform(0.3, 0.6))

    with open(WATCHLIST, "w", encoding="utf-8") as f:
        json.dump(wl, f, ensure_ascii=False, indent=2)
    print(f"\n完成：{ok} 只股票股息率已更新")
    return ok


if __name__ == "__main__":
    main()
