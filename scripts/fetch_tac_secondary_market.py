#!/usr/bin/env python3
"""Fetch TAC FX, commodities and volatility indicators from approved sources.

Investing.com HK historical pages must contain the exact requested trading date.
CNN Fear & Greed is a current official snapshot with its own source timestamp.
Any unavailable, stale, ambiguous or identity-mismatched record remains pending.
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
from typing import Any

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

INSTRUMENTS = {
    "fx": {
        "dxy": ("https://hk.investing.com/currencies/us-dollar-index-historical-data", "US Dollar Index", "index_point", ("US Dollar Index", "DXY")),
        "usd_twd": ("https://hk.investing.com/currencies/usd-twd-historical-data", "USD/TWD", "currency_pair", ("USD/TWD", "USD TWD")),
        "eur_usd": ("https://hk.investing.com/currencies/eur-usd-historical-data", "EUR/USD", "currency_pair", ("EUR/USD", "EUR USD")),
        "gbp_usd": ("https://hk.investing.com/currencies/gbp-usd-historical-data", "GBP/USD", "currency_pair", ("GBP/USD", "GBP USD")),
        "aud_usd": ("https://hk.investing.com/currencies/aud-usd-historical-data", "AUD/USD", "currency_pair", ("AUD/USD", "AUD USD")),
        "usd_jpy": ("https://hk.investing.com/currencies/usd-jpy-historical-data", "USD/JPY", "currency_pair", ("USD/JPY", "USD JPY")),
    },
    "energy": {
        "wti": ("https://hk.investing.com/commodities/crude-oil-historical-data", "WTI Crude Oil", "USD/barrel", ("WTI Crude Oil", "Crude Oil WTI")),
        "brent": ("https://hk.investing.com/commodities/brent-oil-historical-data", "Brent Crude Oil", "USD/barrel", ("Brent Crude Oil", "Brent Oil")),
    },
    "precious_metals": {
        "gold_gc": ("https://hk.investing.com/commodities/gold-historical-data", "Gold Futures", "USD/troy_ounce", ("Gold Futures", "Gold")),
        "silver_si": ("https://hk.investing.com/commodities/silver-historical-data", "Silver Futures", "USD/troy_ounce", ("Silver Futures", "Silver")),
    },
    "risk_indicators": {
        "vix": ("https://hk.investing.com/indices/volatility-s-p-500-historical-data", "CBOE Volatility Index", "index_point", ("CBOE Volatility Index", "S&P 500 VIX", "VIX")),
        "move": ("https://hk.investing.com/indices/ice-bofaml-move-historical-data", "ICE BofA MOVE Index", "index_point", ("ICE BofA MOVE Index", "MOVE Index", "MOVE")),
    },
}
CNN_PAGE = "https://edition.cnn.com/markets/fear-and-greed"
CNN_DATA = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"

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

def parse_history_page(html: str, aliases: tuple[str, ...], trading_date: date) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find("h1")
    heading_text = heading.get_text(" ", strip=True) if heading else ""
    if not any(alias.casefold() in heading_text.casefold() for alias in aliases):
        raise ValueError(f"instrument identity mismatch: expected one of {aliases}, heading={heading_text!r}")
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [normalized_header(cell.get_text(" ", strip=True))
                   for cell in rows[0].find_all(["th", "td"])]
        date_i = next((i for i, h in enumerate(headers) if "日期" in h or h == "date"), None)
        close_i = next((i for i, h in enumerate(headers) if "收市" in h or "收盤" in h or h in {"close", "price"}), None)
        change_i = next((i for i, h in enumerate(headers)
                         if any(token in h for token in ("升跌", "漲跌", "change", "變動"))), None)
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
            change = parse_number(cells[change_i].get_text(" ", strip=True))
            if close <= 0:
                raise ValueError("historical close must be positive")
            return {"close": close, "change_pct": change, "heading": heading_text}
    raise ValueError(f"exact trading-date row {trading_date.isoformat()} not found")

def pending_record(unit: str, reason: str) -> dict:
    return {
        "value": None, "unit": unit, "change": None,
        "change_unit": "percent", "status": "pending_verification",
        "source": None, "fallback_used": False, "fallback_reason": None,
        "notes": f"未取得指定交易日資料，未沿用舊值。原因：{reason}",
    }

def fetch_history_record(session: requests.Session, key: str, url: str,
                         instrument: str, unit: str, aliases: tuple[str, ...],
                         trading_date: date, observed_at: str) -> dict:
    try:
        response = session.get(url, timeout=(10, 30))
        response.raise_for_status()
        if len(response.text) < 5000:
            raise ValueError("response unexpectedly short")
        parsed = parse_history_page(response.text, aliases, trading_date)
        return {
            "value": parsed["close"], "unit": unit,
            "change": parsed["change_pct"], "change_unit": "percent",
            "status": "verified",
            "source": {
                "name": "Investing.com 香港站", "url": url,
                "observed_at": observed_at, "data_date": trading_date.isoformat(),
                "quote_type": "investing_com_hk_historical_close_pct_change",
                "instrument": instrument,
            },
            "fallback_used": False, "fallback_reason": None,
            "notes": "採用歷史資料表指定交易日收市值及日升跌幅；僅接受完全相符的資料日期與品項。",
        }
    except Exception as exc:
        return pending_record(unit, str(exc))

def parse_cnn_fear_greed(payload: dict, observed_at: str,
                         now: datetime | None = None) -> dict:
    if not isinstance(payload, dict) or not isinstance(payload.get("fear_and_greed"), dict):
        raise ValueError("CNN response missing fear_and_greed object")
    item = payload["fear_and_greed"]
    score = item.get("score")
    if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 100:
        raise ValueError("CNN Fear & Greed score missing or outside 0-100")
    raw_timestamp = item.get("timestamp")
    if isinstance(raw_timestamp, (int, float)) and not isinstance(raw_timestamp, bool):
        seconds = raw_timestamp / 1000 if raw_timestamp > 10_000_000_000 else raw_timestamp
        source_time = datetime.fromtimestamp(seconds, timezone.utc)
    elif isinstance(raw_timestamp, str):
        source_time = datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))
        if source_time.tzinfo is None:
            raise ValueError("CNN source timestamp must include timezone")
    else:
        raise ValueError("CNN Fear & Greed source timestamp missing")
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        raise ValueError("CNN validation clock must include timezone")
    if source_time > current_time or (current_time - source_time).total_seconds() > 72 * 3600:
        raise ValueError("CNN Fear & Greed snapshot is stale or future-dated (72-hour limit)")
    return {
        "value": float(score), "unit": "index_score",
        "change": None, "change_unit": None,
        "status": "verified",
        "source": {
            "name": "CNN Business Fear & Greed Index", "url": CNN_PAGE,
            "observed_at": observed_at, "data_date": source_time.date().isoformat(),
            "quote_type": "cnn_fear_greed_current_snapshot",
            "instrument": "CNN Fear & Greed Index",
        },
        "fallback_used": False, "fallback_reason": None,
        "notes": "採用 CNN 官方 Fear & Greed 當前快照；資料日期依來源時間戳記，非前一交易日收盤值。",
    }

def build_fragment(trading_date: date, report_date: date, groups: dict,
                   observed_at: str) -> dict:
    expected = {name: set(items) for name, items in INSTRUMENTS.items()}
    expected["risk_indicators"].add("cnn_fear_greed")
    if set(groups) != set(expected):
        raise ValueError("secondary market group mismatch")
    for group, keys in expected.items():
        if set(groups[group]) != keys:
            raise ValueError(f"{group} field mismatch")
    return {
        "fragment_schema_version": 1,
        "dataset": "tac_secondary_market",
        "report_date": report_date.isoformat(),
        "trading_date": trading_date.isoformat(),
        "fetched_at": observed_at,
        "source_priority": "Investing.com Hong Kong historical pages; CNN Business official current Fear & Greed snapshot",
        **groups,
    }

def self_test() -> None:
    sample = """<html><h1>EUR/USD Historical Data</h1>
    <table><thead><tr><th>Date</th><th>Price</th><th>Open</th><th>High</th><th>Low</th><th>Change %</th></tr></thead>
    <tbody><tr><td>Oct 30, 2026</td><td>1.1532</td><td>1.15</td><td>1.16</td><td>1.14</td><td>0.25%</td></tr></tbody></table></html>"""
    parsed = parse_history_page(sample, ("EUR/USD", "EUR USD"), date(2026, 10, 30))
    assert parsed["close"] == 1.1532 and parsed["change_pct"] == 0.25
    try:
        parse_history_page(sample, ("GBP/USD",), date(2026, 10, 30))
    except ValueError:
        pass
    else:
        raise AssertionError("instrument mismatch must fail closed")
    try:
        parse_history_page(sample, ("EUR/USD",), date(2026, 10, 31))
    except ValueError:
        pass
    else:
        raise AssertionError("missing exact date must fail closed")
    observed = "2026-10-30T12:00:00+00:00"
    fixed_now = datetime.fromisoformat("2026-10-30T12:00:00+00:00")
    cnn = parse_cnn_fear_greed({"fear_and_greed": {"score": 52.5, "timestamp": "2026-10-30T11:00:00Z"}}, observed, fixed_now)
    assert cnn["value"] == 52.5 and cnn["source"]["data_date"] == "2026-10-30"
    for invalid in (
        {"fear_and_greed": {"score": 101, "timestamp": "2026-10-30T11:00:00Z"}},
        {"fear_and_greed": {"score": 50, "timestamp": "2026-10-20T11:00:00Z"}},
    ):
        try:
            parse_cnn_fear_greed(invalid, observed, fixed_now)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid or stale CNN data must fail closed")
    print("PASS: exact-date Investing.com historical close/change parsing")
    print("PASS: instrument identity and stale/missing trading date rejected")
    print("PASS: CNN Fear & Greed score range and source timestamp validation")
    print("PASS: stale or out-of-range CNN data rejected")

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
    groups = {name: {} for name in INSTRUMENTS}
    for group, records in INSTRUMENTS.items():
        for key, (url, instrument, unit, aliases) in records.items():
            groups[group][key] = fetch_history_record(
                session, key, url, instrument, unit, aliases, trading_date, observed_at
            )
            time.sleep(0.25)
    try:
        response = session.get(CNN_DATA, timeout=(10, 30), headers={"Referer": CNN_PAGE})
        response.raise_for_status()
        groups["risk_indicators"]["cnn_fear_greed"] = parse_cnn_fear_greed(response.json(), observed_at)
    except Exception as exc:
        groups["risk_indicators"]["cnn_fear_greed"] = pending_record("index_score", str(exc))
    fragment = build_fragment(trading_date, report_date, groups, observed_at)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(fragment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for group, records in groups.items():
        verified = sum(1 for item in records.values() if item["status"] == "verified")
        print(f"{group}: {verified}/{len(records)} verified; {len(records)-verified} pending")
    print("Saved " + str(output))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("FAIL: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
