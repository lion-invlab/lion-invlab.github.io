#!/usr/bin/env python3
"""Negative and positive tests for the pre-build Stage 2-4 input receipt."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from build_market_source_verification_manifest import build_manifest
from validate_market_snapshot import validate_market_snapshot
from validate_prebuild_stage_inputs import build_receipt, validate_branch, validate_market_inputs, validate_stage4
from build_review_html import apply_market_source_verification_manifest

FIXTURE = Path("simulation-lab/fixtures/report-data-2026-11-23.json")


def expect_error(fn, fragment: str) -> None:
    try:
        fn()
    except ValueError as exc:
        assert fragment in str(exc), str(exc)
    else:
        raise AssertionError(f"expected ValueError containing {fragment!r}")


def calendar_item(week_id: str, start: str, end: str, econ: int, earnings: int, commit: str) -> dict:
    year, week = week_id.split("-W")
    return {
        "repository": "lion-invlab/lion-invlab.github.io",
        "branch": "main",
        "path": f"data/calendar/weeks/{week_id}.json",
        "commit_sha": commit,
        "blob_sha": ("a" if week == "48" else "b") * 40,
        "week_id": week_id,
        "week_start": start,
        "week_end": end,
        "economic_count": econ,
        "earnings_count": earnings,
        "payload": {
            "week_id": week_id,
            "events": {
                "economic": [{"id": f"{week_id}-e-{i}"} for i in range(econ)],
                "earnings": [{"id": f"{week_id}-r-{i}"} for i in range(earnings)],
            },
        },
    }


def main() -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    report_date = "2026-11-23"
    audit = validate_market_snapshot(data, report_date)
    manifest = build_manifest(data, report_date)
    commit = "c" * 40
    bundle = {
        "main_commit_sha": commit,
        "current": calendar_item("2026-W48", "2026-11-23", "2026-11-29", 27, 11, commit),
        "previous": calendar_item("2026-W47", "2026-11-16", "2026-11-22", 2, 1, commit),
    }
    # A complete 44-row register with zero verified observations is valid input:
    # the report can build, but every unverified quote must render as 待核實.
    pending_result = validate_market_inputs(data, audit, manifest, report_date)
    assert pending_result["indicator_count"] == 44
    assert pending_result["numeric_values_reconciled_count"] == 0
    assert manifest["pending_count"] == 44
    expect_error(lambda: build_receipt(
        data=data, fixture_sha256="1" * 64,
        audit=audit, audit_sha256="2" * 64,
        manifest=manifest, manifest_sha256="3" * 64,
        calendar_bundle=bundle,
        repository="lion-invlab/lion-invlab.github.io",
        branch="simulation/tac-process-lab-2026-11-06",
        workflow_run_id="45010119942", workflow_run_attempt="1",
    ), "market source observation manifest is neither PASS nor PARTIAL")

    # Builder must not leak fixture-carried quote values when current-run source
    # observations are unavailable.
    pending_data = copy.deepcopy(data)
    overlay = apply_market_source_verification_manifest(pending_data, manifest)
    closed_rows = [row for row in manifest["rows"] if row.get("verification_status") == "CLOSED"]
    assert overlay["verified_count"] == 0
    assert overlay["pending_count"] == 44
    assert overlay["closed_count"] == len(closed_rows)
    assert overlay["status"] == "PENDING"
    for row in manifest["rows"]:
        group, name = row["group"], row["name"]
        if row.get("verification_status") == "CLOSED":
            assert pending_data[group][name]["display"] == "休市"
            assert pending_data[group][name]["change_display"] == "—"
        elif group == "sectors":
            assert pending_data["sectors"][name] == "待核實"
        else:
            assert pending_data[group][name]["display"] == "待核實"
            assert pending_data[group][name]["change_display"] == "待核實"

    # Positive Gate contract: synthetic test-only observations prove that a
    # complete current-run 44-row evidence bundle can pass without fixture reuse.
    synthetic = copy.deepcopy(manifest)
    synthetic.update({
        "status": "PASS", "verification_scope": "CURRENT_REPORT_SESSION_SOURCE_OBSERVATIONS",
        "source_pages_fetched": True, "displayed_values_independently_reconciled": True,
        "prior_observation_reused_count": 0, "verified_count": 44, "pending_count": 0,
        "browser_observation_records_complete": True, "observation_record_hash_missing_count": 0,
    })
    for row in synthetic["rows"]:
        row.update({
            "verification_status": "VERIFIED", "source_page_fetched": True,
            "display_value_reconciled": True, "display_value_matches_saved_observation": True,
            "observation_provenance": "CURRENT_RUN_BROWSER_OBSERVATION",
            "observation_record_sha256": "a" * 64,
            "browser_observation_record": {
                "source_url": row["source_url"], "data_date": data["trading_date"],
                "observed_value": "100.00", "observed_change": "1.00",
                "checked_at_tw": "2026-11-23T11:00:00Z",
            },
        })
    positive = validate_market_inputs(data, audit, synthetic, report_date)
    assert positive["indicator_count"] == 44
    assert positive["prior_observations_reused"] == 0
    assert positive["source_pages_fetched_this_run"] is True
    assert positive["numeric_values_reconciled_this_run"] is True

    # Partial is a valid production input state: keep all 44 fixed rows,
    # preserve 43 current-session observations, and leave one row explicitly pending.
    partial = copy.deepcopy(synthetic)
    partial["status"] = "PARTIAL"
    partial["verified_count"] = 43
    partial["pending_count"] = 1
    partial["displayed_values_independently_reconciled"] = False
    partial["browser_observation_records_complete"] = False
    pending_row = partial["rows"][0]
    pending_row.update({
        "verification_status": "PENDING_CURRENT_RUN_BROWSER_OBSERVATION",
        "source_page_fetched": False,
        "display_value_reconciled": False,
        "display_value_matches_saved_observation": False,
        "observation_provenance": "NO_COMPLETE_CURRENT_RUN_OBSERVATION",
        "browser_observation_record": None,
        "observation_record_sha256": None,
    })
    partial_result = validate_market_inputs(data, audit, partial, report_date)
    assert partial_result["indicator_count"] == 44
    assert partial_result["numeric_values_reconciled_count"] == 43
    assert partial_result["numeric_values_reconciled_this_run"] is False
    partial_receipt = build_receipt(
        data=data, fixture_sha256="1" * 64,
        audit=audit, audit_sha256="2" * 64,
        manifest=partial, manifest_sha256="3" * 64,
        calendar_bundle=bundle,
        repository="lion-invlab/lion-invlab.github.io",
        branch="simulation/tac-process-lab-2026-11-06",
        workflow_run_id="45010119942", workflow_run_attempt="1",
    )
    assert partial_receipt["status"] == "PASS"
    assert partial_receipt["stage_2_market"]["pending_observation_count"] == 1
    expect_error(lambda: validate_branch("lion-invlab/lion-invlab.github.io", "main"),
                 "refusing non-simulation branch")

    wrong_audit = copy.deepcopy(audit)
    wrong_audit["trading_date"] = "2026-11-19"
    expect_error(lambda: validate_market_inputs(data, wrong_audit, manifest, report_date),
                 "market audit trading_date mismatch")

    missing_obs = copy.deepcopy(manifest)
    missing_obs["rows"][0]["observation_record_sha256"] = None
    expect_error(lambda: validate_market_inputs(data, audit, missing_obs, report_date),
                 "previous calendar commit is not the pinned main commit")

    mixed_dates = copy.deepcopy(manifest)
    mixed_dates["rows"][0]["trading_date"] = "2026-11-19"
    expect_error(lambda: validate_market_inputs(data, audit, mixed_dates, report_date),
                 "calendar path is not the canonical ISO-week database path")

    missing_domain = copy.deepcopy(data)
    missing_domain["political_scan"]["domains_checked"].remove("geopolitics")
    expect_error(lambda: validate_stage4(missing_domain, report_date),
                 "six-domain political/geopolitical scan is incomplete")

    outside_window = copy.deepcopy(data)
    outside_window["headlines"][0]["published_at_tw"] = "2026/11/20 11:59"
    expect_error(lambda: validate_stage4(outside_window, report_date),
                 "outside sealed window")

    wrong_calendar_commit = copy.deepcopy(bundle)
    wrong_calendar_commit["previous"]["commit_sha"] = "d" * 40
    expect_error(lambda: build_receipt(
        data=data, fixture_sha256="1" * 64, audit=audit, audit_sha256="2" * 64,
        manifest=manifest, manifest_sha256="3" * 64, calendar_bundle=wrong_calendar_commit,
        repository="lion-invlab/lion-invlab.github.io",
        branch="simulation/tac-process-lab-2026-11-06",
        workflow_run_id="45010119942", workflow_run_attempt="1"),
        "market source observation manifest is neither PASS nor PARTIAL")

    wrong_calendar_path = copy.deepcopy(bundle)
    wrong_calendar_path["current"]["path"] = "data/calendar/weeks/2026-W47.json"
    expect_error(lambda: build_receipt(
        data=data, fixture_sha256="1" * 64, audit=audit, audit_sha256="2" * 64,
        manifest=manifest, manifest_sha256="3" * 64, calendar_bundle=wrong_calendar_path,
        repository="lion-invlab/lion-invlab.github.io",
        branch="simulation/tac-process-lab-2026-11-06",
        workflow_run_id="45010119942", workflow_run_attempt="1"),
        "market source observation manifest is neither PASS nor PARTIAL")

    print("PASS: complete pending 44-row source register can build with every unverified quote rendered as 待核實")
    print("PASS: rejects wrong branch, mismatched date, incomplete per-row evidence, political-scan gap, out-of-window news and split main commits")
    print("PASS: synthetic current-run 44-row evidence can satisfy Gate; fixture values are never promoted to verified quotes")


if __name__ == "__main__":
    main()
