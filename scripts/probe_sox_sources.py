#!/usr/bin/env python3
"""Numeric SOX source check. Diagnostic/test branch only; never writes report data or JSON."""
from datetime import date, datetime, timedelta, timezone
import re
import sys
import requests

SESSION = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/%5ESOX"
FRED_URL = "https://fred.stlouisfed.org/data/NASDAQSOX"
NASDAQ_URLS = {
    "Nasdaq OMX overview": "https://indexes.nasdaqomx.com/Index/Overview/SOX",
    "Nasdaq indexes overview": "https://indexes.nasdaq.com/index/overview/SOX",
    "Nasdaq indexes history": "https://indexes.nasdaq.com/Index/History/SOX",
}
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; TACSourceProbe/2.0)"}

def num(value):
    return float(value) if value is not None else None

def main():
    print(f"SOX 數值來源交叉驗證｜指定交易日={SESSION.isoformat()}｜僅測試，不寫入正式早報/JSON")
    s = requests.Session()
    s.headers.update(HEADERS)
    errors = []
    yahoo = None
    fred_close = None

    # Yahoo's dated chart endpoint gives machine-readable daily OHLC.
    try:
        start = int(datetime.combine(SESSION, datetime.min.time(), tzinfo=timezone.utc).timestamp())
        end = int((datetime.combine(SESSION, datetime.min.time(), tzinfo=timezone.utc) + timedelta(days=1)).timestamp())
        r = s.get(YAHOO_URL, params={"period1": start, "period2": end, "interval": "1d", "events": "history"}, timeout=(5, 20))
        r.raise_for_status()
        payload = r.json()
        result = payload.get("chart", {}).get("result")
        if not result:
            raise ValueError(payload.get("chart", {}).get("error") or "Yahoo chart 沒有回傳資料")
        item = result[0]
        stamps = item.get("timestamp") or []
        quotes = (item.get("indicators", {}).get("quote") or [{}])[0]
        match = next((i for i, ts in enumerate(stamps)
                      if datetime.fromtimestamp(ts, timezone.utc).date() == SESSION), None)
        if match is None:
            raise ValueError("Yahoo chart 缺少指定交易日資料")
        yahoo = {k: num((quotes.get(k.lower()) or [])[match]) for k in ("Open", "High", "Low", "Close")}
        if any(v is None for v in yahoo.values()):
            raise ValueError(f"Yahoo OHLC 欄位缺漏：{yahoo}")
        if yahoo["High"] < yahoo["Low"] or not yahoo["Low"] <= yahoo["Close"] <= yahoo["High"]:
            raise ValueError(f"Yahoo OHLC 邏輯錯誤：{yahoo}")
        print(f"YAHOO_API｜PASS｜date={SESSION}｜O={yahoo['Open']:.2f} H={yahoo['High']:.2f} L={yahoo['Low']:.2f} C={yahoo['Close']:.2f}")
    except Exception as e:
        errors.append(f"Yahoo chart API: {type(e).__name__}: {e}")
        print(f"YAHOO_API｜FAIL｜{errors[-1]}")

    # FRED published daily series is a second close-only cross-check. It can lag;
    # stale/missing target dates are explicitly reported, never treated as current.
    try:
        r = s.get(FRED_URL, timeout=(5, 20))
        r.raise_for_status()
        rows = re.findall(r"(?m)^\s*(\d{4}-\d{2}-\d{2})\s+([0-9]+(?:\.[0-9]+)?|\.)\s*$", r.text)
        row = next((value for day, value in rows if day == SESSION.isoformat()), None)
        if row is None or row == ".":
            latest_valid = next(((day, value) for day, value in reversed(rows) if value != "."), None)
            if latest_valid:
                raise ValueError(f"FRED 尚無指定交易日資料；該序列最新有效列={latest_valid[0]}:{latest_valid[1]}（視為延遲，不可當第二來源）")
            raise ValueError("FRED 沒有可用的有效收盤列")
        fred_close = float(row)
        print(f"FRED｜PASS｜date={SESSION}｜C={fred_close:.2f}")
    except Exception as e:
        errors.append(f"FRED series: {type(e).__name__}: {e}")
        print(f"FRED｜FAIL｜{errors[-1]}")

    # Official pages are checked for availability and visible date/value clues.
    # Their page markup can be client-rendered; do not claim numeric validation
    # when the raw page does not expose parseable structured values.
    official_reachable = 0
    official_unparsed = 0
    for label, url in NASDAQ_URLS.items():
        try:
            r = s.get(url, timeout=(5, 15))
            r.raise_for_status()
            official_reachable += 1
            html = re.sub(r"\s+", " ", r.text)
            date_hit = SESSION.strftime("%m/%d/%Y") in html or SESSION.isoformat() in html or SESSION.strftime("%b %d, %Y") in html
            # Only report values with an explicit nearby close label; avoid
            # treating arbitrary numbers elsewhere on a page as the close.
            close_hit = bool(re.search(r"(?:close|index value)[^0-9]{0,100}[0-9,]+\.\d{2}", html, re.I))
            if not (date_hit and close_hit):
                official_unparsed += 1
            print(f"NASDAQ_OFFICIAL｜{label}｜HTTP=200｜target_date_visible={date_hit}｜labelled_close_pattern={close_hit}｜bytes={len(r.content)}")
        except Exception as e:
            print(f"NASDAQ_OFFICIAL｜{label}｜UNAVAILABLE｜{type(e).__name__}: {e}")

    if yahoo and fred_close is not None:
        diff = abs(yahoo["Close"] - fred_close)
        print(f"CROSS_CHECK｜Yahoo vs FRED close difference={diff:.2f}")
        if diff > 0.02:
            errors.append(f"Yahoo/FRED 收盤不一致：Yahoo={yahoo['Close']:.2f}, FRED={fred_close:.2f}")
    else:
        errors.append("無法同時取得 Yahoo OHLC 與 FRED 收盤，不能完成雙來源數值驗證")

    print(f"OFFICIAL_PAGE_STATUS｜reachable={official_reachable}/{len(NASDAQ_URLS)}｜raw_html_unparsed={official_unparsed}")
    print("驗收規則｜只有 Yahoo 指定日 OHLC 完整且與 FRED 同日收盤差距 <= 0.02 才能 PASS；FRED 延遲或官方頁無法解析均不得假裝完成獨立來源交叉驗證。")
    if official_unparsed:
        print("OFFICIAL_PAGE_NOTE｜官方頁面原始 HTML 未完整暴露可驗證的日期/收盤欄位；HTTP 200 不等於數值驗證通過。")
    if errors:
        print("FINAL｜FAIL｜來源驗收未完成；不可將本次測試視為正式行情通過。")
        for e in errors:
            print("REASON｜" + e)
        sys.exit(1)
    print("FINAL｜PASS｜Yahoo OHLC 與 FRED 收盤在指定交易日一致；Nasdaq 頁面可解析性另列，不以 HTTP 成功冒充數值驗收。")

if __name__ == "__main__":
    main()
