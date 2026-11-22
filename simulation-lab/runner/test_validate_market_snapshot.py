#!/usr/bin/env python3
"""Regression tests for the 44-indicator source/date metadata gate."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from validate_market_snapshot import validate_market_snapshot


FIXTURE = Path("simulation-lab/fixtures/report-data-2026-11-23.json")


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

    wrong_commodity_url = copy.deepcopy(base)
    wrong_commodity_url["energy"]["WTI原油期貨"]["instrument_url"] = "https://hk.investing.com/commodities/crude-oil-historical-data"
    expect_error(lambda: validate_market_snapshot(wrong_commodity_url, "2026-11-23"), "source.url and instrument_url")

    missing_etf_source = copy.deepcopy(base)
    del missing_etf_source["sector_sources"]["XLK"]
    expect_error(lambda: validate_market_snapshot(missing_etf_source, "2026-11-23"), "key mismatch")

    print("PASS: 44 indicator count, per-row HTTPS source metadata, common date, CFD suppression, commodity identity and ETF source map")


if __name__ == "__main__":
    main()
