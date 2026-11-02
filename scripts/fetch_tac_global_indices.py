#!/usr/bin/env python3
"""Fetch the 17 fixed TAC global indices from their Investing.com HK history pages.

Live retrieval is available for the user's private TAC research workflow.
Only exact requested trading-date rows are accepted; stale closes are never reused.
This collector does not publish data independently; it writes a dated source fragment
for downstream validation and private report assembly.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SOURCE_ROOT = "https://hk.investing.com/indices/"
KEY_LEVEL_INDEXES = ("dow", "sp500", "nasdaq_composite", "sox", "russell_2000")
INDEXES = {
    "dow": ("us-30", "DJI", "道瓊"),
    "sp500": ("us-spx-500", "SPX", "標普"),
    "nasdaq_composite": ("nasdaq-composite", "IXIC", "納斯達克"),
    "russell_2000": ("smallcap-2000", "RUT", "小型股"),
    "sox": ("phlx-semiconductor", "SOX", "半導體"),
    "hang_seng": ("hang-sen-40", "HSI", "恒生"),
    "shanghai_composite": ("shanghai-composite", "SSEC", "上證"),
    "shenzhen_component": ("szse-component", "SZI", "深證"),
    "nikkei_225": ("japan-ni225", "N225", "日經"),
    "kospi": ("kospi", "KS11", "KOSPI"),
    "twse": ("taiwan-weighted", "TWII", "台灣加權"),
    "singapore_sti": ("singapore-straits-time", "STI", "海峽時報"),
    "asx_200": ("aus-200", "AXJO", "ASX"),
    "ftse_100": ("uk-100", "FTSE", "富時100"),
    "dax": ("germany-30", "GDAXI", "DAX"),
    "cac_40": ("france-40", "FCHI", "CAC"),
    "stoxx_europe_600": ("stoxx-600", "STOXX", "STOXX"),
}

def parse_number(raw: str) -> float:
    value = (raw or "").strip().replace(",", "").replace("%", "")
    value = value.replace("−", "-").replace("＋", "+").replace("－", "-")
    if value in {"", "-", "—", "–", "N/A", "NA"}:
        raise ValueError("missing numeric cell")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("non-finite numeric cell")
    return number

def parse_date(raw: str) -> date:
    value = " ".join((raw or "").split())
    match = re.search(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", value)
    if match:
        return date(*(int(part) for part in match.groups()))
    match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", value)
    if match:
        return date(*(int(part) for part in match.groups()))
    for fmt in ("%d/%m/%Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise ValueError("unrecognized historical date: " + value)

def normalized_header(value: str) -> str:
    return re.sub(r"[\s（）()%％]", "", value).lower()

def parse_history_page(html: str, ticker: str, trading_date: date) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find("h1")
    heading_text = heading.get_text(" ", strip=True) if heading else ""
    if ticker.lower() not in heading_text.lower():
        raise ValueError(f"instrument identity mismatch: expected {ticker}, heading={heading_text!r}")

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        header_cells = rows[0].find_all(["th", "td"])
        headers = [normalized_header(cell.get_text(" ", strip=True)) for cell in header_cells]
        date_i = next((i for i, h in enumerate(headers) if "日期" in h or h == "date"), None)
        close_i = next((i for i, h in enumerate(headers) if "收市" in h or "收盤" in h or h == "close"), None)
        change_i = next((i for i, h in enumerate(headers) if ("升跌" in h or "change" in h) and ("%" in h or "percent" in h or "升跌" in h)), None)
        open_i = next((i for i, h in enumerate(headers) if "開市" in h or "開盤" in h or h == "open"), None)
        high_i = next((i for i, h in enumerate(headers) if h in {"高", "high"} or "最高" in h), None)
        low_i = next((i for i, h in enumerate(headers) if h in {"低", "low"} or "最低" in h), None)
        if date_i is None or close_i is None or change_i is None:
            continue
        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if max(date_i, close_i, change_i) >= len(cells):
                continue
            try:
                row_date = parse_date(cells[date_i].get_text(" ", strip=True))
            except ValueError:
                continue
            if row_date != trading_date:
                continue
            close = parse_number(cells[close_i].get_text(" ", strip=True))
            change_pct = parse_number(cells[change_i].get_text(" ", strip=True))
            if close <= 0:
                raise ValueError("historical close must be positive")
            ohlc = None
            ohlc_error = "OHLC columns missing from the historical table"
            if None not in (open_i, high_i, low_i) and max(open_i, high_i, low_i) < len(cells):
                try:
                    open_value = parse_number(cells[open_i].get_text(" ", strip=True))
                    high_value = parse_number(cells[high_i].get_text(" ", strip=True))
                    low_value = parse_number(cells[low_i].get_text(" ", strip=True))
                    if (min(open_value, high_value, low_value) <= 0
                            or high_value < max(open_value, close)
                            or low_value > min(open_value, close)
                            or high_value < low_value):
                        raise ValueError("OHLC range is internally inconsistent")
                    ohlc = {"open": open_value, "high": high_value,
                            "low": low_value, "close": close}
                    ohlc_error = None
                except ValueError as exc:
                    ohlc_error = str(exc)
            return {"close": close, "change_pct": change_pct, "heading": heading_text,
                    "ohlc": ohlc, "ohlc_error": ohlc_error}
    raise ValueError(f"exact trading-date row {trading_date.isoformat()} not found")

def make_pending(observed_at: str, trading_date: date, reason: str) -> dict:
    return {
        "value": None, "unit": "index_point", "change": None,
        "change_unit": "percent", "status": "pending_verification",
        "source": None, "fallback_used": False, "fallback_reason": None,
        "notes": f"未取得指定交易日資料，未沿用舊值。原因：{reason}",
        "ohlc": None, "ohlc_error": reason,
    }

def fetch_one(session: requests.Session, key: str, config: tuple,
              trading_date: date, observed_at: str) -> tuple[str, dict]:
    slug, ticker, label_hint = config
    url = f"{SOURCE_ROOT}{slug}-historical-data"
    try:
        response = session.get(url, timeout=(10, 30))
        response.raise_for_status()
        if len(response.text) < 5000:
            raise ValueError("response unexpectedly short")
        parsed = parse_history_page(response.text, ticker, trading_date)
        return key, {
            "value": parsed["close"], "unit": "index_point",
            "change": parsed["change_pct"], "change_unit": "percent",
            "ohlc": parsed.get("ohlc"), "ohlc_error": parsed.get("ohlc_error"),
            "status": "verified",
            "source": {
                "name": "Investing.com 香港站",
                "url": url, "observed_at": observed_at,
                "data_date": trading_date.isoformat(),
                "quote_type": "investing_com_hk_historical_close_pct_change",
                "instrument": f"{label_hint} ({ticker})",
            },
            "fallback_used": False, "fallback_reason": None,
            "notes": "採用歷史資料表指定交易日的收市價及日升跌幅；僅接受完全相符的資料日期。",
        }
    except Exception as exc:
        return key, make_pending(observed_at, trading_date, str(exc))

def build_fragment(trading_date: date, report_date: date, records: dict,
                   observed_at: str) -> dict:
    if set(records) != set(INDEXES):
        missing = sorted(set(INDEXES) - set(records))
        extra = sorted(set(records) - set(INDEXES))
        raise ValueError(f"global index field mismatch; missing={missing}, extra={extra}")
    global_records = {}
    key_level_records = {}
    for key, item in records.items():
        record = dict(item)
        ohlc = record.pop("ohlc", None)
        ohlc_error = record.pop("ohlc_error", None)
        global_records[key] = record
        if key in KEY_LEVEL_INDEXES:
            verified = record.get("status") == "verified" and isinstance(ohlc, dict)
            key_level_records[key] = {
                "status": "verified" if verified else "pending_verification",
                "ohlc": ohlc if verified else None,
                "source": record.get("source"),
                "notes": "同日 OHLC 已核實" if verified else (ohlc_error or record.get("notes")),
            }
    return {
        "fragment_schema_version": 1,
        "dataset": "tac_global_indices",
        "report_date": report_date.isoformat(),
        "trading_date": trading_date.isoformat(),
        "fetched_at": observed_at,
        "source_priority": "Investing.com Hong Kong historical data pages per TAC_WORK_RULES.md §21.2",
        "global_indices": global_records,
        "key_levels": {
            "report_date": report_date.isoformat(),
            "trading_date": trading_date.isoformat(),
            "fetched_at": observed_at,
            "method": "classic_pivot_p=(H+L+C)/3_s1=2P-H_r1=2P-L",
            "indices": key_level_records,
        },
    }

def self_test() -> None:
    sample = """<html><h1>道瓊斯工業平均指數 (DJI)</h1>
    <table><thead><tr><th>日期</th><th>收市</th><th>開市</th><th>高</th><th>低</th><th>升跌（%）</th></tr></thead>
    <tbody><tr><td>2026年10月30日</td><td>51,770.31</td><td>52,383.90</td><td>52,383.90</td><td>51,563.76</td><td>-1.09%</td></tr></tbody></table></html>"""
    parsed = parse_history_page(sample, "DJI", date(2026, 10, 30))
    assert parsed["close"] == 51770.31
    assert parsed["change_pct"] == -1.09
    assert parsed["ohlc"] == {
        "open": 52383.90, "high": 52383.90,
        "low": 51563.76, "close": 51770.31,
    }
    assert parsed["ohlc_error"] is None
    try:
        parse_history_page(sample, "IXIC", date(2026, 10, 30))
    except ValueError:
        pass
    else:
        raise AssertionError("instrument mismatch must fail closed")
    try:
        parse_history_page(sample, "DJI", date(2026, 10, 31))
    except ValueError:
        pass
    else:
        raise AssertionError("missing requested trading date must fail closed")
    assert len(INDEXES) == 17 and len({v[0] for v in INDEXES.values()}) == 17
    assert parse_date("2026年10月30日") == date(2026, 10, 30)
    assert parse_number("−1.09%") == -1.09
    print("PASS: 17 fixed index mappings and unique source slugs")
    print("PASS: Investing.com HK historical table close/change/OHLC parsing")
    print("PASS: instrument identity mismatch rejected")
    print("PASS: missing exact trading-date row rejected")
    print("PASS: signed percentage and Chinese date parsing")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trading-date")
    parser.add_argument("--report-date")
    parser.add_argument("--output")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.trading_date or not args.report_date or not args.output:
        parser.error("--trading-date, --report-date and --output are required")
    trading_date = date.fromisoformat(args.trading_date)
    report_date = date.fromisoformat(args.report_date)
    observed_at = datetime.now(timezone.utc).isoformat()
    retry = Retry(total=3, connect=3, read=3, backoff_factor=1,
                  status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=frozenset(["GET"]))
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; TAC-Investment-Report/1.0)",
        "Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8",
    })
    records = {}
    for key, config in INDEXES.items():
        _, record = fetch_one(session, key, config, trading_date, observed_at)
        records[key] = record
        time.sleep(0.35)
    fragment = build_fragment(trading_date, report_date, records, observed_at)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(fragment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    verified = sum(1 for item in records.values() if item["status"] == "verified")
    pending = len(records) - verified
    print(f"Global indices: {verified}/17 verified; {pending}/17 pending_verification")
    for key, item in records.items():
        print(f"{key}: {item['status']} value={item['value']} change={item['change']}")
    print("Saved " + str(output))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("FAIL: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
