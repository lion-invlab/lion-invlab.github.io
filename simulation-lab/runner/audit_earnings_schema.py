#!/usr/bin/env python3
"""Read-only audit of the authoritative main-branch earnings calendar schema."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from collections import Counter

from calendar_source_guard import load_authoritative_calendar
from earnings_judgment import migrate_legacy_record


def present(record, key):
    value = record.get(key)
    return value is not None and value != ""


def audit(report_date: str) -> dict:
    bundle = load_authoritative_calendar(report_date)
    current = bundle["current"]
    payload = current["payload"]
    events = payload["events"]["earnings"]
    released = [e for e in events if str(e.get("status", "")).lower() in {"released", "published", "completed"}]

    result = {
        "report_date": report_date,
        "repository": bundle["current"]["repository"],
        "branch": "main",
        "main_commit_sha": bundle["main_commit_sha"],
        "calendar_path": current["path"],
        "calendar_blob_sha": current["blob_sha"],
        "week_id": current["week_id"],
        "schema_version": payload.get("schema_version"),
        "wr_version": payload.get("wr_version"),
        "updated_at": payload.get("updated_at"),
        "event_counts": {
            "economic": current["economic_count"],
            "earnings": current["earnings_count"],
            "released_earnings": len(released),
        },
        "released_status_counts": {},
        "field_coverage": {},
        "legacy_directional_status_without_v2_engine": {},
        "directional_status_without_normalized_basis": {},
        "unversioned_records": 0,
    }

    for metric in ("eps", "revenue"):
        status_key = f"{metric}_comparison_status"
        actual_key = f"{metric}_actual"
        estimate_key = f"{metric}_estimate"
        actual_basis_key = f"{metric}_actual_basis"
        estimate_basis_key = f"{metric}_estimate_basis"
        actual_code_key = f"{metric}_actual_basis_code"
        estimate_code_key = f"{metric}_estimate_basis_code"
        actual_currency_key = f"{metric}_actual_currency"
        estimate_currency_key = f"{metric}_estimate_currency"
        consensus_key = "consensus_source" if metric == "eps" else "revenue_consensus_source"

        result["released_status_counts"][metric] = dict(Counter(
            e.get(status_key) or "null" for e in released
        ))
        keys = [
            actual_key, estimate_key, actual_basis_key, estimate_basis_key,
            actual_code_key, estimate_code_key, actual_currency_key,
            estimate_currency_key, f"{metric}_actual_period",
            f"{metric}_estimate_period", consensus_key,
        ]
        if metric == "revenue":
            keys += ["revenue_actual_unit", "revenue_estimate_unit"]
        result["field_coverage"][metric] = {
            key: sum(1 for e in released if present(e, key))
            for key in keys
        }
        result["legacy_directional_status_without_v2_engine"][metric] = [
            e.get("ticker") for e in released
            if e.get(status_key) in {"beat", "miss", "inline"}
            and e.get("judgment_engine_version") != "1.0.0"
        ]
        result["directional_status_without_normalized_basis"][metric] = [
            e.get("ticker") for e in released
            if e.get(status_key) in {"beat", "miss", "inline"}
            and not (present(e, actual_code_key) and present(e, estimate_code_key))
        ]

    result["unversioned_records"] = sum(
        1 for e in released if e.get("judgment_engine_version") != "1.0.0"
    )

    migrated = [migrate_legacy_record(e, observed_at="read-only-migration-preview") for e in released]
    result["_migration_rows"] = [
        {
            "ticker": e.get("ticker"),
            "eps_legacy_status": e.get("legacy_eps_comparison_status"),
            "eps_v2_status": e.get("eps_comparison_status"),
            "eps_actual_basis_code": e.get("eps_actual_basis_code"),
            "eps_estimate_basis_code": e.get("eps_estimate_basis_code"),
            "eps_reason": e.get("eps_comparison_reason"),
            "revenue_legacy_status": e.get("legacy_revenue_comparison_status"),
            "revenue_v2_status": e.get("revenue_comparison_status"),
            "revenue_actual_basis_code": e.get("revenue_actual_basis_code"),
            "revenue_estimate_basis_code": e.get("revenue_estimate_basis_code"),
            "revenue_reason": e.get("revenue_comparison_reason"),
        }
        for e in migrated
    ]
    result["migration_preview"] = {
        "mode": "IN_MEMORY_READ_ONLY",
        "eps_status_counts": dict(Counter(e.get("eps_comparison_status") or "null" for e in migrated)),
        "revenue_status_counts": dict(Counter(e.get("revenue_comparison_status") or "null" for e in migrated)),
        "eps_directional_records": [
            {
                "ticker": e.get("ticker"),
                "legacy_status": e.get("legacy_eps_comparison_status"),
                "v2_status": e.get("eps_comparison_status"),
                "actual_basis_code": e.get("eps_actual_basis_code"),
                "estimate_basis_code": e.get("eps_estimate_basis_code"),
                "reason": e.get("eps_comparison_reason"),
            }
            for e in migrated
            if e.get("eps_comparison_status") in {"beat", "miss", "inline"}
        ],
        "revenue_directional_records": [
            {
                "ticker": e.get("ticker"),
                "legacy_status": e.get("legacy_revenue_comparison_status"),
                "v2_status": e.get("revenue_comparison_status"),
                "actual_basis_code": e.get("revenue_actual_basis_code"),
                "estimate_basis_code": e.get("revenue_estimate_basis_code"),
                "reason": e.get("revenue_comparison_reason"),
            }
            for e in migrated
            if e.get("revenue_comparison_status") in {"beat", "miss", "inline"}
        ],
        "legacy_status_changes": [
            {
                "ticker": e.get("ticker"),
                "legacy_eps_status": e.get("legacy_eps_comparison_status"),
                "v2_eps_status": e.get("eps_comparison_status"),
                "legacy_revenue_status": e.get("legacy_revenue_comparison_status"),
                "v2_revenue_status": e.get("revenue_comparison_status"),
            }
            for e in migrated
            if e.get("legacy_eps_comparison_status") != e.get("eps_comparison_status")
            or e.get("legacy_revenue_comparison_status") != e.get("revenue_comparison_status")
        ],
    }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-date", required=True, help="Taiwan report date YYYY-MM-DD")
    parser.add_argument("--output", help="Optional local JSON output path; never writes to main")
    parser.add_argument("--migration-csv", help="Optional local CSV with per-company in-memory v2 migration preview")
    args = parser.parse_args()
    result = audit(args.report_date)
    migration_rows = result.pop("_migration_rows", [])
    if args.migration_csv:
        csv_path = Path(args.migration_csv)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "ticker", "eps_legacy_status", "eps_v2_status",
            "eps_actual_basis_code", "eps_estimate_basis_code", "eps_reason",
            "revenue_legacy_status", "revenue_v2_status",
            "revenue_actual_basis_code", "revenue_estimate_basis_code", "revenue_reason",
        ]
        with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(migration_rows)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
