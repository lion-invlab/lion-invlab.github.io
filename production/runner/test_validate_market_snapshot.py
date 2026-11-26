#!/usr/bin/env python3
"""Regression tests for the 44-indicator source/date metadata gate."""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
from pathlib import Path

from validate_market_snapshot import validate_market_snapshot


FIXTURE = Path("production/testdata/report-data-2026-11-23.json")


def expect_error(fn, fragment):
    try:
        fn()
    except ValueError as exc:
        assert fragment in str(exc), str(exc)
    else:
        raise AssertionError("expected validation failure")


def main():
    base = json.loads(FIXTURE.read_text(encoding="utf-8"))
    result = validate_market_snapshot(base, "2026-11-23")
    assert result["status"] == "PASS"
    assert result["verification_scope"] == "METADATA_AND_DATE_ONLY"
    assert result["source_pages_fetched"] is False
    assert result["displayed_values_independently_reconciled"] is False
    assert "not evidence of live source-value verification" in " ".join(result["limitations"])
    assert result["indicator_count"] == 44
    assert result["common_data_dates"] == ["2026-11-20"]
    assert result["per_item_timestamp_count"] == 44
    assert result["per_item_date_only_count"] == 0
    assert result["per_item_timestamp_gap"] == 0
    assert result["per_item_timestamp_missing_count"] == 0
    assert result["group_counts"] == {
        "global_markets": 17, "sectors": 11, "bonds": 3, "fx": 6,
        "energy": 2, "metals": 2, "risk": 3,
    }

    missing_url = copy.deepcopy(base)
    del missing_url["global_markets"]["道瓊工業指數"]["source"]["url"]
    expect_error(lambda: validate_market_snapshot(missing_url, "2026-11-23"), "source.url missing")

    wrong_date = copy.deepcopy(base)
    wrong_date["fx"]["美元／日圓"]["source"]["data_date"] = "2026-11-19"
    expect_error(lambda: validate_market_snapshot(wrong_date, "2026-11-23"), "source date")

    cfd_numeric = copy.deepcopy(base)
    cfd_numeric["global_markets"]["標普500指數"]["source"]["quote_type"] = "cfd_index_reference_series"
    expect_error(lambda: validate_market_snapshot(cfd_numeric, "2026-11-23"), "CFD reference must be suppressed")

    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "market.png"
        evidence.write_bytes(b"verified screenshot bytes")
        cfd_screenshot = copy.deepcopy(cfd_numeric)
        cfd_source = cfd_screenshot["global_markets"]["標普500指數"]["source"]
        cfd_source.update({
            "screenshot_fields_applied": ["close"],
            "history_page_completion_fields": ["change"],
            "screenshot_evidence_path": str(evidence),
            "screenshot_evidence_sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
            "screenshot_observation_applied_at": "2026-11-23T07:05:00+08:00",
        })
        assert validate_market_snapshot(cfd_screenshot, "2026-11-23")["status"] == "PASS"

    wrong_commodity_url = copy.deepcopy(base)
    wrong_commodity_url["energy"]["WTI原油期貨"]["instrument_url"] = "https://hk.investing.com/commodities/crude-oil-historical-data"
    expect_error(lambda: validate_market_snapshot(wrong_commodity_url, "2026-11-23"), "source.url and instrument_url")

    pending_commodity = copy.deepcopy(base)
    pending_row = pending_commodity["energy"]["WTI原油期貨"]
    pending_row["display"] = "待核實"
    pending_row["change_display"] = "待核實"
    pending_row["source"]["verification_status"] = "PENDING"
    # Pending quotes must not fail solely because the current-run contract header was unreadable.
    pending_row.pop("contract_label", None)
    assert validate_market_snapshot(pending_commodity, "2026-11-23")["status"] == "PASS"

    missing_verified_contract = copy.deepcopy(base)
    missing_verified_contract["energy"]["WTI原油期貨"].pop("contract_label", None)
    expect_error(lambda: validate_market_snapshot(missing_verified_contract, "2026-11-23"),
                 "selected contract label missing for verified quote")

    contradictory_pending = copy.deepcopy(pending_commodity)
    contradictory_pending["energy"]["WTI原油期貨"]["source"]["verification_status"] = "VERIFIED"
    expect_error(lambda: validate_market_snapshot(contradictory_pending, "2026-11-23"),
                 "pending display cannot retain verified source status")

    pending_sector = copy.deepcopy(base)
    pending_sector["sectors"]["XLK"] = "待核實"
    pending_sector["sector_sources"]["XLK"]["change_display"] = "待核實"
    pending_sector["sector_sources"]["XLK"]["verification_status"] = "PENDING"
    assert validate_market_snapshot(pending_sector, "2026-11-23")["status"] == "PASS"

    contradictory_pending_sector = copy.deepcopy(pending_sector)
    contradictory_pending_sector["sector_sources"]["XLK"]["verification_status"] = "VERIFIED"
    expect_error(lambda: validate_market_snapshot(contradictory_pending_sector, "2026-11-23"),
                 "pending display cannot retain verified source status")

    closed_sector = copy.deepcopy(base)
    closed_sector["sectors"]["XLK"] = "休市"
    closed_sector["sector_sources"]["XLK"]["change_display"] = "休市"
    closed_sector["sector_sources"]["XLK"]["verification_status"] = "CLOSED"
    assert validate_market_snapshot(closed_sector, "2026-11-23")["status"] == "PASS"

    missing_etf_source = copy.deepcopy(base)
    del missing_etf_source["sector_sources"]["XLK"]
    expect_error(lambda: validate_market_snapshot(missing_etf_source, "2026-11-23"), "key mismatch")

    print("PASS: 44 indicator count, common date, CFD suppression, commodity identity, pending commodity/sector suppression, closed sector state and ETF source map")


if __name__ == "__main__":
    main()
