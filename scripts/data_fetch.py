# -*- coding: utf-8 -*-
"""行情数据层：腾讯主源 + akshare/新浪回退。

所有函数返回 (data, meta)；meta 含 source / collected_at / stale 标记。
失败时不抛异常，返回 (None, {stale: True, error: ...})，由上层决定保留旧值。
"""
import datetime
import hashlib
import html
import json
import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

CN_PREFIX = {"6": "sh", "9": "sh", "0": "sz", "3": "sz", "5": "sh", "1": "sz", "2": "sz", "4": "sz"}


def _code_tencent(symbol: str) -> str:
    """股票代码 → 腾讯格式 sh600085 / sz002384；ETF 515220 → sh，159xxx → sz"""
    p = CN_PREFIX.get(symbol[0], "sh")
    return p + symbol


def _code_sina(symbol: str) -> str:
    p = "sh" if symbol[0] in "69" else "sz"
    return p + symbol


def now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def fetch_spot(codes: list) -> tuple:
    """腾讯批量实时行情（16 只一次请求）。返回 {symbol: {...}} 与 meta。

    字段：name / price / pct / pe_ttm / total_mv / shares_亿 / pb / time
    """
    try:
        url = "http://qt.gtimg.cn/q=" + ",".join(_code_tencent(c) for c in codes)
        req = urllib.request.Request(url, headers=UA)
        raw = urllib.request.urlopen(req, timeout=15).read().decode("gbk", errors="ignore")
    except Exception as e:
        return None, {"source": "tencent", "stale": True, "error": str(e), "collected_at": now()}

    out = {}
    for line in raw.strip().split(";"):
        line = line.strip()
        if not line or "=" not in line or '"' not in line:
            continue
        sym = line.split("=")[0].split("_")[-1][2:]
        parts = line.split('"')[1].split("~")
        if len(parts) < 46:
            continue
        try:
            price = float(parts[3])
            total_mv = float(parts[45]) * 1e8  # 总市值（元，腾讯字段45单位为亿元）
            pe_raw = parts[39]
            pe = float(pe_raw) if pe_raw not in ("", "-", "--") else None
            pb_raw = parts[46]
            pb = float(pb_raw) if pb_raw not in ("", "-", "--") else None
            out[sym] = {
                "name": parts[1],
                "price": price,
                "pct": float(parts[32]) if parts[32] else 0.0,
                "pe_ttm": pe,
                "pb": pb,
                "total_mv": total_mv,
                "shares": round(total_mv / price / 1e8, 4) if price > 0 else None,  # 亿股
                "time": parts[30],
            }
        except (ValueError, IndexError):
            continue
    if not out:
        return None, {"source": "tencent", "stale": True, "error": "no rows", "collected_at": now()}
    return out, {"source": "tencent", "stale": False, "collected_at": now(), "n": len(out)}


def fetch_kline(symbol: str, days: int = 260) -> tuple:
    """260 日前复权日K。akshare 东财主源 → 新浪回退 → 腾讯回退。

    返回 [{d, o, c, h, l, v}] 按日期升序（v 单位：手/股 均可，相对比较）。
    """
    end = datetime.date.today()
    start = end - datetime.timedelta(days=int(days * 1.8) + 30)
    sd, ed = start.strftime("%Y%m%d"), end.strftime("%Y%m%d")

    # 1) akshare 东财
    try:
        import akshare as ak
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=sd, end_date=ed, adjust="qfq")
        if df is not None and not df.empty:
            rows = [{"d": str(r["日期"]), "o": float(r["开盘"]), "c": float(r["收盘"]),
                     "h": float(r["最高"]), "l": float(r["最低"]), "v": float(r["成交量"])}
                    for _, r in df.iterrows()]
            return rows[-days:], {"source": "ak-eastmoney", "stale": False, "collected_at": now()}
    except Exception:
        pass

    # 2) akshare 新浪
    try:
        import akshare as ak
        df = ak.stock_zh_a_daily(symbol=_code_sina(symbol), start_date=sd, end_date=ed, adjust="qfq")
        if df is not None and not df.empty:
            rows = [{"d": str(r["date"]), "o": float(r["open"]), "c": float(r["close"]),
                     "h": float(r["high"]), "l": float(r["low"]), "v": float(r["volume"])}
                    for _, r in df.iterrows()]
            return rows[-days:], {"source": "ak-sina", "stale": False, "collected_at": now()}
    except Exception:
        pass

    # 3) 腾讯日K（fqkline 接口）
    try:
        url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={_code_tencent(symbol)},day,,,{days * 2},qfq"
        req = urllib.request.Request(url, headers=UA)
        raw = urllib.request.urlopen(req, timeout=8).read().decode("utf-8", errors="ignore")
        import json
        data = json.loads(raw)
        node = data.get("data", {}).get(_code_tencent(symbol), {})
        klines = node.get("qfqday") or node.get("day") or []
        rows = []
        for k in klines:
            rows.append({"d": k[0], "o": float(k[1]), "c": float(k[2]), "h": float(k[3]),
                         "l": float(k[4]), "v": float(k[5])})
        if rows:
            return rows[-days:], {"source": "tencent-fqkline", "stale": False, "collected_at": now()}
    except Exception:
        pass

    return None, {"source": "all-failed", "stale": True, "error": "kline sources all failed", "collected_at": now()}


def fetch_csindex_indicator(symbol: str) -> tuple:
    """中证指数官方 indicator.xls 直采（akshare 该接口偶发 403，直采更稳）。

    返回 (df, meta)。df 列：日期/指数简称/指数名称全称/…/市盈率1(加权)/市盈率2(等权)。
    多 host 回退 + OLE2 魔数校验 + 重试。
    """
    import io as _io
    import time as _time
    import pandas as pd
    hosts = ["https://www.csindex.com.cn", "https://oss-ch.csindex.com.cn"]
    path = ("/static/html/csindex/public/uploads/file/autofile/"
            f"indicator/{symbol}indicator.xls")
    raw = None
    last_exc = None
    for host in hosts:
        for attempt in range(2):
            try:
                req = urllib.request.Request(host + path, headers={
                    **UA,
                    "Referer": "https://www.csindex.com.cn/",
                })
                resp = urllib.request.urlopen(req, timeout=30).read()
                if resp[:4] != b"\xd0\xcf\x11\xe0":  # OLE2 xls 魔数校验，拒绝 HTML 错误页
                    raise ValueError(f"{host} 返回非 xls 内容（前4字节 {resp[:4]!r}）")
                raw = resp
                break
            except Exception as e:
                last_exc = e
                _time.sleep(2 * (attempt + 1))
        if raw is not None:
            break
    if raw is None:
        return None, {"source": "csindex-direct", "stale": True,
                      "error": str(last_exc), "collected_at": now()}
    try:
        df = pd.read_excel(_io.BytesIO(raw))
        df.columns = [str(c) for c in df.columns]

        def _pick(sub):
            for c in df.columns:
                if sub in c:
                    return c
            return None

        c_date = _pick("日期") or _pick("Date")
        c_pe1 = _pick("市盈率1")
        c_pe2 = _pick("市盈率2")
        if not (c_date and c_pe1):
            raise ValueError("xls 缺少 日期/市盈率1 列")
        df = df[[c_date, c_pe1, c_pe2]].rename(columns={c_date: "日期", c_pe1: "市盈率1", c_pe2: "市盈率2"})
        df["日期"] = pd.to_datetime(df["日期"], errors="coerce").dt.date
        df["市盈率1"] = pd.to_numeric(df["市盈率1"], errors="coerce")
        df["市盈率2"] = pd.to_numeric(df["市盈率2"], errors="coerce")
    except Exception as e:
        return None, {"source": "csindex-direct", "stale": True,
                      "error": f"xls 解析失败: {e}", "collected_at": now()}
    return df, {"source": "csindex-direct", "stale": False, "collected_at": now()}


def fetch_csindex_pe(symbol: str = "000985") -> tuple:
    """中证指数公司官方 PE（加权 + 等权），返回最新一行与近 5 日。

    直采官方 indicator.xls 为主；失败回退 akshare；均失败返回 (None, meta)。
    """
    df, meta = fetch_csindex_indicator(symbol)
    if df is None or df.empty:
        try:
            import akshare as ak
            df = ak.stock_zh_index_value_csindex(symbol=symbol)
            meta = {"source": "csindex-akshare", "stale": False, "collected_at": now()}
        except Exception as e:
            return None, {"source": "csindex", "stale": True, "error": str(e), "collected_at": now()}
        if df is None or df.empty:
            return None, {"source": "csindex", "stale": True, "error": "empty", "collected_at": now()}
    df = df.dropna(subset=["市盈率1"]).sort_values("日期").tail(5)
    if df.empty:
        return None, {"source": "csindex", "stale": True, "error": "empty after dropna", "collected_at": now()}
    rows = [[str(r["日期"]), str(r["市盈率1"]), str(r["市盈率2"])] for _, r in df.iterrows()]
    latest = rows[-1]
    return {"date": latest[0], "pe_weighted": float(latest[1]), "pe_equal": float(latest[2]), "rows": rows}, \
           {**meta, "source": meta.get("source", "csindex")}


def fetch_bond_10y() -> tuple:
    """中债 10Y 收益率（小数，如 0.017114）。"""
    try:
        import akshare as ak
        df = ak.bond_zh_us_rate()
        col = [c for c in df.columns if "中国国债收益率10年" in str(c)]
        if not col or df.empty:
            return None, {"source": "chinabond", "stale": True, "error": "no col", "collected_at": now()}
        s = df[col[0]].dropna()
        val = float(s.iloc[-1]) / 100.0
        date = str(df.loc[s.index[-1], "日期"])
        return {"date": date, "value": val}, {"source": "chinabond-akshare", "stale": False, "collected_at": now()}
    except Exception as e:
        return None, {"source": "chinabond", "stale": True, "error": str(e), "collected_at": now()}


def fetch_trade_calendar() -> tuple:
    """交易日历（新浪）。失败时回退：周一~周五即视为交易日。"""
    try:
        import akshare as ak
        df = ak.tool_trade_date_hist_sina()
        days = set(df["trade_date"].astype(str))
        return days, {"source": "sina-calendar", "stale": False, "collected_at": now()}
    except Exception as e:
        return None, {"source": "fallback-weekday", "stale": True, "error": str(e), "collected_at": now()}


def _clean_html_cell(fragment: str) -> str:
    """把同花顺表格单元格变成可解析的纯文本。"""
    fragment = re.sub(r"<script\b.*?</script>", "", fragment, flags=re.I | re.S)
    fragment = re.sub(r"<style\b.*?</style>", "", fragment, flags=re.I | re.S)
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(fragment)).strip()


def _number(value: str):
    value = value.strip().replace(",", "")
    if value in ("", "-", "--", "—"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_ths_worth_html(text: str, symbol: str, url: str,
                         retrieved_at: str | None = None) -> dict:
    """解析同花顺 F10 个股 ``worth.html`` 的公开盈利预测表。

    只读取页面直接披露的数据：
    - ``yjycData`` 中标记为 ``SJ`` 的历史实际 EPS/净利润；
    - “汇总--预测年报每股收益”表中的年度、机构数、最小/均值/最大值。

    不使用行情价或 PE 反推 EPS，也不对缺失年度做插值。
    """
    if not re.fullmatch(r"\d{6}", str(symbol)):
        raise ValueError(f"非法股票代码: {symbol!r}")

    start = re.search(r"<div\b[^>]*\bid=[\"']forecast[\"'][^>]*>", text, re.I)
    end = re.search(r"<div\b[^>]*\bid=[\"']forecastdetail[\"'][^>]*>", text, re.I)
    if not start or not end or end.start() <= start.start():
        raise ValueError("页面缺少 forecast 区块")
    section = text[start.start():end.start()]

    as_of_match = re.search(r"截至\s*(\d{4}-\d{2}-\d{2})", section)
    as_of = as_of_match.group(1) if as_of_match else None

    forecasts = []
    table_blocks = re.findall(r"<table\b[^>]*>(.*?)</table>", section, re.I | re.S)
    for block in table_blocks:
        cap_match = re.search(r"<caption\b[^>]*>(.*?)</caption>", block, re.I | re.S)
        caption = _clean_html_cell(cap_match.group(1)) if cap_match else ""
        if "预测年报每股收益" not in caption:
            continue
        for tr in re.findall(r"<tr\b[^>]*>(.*?)</tr>", block, re.I | re.S):
            cells = [_clean_html_cell(x) for x in
                     re.findall(r"<t[hd]\b[^>]*>(.*?)</t[hd]>", tr, re.I | re.S)]
            if len(cells) < 5 or not re.fullmatch(r"20\d{2}", cells[0]):
                continue
            count = _number(cells[1])
            low, mean, high = (_number(cells[2]), _number(cells[3]), _number(cells[4]))
            if count is None or low is None or mean is None or high is None:
                continue
            forecasts.append({
                "year": int(cells[0]),
                "count": int(count),
                "min": low,
                "mean": mean,
                "max": high,
                "industry_mean": _number(cells[5]) if len(cells) > 5 else None,
                "metric": "diluted_eps",
                "unit": "CNY/share",
            })
        break

    actual_eps_history = []
    data_match = re.search(
        r"<div\b[^>]*\bid=[\"']yjycData[\"'][^>]*>(.*?)</div>",
        section, re.I | re.S)
    if data_match:
        try:
            rows = json.loads(html.unescape(data_match.group(1)).strip())
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError(f"yjycData JSON 解析失败: {exc}") from exc
        for row in rows:
            if not isinstance(row, list) or len(row) < 4 or str(row[3]).upper() != "SJ":
                continue
            eps, net_profit = _number(str(row[1])), _number(str(row[2]))
            if eps is None:
                continue
            actual_eps_history.append({
                "year": int(row[0]),
                "eps": eps,
                "net_profit": net_profit,
                "net_profit_unit": "CNY 100m",
                "kind": "actual",
            })

    title_match = re.search(r"<title>(.*?)</title>", text, re.I | re.S)
    title = _clean_html_cell(title_match.group(1)) if title_match else f"{symbol} 盈利预测"
    return {
        "schema_version": "ths-worth-forecast-v1",
        "symbol": str(symbol),
        "title": title,
        "provider": "同花顺F10",
        "url": url,
        "as_of": as_of,
        "retrieved_at": retrieved_at or now(),
        "forecasts": sorted(forecasts, key=lambda x: x["year"]),
        "actual_eps_history": sorted(actual_eps_history, key=lambda x: x["year"]),
        "source_note": "同花顺页面声明：预测数据根据各机构发布的研究报告摘录所得。",
    }


def fetch_ths_worth_forecast(symbol: str, timeout: int = 8) -> tuple:
    """抓取同花顺个股 worth 页面的一致预期与实际 EPS 历史。

    返回 ``(data, meta)``。失败时 ``data=None``，meta 保留 URL、异常类型、
    时间与状态；调用方可以保留上次成功数据，但不得把价格/PE 当作预测回退。
    """
    url = f"https://basic.10jqka.com.cn/{symbol}/worth.html"
    retrieved_at = now()
    try:
        req = urllib.request.Request(
            url,
            headers={**UA, "Referer": "https://basic.10jqka.com.cn/"},
        )
        raw = urllib.request.urlopen(req, timeout=timeout).read()
        text = raw.decode("gb18030", errors="replace")
        data = parse_ths_worth_html(text, symbol, url, retrieved_at)
        data["raw_sha256"] = hashlib.sha256(raw).hexdigest()
        if not data["forecasts"]:
            return data, {
                "source": "ths-worth",
                "provider": "同花顺F10",
                "source_url": url,
                "status": "no_consensus",
                "stale": False,
                "error": "页面可访问，但没有结构化一致预期 EPS 行",
                "collected_at": retrieved_at,
                "raw_sha256": data["raw_sha256"],
            }
        return data, {
            "source": "ths-worth",
            "provider": "同花顺F10",
            "source_url": url,
            "status": "ok",
            "stale": False,
            "collected_at": retrieved_at,
            "as_of": data.get("as_of"),
            "forecast_years": [x["year"] for x in data["forecasts"]],
            "raw_sha256": data["raw_sha256"],
        }
    except Exception as exc:
        return None, {
            "source": "ths-worth",
            "provider": "同花顺F10",
            "source_url": url,
            "status": "error",
            "stale": True,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "collected_at": retrieved_at,
        }


def fetch_profit_forecast(symbol: str) -> tuple:
    """兼容旧调用名；现返回同花顺结构化年度 EPS，而非净利润猜测。"""
    return fetch_ths_worth_forecast(symbol)
