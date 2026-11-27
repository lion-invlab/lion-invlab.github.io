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

VALUE_FIELDS = {"Price", "Close", "收市", "收盤", "收盤價", "Score", "Current Score"}
CHANGE_FIELDS = {"Change %", "升跌（%）", "漲跌（%）", "變動%", "Band", "Current Band"}


def expected_sources(data: dict) -> dict:
    rows = {}
    for group in ("global_markets", "bonds", "fx", "energy", "metals", "risk"):
        for name, item in (data.get(group) or {}).items():
            rows[(group, name)] = item.get("source") or {}
    for name, source in (data.get("sector_sources") or {}).items():
        rows[("sectors", name)] = source
    return rows


def persist_fixture(path: Path, data: dict, *, no_fixture_write: bool = False) -> bool:
    """Persist the working Fixture only for production runs, never diagnostic runs."""
    if no_fixture_write:
        return False
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
    return True


def _apply_screenshot_fields(row: dict, observation: dict, screenshot: dict) -> dict:
    """Overlay user screenshot fields; page reads may fill only fields absent from the screenshot."""
    if not screenshot:
        return observation
    fields = screenshot["fields"]
    group, name = row["group"], row["name"]
    observation["group"] = group
    observation["name"] = name
    is_fg = group == "risk" and name == "fear_greed"
    value_key, change_key = ("score", "band") if is_fg else ("close", "change")
    identity = screenshot.get("instrument_identity")
    identity_ok = _identity_matches(group, name, identity)
    required = (value_key, change_key)
    screenshot_only = all(key in fields for key in required)
    source_url = screenshot.get("source_url")
    approved_primary = set(row.get("approved_primary_urls") or [])
    approved_backup = set(row.get("approved_backup_urls") or [])
    if source_url == row.get("source_url") or source_url in approved_primary:
        screenshot_role = "PRIMARY"
    elif source_url in approved_backup:
        screenshot_role = "BACKUP_1" if "fgscore" in str(source_url).lower() else "BACKUP_2"
    else:
        raise ValueError(f"{group}/{name}: screenshot URL is not approved")

    screenshot_evidence = {}
    for key, item in fields.items():
        screenshot_evidence[key] = {
            "source_type": "USER_PROVIDED_SCREENSHOT",
            "source_url": source_url,
            "evidence_path": item["evidence_path"],
            "evidence_sha256": item["evidence_sha256"],
            "captured_at": item["captured_at"],
            "quote_timestamp": item.get("quote_timestamp"),
            "field_name": item["field_name"],
            "value": item["value"],
            "instrument_identity": identity,
            "observed_date": screenshot.get("data_date"),
        }

    expected_value = row.get("expected_value")
    expected_change = row.get("expected_change")
    if screenshot_only:
        value = fields[value_key]["value"]
        change = fields[change_key]["value"]
        value_match = expected_value is None or _numeric_match(value, expected_value, rounded_integer=is_fg)
        change_match = (
            (not expected_change or str(change).strip().casefold() == str(expected_change).strip().casefold())
            if is_fg else
            (expected_change is None or _numeric_match(change, expected_change))
        )
        observation.update({
            "status": "VERIFIED" if identity_ok and value_match and change_match else "OBSERVED_PENDING_FIELD_MAPPING",
            "source_url": source_url,
            "evidence_source_url": source_url,
            "source_role": screenshot_role,
            "target_date": row.get("target_date") or observation.get("target_date"),
            "observed_date": screenshot.get("data_date"),
            "page_title": "User-provided screenshot from approved source",
            "instrument_identity": identity,
            "instrument_identity_status": "VERIFIED" if identity_ok else "NOT_INDEPENDENTLY_VERIFIED",
            "screenshot_instrument_identity_status": "VERIFIED" if identity_ok else "NOT_INDEPENDENTLY_VERIFIED",
            "field_mapping_status": "VERIFIED",
            "observed_value": value,
            "observed_change": change,
            "observed_value_field": fields[value_key]["field_name"],
            "observed_change_field": fields[change_key]["field_name"],
            "observed_value_key": value_key,
            "observed_change_key": change_key,
            "observed_headers": [fields[key]["field_name"] for key in fields],
            "observed_row_text": f'{screenshot.get("data_date")} | ' + " | ".join(
                f'{item["field_name"]}: {item["value"]}' for item in fields.values()
            ),
            "display_value_match": value_match,
            "display_change_match": change_match,
            "read_method": "USER_PROVIDED_SCREENSHOT",
            "provenance": "CURRENT_USER_PROVIDED_SCREENSHOT",
            "read_status": "USER_PROVIDED_SCREENSHOT_CONFIRMED",
            "source_page_fetched": False,
            "http_status": None,
            "web_reader_ref": None,
            "web_line_start": None,
            "web_line_end": None,
            "field_evidence": screenshot_evidence,
            "screenshot_evidence_path": screenshot.get("evidence_path"),
            "screenshot_evidence_sha256": screenshot.get("evidence_sha256"),
            "finished_at_utc": screenshot.get("captured_at"),
            "finished_at_tw": screenshot.get("captured_at"),
        })
        return observation

    missing_value = value_key not in fields
    missing_change = change_key not in fields
    page_ok = (
        identity_ok
        and observation.get("source_page_fetched") is True
        and observation.get("instrument_identity_status") == "VERIFIED"
        and observation.get("field_mapping_status") == "VERIFIED"
        and (not missing_value or observation.get("observed_value") is not None)
        and (not missing_change or observation.get("observed_change") is not None)
    )
    if not page_ok:
        observation.update({
            "source_url": source_url,
            "evidence_source_url": source_url,
            "source_role": screenshot_role,
            "target_date": row.get("target_date") or observation.get("target_date"),
            "observed_date": screenshot.get("data_date"),
            "instrument_identity": identity,
            "instrument_identity_status": "VERIFIED" if identity_ok else "NOT_INDEPENDENTLY_VERIFIED",
            "screenshot_instrument_identity_status": "VERIFIED" if identity_ok else "NOT_INDEPENDENTLY_VERIFIED",
            "field_mapping_status": "PENDING_FIELD_HEADER_MAPPING",
            "read_method": "MIXED_SCREENSHOT_AND_HISTORICAL_PAGE",
            "provenance": "CURRENT_RUN_MIXED_FIELD_OBSERVATION",
            "read_status": "MIXED_FIELD_OBSERVATIONS_PENDING",
            "source_page_fetched": False,
            "field_evidence": screenshot_evidence,
            "status": "OBSERVED_PENDING_FIELD_MAPPING",
        })
        return observation

    page_value = observation.get("observed_value")
    page_change = observation.get("observed_change")
    page_url = observation.get("evidence_source_url") or observation.get("source_url")
    if is_fg:
        page_source_type = (
            "CNN_OFFICIAL_CURRENT_DASHBOARD"
            if observation.get("read_method") == "CNN_OFFICIAL_CURRENT_DASHBOARD"
            else "FGSCORE_HISTORICAL_PAGE"
        )
    else:
        page_source_type = "INVESTING_HISTORICAL_PAGE"

    evidence = dict(screenshot_evidence)
    if value_key in fields:
        observation["observed_value"] = fields[value_key]["value"]
        observation["observed_value_field"] = fields[value_key]["field_name"]
        observation["display_value_match"] = (
            expected_value is None or _numeric_match(fields[value_key]["value"], expected_value, rounded_integer=is_fg)
        )
    else:
        evidence[value_key] = {
            "source_type": page_source_type, "source_url": page_url,
            "page_title": observation.get("page_title"),
            "instrument_identity": observation.get("instrument_identity"),
            "observed_date": observation.get("observed_date"),
            "web_reader_ref": observation.get("web_reader_ref"),
            "web_line_start": observation.get("web_line_start"),
            "web_line_end": observation.get("web_line_end"),
            "field_name": observation.get("observed_value_field"),
            "value": page_value, "observed_at": observation.get("finished_at_tw") or observation.get("finished_at_utc"),
        }
        observation["display_value_match"] = (
            expected_value is None or _numeric_match(page_value, expected_value, rounded_integer=is_fg)
        )
    if change_key in fields:
        observation["observed_change"] = fields[change_key]["value"]
        observation["observed_change_field"] = fields[change_key]["field_name"]
        observation["display_change_match"] = (
            (not expected_change or str(fields[change_key]["value"]).strip().casefold() == str(expected_change).strip().casefold())
            if is_fg else
            (expected_change is None or _numeric_match(fields[change_key]["value"], expected_change))
        )
    else:
        evidence[change_key] = {
            "source_type": page_source_type, "source_url": page_url,
            "page_title": observation.get("page_title"),
            "instrument_identity": observation.get("instrument_identity"),
            "observed_date": observation.get("observed_date"),
            "web_reader_ref": observation.get("web_reader_ref"),
            "web_line_start": observation.get("web_line_start"),
            "web_line_end": observation.get("web_line_end"),
            "field_name": observation.get("observed_change_field"),
            "value": page_change, "observed_at": observation.get("finished_at_tw") or observation.get("finished_at_utc"),
        }
        observation["display_change_match"] = (
            (not expected_change or str(page_change).strip().casefold() == str(expected_change).strip().casefold())
            if is_fg else
            (expected_change is None or _numeric_match(page_change, expected_change))
        )
    observation.update({
        "observed_value_key": value_key,
        "observed_change_key": change_key,
        "screenshot_instrument_identity_status": "VERIFIED" if identity_ok else "NOT_INDEPENDENTLY_VERIFIED",
        "read_method": "MIXED_SCREENSHOT_AND_HISTORICAL_PAGE",
        "provenance": "CURRENT_RUN_MIXED_FIELD_OBSERVATION",
        "read_status": "MIXED_FIELD_OBSERVATIONS_CONFIRMED",
        "source_page_fetched": True,
        "field_evidence": evidence,
    })
    observation["status"] = (
        "VERIFIED"
        if observation.get("instrument_identity_status") == "VERIFIED"
        and identity_ok
        and observation.get("field_mapping_status") == "VERIFIED"
        and observation.get("display_value_match") is True
        and observation.get("display_change_match") is True
        else "OBSERVED_PENDING_FIELD_MAPPING"
    )
    return observation


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
        method = raw.get("read_method")
        approved_urls={source.get("url"),*(source.get("approved_primary_urls") or []),*(source.get("approved_backup_urls") or [])}
        if raw.get("source_url") not in approved_urls:
            raise ValueError(f"{group}/{name}: source URL is not in the approved primary/backup list")
        if group=="risk" and name=="fear_greed":
            if method=="CNN_OFFICIAL_CURRENT_DASHBOARD" and raw.get("source_url") not in (source.get("approved_primary_urls") or []):
                raise ValueError("CNN current dashboard must use an approved CNN official URL")
            if method=="CHATGPT_WEB_OPEN_HISTORICAL_PAGE" and raw.get("source_url") not in (source.get("approved_backup_urls") or []):
                raise ValueError("Fear & Greed historical-page fallback must use an approved provider backup URL")
            if method=="CHATGPT_WEB_OPEN_HISTORICAL_PAGE":
                raw["source_role"]="BACKUP_1" if "fgscore.com" in raw.get("source_url","") else "BACKUP_2"
                raw["evidence_source_url"]=raw.get("source_url")
            elif method=="CNN_OFFICIAL_CURRENT_DASHBOARD":
                raw["source_role"]="PRIMARY"
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

        if method == "CHATGPT_WEB_OPEN_HISTORICAL_PAGE":
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
            raw["provenance"] = "CURRENT_CHATGPT_WEB_OPEN_OBSERVATION"
        elif method == "CNN_OFFICIAL_CURRENT_DASHBOARD":
            if group != "risk" or name != "fear_greed":
                raise ValueError(f"{group}/{name}: CNN dashboard method is only valid for Fear & Greed")
            if raw.get("source_url") not in (source.get("approved_primary_urls") or []):
                raise ValueError("CNN current dashboard URL is not in the approved official URL list")
            if raw.get("read_status") != "PAGE_CONTENT_READ_SUCCESS":
                raise ValueError("CNN current dashboard page was not read successfully")
            if raw.get("observed_value_field") != "Current Score" or raw.get("observed_change_field") != "Current Band":
                raise ValueError("CNN current dashboard must map Current Score and Current Band")
            headers=set(raw.get("observed_headers") or [])
            if not {"Current Score","Current Band"}.issubset(headers):
                raise ValueError("CNN current dashboard field headers are missing")
            if not raw.get("web_reader_ref") or not isinstance(raw.get("web_line_start"),int) or not isinstance(raw.get("web_line_end"),int):
                raise ValueError("CNN current dashboard requires direct web reader citation and line range")
            if raw.get("web_line_start")<0 or raw.get("web_line_end")<raw.get("web_line_start"):
                raise ValueError("CNN current dashboard web line range is invalid")
            try:
                score=float(raw.get("observed_value"))
            except (TypeError,ValueError):
                raise ValueError("CNN current dashboard score must be numeric")
            if not 0<=score<=100:
                raise ValueError("CNN current dashboard score must be between 0 and 100")
            valid_bands={"Extreme Fear","Fear","Neutral","Greed","Extreme Greed"}
            if str(raw.get("observed_change") or "") not in valid_bands:
                raise ValueError("CNN current dashboard sentiment band is invalid")
            if not raw.get("source_timestamp_utc"):
                raise ValueError("CNN current dashboard Last updated timestamp is required")
            timestamp=datetime.fromisoformat(raw["source_timestamp_utc"].replace("Z","+00:00"))
            if timestamp.tzinfo is None or timestamp.astimezone(timezone.utc)>captured.astimezone(timezone.utc)+timedelta(minutes=5):
                raise ValueError("CNN current dashboard Last updated timestamp is invalid")
            row_text=str(raw.get("observed_row_text") or "")
            if target_date not in row_text and timestamp.astimezone(timezone.utc).date().isoformat()!=target_date:
                raise ValueError("CNN current dashboard does not match the target trading date")
            raw["source_role"]="PRIMARY"
            raw["read_status"]="PAGE_CONTENT_READ_SUCCESS"
            raw["source_page_fetched"]=True
            raw["provenance"]="CURRENT_CNN_OFFICIAL_DASHBOARD_OBSERVATION"
        else:
            raise ValueError(f"{group}/{name}: unsupported read method {method!r}")

        is_fear_greed = group == "risk" and name == "fear_greed"
        is_cnn_official = method == "CNN_OFFICIAL_CURRENT_DASHBOARD"
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
        # Direct ChatGPT page observations must carry field-level provenance into
        # the Run's normalized bundle. The pre-build gate verifies these exact
        # fields; page title/row text alone is not a sufficient handoff.
        if raw["status"] == "VERIFIED" and method in (
            "CHATGPT_WEB_OPEN_HISTORICAL_PAGE", "CNN_OFFICIAL_CURRENT_DASHBOARD"
        ):
            field_evidence = dict(raw.get("field_evidence") or {})
            if method == "CNN_OFFICIAL_CURRENT_DASHBOARD":
                evidence_source_type = "CNN_OFFICIAL_CURRENT_DASHBOARD"
            elif group == "risk" and name == "fear_greed" and "fgscore" in str(raw.get("source_url") or "").lower():
                evidence_source_type = "FGSCORE_CURRENT_DASHBOARD"
            else:
                evidence_source_type = "INVESTING_HISTORICAL_PAGE"
            value_key = "score" if is_fear_greed else "close"
            change_key = "band" if is_fear_greed else "change"
            evidence_base = {
                "source_type": evidence_source_type,
                "source_url": raw.get("source_url"),
                "page_title": raw.get("page_title"),
                "instrument_identity": raw.get("instrument_identity"),
                "observed_date": raw.get("observed_date"),
                "web_reader_ref": raw.get("web_reader_ref"),
                "web_line_start": raw.get("web_line_start"),
                "web_line_end": raw.get("web_line_end"),
                "captured_at_utc": raw.get("captured_at_utc") or bundle.get("captured_at_utc"),
                "observed_row_text": raw.get("observed_row_text"),
            }
            for field_key, field_value, field_name in (
                (value_key, raw.get("observed_value"), raw.get("observed_value_field")),
                (change_key, raw.get("observed_change"), raw.get("observed_change_field")),
            ):
                if field_key not in field_evidence:
                    field_evidence[field_key] = {
                        **evidence_base, "field_name": field_name, "value": field_value
                    }
            raw["field_evidence"] = field_evidence
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
                        help="Direct CNN official current-dashboard page observation; previous_close is not accepted")
    parser.add_argument("--output", required=True)
    parser.add_argument("--no-fixture-write", action="store_true",
                        help="Emit observations without writing populated values back to the input fixture")
    args = parser.parse_args()
    data_path=Path(args.data)
    original_data = json.loads(data_path.read_text(encoding="utf-8"))
    # Evidence must be supplied inside the Run-scoped packet; no date-global
    # screenshot sidecar may trigger browser automation or override this input.
    data=blank_fixture(original_data,apply_screenshots=False)
    bundle = json.loads(Path(args.input).read_text(encoding="utf-8"))
    cnn_capture = json.loads(Path(args.cnn_observation).read_text(encoding="utf-8"))
    cnn_rows = [row for row in (cnn_capture.get("observations") or [])
                if row.get("group") == "risk" and row.get("name") == "fear_greed"]
    if len(cnn_rows) > 1:
        raise ValueError(f"CNN capture must contain at most one risk/fear_greed row, got {len(cnn_rows)}")
    # Prefer a verified CNN current-dashboard observation. If the official
    # dashboard is unavailable, retain the explicitly approved provider backup row.
    if cnn_rows and cnn_rows[0].get("read_method") == "CNN_OFFICIAL_CURRENT_DASHBOARD" and cnn_rows[0].get("read_status") == "PAGE_CONTENT_READ_SUCCESS":
        bundle["observations"] = [
            row for row in (bundle.get("observations") or [])
            if not (row.get("group") == "risk" and row.get("name") == "fear_greed")
        ] + [cnn_rows[0]]
    result = validate_bundle(data, args.report_date, bundle)
    # MOVE remains the pinned Investing.com observation. If its row is absent
    # or pending, preserve that status; never substitute TradingView.
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
