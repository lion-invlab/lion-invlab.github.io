#!/usr/bin/env python3
"""Assemble source fragments into a complete, schema-valid TAC daily snapshot.

Missing fields remain pending_verification. This script never fetches market data
and never edits an HTML report or approved mother template.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from validate_tac_daily_snapshot import load_validator, sample_snapshot

DATA_GROUPS = (
    "global_indices",
    "sectors",
    "bonds",
    "fx",
    "energy",
    "precious_metals",
    "risk_indicators",
    "news",
    "economic_calendar",
    "earnings_calendar",
    "narrative",
)

MARKET_RECORD_GROUPS = ("global_indices", "sectors", "bonds", "fx", "energy", "precious_metals", "risk_indicators")


def assemble(report_date: str, trading_date: str, generated_at: str,
             fragments: list[dict], validator, schema) -> dict:
    report_day = date.fromisoformat(report_date)
    trading_day = date.fromisoformat(trading_date)
    snapshot = sample_snapshot(schema)
    snapshot["meta"].update({
        "report_date": report_day.isoformat(),
        "trading_date": trading_day.isoformat(),
        "generated_at": generated_at,
    })

    seen: dict[str, set[str]] = {group: set() for group in DATA_GROUPS}
    fedwatch_seen = False

    for fragment in fragments:
        fragment_report = fragment.get("report_date")
        fragment_trading = fragment.get("trading_date")
        if fragment_report and fragment_report != report_day.isoformat():
            raise ValueError(
                f"fragment report_date mismatch: {fragment_report} != {report_day.isoformat()}"
            )
        if fragment_trading and fragment_trading != trading_day.isoformat():
            raise ValueError(
                f"fragment trading_date mismatch: {fragment_trading} != {trading_day.isoformat()}"
            )

        found_group = False
        for group in DATA_GROUPS:
            if group not in fragment:
                continue
            found_group = True
            records = fragment[group]
            if not isinstance(records, dict):
                raise ValueError(f"fragment group {group} must be an object")
            expected_fields = set(snapshot[group])
            unexpected = set(records) - expected_fields
            if unexpected:
                raise ValueError(f"unexpected {group} fields: {sorted(unexpected)}")
            duplicates = seen[group] & set(records)
            if duplicates:
                raise ValueError(f"duplicate {group} fields across fragments: {sorted(duplicates)}")
            snapshot[group].update(records)
            seen[group].update(records)

        if "fedwatch" in fragment:
            found_group = True
            if fedwatch_seen:
                raise ValueError("multiple FedWatch fragments supplied")
            if not isinstance(fragment["fedwatch"], dict):
                raise ValueError("fragment group fedwatch must be an object")
            snapshot["fedwatch"] = fragment["fedwatch"]
            fedwatch_seen = True

        if not found_group:
            raise ValueError("fragment contains no recognized TAC data group")

    errors = sorted(validator.iter_errors(snapshot), key=lambda error: list(error.path))
    if errors:
        details = []
        for error in errors:
            location = ".".join(str(part) for part in error.path) or "$"
            details.append(f"{location}: {error.message}")
        raise ValueError("assembled snapshot failed schema validation: " + "; ".join(details))

    return snapshot


def self_test() -> None:
    validator, schema = load_validator()
    timestamp = "2026-10-31T12:00:00+00:00"
    record = {
        "value": 7000.0,
        "unit": "index_point",
        "change": 1.25,
        "change_unit": "percent",
        "status": "verified",
        "source": {
            "name": "Synthetic test source",
            "url": "https://example.com/market",
            "observed_at": timestamp,
            "data_date": "2026-10-30",
            "quote_type": "daily_close",
            "instrument": "S&P 500",
        },
        "fallback_used": False,
        "fallback_reason": None,
        "notes": "Synthetic assembler self-test only",
    }
    fragment = {
        "dataset": "synthetic_test",
        "report_date": "2026-11-02",
        "trading_date": "2026-10-30",
        "fetched_at": timestamp,
        "global_indices": {"sp500": record},
    }
    result = assemble("2026-11-02", "2026-10-30", timestamp,
                      [fragment], validator, schema)
    assert result["global_indices"]["sp500"]["value"] == 7000.0
    assert result["global_indices"]["dow"]["status"] == "pending_verification"
    assert result["bonds"]["us_10y"]["status"] == "pending_verification"
    print("PASS: fragment merged into normalized snapshot")
    print("PASS: absent fields remain pending_verification")
    print("PASS: complete assembled snapshot conforms to JSON Schema")

    source={"name":"Reuters","url":"https://www.reuters.com/world/","observed_at":timestamp,"data_date":"2026-10-30","quote_type":"original_article","instrument":"macro news"}
    content_fragment={
        "news":{"global_focus":[{"title":"Verified story","summary":"Original article summary","published_at":timestamp,"source":source,"related_sources":[],"notes":""}],"market_headlines":[],"global_focus_meta":"Window test","market_headlines_meta":"Window test","notes":"Synthetic content test"},
        "economic_calendar":{"events":[{"event_id":"us-cpi","name":"US CPI","country":"US","event_time":timestamp,"importance":3,"status":"published","previous":"3.0%","forecast":"3.1%","actual":"3.2%","impact":"Inflation surprise","source":source,"notes":""}],"notes":"3-star only"},
        "earnings_calendar":{"events":[],"notes":"No synthetic earnings"},
        "narrative":{"status":"verified","summary_title":"Market Summary","summary":[{"label":"主軸｜","text":"A"},{"label":"跨市場｜","text":"B"},{"label":"風險｜","text":"C"},{"label":"操作｜","text":"D"}],"market_sentiment":"Risk-off","market_observation":"Breadth weakened","core_observation":"Rates remain key","key_levels":"待核實","notes":"Synthetic content test"}
    }
    merged=assemble("2026-11-02","2026-10-30",timestamp,[fragment,content_fragment],validator,schema)
    assert len(merged["news"]["global_focus"])==1
    assert merged["economic_calendar"]["events"][0]["importance"]==3
    assert merged["narrative"]["status"]=="verified"
    print("PASS: content fragments merge with market data and enforce 3-star events")

    try:
        assemble("2026-11-02","2026-10-30",timestamp,[fragment,content_fragment,content_fragment],validator,schema)
    except ValueError as exc:
        assert "duplicate news fields" in str(exc)
    else:
        raise AssertionError("duplicate content group overwrite must be rejected")
    print("PASS: duplicate news/calendar content fragments rejected")

    try:
        assemble("2026-11-02", "2026-10-30", timestamp,
                 [dict(fragment, trading_date="2026-10-29")], validator, schema)
    except ValueError as exc:
        assert "trading_date mismatch" in str(exc)
    else:
        raise AssertionError("mismatched trading date must be rejected")
    print("PASS: mismatched trading date rejected")

    try:
        assemble("2026-11-02", "2026-10-30", timestamp,
                 [fragment, fragment], validator, schema)
    except ValueError as exc:
        assert "duplicate global_indices fields" in str(exc)
    else:
        raise AssertionError("duplicate field overwrite must be rejected")
    print("PASS: duplicate field overwrite rejected")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-date")
    parser.add_argument("--trading-date")
    parser.add_argument("--generated-at")
    parser.add_argument("--fragment", action="append", default=[])
    parser.add_argument("--output")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0
    if not all((args.report_date, args.trading_date, args.output)):
        parser.error("--report-date, --trading-date and --output are required")
    if not args.fragment:
        parser.error("at least one --fragment is required")

    generated_at = args.generated_at or datetime.now(timezone.utc).isoformat()
    validator, schema = load_validator()
    fragments = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.fragment]
    snapshot = assemble(args.report_date, args.trading_date, generated_at,
                        fragments, validator, schema)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    verified = 0
    pending = 0
    for group in MARKET_RECORD_GROUPS:
        for item in snapshot[group].values():
            if item["status"] == "verified":
                verified += 1
            elif item["status"] == "pending_verification":
                pending += 1
    print(f"Snapshot assembled: {verified} verified records; {pending} pending_verification records")
    print(f"FedWatch status: {snapshot['fedwatch']['status']}")
    print("Schema validation: PASS")
    print("Saved " + str(output))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("FAIL: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
