#!/usr/bin/env python3
"""Fetch FRED DGS2/DGS10/DGS30 only as the documented U.S. Treasury fallback."""
from __future__ import annotations

import argparse
import csv
import json
from datetime import date, datetime, timedelta, timezone
import math
from io import StringIO
from pathlib import Path

SERIES = {
    "us_2y": ("DGS2", "2-year Treasury constant maturity rate"),
    "us_10y": ("DGS10", "10-year Treasury constant maturity rate"),
    "us_30y": ("DGS30", "30-year Treasury constant maturity rate"),
}
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv"

def parse_csv(text: str) -> dict[str, dict[str, float | None]]:
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames or "observation_date" not in reader.fieldnames:
        raise ValueError("FRED CSV missing observation_date column")
    missing = [series for series, _ in SERIES.values() if series not in reader.fieldnames]
    if missing:
        raise ValueError("FRED CSV missing series columns: " + ", ".join(missing))
    rows: dict[str, dict[str, float | None]] = {}
    for row in reader:
        day = row.get("observation_date", "")
        if not day:
            continue
        values: dict[str, float | None] = {}
        for key, (series, _) in SERIES.items():
            raw = (row.get(series) or "").strip()
            if raw in {"", "."}:
                values[key] = None
            else:
                value = float(raw)
                if not math.isfinite(value):
                    raise ValueError(f"non-finite FRED value for {series} on {day}: {raw}")
                values[key] = value
        rows[day] = values
    if not rows:
        raise ValueError("FRED CSV contained no dated observations")
    return rows

def build_fragment(rows: dict[str, dict[str, float | None]], trading_date: date,
                   report_date: date, observed_at: str) -> dict:
    day = trading_date.isoformat()
    if day not in rows:
        latest = max(rows)
        raise ValueError(f"requested trading date {day} absent from FRED; latest returned date is {latest}")
    previous_days = [d for d in rows if d < day]
    prior = rows[max(previous_days)] if previous_days else {}
    bonds = {}
    for key, (series, instrument) in SERIES.items():
        value = rows[day][key]
        previous = prior.get(key)
        if value is None:
            status, change = "missing", None
            notes = "FRED fallback has no observation for this date; do not carry forward an older value."
        else:
            status = "verified"
            change = round(value - previous, 4) if previous is not None else None
            notes = "FRED DGS constant-maturity series used only because the primary Treasury feed was unavailable or incomplete."
        bonds[key] = {
            "value": value, "unit": "%", "change": change,
            "change_unit": "percentage_point" if change is not None else None,
            "status": status,
            "source": {
                "name": "Federal Reserve Bank of St. Louis FRED",
                "url": f"https://fred.stlouisfed.org/series/{series}",
                "observed_at": observed_at, "data_date": day,
                "quote_type": "fred_daily_constant_maturity_rate",
                "instrument": instrument,
            },
            "fallback_used": True,
            "fallback_reason": "U.S. Treasury primary daily par-yield feed unavailable or missing requested observation; FRED DGS fallback used per TAC_WORK_RULES.md.",
            "notes": notes,
        }
    return {
        "fragment_schema_version": 1,
        "dataset": "us_treasury_fred_fallback",
        "report_date": report_date.isoformat(),
        "trading_date": day,
        "fetched_at": observed_at,
        "source_url": FRED_CSV,
        "fallback_used": True,
        "fallback_reason": "Primary U.S. Treasury feed unavailable or incomplete.",
        "bonds": bonds,
    }

def fetch_csv(trading_date: date) -> str:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    session = requests.Session()
    retry = Retry(total=3, connect=3, read=3, backoff_factor=1,
                  status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=frozenset(["GET"]))
    session.mount("https://", HTTPAdapter(max_retries=retry))
    # Include a lookback window so the first trading day of a month can still
    # calculate its daily change against the prior available FRED observation.
    params = {"id": ",".join(v[0] for v in SERIES.values()),
              "cosd": (trading_date - timedelta(days=14)).isoformat(),
              "coed": trading_date.isoformat()}
    response = session.get(FRED_CSV, params=params, timeout=(10, 30),
                           headers={"User-Agent": "TAC-Investment-Report/1.0"})
    response.raise_for_status()
    if "observation_date" not in response.text[:500]:
        raise ValueError("FRED response is not the expected CSV")
    return response.text

def self_test() -> None:
    sample = """observation_date,DGS2,DGS10,DGS30
2026-09-30,4.08,4.48,4.88
2026-10-01,4.10,4.50,4.90
2026-10-29,4.10,4.50,4.90
2026-10-30,4.12,4.55,4.95
"""
    rows = parse_csv(sample)
    out = build_fragment(rows, date(2026, 10, 30), date(2026, 11, 2),
                         "2026-10-31T12:00:00+00:00")
    assert out["bonds"]["us_2y"]["value"] == 4.12
    assert out["bonds"]["us_10y"]["change"] == 0.05
    assert out["bonds"]["us_30y"]["fallback_used"] is True
    month_start = build_fragment(rows, date(2026, 10, 1), date(2026, 11, 2),
                                 "2026-10-31T12:00:00+00:00")
    assert month_start["bonds"]["us_2y"]["change"] == 0.02
    try:
        build_fragment(rows, date(2026, 10, 31), date(2026, 11, 2),
                       "2026-10-31T12:00:00+00:00")
    except ValueError:
        pass
    else:
        raise AssertionError("missing requested date must fail closed")
    print("PASS: FRED CSV parsing and 2Y/10Y/30Y extraction")
    print("PASS: daily changes and explicit fallback provenance")
    print("PASS: first trading day of month uses prior-month observation")
    print("PASS: missing requested trading date rejected")

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
    rows = parse_csv(fetch_csv(trading_date))
    fragment = build_fragment(rows, trading_date, report_date, observed_at)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(fragment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PASS: FRED fallback data retrieved for " + trading_date.isoformat())
    for key, record in fragment["bonds"].items():
        print(key + "=" + str(record["value"]) + "% status=" + record["status"])
    print("Saved " + str(output))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
