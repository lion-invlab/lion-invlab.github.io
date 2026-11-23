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


def verification_fields(source: dict, display, change_display, observation: dict | None = None) -> dict:
    """Accept only a complete observation captured by this workflow run."""
    observation = observation or {}
    source_url = source.get("url")
    data_date = source.get("data_date")
    verified = (
        observation.get("status") == "VERIFIED"
        and observation.get("http_status") == 200
        and observation.get("source_url") == source_url
        and observation.get("target_date") == data_date
        and observation.get("instrument_identity_status") == "VERIFIED"
        and observation.get("field_mapping_status") == "VERIFIED"
        and observation.get("display_value_match") is True
        and observation.get("display_change_match") is True
        and observation.get("observed_value") is not None
        and observation.get("observed_change") is not None
        and bool(observation.get("finished_at_utc"))
    )
    record = None
    record_hash = None
    if verified:
        record = {
            "source_url": source_url,
            "data_endpoint_url": observation.get("data_endpoint_url"),
            "instrument_identity": observation.get("instrument_identity"),
            "data_date": data_date,
            "observed_value_field": observation.get("observed_value_field"),
            "observed_value": observation.get("observed_value"),
            "observed_change_field": observation.get("observed_change_field"),
            "observed_change": observation.get("observed_change"),
            "checked_at_tw": observation.get("finished_at_utc"),
            "evidence_method": observation.get("read_method"),
            "quote_type": source.get("quote_type"),
            "source_role": source.get("source_role"),
        }
        canonical = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        record_hash = hashlib.sha256(canonical).hexdigest()
    return {
        "verification_status": source.get("verification_status") if verified else "PENDING_CURRENT_RUN_BROWSER_OBSERVATION",
        "source_page_fetched": observation.get("http_status") == 200,
        "display_value_reconciled": verified,
        "display_value_matches_saved_observation": verified,
        "observation_provenance": "CURRENT_RUN_BROWSER_OBSERVATION" if verified else "NO_COMPLETE_CURRENT_RUN_OBSERVATION",
        "raw_response_sha256": None,
        "evidence_status": "BROWSER_OBSERVATION_VERIFIED" if verified else "BROWSER_OBSERVATION_PENDING",
        "browser_observation_record": record,
        "observation_record_sha256": record_hash,
        "captured_at_tw": observation.get("finished_at_utc"),
        "observed_at_tw": observation.get("finished_at_utc") if verified else None,
        "source_record_updated_at_tw": source.get("checked_at_tw"),
        "evidence_method": observation.get("read_method") if verified else None,
        "verified_close": observation.get("observed_value") if verified else None,
        "verified_change": observation.get("observed_change") if verified else None,
    }

def build_manifest(data: dict, report_date: str, browser_observations: dict | None = None) -> dict:
    audit = validate_market_snapshot(data, report_date)
    browser_observations = browser_observations or {}
    rows = []
    for group in ("global_markets", "bonds", "fx", "energy", "metals", "risk"):
        for name, item in (data.get(group) or {}).items():
            source = item.get("source") or {}
            if group == "bonds":
                expected_url = BOND_PRIMARY_URLS.get(name)
                if expected_url is None or source.get("url") != expected_url:
                    raise ValueError(f"{name}: primary source must be the specified Investing.com historical-data URL")
            cross_check = source.get("cross_check") or {}
            verification = verification_fields(source, item.get("display"), item.get("change_display"), browser_observations.get((group, name)), group, name)
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
        verification = verification_fields(source, source.get("history_close"), source.get("change_display"), browser_observations.get(("sectors", name)), "sectors", name)
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
        "schema_version": "1.1",
        "status": status,
        "report_date": report_date,
        "trading_date": audit["trading_date"],
        "verification_scope": "CURRENT_RUN_BROWSER_OBSERVATIONS",
        "source_pages_fetched": all(row["source_page_fetched"] for row in rows),
        "displayed_values_independently_reconciled": verified_count == 44,
        "prior_observation_reused_count": 0,
        "prior_observation_missing_time_count": pending_count,
        "row_count": len(rows),
        "pending_count": pending_count,
        "verified_count": verified_count,
        "browser_observation_records_complete": pending_count == 0 and observation_hash_missing_count == 0,
        "observation_record_hash_missing_count": observation_hash_missing_count,
        "raw_response_sha256_saved_count": raw_response_saved_count,
        "rows": rows,
        "warning": f"本次瀏覽器驗證完整通過 {verified_count}/44 項；尚有 {pending_count} 項未取得完整商品身分、欄位映射與報價核對證據。舊 Fixture 觀察紀錄不納入驗證。",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--report-date", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--observations", required=True)
    args = parser.parse_args()
    data = json.loads(Path(args.data).read_text(encoding="utf-8"))
    obs_payload = json.loads(Path(args.observations).read_text(encoding="utf-8"))
    obs_rows = obs_payload.get("observations") or []
    obs_map = {(row.get("group"), row.get("name")): row for row in obs_rows}
    if len(obs_map) != 44:
        raise SystemExit(f"expected 44 unique browser observations, got {len(obs_map)}")
    result = build_manifest(data, args.report_date, obs_map)
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
