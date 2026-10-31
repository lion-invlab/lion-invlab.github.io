#!/usr/bin/env python3
"""Validate TAC editorial content against its schema and report-specific rules."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "tac-daily-content.schema.json"


def load_validator():
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError as exc:
        raise RuntimeError("Missing dependency: install jsonschema before validating TAC content") from exc
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker()), schema


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def validate_report_rules(data: dict) -> list[str]:
    errors: list[str] = []
    meta = data["meta"]
    report_day = date.fromisoformat(meta["report_date"])
    trading_day = date.fromisoformat(meta["trading_date"])
    expected_type = "monday" if report_day.weekday() == 0 else "weekday"
    if report_day.weekday() > 4:
        errors.append("weekend report dates are not eligible for automatic production")
    if meta["template_type"] != expected_type:
        errors.append(f"template_type must be {expected_type} for report_date {report_day}")
    if trading_day >= report_day:
        errors.append("trading_date must precede report_date")

    start = meta.get("news_window_start")
    end = meta.get("news_window_end")
    if start and end and parse_dt(start) >= parse_dt(end):
        errors.append("news_window_start must precede news_window_end")

    for group_name in ("focus_news", "market_headlines"):
        ids: set[str] = set()
        for index, item in enumerate(data[group_name]):
            label = f"{group_name}[{index}]"
            if item["id"] in ids:
                errors.append(f"{label}: duplicate id {item['id']}")
            ids.add(item["id"])
            if start and parse_dt(item["published_at"]) < parse_dt(start):
                errors.append(f"{label}: published_at precedes configured news window")
            if end and parse_dt(item["published_at"]) > parse_dt(end):
                errors.append(f"{label}: published_at exceeds configured news window")
            if group_name == "focus_news" and item["category"] not in {"macro", "policy", "geopolitics"}:
                errors.append(f"{label}: focus_news only accepts macro/policy/geopolitics categories")

    report_day = date.fromisoformat(data["meta"]["report_date"])
    previous_start = report_day - timedelta(days=7)
    previous_end = previous_start + timedelta(days=4)
    for group_name in ("economic_calendar", "earnings_calendar", "previous_economic_calendar", "previous_earnings_calendar"):
        events = data[group_name]
        if group_name.startswith("previous_"):
            if expected_type == "weekday" and events:
                errors.append(f"{group_name}: weekday reports must not contain previous-week events")
            if expected_type == "monday":
                for event in events:
                    event_day = parse_dt(event["event_date"]).date()
                    if not previous_start <= event_day <= previous_end:
                        errors.append(f"{group_name}[{event['id']}]: event date outside previous Monday-Friday window")
                    if event["status"] != "released":
                        errors.append(f"{group_name}[{event['id']}]: previous-week events must be released")
        dates = [parse_dt(item["event_date"]) for item in events]
        if dates != sorted(dates):
            errors.append(f"{group_name} must be sorted by event_date ascending")
        ids: set[str] = set()
        for index, item in enumerate(events):
            label = f"{group_name}[{index}]"
            if item["id"] in ids:
                errors.append(f"{label}: duplicate id {item['id']}")
            ids.add(item["id"])
            if group_name in {"economic_calendar", "previous_economic_calendar"}:
                if item["importance_stars"] != 3:
                    errors.append(f"{label}: only 3-star economic events are permitted")
            else:
                basis = item["importance_basis"]
                stars = item["importance_stars"]
                rating_source = item["importance_rating_source"]
                basis_source = item["importance_basis_source"].strip()
                if not basis_source:
                    errors.append(f"{label}: earnings importance basis requires a traceable source")
                if basis == "source_rating":
                    if stars != 3 or not rating_source:
                        errors.append(
                            f"{label}: source-rated earnings must carry an explicit 3-star rating and rating source"
                        )
                elif basis == "major_event_assessment":
                    if stars is not None or rating_source is not None:
                        errors.append(
                            f"{label}: assessed earnings must not display an invented star rating"
                        )
            if item["status"] == "released" and item.get("actual") is None and group_name in {"economic_calendar", "previous_economic_calendar"}:
                errors.append(f"{label}: released economic event requires actual value")
            if item["status"] == "released" and group_name in {"earnings_calendar", "previous_earnings_calendar"}:
                if item.get("eps_actual") is None and item.get("revenue_actual") is None:
                    errors.append(f"{label}: released earnings event requires EPS or revenue actual")

    for group in ("previous_economic_calendar", "previous_earnings_calendar"):
        if expected_type == "monday" and data["coverage"][group]["status"] == "not_applicable":
            errors.append(f"coverage.{group}: Monday reports must verify the previous-week section or mark it incomplete")
        if expected_type == "weekday" and data["coverage"][group]["status"] != "not_applicable":
            errors.append(f"coverage.{group}: weekday reports must mark previous-week sections not_applicable")

    for group, coverage in data["coverage"].items():
        if coverage["status"] == "complete":
            if not coverage["checked_at"] or not coverage["source_refs"]:
                errors.append(f"coverage.{group}: complete requires checked_at and at least one source reference")
        elif coverage["status"] == "not_applicable" and group not in {"previous_economic_calendar", "previous_earnings_calendar"}:
            errors.append(f"coverage.{group}: not_applicable is only valid for previous-week groups")
    summary = data["analysis"]["summary"]
    if summary["status"] == "verified" and (not summary["headline"] or not summary["text"] or not summary["source_refs"]):
        errors.append("verified summary requires headline, text and source references")
    for tab, item in data["analysis"]["market_observation_highlights"].items():
        if item["status"] == "verified" and (not item["text"] or not item["source_refs"]):
            errors.append(f"verified market observation {tab} requires text and source references")
    return errors


def self_test(validator, schema):
    sample = {
        "schema_version": 2,
        "meta": {
            "report_date": "2026-11-02",
            "trading_date": "2026-10-30",
            "generated_at": "2026-10-31T21:00:00+08:00",
            "timezone": "Asia/Taipei",
            "wr_version": "3.5",
            "template_type": "monday",
            "news_window_start": "2026-10-30T12:00:00+08:00",
            "news_window_end": "2026-11-02T05:00:00+08:00"
        },
        "focus_news": [],
        "market_headlines": [],
        "economic_calendar": [],
        "earnings_calendar": [],
        "previous_economic_calendar": [],
        "previous_earnings_calendar": [],
        "coverage": {
            group: {"status": "incomplete", "source_refs": [], "checked_at": None}
            for group in ("focus_news", "market_headlines", "economic_calendar", "earnings_calendar",
                          "previous_economic_calendar", "previous_earnings_calendar")
        },
        "analysis": {
            "summary": {"headline": None, "text": None, "source_refs": [], "status": "pending_verification"},
            "market_observation_highlights": {
                key: {"text": None, "source_refs": [], "status": "pending_verification"}
                for key in ("market_view", "key_levels", "core_observations")
            },
            "market_sentiment": {"label": None, "score": None, "text": None, "source_refs": [], "status": "pending_verification"}
        }
    }
    schema_errors = list(validator.iter_errors(sample))
    if schema_errors:
        raise AssertionError("valid pending-content sample rejected: " + "; ".join(e.message for e in schema_errors[:5]))
    if validate_report_rules(sample):
        raise AssertionError("valid pending-content sample failed report rules")
    print("PASS: complete pending-content shell accepted")

    # A confirmed empty calendar is valid only when its coverage was actually checked.
    complete_empty = json.loads(json.dumps(sample))
    complete_empty["coverage"]["economic_calendar"] = {
        "status": "complete", "source_refs": ["calendar-source"], "checked_at": "2026-10-31T20:00:00+08:00"
    }
    if validate_report_rules(complete_empty):
        raise AssertionError("verified empty calendar coverage should pass")
    print("PASS: confirmed empty calendar distinguished from incomplete collection")

    incomplete_empty = json.loads(json.dumps(sample))
    incomplete_empty["coverage"]["economic_calendar"] = {
        "status": "complete", "source_refs": [], "checked_at": None
    }
    if not any("coverage.economic_calendar: complete requires" in e for e in validate_report_rules(incomplete_empty)):
        raise AssertionError("empty complete coverage without provenance unexpectedly passed")
    print("PASS: empty calendar cannot be marked complete without provenance")

    bad = json.loads(json.dumps(sample))
    bad["meta"]["template_type"] = "weekday"
    if not validate_report_rules(bad):
        raise AssertionError("wrong Monday template type unexpectedly passed")
    print("PASS: Monday/weekday template mismatch rejected")

    bad = json.loads(json.dumps(sample))
    bad["economic_calendar"] = [
        {"id":"later","event_date":"2026-10-30T22:00:00+08:00","region":"US","event_name":"Later","importance_stars":3,"previous":None,"forecast":None,"actual":None,"status":"upcoming","impact_judgment":None,"source":{"name":"Test","url":"https://example.com/a","published_at":None,"observed_at":"2026-10-31T12:00:00+08:00"}},
        {"id":"earlier","event_date":"2026-10-30T20:00:00+08:00","region":"US","event_name":"Earlier","importance_stars":3,"previous":None,"forecast":None,"actual":None,"status":"upcoming","impact_judgment":None,"source":{"name":"Test","url":"https://example.com/b","published_at":None,"observed_at":"2026-10-31T12:00:00+08:00"}}
    ]
    if not any("sorted by event_date" in e for e in validate_report_rules(bad)):
        raise AssertionError("unsorted economic events unexpectedly passed")
    print("PASS: unsorted calendar events rejected")

    bad = json.loads(json.dumps(sample))
    bad["focus_news"] = [{
        "id":"n1","category":"company","headline":"Company news","summary":"Test summary",
        "published_at":"2026-10-31T00:00:00+08:00",
        "source":{"name":"Test","url":"https://example.com/news","published_at":"2026-10-31T00:00:00+08:00","observed_at":"2026-10-31T12:00:00+08:00"},
        "status":"verified","impact":None
    }]
    if not any("focus_news only accepts" in e for e in validate_report_rules(bad)):
        raise AssertionError("non-macro focus news unexpectedly passed")
    print("PASS: non-macro focus news rejected")

    # Earnings without provider stars may be selected only with an explicit, traceable
    # major-event assessment; they must not be assigned an invented star.
    earnings = {
        "id": "earnings-assessed",
        "event_date": "2026-11-02T21:00:00+08:00",
        "company": "Synthetic Example Corp",
        "ticker": "SYN",
        "session": "after_market",
        "importance_stars": None,
        "importance_basis": "major_event_assessment",
        "importance_basis_source": "Synthetic test: mega-cap index constituent; source evidence recorded separately",
        "importance_rating_source": None,
        "eps_estimate": None,
        "eps_actual": None,
        "revenue_estimate": None,
        "revenue_actual": None,
        "status": "upcoming",
        "stock_price_reaction": None,
        "source": {
            "name": "Synthetic IR calendar",
            "url": "https://example.com/earnings",
            "published_at": None,
            "observed_at": "2026-10-31T12:00:00+08:00"
        }
    }
    rated = json.loads(json.dumps(sample))
    rated["earnings_calendar"] = [earnings]
    schema_errors = list(validator.iter_errors(rated))
    rule_errors = validate_report_rules(rated)
    if schema_errors or rule_errors:
        raise AssertionError("unrated but sourced major-event assessment should pass: " +
                             "; ".join(e.message for e in schema_errors) + "; ".join(rule_errors))
    print("PASS: earnings may be selected without stars when major-event basis is traceable")

    bad = json.loads(json.dumps(rated))
    bad["earnings_calendar"][0]["importance_stars"] = 3
    if not any("invented star rating" in e for e in validate_report_rules(bad)):
        raise AssertionError("major-event assessment with an unsupported star unexpectedly passed")
    print("PASS: earnings assessment cannot invent a star rating")



def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    validator, schema = load_validator()
    if args.self_test:
        self_test(validator, schema)
        return 0
    if not args.file:
        parser.error("--file is required unless --self-test is used")
    data = json.loads(Path(args.file).read_text(encoding="utf-8"))
    schema_errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    rule_errors = validate_report_rules(data)
    for error in schema_errors:
        location = ".".join(str(part) for part in error.path) or "$"
        print(f"FAIL schema {location}: {error.message}", file=sys.stderr)
    for error in rule_errors:
        print(f"FAIL rule: {error}", file=sys.stderr)
    if schema_errors or rule_errors:
        print("TAC EDITORIAL CONTENT INVALID", file=sys.stderr)
        return 1
    print("PASS: TAC editorial content conforms to schema and report rules")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
