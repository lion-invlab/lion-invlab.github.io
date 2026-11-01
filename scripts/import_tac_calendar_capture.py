#!/usr/bin/env python3
"""Normalize source-captured economic and earnings calendar rows into TAC editorial fragments.

This adapter does not fetch or scrape providers. It accepts a human- or provider-captured
JSON payload with explicit source provenance, imports independently assessed TAC 4/5-star economic events, and
refuses to invent earnings importance ratings.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
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
    if date.fromisoformat(report_date).weekday() != 0 and (
        payload.get("previous_economic_events") or payload.get("previous_earnings_events")
    ):
        raise ValueError("previous-week calendar events are only valid in Monday reports")
    base_source = payload["source"]
    if not isinstance(base_source, dict):
        raise ValueError("source must be an object")
    fragment = {
        "report_date": report_date,
        "trading_date": trading_date,
        "economic_calendar": [],
        "earnings_calendar": [],
        "previous_economic_calendar": [],
        "previous_earnings_calendar": []
    }

    # Coverage is explicit: an empty event array is not proof that a provider
    # calendar was fully checked. Only caller-supplied, provenance-backed status
    # can distinguish a confirmed empty result from an incomplete capture.
    supplied_coverage = payload.get("coverage", {})
    if not isinstance(supplied_coverage, dict):
        raise ValueError("coverage must be an object when supplied")
    allowed_coverage = {"economic_calendar", "earnings_calendar", "previous_economic_calendar", "previous_earnings_calendar"}
    unknown_coverage = set(supplied_coverage) - allowed_coverage
    if unknown_coverage:
        raise ValueError("unsupported calendar coverage groups: " + ", ".join(sorted(unknown_coverage)))
    if supplied_coverage:
        fragment["coverage"] = {}
        for group, record in supplied_coverage.items():
            if not isinstance(record, dict):
                raise ValueError(f"coverage.{group} must be an object")
            status = record.get("status")
            refs = record.get("source_refs")
            if status not in {"complete", "incomplete"}:
                raise ValueError(f"coverage.{group}.status must be complete or incomplete")
            if not isinstance(refs, list) or any(not isinstance(x, str) or not x.strip() for x in refs):
                raise ValueError(f"coverage.{group}.source_refs must be an array of non-empty strings")
            checked_at = record.get("checked_at")
            if checked_at is not None:
                checked_at = aware_datetime(checked_at, f"coverage.{group}.checked_at")
            checked_dates = record.get("checked_dates", [])
            if not isinstance(checked_dates, list):
                raise ValueError(f"coverage.{group}.checked_dates must be an array")
            checked_dates = [date.fromisoformat(str(item)).isoformat() for item in checked_dates]
            if len(checked_dates) != len(set(checked_dates)):
                raise ValueError(f"coverage.{group}.checked_dates contains duplicates")
            if status == "complete":
                if not refs or not checked_at:
                    raise ValueError(f"coverage.{group}: complete requires source_refs and checked_at")
                report_day = date.fromisoformat(report_date)
                current_week_start = report_day - timedelta(days=report_day.weekday())
                week_start = current_week_start if group in {"economic_calendar", "earnings_calendar"} else current_week_start - timedelta(days=7)
                expected_dates = [(week_start + timedelta(days=i)).isoformat() for i in range(5)]
                missing_dates = sorted(set(expected_dates) - set(checked_dates))
                if missing_dates:
                    raise ValueError(
                        f"coverage.{group}: cannot be complete; missing checked weekdays: "
                        + ", ".join(missing_dates)
                    )
            fragment["coverage"][group] = {
                "status": status, "source_refs": refs, "checked_at": checked_at,
                "checked_dates": checked_dates
            }

    for input_group, output_group in (("economic_events", "economic_calendar"),
                                     ("previous_economic_events", "previous_economic_calendar")):
      for row in payload.get(input_group, []):
        stars = row.get("importance_stars")
        if stars not in {4, 5}:
            continue
        basis_source = row.get("importance_basis_source")
        if row.get("importance_basis") != "major_event_assessment" or not isinstance(basis_source, str) or not basis_source.strip():
            raise ValueError(f"economic event {row.get('id')}: TAC 4/5-star rating requires a traceable independent assessment")
        event = {
            "id": str(row["id"]),
            "event_date": aware_datetime(row["event_date"], "economic event_date"),
            "region": str(row["region"]),
            "event_name": str(row["event_name"]),
            "importance_stars": stars,
            "importance_basis": "major_event_assessment",
            "importance_basis_source": basis_source.strip(),
            "previous": row.get("previous"),
            "forecast": row.get("forecast"),
            "actual": row.get("actual"),
            "status": row["status"],
            "impact_judgment": row.get("impact_judgment"),
            "source": source_record(base_source, row.get("source"), observed_at)
        }
        fragment[output_group].append(event)

    for input_group, output_group in (("earnings_events", "earnings_calendar"),
                                     ("previous_earnings_events", "previous_earnings_calendar")):
      for row in payload.get(input_group, []):
        if row.get("include_in_report") is not True:
            continue
        basis = row.get("importance_basis")
        stars = row.get("importance_stars")
        rating_source = row.get("importance_rating_source")
        basis_source = row.get("importance_basis_source")
        if not isinstance(basis_source, str) or not basis_source.strip():
            raise ValueError(f"earnings {row.get('id')}: importance_basis_source is required")
        if basis != "major_event_assessment" or stars not in {4, 5} or rating_source is not None:
            raise ValueError(f"earnings {row.get('id')}: report inclusion requires an independent TAC 4/5-star assessment; provider ratings cannot be displayed")

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
        # Preserve the richer WR §20 fields for already-published earnings.
        detail_fields = (
            "industry", "reporting_period", "time_known", "time_type", "eps_basis",
            "eps_currency", "revenue_currency", "revenue_unit", "eps_comparison_status",
            "revenue_comparison_status", "financial_judgment", "stock_price_reaction_window",
            "eps_note", "revenue_note"
        )
        for field in detail_fields:
            if field in row:
                event[field] = row[field]
        for field in ("consensus_source", "price_reaction_source"):
            if field in row:
                event[field] = source_record(base_source, row[field], observed_at) if row[field] else None
        fragment[output_group].append(event)

    for group in ("economic_calendar", "earnings_calendar", "previous_economic_calendar", "previous_earnings_calendar"):
        fragment[group].sort(key=lambda item: item["event_date"])
    return fragment


def self_test() -> None:
    payload = {
        "report_date": "2026-11-02",
        "trading_date": "2026-10-30",
        "observed_at": "2026-10-31T21:00:00+08:00",
        "source": {"name": "Synthetic source", "url": "https://example.com/calendar"},
        "economic_events": [
            {"id":"e3","event_date":"2026-11-02T22:00:00+08:00","region":"US","event_name":"High impact","importance_stars":5,"importance_basis":"major_event_assessment","importance_basis_source":"Synthetic official schedule and market relevance","previous":1,"forecast":2,"actual":None,"status":"upcoming"},
            {"id":"e1","event_date":"2026-11-02T20:00:00+08:00","region":"US","event_name":"Low impact","importance_stars":1,"previous":1,"forecast":2,"actual":None,"status":"upcoming"}
        ],
        "earnings_events": [{
            "id":"a1","include_in_report":True,"event_date":"2026-11-02T21:30:00+08:00",
            "company":"Synthetic Mega Cap","ticker":"SYN","session":"after_market",
            "importance_stars":5,"importance_basis":"major_event_assessment",
            "importance_basis_source":"Synthetic test basis; supporting source is the company index membership record",
            "importance_rating_source":None,"eps_estimate":1.2,"eps_actual":None,
            "revenue_estimate":100.0,"revenue_actual":None,"status":"upcoming"
        }],
        "previous_economic_events": [{
            "id":"prev-e1","event_date":"2026-10-30T20:30:00+08:00","region":"US",
            "event_name":"Prior CPI","importance_stars":5,"importance_basis":"major_event_assessment","importance_basis_source":"Synthetic official release and market impact","previous":"2.0%","forecast":"2.1%",
            "actual":"2.2%","status":"released"
        }],
        "previous_earnings_events": [{
            "id":"prev-a1","include_in_report":True,"event_date":"2026-10-30T21:30:00+08:00",
            "company":"Prior Synthetic Mega Cap","ticker":"PSYN","session":"after_market",
            "importance_stars":5,"importance_basis":"major_event_assessment",
            "importance_basis_source":"Synthetic prior-week test assessment",
            "importance_rating_source":None,"eps_estimate":1.0,"eps_actual":1.1,
            "revenue_estimate":90.0,"revenue_actual":92.0,"status":"released",
            "industry":"Synthetic software","reporting_period":"2026 Q3","time_known":False,"time_type":"session_only",
            "eps_basis":"GAAP diluted EPS","eps_currency":"USD","revenue_currency":"USD","revenue_unit":"B",
            "eps_comparison_status":"beat","revenue_comparison_status":"beat",
            "financial_judgment":"Synthetic released-earnings judgment.",
            "stock_price_reaction_window":"2026-10-30 first regular-session close",
            "consensus_source":{"name":"Synthetic consensus","url":"https://example.com/consensus","notes":"Synthetic test source"},
            "price_reaction_source":{"name":"Synthetic price reaction","url":"https://example.com/price","notes":"Synthetic test source"},
            "eps_note":"Synthetic EPS note","revenue_note":"Synthetic revenue note",
            "industry":"Synthetic industry","reporting_period":"2026 Q3","time_known":True,"time_type":"release_time",
            "eps_basis":"GAAP diluted EPS","eps_currency":"USD","revenue_currency":"USD","revenue_unit":"B",
            "eps_comparison_status":"beat","revenue_comparison_status":"beat",
            "financial_judgment":"Synthetic published earnings judgment.",
            "stock_price_reaction_window":"2026-10-30 first regular session close",
            "eps_note":"Synthetic EPS note.","revenue_note":"Synthetic revenue note.",
            "consensus_source":{"name":"Synthetic consensus source","url":"https://example.com/consensus"},
            "price_reaction_source":{"name":"Synthetic price reaction source","url":"https://example.com/reaction"}
        }]
    }
    fragment = normalize(payload)
    assert [x["id"] for x in fragment["economic_calendar"]] == ["e3"]
    assert fragment["earnings_calendar"][0]["importance_stars"] == 5
    validator, schema = load_validator()
    assembled = assemble(
        "2026-11-02", "2026-10-30", "2026-10-31T21:00:00+08:00",
        [fragment], validator, schema
    )
    assert len(assembled["economic_calendar"]) == 1
    assert len(assembled["earnings_calendar"]) == 1
    assert assembled["previous_economic_calendar"][0]["id"] == "prev-e1"
    assert assembled["previous_earnings_calendar"][0]["id"] == "prev-a1"
    prior = assembled["previous_earnings_calendar"][0]
    assert prior["industry"] == "Synthetic software"
    assert prior["time_type"] == "session_only"
    assert prior["consensus_source"]["name"] == "Synthetic consensus"
    assert prior["price_reaction_source"]["name"] == "Synthetic price reaction"

    empty_capture = dict(payload)
    empty_capture["economic_events"] = []
    empty_capture["earnings_events"] = []
    empty_capture["coverage"] = {
        "economic_calendar": {
            "status": "complete", "source_refs": ["synthetic-calendar-index"],
            "checked_at": "2026-10-31T21:00:00+08:00",
            "checked_dates": ["2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06"]
        },
        "earnings_calendar": {
            "status": "incomplete", "source_refs": [], "checked_at": None
        }
    }
    empty_fragment = normalize(empty_capture)
    incomplete_dates_capture = dict(empty_capture)
    incomplete_dates_capture["coverage"] = {
        "economic_calendar": {
            "status": "complete", "source_refs": ["synthetic-calendar-index"],
            "checked_at": "2026-10-31T21:00:00+08:00",
            "checked_dates": ["2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05"]
        }
    }
    try:
        normalize(incomplete_dates_capture)
    except ValueError as exc:
        assert "missing checked weekdays" in str(exc)
    else:
        raise AssertionError("coverage with a missing weekday must not be marked complete")
    empty_assembled = assemble(
        "2026-11-02", "2026-10-30", "2026-10-31T21:00:00+08:00",
        [empty_fragment], validator, schema
    )
    assert empty_assembled["economic_calendar"] == []
    assert empty_assembled["coverage"]["economic_calendar"]["status"] == "complete"
    assert empty_assembled["coverage"]["earnings_calendar"]["status"] == "incomplete"
    print("PASS: verified empty calendar remains distinct from an incomplete capture")
    print("PASS: complete coverage requires all five weekdays in the applicable week")

    print("PASS: only independently assessed TAC 4/5-star economic events are imported")
    print("PASS: earnings require traceable independent TAC 4/5-star assessments")
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
        f"Calendar capture imported: {len(fragment['economic_calendar'])} TAC 4/5-star economic events; "
        f"{len(fragment['earnings_calendar'])} selected earnings events."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
