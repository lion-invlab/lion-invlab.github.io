#!/usr/bin/env python3
"""Read-only baseline audit of an authoritative main-branch calendar JSON."""
from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter

from earnings_judgment import audit_consensus_attempts, migrate_legacy_record

RELEASED = {"released", "published", "completed"}


def git_text(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, text=True, capture_output=True).stdout.strip()


def audit(path: str) -> dict:
    main_commit = git_text("rev-parse", "origin/main")
    blob_sha = git_text("rev-parse", f"origin/main:{path}")
    raw = git_text("show", f"origin/main:{path}")
    payload = json.loads(raw)
    events = payload.get("events", {}).get("earnings", [])
    released = [item for item in events if isinstance(item, dict) and str(item.get("status", "")).casefold() in RELEASED]

    result = {
        "source_ref": "origin/main",
        "main_commit_sha": main_commit,
        "calendar_path": path,
        "calendar_blob_sha": blob_sha,
        "week_id": payload.get("week_id"),
        "schema_version": payload.get("schema_version"),
        "wr_version": payload.get("wr_version"),
        "updated_at": payload.get("updated_at"),
        "released_count": len(released),
        "metrics": {},
    }

    for metric in ("eps", "revenue"):
        migrated = [migrate_legacy_record(item, observed_at="2026-11-13T00:00:00+08:00") for item in released]
        status_key = f"{metric}_comparison_status"
        attempt_key = f"{metric}_consensus_attempts"
        attempt_issues = [
            audit_consensus_attempts(item, metric)
            for item in released
        ]
        result["metrics"][metric] = {
            "legacy_status_counts": dict(Counter(item.get(status_key) or "null" for item in released)),
            "v2_preview_status_counts": dict(Counter(item.get(status_key) or "null" for item in migrated)),
            "actual_present": sum(item.get(f"{metric}_actual") is not None for item in released),
            "actual_basis_label_present": sum(bool(item.get(f"{metric}_actual_basis")) for item in released),
            **({"legacy_eps_narrative_basis_present": sum(bool(item.get("eps_basis")) for item in released)} if metric == "eps" else {}),
            "estimate_basis_label_present": sum(bool(item.get(f"{metric}_estimate_basis")) for item in released),
            "legacy_currency_field_present": sum(bool(item.get(f"{metric}_currency")) for item in released),
            "estimate_present": sum(item.get(f"{metric}_estimate") is not None for item in released),
            "actual_basis_code_present": sum(item.get(f"{metric}_actual_basis_code") not in (None, "") for item in released),
            "estimate_basis_code_present": sum(item.get(f"{metric}_estimate_basis_code") not in (None, "") for item in released),
            "actual_currency_present": sum(item.get(f"{metric}_actual_currency") not in (None, "") for item in released),
            "estimate_currency_present": sum(item.get(f"{metric}_estimate_currency") not in (None, "") for item in released),
            "actual_period_present": sum(item.get(f"{metric}_actual_period") not in (None, "") for item in released),
            "estimate_period_present": sum(item.get(f"{metric}_estimate_period") not in (None, "") for item in released),
            "consensus_source_present": sum(isinstance(item.get("consensus_source" if metric == "eps" else "revenue_consensus_source"), dict) for item in released),
            "preview_actual_basis_code_present": sum(item.get(f"{metric}_actual_basis_code") not in (None, "") for item in migrated),
            "preview_estimate_basis_code_present": sum(item.get(f"{metric}_estimate_basis_code") not in (None, "") for item in migrated),
            "preview_actual_currency_present": sum(item.get(f"{metric}_actual_currency") not in (None, "") for item in migrated),
            "preview_estimate_currency_present": sum(item.get(f"{metric}_estimate_currency") not in (None, "") for item in migrated),
            "preview_actual_period_present": sum(item.get(f"{metric}_actual_period") not in (None, "") for item in migrated),
            "preview_estimate_period_present": sum(item.get(f"{metric}_estimate_period") not in (None, "") for item in migrated),
            **({"actual_unit_present": sum(item.get("revenue_actual_unit") not in (None, "") for item in released), "estimate_unit_present": sum(item.get("revenue_estimate_unit") not in (None, "") for item in released)} if metric == "revenue" else {}),
            **({"legacy_unit_field_present": sum(bool(item.get("revenue_unit")) for item in released)} if metric == "revenue" else {}),
            "attempt_history_present": sum(isinstance(item.get(attempt_key), list) and len(item.get(attempt_key)) > 0 for item in released),
            "attempt_history_complete": sum(issue in (None, "no_usable_consensus_after_all_priority_sources") for issue in attempt_issues),
            "attempt_issue_counts": dict(Counter(issue or "valid_adopted_source" for issue in attempt_issues)),
            "records": [
                {
                    "ticker": item.get("ticker"),
                    "legacy_status": item.get(status_key),
                    "v2_preview_status": judged.get(status_key),
                    "v2_preview_reason": judged.get(f"{metric}_comparison_reason"),
                    "attempt_count": len(item.get(attempt_key) or []) if isinstance(item.get(attempt_key), list) else 0,
                    "attempt_issue": issue,
                }
                for item, judged, issue in zip(released, migrated, attempt_issues)
            ],
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--week-path", required=True, help="Path inside origin/main, e.g. data/calendar/weeks/2026-W46.json")
    args = parser.parse_args()
    print(json.dumps(audit(args.week_path), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
