#!/usr/bin/env python3
"""Validate direct ChatGPT web-page observations before SIM-1.4 Stage 2 manifest creation."""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import tempfile
import sys
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from stage2_market_fixture_bootstrap import blank_fixture, populate_fixture

from build_market_source_verification_manifest import (
    _decimal_value, _expected_change, _expected_value, _identity_matches, _numeric_match,
)

VALUE_FIELDS = {"Price", "Close", "收市", "收盤", "收盤價", "Score"}
CHANGE_FIELDS = {"Change %", "升跌（%）", "漲跌（%）", "變動%", "Band"}
CNN_ENDPOINT = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"


def expected_sources(data: dict) -> dict:
    rows = {}
    for group in ("global_markets", "bonds", "fx", "energy", "metals", "risk"):
        for name, item in (data.get(group) or {}).items():
            rows[(group, name)] = item.get("source") or {}
    for name, source in (data.get("sector_sources") or {}).items():
        rows[("sectors", name)] = source
    return rows


def validate_bundle(data: dict, report_date: str, bundle: dict) -> dict:
    if bundle.get("report_date") != report_date:
        raise ValueError("web observation bundle report_date mismatch")
    trading_date = data.get("trading_date")
    if bundle.get("trading_date") != trading_date:
        raise ValueError("web observation bundle trading_date mismatch")
    captured_text = bundle.get("captured_at_utc")
    if not captured_text:
        raise ValueError("web observation bundle captured_at_utc missing")
    captured = datetime.fromisoformat(captured_text.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    if captured.tzinfo is None:
        raise ValueError("web observation capture timestamp must be timezone-aware")
    age = now - captured.astimezone(timezone.utc)
    # Historical close observations remain valid after capture when report/trading dates and each row are exact.
    # Allow the full report-production day; exact identities, target dates and row values remain mandatory.
    if age < timedelta(minutes=-5) or age > timedelta(hours=24):
        raise ValueError("web observation bundle is stale or future-dated")

    expected = expected_sources(data)
    incoming = bundle.get("observations") or []
    by_key = {(row.get("group"), row.get("name")): row for row in incoming}
    if len(by_key) != 44 or len(incoming) != 44:
        raise ValueError(f"expected 44 unique direct web observations, got {len(by_key)} unique / {len(incoming)} rows")
    if set(by_key) != set(expected):
        raise ValueError("direct web observations do not match exact 44 fixture identities")

    normalized = []
    for key in sorted(expected):
        group, name = key
        source = expected[key]
        raw = dict(by_key[key])
        if raw.get("source_url") != source.get("url"):
            raise ValueError(f"{group}/{name}: source URL does not match fixture primary URL")
        target_date = source.get("data_date")
        if raw.get("target_date") != target_date:
            raise ValueError(f"{group}/{name}: target date mismatch")
        if raw.get("read_status") not in ("SOURCE_NO_DATA", "MARKET_CLOSED", "SOURCE_UPDATE_PENDING") and raw.get("observed_date") != target_date:
            raise ValueError(f"{group}/{name}: observed date mismatch")
        move_tool_failure = group == "risk" and name == "move" and raw.get("read_status") == "TOOL_READ_FAILURE"
        if not move_tool_failure and (raw.get("page_title") is None or not str(raw.get("page_title")).strip()):
            raise ValueError(f"{group}/{name}: page title missing")
        if not move_tool_failure and (not raw.get("instrument_identity") or not _identity_matches(group, name, raw.get("instrument_identity"))):
            raise ValueError(f"{group}/{name}: instrument identity not independently matched")

        method = raw.get("read_method")
        if method in ("CHATGPT_WEB_OPEN_HISTORICAL_PAGE", "CHATGPT_WEB_SEARCH_RESULT_HISTORICAL_PAGE"):
            value_field = raw.get("observed_value_field")
            change_field = raw.get("observed_change_field")
            headers = set(raw.get("observed_headers") or [])
            move_tool_failure = group == "risk" and name == "move" and raw.get("read_status") == "TOOL_READ_FAILURE"
            if not move_tool_failure and (value_field not in VALUE_FIELDS or change_field not in CHANGE_FIELDS):
                raise ValueError(f"{group}/{name}: invalid historical table field mapping")
            if not move_tool_failure and (value_field not in headers or change_field not in headers):
                raise ValueError(f"{group}/{name}: mapped columns are absent from observed headers")
            if not raw.get("web_reader_ref") or not isinstance(raw.get("web_line_start"), int) or not isinstance(raw.get("web_line_end"), int):
                raise ValueError(f"{group}/{name}: direct web reader citation and source line range are required")
            if raw.get("web_line_start") < 0 or raw.get("web_line_end") < raw.get("web_line_start"):
                raise ValueError(f"{group}/{name}: invalid direct web reader source line range")
            row_text = str(raw.get("observed_row_text") or "")
            if group == "risk" and name == "fear_greed":
                if source.get("source_role") not in ("BACKUP_1", "BACKUP", "SECONDARY"):
                    raise ValueError("CNN Fear & Greed web-page fallback is allowed only when fixture pins an explicit backup source")
                if raw.get("read_status") != "PAGE_CONTENT_READ_SUCCESS":
                    raise ValueError("Fear & Greed backup page was not read successfully")
                from datetime import date as _date
                _d = _date.fromisoformat(target_date)
                date_markers = (
                    target_date,
                    _d.strftime("%b %d, %Y"),
                    _d.strftime("%B %d, %Y"),
                    f"{_d.year}年{_d.month}月{_d.day}日",
                    f"{_d.year}/{_d.month}/{_d.day}",
                )
                if not any(marker in row_text for marker in date_markers):
                    raise ValueError("Fear & Greed backup row does not contain the target date")
                if value_field != "Score" or change_field != "Band":
                    raise ValueError("Fear & Greed backup must map Score and Band columns")
            elif raw.get("read_status") == "PAGE_CONTENT_READ_SUCCESS":
                from datetime import date as _date
                _d = _date.fromisoformat(target_date)
                date_markers = (target_date, _d.strftime("%b %d, %Y"), _d.strftime("%B %d, %Y"),
                                f"{_d.year}年{_d.month}月{_d.day}日", f"{_d.year}/{_d.month}/{_d.day}")
                if not any(marker in row_text for marker in date_markers):
                    raise ValueError(f"{group}/{name}: source row text does not contain target date")
            elif raw.get("read_status") in ("SOURCE_NO_DATA", "MARKET_CLOSED", "SOURCE_UPDATE_PENDING", "TOOL_READ_FAILURE"):
                if raw.get("observed_value") is not None or raw.get("observed_change") is not None:
                    raise ValueError(f"{group}/{name}: no-data/closed/update-pending/read-failure row cannot carry numeric observations")
                if raw.get("read_status") != "TOOL_READ_FAILURE" and not row_text.strip():
                    raise ValueError(f"{group}/{name}: no-data/closed/update-pending page evidence text missing")
                if raw.get("read_status") == "MARKET_CLOSED" and not raw.get("closure_evidence_url"):
                    raise ValueError(f"{group}/{name}: market closure requires an official holiday evidence URL")
                if raw.get("read_status") in ("SOURCE_UPDATE_PENDING", "TOOL_READ_FAILURE") and not (group == "risk" and name == "move"):
                    raise ValueError(f"{group}/{name}: MOVE-only pending/read-failure status used on another row")
            else:
                raise ValueError(f"{group}/{name}: unsupported historical page read status {raw.get('read_status')!r}")
            if group == "risk" and name == "move":
                backup_url = "https://www.tradingview.com/symbols/ICE-MOVE/"
                attempt_url = str(raw.get("attempt_url") or "")
                if attempt_url:
                    if attempt_url != backup_url:
                        raise ValueError("MOVE backup attempt_url must be the exact TradingView ICE:MOVE history URL")
                    raw["source_role"] = "BACKUP_1"
                    raw["evidence_source_url"] = backup_url
                    if raw.get("observed_value") is not None and raw.get("observed_change") is not None:
                        observed_at = raw.get("finished_at_tw") or raw.get("finished_at_utc") or captured.isoformat()
                        raw["field_evidence"] = {
                            "close": {"source_type": "TRADINGVIEW_HISTORICAL_PAGE", "source_url": backup_url,
                                      "field_name": raw.get("observed_value_field"), "value": raw.get("observed_value"), "observed_at": observed_at},
                            "change": {"source_type": "TRADINGVIEW_HISTORICAL_PAGE", "source_url": backup_url,
                                       "field_name": raw.get("observed_change_field"), "value": raw.get("observed_change"), "observed_at": observed_at},
                        }
                elif raw.get("read_status") == "SOURCE_UPDATE_PENDING":
                    raw["source_role"] = "PRIMARY_AND_BACKUP_PENDING"
            raw["http_status"] = None
            raw["source_page_fetched"] = raw.get("read_status") != "TOOL_READ_FAILURE"
            raw["provenance"] = (
                "CURRENT_CHATGPT_WEB_SEARCH_RESULT_OBSERVATION"
                if method == "CHATGPT_WEB_SEARCH_RESULT_HISTORICAL_PAGE"
                else "CURRENT_CHATGPT_WEB_OPEN_OBSERVATION"
            )
        elif method == "CNN_OFFICIAL_PREVIOUS_CLOSE":
            if group != "risk" or name != "fear_greed":
                raise ValueError(f"{group}/{name}: CNN JSON method is only valid for Fear & Greed")
            if raw.get("data_endpoint_url") != CNN_ENDPOINT or raw.get("http_status") != 200:
                raise ValueError("CNN official API endpoint evidence missing")
            if raw.get("status") != "VERIFIED":
                raise ValueError("CNN official previous_close observation is not VERIFIED")
            raw["read_status"] = "API_RESPONSE_READ_SUCCESS"
            if not re.fullmatch(r"[0-9a-f]{64}", str(raw.get("raw_response_sha256") or "")):
                raise ValueError("CNN official response SHA-256 missing or malformed")
            if raw.get("observed_value_field") != "fear_and_greed.previous_close":
                raise ValueError("CNN previous_close field mapping mismatch")
            if raw.get("observed_change_field") != "derived_from_fear_and_greed.previous_close_using_cnn_bands":
                raise ValueError("CNN previous_close band mapping mismatch")
            if raw.get("previous_close_target_date") != target_date:
                raise ValueError("CNN previous_close target session date mismatch")
            headline_timestamp = raw.get("source_timestamp_utc")
            if not headline_timestamp or datetime.fromisoformat(headline_timestamp.replace("Z", "+00:00")).date().isoformat() <= target_date:
                raise ValueError("CNN previous_close timestamp does not post-date target session")
            raw["source_page_fetched"] = True
            raw["provenance"] = "CURRENT_CNN_OFFICIAL_API_OBSERVATION"
        else:
            raise ValueError(f"{group}/{name}: unsupported read method {method!r}")

        is_fear_greed = group == "risk" and name == "fear_greed"
        is_cnn_official = method == "CNN_OFFICIAL_PREVIOUS_CLOSE"
        is_fear_greed_backup = is_fear_greed and method == "CHATGPT_WEB_OPEN_HISTORICAL_PAGE"
        expected_value = source.get("score_value") if is_fear_greed else _expected_value(source)
        if is_fear_greed:
            # CNN official previous_close is raw decimal precision; FGScore backup
            # publishes a rounded integer. Keep the expected raw values separate.
            expected_raw_value = (
                source.get("source_score_value")
                if is_cnn_official
                else source.get("backup_source_score_value", source.get("score_value"))
            )
        else:
            expected_raw_value = expected_value
        expected_change = _expected_change(source)
        value_match = (
            raw.get("observed_value") is not None
            and (expected_value is None or _numeric_match(
                raw.get("observed_value"), expected_value, rounded_integer=is_fear_greed
            ))
        )
        raw_score_match = (
            raw.get("observed_value") is not None
            and (expected_raw_value is None or _numeric_match(raw.get("observed_value"), expected_raw_value))
        ) if is_fear_greed else True
        if is_fear_greed:
            change_match = (
                bool(str(raw.get("observed_change") or "").strip())
                and (expected_change is None or
                     str(raw.get("observed_change") or "").strip().casefold() == str(expected_change or "").strip().casefold())
            )
        else:
            change_match = (
                raw.get("observed_change") is not None
                and (expected_change is None or _numeric_match(raw.get("observed_change"), expected_change))
            )
        raw["preexisting_value_comparison"] = (
            "NOT_PERFORMED_BLANK_INPUT" if expected_value is None else "COMPARED_TO_EXISTING_FIXTURE"
        )
        if raw.get("read_status") in ("SOURCE_NO_DATA", "MARKET_CLOSED", "SOURCE_UPDATE_PENDING"):
            value_match = False
            raw_score_match = False
            change_match = False
        raw["expected_display_value"] = expected_value
        raw["expected_source_raw_value"] = expected_raw_value if is_fear_greed else None
        raw["raw_source_value_match"] = raw_score_match
        raw["expected_change_display"] = expected_change
        raw["instrument_identity_status"] = "NOT_INDEPENDENTLY_VERIFIED" if raw.get("read_status") == "TOOL_READ_FAILURE" else "VERIFIED"
        raw["field_mapping_status"] = "PENDING_FIELD_HEADER_MAPPING" if raw.get("read_status") == "TOOL_READ_FAILURE" else "VERIFIED"
        raw["display_value_match"] = value_match
        raw["display_change_match"] = change_match
        raw["status"] = "VERIFIED" if value_match and raw_score_match and change_match else "OBSERVED_PENDING_VALIDATION"
        if not raw.get("finished_at_utc"):
            raw["finished_at_utc"] = captured.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        if not raw.get("finished_at_tw"):
            raw["finished_at_tw"] = captured.astimezone(timezone(timedelta(hours=8))).isoformat()
        raw["capture_session"] = bundle.get("capture_session", "TAC-CHATGPT-WEB-READ")
        raw["prior_observation_reused"] = False
        raw["attempt_count"] = 1
        raw["verification_round"] = 1
        canonical = json.dumps(
            {k: v for k, v in raw.items() if k != "observation_record_sha256"},
            ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")
        raw["observation_record_sha256"] = hashlib.sha256(canonical).hexdigest()
        normalized.append(raw)

    counts = {}
    for row in normalized:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    verified = sum(1 for row in normalized if row["status"] == "VERIFIED")
    return {
        "schema_version": "1.0",
        "report_date": report_date,
        "trading_date": trading_date,
        "capture_method": "CHATGPT_DIRECT_WEB_PAGE_READ",
        "capture_session": bundle.get("capture_session", "TAC-CHATGPT-WEB-READ"),
        "captured_at_utc": captured.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status_counts": counts,
        "verified_count": verified,
        "source_pages_fetched": all(row.get("source_page_fetched") is True for row in normalized),
        "displayed_values_independently_reconciled": verified == 44,
        "prior_observation_reused_count": 0,
        "observations": normalized,
    }



def merge_move_backup_observation(result: dict, fallback: dict, primary_read_status: str) -> dict:
    """Replace only MOVE with a separately captured TradingView backup observation."""
    if (fallback.get("group"), fallback.get("name")) != ("risk", "move"):
        raise ValueError("targeted backup capture did not return the MOVE row")
    backup_url = "https://www.tradingview.com/symbols/ICE-MOVE/"
    if fallback.get("evidence_source_url") != backup_url:
        raise ValueError("MOVE backup evidence URL is not the pinned TradingView history page")
    if fallback.get("status") == "VERIFIED":
        fallback["source_role"] = "BACKUP_1"
        fallback["read_status"] = "PAGE_CONTENT_READ_SUCCESS"
        fallback["provenance"] = "CURRENT_RUN_BROWSER_OBSERVATION"
    elif fallback.get("status") in ("TARGET_DATE_NOT_FOUND", "SOURCE_UPDATE_PENDING"):
        fallback.update({"status": "SOURCE_UPDATE_PENDING", "read_status": "SOURCE_UPDATE_PENDING",
                         "observed_date": None, "observed_value": None, "observed_change": None,
                         "observed_value_field": None, "observed_change_field": None})
    elif fallback.get("status") == "TOOL_READ_FAILURE":
        if primary_read_status == "SOURCE_NO_DATA":
            fallback.update({"status": "SOURCE_UPDATE_PENDING", "read_status": "SOURCE_UPDATE_PENDING",
                             "observed_date": None, "observed_value": None, "observed_change": None,
                             "observed_value_field": None, "observed_change_field": None,
                             "error": "INVESTING_HISTORY_ROW_ABSENT; TRADINGVIEW_BACKUP_READ_FAILED"})
        else:
            fallback["read_status"] = "TOOL_READ_FAILURE"
    else:
        raise ValueError(f"unsupported MOVE backup status: {fallback.get('status')!r}")
    canonical = json.dumps(
        {key: value for key, value in fallback.items() if key != "observation_record_sha256"},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    fallback["observation_record_sha256"] = hashlib.sha256(canonical).hexdigest()
    rows = result.get("observations") or []
    replaced = False
    for index, row in enumerate(rows):
        if (row.get("group"), row.get("name")) == ("risk", "move"):
            rows[index] = fallback
            replaced = True
            break
    if not replaced:
        raise ValueError("normalized 44-row bundle is missing MOVE")
    counts = {}
    for row in rows:
        counts[row.get("status", "UNKNOWN")] = counts.get(row.get("status", "UNKNOWN"), 0) + 1
    result["observations"] = rows
    result["row_count"] = len(rows)
    result["status_counts"] = counts
    result["verified_count"] = sum(1 for row in rows if row.get("status") == "VERIFIED")
    result["displayed_values_independently_reconciled"] = result["verified_count"] == 44
    result["source_pages_fetched"] = all(row.get("source_page_fetched") is True for row in rows)
    result["move_backup_attempted"] = True
    result["move_backup_status"] = fallback.get("status")
    return result

def maybe_capture_move_backup(data_path: Path, report_date: str, bundle: dict, result: dict) -> dict:
    """If the primary MOVE web row is missing, read only TradingView ICE:MOVE once."""
    raw_move = next((row for row in (bundle.get("observations") or [])
                     if row.get("group") == "risk" and row.get("name") == "move"), None)
    if not raw_move or raw_move.get("read_status") not in ("SOURCE_NO_DATA", "TOOL_READ_FAILURE"):
        return result
    primary_status = raw_move.get("read_status")
    browser_script = Path(__file__).with_name("browser_verify_market_history.py")
    with tempfile.TemporaryDirectory(prefix="tac-move-backup-") as tmp:
        output = Path(tmp) / "move-backup-observation.json"
        command = [sys.executable, str(browser_script), "--fixture", str(data_path),
                   "--report-date", report_date, "--output", str(output),
                   "--timeout-ms", "12000", "--concurrency", "1",
                   "--no-fixture-write", "--only", "risk:move", "--move-backup-only"]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
            payload = json.loads(output.read_text(encoding="utf-8"))
            rows = payload.get("observations") or []
            if len(rows) != 1:
                raise ValueError("targeted TradingView backup did not return exactly one row")
            primary_normalized = dict(next(row for row in result["observations"] if row.get("group") == "risk" and row.get("name") == "move"))
            merged = merge_move_backup_observation(result, rows[0], primary_status)
            move_row = next(row for row in merged["observations"] if row.get("group") == "risk" and row.get("name") == "move")
            primary_attempt_status = "TARGET_DATE_NOT_FOUND" if primary_status == "SOURCE_NO_DATA" else primary_status
            primary_attempt_read_status = "SOURCE_UPDATE_PENDING" if primary_status == "SOURCE_NO_DATA" else primary_status
            primary_attempt = {
                "round": 1, "source_role": "PRIMARY", "request_url": raw_move.get("source_url"),
                "status": primary_attempt_status, "read_status": primary_attempt_read_status,
                "http_status": primary_normalized.get("http_status"), "page_title": primary_normalized.get("page_title"),
                "final_url": primary_normalized.get("final_url"), "instrument_identity": primary_normalized.get("instrument_identity"),
                "observed_row_text": primary_normalized.get("observed_row_text"),
                "page_body_excerpt": primary_normalized.get("page_body_excerpt"), "error": primary_normalized.get("error"),
                "started_at_utc": primary_normalized.get("started_at_utc"), "finished_at_utc": primary_normalized.get("finished_at_utc"),
            }
            backup_attempts = move_row.get("attempt_history") or [{
                "round": 2, "source_role": "BACKUP_1",
                "request_url": "https://www.tradingview.com/symbols/ICE-MOVE/",
                "status": move_row.get("status"), "read_status": move_row.get("read_status"),
                "page_title": move_row.get("page_title"), "instrument_identity": move_row.get("instrument_identity"),
                "error": move_row.get("error"),
            }]
            for attempt in backup_attempts:
                attempt["round"] = 2
            move_row["attempt_history"] = [primary_attempt] + backup_attempts
            move_row["attempt_count"] = len(move_row["attempt_history"])
            move_row["verification_round"] = 2
            canonical = json.dumps({key: value for key, value in move_row.items() if key != "observation_record_sha256"},
                                   ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            move_row["observation_record_sha256"] = hashlib.sha256(canonical).hexdigest()
            return merged
        except Exception as exc:
            fallback = {
                "group": "risk", "name": "move", "source_url": raw_move.get("source_url"),
                "target_date": raw_move.get("target_date"), "status": "TOOL_READ_FAILURE",
                "read_status": "TOOL_READ_FAILURE", "source_role": "BACKUP_1",
                "evidence_source_url": "https://www.tradingview.com/symbols/ICE-MOVE/",
                "error": f"TRADINGVIEW_MOVE_BACKUP_EXCEPTION: {type(exc).__name__}: {exc}",
            }
            return merge_move_backup_observation(result, fallback, primary_status)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--report-date", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--cnn-observation", required=True,
                        help="Fresh single-row Playwright capture of CNN official graphdata response")
    parser.add_argument("--output", required=True)
    parser.add_argument("--no-fixture-write", action="store_true",
                        help="Emit observations without writing populated values back to the input fixture")
    args = parser.parse_args()
    data_path=Path(args.data)
    original_data = json.loads(data_path.read_text(encoding="utf-8"))
    screenshot_sidecar=Path(f"simulation-lab/input/market-screenshot-observations-{args.report_date}.json")
    if screenshot_sidecar.is_file():
        # Screenshot inputs outrank any previously assembled direct-web bundle.
        # Delegate to the single screenshot-first browser reader, which fills only missing fields.
        browser_script=Path(__file__).with_name("browser_verify_market_history.py")
        command=[sys.executable,str(browser_script),"--fixture",str(data_path),
            "--report-date",args.report_date,"--output",args.output,
            "--timeout-ms","15000","--concurrency","2"]
        if args.no_fixture_write: command.append("--no-fixture-write")
        subprocess.run(command,check=True)
        return
    data=blank_fixture(original_data,apply_screenshots=False)
    bundle = json.loads(Path(args.input).read_text(encoding="utf-8"))
    cnn_capture = json.loads(Path(args.cnn_observation).read_text(encoding="utf-8"))
    cnn_rows = [row for row in (cnn_capture.get("observations") or [])
                if row.get("group") == "risk" and row.get("name") == "fear_greed"]
    if len(cnn_rows) > 1:
        raise ValueError(f"CNN capture must contain at most one risk/fear_greed row, got {len(cnn_rows)}")
    # Prefer a verified official CNN previous_close record. If CNN's endpoint
    # cannot map that field, retain the explicitly pinned FGScore backup web row.
    if cnn_rows and cnn_rows[0].get("status") == "VERIFIED":
        bundle["observations"] = [
            row for row in (bundle.get("observations") or [])
            if not (row.get("group") == "risk" and row.get("name") == "fear_greed")
        ] + [cnn_rows[0]]
    result = validate_bundle(data, args.report_date, bundle)
    result = maybe_capture_move_backup(data_path, args.report_date, bundle, result)
    result["row_count"]=len(result["observations"])
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result["bundle_sha256"]=hashlib.sha256(output.read_bytes()).hexdigest()
    summary={
        "output": str(output),
        "row_count": len(result["observations"]),
        "verified_count": result["verified_count"],
        "status_counts": result["status_counts"],
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "preexisting_market_values_used": False,
    }
    if not args.no_fixture_write:
        populated=populate_fixture(data,result)
        data_path.write_text(json.dumps(populated,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        summary.update({"fixture_output":str(data_path),
            "pending_count":populated["stage2_market_bootstrap"]["pending_count"]})
    print(json.dumps(summary,ensure_ascii=False))


if __name__ == "__main__":
    main()
