#!/usr/bin/env python3
"""Fetch the 11 fixed S&P 500 sector SPDR ETFs from Investing.com HK history pages.

Only exact requested trading-date rows are accepted. Missing or blocked rows remain
pending_verification; stale quotes are never reused.
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

SOURCE_ROOT = "https://hk.investing.com/etfs/"
SECTORS = {
    "xlk": ("spdr-select-sector---technology", "XLK", "科技"),
    "xly": ("spdr-consumer-discr.-select-sector", "XLY", "非必需消費"),
    "xlb": ("spdr-materials-select-sector-etf", "XLB", "原材料"),
    "xlu": ("spdr-select-sector---utilities", "XLU", "公用事業"),
    "xli": ("industrial-sector-spdr-trust", "XLI", "工業"),
    "xlv": ("spdr---health-care", "XLV", "醫療保健"),
    "xlf": ("financial-select-sector-spdr-fund", "XLF", "金融"),
    "xlc": ("communication-services-select-spdr", "XLC", "通訊服務"),
    "xlre": ("real-estate-select-sector-spdr", "XLRE", "房地產"),
    "xlp": ("spdr---consumer-staples", "XLP", "必需消費"),
    "xle": ("spdr-energy-select-sector-fund", "XLE", "能源"),
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
        headers = [normalized_header(cell.get_text(" ", strip=True))
                   for cell in rows[0].find_all(["th", "td"])]
        date_i = next((i for i, h in enumerate(headers) if "日期" in h or h == "date"), None)
        close_i = next((i for i, h in enumerate(headers) if "收市" in h or "收盤" in h or h == "close"), None)
        change_i = next((i for i, h in enumerate(headers) if ("升跌" in h or "change" in h) and ("%" in h or "percent" in h or "升跌" in h)), None)
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
            return {"close": close, "change_pct": change_pct, "heading": heading_text}
    raise ValueError(f"exact trading-date row {trading_date.isoformat()} not found")

def pending_record(reason: str) -> dict:
    return {
        "value": None, "unit": "USD/share", "change": None,
        "change_unit": "percent", "status": "pending_verification",
        "source": None, "fallback_used": False, "fallback_reason": None,
        "notes": f"未取得指定交易日資料，未沿用舊值。原因：{reason}",
    }

def fetch_one(session: requests.Session, key: str, config: tuple,
              trading_date: date, observed_at: str) -> tuple[str, dict]:
    slug, ticker, label = config
    url = f"{SOURCE_ROOT}{slug}-historical-data"
    try:
        response = session.get(url, timeout=(10, 30))
        response.raise_for_status()
        if len(response.text) < 5000:
            raise ValueError("response unexpectedly short")
        parsed = parse_history_page(response.text, ticker, trading_date)
        return key, {
            "value": parsed["close"], "unit": "USD/share",
            "change": parsed["change_pct"], "change_unit": "percent",
            "status": "verified",
            "source": {
                "name": "Investing.com 香港站",
                "url": url, "observed_at": observed_at,
                "data_date": trading_date.isoformat(),
                "quote_type": "investing_com_hk_historical_close_pct_change",
                "instrument": f"{label} ({ticker})",
            },
            "fallback_used": False, "fallback_reason": None,
            "notes": "採用歷史資料表指定交易日收市價及日升跌幅；早報顯示日漲跌幅。",
        }
    except Exception as exc:
        return key, pending_record(str(exc))

def build_fragment(trading_date: date, report_date: date,
                   records: dict, observed_at: str) -> dict:
    if set(records) != set(SECTORS):
        raise ValueError("sector ETF field mismatch")
    return {
        "fragment_schema_version": 1,
        "dataset": "tac_sector_etfs",
        "report_date": report_date.isoformat(),
        "trading_date": trading_date.isoformat(),
        "fetched_at": observed_at,
        "source_priority": "Investing.com Hong Kong ETF historical data pages",
        "sectors": records,
    }

def self_test() -> None:
    sample = """<html><h1>State Street Technology Select Sector SPDR ETF (XLK)</h1>
    <table><thead><tr><th>日期</th><th>收市</th><th>開市</th><th>高</th><th>低</th><th>升跌（%）</th></tr></thead>
    <tbody><tr><td>2026年10月30日</td><td>179.51</td><td>182.11</td><td>182.29</td><td>176.92</td><td>-4.89%</td></tr></tbody></table></html>"""
    parsed = parse_history_page(sample, "XLK", date(2026, 10, 30))
    assert parsed["close"] == 179.51 and parsed["change_pct"] == -4.89
    try:
        parse_history_page(sample, "XLY", date(2026, 10, 30))
    except ValueError:
        pass
    else:
        raise AssertionError("instrument mismatch must fail closed")
    try:
        parse_history_page(sample, "XLK", date(2026, 10, 31))
    except ValueError:
        pass
    else:
        raise AssertionError("missing exact trading date must fail closed")
    assert len(SECTORS) == 11 and len({v[0] for v in SECTORS.values()}) == 11
    assert parse_date("2026年10月30日") == date(2026, 10, 30)
    assert parse_number("−4.89%") == -4.89
    print("PASS: 11 fixed S&P sector ETF mappings")
    print("PASS: Investing.com HK historical close/change parser")
    print("PASS: instrument identity mismatch rejected")
    print("PASS: missing exact trading-date row rejected")

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
    for key, config in SECTORS.items():
        _, record = fetch_one(session, key, config, trading_date, observed_at)
        records[key] = record
        time.sleep(0.35)
    fragment = build_fragment(trading_date, report_date, records, observed_at)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(fragment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    verified = sum(1 for item in records.values() if item["status"] == "verified")
    pending = len(records) - verified
    print(f"Sector ETFs: {verified}/11 verified; {pending}/11 pending_verification")
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
