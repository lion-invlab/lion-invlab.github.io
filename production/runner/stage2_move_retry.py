#!/usr/bin/env python3
"""Targeted delayed MOVE retry; preserves the other 43 Stage 2 observations byte-for-byte."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from stage2_market_fixture_bootstrap import blank_fixture, populate_fixture


MOVE_KEY = ("risk", "move")
PENDING_STATUSES = {
    "PENDING", "SOURCE_NO_DATA", "SOURCE_UPDATE_PENDING", "TOOL_READ_FAILURE",
    "OBSERVED_PENDING_FIELD_MAPPING", "OBSERVED_PENDING_VALIDATION",
}


def _canonical_hash(value: dict) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _row_map(bundle: dict, expected_count: int = 44) -> dict:
    rows = bundle.get("observations") or []
    mapping = {(row.get("group"), row.get("name")): row for row in rows}
    if len(rows) != expected_count or len(mapping) != expected_count:
        raise ValueError(f"Expected {expected_count} unique observations, got {len(mapping)}")
    if MOVE_KEY not in mapping:
        raise ValueError("Stage 2 observation bundle is missing risk:move")
    return mapping


def merge_move_retry_observation(existing_bundle: dict, retry_bundle: dict) -> dict:
    """Replace only risk:move; every other observation must remain exactly unchanged."""
    if existing_bundle.get("report_date") != retry_bundle.get("report_date"):
        raise ValueError("MOVE retry report_date does not match the frozen 44-row bundle")
    if existing_bundle.get("trading_date") != retry_bundle.get("trading_date"):
        raise ValueError("MOVE retry trading_date does not match the frozen 44-row bundle")

    existing = _row_map(existing_bundle)
    retry_rows = retry_bundle.get("observations") or []
    if len(retry_rows) != 1 or (retry_rows[0].get("group"), retry_rows[0].get("name")) != MOVE_KEY:
        raise ValueError("Delayed retry must contain exactly one risk:move observation")

    previous = copy.deepcopy(existing[MOVE_KEY])
    replacement = copy.deepcopy(retry_rows[0])
    if replacement.get("source_url") != previous.get("source_url"):
        raise ValueError("MOVE retry source_url does not match the pinned primary source")
    if replacement.get("target_date") != existing_bundle.get("trading_date"):
        raise ValueError("MOVE retry target_date does not match the frozen trading_date")

    status = replacement.get("status")
    read_status = replacement.get("read_status")
    if status == "VERIFIED":
        if (
            replacement.get("observed_date") != existing_bundle.get("trading_date")
            or replacement.get("observed_value") is None
            or replacement.get("observed_change") is None
            or replacement.get("instrument_identity_status") != "VERIFIED"
            or replacement.get("field_mapping_status") != "VERIFIED"
        ):
            raise ValueError("A verified MOVE retry must have exact date, value, change, identity and field mapping")
    elif status in PENDING_STATUSES or read_status in PENDING_STATUSES:
        if read_status in ("SOURCE_UPDATE_PENDING", "TOOL_READ_FAILURE", "SOURCE_NO_DATA"):
            replacement["observed_date"] = None
            replacement["observed_value"] = None
            replacement["observed_change"] = None
            replacement["observed_value_field"] = None
            replacement["observed_change_field"] = None
    else:
        raise ValueError(f"Unsupported MOVE retry status: {status!r}/{read_status!r}")

    previous_hash = previous.get("observation_record_sha256") or _canonical_hash(previous)
    replacement["delayed_retry"] = {
        "attempted_at": replacement.get("finished_at_tw") or replacement.get("finished_at_utc"),
        "previous_status": previous.get("status"),
        "previous_read_status": previous.get("read_status"),
        "previous_observation_record_sha256": previous_hash,
        "scope": "risk:move_only",
    }
    replacement.pop("observation_record_sha256", None)
    replacement["observation_record_sha256"] = _canonical_hash(replacement)

    result = copy.deepcopy(existing_bundle)
    merged_rows = []
    before_non_move = {
        key: _canonical_hash(row) for key, row in existing.items() if key != MOVE_KEY
    }
    for row in result["observations"]:
        if (row.get("group"), row.get("name")) == MOVE_KEY:
            merged_rows.append(replacement)
        else:
            merged_rows.append(row)
    after_non_move = {
        (row.get("group"), row.get("name")): _canonical_hash(row)
        for row in merged_rows if (row.get("group"), row.get("name")) != MOVE_KEY
    }
    if before_non_move != after_non_move:
        raise ValueError("Non-MOVE observation changed during targeted retry")

    result["observations"] = merged_rows
    result["row_count"] = 44
    result["verified_count"] = sum(1 for row in merged_rows if row.get("status") in ("VERIFIED", "BACKUP_VERIFIED"))
    result["closed_count"] = sum(1 for row in merged_rows if row.get("read_status") == "MARKET_CLOSED" or row.get("status") == "MARKET_CLOSED")
    result["pending_count"] = 44 - result["verified_count"] - result["closed_count"]
    counts = {}
    for row in merged_rows:
        label = "MARKET_CLOSED" if row.get("read_status") == "MARKET_CLOSED" or row.get("status") == "MARKET_CLOSED" else row.get("status", "UNKNOWN")
        counts[label] = counts.get(label, 0) + 1
    result["status_counts"] = counts
    result["capture_method"] = "INITIAL_44_PLUS_TARGETED_MOVE_DELAYED_RETRY"
    result["prior_observation_reused_count"] = 43
    result["source_pages_fetched_this_run"] = False
    result["numeric_values_reconciled_this_run"] = False
    result["displayed_values_independently_reconciled_this_run"] = False
    result["move_delayed_retry"] = {
        "attempted": True,
        "scope": "risk:move_only",
        "status": replacement.get("status"),
        "read_status": replacement.get("read_status"),
        "observation_record_sha256": replacement["observation_record_sha256"],
        "non_move_observations_unchanged": True,
        "reused_non_move_observation_count": 43,
    }
    return result


def _market_value_snapshot(data: dict) -> dict:
    snapshot = {}
    for group in ("global_markets", "bonds", "fx", "energy", "metals", "risk"):
        for name, item in (data.get(group) or {}).items():
            if (group, name) == MOVE_KEY:
                continue
            source = item.get("source") or {}
            snapshot[f"{group}:{name}"] = {
                "display": item.get("display"),
                "change_display": item.get("change_display"),
                "close_value": source.get("close_value"),
                "daily_change_percent": source.get("daily_change_percent"),
                "history_close": source.get("history_close"),
                "history_change": source.get("history_change"),
            }
    for name, display in (data.get("sectors") or {}).items():
        source = (data.get("sector_sources") or {}).get(name) or {}
        snapshot[f"sectors:{name}"] = {
            "display": display,
            "change_display": source.get("change_display"),
            "close_value": source.get("close_value"),
            "daily_change_percent": source.get("daily_change_percent"),
            "history_close": source.get("history_close"),
            "history_change": source.get("history_change"),
        }
    return snapshot


def run_retry(fixture_path: Path, report_date: str, input_path: Path,
              output_observations: Path, output_fixture: Path,
              timeout_ms: int = 12000) -> dict:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    existing = json.loads(input_path.read_text(encoding="utf-8"))
    if fixture.get("report_date") != report_date or existing.get("report_date") != report_date:
        raise ValueError("MOVE retry report_date mismatch")
    if fixture.get("trading_date") != existing.get("trading_date"):
        raise ValueError("Fixture and observation bundle trading_date mismatch")
    current = _row_map(existing)[MOVE_KEY]
    if current.get("status") not in PENDING_STATUSES and current.get("read_status") not in PENDING_STATUSES:
        return {"status": "SKIPPED_NOT_PENDING", "move_status": current.get("status")}

    browser_script = Path(__file__).with_name("browser_verify_market_history.py")
    with tempfile.TemporaryDirectory(prefix="tac-move-delayed-retry-") as tmp:
        retry_output = Path(tmp) / "move-retry.json"
        command = [
            sys.executable, str(browser_script),
            "--fixture", str(fixture_path),
            "--report-date", report_date,
            "--output", str(retry_output),
            "--timeout-ms", str(timeout_ms),
            "--concurrency", "1",
            "--no-fixture-write",
            "--only", "risk:move",
        ]
        subprocess.run(command, check=True, capture_output=True, text=True)
        retry_bundle = json.loads(retry_output.read_text(encoding="utf-8"))

    merged = merge_move_retry_observation(existing, retry_bundle)
    blank = blank_fixture(copy.deepcopy(fixture), apply_screenshots=False)
    populated = populate_fixture(blank, merged)
    if _market_value_snapshot(fixture) != _market_value_snapshot(populated):
        raise ValueError("Targeted MOVE retry changed one or more non-MOVE market values")
    output_observations.parent.mkdir(parents=True, exist_ok=True)
    output_fixture.parent.mkdir(parents=True, exist_ok=True)
    output_observations.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output_fixture.write_text(json.dumps(populated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "status": "UPDATED" if merged["move_delayed_retry"]["status"] == "VERIFIED" else "PENDING",
        "move_status": merged["move_delayed_retry"]["status"],
        "verified_count": merged["verified_count"],
        "pending_count": merged["pending_count"],
        "non_move_values_unchanged": True,
        "observations_output": str(output_observations),
        "fixture_output": str(output_fixture),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--report-date", required=True)
    parser.add_argument("--input-observations", required=True)
    parser.add_argument("--output-observations", required=True)
    parser.add_argument("--output-fixture", required=True)
    parser.add_argument("--timeout-ms", type=int, default=12000)
    args = parser.parse_args()
    result = run_retry(
        Path(args.fixture), args.report_date, Path(args.input_observations),
        Path(args.output_observations), Path(args.output_fixture), args.timeout_ms,
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
