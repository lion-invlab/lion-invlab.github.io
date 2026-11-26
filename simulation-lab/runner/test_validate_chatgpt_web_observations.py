#!/usr/bin/env python3
"""Regression tests for direct ChatGPT web-read evidence ingestion."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from pathlib import Path

from build_market_source_verification_manifest import IDENTITY_ALIASES
from validate_chatgpt_web_observations import main as validator_main, validate_bundle, merge_move_backup_observation
from stage2_market_fixture_bootstrap import blank_fixture, populate_fixture

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
            if is_fear_greed:
                value = source.get("backup_source_score_value", source.get("score_value", "17"))
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

    # The same direct observations must also populate a zero-value market input;
    # they must not be compared against stale numeric values from the base fixture.
    blank_data = blank_fixture(copy.deepcopy(data))
    blank_result = validate_bundle(blank_data, "2026-11-24", bundle)
    assert blank_result["verified_count"] == 43
    assert blank_result["status_counts"].get("OBSERVED_PENDING_VALIDATION") == 1
    blank_fear_greed = next(x for x in blank_result["observations"]
                             if x["group"] == "risk" and x["name"] == "fear_greed")
    assert blank_fear_greed["preexisting_value_comparison"] == "NOT_PERFORMED_BLANK_INPUT"
    assert blank_fear_greed["display_value_match"] is True
    populated_blank = populate_fixture(blank_data, blank_result)
    assert populated_blank["stage2_market_bootstrap"]["preexisting_market_values_used"] is False
    assert populated_blank["stage2_market_bootstrap"]["verified_count"] == 43
    assert populated_blank["global_markets"]["日經225"]["source"]["verification_status"] == "CLOSED"
    assert populated_blank["global_markets"]["日經225"]["display"] == "休市"

    # MOVE may be pending publication at the early capture cutoff. It must stay blank,
    # while the other 43 rows remain independently processed.
    move_pending_bundle = copy.deepcopy(bundle)
    move_pending = next(x for x in move_pending_bundle["observations"]
                        if x["group"] == "risk" and x["name"] == "move")
    move_pending.update({
        "read_status": "SOURCE_UPDATE_PENDING",
        "observed_date": None,
        "observed_value": None,
        "observed_change": None,
        "observed_row_text": "Investing.com and TradingView history pages were readable; target session row not yet posted.",
    })
    move_pending_result = validate_bundle(blank_data, "2026-11-24", move_pending_bundle)
    assert move_pending_result["verified_count"] == 42
    assert move_pending_result["status_counts"].get("OBSERVED_PENDING_VALIDATION") == 2
    move_pending_normalized = next(x for x in move_pending_result["observations"]
                                    if x["group"] == "risk" and x["name"] == "move")
    assert move_pending_normalized["read_status"] == "SOURCE_UPDATE_PENDING"
    pending_fixture = populate_fixture(blank_data, move_pending_result)
    assert pending_fixture["risk"]["move"]["display"] == "待核實"
    assert pending_fixture["risk"]["move"]["change_display"] == "待核實"
    assert pending_fixture["risk"]["move"]["source"].get("close_value") is None
    assert pending_fixture["risk"]["move"]["source"]["verification_status"] == "PENDING"

    # A target-date TradingView ICE:MOVE historical row is the sole permitted backup.
    move_backup_bundle = copy.deepcopy(bundle)
    move_backup = next(x for x in move_backup_bundle["observations"]
                       if x["group"] == "risk" and x["name"] == "move")
    move_source = data["risk"]["move"]["source"]
    backup_close = move_source.get("close_value") or move_source.get("history_close")
    backup_change = move_source.get("daily_change_percent") or move_source.get("history_change")
    move_backup.update({
        "attempt_url": "https://www.tradingview.com/symbols/ICE-MOVE/history/",
        "source_role": "BACKUP_1",
        "page_title": "ICE BofAML U.S. Bond Market Option Volatility Estimate Index",
        "instrument_identity": "ICE BofAML U.S. Bond Market Option Volatility Estimate Index",
        "observed_value": backup_close,
        "observed_change": backup_change,
        "observed_value_field": "Price",
        "observed_change_field": "Change %",
        "observed_headers": ["Date", "Price", "Change %"],
        "observed_row_text": "Nov 23, 2026 | " + str(backup_close) + " | " + str(backup_change),
        "read_status": "PAGE_CONTENT_READ_SUCCESS",
        "observed_date": move_source.get("data_date"),
    })
    move_backup_result = validate_bundle(blank_data, "2026-11-24", move_backup_bundle)
    move_backup_normalized = next(x for x in move_backup_result["observations"]
                                  if x["group"] == "risk" and x["name"] == "move")
    assert move_backup_normalized["status"] == "VERIFIED"
    assert move_backup_normalized["source_role"] == "BACKUP_1"
    backup_fixture = populate_fixture(blank_data, move_backup_result)
    assert backup_fixture["risk"]["move"]["source"]["verification_status"] == "BACKUP_VERIFIED"
    assert backup_fixture["risk"]["move"]["source"]["verified_source_role"] == "BACKUP_1"
    assert backup_fixture["risk"]["move"]["source"]["evidence_source_url"] == "https://www.tradingview.com/symbols/ICE-MOVE/history/"

    # The production web-bundle path performs only a one-row TradingView read when
    # Investing.com reports SOURCE_NO_DATA; the other 43 normalized observations stay untouched.
    primary_missing_bundle = copy.deepcopy(bundle)
    primary_missing = next(x for x in primary_missing_bundle["observations"]
                           if x["group"] == "risk" and x["name"] == "move")
    primary_missing.update({"read_status": "SOURCE_NO_DATA", "observed_date": None,
                            "observed_value": None, "observed_change": None,
                            "observed_row_text": "Investing.com historical page readable; target row absent."})
    primary_missing_result = validate_bundle(blank_data, "2026-11-24", primary_missing_bundle)
    merged_backup = merge_move_backup_observation(copy.deepcopy(primary_missing_result),
                                                  copy.deepcopy(move_backup_normalized), "SOURCE_NO_DATA")
    merged_move = next(x for x in merged_backup["observations"]
                       if x["group"] == "risk" and x["name"] == "move")
    assert merged_backup["move_backup_attempted"] is True
    assert merged_backup["verified_count"] == 43
    assert merged_move["source_role"] == "BACKUP_1"
    assert merged_move["evidence_source_url"] == "https://www.tradingview.com/symbols/ICE-MOVE/history/"

    # Exercise the exact production CLI path: blank the supplied fixture, validate the
    # date-matched direct page bundle, and write only current observations back in place.
    with tempfile.TemporaryDirectory() as tmp:
        data_path=Path(tmp)/"report-data.json"
        bundle_path=Path(tmp)/"web-observations.json"
        cnn_path=Path(tmp)/"cnn-observations.json"
        output_path=Path(tmp)/"normalized-observations.json"
        data_path.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
        bundle_path.write_text(json.dumps(bundle,ensure_ascii=False),encoding="utf-8")
        cnn_path.write_text('{"observations":[]}',encoding="utf-8")
        argv=["validate_chatgpt_web_observations.py","--data",str(data_path),
              "--report-date","2026-11-24","--input",str(bundle_path),
              "--cnn-observation",str(cnn_path),"--output",str(output_path)]
        with patch.object(sys,"argv",argv):
            validator_main()
        written=json.loads(data_path.read_text(encoding="utf-8"))
        normalized=json.loads(output_path.read_text(encoding="utf-8"))
        assert written["stage2_market_bootstrap"]["preexisting_market_values_used"] is False
        assert written["stage2_market_bootstrap"]["verified_count"] == 43
        assert len(normalized["observations"]) == 44
        assert written["global_markets"]["日經225"]["source"]["verification_status"] == "CLOSED"

    # CNN official previous_close is raw decimal precision and must match its own pinned raw value.
    cnn_official = copy.deepcopy(bundle)
    cnn_fg = next(x for x in cnn_official["observations"] if x["group"] == "risk" and x["name"] == "fear_greed")
    cnn_fg.update({
        "read_method": "CNN_OFFICIAL_PREVIOUS_CLOSE",
        "data_endpoint_url": "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
        "http_status": 200,
        "raw_response_sha256": "a" * 64,
        "observed_value_field": "fear_and_greed.previous_close",
        "observed_change_field": "derived_from_fear_and_greed.previous_close_using_cnn_bands",
        "previous_close_target_date": "2026-11-23",
        "source_timestamp_utc": "2026-11-24T01:59:53+00:00",
        "observed_value": "16.9658627087199",
        "observed_change": "extreme fear",
        "status": "VERIFIED",
    })
    cnn_result = validate_bundle(data, "2026-11-24", cnn_official)
    assert cnn_result["verified_count"] == 43
    assert cnn_result["status_counts"].get("OBSERVED_PENDING_VALIDATION") == 1
    cnn_row = next(x for x in cnn_result["observations"] if x["group"] == "risk" and x["name"] == "fear_greed")
    assert cnn_row["raw_source_value_match"] is True

    wrong_cnn_raw = copy.deepcopy(cnn_official)
    wrong_cnn_fg = next(x for x in wrong_cnn_raw["observations"] if x["group"] == "risk" and x["name"] == "fear_greed")
    wrong_cnn_fg["observed_value"] = "17"
    wrong_cnn_result = validate_bundle(data, "2026-11-24", wrong_cnn_raw)
    assert wrong_cnn_result["verified_count"] == 42
    assert wrong_cnn_result["status_counts"].get("OBSERVED_PENDING_VALIDATION") == 2

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

    print("PASS: 43 current-session historical page observations reconcile to exact fixture values and dates")
    print("PASS: one official market closure is explicitly recorded; no numeric market row is silently reused")
    print("PASS: CNN official previous_close uses its raw decimal; FGScore fallback uses its separately pinned rounded integer")
    print("PASS: wrong URL, stale capture, missing rows and numeric mismatches cannot pass")


if __name__ == "__main__":
    main()
