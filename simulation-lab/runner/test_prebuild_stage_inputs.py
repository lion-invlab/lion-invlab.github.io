#!/usr/bin/env python3
"""Negative and positive tests for the pre-build Stage 2-4 input receipt."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from build_market_source_verification_manifest import build_manifest
from validate_market_snapshot import validate_market_snapshot
from validate_prebuild_stage_inputs import build_receipt, validate_branch, validate_market_inputs, validate_stage4

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
    receipt = build_receipt(
        data=data, fixture_sha256="1" * 64,
        audit=audit, audit_sha256="2" * 64,
        manifest=manifest, manifest_sha256="3" * 64,
        calendar_bundle=bundle,
        repository="lion-invlab/lion-invlab.github.io",
        branch="simulation/tac-process-lab-2026-11-06",
        workflow_run_id="45010119942", workflow_run_attempt="1",
    )
    assert receipt["status"] == "PASS"
    assert receipt["gate"] == "PRE_BUILD_STAGE_2_TO_4_INPUT_RECEIPT"
    assert receipt["stage_2_market"]["indicator_count"] == 44
    assert receipt["stage_2_market"]["raw_response_sha256_saved_count"] == 0
    assert receipt["stage_2_market"]["source_pages_fetched_this_run"] is False
    assert receipt["stage_3_calendar"]["main_commit_sha"] == commit
    assert receipt["stage_3_calendar"]["current"]["economic_count"] == 27
    assert receipt["stage_4_news_and_analysis"]["unique_news_urls"] == 15

    expect_error(lambda: validate_branch("lion-invlab/lion-invlab.github.io", "main"),
                 "refusing non-simulation branch")

    wrong_audit = copy.deepcopy(audit)
    wrong_audit["trading_date"] = "2026-11-19"
    expect_error(lambda: validate_market_inputs(data, wrong_audit, manifest, report_date),
                 "market audit trading_date mismatch")

    missing_obs = copy.deepcopy(manifest)
    missing_obs["rows"][0]["observation_record_sha256"] = None
    expect_error(lambda: validate_market_inputs(data, audit, missing_obs, report_date),
                 "observation record hashes are invalid")

    mixed_dates = copy.deepcopy(manifest)
    mixed_dates["rows"][0]["trading_date"] = "2026-11-19"
    expect_error(lambda: validate_market_inputs(data, audit, mixed_dates, report_date),
                 "mixed trading dates")

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
        "not the pinned main commit")

    wrong_calendar_path = copy.deepcopy(bundle)
    wrong_calendar_path["current"]["path"] = "data/calendar/weeks/2026-W47.json"
    expect_error(lambda: build_receipt(
        data=data, fixture_sha256="1" * 64, audit=audit, audit_sha256="2" * 64,
        manifest=manifest, manifest_sha256="3" * 64, calendar_bundle=wrong_calendar_path,
        repository="lion-invlab/lion-invlab.github.io",
        branch="simulation/tac-process-lab-2026-11-06",
        workflow_run_id="45010119942", workflow_run_attempt="1"),
        "canonical ISO-week database path")

    print("PASS: valid receipt binds 44 observations, two pinned main calendar weeks, 15 news items and five-layer analysis")
    print("PASS: rejects wrong branch, mismatched date, incomplete per-row evidence, political-scan gap, out-of-window news and split main commits")
    print("PASS: zero raw HTTP response hashes is accepted when browser observations are complete")


if __name__ == "__main__":
    main()
