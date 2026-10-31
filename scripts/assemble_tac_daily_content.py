#!/usr/bin/env python3
"""Assemble independently sourced TAC editorial fragments without inventing content."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from validate_tac_daily_content import load_validator, validate_report_rules

ARRAY_GROUPS = ("focus_news", "market_headlines", "economic_calendar", "earnings_calendar")


def empty_content(report_date: str, trading_date: str, generated_at: str, wr_version: str = "3.5") -> dict:
    report_day = date.fromisoformat(report_date)
    expected_template = "monday" if report_day.weekday() == 0 else "weekday"
    if report_day.weekday() > 4:
        raise ValueError("weekend report dates are not eligible for automatic production")
    return {
        "schema_version": 1,
        "meta": {
            "report_date": report_day.isoformat(),
            "trading_date": date.fromisoformat(trading_date).isoformat(),
            "generated_at": generated_at,
            "timezone": "Asia/Taipei",
            "wr_version": wr_version,
            "template_type": expected_template,
            "news_window_start": None,
            "news_window_end": None,
        },
        "focus_news": [],
        "market_headlines": [],
        "economic_calendar": [],
        "earnings_calendar": [],
        "analysis": {
            "summary": {"text": None, "source_refs": [], "status": "pending_verification"},
            "market_observation_highlights": [],
            "market_sentiment": {
                "label": None, "score": None, "text": None,
                "source_refs": [], "status": "pending_verification"
            },
        },
    }


def assemble(report_date: str, trading_date: str, generated_at: str,
             fragments: list[dict], validator, schema) -> dict:
    result = empty_content(report_date, trading_date, generated_at)
    seen = {group: set() for group in ARRAY_GROUPS}
    scalar_seen = set()

    for index, fragment in enumerate(fragments):
        if not isinstance(fragment, dict):
            raise ValueError(f"fragment[{index}] must be an object")
        for field, expected in (("report_date", report_date), ("trading_date", trading_date)):
            actual = fragment.get(field)
            if actual is not None and actual != expected:
                raise ValueError(f"fragment[{index}] {field} mismatch: {actual} != {expected}")
        if fragment.get("template_type") not in (None, result["meta"]["template_type"]):
            raise ValueError(f"fragment[{index}] template_type mismatch")
        if fragment.get("news_window"):
            window = fragment["news_window"]
            if not isinstance(window, dict) or set(window) - {"start", "end"}:
                raise ValueError(f"fragment[{index}] news_window must contain only start/end")
            for key, meta_key in (("start", "news_window_start"), ("end", "news_window_end")):
                value = window.get(key)
                if value:
                    existing = result["meta"][meta_key]
                    if existing and existing != value:
                        raise ValueError(f"conflicting news window {meta_key}: {existing} vs {value}")
                    result["meta"][meta_key] = value

        found = False
        for group in ARRAY_GROUPS:
            if group not in fragment:
                continue
            found = True
            records = fragment[group]
            if not isinstance(records, list):
                raise ValueError(f"fragment[{index}].{group} must be an array")
            for record in records:
                if not isinstance(record, dict) or not record.get("id"):
                    raise ValueError(f"fragment[{index}].{group} record must have a stable id")
                record_id = record["id"]
                if record_id in seen[group]:
                    raise ValueError(f"duplicate {group} id across fragments: {record_id}")
                seen[group].add(record_id)
                result[group].append(record)

        for group in ("analysis",):
            if group not in fragment:
                continue
            found = True
            analysis = fragment[group]
            if not isinstance(analysis, dict):
                raise ValueError("analysis fragment must be an object")
            for key, value in analysis.items():
                if key not in result["analysis"]:
                    raise ValueError(f"unknown analysis field: {key}")
                if key in scalar_seen:
                    raise ValueError(f"duplicate analysis field across fragments: {key}")
                scalar_seen.add(key)
                if key == "market_observation_highlights":
                    if not isinstance(value, list):
                        raise ValueError("market_observation_highlights must be an array")
                    result["analysis"][key] = value
                elif key == "summary":
                    result["analysis"][key] = value
                elif key == "market_sentiment":
                    result["analysis"][key] = value
        if not found:
            raise ValueError(f"fragment[{index}] contains no recognized editorial group")

    errors = list(validator.iter_errors(result))
    if errors:
        details = []
        for error in errors:
            location = ".".join(str(part) for part in error.path) or "$"
            details.append(f"{location}: {error.message}")
        raise ValueError("assembled editorial content failed schema validation: " + "; ".join(details))
    rule_errors = validate_report_rules(result)
    if rule_errors:
        raise ValueError("assembled editorial content failed report rules: " + "; ".join(rule_errors))
    return result


def self_test():
    validator, schema = load_validator()
    generated = "2026-10-31T12:00:00+08:00"
    sample = {
        "report_date": "2026-11-02",
        "trading_date": "2026-10-30",
        "news_window": {
            "start": "2026-10-30T12:00:00+08:00",
            "end": "2026-11-02T05:00:00+08:00"
        },
        "focus_news": [{
            "id": "focus-1", "category": "macro", "headline": "Synthetic macro headline",
            "summary": "Synthetic summary for testing only",
            "published_at": "2026-10-31T08:00:00+08:00",
            "source": {"name":"Synthetic source","url":"https://example.com/story",
                       "published_at":"2026-10-31T08:00:00+08:00",
                       "observed_at":generated},
            "status":"verified","impact":None
        }]
    }
    assembled = assemble("2026-11-02","2026-10-30",generated,[sample],validator,schema)
    assert assembled["meta"]["template_type"] == "monday"
    assert len(assembled["focus_news"]) == 1
    assert assembled["market_headlines"] == []
    assert assembled["analysis"]["summary"]["status"] == "pending_verification"
    print("PASS: source fragment assembled with Monday template metadata")
    print("PASS: missing news and analysis remain empty/pending; no placeholder content invented")

    try:
        assemble("2026-11-02","2026-10-30",generated,[sample,sample],validator,schema)
    except ValueError as exc:
        assert "duplicate focus_news id" in str(exc)
    else:
        raise AssertionError("duplicate editorial IDs must be rejected")
    print("PASS: duplicate editorial item IDs rejected")

    try:
        assemble("2026-11-02","2026-10-30",generated,
                 [dict(sample, trading_date="2026-10-29")],validator,schema)
    except ValueError as exc:
        assert "trading_date mismatch" in str(exc)
    else:
        raise AssertionError("mismatched trading date must be rejected")
    print("PASS: mismatched trading date rejected")

    try:
        assemble("2026-11-02","2026-10-30",generated,
                 [dict(sample, news_window={"start":"2026-11-02T05:00:00+08:00",
                                            "end":"2026-10-30T12:00:00+08:00"})],
                 validator,schema)
    except ValueError as exc:
        assert "news_window_start must precede" in str(exc)
    else:
        raise AssertionError("invalid news window must be rejected")
    print("PASS: invalid news time window rejected")


def main():
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
    if not all((args.report_date,args.trading_date,args.output)) or not args.fragment:
        parser.error("--report-date, --trading-date, --output and at least one --fragment are required")
    generated = args.generated_at or datetime.now(timezone.utc).isoformat()
    validator, schema = load_validator()
    fragments = [json.loads(Path(p).read_text(encoding="utf-8")) for p in args.fragment]
    result = assemble(args.report_date,args.trading_date,generated,fragments,validator,schema)
    output = Path(args.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Editorial content assembled and validated")
    for group in ARRAY_GROUPS:
        print(f"{group}: {len(result[group])} items")
    print("Analysis summary:",result["analysis"]["summary"]["status"])
    print("Market sentiment:",result["analysis"]["market_sentiment"]["status"])
    print("Saved "+str(output))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("FAIL: "+str(exc),file=sys.stderr)
        raise SystemExit(1)
