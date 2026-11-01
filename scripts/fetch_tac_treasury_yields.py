#!/usr/bin/env python3
"""Fetch the official U.S. Treasury daily par yield curve for TAC's 2Y/10Y/30Y fields."""
from __future__ import annotations
import argparse
import csv
import io
import json
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
import urllib.request

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


def fetch_fred_rows(trading_date: date):
    start = trading_date - timedelta(days=10)
    url = (
        "https://fred.stlouisfed.org/graph/fredgraph.csv"
        f"?id=DGS2,DGS10,DGS30&cosd={start.isoformat()}&coed={trading_date.isoformat()}"
    )
    request = urllib.request.Request(
        url, headers={"User-Agent": "TAC-Investment-Report/1.0", "Accept": "text/csv"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read(2_000_000).decode("utf-8-sig")
    rows = {}
    for row in csv.DictReader(io.StringIO(payload)):
        raw_date = row.get("observation_date") or row.get("DATE")
        if not raw_date:
            continue
        day = date.fromisoformat(raw_date)
        rows[day] = {
            "DGS2": row.get("DGS2"),
            "DGS10": row.get("DGS10"),
            "DGS30": row.get("DGS30"),
        }
    if not rows:
        raise ValueError("FRED returned no parseable daily Treasury observations")
    return rows, url


def build_combined_fragment(official_rows, fred_rows, fred_url, trading_date,
                            report_date, observed_at, official_error=None,
                            fred_error=None):
    official_current = official_rows.get(trading_date)
    official_prior_dates = [day for day in official_rows if day < trading_date]
    official_prior = official_rows[max(official_prior_dates)] if official_prior_dates else None
    fred_current = fred_rows.get(trading_date)
    fred_prior_dates = [day for day in fred_rows if day < trading_date]
    fred_prior = fred_rows[max(fred_prior_dates)] if fred_prior_dates else None
    bonds = {}
    for key, (field, instrument) in FIELDS.items():
        official_value = parse_number(official_current.get(field)) if official_current else None
        fred_field = {"BC_2YEAR": "DGS2", "BC_10YEAR": "DGS10", "BC_30YEAR": "DGS30"}[field]
        fred_value = parse_number(fred_current.get(fred_field)) if fred_current else None
        if official_value is not None:
            previous = parse_number(official_prior.get(field)) if official_prior else None
            bonds[key] = {
                "value": official_value, "unit": "%", 
                "change": round(official_value - previous, 4) if previous is not None else None,
                "change_unit": "percentage_point" if previous is not None else None,
                "status": "verified",
                "source": {
                    "name": "U.S. Department of the Treasury", "url": SOURCE_PAGE,
                    "observed_at": observed_at, "data_date": trading_date.isoformat(),
                    "quote_type": "daily_treasury_par_yield_curve_cmt",
                    "instrument": instrument,
                },
                "fallback_used": False, "fallback_reason": None,
                "notes": "採用美國財政部 Daily Treasury Par Yield Curve CMT；屬指標性平價殖利率，非個別債券即時殖利率。",
            }
        elif fred_value is not None:
            previous = parse_number(fred_prior.get(fred_field)) if fred_prior else None
            reason = official_error or "財政部指定日期／期別缺值，依 WR 啟用 FRED 備援"
            bonds[key] = {
                "value": fred_value, "unit": "%",
                "change": round(fred_value - previous, 4) if previous is not None else None,
                "change_unit": "percentage_point" if previous is not None else None,
                "status": "verified",
                "source": {
                    "name": "Federal Reserve Bank of St. Louis FRED", "url": fred_url,
                    "observed_at": observed_at, "data_date": trading_date.isoformat(),
                    "quote_type": "fred_daily_constant_maturity_treasury_yield",
                    "instrument": f"{instrument} ({fred_field})",
                },
                "fallback_used": True, "fallback_reason": reason,
                "notes": "財政部優先來源缺值，改採 FRED 同日期同期限 DGS 序列；備援原因已記錄。",
            }
        else:
            reason = "; ".join(x for x in (official_error, fred_error) if x) or (
                "財政部與 FRED 均無指定交易日同期限資料"
            )
            bonds[key] = {
                "value": None, "unit": "%", "change": None, "change_unit": None,
                "status": "pending_verification", "source": None,
                "fallback_used": False, "fallback_reason": None,
                "notes": "待核實；未沿用舊值。原因：" + reason,
            }
    return {
        "fragment_schema_version": 1, "dataset": "us_treasury_daily_yields",
        "report_date": report_date.isoformat(), "trading_date": trading_date.isoformat(),
        "fetched_at": observed_at, "bonds": bonds,
    }


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
        # Deterministic primary/fallback selection test.
        day = date(2026, 10, 30)
        official = {
            date(2026, 10, 29): {"BC_2YEAR": "3.50", "BC_10YEAR": "4.10", "BC_30YEAR": "4.70"},
            day: {"BC_2YEAR": "3.55", "BC_10YEAR": "N/A", "BC_30YEAR": "4.75"},
        }
        fred = {
            date(2026, 10, 29): {"DGS2": "3.50", "DGS10": "4.10", "DGS30": "4.70"},
            day: {"DGS2": "3.56", "DGS10": "4.16", "DGS30": "4.76"},
        }
        combined = build_combined_fragment(official, fred, "https://fred.stlouisfed.org/graph/fredgraph.csv", day,
            date(2026, 11, 2), "2026-10-31T11:00:00+08:00")
        assert combined["bonds"]["us_2y"]["source"]["name"] == "U.S. Department of the Treasury"
        assert combined["bonds"]["us_10y"]["source"]["name"].endswith("FRED")
        assert combined["bonds"]["us_10y"]["fallback_used"] is True
        assert combined["bonds"]["us_30y"]["fallback_used"] is False
        print("PASS: Treasury primary retained; FRED exact-date fallback used only for missing maturity")
        return 0
    if not args.trading_date or not args.report_date or not args.output:
        parser.error("--trading-date, --report-date and --output are required")
    trading_date = date.fromisoformat(args.trading_date)
    report_date = date.fromisoformat(args.report_date)
    observed_at = datetime.now(timezone.utc).isoformat()
    official_rows, official_error = {}, None
    try:
        official_rows = parse_feed(fetch_xml(trading_date.year))
        if trading_date not in official_rows:
            latest = max(official_rows)
            official_error = f"Treasury exact date missing; latest returned date={latest.isoformat()}"
    except Exception as exc:
        official_error = f"Treasury official feed unavailable: {type(exc).__name__}: {exc}"
    fred_rows, fred_url, fred_error = {}, None, None
    try:
        fred_rows, fred_url = fetch_fred_rows(trading_date)
    except Exception as exc:
        fred_error = f"FRED fallback unavailable: {type(exc).__name__}: {exc}"
    fragment = build_combined_fragment(
        official_rows, fred_rows, fred_url or "https://fred.stlouisfed.org/graph/fredgraph.csv",
        trading_date, report_date, observed_at, official_error, fred_error
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(fragment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    verified = sum(1 for item in fragment["bonds"].values() if item["status"] == "verified")
    pending = 3 - verified
    print(f"Treasury yields: {verified}/3 verified; {pending}/3 pending_verification")
    for key, record in fragment["bonds"].items():
        source = record.get("source") or {}
        print(f"{key}={record['value']}% status={record['status']} source={source.get('name')} fallback={record['fallback_used']}")
    print("Saved " + str(output))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("FAIL: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
