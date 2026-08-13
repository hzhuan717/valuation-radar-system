# -*- coding: utf-8 -*-
"""PE/PB 历史分位补充器：百度股市通 5 年历史 → 当前分位 → 直接估值判断。

对所有股票给直接信号：
- 有 PE 且 PE>0：PE(TTM) 5年分位（<30% 低估可买 / 30~70% 持有观望 / >70% 高估观望）
- 亏损股（PE<=0）：PB 5年分位（同阈值）
- ETF：底层中证指数 PE 5年分位（官方序列缺失时标注观察，不显示空白）
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
STATE = os.path.join(BASE, "state.json")

import sys as _sys  # noqa: E402
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_fetch import fetch_csindex_indicator  # noqa: E402

# ETF → 底层跟踪指数（天天基金F10 跟踪标的核对）
# legu：乐咕乐股指数估值代码（TTM PE 全历史，主源）；csindex：中证官网（近20交易日，回退）
ETF_INDEX_MAP = {
    "515220": {"code": "000820", "name": "中证申万煤炭指数", "legu": "000820.CSI"},
    "159583": {"code": "931160", "name": "中证全指通信设备指数", "legu": "931160.CSI"},
    "159141": {"code": None, "name": "中证科创创业人工智能指数", "legu": None},
    "510210": {"code": "000001", "name": "上证综合指数", "legu": "000001.SH"},
    "159330": {"code": "000300", "name": "沪深300指数", "legu": "000300.SH"},
}


def fetch_legu_index_pe(legu_code: str) -> tuple:
    """乐咕乐股指数 TTM PE 全历史（公开站点接口，token=MD5(今日日期)）。

    字段口径：``addTtmPe`` = 滚动市盈率(TTM) 加权（与中证官网市盈率1 同口径），
    ``ttmPe`` = 等权平均，``middleTtmPe`` = 中位数。
    返回 [(date_str, addTtmPe), ...] 升序；失败抛异常。
    """
    import hashlib
    import http.cookiejar
    import urllib.request
    UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    tok = hashlib.md5(datetime.date.today().strftime("%Y-%m-%d").encode()).hexdigest()
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    page_url = f"https://legulegu.com/stockdata/index-ttm-lyr-pe?indexCode={legu_code}"
    op.open(urllib.request.Request(page_url, headers=UA), timeout=20)
    url = f"https://legulegu.com/api/stockdata/index-basic-pe?indexCode={legu_code}&token={tok}"
    raw = op.open(urllib.request.Request(url, headers={**UA, "Referer": page_url}),
                  timeout=25).read().decode("utf-8", errors="ignore")
    data = json.loads(raw).get("data") or []
    rows = []
    for r in data:
        try:
            pe = float(r.get("addTtmPe"))
        except (TypeError, ValueError):
            continue
        if pe and pe > 0:
            rows.append((str(r.get("date"))[:10], pe))
    rows.sort(key=lambda x: x[0])
    if len(rows) < 60:
        raise ValueError(f"乐咕乐股指数PE历史不足({len(rows)})")
    return rows, {"source": "legulegu-index", "n": len(rows)}


def fetch_baidu_hist(symbol: str, indicator: str, years: str = "近五年") -> tuple:
    try:
        import akshare as ak
        df = ak.stock_zh_valuation_baidu(symbol=symbol, indicator=indicator, period=years)
        if df is None or df.empty or "value" not in df.columns:
            return None, {"status": "error", "error": "empty"}
        df["value"] = df["value"].astype(float)
        return df, {"status": "ok", "n": len(df)}
    except Exception as e:
        return None, {"status": "error", "error": f"{type(e).__name__}: {e}"}


def percentile(sorted_vals, value):
    if not sorted_vals or value is None:
        return None
    less = sum(1 for v in sorted_vals if v < value)
    return less / len(sorted_vals)


def verdict(pct):
    if pct is None:
        return None, None, None
    if pct < 0.30:
        return "低估区", "低估可买", "green"
    if pct <= 0.70:
        return "合理区", "持有观望", "gold"
    return "高估区", "高估观望", "red"


def main():
    with open(STATE, encoding="utf-8") as f:
        st = json.load(f)
    stocks = st["stocks"]
    pe_stats = {}

    for code, s in stocks.items():
        name = s.get("name")
        pe_now = s.get("pe_ttm")
        # ETF：底层指数 PE 5 年分位（D级工程化参考；无官方序列时给观察信号）
        if code in ETF_INDEX_MAP:
            idx_meta = ETF_INDEX_MAP[code]
            idx_code, idx_name = idx_meta["code"], idx_meta["name"]
            idx_meta = ETF_INDEX_MAP[code]
            idx_code, idx_name, legu_code = idx_meta["code"], idx_meta["name"], idx_meta.get("legu")
            if not legu_code and not idx_code:
                stats = {
                    "ok": True,
                    "metric": "指数PE",
                    "pe": None, "pe_min": None, "pe_max": None, "pe_median": None,
                    "pctile": None,
                    "zone": "参考", "signal": "观察", "color": "gold",
                    "hist_n": None, "hist_last_date": None,
                    "source": f"跟踪指数：{idx_name}",
                    "note": "新指数尚无官方PE历史序列，仅观察（待补充）",
                }
                pe_stats[code] = stats
                print(f"{code} {name}: ETF观察 跟踪指数={idx_name}（官方PE序列暂缺）")
                continue
            stats = None
            # 1) 主源：乐咕乐股指数 TTM PE 全历史 → 5 年分位
            if legu_code:
                try:
                    rows, _meta = fetch_legu_index_pe(legu_code)
                    last_date = datetime.date.fromisoformat(rows[-1][0])
                    cut = last_date - datetime.timedelta(days=365 * 5)
                    win = [v for d, v in rows if datetime.date.fromisoformat(d) >= cut]
                    if len(win) < 30:
                        raise ValueError(f"指数PE 5年窗口不足({len(win)})")
                    pe_now = float(rows[-1][1])
                    hist = sorted(win)
                    pct = percentile(hist, pe_now)
                    zone, signal, color = verdict(pct)
                    stats = {
                        "ok": True,
                        "metric": "指数PE",
                        "pe": round(pe_now, 2),
                        "pe_min": round(min(hist), 2),
                        "pe_max": round(max(hist), 2),
                        "pe_median": round(sorted(hist)[len(hist) // 2], 2),
                        "pctile": round(pct, 4) if pct is not None else None,
                        "zone": zone, "signal": signal, "color": color,
                        "hist_n": len(hist),
                        "hist_last_date": str(last_date),
                        "source": f"乐咕乐股指数估值·{idx_name}",
                        "collected_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "note": "ETF按底层指数TTM PE 5年历史分位参考（D级工程化，非公开方法公式）",
                    }
                except Exception as e:
                    print(f"{code} {name}: 乐咕乐股指数PE失败({type(e).__name__}: {e})，回退中证官网")
            # 2) 回退：中证官网近20交易日 PE（无5年分位，仅指数参考）
            if stats is None and idx_code:
                try:
                    df, _meta = fetch_csindex_indicator(idx_code)
                    if df is None or df.empty:
                        raise ValueError("指数PE序列为空")
                    df = df.dropna(subset=["市盈率1"]).sort_values("日期")
                    pe_now = float(df["市盈率1"].iloc[-1])
                    hist = df["市盈率1"].astype(float).tolist()
                    stats = {
                        "ok": True,
                        "metric": "指数PE",
                        "pe": round(pe_now, 2),
                        "pe_min": round(min(hist), 2),
                        "pe_max": round(max(hist), 2),
                        "pe_median": round(sorted(hist)[len(hist) // 2], 2),
                        "pctile": None,
                        "zone": "参考", "signal": "指数参考", "color": "blue",
                        "hist_n": len(hist),
                        "hist_last_date": str(df["日期"].max()),
                        "source": f"中证指数官方·{idx_name}({idx_code})",
                        "collected_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "note": "官方序列仅近20交易日窗口，无5年分位，仅指数参考",
                    }
                except Exception as e:
                    print(f"{code} {name}: 中证官网回退失败({type(e).__name__}: {e})")
            # 3) 全部失败 → 观察
            if stats is None:
                stats = {
                    "ok": True,
                    "metric": "指数PE",
                    "pe": None, "pe_min": None, "pe_max": None, "pe_median": None,
                    "pctile": None,
                    "zone": "参考", "signal": "观察", "color": "gold",
                    "hist_n": None, "hist_last_date": None,
                    "source": f"跟踪指数：{idx_name}",
                    "note": "指数PE序列暂时无法访问，观察；每日流水线自动重试",
                }
            pe_stats[code] = stats
            print(f"{code} {name}: ETF参考 指数PE={stats.get('pe')} 分位={None if stats.get('pctile') is None else round(stats['pctile']*100)}% -> {stats.get('signal')}")
            continue

        # 亏损股 → PB 分位
        if pe_now is not None and pe_now <= 0:
            df, meta = fetch_baidu_hist(code, "市净率")
            if df is None:
                pe_stats[code] = {"ok": False, "error": meta.get("error", "?"), "pe": pe_now}
                print(f"{code} {name}: PB 爬取失败 -> {meta.get('error','?')}")
                continue
            hist = sorted(df["value"].dropna().tolist())
            pb_now = s.get("pb")
            pct = percentile(hist, pb_now)
            zone, signal, color = verdict(pct)
            stats = {
                "ok": True,
                "metric": "PB",
                "pe": pb_now,
                "pe_min": round(hist[0], 2),
                "pe_max": round(hist[-1], 2),
                "pe_median": round(sorted(hist)[len(hist) // 2], 2),
                "pctile": round(pct, 4) if pct is not None else None,
                "zone": zone,
                "signal": signal,
                "color": color,
                "hist_n": len(hist),
                "hist_last_date": str(df["date"].iloc[-1]),
                "source": "百度股市通历史PB",
                "collected_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "note": "亏损股以 PB 替代 PE 分位",
            }
            pe_stats[code] = stats
            print(f"{code} {name}: 亏损股PB={pb_now} 5Y分位={pct*100:.0f}% -> {signal}")
            continue

        # 正常 → PE 分位
        df, meta = fetch_baidu_hist(code, "市盈率(TTM)")
        if df is None:
            pe_stats[code] = {"ok": False, "error": meta.get("error", "?"), "pe": pe_now}
            print(f"{code} {name}: PE 爬取失败 -> {meta.get('error','?')}")
            continue
        hist = sorted(df["value"].dropna().tolist())
        if pe_now is None:
            pe_now = float(df["value"].iloc[-1])
        pct = percentile(hist, pe_now)
        zone, signal, color = verdict(pct)
        stats = {
            "ok": True,
            "metric": "PE",
            "pe": round(pe_now, 2),
            "pe_min": round(hist[0], 2),
            "pe_max": round(hist[-1], 2),
            "pe_median": round(sorted(hist)[len(hist) // 2], 2),
            "pctile": round(pct, 4) if pct is not None else None,
            "zone": zone,
            "signal": signal,
            "color": color,
            "hist_n": len(hist),
            "hist_last_date": str(df["date"].iloc[-1]),
            "source": "百度股市通历史PE(TTM)",
            "collected_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        pe_stats[code] = stats
        print(f"{code} {name}: PE={pe_now} 5Y分位={pct*100:.0f}% -> {signal}")

    st["pe_history"] = pe_stats
    st["meta"]["pe_history_updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)
    print("\n已写入 state.json 的 pe_history 字段")


if __name__ == "__main__":
    main()
