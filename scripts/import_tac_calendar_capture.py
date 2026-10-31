#!/usr/bin/env python3
"""Normalize source-captured economic and earnings calendar rows into TAC editorial fragments.

This adapter does not fetch or scrape providers. It accepts a human- or provider-captured
JSON payload with explicit source provenance, applies TAC's 3-star economic filter, and
refuses to invent earnings importance ratings.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

from assemble_tac_daily_content import assemble
from validate_tac_daily_content import load_validator


def aware_datetime(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include a timezone offset")
    return parsed.isoformat()


def source_record(base: dict, override: dict | None, observed_at: str) -> dict:
    src = dict(base)
    if override:
        src.update(override)
    name = src.get("name")
    url = src.get("url")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("source.name is required")
    if not isinstance(url, str) or urlparse(url).scheme not in {"https", "http"} or not urlparse(url).netloc:
        raise ValueError("source.url must be an absolute HTTP(S) URL")
    published = src.get("published_at")
    if published is not None:
        published = aware_datetime(published, "source.published_at")
    return {
        "name": name.strip(),
        "url": url,
        "published_at": published,
        "observed_at": observed_at,
        "publisher": src.get("publisher"),
        "notes": src.get("notes")
    }


def normalize(payload: dict) -> dict:
    report_date = date.fromisoformat(payload["report_date"]).isoformat()
    trading_date = date.fromisoformat(payload["trading_date"]).isoformat()
    observed_at = aware_datetime(payload["observed_at"], "observed_at")
    base_source = payload["source"]
    if not isinstance(base_source, dict):
        raise ValueError("source must be an object")
    fragment = {
        "report_date": report_date,
        "trading_date": trading_date,
        "economic_calendar": [],
        "earnings_calendar": []
    }

    for row in payload.get("economic_events", []):
        stars = row.get("importance_stars")
        if stars != 3:
            continue
        event = {
            "id": str(row["id"]),
            "event_date": aware_datetime(row["event_date"], "economic event_date"),
            "region": str(row["region"]),
            "event_name": str(row["event_name"]),
            "importance_stars": 3,
            "previous": row.get("previous"),
            "forecast": row.get("forecast"),
            "actual": row.get("actual"),
            "status": row["status"],
            "impact_judgment": row.get("impact_judgment"),
            "source": source_record(base_source, row.get("source"), observed_at)
        }
        fragment["economic_calendar"].append(event)

    for row in payload.get("earnings_events", []):
        if row.get("include_in_report") is not True:
            continue
        basis = row.get("importance_basis")
        stars = row.get("importance_stars")
        rating_source = row.get("importance_rating_source")
        basis_source = row.get("importance_basis_source")
        if not isinstance(basis_source, str) or not basis_source.strip():
            raise ValueError(f"earnings {row.get('id')}: importance_basis_source is required")
        if basis == "source_rating":
            if stars != 3 or not isinstance(rating_source, str) or not rating_source.strip():
                raise ValueError(f"earnings {row.get('id')}: only explicit source 3-star ratings may be displayed")
        elif basis == "major_event_assessment":
            if stars is not None or rating_source is not None:
                raise ValueError(f"earnings {row.get('id')}: assessed importance must not carry a star")
        else:
            raise ValueError(f"earnings {row.get('id')}: invalid importance_basis")

        event = {
            "id": str(row["id"]),
            "event_date": aware_datetime(row["event_date"], "earnings event_date"),
            "company": str(row["company"]),
            "ticker": row.get("ticker"),
            "session": row.get("session", "unknown"),
            "importance_stars": stars,
            "importance_basis": basis,
            "importance_basis_source": basis_source.strip(),
            "importance_rating_source": rating_source,
            "eps_estimate": row.get("eps_estimate"),
            "eps_actual": row.get("eps_actual"),
            "revenue_estimate": row.get("revenue_estimate"),
            "revenue_actual": row.get("revenue_actual"),
            "status": row["status"],
            "stock_price_reaction": row.get("stock_price_reaction"),
            "source": source_record(base_source, row.get("source"), observed_at)
        }
        fragment["earnings_calendar"].append(event)

    for group in ("economic_calendar", "earnings_calendar"):
        fragment[group].sort(key=lambda item: item["event_date"])
    return fragment


def self_test() -> None:
    payload = {
        "report_date": "2026-11-02",
        "trading_date": "2026-10-30",
        "observed_at": "2026-10-31T21:00:00+08:00",
        "source": {"name": "Synthetic source", "url": "https://example.com/calendar"},
        "economic_events": [
            {"id":"e3","event_date":"2026-11-02T22:00:00+08:00","region":"US","event_name":"High impact","importance_stars":3,"previous":1,"forecast":2,"actual":None,"status":"upcoming"},
            {"id":"e1","event_date":"2026-11-02T20:00:00+08:00","region":"US","event_name":"Low impact","importance_stars":1,"previous":1,"forecast":2,"actual":None,"status":"upcoming"}
        ],
        "earnings_events": [{
            "id":"a1","include_in_report":True,"event_date":"2026-11-02T21:30:00+08:00",
            "company":"Synthetic Mega Cap","ticker":"SYN","session":"after_market",
            "importance_stars":None,"importance_basis":"major_event_assessment",
            "importance_basis_source":"Synthetic test basis; supporting source is the company index membership record",
            "importance_rating_source":None,"eps_estimate":1.2,"eps_actual":None,
            "revenue_estimate":100.0,"revenue_actual":None,"status":"upcoming"
        }]
    }
    fragment = normalize(payload)
    assert [x["id"] for x in fragment["economic_calendar"]] == ["e3"]
    assert fragment["earnings_calendar"][0]["importance_stars"] is None
    validator, schema = load_validator()
    assembled = assemble(
        "2026-11-02", "2026-10-30", "2026-10-31T21:00:00+08:00",
        [fragment], validator, schema
    )
    assert len(assembled["economic_calendar"]) == 1
    assert len(assembled["earnings_calendar"]) == 1
    print("PASS: only source-native 3-star economic events are imported")
    print("PASS: unrated earnings require a traceable major-event assessment and retain null stars")
    print("PASS: source URLs and observation timestamps are preserved through assembly")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input")
    parser.add_argument("--output")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.input or not args.output:
        parser.error("--input and --output are required")
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    fragment = normalize(payload)
    Path(args.output).write_text(json.dumps(fragment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Calendar capture imported: {len(fragment['economic_calendar'])} economic 3-star events; "
        f"{len(fragment['earnings_calendar'])} selected earnings events."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
