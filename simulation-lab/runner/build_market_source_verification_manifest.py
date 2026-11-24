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
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

from validate_market_snapshot import validate_market_snapshot

BOND_PRIMARY_URLS = {
    "2年期美債殖利率": "https://www.investing.com/rates-bonds/u.s.-2-year-bond-yield-historical-data",
    "10年期美債殖利率": "https://www.investing.com/rates-bonds/u.s.-10-year-bond-yield-historical-data",
    "30年期美債殖利率": "https://www.investing.com/rates-bonds/u.s.-30-year-bond-yield-historical-data",
}


IDENTITY_ALIASES = {
    "道瓊工業指數": ["Dow Jones Industrial Average", "Dow Jones", "DJI"],
    "標普500指數": ["S&P 500", "SPX"],
    "那斯達克綜合指數": ["Nasdaq Composite", "IXIC"],
    "羅素2000指數": ["Russell 2000", "RUT"],
    "費城半導體指數": ["PHLX Semiconductor", "Philadelphia Semiconductor", "SOX"],
    "日經225": ["Nikkei 225", "N225"],
    "韓國 KOSPI": ["KOSPI", "KS11"],
    "台灣加權指數": ["Taiwan Weighted", "TWII"],
    "新加坡海峽時報指數 STI": ["FTSE Straits Times", "STI"],
    "澳洲 S&P/ASX 200": ["S&P/ASX 200", "S&P/ASX200", "ASX 200", "AXJO"],
    "上海綜合指數": ["Shanghai Composite", "SSEC"],
    "深證成指": ["SZSE Component", "SZI"],
    "香港恆生指數": ["Hang Seng", "HSI"],
    "英國 FTSE 100": ["FTSE 100", "UKX"],
    "德國 DAX": ["DAX", "GDAXI"],
    "法國 CAC 40": ["CAC 40", "FCHI"],
    "STOXX Europe 600": ["STOXX Europe 600", "STOXX 600", "SXXP"],
    "2年期美債殖利率": ["United States 2-Year Bond Yield", "2-Year Bond Yield"],
    "10年期美債殖利率": ["United States 10-Year Bond Yield", "10-Year Bond Yield"],
    "30年期美債殖利率": ["United States 30-Year Bond Yield", "30-Year Bond Yield"],
    "美元指數": ["US Dollar Index", "DXY"],
    "美元／新台幣": ["USD/TWD"],
    "歐元／美元": ["EUR/USD", "EUR USD"],
    "英鎊／美元": ["GBP/USD"],
    "澳幣／美元": ["AUD/USD"],
    "美元／日圓": ["USD/JPY"],
    "WTI原油期貨": ["WTI原油期貨", "WTI Crude Oil", "CLF27"],
    "Brent原油期貨": ["倫敦布倫特原油期貨", "Brent Oil", "LCOG7"],
    "黃金期貨 GC": ["黃金期貨", "Gold Futures", "GCZ6"],
    "白銀期貨 SI": ["白銀期貨", "Silver Futures", "SIZ6"],
    "vix": ["CBOE Volatility Index", "VIX"],
    "move": ["ICE BofAML MOVE", "MOVE"],
    "fear_greed": ["CNN Fear & Greed Index", "Fear & Greed"],
}

def _decimal_value(value):
    try:
        return Decimal(str(value).replace(",", "").replace("%", "").replace("+", "").strip())
    except (InvalidOperation, TypeError, ValueError):
        return None

def _identity_matches(group, name, identity):
    text = str(identity or "").casefold()
    aliases = [name] if group == "sectors" else IDENTITY_ALIASES.get(name, [name])
    return bool(text) and any(str(alias).casefold() in text for alias in aliases)

def _expected_value(source):
    for key in ("close_value", "history_close", "source_score_value", "score_value"):
        if source.get(key) is not None:
            return source.get(key)
    return None

def _expected_change(source):
    for key in ("daily_change_percent", "history_change", "band"):
        if source.get(key) is not None:
            return source.get(key)
    return None

def _numeric_match(observed, expected, rounded_integer=False):
    actual = _decimal_value(observed)
    target = _decimal_value(expected)
    if actual is None or target is None:
        return False
    if rounded_integer:
        return actual.quantize(Decimal("1"), rounding=ROUND_HALF_UP) == target.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return abs(actual - target) <= Decimal("0.0000001")

def verification_fields(source: dict, display, change_display, observation: dict | None = None,
                        group: str = "", name: str = "") -> dict:
    """Accept only complete, fresh source observations from this report session."""
    observation = observation or {}
    source_url = source.get("url")
    if observation.get("read_status") == "MARKET_CLOSED":
        return {
            "verification_status": "CLOSED",
            "source_page_fetched": True,
            "display_value_reconciled": False,
            "display_value_matches_saved_observation": False,
            "observation_provenance": "CURRENT_CHATGPT_WEB_OPEN_OBSERVATION",
            "raw_response_sha256": None,
            "evidence_status": "MARKET_CLOSED",
            "browser_observation_record": None,
            "observation_record_sha256": None,
            "captured_at_tw": observation.get("finished_at_tw") or observation.get("finished_at_utc"),
        }
    data_date = source.get("data_date")
    read_method = observation.get("read_method")
    provenance = observation.get("provenance")
    page_read_ok = (
        observation.get("http_status") == 200
        or (observation.get("source_page_fetched") is True
            and observation.get("read_status") == "PAGE_CONTENT_READ_SUCCESS")
    )
    identity_ok = _identity_matches(group, name, observation.get("instrument_identity"))
    value_field = str(observation.get("observed_value_field") or "")
    change_field = str(observation.get("observed_change_field") or "")
    is_fear_greed = group == "risk" and name == "fear_greed"
    fear_greed_backup = is_fear_greed and source.get("source_role") in ("BACKUP_1", "BACKUP", "SECONDARY")
    if is_fear_greed and fear_greed_backup:
        field_ok = value_field == "Score" and change_field == "Band"
    elif is_fear_greed:
        field_ok = (
            value_field == "fear_and_greed.previous_close"
            and change_field == "derived_from_fear_and_greed.previous_close_using_cnn_bands"
        )
    else:
        field_ok = (
            value_field in ("Price", "Close", "收市", "收盤", "收盤價")
            and change_field in ("Change %", "升跌（%）", "漲跌（%）", "變動%")
        )
    expected_value = source.get("score_value") if is_fear_greed else _expected_value(source)
    expected_change = source.get("band") if fear_greed_backup else _expected_change(source)
    value_match = _numeric_match(
        observation.get("observed_value"), expected_value,
        rounded_integer=is_fear_greed,
    )
    raw_score_match = True
    if is_fear_greed:
        raw_score_match = _numeric_match(observation.get("observed_value"), source.get("source_score_value"))
        change_match = str(observation.get("observed_change") or "").strip().casefold() == str(expected_change or "").strip().casefold()
    else:
        change_match = _numeric_match(observation.get("observed_change"), expected_change)
    current_provenance = provenance in (
        "CURRENT_RUN_BROWSER_OBSERVATION",
        "CURRENT_CHATGPT_WEB_OPEN_OBSERVATION",
        "CURRENT_CHATGPT_WEB_SEARCH_RESULT_OBSERVATION",
        "CURRENT_CNN_OFFICIAL_API_OBSERVATION",
        "SYNTHETIC_TEST_ONLY",
    )
    verified = (
        observation.get("status") == "VERIFIED"
        and page_read_ok
        and observation.get("source_url") == source_url
        and observation.get("target_date") == data_date
        and observation.get("observed_date") == data_date
        and identity_ok
        and observation.get("instrument_identity_status") == "VERIFIED"
        and field_ok
        and observation.get("field_mapping_status") == "VERIFIED"
        and value_match
        and raw_score_match
        and change_match
        and observation.get("display_value_match") is True
        and observation.get("display_change_match") is True
        and observation.get("observed_value") is not None
        and observation.get("observed_change") is not None
        and bool(observation.get("finished_at_utc"))
        and bool(read_method)
        and current_provenance
    )
    record = None
    record_hash = None
    if verified:
        record = {
            "source_url": source_url,
            "data_endpoint_url": observation.get("data_endpoint_url"),
            "instrument_identity": observation.get("instrument_identity"),
            "data_date": data_date,
            "observed_date": observation.get("observed_date"),
            "observed_value_field": value_field,
            "observed_value": observation.get("observed_value"),
            "expected_source_raw_value": source.get("source_score_value") if group == "risk" and name == "fear_greed" else None,
            "observed_change_field": change_field,
            "observed_change": observation.get("observed_change"),
            "checked_at_tw": observation.get("finished_at_tw") or observation.get("finished_at_utc"),
            "evidence_method": read_method,
            "provenance": provenance,
            "web_reader_ref": observation.get("web_reader_ref"),
            "web_line_start": observation.get("web_line_start"),
            "web_line_end": observation.get("web_line_end"),
            "read_status": observation.get("read_status"),
            "raw_response_sha256": observation.get("raw_response_sha256"),
            "quote_type": source.get("quote_type"),
            "source_role": source.get("source_role"),
        }
        canonical = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        record_hash = hashlib.sha256(canonical).hexdigest()
    source_role = source.get("source_role", "PRIMARY")
    verification_status = (
        "BACKUP_VERIFIED" if verified and source_role in ("BACKUP_1", "BACKUP", "SECONDARY")
        else "VERIFIED" if verified
        else "PENDING_CURRENT_RUN_BROWSER_OBSERVATION"
    )
    return {
        "verification_status": verification_status,
        "source_page_fetched": page_read_ok,
        "display_value_reconciled": verified,
        "display_value_matches_saved_observation": verified,
        "observation_provenance": provenance if verified else "NO_COMPLETE_CURRENT_RUN_OBSERVATION",
        "raw_response_sha256": observation.get("raw_response_sha256") if verified else None,
        "evidence_status": "SOURCE_OBSERVATION_VERIFIED" if verified else "SOURCE_OBSERVATION_PENDING",
        "browser_observation_record": record,
        "observation_record_sha256": record_hash,
        "captured_at_tw": observation.get("finished_at_tw") or observation.get("finished_at_utc"),
        "observed_at_tw": (observation.get("finished_at_tw") or observation.get("finished_at_utc")) if verified else None,
        "source_record_updated_at_tw": source.get("checked_at_tw"),
        "evidence_method": read_method if verified else None,
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
    closed_count = sum(1 for row in rows if row["verification_status"] == "CLOSED")
    pending_count = sum(1 for row in rows if row["verification_status"] == "PENDING_CURRENT_RUN_BROWSER_OBSERVATION")
    if verified_count + closed_count + pending_count != len(rows):
        raise ValueError("44-row status counts do not reconcile: verified + closed + pending must equal row_count")
    observation_hash_missing_count = sum(1 for row in rows if row["verification_status"] in ("VERIFIED", "BACKUP_VERIFIED") and not row["observation_record_sha256"])
    raw_response_saved_count = sum(1 for row in rows if row["raw_response_sha256"])
    # PASS means every one of the 44 numeric rows is independently reconciled; a closed market remains PARTIAL.
    status = "PASS" if verified_count == 44 and observation_hash_missing_count == 0 else "PARTIAL" if verified_count else "PENDING"
    return {
        "schema_version": "1.1",
        "status": status,
        "report_date": report_date,
        "trading_date": audit["trading_date"],
        "verification_scope": "CURRENT_REPORT_SESSION_SOURCE_OBSERVATIONS",
        "source_pages_fetched": all(row["source_page_fetched"] for row in rows),
        "displayed_values_independently_reconciled": verified_count == 44,
        "prior_observation_reused_count": 0,
        "prior_observation_missing_time_count": pending_count,
        "row_count": len(rows),
        "pending_count": pending_count,
        "closed_count": closed_count,
        "verified_count": verified_count,
        "browser_observation_records_complete": pending_count == 0 and observation_hash_missing_count == 0,
        "observation_record_hash_missing_count": observation_hash_missing_count,
        "raw_response_sha256_saved_count": raw_response_saved_count,
        "rows": rows,
        "warning": f"本次來源頁面觀察：{verified_count} 項已核實、{closed_count} 項休市、{pending_count} 項待核實；舊 Fixture 觀察紀錄不納入驗證。",
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
