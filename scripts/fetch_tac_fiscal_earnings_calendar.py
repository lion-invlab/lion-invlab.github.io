#!/usr/bin/env python3
"""Fetch Fiscal.ai earnings-event candidates without inventing report times or ratings.

Requires FISCAL_API_KEY in the environment (for GitHub Actions, store it as a secret).
The API's free-trial key is restricted to trial companies. This collector emits source
candidates only; it does not assert EPS/revenue actuals or analyst consensus.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

API_URL = "https://api.fiscal.ai/v1/events-calendar"
SOURCE_URL = "https://docs.fiscal.ai/docs/api-reference"


def request_page(api_key: str, params: dict[str, str], timeout: int = 30) -> dict:
    url = API_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={"X-Api-Key": api_key, "Accept": "application/json", "User-Agent": "TAC-Calendar-Collector/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status != 200:
                raise RuntimeError(f"Fiscal.ai returned HTTP {response.status}")
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Fiscal.ai HTTP {exc.code}: {detail}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ValueError("Fiscal.ai response missing data array")
    return payload


def normalize_event(row: dict, observed_at: str) -> dict | None:
    if row.get("eventType") != "earnings" or row.get("eventRole") != "financial_results_release":
        return None
    ticker = (row.get("primaryListing") or {}).get("ticker")
    event_date = row.get("eventDate")
    if not event_date:
        window = row.get("dateWindow")
        if isinstance(window, dict):
            event_date = window.get("startDate") or window.get("start")
    if not event_date:
        return None
    # Deliberately preserve date/session separately. Never synthesize a clock time.
    return {
        "event_id": row.get("eventId"),
        "company_id": row.get("companyFiscalIdentifier"),
        "company": row.get("displayNameEnglish"),
        "ticker": ticker,
        "title": row.get("title"),
        "period_label": row.get("periodLabel"),
        "event_date": event_date,
        "date_window": row.get("dateWindow"),
        "event_status": row.get("eventStatus"),
        "event_session": row.get("eventSession"),
        "event_time": row.get("eventTime"),
        "event_timezone": row.get("eventTimezone"),
        "event_datetime_utc": row.get("eventDatetimeUtc"),
        "market_cap_usd": row.get("marketCapUsd"),
        "sector": row.get("sector"),
        "source": {
            "name": "Fiscal.ai Events Calendar",
            "url": SOURCE_URL,
            "observed_at": observed_at,
        },
        "editorial_status": "pending_enrichment",
        "importance_stars": None,
        "note": "Schedule candidate only; no EPS/revenue values or importance rating inferred.",
    }


def fetch_calendar(api_key: str, start_date: str, end_date: str, country: str = "US") -> dict:
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if end < start:
        raise ValueError("end-date must not precede start-date")
    observed_at = datetime.now(timezone.utc).isoformat()
    params = {
        "country": country,
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "page": "1",
        "pageSize": "1000",
    }
    page = 1
    raw_rows: list[dict] = []
    while True:
        params["page"] = str(page)
        payload = request_page(api_key, params)
        raw_rows.extend(payload["data"])
        pagination = payload.get("pagination") or {}
        total_pages = pagination.get("totalPages", page)
        if page >= int(total_pages):
            break
        page += 1
        if page > 100:
            raise RuntimeError("Pagination safety limit exceeded")
    candidates = []
    for row in raw_rows:
        event = normalize_event(row, observed_at)
        if event:
            candidates.append(event)
    candidates.sort(key=lambda x: (x["event_date"], x.get("ticker") or "", x.get("event_id") or ""))
    return {
        "provider": "Fiscal.ai",
        "endpoint": API_URL,
        "requested_range": {"start": start.isoformat(), "end": end.isoformat(), "country": country},
        "observed_at": observed_at,
        "source_documentation": SOURCE_URL,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "limitations": [
            "Free-trial API keys return only free-trial companies.",
            "Events Calendar supplies earnings event schedule only; it does not supply EPS/revenue actuals or consensus in this response.",
            "Missing event time/timezone is kept missing; no clock time is fabricated.",
            "All rows remain pending enrichment and are not publication-ready.",
        ],
    }


def self_test() -> None:
    row = {
        "eventType": "earnings", "eventRole": "financial_results_release",
        "eventId": "evt-1", "companyFiscalIdentifier": "FSCLC123",
        "displayNameEnglish": "Example Corp", "primaryListing": {"ticker": "EXM"},
        "title": "Q3 Earnings Release", "periodLabel": "Q3 2026",
        "eventDate": "2026-11-03", "eventStatus": "confirmed",
        "eventSession": "after_close", "eventTime": None, "eventTimezone": None,
        "eventDatetimeUtc": None, "marketCapUsd": 1000000000, "sector": "Technology",
    }
    event = normalize_event(row, "2026-10-31T12:00:00+00:00")
    assert event and event["event_date"] == "2026-11-03"
    assert event["event_time"] is None and event["event_timezone"] is None
    assert event["importance_stars"] is None
    assert event["editorial_status"] == "pending_enrichment"
    assert normalize_event({**row, "eventRole": "earnings_call_for_results"}, "x") is None
    assert normalize_event({**row, "eventType": "dividend"}, "x") is None
    print("PASS: only financial-results-release events are retained")
    print("PASS: unknown time/timezone and importance remain null")
    print("PASS: candidate remains pending enrichment")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--country", default="US")
    parser.add_argument("--output")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    api_key = os.environ.get("FISCAL_API_KEY")
    if not api_key:
        print("FISCAL_API_KEY is not configured; no network request made.", file=sys.stderr)
        return 2
    if not args.start_date or not args.end_date or not args.output:
        parser.error("--start-date, --end-date and --output are required")
    result = fetch_calendar(api_key, args.start_date, args.end_date, args.country)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Fetched {result['candidate_count']} earnings schedule candidates; all remain pending enrichment.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
