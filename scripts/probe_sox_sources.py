#!/usr/bin/env python3
"""Test-branch SOX numeric source check. Diagnostic only; never writes report data or JSON."""
from datetime import date, datetime, timedelta, timezone
import re
import sys
import requests

SESSION = date.fromisoformat(sys.argv[1]) if __name__ == "__main__" and len(sys.argv) > 1 else date.today()
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/%5ESOX"
FRED_URL = "https://fred.stlouisfed.org/data/NASDAQSOX"
INVESTING_URL = "https://ph.investing.com/indices/phlx-semiconductor-historical-data"
YCHARTS_URL = "https://ycharts.com/indices/%5ESOX/level"
CLOSELOOK_URL = "https://www.closelook.io/indices/stock/sox.indx/price-history"
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

def extract_investing_row(html, session):
    """Parse the exact-date historical row from Investing.com HTML when present."""
    flat = clean_html(html)
    month = session.strftime("%b")
    # Table order is Date, Price (close), Open, High, Low.
    pattern = (
        rf"\b{re.escape(month)}\s+{session.day},\s*{session.year}\s+"
        rf"([0-9,]+\.\d+)\s+([0-9,]+\.\d+)\s+"
        rf"([0-9,]+\.\d+)\s+([0-9,]+\.\d+)"
    )
    m = re.search(pattern, flat, re.I)
    if not m:
        return None
    values = [float(x.replace(",", "")) for x in m.groups()]
    close, open_, high, low = values
    return {"Open": open_, "High": high, "Low": low, "Close": close}


def extract_ycharts_row(html, session):
    """Parse YCharts public historical OHLC table for the exact session date."""
    flat = clean_html(html)
    month = session.strftime("%b")
    # YCharts table order is Date, Open, High, Low, Close.
    pattern = (
        rf"\b{re.escape(month)}\s+{session.day},\s*{session.year}\s+"
        rf"([0-9,]+\.\d+)\s+([0-9,]+\.\d+)\s+"
        rf"([0-9,]+\.\d+)\s+([0-9,]+\.\d+)"
    )
    m = re.search(pattern, flat, re.I)
    if not m:
        return None
    values = [float(x.replace(",", "")) for x in m.groups()]
    open_, high, low, close = values
    return {"Open": open_, "High": high, "Low": low, "Close": close}


def extract_closelook_row(html, session):
    """Parse Closelook public history table by ISO date, never a live snapshot."""
    flat = clean_html(html)
    pattern = (
        rf"\b{session.isoformat()}\s+"
        rf"([0-9,]+\.\d+)\s+([0-9,]+\.\d+)\s+"
        rf"([0-9,]+\.\d+)\s+([0-9,]+\.\d+)"
    )
    m = re.search(pattern, flat, re.I)
    if not m:
        return None
    values = [float(x.replace(",", "")) for x in m.groups()]
    open_, high, low, close = values
    return {"Open": open_, "High": high, "Low": low, "Close": close}


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

    # Independent public historical-table cross-check. Prefer Investing.com;
    # fall back to YCharts when Investing blocks automated requests (e.g. HTTP 403).
    secondary = None
    secondary_name = None
    try:
        r = s.get(INVESTING_URL, timeout=(5, 20))
        r.raise_for_status()
        secondary = extract_investing_row(r.text, SESSION)
        if secondary is None:
            print(f"INVESTING｜UNPARSEABLE｜HTTP={r.status_code}｜body_chars={len(r.text)}")
        else:
            secondary_name = "Investing.com"
            print(f"INVESTING｜PASS｜date={SESSION}｜O={secondary['Open']:.2f} H={secondary['High']:.2f} L={secondary['Low']:.2f} C={secondary['Close']:.2f}")
    except Exception as e:
        print(f"INVESTING｜UNAVAILABLE｜{type(e).__name__}: {e}")

    if secondary is None:
        try:
            r = s.get(YCHARTS_URL, timeout=(5, 20))
            r.raise_for_status()
            secondary = extract_ycharts_row(r.text, SESSION)
            if secondary is None:
                print(f"YCHARTS｜UNPARSEABLE｜HTTP={r.status_code}｜body_chars={len(r.text)}")
            else:
                secondary_name = "YCharts"
                print(f"YCHARTS｜PASS｜date={SESSION}｜O={secondary['Open']:.2f} H={secondary['High']:.2f} L={secondary['Low']:.2f} C={secondary['Close']:.2f}")
        except Exception as e:
            print(f"YCHARTS｜UNAVAILABLE｜{type(e).__name__}: {e}")

    if secondary is None:
        try:
            r = s.get(CLOSELOOK_URL, timeout=(5, 20))
            r.raise_for_status()
            secondary = extract_closelook_row(r.text, SESSION)
            if secondary is None:
                print(f"CLOSELOOK｜UNPARSEABLE｜HTTP={r.status_code}｜body_chars={len(r.text)}")
            else:
                secondary_name = "Closelook"
                print(f"CLOSELOOK｜PASS｜date={SESSION}｜O={secondary['Open']:.2f} H={secondary['High']:.2f} L={secondary['Low']:.2f} C={secondary['Close']:.2f}")
        except Exception as e:
            print(f"CLOSELOOK｜UNAVAILABLE｜{type(e).__name__}: {e}")

    if secondary is not None and yahoo is not None:
        for key in ("Open", "High", "Low", "Close"):
            if abs(secondary[key] - yahoo[key]) > TOLERANCE:
                failures.append(f"{secondary_name} {key} 與 Yahoo 不一致：{secondary[key]:.2f} vs {yahoo[key]:.2f}")

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
                # Live SEO snapshot is not a historical observation for SESSION.
                # Report the limitation but do not treat a wrong-date quote as
                # a conflicting same-session close.
                pass
            elif yahoo is not None and abs(close - yahoo["Close"]) > TOLERANCE:
                failures.append(f"{label} 收盤與 Yahoo 不一致：Nasdaq={close:.2f}, Yahoo={yahoo['Close']:.2f}")
        except Exception as e:
            print(f"NASDAQ｜{label}｜UNAVAILABLE｜{type(e).__name__}: {e}")

    current_official = [(n, d, c) for n, d, c in official_snapshots if d == SESSION]
    if not current_official:
        print("NASDAQ_HISTORY｜NO_PUBLIC_EXACT_DATE_SNAPSHOT｜公開頁面只解析到即時快照；歷史服務需要 GIW 權限，未計入第二來源")
    if len(current_official) >= 2:
        vals = [x[2] for x in current_official]
        if max(vals) - min(vals) > TOLERANCE:
            failures.append("Nasdaq 官方不同網址的收盤值互相不一致：" + str([(n, round(c, 2)) for n, d, c in current_official]))

    # Nasdaq's documented legacy historical endpoint is date-scoped. Probe it
    # separately from the live DATA AS OF snapshot; diagnostic only until its
    # schema and symbol identifier are validated across several sessions.
    history_url = "https://indexes.nasdaqomx.com/reports2/history.ashx"
    try:
        r = s.get(history_url, params={
            "IndexSymbol": "SOX",
            "StartDate": SESSION.isoformat(),
            "EndDate": SESSION.isoformat(),
            "Type": "csv",
            "FileType": "EOD",
        }, timeout=(5, 15))
        r.raise_for_status()
        body = r.text.strip()
        preview = re.sub(r"\\s+", " ", body)[:500]
        print(f"NASDAQ_HISTORY_API｜HTTP={r.status_code}｜bytes={len(r.content)}｜preview={preview}")
        if not body or len(body) < 20 or re.search(r"(?i)not found|invalid|error|unauthorized|exception", body[:1000]):
            print("NASDAQ_HISTORY_API｜NOT_VALIDATED｜回應內容不足或含錯誤訊號")
        else:
            print("NASDAQ_HISTORY_API｜RAW_RESPONSE_ONLY｜尚未驗證欄位與指定日期，不計入交叉驗收")
    except Exception as e:
        print(f"NASDAQ_HISTORY_API｜UNAVAILABLE｜{type(e).__name__}: {e}")

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

    independent_crosscheck = (
        yahoo is not None and secondary is not None and
        all(abs(secondary[k] - yahoo[k]) <= TOLERANCE for k in ("Open", "High", "Low", "Close"))
    )
    if not independent_crosscheck:
        failures.append("未能完成 Yahoo Finance 與第二公開歷史來源的指定日 OHLC 雙來源交叉驗證")

    if failures:
        print("FINAL｜FAIL｜不可將此日期 SOX 資料視為驗收通過")
        for issue in failures:
            print("REASON｜" + issue)
        sys.exit(1)
    print("FINAL｜PASS_WITH_LIMITATION｜Yahoo Finance 與第二公開歷史來源（Investing.com 優先，YCharts／Closelook 備援）指定日 OHLC 一致；Nasdaq 公開頁面未提供可驗證的同日歷史快照，官方歷史服務需 GIW 權限，故不宣稱 Nasdaq 官方交叉驗收通過。")

if __name__ == "__main__":
    main()
