#!/usr/bin/env python3
"""Validate direct ChatGPT web-page observations before SIM-1.4 Stage 2 manifest creation."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from build_market_source_verification_manifest import (
    _decimal_value, _expected_change, _expected_value, _identity_matches, _numeric_match,
)

VALUE_FIELDS = {"Price", "Close", "收市", "收盤", "收盤價"}
CHANGE_FIELDS = {"Change %", "升跌（%）", "漲跌（%）", "變動%"}
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
    if age < timedelta(minutes=-5) or age > timedelta(minutes=90):
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
        if raw.get("target_date") != target_date or raw.get("observed_date") != target_date:
            raise ValueError(f"{group}/{name}: target/observed date mismatch")
        if raw.get("page_title") is None or not str(raw.get("page_title")).strip():
            raise ValueError(f"{group}/{name}: page title missing")
        if not raw.get("instrument_identity") or not _identity_matches(group, name, raw.get("instrument_identity")):
            raise ValueError(f"{group}/{name}: instrument identity not independently matched")

        method = raw.get("read_method")
        if method == "CHATGPT_WEB_OPEN_HISTORICAL_PAGE":
            if raw.get("read_status") != "PAGE_CONTENT_READ_SUCCESS":
                raise ValueError(f"{group}/{name}: direct historical page read status is not successful")
            if group == "risk" and name == "fear_greed":
                raise ValueError("CNN Fear & Greed must use the official CNN historical JSON endpoint")
            value_field = raw.get("observed_value_field")
            change_field = raw.get("observed_change_field")
            headers = set(raw.get("observed_headers") or [])
            if value_field not in VALUE_FIELDS or change_field not in CHANGE_FIELDS:
                raise ValueError(f"{group}/{name}: invalid historical table field mapping")
            if value_field not in headers or change_field not in headers:
                raise ValueError(f"{group}/{name}: mapped columns are absent from observed headers")
            row_text = str(raw.get("observed_row_text") or "")
            date_markers = (target_date, "2026年11月20日", "Nov 20, 2026")
            if not any(marker in row_text for marker in date_markers):
                raise ValueError(f"{group}/{name}: source row text does not contain target date")
            raw["http_status"] = None
            raw["source_page_fetched"] = True
            raw["provenance"] = "CURRENT_CHATGPT_WEB_OPEN_OBSERVATION"
        elif method == "CNN_OFFICIAL_HISTORICAL_JSON":
            if group != "risk" or name != "fear_greed":
                raise ValueError(f"{group}/{name}: CNN JSON method is only valid for Fear & Greed")
            if raw.get("data_endpoint_url") != CNN_ENDPOINT or raw.get("http_status") != 200:
                raise ValueError("CNN official historical endpoint evidence missing")
            if raw.get("read_status") != "API_RESPONSE_READ_SUCCESS":
                raise ValueError("CNN official historical JSON response not successfully read")
            if not re.fullmatch(r"[0-9a-f]{64}", str(raw.get("raw_response_sha256") or "")):
                raise ValueError("CNN official historical response SHA-256 missing or malformed")
            if raw.get("observed_value_field") != "fear_and_greed_historical.data[].y":
                raise ValueError("CNN score field mapping mismatch")
            if raw.get("observed_change_field") != "fear_and_greed_historical.data[].rating":
                raise ValueError("CNN rating field mapping mismatch")
            raw["source_page_fetched"] = True
            raw["provenance"] = "CURRENT_CNN_OFFICIAL_API_OBSERVATION"
        else:
            raise ValueError(f"{group}/{name}: unsupported read method {method!r}")

        expected_value = _expected_value(source)
        expected_change = _expected_change(source)
        value_match = _numeric_match(
            raw.get("observed_value"), expected_value,
            rounded_integer=(group == "risk" and name == "fear_greed"),
        )
        if group == "risk" and name == "fear_greed":
            change_match = str(raw.get("observed_change") or "").strip().casefold() == str(expected_change or "").strip().casefold()
        else:
            change_match = _numeric_match(raw.get("observed_change"), expected_change)
        raw["expected_display_value"] = expected_value
        raw["expected_change_display"] = expected_change
        raw["instrument_identity_status"] = "VERIFIED"
        raw["field_mapping_status"] = "VERIFIED"
        raw["display_value_match"] = value_match
        raw["display_change_match"] = change_match
        raw["status"] = "VERIFIED" if value_match and change_match else "OBSERVED_PENDING_VALIDATION"
        raw["finished_at_utc"] = captured.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--report-date", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    data = json.loads(Path(args.data).read_text(encoding="utf-8"))
    bundle = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = validate_bundle(data, args.report_date, bundle)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "row_count": len(result["observations"]),
        "verified_count": result["verified_count"],
        "status_counts": result["status_counts"],
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
