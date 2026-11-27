#!/usr/bin/env python3
"""Stage 2 regression tests for screenshot-first, field-level evidence provenance."""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import tempfile
from pathlib import Path

from build_market_source_verification_manifest import build_manifest, verification_fields


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

    # The production browser reader must make exactly one pinned-source read
    # per row; an alternate-source retry is forbidden.
    browser_path = Path("production/runner/browser_verify_market_history.py")
    browser_source = browser_path.read_text(encoding="utf-8")
    browser_ast = ast.parse(browser_source)
    observe_fn = next(
        node for node in browser_ast.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "observe"
    )
    observe_once_calls = [
        node for node in ast.walk(observe_fn)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        and node.func.id == "observe_once"
    ]
    assert len(observe_once_calls) == 1
    assert "--move-backup-only" not in browser_source
    validator_source = Path("production/runner/validate_chatgpt_web_observations.py").read_text(encoding="utf-8")
    assert "https://www.tradingview.com/symbols/ICE-MOVE/" in validator_source
    assert "TRADINGVIEW_HISTORICAL_PAGE" in validator_source
    assert "MOVE TradingView backup is allowed only after Investing.com TOOL_READ_FAILURE or SOURCE_NO_DATA" in validator_source
    move_template = json.loads(Path("production/config/report-data-template.json").read_text(encoding="utf-8"))
    assert move_template["risk"]["move"]["source"]["approved_backup_urls"] == ["https://www.tradingview.com/symbols/ICE-MOVE/"]
    # MOVE remains pending on a failed primary read unless a separately evidenced, date-matched TradingView backup is supplied.
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

    # A separately evidenced, exact TradingView ICE:MOVE observation is accepted
    # as BACKUP_VERIFIED only for MOVE; the primary Investing.com URL remains pinned.
    tv_url = "https://www.tradingview.com/symbols/ICE-MOVE/"
    move_source_for_backup = copy.deepcopy(move_source)
    move_source_for_backup["approved_backup_urls"] = [tv_url]
    move_backup_observation = {
        "status": "VERIFIED",
        "source_url": tv_url,
        "evidence_source_url": tv_url,
        "source_role": "BACKUP_1",
        "source_type": "TRADINGVIEW_HISTORICAL_PAGE",
        "target_date": move_source["data_date"],
        "observed_date": move_source["data_date"],
        "instrument_identity": "ICE BofAML U.S. Bond Market Option Volatility Estimate Index",
        "instrument_identity_status": "VERIFIED",
        "field_mapping_status": "VERIFIED",
        "observed_value": move_source["close_value"],
        "observed_change": move_source["daily_change_percent"],
        "observed_value_field": "Price",
        "observed_change_field": "Change %",
        "display_value_match": True,
        "display_change_match": True,
        "read_method": "CHATGPT_WEB_OPEN_HISTORICAL_PAGE",
        "provenance": "CURRENT_CHATGPT_WEB_OPEN_OBSERVATION",
        "read_status": "PAGE_CONTENT_READ_SUCCESS",
        "source_page_fetched": True,
        "finished_at_utc": "2026-11-23T14:00:00Z",
        "finished_at_tw": "2026-11-23T22:00:00+08:00",
        "field_evidence": {
            "close": {"source_type": "TRADINGVIEW_HISTORICAL_PAGE", "source_url": tv_url},
            "change": {"source_type": "TRADINGVIEW_HISTORICAL_PAGE", "source_url": tv_url},
        },
    }
    move_backup_result = verification_fields(
        move_source_for_backup, data["risk"]["move"]["display"],
        data["risk"]["move"]["change_display"], move_backup_observation, "risk", "move"
    )
    assert move_backup_result["verification_status"] == "BACKUP_VERIFIED"
    assert move_backup_result["market_data_status"] == "BACKUP_VERIFIED"
    assert move_backup_result["browser_observation_record"]["source_role"] == "BACKUP_1"
    assert move_backup_result["browser_observation_record"]["evidence_source_url"] == tv_url
    move_manifest = build_manifest(
        data, data["report_date"], {("risk", "move"): move_backup_observation}
    )
    move_manifest_row = next(
        row for row in move_manifest["rows"]
        if row["group"] == "risk" and row["name"] == "move"
    )
    assert move_manifest_row["verification_status"] == "BACKUP_VERIFIED"
    assert move_manifest_row["evidence_source_url"] == tv_url
    assert move_manifest_row["evidence_source_name"] == "TradingView ICE:MOVE"
    assert move_manifest_row["evidence_source_role"] == "BACKUP_1"

    print("PASS: screenshot-only fields are accepted without claiming a browser page read")
    print("PASS: MOVE Investing.com read failure remains pending until a cited, date-matched TradingView backup is supplied")
    print("PASS: mixed screenshot/history-page fields retain independent provenance")
    print("PASS: malformed screenshot evidence SHA cannot pass Stage 2 verification")
    from test_stage2_screenshot_inputs import main as test_screenshot_inputs
    test_screenshot_inputs()


if __name__ == "__main__":
    main()
