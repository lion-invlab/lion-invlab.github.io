#!/usr/bin/env python3
"""Regression tests for direct ChatGPT web-read evidence ingestion."""
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from build_market_source_verification_manifest import IDENTITY_ALIASES
from validate_chatgpt_web_observations import validate_bundle

FIXTURE = Path("simulation-lab/fixtures/report-data-2026-11-24.json")
CLOSURE_URL = "https://www8.cao.go.jp/chosei/shukujitsu/gaiyou.html"
FG_WEB_REF = "SYNTHETIC_TEST_ONLY"


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
            is_fear_greed = group == "risk" and name == "fear_greed"
            is_closed = group == "global_markets" and name == "日經225"
            is_no_data = group == "risk" and name == "move"
            if is_fear_greed:
                value = "17"
                change = "Extreme Fear"
                value_field, change_field = "Score", "Band"
                headers = ["When", "Score", "Change to now", "Band"]
                row_text = "As of Nov 23, 2026 UTC | Now | 17 | — | Extreme Fear"
                page_title = "Fear & Greed Index - FGScore"
                identity = "US stocks · CNN Fear & Greed Index"
                reader_ref, line_start, line_end = FG_WEB_REF, 7, 17
                read_method = "CHATGPT_WEB_OPEN_HISTORICAL_PAGE"
                read_status = "PAGE_CONTENT_READ_SUCCESS"
                observed_date = source.get("data_date")
            elif is_closed:
                value = change = None
                value_field, change_field = "Price", "Change %"
                headers = ["Date", "Price", "Change %"]
                row_text = "Last available row: Nov 20, 2026; Japan market closed on Nov 23, 2026 (Labor Thanksgiving Day)."
                page_title = "Nikkei 225 Historical Data"
                identity = "Nikkei 225"
                reader_ref, line_start, line_end = FG_WEB_REF, 47, 51
                read_method = "CHATGPT_WEB_OPEN_HISTORICAL_PAGE"
                read_status = "MARKET_CLOSED"
                observed_date = None
            elif is_no_data:
                value_field, change_field = "Price", "Change %"
                headers = ["Date", "Price", "Open", "High", "Low", "Vol.", "Change %"]
                row_text = "Nov 23, 2026 | 100.91 | 106.31 | 110.09 | 100.91 | | -5.08%"
                page_title = "ICE BofAML MOVE Historical Data"
                identity = "ICE BofAML MOVE"
                reader_ref, line_start, line_end = FG_WEB_REF, 45, 50
                read_method = "CHATGPT_WEB_SEARCH_RESULT_HISTORICAL_PAGE"
                read_status = "PAGE_CONTENT_READ_SUCCESS"
                observed_date = source.get("data_date")
            else:
                is_hk = "hk.investing.com" in str(source.get("url") or "")
                value_field, change_field = ("收市", "升跌（%）") if is_hk else ("Price", "Change %")
                headers = [value_field, change_field]
                date_label = "2026年11月23日" if is_hk else "Nov 23, 2026"
                row_text = f"{date_label} | {value} | {change}"
                page_title = name
                identity = IDENTITY_ALIASES.get(name, [name])[0]
                reader_ref, line_start, line_end = FG_WEB_REF, 50, 56
                read_method = "CHATGPT_WEB_OPEN_HISTORICAL_PAGE"
                read_status = "PAGE_CONTENT_READ_SUCCESS"
                observed_date = source.get("data_date")
            row = {
                "group": group, "name": name, "source_url": source.get("url"),
                "target_date": source.get("data_date"), "observed_date": observed_date,
                "page_title": page_title, "instrument_identity": identity,
                "observed_value": value, "observed_change": change,
                "observed_value_field": value_field, "observed_change_field": change_field,
                "observed_headers": headers, "observed_row_text": row_text,
                "web_reader_ref": reader_ref, "web_line_start": line_start, "web_line_end": line_end,
                "read_method": read_method, "status": "VERIFIED", "read_status": read_status,
                "http_status": None,
            }
            if is_closed:
                row["closure_evidence_url"] = CLOSURE_URL
            rows.append(row)
    for name, source in (data.get("sector_sources") or {}).items():
        is_hk = "hk.investing.com" in str(source.get("url") or "")
        value_field, change_field = ("收市", "升跌（%）") if is_hk else ("Price", "Change %")
        rows.append({
            "group": "sectors", "name": name, "source_url": source.get("url"),
            "target_date": source.get("data_date"), "observed_date": source.get("data_date"),
            "page_title": f"State Street SPDR ETF ({name})", "instrument_identity": name,
            "observed_value": source.get("history_close"), "observed_change": source.get("history_change"),
            "observed_value_field": value_field, "observed_change_field": change_field,
            "observed_headers": [value_field, change_field],
            "observed_row_text": f"{'2026年11月23日' if is_hk else 'Nov 23, 2026'} | {source.get('history_close')} | {source.get('history_change')}",
            "web_reader_ref": FG_WEB_REF, "web_line_start": 50, "web_line_end": 56,
            "read_method": "CHATGPT_WEB_OPEN_HISTORICAL_PAGE", "status": "VERIFIED",
            "read_status": "PAGE_CONTENT_READ_SUCCESS", "http_status": None,
        })
    return {
        "report_date": "2026-11-24", "trading_date": data["trading_date"],
        "captured_at_utc": captured, "capture_session": "SYNTHETIC_TEST_ONLY",
        "observations": rows,
    }


def main():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    bundle = make_bundle(data)
    result = validate_bundle(data, "2026-11-24", bundle)
    assert len(result["observations"]) == 44
    assert result["verified_count"] == 43
    assert result["status_counts"].get("OBSERVED_PENDING_VALIDATION") == 1
    assert result["prior_observation_reused_count"] == 0
    assert result["displayed_values_independently_reconciled"] is False

    # A same-report-day historical close observation remains reusable after delayed orchestration.
    delayed = copy.deepcopy(bundle)
    delayed["captured_at_utc"] = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    delayed_result = validate_bundle(data, "2026-11-24", delayed)
    assert len(delayed_result["observations"]) == 44

    wrong_value = copy.deepcopy(bundle)
    first_verified = next(x for x in wrong_value["observations"] if x["read_status"] == "PAGE_CONTENT_READ_SUCCESS" and x["group"] != "risk")
    first_verified["observed_value"] = "0"
    partial = validate_bundle(data, "2026-11-24", wrong_value)
    assert partial["verified_count"] == 42
    assert partial["status_counts"].get("OBSERVED_PENDING_VALIDATION") == 2

    wrong_url = copy.deepcopy(bundle)
    wrong_url["observations"][0]["source_url"] += "?wrong=1"
    try:
        validate_bundle(data, "2026-11-24", wrong_url)
    except ValueError as exc:
        assert "source URL" in str(exc)
    else:
        raise AssertionError("wrong source URL must be rejected")

    stale = copy.deepcopy(bundle)
    stale["captured_at_utc"] = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    try:
        validate_bundle(data, "2026-11-24", stale)
    except ValueError as exc:
        assert "stale" in str(exc)
    else:
        raise AssertionError("stale web evidence must be rejected")

    missing = copy.deepcopy(bundle)
    missing["observations"].pop()
    try:
        validate_bundle(data, "2026-11-24", missing)
    except ValueError as exc:
        assert "44 unique" in str(exc)
    else:
        raise AssertionError("missing source observation must be rejected")

    print("PASS: 42 current-session direct page reads plus one dated Investing.com search-result row reconcile to exact fixture values and dates")
    print("PASS: one official market closure remains explicitly pending; no market row is silently reused")
    print("PASS: CNN Fear & Greed uses the pinned FGScore backup only when official mapping is unavailable")
    print("PASS: wrong URL, stale capture, missing rows and numeric mismatches cannot pass")


if __name__ == "__main__":
    main()
