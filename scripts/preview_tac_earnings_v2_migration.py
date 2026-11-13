#!/usr/bin/env python3
"""Read-only v1 -> v2 earnings migration preview. Never writes source week JSON."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from tac_earnings_judgment import migrate_legacy_record


def preview_files(files: list[str]) -> tuple[list[dict], dict]:
    rows = []
    source_unchanged = True
    for file_name in files:
        path = Path(file_name)
        payload = json.loads(path.read_text(encoding="utf-8"))
        week_id = payload.get("week_id") or path.stem
        for event in payload.get("events", {}).get("earnings", []):
            if event.get("status") != "released":
                continue
            original = json.loads(json.dumps(event, ensure_ascii=False))
            migrated = migrate_legacy_record(dict(event), observed_at="read-only-migration-preview")
            source_unchanged = source_unchanged and event == original
            rows.append({
                "week_id": week_id,
                "ticker": event.get("ticker"),
                "company": event.get("company"),
                "event_id": event.get("id"),
                "eps_legacy_status": event.get("eps_comparison_status"),
                "eps_v2_status": migrated.get("eps_comparison_status"),
                "eps_reason": migrated.get("eps_comparison_reason"),
                "eps_actual_basis_code": migrated.get("eps_actual_basis_code"),
                "eps_estimate_basis_code": migrated.get("eps_estimate_basis_code"),
                "revenue_legacy_status": event.get("revenue_comparison_status"),
                "revenue_v2_status": migrated.get("revenue_comparison_status"),
                "revenue_reason": migrated.get("revenue_comparison_reason"),
                "revenue_actual_basis_code": migrated.get("revenue_actual_basis_code"),
                "revenue_estimate_basis_code": migrated.get("revenue_estimate_basis_code"),
            })
    per_week = {}
    for week_id in sorted({row["week_id"] for row in rows}):
        subset = [row for row in rows if row["week_id"] == week_id]
        per_week[week_id] = {
            "released_records": len(subset),
            "eps_status_counts": dict(Counter(row["eps_v2_status"] for row in subset)),
            "revenue_status_counts": dict(Counter(row["revenue_v2_status"] for row in subset)),
        }
    summary = {
        "mode": "IN_MEMORY_READ_ONLY",
        "source_files": files,
        "released_records": len(rows),
        "per_week": per_week,
        "eps_status_counts": dict(Counter(row["eps_v2_status"] for row in rows)),
        "revenue_status_counts": dict(Counter(row["revenue_v2_status"] for row in rows)),
        "source_records_unchanged": source_unchanged,
    }
    return rows, summary


def write_csv(rows: list[dict], output: str) -> None:
    fields = list(rows[0]) if rows else [
        "week_id", "ticker", "company", "event_id",
        "eps_legacy_status", "eps_v2_status", "eps_reason",
        "eps_actual_basis_code", "eps_estimate_basis_code",
        "revenue_legacy_status", "revenue_v2_status", "revenue_reason",
        "revenue_actual_basis_code", "revenue_estimate_basis_code",
    ]
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def self_test() -> None:
    from copy import deepcopy
    from tac_earnings_judgment import migrate_legacy_record

    record = {
        "ticker": "TEST",
        "status": "released",
        "reporting_period": "Q3 2026",
        "eps_actual": 1.2,
        "eps_estimate": 1.0,
        "eps_actual_basis": "GAAP diluted EPS (USD/share)",
        "eps_estimate_basis": "GAAP diluted EPS consensus (USD/share)",
        "source": {"url": "https://issuer.example/results", "observed_at": "2026-11-13T10:00:00+08:00"},
        "consensus_source": {"url": "https://consensus.example/eps", "observed_at": "2026-11-12T10:00:00+08:00"},
    }
    original = deepcopy(record)
    migrated = migrate_legacy_record(dict(record), observed_at="preview-test")
    assert record == original, "migration preview must not mutate source record"
    assert migrated["eps_comparison_status"] == "beat"
    assert migrated["revenue_comparison_status"] == "pending"
    print("PASS: read-only legacy migration preview")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", nargs="+", help="Week JSON files to preview without writing")
    parser.add_argument("--output", help="Optional CSV path for per-company preview")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    if args.files:
        rows, summary = preview_files(args.files)
        if args.output:
            write_csv(rows, args.output)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        if not summary["source_records_unchanged"]:
            raise SystemExit("Source mutation detected; refusing to continue")


if __name__ == "__main__":
    main()
