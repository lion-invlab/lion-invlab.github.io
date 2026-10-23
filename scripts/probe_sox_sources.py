#!/usr/bin/env python3
"""Test-branch SOX numeric source check. Diagnostic only; never writes report data or JSON."""
from datetime import date, datetime, timedelta, timezone
import re
import sys
import requests

SESSION = date.fromisoformat(sys.argv[1]) if __name__ == "__main__" and len(sys.argv) > 1 else date.today()
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/%5ESOX"
FRED_URL = "https://fred.stlouisfed.org/data/NASDAQSOX"
NASDAQ_URLS = {
    "Nasdaq OMX overview": "https://indexes.nasdaqomx.com/Index/Overview/SOX",
    "Nasdaq indexes overview": "https://indexes.nasdaq.com/index/overview/SOX",
    "Nasdaq indexes history": "https://indexes.nasdaq.com/Index/History/SOX",
}
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; TACSourceProbe/3.0)"}
TOLERANCE = 0.02

def clean_html(value):
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def extract_nasdaq_snapshot(html):
    # The rendered SEO HTML commonly exposes a DATA AS OF snapshot. Treat it
    # only as a current snapshot; date must equal the requested session.
    flat = clean_html(html).replace(",", "")
    m = re.search(r"DATA AS OF\s*(\d{1,2}/\d{1,2}/\d{4})\s+([0-9]+\.\d{2})", flat, re.I)
    if not m:
        return None
    mm, dd, yyyy = map(int, m.group(1).split("/"))
    snapshot_date = date(yyyy, mm, dd)
    close = float(m.group(2))
    return snapshot_date, close

def main():
    print(f"SOX 指定交易日數值驗證｜date={SESSION}｜測試分支專用，不寫入正式早報/JSON")
    s = requests.Session()
    s.headers.update(HEADERS)
    failures = []
    yahoo = None

    # Primary machine-readable OHLC source.
    try:
        start = int(datetime.combine(SESSION, datetime.min.time(), tzinfo=timezone.utc).timestamp())
        end = start + 86400
        r = s.get(YAHOO_URL, params={"period1": start, "period2": end, "interval": "1d", "events": "history"}, timeout=(5, 20))
        r.raise_for_status()
        payload = r.json()
        items = payload.get("chart", {}).get("result")
        if not items:
            raise ValueError(payload.get("chart", {}).get("error") or "Yahoo chart 無資料")
        item = items[0]
        stamps = item.get("timestamp") or []
        quote = (item.get("indicators", {}).get("quote") or [{}])[0]
        idx = next((i for i, ts in enumerate(stamps) if datetime.fromtimestamp(ts, timezone.utc).date() == SESSION), None)
        if idx is None:
            raise ValueError("Yahoo 缺少指定交易日")
        yahoo = {k: (quote.get(k.lower()) or [None])[idx] for k in ("Open", "High", "Low", "Close")}
        if any(v is None for v in yahoo.values()):
            raise ValueError(f"OHLC 欄位缺漏：{yahoo}")
        yahoo = {k: float(v) for k, v in yahoo.items()}
        if yahoo["High"] < yahoo["Low"] or not yahoo["Low"] <= yahoo["Close"] <= yahoo["High"]:
            raise ValueError(f"OHLC 邏輯錯誤：{yahoo}")
        print(f"YAHOO_API｜PASS｜date={SESSION}｜O={yahoo['Open']:.2f} H={yahoo['High']:.2f} L={yahoo['Low']:.2f} C={yahoo['Close']:.2f}")
    except Exception as e:
        failures.append(f"Yahoo OHLC 來源失敗：{type(e).__name__}: {e}")
        print("YAHOO_API｜FAIL｜" + failures[-1])

    # Compare machine-readable Yahoo close against each parseable official
    # Nasdaq snapshot. Stale dates and variant disagreements are hard failures.
    official_snapshots = []
    for label, url in NASDAQ_URLS.items():
        try:
            r = s.get(url, timeout=(5, 15))
            r.raise_for_status()
            snapshot = extract_nasdaq_snapshot(r.text)
            if snapshot is None:
                print(f"NASDAQ｜{label}｜UNPARSEABLE｜HTTP={r.status_code}｜不可視為數值通過")
                continue
            snap_date, close = snapshot
            official_snapshots.append((label, snap_date, close))
            state = "CURRENT" if snap_date == SESSION else "STALE_OR_WRONG_DATE"
            print(f"NASDAQ｜{label}｜{state}｜date={snap_date}｜snapshot_close={close:.2f}")
            if snap_date != SESSION:
                failures.append(f"{label} 日期不符：頁面={snap_date}，要求={SESSION}")
            elif yahoo is not None and abs(close - yahoo["Close"]) > TOLERANCE:
                failures.append(f"{label} 收盤與 Yahoo 不一致：Nasdaq={close:.2f}, Yahoo={yahoo['Close']:.2f}")
        except Exception as e:
            print(f"NASDAQ｜{label}｜UNAVAILABLE｜{type(e).__name__}: {e}")

    current_official = [(n, d, c) for n, d, c in official_snapshots if d == SESSION]
    if not current_official:
        failures.append("沒有任何 Nasdaq 官方頁面成功解析出指定交易日快照")
    if len(current_official) >= 2:
        vals = [x[2] for x in current_official]
        if max(vals) - min(vals) > TOLERANCE:
            failures.append("Nasdaq 官方不同網址的收盤值互相不一致：" + str([(n, round(c, 2)) for n, d, c in current_official]))

    # FRED is diagnostic only because its publication can lag. Never require it
    # as the same-day second source and never count stale observations as passes.
    try:
        r = s.get(FRED_URL, timeout=(5, 15))
        r.raise_for_status()
        rows = re.findall(r"(?m)^\s*(\d{4}-\d{2}-\d{2})\s+([0-9]+(?:\.[0-9]+)?|\.)\s*$", r.text)
        valid = [(date.fromisoformat(d), float(v)) for d, v in rows if v != "."]
        latest = max(valid, default=None, key=lambda x: x[0])
        same_day = next((v for d, v in valid if d == SESSION), None)
        if same_day is None:
            print(f"FRED｜LAGGING_OR_UNAVAILABLE｜latest_valid_date={latest[0] if latest else 'unknown'}｜僅診斷，不計入驗收")
        else:
            print(f"FRED｜INFO｜date={SESSION}｜C={same_day:.2f}｜僅診斷，不作唯一判定")
            if yahoo is not None and abs(same_day - yahoo["Close"]) > TOLERANCE:
                print(f"FRED｜DIFFERS_FROM_YAHOO｜difference={abs(same_day-yahoo['Close']):.2f}｜需查明修訂/來源差異")
    except Exception as e:
        print(f"FRED｜DIAGNOSTIC_UNAVAILABLE｜{type(e).__name__}: {e}")

    if failures:
        print("FINAL｜FAIL｜不可將此日期 SOX 資料視為驗收通過")
        for issue in failures:
            print("REASON｜" + issue)
        sys.exit(1)
    print("FINAL｜PASS｜Yahoo 指定日 OHLC 合法，且至少一個 Nasdaq 官方頁面日期與收盤一致；其他官方頁面若無法解析會明確保留診斷狀態。")

if __name__ == "__main__":
    main()
