#!/usr/bin/env python3
"""Fetch the official U.S. Treasury daily par yield curve for TAC's 2Y/10Y/30Y fields."""
from __future__ import annotations
import argparse
import json
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

FEED_BASE = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml"
SOURCE_PAGE = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve"
FIELDS = {
    "us_2y": ("BC_2YEAR", "2-year CMT par yield"),
    "us_10y": ("BC_10YEAR", "10-year CMT par yield"),
    "us_30y": ("BC_30YEAR", "30-year CMT par yield"),
}

def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":", 1)[-1]

def parse_date(raw: str) -> date:
    value = (raw or "").strip()
    if not value:
        raise ValueError("Treasury XML entry has no NEW_DATE")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return date.fromisoformat(value[:10])

def parse_number(raw: str):
    value = (raw or "").strip()
    if not value or value.upper() in {"N/A", "NA", "NULL"}:
        return None
    try:
        return float(Decimal(value))
    except InvalidOperation as exc:
        raise ValueError("invalid Treasury numeric value: " + value) from exc

def parse_feed(xml_text: str):
    root = ET.fromstring(xml_text)
    rows = {}
    for entry in root.iter():
        if local_name(entry.tag) != "entry":
            continue
        props = {}
        for element in entry.iter():
            key = local_name(element.tag)
            if key in {"NEW_DATE", *[v[0] for v in FIELDS.values()]}:
                props[key] = element.text
        if "NEW_DATE" in props:
            rows[parse_date(props["NEW_DATE"])] = props
    if not rows:
        raise ValueError("Treasury XML feed returned no parseable entries")
    return rows

def build_fragment(rows, trading_date: date, report_date: date, observed_at: str):
    if trading_date not in rows:
        latest = max(rows)
        raise ValueError(
            f"requested trading date {trading_date.isoformat()} absent; "
            f"latest returned date is {latest.isoformat()}"
        )
    current = rows[trading_date]
    prior_dates = [d for d in rows if d < trading_date]
    prior = rows[max(prior_dates)] if prior_dates else None
    bonds = {}
    for key, (field, instrument) in FIELDS.items():
        value = parse_number(current.get(field))
        previous = parse_number(prior.get(field)) if prior else None
        if value is None:
            status = "missing"
            change = None
            notes = "Treasury feed returned N/A for this maturity; do not substitute another yield series."
        else:
            status = "verified"
            change = round(value - previous, 4) if previous is not None else None
            notes = "Daily Treasury Par Yield Curve CMT; indicative par yield, not an individual bond's live yield."
        bonds[key] = {
            "value": value,
            "unit": "%",
            "change": change,
            "change_unit": "percentage_point" if change is not None else None,
            "status": status,
            "source": {
                "name": "U.S. Department of the Treasury",
                "url": SOURCE_PAGE,
                "observed_at": observed_at,
                "data_date": trading_date.isoformat(),
                "quote_type": "daily_treasury_par_yield_curve_cmt",
                "instrument": instrument,
            },
            "fallback_used": False,
            "fallback_reason": None,
            "notes": notes,
        }
    return {
        "fragment_schema_version": 1,
        "dataset": "us_treasury_daily_par_yield_curve",
        "report_date": report_date.isoformat(),
        "trading_date": trading_date.isoformat(),
        "fetched_at": observed_at,
        "source_url": FEED_BASE + "?data=daily_treasury_yield_curve&field_tdr_date_value=" + str(trading_date.year),
        "bonds": bonds,
    }

def fetch_xml(year: int) -> str:
    try:
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
    except ImportError as exc:
        raise RuntimeError("Install requests before running Treasury collector") from exc
    url = FEED_BASE
    params = {"data": "daily_treasury_yield_curve", "field_tdr_date_value": str(year)}
    retry = Retry(total=3, connect=3, read=3, backoff_factor=1,
                  status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=frozenset(["GET"]))
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    response = session.get(url, params=params, timeout=(10, 30),
                           headers={"User-Agent": "TAC-Investment-Report/1.0"})
    response.raise_for_status()
    if not response.content.strip().startswith(b"<?xml") and b"<feed" not in response.content[:1000]:
        raise ValueError("Treasury response is not the expected XML feed")
    return response.text

def self_test():
    xml = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry><content><m:properties xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata" xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices"><d:NEW_DATE>2026-10-29T00:00:00</d:NEW_DATE><d:BC_2YEAR>3.50</d:BC_2YEAR><d:BC_10YEAR>4.10</d:BC_10YEAR><d:BC_30YEAR>4.70</d:BC_30YEAR></m:properties></content></entry><entry><content><m:properties xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata" xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices"><d:NEW_DATE>2026-10-30T00:00:00</d:NEW_DATE><d:BC_2YEAR>3.55</d:BC_2YEAR><d:BC_10YEAR>4.15</d:BC_10YEAR><d:BC_30YEAR>4.75</d:BC_30YEAR></m:properties></content></entry></feed>"""
    rows = parse_feed(xml)
    out = build_fragment(rows, date(2026, 10, 30), date(2026, 11, 2), "2026-10-31T11:00:00+08:00")
    assert out["bonds"]["us_2y"]["value"] == 3.55
    assert out["bonds"]["us_10y"]["change"] == 0.05
    assert out["bonds"]["us_30y"]["source"]["data_date"] == "2026-10-30"
    try:
        build_fragment(rows, date(2026, 10, 31), date(2026, 11, 2), "2026-10-31T11:00:00+08:00")
    except ValueError:
        pass
    else:
        raise AssertionError("missing requested trading date must fail closed")
    print("PASS: XML parsing, 2Y/10Y/30Y extraction and daily change")
    print("PASS: missing requested trading date rejected")

def main():
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
    rows = parse_feed(fetch_xml(trading_date.year))
    fragment = build_fragment(rows, trading_date, report_date, observed_at)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(fragment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PASS: official Treasury data retrieved for " + trading_date.isoformat())
    for key, record in fragment["bonds"].items():
        print(key + "=" + str(record["value"]) + "% status=" + record["status"])
    print("Saved " + str(output))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("FAIL: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
