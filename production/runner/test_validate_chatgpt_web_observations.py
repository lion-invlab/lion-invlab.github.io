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
from decimal import Decimal

from build_market_source_verification_manifest import IDENTITY_ALIASES, build_manifest
from validate_chatgpt_web_observations import main as validator_main, validate_bundle
from stage2_market_fixture_bootstrap import blank_fixture, populate_fixture
from validate_chatgpt_web_observations import persist_fixture
from stage2_screenshot_inputs import apply_screenshot_values_to_fixture, load_screenshot_bundle
from stage2_move_retry import merge_move_retry_observation
from validate_prebuild_stage_inputs import validate_observation_bundle

FIXTURE = Path("production/testdata/report-data-2026-11-24.json")
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
                row["closure_evidence_text"] = "Official Japan public-holiday calendar identifies 2026-11-23 as Labor Thanksgiving Day."
                row["closure_evidence_reader_ref"] = "CLOSURE_TEST_REF"
                row["closure_evidence_line_start"] = 10
                row["closure_evidence_line_end"] = 12
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
    # Diagnostic mode must never persist the blanked or screenshot-enriched working Fixture.
    with tempfile.TemporaryDirectory() as tmp:
        diagnostic_path = Path(tmp) / "fixture.json"
        original = b'{"keep":"original"}'
        diagnostic_path.write_bytes(original)
        assert persist_fixture(diagnostic_path, {"changed": True}, no_fixture_write=True) is False
        assert diagnostic_path.read_bytes() == original
        assert persist_fixture(diagnostic_path, {"changed": True}, no_fixture_write=False) is True
        assert json.loads(diagnostic_path.read_text(encoding="utf-8")) == {"changed": True}

    data = json.loads(FIXTURE.read_text(encoding="utf-8"))

    # Investing.com HK's native Traditional Chinese historical table headers
    # must be accepted as screenshot field labels, including the clipped-width
    # single-character High/Low columns shown in mobile captures.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        image_a = root / "hangseng-a.png"
        image_b = root / "hangseng-b.png"
        image_a.write_bytes(b"synthetic investing screenshot A")
        image_b.write_bytes(b"synthetic investing screenshot B")
        import hashlib
        sha_a = hashlib.sha256(image_a.read_bytes()).hexdigest()
        sha_b = hashlib.sha256(image_b.read_bytes()).hexdigest()
        hs_source = data["global_markets"]["香港恆生指數"]["source"]
        hs_bundle = {
            "report_date": data["report_date"], "trading_date": data["trading_date"],
            "observations": [{
                "group":"global_markets", "name":"香港恆生指數",
                "data_date":data["trading_date"], "source_url":hs_source["url"],
                "instrument_identity":"Hang Seng Index (香港恆生指數)",
                "captured_at":"2026-11-24T06:38:00+08:00",
                "fields":{
                    "close":{"value":"22,383.74","field_name":"價格","evidence_path":"hangseng-a.png","evidence_sha256":sha_a,"captured_at":"2026-11-24T06:38:00+08:00"},
                    "open":{"value":"22,168.19","field_name":"開市","evidence_path":"hangseng-a.png","evidence_sha256":sha_a,"captured_at":"2026-11-24T06:38:00+08:00"},
                    "high":{"value":"22,436.18","field_name":"高","evidence_path":"hangseng-a.png","evidence_sha256":sha_a,"captured_at":"2026-11-24T06:38:00+08:00"},
                    "low":{"value":"21,998.05","field_name":"低","evidence_path":"hangseng-b.png","evidence_sha256":sha_b,"captured_at":"2026-11-24T06:38:00+08:00"},
                    "change":{"value":"-0.12%","field_name":"升跌率 %","evidence_path":"hangseng-b.png","evidence_sha256":sha_b,"captured_at":"2026-11-24T06:38:00+08:00"},
                },
            }],
        }
        hs_path = root / "hangseng-sidecar.json"
        hs_path.write_text(json.dumps(hs_bundle,ensure_ascii=False),encoding="utf-8")
        loaded_hs = load_screenshot_bundle(hs_path,data,root)
        hs_fields = loaded_hs[("global_markets","香港恆生指數")]["fields"]
        assert set(hs_fields) == {"close","open","high","low","change"}
        assert hs_fields["high"]["field_name"] == "高" and hs_fields["low"]["field_name"] == "低"
        assert hs_fields["change"]["field_name"] == "升跌率 %"
        assert hs_fields["low"]["evidence_sha256"] == sha_b

    # Screenshot fields, including optional OHLC, must populate the blank Fixture
    # without inheriting stale PRIMARY provenance from a previous observation.
    screenshot_fixture = blank_fixture(copy.deepcopy(data))
    move_screenshot = {
        "group":"risk","name":"move","source_url":data["risk"]["move"]["source"]["url"],
        "data_date":data["trading_date"],"instrument_identity":"Merrill Lynch Option Volatility Estimate (INDEXNYSEGIS: MOVE)",
        "captured_at":"2026-11-26T06:47:00+08:00",
        "fields":{
            "close":{"value":"97.54","field_name":"Price","evidence_path":"screenshots/move.png","evidence_sha256":"a"*64,"captured_at":"2026-11-26T06:47:00+08:00"},
            "change":{"value":"-1.32%","field_name":"Change %","evidence_path":"screenshots/move.png","evidence_sha256":"a"*64,"captured_at":"2026-11-26T06:47:00+08:00"},
            "open":{"value":"99.32","field_name":"Open","evidence_path":"screenshots/move.png","evidence_sha256":"a"*64,"captured_at":"2026-11-26T06:47:00+08:00"},
            "high":{"value":"102.73","field_name":"High","evidence_path":"screenshots/move.png","evidence_sha256":"a"*64,"captured_at":"2026-11-26T06:47:00+08:00"},
            "low":{"value":"97.40","field_name":"Low","evidence_path":"screenshots/move.png","evidence_sha256":"a"*64,"captured_at":"2026-11-26T06:47:00+08:00"},
        },
    }
    apply_screenshot_values_to_fixture(screenshot_fixture,{("risk","move"):move_screenshot})
    move_source = screenshot_fixture["risk"]["move"]["source"]
    assert move_source["close_value"] == "97.54"
    assert move_source["daily_change_percent"] == "-1.32"
    assert Decimal(move_source["open"]) == Decimal("99.32") and Decimal(move_source["high"]) == Decimal("102.73") and Decimal(move_source["low"]) == Decimal("97.40")
    assert "source_role" not in move_source
    screenshot_bundle = make_bundle(screenshot_fixture)
    screenshot_row = next(x for x in screenshot_bundle["observations"] if x["group"]=="risk" and x["name"]=="move")
    screenshot_row.update({
        "status":"VERIFIED","read_status":"USER_PROVIDED_SCREENSHOT_CONFIRMED",
        "read_method":"USER_PROVIDED_SCREENSHOT","provenance":"CURRENT_USER_PROVIDED_SCREENSHOT",
        "source_page_fetched":False,"instrument_identity":move_screenshot["instrument_identity"],
        "instrument_identity_status":"VERIFIED","screenshot_instrument_identity_status":"VERIFIED",
        "field_mapping_status":"VERIFIED","observed_value":"97.54","observed_change":"-1.32",
        "observed_value_field":"Price","observed_change_field":"Change %",
        "field_evidence":{
            key:{"source_type":"USER_PROVIDED_SCREENSHOT","evidence_path":"screenshots/move.png",
                 "evidence_sha256":"a"*64,"value":value["value"],"field_name":value["field_name"]}
            for key,value in move_screenshot["fields"].items()
        },
    })
    screenshot_populated = populate_fixture(screenshot_fixture,screenshot_bundle)
    screenshot_move_source = screenshot_populated["risk"]["move"]["source"]
    assert screenshot_move_source["verification_status"] == "VERIFIED"
    assert screenshot_move_source["source_role"] == "USER_PROVIDED_SCREENSHOT"
    assert screenshot_move_source["source_page_fetched"] is False
    assert Decimal(screenshot_move_source["open"]) == Decimal("99.32") and Decimal(screenshot_move_source["high"]) == Decimal("102.73") and Decimal(screenshot_move_source["low"]) == Decimal("97.40")
    bundle = make_bundle(data)

    # A delayed retry may replace only MOVE; the other 43 frozen observations
    # must remain byte-for-byte equivalent after canonical JSON serialization.
    pending_base = copy.deepcopy(bundle)
    pending_move = next(x for x in pending_base["observations"] if x["group"]=="risk" and x["name"]=="move")
    pending_move.update({"status":"SOURCE_UPDATE_PENDING","read_status":"SOURCE_UPDATE_PENDING",
                         "observed_date":None,"observed_value":None,"observed_change":None})
    retry_move = copy.deepcopy(pending_move)
    retry_move.update({
        "status":"VERIFIED","read_status":"PAGE_CONTENT_READ_SUCCESS",
        "observed_date":data["trading_date"],"observed_value":"97.54","observed_change":"-1.32",
        "instrument_identity_status":"VERIFIED","field_mapping_status":"VERIFIED",
        "source_page_fetched":True,"finished_at_tw":"2026-11-24T07:30:00+08:00",
    })
    retry_bundle = {"report_date":bundle["report_date"],"trading_date":bundle["trading_date"],"observations":[retry_move]}
    merged_retry = merge_move_retry_observation(pending_base,retry_bundle)
    before_non_move = {(x["group"],x["name"]):json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))
                       for x in pending_base["observations"] if (x["group"],x["name"]) != ("risk","move")}
    after_non_move = {(x["group"],x["name"]):json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))
                      for x in merged_retry["observations"] if (x["group"],x["name"]) != ("risk","move")}
    assert before_non_move == after_non_move
    assert merged_retry["prior_observation_reused_count"] == 43
    assert merged_retry["move_delayed_retry"]["non_move_observations_unchanged"] is True
    assert merged_retry["source_pages_fetched_this_run"] is False
    assert next(x for x in merged_retry["observations"] if x["group"]=="risk" and x["name"]=="move")["observed_value"] == "97.54"

    still_pending_retry = copy.deepcopy(retry_move)
    still_pending_retry.update({"status":"SOURCE_UPDATE_PENDING","read_status":"SOURCE_UPDATE_PENDING",
                                "observed_date":None,"observed_value":None,"observed_change":None})
    pending_merged = merge_move_retry_observation(
        pending_base,{"report_date":bundle["report_date"],"trading_date":bundle["trading_date"],"observations":[still_pending_retry]})
    pending_merged_move = next(x for x in pending_merged["observations"] if x["group"]=="risk" and x["name"]=="move")
    assert pending_merged_move["observed_value"] is None and pending_merged_move["observed_change"] is None
    assert pending_merged_move["status"] == "SOURCE_UPDATE_PENDING"
    result = validate_bundle(data, "2026-11-24", bundle)
    assert len(result["observations"]) == 44
    assert result["verified_count"] == 43
    assert result["status_counts"].get("OBSERVED_PENDING_VALIDATION") == 1
    assert result["prior_observation_reused_count"] == 0
    assert result["displayed_values_independently_reconciled"] is False

    # The normalized direct-web bundle is also the Stage 4 pre-build input.
    # Every VERIFIED page row must carry field-level evidence, not merely a
    # page title and row excerpt.
    prebuild_summary = validate_observation_bundle(result, "2026-11-24", "2026-11-23")
    assert prebuild_summary["row_count"] == 44
    assert prebuild_summary["page_only_row_count"] == 43
    assert prebuild_summary["screenshot_only_row_count"] == 0
    assert prebuild_summary["mixed_field_row_count"] == 0
    verified_rows = [row for row in result["observations"] if row["status"] == "VERIFIED"]
    assert all({"close", "change"}.issubset(row.get("field_evidence", {}))
               for row in verified_rows if not (row["group"] == "risk" and row["name"] == "fear_greed"))
    fear_greed_row = next(row for row in verified_rows
                          if row["group"] == "risk" and row["name"] == "fear_greed")
    assert {"score", "band"}.issubset(fear_greed_row["field_evidence"])

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
    assert populated_blank["global_markets"]["日經225"]["display"] == "-" and populated_blank["global_markets"]["日經225"]["change_display"] == "休市"

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
        "observed_row_text": "Investing.com historical page was readable; target session row not yet posted.",
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

    # MOVE must reject every alternate historical-page source and keep the
    # approved Investing.com URL as its only page evidence source.
    for invalid_fields in (
        {"attempt_url": "https://www.tradingview.com/symbols/ICE-MOVE/"},
        {"evidence_source_url": "https://www.tradingview.com/symbols/ICE-MOVE/"},
        {"source_role": "BACKUP_1"},
    ):
        invalid_bundle = copy.deepcopy(bundle)
        invalid_move = next(x for x in invalid_bundle["observations"]
                            if x["group"] == "risk" and x["name"] == "move")
        invalid_move.update(invalid_fields)
        try:
            validate_bundle(blank_data, "2026-11-24", invalid_bundle)
        except ValueError as exc:
            assert "MOVE" in str(exc) and ("alternate" in str(exc) or "pinned" in str(exc))
        else:
            raise AssertionError(f"Unapproved MOVE alternate-source evidence was accepted: {invalid_fields}")

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

    # CNN Business current dashboard is the official primary source; no API endpoint is accepted.
    cnn_official = copy.deepcopy(bundle)
    cnn_fg = next(x for x in cnn_official["observations"] if x["group"] == "risk" and x["name"] == "fear_greed")
    fg_source = data["risk"]["fear_greed"]["source"]
    official_score = fg_source.get("source_score_value")
    official_band = fg_source.get("source_band") or fg_source.get("band")
    cnn_fg.update({
        "read_method": "CNN_OFFICIAL_CURRENT_DASHBOARD",
        "source_url": fg_source["approved_primary_urls"][0],
        "source_role": "PRIMARY",
        "page_title": "CNN Business Fear & Greed Index",
        "instrument_identity": "CNN Fear & Greed Index",
        "observed_value": official_score,
        "observed_change": official_band,
        "observed_value_field": "Current Score",
        "observed_change_field": "Current Band",
        "observed_headers": ["Current Score", "Current Band"],
        "observed_row_text": f"2026-11-23 | Current CNN score {official_score} | {official_band}",
        "source_timestamp_utc": "2026-11-23T23:00:00Z",
        "web_reader_ref": "CNN_TEST_REF",
        "web_line_start": 5,
        "web_line_end": 10,
        "observed_date": fg_source.get("data_date"),
        "read_status": "PAGE_CONTENT_READ_SUCCESS",
        "source_page_fetched": True,
        "status": "VERIFIED",
        "http_status": None,
    })
    cnn_result = validate_bundle(data, "2026-11-24", cnn_official)
    assert cnn_result["verified_count"] == 43
    assert cnn_result["status_counts"].get("OBSERVED_PENDING_VALIDATION") == 1
    cnn_row = next(x for x in cnn_result["observations"] if x["group"] == "risk" and x["name"] == "fear_greed")
    assert cnn_row["raw_source_value_match"] is True

    wrong_cnn_raw = copy.deepcopy(cnn_official)
    wrong_cnn_fg = next(x for x in wrong_cnn_raw["observations"] if x["group"] == "risk" and x["name"] == "fear_greed")
    wrong_cnn_fg["observed_value"] = str(float(official_score) + 1)
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

    # Real 2026-11-27 handoff fixture: all 44 rows must bind to the 2026-11-26 target date.
    from create_run_fixture import build as build_run_fixture
    run_1127 = build_run_fixture(datetime(2026, 11, 27).date(), "TAC-2026-11-27-BUNDLE-TEST")
    data_1127 = run_1127["market_fixture"]
    bundle_1127 = json.loads(Path("production/input/market-history-web-observations-2026-11-27.json").read_text(encoding="utf-8"))
    normalized_1127 = validate_bundle(data_1127, "2026-11-27", bundle_1127)
    assert len(normalized_1127["observations"]) == 44
    assert normalized_1127["verified_count"] == 27
    move_1127 = next(row for row in normalized_1127["observations"] if row.get("group") == "risk" and row.get("name") == "move")
    assert move_1127["read_status"] == "SOURCE_UPDATE_PENDING"
    assert normalized_1127["prior_observation_reused_count"] == 0
    populated_1127 = populate_fixture(data_1127, normalized_1127)
    fixture_statuses = [
        (item.get("source") or {}).get("verification_status")
        for group in ("global_markets", "bonds", "fx", "energy", "metals", "risk")
        for item in (populated_1127.get(group) or {}).values()
    ] + [
        (source or {}).get("verification_status")
        for source in (populated_1127.get("sector_sources") or {}).values()
    ]
    assert fixture_statuses.count("VERIFIED") == 26, fixture_statuses
    assert fixture_statuses.count("BACKUP_VERIFIED") == 1, fixture_statuses
    assert fixture_statuses.count("CLOSED") == 16, fixture_statuses
    assert fixture_statuses.count("PENDING") == 1, fixture_statuses
    assert populated_1127["global_markets"]["道瓊工業指數"]["source"]["verification_status"] == "CLOSED"
    assert populated_1127["sector_sources"]["XLE"]["verification_status"] == "CLOSED"
    # Regression: every officially closed sector must expose the same CLOSED display state.
    for sector_name, sector_source in populated_1127["sector_sources"].items():
        if sector_source.get("verification_status") == "CLOSED":
            assert populated_1127["sectors"][sector_name] == "休市", (sector_name, populated_1127["sectors"][sector_name])
            assert sector_source.get("change_display") == "休市", (sector_name, sector_source.get("change_display"))
    assert populated_1127["risk"]["move"]["source"]["verification_status"] == "PENDING"
    assert populated_1127["risk"]["move"]["source"].get("close_value") is None
    assert populated_1127["trading_date"] == "2026-11-26"

    print("PASS: 43 current-session historical page observations reconcile to exact fixture values and dates")
    print("PASS: one official market closure is explicitly recorded; no numeric market row is silently reused")
    print("PASS: CNN Business current dashboard is the official primary source; FGScore remains a separately pinned backup")
    print("PASS: wrong URL, stale capture, missing rows and numeric mismatches cannot pass")


if __name__ == "__main__":
    main()
