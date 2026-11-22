#!/usr/bin/env python3
"""Build an explicit 44-row source-verification worklist from the report fixture.

This is a tracking manifest only. It does not fetch source pages or claim that
displayed values have been independently reconciled.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from validate_market_snapshot import validate_market_snapshot

BOND_PRIMARY_URLS = {
    "2年期美債殖利率": "https://www.investing.com/rates-bonds/u.s.-2-year-bond-yield-historical-data",
    "10年期美債殖利率": "https://www.investing.com/rates-bonds/u.s.-10-year-bond-yield-historical-data",
    "30年期美債殖利率": "https://www.investing.com/rates-bonds/u.s.-30-year-bond-yield-historical-data",
}


def verification_fields(source: dict, display, change_display) -> dict:
    """Carry forward only source observations already reconciled against fixture values."""
    evidence_method = source.get("evidence_method")
    source_status = source.get("verification_status")
    source_url = source.get("url")
    data_date = source.get("data_date")
    observed_at = source.get("verified_at_tw") or source.get("read_at_taipei") or source.get("read_at")
    verified = (
        source_status in ("VERIFIED", "BACKUP_VERIFIED")
        and bool(evidence_method)
        and bool(source_url)
        and bool(data_date)
        and bool(observed_at)
    )
    if verified and source.get("close_value") is not None:
        verified = str(display).removesuffix("%") == str(source.get("close_value"))
        if source.get("daily_change_bp") is not None:
            verified = verified and str(change_display) == str(source.get("daily_change_bp")) + " bp"
        else:
            verified = verified and str(change_display) == str(source.get("daily_change_percent"))
    elif verified and source.get("history_close") is not None:
        source_close = source.get("close")
        history_close = source.get("history_close")
        verified = str(display).removesuffix("%") == str(history_close)
        verified = verified and (source_close is None or str(source_close) == str(history_close))
        verified = verified and str(change_display) == str(source.get("history_change"))
    elif verified and source.get("score_value") is not None:
        verified = str(display) == str(source.get("score_value")) and str(change_display) == str(source.get("band"))
    else:
        verified = False
    observation_record = None
    observation_record_sha256 = None
    if verified:
        observation_record = {
            "source_url": source_url,
            "instrument_identity": source.get("instrument_identity") or source.get("contract_label") or source.get("name"),
            "data_date": data_date,
            "observed_value_field": "Close/Price or provider index value",
            "observed_value": (source.get("close_value") or source.get("history_close") or source.get("score_value")),
            "observed_change_field": "Change % / bp / provider band",
            "observed_change": (source.get("daily_change_bp") or source.get("daily_change_percent") or source.get("history_change") or source.get("band")),
            "checked_at_tw": observed_at,
            "evidence_method": evidence_method,
            "quote_type": source.get("quote_type"),
            "source_role": source.get("source_role"),
        }
        canonical = json.dumps(observation_record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        observation_record_sha256 = hashlib.sha256(canonical).hexdigest()
    return {
        "verification_status": source_status if verified else "PENDING_OBSERVATION_TIMESTAMP",
        # This builder reuses fixture-carried prior observations; it does not
        # fetch pages or independently reconcile values during this workflow run.
        "source_page_fetched": False,
        "display_value_reconciled": False,
        "display_value_matches_saved_observation": bool(verified),
        "observation_provenance": "FIXTURE_PRIOR_VERIFICATION_RECORD" if verified else "MISSING_PER_ITEM_OBSERVATION_TIME",
        "raw_response_sha256": source.get("raw_response_sha256"),
        "evidence_status": "RAW_RESPONSE_SAVED" if source.get("raw_response_sha256") else "BROWSER_OBSERVATION_SAVED" if verified else "NO_USABLE_OBSERVATION",
        "browser_observation_record": observation_record,
        "observation_record_sha256": observation_record_sha256,
        "captured_at_tw": None,
        "observed_at_tw": observed_at if verified else None,
        "source_record_updated_at_tw": source.get("checked_at_tw"),
        "evidence_method": evidence_method if verified else None,
        "verified_close": (source.get("close_value") or source.get("history_close") or source.get("score_value")) if verified else None,
        "verified_change": (source.get("daily_change_bp") or source.get("daily_change_percent") or source.get("history_change") or source.get("band")) if verified else None,
    }


def build_manifest(data: dict, report_date: str) -> dict:
    audit = validate_market_snapshot(data, report_date)
    rows = []
    for group in ("global_markets", "bonds", "fx", "energy", "metals", "risk"):
        for name, item in (data.get(group) or {}).items():
            source = item.get("source") or {}
            if group == "bonds":
                expected_url = BOND_PRIMARY_URLS.get(name)
                if expected_url is None or source.get("url") != expected_url:
                    raise ValueError(f"{name}: primary source must be the specified Investing.com historical-data URL")
            cross_check = source.get("cross_check") or {}
            verification = verification_fields(source, item.get("display"), item.get("change_display"))
            rows.append({
                "group": group,
                "name": name,
                "display": item.get("display"),
                "change_display": item.get("change_display"),
                "trading_date": source.get("data_date"),
                "quote_type": source.get("quote_type"),
                "source_name": source.get("name"),
                "source_url": source.get("url"),
                "source_role": "PRIMARY" if group == "bonds" else source.get("source_role", "PRIMARY_AS_CONFIGURED"),
                "cross_check_name": cross_check.get("name"),
                "cross_check_url": cross_check.get("url"),
                "cross_check_role": cross_check.get("role"),
                "checked_at_tw": source.get("verified_at_tw") or source.get("read_at_taipei") or source.get("read_at"),
                "source_record_updated_at_tw": source.get("checked_at_tw"),
                **verification,
                "notes": source.get("note") if verification["verification_status"] in ("VERIFIED", "BACKUP_VERIFIED") else "待擷取來源歷史資料列並逐項核對；目前僅有 Fixture 內來源中繼資料。",
            })
    for name, display in (data.get("sectors") or {}).items():
        source = (data.get("sector_sources") or {}).get(name) or {}
        verification = verification_fields(source, source.get("history_close"), source.get("change_display"))
        rows.append({
            "group": "sectors",
            "name": name,
            "display": display,
            "change_display": source.get("change_display"),
            "trading_date": source.get("data_date"),
            "quote_type": source.get("quote_type"),
            "source_name": source.get("name"),
            "source_url": source.get("url"),
            "checked_at_tw": source.get("verified_at_tw") or source.get("read_at_taipei") or source.get("read_at"),
            "source_record_updated_at_tw": source.get("checked_at_tw"),
            **verification,
            "notes": source.get("note") if verification["verification_status"] == "VERIFIED" else "待擷取來源歷史資料列並逐項核對；目前僅有 Fixture 內來源中繼資料。",
        })
    rows.sort(key=lambda row: (row["group"], row["name"]))
    if len(rows) != 44:
        raise ValueError(f"expected 44 source-verification rows, got {len(rows)}")
    verified_count = sum(1 for row in rows if row["verification_status"] in ("VERIFIED", "BACKUP_VERIFIED"))
    pending_count = len(rows) - verified_count
    observation_hash_missing_count = sum(1 for row in rows if row["verification_status"] in ("VERIFIED", "BACKUP_VERIFIED") and not row["observation_record_sha256"])
    raw_response_saved_count = sum(1 for row in rows if row["raw_response_sha256"])
    status = "PASS" if pending_count == 0 and observation_hash_missing_count == 0 else "PARTIAL" if verified_count else "PENDING"
    return {
        "schema_version": "1.0",
        "status": status,
        "report_date": report_date,
        "trading_date": audit["trading_date"],
        "verification_scope": "PRIOR_FIXTURE_OBSERVATIONS_REUSED_CURRENT_RUN_DID_NOT_FETCH_OR_RECONCILE_SOURCE_PAGES",
        "source_pages_fetched": False,
        "displayed_values_independently_reconciled": False,
        "prior_observation_reused_count": verified_count,
        "prior_observation_missing_time_count": pending_count,
        "row_count": len(rows),
        "pending_count": pending_count,
        "verified_count": verified_count,
        "browser_observation_records_complete": pending_count == 0 and observation_hash_missing_count == 0,
        "observation_record_hash_missing_count": observation_hash_missing_count,
        "raw_response_sha256_saved_count": raw_response_saved_count,
        "rows": rows,
        "warning": f"沿用 Fixture 既有逐筆觀察紀錄 {verified_count}/44 項；缺少可追溯逐筆觀察時間 {pending_count} 項；觀察紀錄 SHA-256 缺漏 {observation_hash_missing_count} 項。本輪未重新擷取來源頁或獨立重核數值；原始 HTTP response body 已封存 {raw_response_saved_count}/44 項（非必要條件）。",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--report-date", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    data = json.loads(Path(args.data).read_text(encoding="utf-8"))
    result = build_manifest(data, args.report_date)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    raw = path.read_bytes()
    print(json.dumps({
        "output": str(path),
        "row_count": result["row_count"],
        "pending_count": result["pending_count"],
        "verified_count": result["verified_count"],
        "sha256": hashlib.sha256(raw).hexdigest(),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
