#!/usr/bin/env python3
"""Validate ChatGPT's direct webpage-read market observation package."""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "tac-investing-com-web-observations.schema.json"


def load():
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError as exc:
        raise RuntimeError("jsonschema dependency is required") from exc
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker()), schema


def coverage_report(data: dict, expected: list[str]) -> dict:
    rows = data.get("observations", [])
    ids = [row.get("asset_id") for row in rows]
    duplicates = sorted({asset_id for asset_id in ids if ids.count(asset_id) > 1})
    present = set(ids)
    missing = sorted(set(expected) - present)
    pending = sorted(
        row["asset_id"] for row in rows
        if row.get("verification_status") not in {"verified", "market_closed"}
    )
    if data.get("fedwatch", {}).get("verification_status") != "verified":
        pending.append("fedwatch")
    return {
        "expected_count": len(expected),
        "received_count": len(rows),
        "missing_asset_ids": missing,
        "duplicate_asset_ids": duplicates,
        "unverified_asset_ids": pending,
        "complete": not missing and not duplicates and not pending,
    }


def validate(data: dict, validator, schema: dict, require_complete: bool = False) -> tuple[list[str], dict]:
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    messages = []
    for error in errors:
        location = ".".join(str(x) for x in error.path) or "$"
        messages.append(f"{location}: {error.message}")
    expected = schema["properties"]["expected_asset_ids"]["const"]
    report = coverage_report(data, expected)
    if report["duplicate_asset_ids"]:
        messages.append("duplicate asset_id values are not allowed")
    if require_complete and not report["complete"]:
        messages.append("market observation coverage is incomplete")
    return messages, report


def sample(schema: dict) -> dict:
    expected = schema["properties"]["expected_asset_ids"]["const"]
    return {
        "schema_version": 1,
        "meta": {
            "report_date": "2026-11-02",
            "trading_date": "2026-10-30",
            "generated_at": "2026-11-01T09:00:00+08:00",
            "timezone": "Asia/Taipei",
            "wr_version": "3.10",
            "capture_operator": "ChatGPT direct webpage review",
        },
        "expected_asset_ids": expected,
        "observations": [
            {
                "asset_id": asset_id,
                "instrument": asset_id,
                "value_type": "price",
                "value": None,
                "change": None,
                "change_unit": None,
                "unit": "not_yet_observed",
                "currency": None,
                "quote_basis": "historical_close",
                "data_date": None,
                "observed_at": "2026-11-01T09:00:00+08:00",
                "source": None,
                "retrieval_method": "chatgpt_direct_webpage_read",
                "verification_status": "pending_verification",
                "fallback_used": False,
                "fallback_reason": None,
                "notes": "Self-test pending record; not a market quote.",
            }
            for asset_id in expected
        ],
        "fedwatch": {
            "target_meeting": None, "updated_at": None, "source": None,
            "probabilities": [], "retrieval_method": "chatgpt_direct_webpage_read",
            "verification_status": "pending_verification",
            "notes": "Self-test pending record; not a live probability snapshot."
        },
    }


def self_test(validator, schema):
    data = sample(schema)
    errors, report = validate(data, validator, schema)
    if errors or report["complete"]:
        raise AssertionError("complete pending fixture should be structurally valid but incomplete")
    print("PASS: all 45 pending observations validate as structurally valid/incomplete")

    bad = copy.deepcopy(data)
    bad["observations"][0]["verification_status"] = "verified"
    errors, _ = validate(bad, validator, schema)
    if not errors:
        raise AssertionError("verified record without value/date/source was accepted")
    print("PASS: verified observation without value/date/source rejected")

    bad = copy.deepcopy(data)
    bad["observations"].append(copy.deepcopy(bad["observations"][0]))
    errors, report = validate(bad, validator, schema)
    if not errors or not report["duplicate_asset_ids"]:
        raise AssertionError("duplicate asset_id was accepted")
    print("PASS: duplicate asset_id rejected")

    bad = copy.deepcopy(data)
    bad["observations"][0]["fallback_used"] = True
    errors, _ = validate(bad, validator, schema)
    if not errors:
        raise AssertionError("fallback without reason was accepted")
    print("PASS: fallback without reason rejected")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file")
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    validator, schema = load()
    if args.self_test:
        self_test(validator, schema)
        return 0
    if not args.file:
        parser.error("--file is required unless --self-test is used")
    data = json.loads(Path(args.file).read_text(encoding="utf-8"))
    errors, report = validate(data, validator, schema, args.require_complete)
    print(json.dumps({"coverage": report, "errors": errors}, ensure_ascii=False, indent=2))
    if errors:
        print("TAC WEB OBSERVATION VALIDATION FAILED", file=sys.stderr)
        return 1
    print("TAC WEB OBSERVATION STRUCTURE VALID")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
