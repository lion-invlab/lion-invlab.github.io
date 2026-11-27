#!/usr/bin/env python3
"""Regression tests for SHA-bound screenshot ingestion and fixture precedence."""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
from pathlib import Path

from stage2_screenshot_inputs import apply_page_completions_to_fixture, apply_screenshot_values_to_fixture, load_screenshot_bundle
from validate_chatgpt_web_observations import _apply_screenshot_fields, persist_fixture


FIXTURE = Path("production/testdata/report-data-2026-11-23.json")


def main():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    source = fixture["global_markets"]["標普500指數"]["source"]
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        fixture_path = root / "diagnostic-fixture.json"
        original_bytes = b'{"original":"must remain untouched"}\\n'
        fixture_path.write_bytes(original_bytes)
        assert persist_fixture(fixture_path, {"changed": True}, no_fixture_write=True) is False
        assert fixture_path.read_bytes() == original_bytes
        assert persist_fixture(fixture_path, {"changed": True}, no_fixture_write=False) is True
        assert json.loads(fixture_path.read_text(encoding="utf-8")) == {"changed": True}
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

        close_image = root / "spx-close.png"
        change_image = root / "spx-change.png"
        close_image.write_bytes(b"close-only screenshot")
        change_image.write_bytes(b"change-only screenshot")
        multi_image_bundle = copy.deepcopy(bundle)
        multi_fields = multi_image_bundle["observations"][0]["fields"]
        multi_fields["close"].update({
            "evidence_path": "spx-close.png",
            "evidence_sha256": hashlib.sha256(close_image.read_bytes()).hexdigest(),
            "captured_at": "2026-11-23T07:04:00+08:00",
        })
        multi_fields["change"].update({
            "evidence_path": "spx-change.png",
            "evidence_sha256": hashlib.sha256(change_image.read_bytes()).hexdigest(),
            "captured_at": "2026-11-23T07:05:00+08:00",
        })
        multi_image_bundle["observations"][0].pop("evidence_path")
        multi_image_bundle["observations"][0].pop("evidence_sha256")
        bundle_path.write_text(json.dumps(multi_image_bundle), encoding="utf-8")
        multi_image_loaded = load_screenshot_bundle(bundle_path, fixture, root)
        multi_fields_loaded = multi_image_loaded[("global_markets", "標普500指數")]["fields"]
        assert multi_fields_loaded["close"]["evidence_sha256"] != multi_fields_loaded["change"]["evidence_sha256"]
        assert multi_fields_loaded["close"]["evidence_path"] != multi_fields_loaded["change"]["evidence_path"]

        # Rewriting sidecar dates cannot make a prior-day image current.
        stale_bundle = copy.deepcopy(bundle)
        stale_bundle["observations"][0]["captured_at"] = "2026-11-22T07:05:00+08:00"
        bundle_path.write_text(json.dumps(stale_bundle), encoding="utf-8")
        try:
            load_screenshot_bundle(bundle_path, fixture, root)
        except ValueError as exc:
            assert "screenshot is stale" in str(exc)
        else:
            raise AssertionError("prior-day screenshot was accepted for today's report")

        # Every image field is independently date-bound.
        stale_field_bundle = copy.deepcopy(bundle)
        stale_field_bundle["observations"][0]["fields"]["close"] = {
            "value": "6,812.34", "field_name": "Close",
            "captured_at": "2026-11-22T07:05:00+08:00",
        }
        bundle_path.write_text(json.dumps(stale_field_bundle), encoding="utf-8")
        try:
            load_screenshot_bundle(bundle_path, fixture, root)
        except ValueError as exc:
            assert "screenshot is stale" in str(exc)
        else:
            raise AssertionError("prior-day field screenshot was accepted")

        naive_bundle = copy.deepcopy(bundle)
        naive_bundle["observations"][0]["captured_at"] = "2026-11-23T07:05:00"
        bundle_path.write_text(json.dumps(naive_bundle), encoding="utf-8")
        try:
            load_screenshot_bundle(bundle_path, fixture, root)
        except ValueError as exc:
            assert "explicit timezone" in str(exc)
        else:
            raise AssertionError("timezone-naive screenshot timestamp was accepted")

        bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
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

        wrong_identity_input = copy.deepcopy(loaded[("global_markets", "標普500指數")])
        wrong_identity_input["instrument_identity"] = "Nasdaq Composite (IXIC)"
        wrong_identity = _apply_screenshot_fields(
            work_row, {"group": "global_markets", "name": "標普500指數", "target_date": fixture["trading_date"]},
            wrong_identity_input
        )
        assert wrong_identity["status"] == "OBSERVED_PENDING_FIELD_MAPPING"
        assert wrong_identity["screenshot_instrument_identity_status"] == "NOT_INDEPENDENTLY_VERIFIED"

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
        assert mixed["field_evidence"]["change"]["source_type"] == "INVESTING_HISTORICAL_PAGE", {"screenshot_fields": list(partial[("global_markets", "標普500指數")]["fields"]), "field_evidence": mixed["field_evidence"]}
        completed_fixture = apply_screenshot_values_to_fixture(copy.deepcopy(fixture), partial)
        apply_page_completions_to_fixture(completed_fixture, [mixed], partial)
        completed_row = completed_fixture["global_markets"]["標普500指數"]
        assert completed_row["change_display"] == "-0.42%", (completed_row["change_display"], mixed.get("source_page_fetched"), mixed.get("screenshot_instrument_identity_status"), partial[("global_markets", "標普500指數")]["fields"].keys())
        assert completed_row["source"]["daily_change_percent"] == "-0.42"

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
        optional_fixture = apply_screenshot_values_to_fixture(copy.deepcopy(fixture), optional_only)
        apply_page_completions_to_fixture(optional_fixture, [optional_mixed], optional_only)
        optional_row = optional_fixture["global_markets"]["標普500指數"]
        assert optional_row["display"] == "6,812.34"
        assert optional_row["change_display"] == "-0.42%"

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
    print("PASS: wrong hash/date, prior-day screenshots and timezone-naive timestamps are rejected")


if __name__ == "__main__":
    main()
