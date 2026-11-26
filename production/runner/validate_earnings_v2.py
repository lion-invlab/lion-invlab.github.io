#!/usr/bin/env python3
"""Validate v2 earnings records against JSON Schema and the single judgment engine."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from earnings_judgment import ENGINE_VERSION, audit_record

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/tac-earnings-record-v2.schema.json"


def validate_record(record: dict, schema: dict) -> list[str]:
    if record.get("judgment_engine_version") != ENGINE_VERSION:
        return []
    errors = [
        f"schema:{'.'.join(str(p) for p in err.absolute_path) or '<root>'}: {err.message}"
        for err in Draft202012Validator(schema).iter_errors(record)
    ]
    errors.extend(f"engine:{issue}" for issue in audit_record(record))
    return errors


def validate_payload(payload: dict, schema: dict) -> dict:
    records = payload.get("events", {}).get("earnings", [])
    checked = 0
    failures = []
    for index, record in enumerate(records):
        if record.get("judgment_engine_version") != ENGINE_VERSION:
            continue
        checked += 1
        for issue in validate_record(record, schema):
            failures.append({"index": index, "ticker": record.get("ticker"), "id": record.get("id"), "issue": issue})
    return {"schema_version": payload.get("schema_version"), "v2_records_checked": checked, "failures": failures, "valid": not failures}


def self_test(schema: dict) -> None:
    # Numerical comparisons are valid without PIT snapshots or detailed basis codes.
    good = {
        "judgment_engine_version": ENGINE_VERSION,
        "judgment_timestamp": "2026-11-13T13:00:00+08:00",
        "earnings_comparison_summary": "EPS：優於預期；營收：尚未公布／數值尚未齊備",
        "eps_actual": 1.2, "eps_estimate": 1.0,
        "eps_comparison_status": "beat",
        "eps_comparison_reason": "actual_above_platform_consensus",
        "eps_surprise": 0.2, "eps_surprise_pct": 20.0,
        "revenue_actual": None, "revenue_estimate": 8.0,
        "revenue_comparison_status": "pending",
        "revenue_comparison_reason": "actual_or_consensus_not_yet_available",
    }
    assert validate_record(good, schema) == [], validate_record(good, schema)
    bad = dict(good)
    bad["eps_comparison_status"] = "miss"
    assert any("stored_status_differs_from_engine_result" in x for x in validate_record(bad, schema)), "status inconsistent with numerical engine result must fail"
    assert validate_record({"judgment_engine_version": "legacy"}, schema) == [], "legacy records are outside v2 validation"
    print("PASS: practical earnings schema, numerical engine consistency, no PIT/basis evidence gate, legacy compatibility")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="Calendar week JSON to validate; only versioned v2 earnings records are checked")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    if args.self_test:
        self_test(schema)
    if args.file:
        payload = json.loads(Path(args.file).read_text(encoding="utf-8"))
        result = validate_payload(payload, schema)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not result["valid"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
