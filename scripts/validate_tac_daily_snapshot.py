#!/usr/bin/env python3
"""Validate normalized TAC daily market snapshots against the checked-in JSON Schema."""
from __future__ import annotations
import argparse
import copy
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "tac-daily-market-snapshot.schema.json"

def load_validator():
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError:
        raise RuntimeError("Missing dependency: install jsonschema before validating TAC snapshots")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker()), schema

def sample_snapshot(schema):
    props = schema["properties"]
    snapshot = {
        "schema_version": 1,
        "meta": {
            "report_date": "2026-11-02",
            "trading_date": "2026-10-30",
            "generated_at": "2026-10-31T11:00:00+08:00",
            "timezone": "Asia/Taipei",
            "wr_version": "3.5",
        },
    }
    for group in ("global_indices", "sectors", "bonds", "fx", "energy", "precious_metals", "risk_indicators"):
        snapshot[group] = {}
        for key in props[group]["required"]:
            snapshot[group][key] = {
                "value": None, "unit": "index_point", "change": None,
                "change_unit": None, "status": "pending_verification",
                "source": None, "fallback_used": False,
                "fallback_reason": None, "notes": "Awaiting source retrieval",
            }
    snapshot["news"] = {"global_focus": [], "market_headlines": [], "global_focus_meta": "待核實", "market_headlines_meta": "待核實", "notes": "Awaiting source-linked news retrieval"}
    snapshot["economic_calendar"] = {"events": [], "notes": "Awaiting Investing.com 3-star event retrieval"}
    snapshot["earnings_calendar"] = {"events": [], "notes": "Awaiting 3-star earnings retrieval"}
    snapshot["narrative"] = {"status": "pending_verification", "summary_title": "", "summary": [], "market_sentiment": "",
                             "market_observation": "", "core_observation": "", "key_levels": "",
                             "notes": "Awaiting verified market data and event synthesis"}
    snapshot["fedwatch"] = {
        "target_meeting": None, "updated_at": None, "source": None,
        "probabilities": [], "status": "pending_verification",
        "notes": "Awaiting current meeting snapshot",
    }
    return snapshot

def self_test(validator, schema):
    valid = sample_snapshot(schema)
    errors = list(validator.iter_errors(valid))
    if errors:
        raise AssertionError("valid pending-data snapshot rejected: " + "; ".join(e.message for e in errors[:5]))
    print("PASS: complete pending-data snapshot accepted")

    bad_verified = copy.deepcopy(valid)
    bad_verified["global_indices"]["sp500"]["status"] = "verified"
    errors = list(validator.iter_errors(bad_verified))
    if not errors:
        raise AssertionError("verified record with null value/source unexpectedly passed")
    print("PASS: verified record without value/source rejected")

    bad_fallback = copy.deepcopy(valid)
    bad_fallback["fx"]["usd_twd"]["fallback_used"] = True
    errors = list(validator.iter_errors(bad_fallback))
    if not errors:
        raise AssertionError("fallback without reason unexpectedly passed")
    print("PASS: fallback without reason rejected")

    bad_field = copy.deepcopy(valid)
    del bad_field["global_indices"]["sox"]
    errors = list(validator.iter_errors(bad_field))
    if not errors:
        raise AssertionError("missing required market field unexpectedly passed")
    print("PASS: missing required market field rejected")

    content_valid=copy.deepcopy(valid)
    source={"name":"Reuters","url":"https://www.reuters.com/world/","observed_at":"2026-10-31T12:00:00+00:00","data_date":"2026-10-30","quote_type":"original_article","instrument":"macro news"}
    content_valid["news"]["global_focus"]=[{"title":"Verified macro story","summary":"Original report summary.","published_at":"2026-10-30T18:00:00+00:00","source":source,"notes":""}]
    content_valid["economic_calendar"]["events"]=[{"event_id":"us-cpi-2026-10","name":"US CPI","country":"US","event_time":"2026-10-30T20:30:00+00:00","importance":3,"status":"published","previous":"3.0%","forecast":"3.1%","actual":"3.2%","impact":"Inflation surprise","source":source,"notes":""}]
    content_valid["earnings_calendar"]["events"]=[{"event_id":"abc-q3-2026","company":"Example Corp","ticker":"ABC","report_time":"2026-10-30T20:00:00+00:00","session":"pre_market","importance":3,"status":"published","eps_actual":"1.20","eps_estimate":"1.10","revenue_actual":"10B","revenue_estimate":"9.8B","stock_reaction":"+2%","analysis":"Beat expectations","source":source,"notes":""}]
    content_valid["narrative"]={"status":"verified","summary_title":"市場觀察摘要","summary":[{"label":"市場主軸｜","text":"A"},{"label":"跨市場｜","text":"B"},{"label":"風險訊號｜","text":"C"},{"label":"操作結論｜","text":"D"}],"market_sentiment":"Risk-off","market_observation":"Breadth weakened","core_observation":"Rates remain key","key_levels":"待核實","notes":"Synthetic schema test"}
    errors=list(validator.iter_errors(content_valid))
    if errors: raise AssertionError("valid content contract rejected: "+"; ".join(e.message for e in errors[:5]))
    print("PASS: source-linked news, 3-star calendars and verified narrative accepted")

    bad_star=copy.deepcopy(content_valid)
    bad_star["economic_calendar"]["events"][0]["importance"]=2
    errors=list(validator.iter_errors(bad_star))
    if not errors: raise AssertionError("economic event below 3-star threshold unexpectedly accepted")
    bad_star=copy.deepcopy(content_valid)
    bad_star["earnings_calendar"]["events"][0]["importance"]=5
    errors=list(validator.iter_errors(bad_star))
    if not errors: raise AssertionError("legacy five-star earnings unexpectedly accepted")
    print("PASS: non-3-star calendar events and legacy five-star ratings rejected")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="Snapshot JSON file to validate")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    validator, schema = load_validator()
    if args.self_test:
        self_test(validator, schema)
        return 0
    if not args.file:
        parser.error("--file is required unless --self-test is used")
    path = Path(args.file)
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    if errors:
        for error in errors:
            location = ".".join(str(x) for x in error.path) or "$"
            print("FAIL " + location + ": " + error.message, file=sys.stderr)
        print("TAC MARKET SNAPSHOT INVALID", file=sys.stderr)
        return 1
    print("PASS: TAC market snapshot conforms to schema")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
