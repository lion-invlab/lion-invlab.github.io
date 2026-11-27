#!/usr/bin/env python3
"""Stage 2 regression tests for screenshot-first, field-level evidence provenance."""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
from pathlib import Path

from build_market_source_verification_manifest import verification_fields


FIXTURE = Path("production/testdata/report-data-2026-11-23.json")


def screenshot_field(path: str, digest: str):
    return {
        "source_type": "USER_PROVIDED_SCREENSHOT",
        "evidence_path": path,
        "evidence_sha256": digest,
        "captured_at": "2026-11-23T07:05:00+08:00",
    }


def base_observation(source: dict, *, mixed: bool = False):
    if mixed:
        provenance = "CURRENT_RUN_MIXED_FIELD_OBSERVATION"
        read_method = "MIXED_SCREENSHOT_AND_HISTORICAL_PAGE"
        read_status = "MIXED_FIELD_OBSERVATIONS_CONFIRMED"
    else:
        provenance = "CURRENT_USER_PROVIDED_SCREENSHOT"
        read_method = "USER_PROVIDED_SCREENSHOT"
        read_status = "USER_PROVIDED_SCREENSHOT_CONFIRMED"
    return {
        "status": "VERIFIED",
        "source_url": source["url"],
        "target_date": source["data_date"],
        "observed_date": source["data_date"],
        "instrument_identity": "S&P 500 (SPX)",
        "instrument_identity_status": "VERIFIED",
        "screenshot_instrument_identity_status": "VERIFIED",
        "field_mapping_status": "VERIFIED",
        "observed_value": source["close_value"],
        "observed_change": source["daily_change_percent"],
        "observed_value_field": "Close",
        "observed_change_field": "Change %",
        "display_value_match": True,
        "display_change_match": True,
        "finished_at_utc": "2026-11-22T23:05:00Z",
        "finished_at_tw": "2026-11-23T07:05:00+08:00",
        "read_method": read_method,
        "provenance": provenance,
        "read_status": read_status,
        "source_page_fetched": mixed,
        "field_evidence": {
            "close": {"source_type": "UNSET"},
            "change": (
                {"source_type": "INVESTING_HISTORICAL_PAGE",
                 "source_url": source["url"],
                 "observed_at": "2026-11-23T07:06:00+08:00"}
                if mixed else {"source_type": "UNSET"}
            ),
        },
    }


def main():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    source = data["global_markets"]["標普500指數"]["source"]
    display = data["global_markets"]["標普500指數"]["display"]
    change = data["global_markets"]["標普500指數"]["change_display"]

    with tempfile.TemporaryDirectory() as tmp:
        evidence_path = Path(tmp) / "spx-screenshot.png"
        evidence_path.write_bytes(b"test screenshot evidence bytes")
        evidence_sha = hashlib.sha256(evidence_path.read_bytes()).hexdigest()

        screenshot = base_observation(source)
        screenshot["field_evidence"]["close"] = screenshot_field(str(evidence_path), evidence_sha)
        screenshot["field_evidence"]["change"] = screenshot_field(str(evidence_path), evidence_sha)
        result = verification_fields(source, display, change, screenshot, "global_markets", "標普500指數")
        assert result["verification_status"] == "VERIFIED"
        assert result["source_page_fetched"] is False
        assert result["browser_observation_record"]["field_evidence"]["close"]["source_type"] == "USER_PROVIDED_SCREENSHOT"
        assert result["observation_record_sha256"] and len(result["observation_record_sha256"]) == 64

        false_page_claim = copy.deepcopy(screenshot)
        false_page_claim["source_page_fetched"] = True
        result = verification_fields(source, display, change, false_page_claim, "global_markets", "標普500指數")
        assert result["verification_status"] == "PENDING_CURRENT_RUN_BROWSER_OBSERVATION"

        mixed = base_observation(source, mixed=True)
        mixed["field_evidence"]["close"] = screenshot_field(str(evidence_path), evidence_sha)
        result = verification_fields(source, display, change, mixed, "global_markets", "標普500指數")
        assert result["verification_status"] == "VERIFIED"
        assert result["source_page_fetched"] is True
        assert result["browser_observation_record"]["field_evidence"]["close"]["source_type"] == "USER_PROVIDED_SCREENSHOT"
        assert result["browser_observation_record"]["field_evidence"]["change"]["source_type"] == "INVESTING_HISTORICAL_PAGE"

        mislabeled_partial = copy.deepcopy(mixed)
        mislabeled_partial["provenance"] = "CURRENT_USER_PROVIDED_SCREENSHOT"
        mislabeled_partial["read_method"] = "USER_PROVIDED_SCREENSHOT"
        mislabeled_partial["read_status"] = "USER_PROVIDED_SCREENSHOT_CONFIRMED"
        result = verification_fields(source, display, change, mislabeled_partial, "global_markets", "標普500指數")
        assert result["verification_status"] == "PENDING_CURRENT_RUN_BROWSER_OBSERVATION"

        bad_hash = copy.deepcopy(screenshot)
        bad_hash["field_evidence"]["close"]["evidence_sha256"] = "b" * 64
        result = verification_fields(source, display, change, bad_hash, "global_markets", "標普500指數")
        assert result["verification_status"] == "PENDING_CURRENT_RUN_BROWSER_OBSERVATION"
        assert result["observation_record_sha256"] is None

    # MOVE must remain pending when the approved Investing.com page cannot be read; no TradingView substitution.
    move_source = data["risk"]["move"]["source"]
    move_observation = {
        "status": "OBSERVED_PENDING_VALIDATION",
        "source_url": move_source["url"],
        "evidence_source_url": move_source["url"],
        "source_role": "PRIMARY",
        "target_date": move_source["data_date"],
        "observed_date": None,
        "instrument_identity": move_source.get("instrument_identity", "ICE BofAML MOVE Index"),
        "instrument_identity_status": "NOT_INDEPENDENTLY_VERIFIED",
        "field_mapping_status": "PENDING_FIELD_HEADER_MAPPING",
        "observed_value": None,
        "observed_change": None,
        "read_method": "CHATGPT_WEB_OPEN_HISTORICAL_PAGE",
        "provenance": "CURRENT_CHATGPT_WEB_OPEN_OBSERVATION",
        "read_status": "TOOL_READ_FAILURE",
        "http_status": 200,
        "source_page_fetched": False,
        "field_evidence": {},
    }
    move_result = verification_fields(
        move_source, data["risk"]["move"]["display"],
        data["risk"]["move"]["change_display"], move_observation, "risk", "move"
    )
    # A failed read must not be serialized as a verified browser-observation record.
    # The primary source identity remains in the fixture; the unverified attempt is pending.
    assert move_result["verification_status"] == "PENDING_CURRENT_RUN_BROWSER_OBSERVATION"
    assert move_result["market_data_status"] == "TOOL_READ_FAILURE"
    assert move_result["browser_observation_record"] is None
    assert move_result["observation_record_sha256"] is None
    assert move_result["source_page_fetched"] is False

    print("PASS: screenshot-only fields are accepted without claiming a browser page read")
    print("PASS: MOVE Investing.com read failure remains pending; no TradingView fallback is accepted")
    print("PASS: mixed screenshot/history-page fields retain independent provenance")
    print("PASS: malformed screenshot evidence SHA cannot pass Stage 2 verification")
    from test_stage2_screenshot_inputs import main as test_screenshot_inputs
    test_screenshot_inputs()


if __name__ == "__main__":
    main()
