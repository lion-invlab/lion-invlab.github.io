#!/usr/bin/env python3
"""Regression tests for direct ChatGPT web-read evidence ingestion."""
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from build_market_source_verification_manifest import IDENTITY_ALIASES
from validate_chatgpt_web_observations import validate_bundle

FIXTURE = Path("simulation-lab/fixtures/report-data-2026-11-23.json")


def make_bundle(data):
    captured = datetime.now(timezone.utc).isoformat()
    rows = []
    groups = ("global_markets", "bonds", "fx", "energy", "metals", "risk")
    for group in groups:
        for name, item in (data.get(group) or {}).items():
            source = item.get("source") or {}
            value = source.get("close_value")
            if value is None:
                value = source.get("history_close")
            if value is None:
                value = source.get("score_value")
            change = source.get("daily_change_percent")
            if change is None:
                change = source.get("history_change")
            if change is None:
                change = source.get("band")
            is_cnn = group == "risk" and name == "fear_greed"
            if is_cnn:
                value = "10.4133580705009"
            value_field = "fear_and_greed_historical.data[].y" if is_cnn else "Price"
            change_field = "fear_and_greed_historical.data[].rating" if is_cnn else "Change %"
            headers = [value_field, change_field]
            rows.append({
                "group": group, "name": name, "source_url": source.get("url"),
                "target_date": source.get("data_date"), "observed_date": source.get("data_date"),
                "page_title": "CNN Business Fear & Greed historical data" if is_cnn else name,
                "instrument_identity": IDENTITY_ALIASES.get(name, [name])[0],
                "observed_value": value, "observed_change": change,
                "observed_value_field": value_field, "observed_change_field": change_field,
                "observed_headers": headers,
                "observed_row_text": "" if is_cnn else f"Nov 20, 2026 | {value} | {change}",
                "web_reader_ref": "SYNTHETIC_TEST_ONLY" if not is_cnn else None,
                "web_line_start": 50 if not is_cnn else None,
                "web_line_end": 50 if not is_cnn else None,
                "read_method": "CNN_OFFICIAL_HISTORICAL_JSON" if is_cnn else "CHATGPT_WEB_OPEN_HISTORICAL_PAGE",
                "status": "VERIFIED",
                "read_status": "API_RESPONSE_READ_SUCCESS" if is_cnn else "PAGE_CONTENT_READ_SUCCESS",
                "http_status": 200 if is_cnn else None,
                "data_endpoint_url": "https://production.dataviz.cnn.io/index/fearandgreed/graphdata" if is_cnn else None,
                "raw_response_sha256": "a" * 64 if is_cnn else None,
            })
    for name, source in (data.get("sector_sources") or {}).items():
        rows.append({
            "group": "sectors", "name": name, "source_url": source.get("url"),
            "target_date": source.get("data_date"), "observed_date": source.get("data_date"),
            "page_title": f"State Street SPDR ETF ({name})",
            "instrument_identity": name,
            "observed_value": source.get("history_close"), "observed_change": source.get("history_change"),
            "observed_value_field": "Price", "observed_change_field": "Change %",
            "observed_headers": ["Price", "Change %"],
            "observed_row_text": f"Nov 20, 2026 | {source.get('history_close')} | {source.get('history_change')}",
            "web_reader_ref": "SYNTHETIC_TEST_ONLY", "web_line_start": 50, "web_line_end": 50,
            "read_method": "CHATGPT_WEB_OPEN_HISTORICAL_PAGE", "status": "VERIFIED",
            "read_status": "PAGE_CONTENT_READ_SUCCESS", "http_status": None,
        })
    return {
        "report_date": "2026-11-23", "trading_date": data["trading_date"],
        "captured_at_utc": captured, "capture_session": "SYNTHETIC_TEST_ONLY",
        "observations": rows,
    }


def main():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    bundle = make_bundle(data)
    result = validate_bundle(data, "2026-11-23", bundle)
    assert len(result["observations"]) == 44
    assert result["verified_count"] == 44
    assert result["status_counts"] == {"VERIFIED": 44}
    assert result["prior_observation_reused_count"] == 0
    assert result["displayed_values_independently_reconciled"] is True

    wrong_value = copy.deepcopy(bundle)
    wrong_value["observations"][0]["observed_value"] = "0"
    partial = validate_bundle(data, "2026-11-23", wrong_value)
    assert partial["verified_count"] == 43
    assert partial["status_counts"].get("OBSERVED_PENDING_VALIDATION") == 1

    wrong_url = copy.deepcopy(bundle)
    wrong_url["observations"][0]["source_url"] += "?wrong=1"
    try:
        validate_bundle(data, "2026-11-23", wrong_url)
    except ValueError as exc:
        assert "source URL" in str(exc)
    else:
        raise AssertionError("wrong source URL must be rejected")

    stale = copy.deepcopy(bundle)
    stale["captured_at_utc"] = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    try:
        validate_bundle(data, "2026-11-23", stale)
    except ValueError as exc:
        assert "stale" in str(exc)
    else:
        raise AssertionError("stale web evidence must be rejected")

    missing = copy.deepcopy(bundle)
    missing["observations"].pop()
    try:
        validate_bundle(data, "2026-11-23", missing)
    except ValueError as exc:
        assert "44 unique" in str(exc)
    else:
        raise AssertionError("missing source observation must be rejected")

    print("PASS: 44 current-session direct page reads reconcile to exact fixture values and dates")
    print("PASS: CNN decimal score is compared using TAC integer display rounding")
    print("PASS: wrong URL, stale capture, missing rows and numeric mismatches cannot pass")


if __name__ == "__main__":
    main()
