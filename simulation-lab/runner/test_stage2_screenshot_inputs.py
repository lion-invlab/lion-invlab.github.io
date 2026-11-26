#!/usr/bin/env python3
"""Regression tests for SHA-bound screenshot ingestion and fixture precedence."""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
from pathlib import Path

from stage2_screenshot_inputs import apply_screenshot_values_to_fixture, load_screenshot_bundle
from browser_verify_market_history import _apply_screenshot_fields


FIXTURE = Path("simulation-lab/fixtures/report-data-2026-11-23.json")


def main():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    source = fixture["global_markets"]["標普500指數"]["source"]
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        image = root / "spx.png"
        image.write_bytes(b"stage2 screenshot evidence bytes")
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        bundle = {
            "report_date": fixture["report_date"],
            "trading_date": fixture["trading_date"],
            "observations": [{
                "group": "global_markets",
                "name": "標普500指數",
                "data_date": fixture["trading_date"],
                "source_url": source["url"],
                "instrument_identity": "S&P 500 (SPX)",
                "evidence_path": "spx.png",
                "evidence_sha256": digest,
                "captured_at": "2026-11-23T07:05:00+08:00",
                "fields": {
                    "close": {"value": "6,812.34", "field_name": "Close"},
                    "change": {"value": "-0.42%", "field_name": "Change %"},
                },
            }],
        }
        bundle_path = root / "bundle.json"
        bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
        loaded = load_screenshot_bundle(bundle_path, fixture, root)
        assert ("global_markets", "標普500指數") in loaded
        assert loaded[("global_markets", "標普500指數")]["fields"]["close"]["evidence_sha256"] == digest

        updated = apply_screenshot_values_to_fixture(copy.deepcopy(fixture), loaded)
        row = updated["global_markets"]["標普500指數"]
        assert row["display"] == "6,812.34"
        assert row["change_display"] == "-0.42%"
        assert row["source"]["close_value"] == "6812.34"
        assert row["source"]["daily_change_percent"] == "-0.42"

        work_row = {
            "group": "global_markets", "name": "標普500指數",
            "source_url": source["url"], "target_date": fixture["trading_date"],
            "expected_value": "6812.34", "expected_change": "-0.42",
        }
        screenshot_only = _apply_screenshot_fields(
            work_row, {"group": "global_markets", "name": "標普500指數", "target_date": fixture["trading_date"]},
            loaded[("global_markets", "標普500指數")]
        )
        assert screenshot_only["status"] == "VERIFIED"
        assert screenshot_only["source_page_fetched"] is False

        partial_bundle = copy.deepcopy(bundle)
        partial_bundle["observations"][0]["fields"].pop("change")
        bundle_path.write_text(json.dumps(partial_bundle), encoding="utf-8")
        partial = load_screenshot_bundle(bundle_path, fixture, root)
        page_observation = {
            "status": "OBSERVED_PENDING_FIELD_MAPPING",
            "source_page_fetched": True,
            "field_mapping_status": "VERIFIED",
            "instrument_identity_status": "VERIFIED",
            "instrument_identity": "S&P 500",
            "observed_value": "6000.00",
            "observed_change": "-0.42",
            "observed_value_field": "Price",
            "observed_change_field": "Change %",
            "display_value_match": False,
            "display_change_match": True,
            "finished_at_tw": "2026-11-23T07:06:00+08:00",
        }
        mixed = _apply_screenshot_fields(
            work_row, page_observation, partial[("global_markets", "標普500指數")]
        )
        assert mixed["status"] == "VERIFIED"
        assert mixed["observed_value"] == "6,812.34"
        assert mixed["observed_change"] == "-0.42"
        assert mixed["field_evidence"]["close"]["source_type"] == "USER_PROVIDED_SCREENSHOT"
        assert mixed["field_evidence"]["change"]["source_type"] == "INVESTING_HISTORICAL_PAGE"

        optional_only_bundle = copy.deepcopy(bundle)
        optional_only_bundle["observations"][0]["fields"] = {
            "high": {"value": "6,845.20", "field_name": "High"}
        }
        bundle_path.write_text(json.dumps(optional_only_bundle), encoding="utf-8")
        optional_only = load_screenshot_bundle(bundle_path, fixture, root)
        complete_page = {
            "status": "VERIFIED",
            "source_page_fetched": True,
            "field_mapping_status": "VERIFIED",
            "instrument_identity_status": "VERIFIED",
            "instrument_identity": "S&P 500",
            "observed_value": "6812.34",
            "observed_change": "-0.42",
            "observed_value_field": "Price",
            "observed_change_field": "Change %",
            "display_value_match": True,
            "display_change_match": True,
            "finished_at_tw": "2026-11-23T07:06:00+08:00",
        }
        optional_mixed = _apply_screenshot_fields(
            work_row, complete_page, optional_only[("global_markets", "標普500指數")]
        )
        assert optional_mixed["status"] == "VERIFIED"
        assert optional_mixed["field_evidence"]["high"]["source_type"] == "USER_PROVIDED_SCREENSHOT"
        assert optional_mixed["field_evidence"]["close"]["source_type"] == "INVESTING_HISTORICAL_PAGE"

        wrong_hash = copy.deepcopy(bundle)
        wrong_hash["observations"][0]["evidence_sha256"] = "0" * 64
        bundle_path.write_text(json.dumps(wrong_hash), encoding="utf-8")
        try:
            load_screenshot_bundle(bundle_path, fixture, root)
        except ValueError as exc:
            assert "SHA-256 mismatch" in str(exc)
        else:
            raise AssertionError("mismatched screenshot SHA was accepted")

        wrong_date = copy.deepcopy(bundle)
        wrong_date["trading_date"] = "2026-11-24"
        bundle_path.write_text(json.dumps(wrong_date), encoding="utf-8")
        try:
            load_screenshot_bundle(bundle_path, fixture, root)
        except ValueError as exc:
            assert "trading_date" in str(exc)
        else:
            raise AssertionError("date-mismatched screenshot bundle was accepted")

    print("PASS: screenshot evidence is SHA-checked against actual file bytes")
    print("PASS: screenshot values override Fixture close/change before expected-value construction")
    print("PASS: wrong evidence hash and wrong trading date are rejected")


if __name__ == "__main__":
    main()
