#!/usr/bin/env python3
"""Fail-closed validator for TAC earnings Schema v2 records."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from earnings_judgment import ENGINE_VERSION, audit_record

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/tac-earnings-record-v2.schema.json"
RELEASED_STATUSES = {"released", "published", "completed"}


def is_released_record(record: dict) -> bool:
    """Return True for records whose earnings have actually been published."""
    return str(record.get("status", "")).strip().casefold() in RELEASED_STATUSES


def validate_record(record: dict, schema: dict) -> list[str]:
    """Validate one v2 record. Legacy records are handled at payload level."""
    if record.get("judgment_engine_version") != ENGINE_VERSION:
        return []
    errors = [
        f"schema:{'.'.join(str(p) for p in err.absolute_path) or '<root>'}: {err.message}"
        for err in Draft202012Validator(schema).iter_errors(record)
    ]
    errors.extend(f"engine:{issue}" for issue in audit_record(record))
    return errors


def validate_payload(
    payload: dict,
    schema: dict,
    *,
    require_v2: bool = True,
    expected_released_count: int | None = None,
) -> dict:
    """Validate every published earnings record and fail closed on incomplete rollout.

    In strict mode every released/published earnings record must carry the current
    engine version and pass both JSON Schema and deterministic engine re-computation.
    This prevents a zero-record or partial v2 rollout from being reported as valid.
    """
    events = payload.get("events")
    records = events.get("earnings") if isinstance(events, dict) else None
    if not isinstance(records, list):
        return {
            "released_records": 0,
            "v2_records_checked": 0,
            "legacy_or_unversioned_records": 0,
            "failures": [{"index": None, "ticker": None, "issue": "missing_or_invalid_events_earnings_array"}],
            "valid": False,
        }

    released = [(i, r) for i, r in enumerate(records) if isinstance(r, dict) and is_released_record(r)]
    checked = 0
    legacy = 0
    failures = []

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            failures.append({
                "index": index, "ticker": None,
                "issue": "earnings_record_is_not_an_object",
            })

    if require_v2 and payload.get("schema_version") != 2:
        failures.append({
            "index": None, "ticker": None,
            "issue": "calendar_schema_version_must_be_2_got_" + repr(payload.get("schema_version")),
        })

    if expected_released_count is not None and len(released) != expected_released_count:
        failures.append({
            "index": None, "ticker": None,
            "issue": f"released_record_count_mismatch_expected_{expected_released_count}_got_{len(released)}",
        })

    if require_v2 and not released:
        failures.append({
            "index": None, "ticker": None,
            "issue": "no_released_earnings_records_found_v2_rollout_not_proven",
        })

    for index, record in released:
        if record.get("judgment_engine_version") != ENGINE_VERSION:
            legacy += 1
            if require_v2:
                failures.append({
                    "index": index,
                    "ticker": record.get("ticker"),
                    "issue": "released_record_missing_current_judgment_engine_version",
                })
            continue

        checked += 1
        for issue in validate_record(record, schema):
            failures.append({
                "index": index,
                "ticker": record.get("ticker"),
                "id": record.get("id"),
                "issue": issue,
            })

    return {
        "released_records": len(released),
        "v2_records_checked": checked,
        "legacy_or_unversioned_records": legacy,
        "failures": failures,
        "valid": not failures,
    }


def self_test(schema: dict) -> None:
    good = {
        "status": "released",
        "event_date": "2026-11-13T12:00:00+08:00",
        "judgment_engine_version": ENGINE_VERSION,
        "judgment_timestamp": "2026-11-13T13:00:00+08:00",
        "earnings_comparison_summary": "EPS：優於預期；營收：資料／比較口徑待核實",
        "eps_actual": 1.2, "eps_estimate": 1.0,
        "eps_actual_basis_code": "US_GAAP_DILUTED_EPS",
        "eps_estimate_basis_code": "US_GAAP_DILUTED_EPS",
        "eps_actual_currency": "USD", "eps_estimate_currency": "USD",
        "eps_actual_period": "Q3 2026", "eps_estimate_period": "Q3 2026",
        "eps_surprise": 0.2, "eps_surprise_pct": 20.0,
        "eps_comparison_status": "beat", "eps_comparison_reason": "actual_above_comparable_consensus",
        "revenue_comparison_status": "pending", "revenue_comparison_reason": "missing_or_invalid_actual_or_consensus",
        "source": {"url": "https://issuer.example/results", "observed_at": "2026-11-13T12:00:00+08:00"},
        "consensus_source": {"name": "LSEG I/B/E/S", "url": "https://consensus.example/eps", "observed_at": "2026-11-13T11:00:00+08:00", "source_level": 1},
        "eps_consensus_attempts": [{
            "source_level": 1, "provider": "LSEG I/B/E/S", "metric": "EPS",
            "url": "https://consensus.example/eps", "observed_at": "2026-11-13T11:00:00+08:00",
            "data_as_of": "2026-11-12T20:00:00+08:00", "period": "Q3 2026",
            "value": 1.0, "currency": "USD", "basis_code": "US_GAAP_DILUTED_EPS",
            "statistic": "primary_consensus", "outcome": "adopted",
            "reason": "valid_pre_release_same_basis_consensus"
        }],
    }
    assert validate_record(good, schema) == [], validate_record(good, schema)

    bad = dict(good)
    bad.pop("eps_actual_currency")
    assert validate_record(bad, schema), "directional record without separate currency must fail"

    bad = dict(good)
    bad["eps_comparison_status"] = "miss"
    assert any("stored_status_differs_from_engine_result" in x for x in validate_record(bad, schema)), "status inconsistent with engine must fail"

    # The key regression: no v2 records must never be treated as a successful rollout.
    zero_v2 = validate_payload({"events": {"earnings": [{"status": "released", "ticker": "OLD"}]}}, schema)
    assert not zero_v2["valid"]
    assert zero_v2["v2_records_checked"] == 0
    assert zero_v2["legacy_or_unversioned_records"] == 1

    empty = validate_payload({"events": {"earnings": []}}, schema)
    assert not empty["valid"], "empty released population must not prove a successful rollout"

    mixed = validate_payload({"events": {"earnings": [good, {"status": "published", "ticker": "OLD"}]}}, schema)
    assert not mixed["valid"], "one legacy published record must fail strict rollout validation"
    assert mixed["v2_records_checked"] == 1 and mixed["legacy_or_unversioned_records"] == 1

    all_v2 = validate_payload({"schema_version": 2, "events": {"earnings": [good]}}, schema)
    assert all_v2["valid"], all_v2
    wrong_schema = validate_payload({"schema_version": 1, "events": {"earnings": [good]}}, schema)
    assert not wrong_schema["valid"], "strict v2 validation must reject top-level schema v1"
    malformed = validate_payload({"schema_version": 2, "events": {"earnings": [good, None]}}, schema)
    assert not malformed["valid"], "non-object earnings rows must fail validation"
    wrong_count = validate_payload({"schema_version": 2, "events": {"earnings": [good]}}, schema, expected_released_count=2)
    assert not wrong_count["valid"], "unexpectedly missing released records must fail"

    # Diagnostic mode may inspect a pre-migration payload, but must remain explicitly non-production.
    diagnostic = validate_payload(
        {"schema_version": 1, "events": {"earnings": [{"status": "released", "ticker": "OLD"}]}},
        schema,
        require_v2=False,
    )
    assert diagnostic["valid"] and diagnostic["legacy_or_unversioned_records"] == 1

    print("PASS: v2 schema, engine consistency, zero-v2 fail-closed, mixed rollout, expected count")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="Calendar week JSON to validate")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument(
        "--allow-legacy",
        action="store_true",
        help="Diagnostic-only mode: inspect a pre-v2 payload without requiring full migration",
    )
    parser.add_argument(
        "--expected-released-count",
        type=int,
        default=None,
        help="Optional independently audited count of released earnings records",
    )
    args = parser.parse_args()

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    if args.self_test:
        self_test(schema)
    if args.file:
        payload = json.loads(Path(args.file).read_text(encoding="utf-8"))
        result = validate_payload(
            payload,
            schema,
            require_v2=not args.allow_legacy,
            expected_released_count=args.expected_released_count,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not result["valid"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
