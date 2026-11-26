#!/usr/bin/env python3
"""Negative and positive tests for the pre-build Stage 2-4 input receipt."""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
from pathlib import Path

from build_market_source_verification_manifest import build_manifest
from validate_market_snapshot import validate_market_snapshot
from validate_prebuild_stage_inputs import build_receipt, validate_branch, validate_market_inputs, validate_observation_bundle, validate_stage4
from build_review_html import apply_market_source_verification_manifest

FIXTURE = Path("production/testdata/report-data-2026-11-23.json")


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
    pending_receipt = build_receipt(
        data=data, fixture_sha256="1" * 64,
        audit=audit, audit_sha256="2" * 64,
        manifest=manifest, manifest_sha256="3" * 64,
        calendar_bundle=bundle,
        repository="lion-invlab/lion-invlab.github.io",
        branch="main",
        workflow_run_id="45010119942", workflow_run_attempt="1",
    )
    assert pending_receipt["stage_2_market"]["source_verification_status"] == "PENDING"
    assert pending_receipt["stage_2_market"]["pending_observation_count"] == 44
    # The frozen receipt binds the exact Fixture, 44-row Manifest and metadata audit.
    assert pending_receipt["fixture"]["sha256"] == "1" * 64
    assert pending_receipt["stage_2_market"]["audit_sha256"] == "2" * 64
    assert pending_receipt["stage_2_market"]["manifest_sha256"] == "3" * 64
    assert pending_receipt["stage_2_market"]["numeric_values_reconciled_count"] == 0

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
        "source_pages_fetched": True, "displayed_values_reconciled": True, "displayed_values_independently_reconciled": True, "screenshot_field_count": 0,
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

    observation_rows = []
    for row in synthetic["rows"]:
        is_fg = row["group"] == "risk" and row["name"] == "fear_greed"
        value_key, change_key = ("score", "band") if is_fg else ("close", "change")
        source_type = "CNN_OFFICIAL_API" if is_fg else "INVESTING_HISTORICAL_PAGE"
        observation_rows.append({
            "group": row["group"], "name": row["name"],
            "source_url": row["source_url"], "target_date": data["trading_date"],
            "status": "VERIFIED", "read_method": "PLAYWRIGHT_RENDERED_HISTORY_TABLE", "source_page_fetched": True,
            "observed_value": "100.00", "observed_change": "1.00",
            "observed_value_key": value_key, "observed_change_key": change_key,
            "field_evidence": {
                value_key: {"source_type": source_type, "value": "100.00"},
                change_key: {"source_type": source_type, "value": "1.00"},
            },
            "observation_record_sha256": "e" * 64,
        })
    for observation in observation_rows:
        canonical = dict(observation)
        canonical.pop("observation_record_sha256", None)
        observation["observation_record_sha256"] = hashlib.sha256(
            json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    observation_bundle = {
        "report_date": report_date, "trading_date": data["trading_date"],
        "row_count": 44, "observations": observation_rows,
    }
    observation_summary = validate_observation_bundle(observation_bundle, report_date, data["trading_date"])
    assert observation_summary["row_count"] == 44
    assert observation_summary["page_only_row_count"] == 44
    screenshot_bundle_test = copy.deepcopy(observation_bundle)
    screenshot_row_test = screenshot_bundle_test["observations"][0]
    screenshot_row_test["read_method"] = "USER_PROVIDED_SCREENSHOT"
    screenshot_row_test["source_page_fetched"] = False
    screenshot_row_test["field_evidence"] = {
        screenshot_row_test["observed_value_key"]: {"source_type": "USER_PROVIDED_SCREENSHOT"},
        screenshot_row_test["observed_change_key"]: {"source_type": "USER_PROVIDED_SCREENSHOT"},
    }
    screenshot_row_test.pop("observation_record_sha256", None)
    screenshot_row_test["observation_record_sha256"] = hashlib.sha256(
        json.dumps(screenshot_row_test, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    screenshot_summary = validate_observation_bundle(screenshot_bundle_test, report_date, data["trading_date"])
    assert screenshot_summary["screenshot_only_row_count"] == 1
    mixed_bundle_test = copy.deepcopy(observation_bundle)
    mixed_row_test = mixed_bundle_test["observations"][0]
    mixed_row_test["read_method"] = "MIXED_SCREENSHOT_AND_HISTORICAL_PAGE"
    mixed_row_test["source_page_fetched"] = True
    mixed_row_test["field_evidence"][mixed_row_test["observed_value_key"]] = {"source_type": "USER_PROVIDED_SCREENSHOT"}
    mixed_row_test.pop("observation_record_sha256", None)
    mixed_row_test["observation_record_sha256"] = hashlib.sha256(
        json.dumps(mixed_row_test, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    mixed_summary = validate_observation_bundle(mixed_bundle_test, report_date, data["trading_date"])
    assert mixed_summary["mixed_field_row_count"] == 1
    receipt_with_observations = build_receipt(
        data=data, fixture_sha256="1" * 64,
        audit=audit, audit_sha256="2" * 64,
        manifest=synthetic, manifest_sha256="3" * 64,
        calendar_bundle=bundle,
        repository="lion-invlab/lion-invlab.github.io",
        branch="main",
        workflow_run_id="45010119942", workflow_run_attempt="1",
        observation_bundle=observation_bundle,
        observation_bundle_sha256="d" * 64,
    )
    assert receipt_with_observations["stage_2_market"]["observation_bundle_sha256"] == "d" * 64
    bad_observation_bundle = copy.deepcopy(observation_bundle)
    bad_observation_bundle["observations"][1] = copy.deepcopy(bad_observation_bundle["observations"][0])
    expect_error(lambda: validate_observation_bundle(bad_observation_bundle, report_date, data["trading_date"]),
                 "duplicate or unnamed row")

    # User-provided current-session screenshot is valid evidence when the
    # screenshot timestamp and SHA are sealed by the manifest builder.
    with tempfile.TemporaryDirectory() as tmp:
        screenshot_file = Path(tmp) / "move.png"
        screenshot_file.write_bytes(b"sealed MOVE screenshot bytes")
        screenshot_sha = hashlib.sha256(screenshot_file.read_bytes()).hexdigest()
        screenshot_evidence = copy.deepcopy(synthetic)
        screenshot_evidence["source_pages_fetched"] = False
        screenshot_evidence["displayed_values_independently_reconciled"] = False
        screenshot_evidence["screenshot_row_count"] = 1
        screenshot_evidence["screenshot_field_count"] = 2
        screenshot_row = next(row for row in screenshot_evidence["rows"]
                              if row.get("group") == "risk" and row.get("name") == "move")
        screenshot_row["observation_provenance"] = "CURRENT_USER_PROVIDED_SCREENSHOT"
        screenshot_row["source_page_fetched"] = False
        screenshot_row["browser_observation_record"]["screenshot_instrument_identity_status"] = "VERIFIED"
        screenshot_row["browser_observation_record"]["field_evidence"] = {
            field: {
                "source_type": "USER_PROVIDED_SCREENSHOT",
                "evidence_path": str(screenshot_file),
                "evidence_sha256": screenshot_sha,
                "captured_at": "2026-11-23T07:05:00+08:00",
            }
            for field in ("close", "change")
        }
        screenshot_result = validate_market_inputs(data, audit, screenshot_evidence, report_date)
        assert screenshot_result["indicator_count"] == 44
        assert screenshot_result["source_pages_fetched_this_run"] is False
        assert screenshot_result["numeric_values_reconciled_this_run"] is True
        assert screenshot_result["numeric_values_independently_reconciled_this_run"] is False

    # Partial is a valid production input state: keep all 44 fixed rows,
    # preserve 43 current-session observations, and leave one row explicitly pending.
    partial = copy.deepcopy(synthetic)
    partial["status"] = "PARTIAL"
    partial["verified_count"] = 42
    partial["pending_count"] = 1
    partial["closed_count"] = 1
    partial["displayed_values_independently_reconciled"] = False
    partial["displayed_values_reconciled"] = False
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
    closed_row = partial["rows"][1]
    closed_row.update({
        "verification_status": "CLOSED",
        "source_page_fetched": True,
        "display_value_reconciled": False,
        "display_value_matches_saved_observation": False,
        "evidence_status": "MARKET_CLOSED",
        "observation_provenance": "CURRENT_CHATGPT_WEB_OPEN_OBSERVATION",
        "browser_observation_record": None,
        "observation_record_sha256": None,
    })
    partial_result = validate_market_inputs(data, audit, partial, report_date)
    assert partial_result["indicator_count"] == 44
    assert partial_result["numeric_values_reconciled_count"] == 42
    assert partial_result["closed_count"] == 1
    assert partial_result["numeric_values_reconciled_this_run"] is False
    partial_receipt = build_receipt(
        data=data, fixture_sha256="1" * 64,
        audit=audit, audit_sha256="2" * 64,
        manifest=partial, manifest_sha256="3" * 64,
        calendar_bundle=bundle,
        repository="lion-invlab/lion-invlab.github.io",
        branch="main",
        workflow_run_id="45010119942", workflow_run_attempt="1",
    )
    assert partial_receipt["status"] == "PASS"
    assert partial_receipt["stage_2_market"]["pending_observation_count"] == 1
    assert partial_receipt["stage_2_market"]["closed_count"] == 1
    expect_error(lambda: validate_branch("lion-invlab/lion-invlab.github.io", "main"),
                 "refusing non-simulation branch")

    wrong_audit = copy.deepcopy(audit)
    wrong_audit["trading_date"] = "2026-11-19"
    expect_error(lambda: validate_market_inputs(data, wrong_audit, manifest, report_date),
                 "market audit trading_date mismatch")

    missing_obs = copy.deepcopy(synthetic)
    missing_obs["rows"][0]["observation_record_sha256"] = None
    expect_error(lambda: validate_market_inputs(data, audit, missing_obs, report_date),
                 "verified row observation hash invalid")

    mixed_dates = copy.deepcopy(synthetic)
    mixed_dates["rows"][0]["trading_date"] = "2026-11-19"
    expect_error(lambda: validate_market_inputs(data, audit, mixed_dates, report_date),
                 "source manifest contains mixed trading dates")

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
        manifest=synthetic, manifest_sha256="3" * 64, calendar_bundle=wrong_calendar_commit,
        repository="lion-invlab/lion-invlab.github.io",
        branch="main",
        workflow_run_id="45010119942", workflow_run_attempt="1"),
        "previous calendar commit is not the pinned main commit")

    wrong_calendar_path = copy.deepcopy(bundle)
    wrong_calendar_path["current"]["path"] = "data/calendar/weeks/2026-W47.json"
    expect_error(lambda: build_receipt(
        data=data, fixture_sha256="1" * 64, audit=audit, audit_sha256="2" * 64,
        manifest=synthetic, manifest_sha256="3" * 64, calendar_bundle=wrong_calendar_path,
        repository="lion-invlab/lion-invlab.github.io",
        branch="main",
        workflow_run_id="45010119942", workflow_run_attempt="1"),
        "calendar path is not the canonical ISO-week database path")

    print("PASS: complete pending 44-row source register can build with every unverified quote rendered as 待核實")
    print("PASS: rejects wrong branch, mismatched date, incomplete per-row evidence, political-scan gap, out-of-window news and split main commits")
    print("PASS: synthetic current-run 44-row evidence can satisfy Gate; fixture values are never promoted to verified quotes")


if __name__ == "__main__":
    main()
