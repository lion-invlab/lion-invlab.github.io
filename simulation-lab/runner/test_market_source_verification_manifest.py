#!/usr/bin/env python3
"""Regression tests: distinguish prior observations from current source-page fetching."""
import copy
import json
from pathlib import Path
from build_market_source_verification_manifest import build_manifest
from build_review_html import apply_market_source_verification_manifest

def main():
    data=json.loads(Path("simulation-lab/fixtures/report-data-2026-11-23.json").read_text(encoding="utf-8"))
    result=build_manifest(data,"2026-11-23")
    assert result["row_count"]==44
    assert result["verified_count"]==0
    assert result["pending_count"]==44
    assert result["status"]=="PENDING"
    assert result["source_pages_fetched"] is False
    assert result["displayed_values_independently_reconciled"] is False
    assert result["prior_observation_reused_count"]==0
    assert result["prior_observation_missing_time_count"]==44
    assert result["browser_observation_records_complete"] is False
    assert result["observation_record_hash_missing_count"]==0
    assert result["raw_response_sha256_saved_count"]==0
    assert len({(r["group"],r["name"]) for r in result["rows"]})==44
    assert all(r["verification_status"]=="PENDING_CURRENT_RUN_BROWSER_OBSERVATION" for r in result["rows"])
    assert all(r["verification_status"]!="BACKUP_VERIFIED" for r in result["rows"])
    pending=[r for r in result["rows"] if r["verification_status"]=="PENDING_CURRENT_RUN_BROWSER_OBSERVATION"]
    assert len(pending)==44
    verified=[r for r in result["rows"] if r["verification_status"] in ("VERIFIED","BACKUP_VERIFIED")]
    assert all(r["source_page_fetched"] is False for r in result["rows"])
    assert all(r["display_value_reconciled"] is False for r in result["rows"])
    assert verified==[]
    assert all(r["observation_provenance"]=="NO_COMPLETE_CURRENT_RUN_OBSERVATION" for r in result["rows"])
    assert all(r["evidence_status"]=="SOURCE_OBSERVATION_PENDING" for r in result["rows"])
    assert all(r["observation_record_sha256"] is None for r in result["rows"])
    assert all(r["browser_observation_record"] is None for r in result["rows"])
    
    
    
    
    for row in verified:
        if row["group"] in ("energy","metals"):
            assert str(row["display"]).removesuffix("%")==str(row["browser_observation_record"]["observed_value"]),row["name"]
        if row["group"]=="sectors":
            assert str(row["change_display"])==str(row["browser_observation_record"]["observed_change"]),row["name"]
            assert row["browser_observation_record"]["observed_value"] is not None,row["name"]
    bond_rows={r["name"]:r for r in result["rows"] if r["group"]=="bonds"}
    expected={
      "2年期美債殖利率":"https://www.investing.com/rates-bonds/u.s.-2-year-bond-yield-historical-data",
      "10年期美債殖利率":"https://www.investing.com/rates-bonds/u.s.-10-year-bond-yield-historical-data",
      "30年期美債殖利率":"https://www.investing.com/rates-bonds/u.s.-30-year-bond-yield-historical-data"}
    assert set(bond_rows)==set(expected)
    for name,url in expected.items():
        assert bond_rows[name]["source_url"]==url
        assert bond_rows[name]["source_role"]=="PRIMARY"
        assert "home.treasury.gov" in bond_rows[name]["cross_check_url"]
        assert bond_rows[name]["cross_check_role"]=="CROSS_CHECK_ONLY"
    assert all(r["raw_response_sha256"] is None for r in result["rows"])
    assert "舊 Fixture 觀察紀錄不納入驗證" in result["warning"]
    assert all(r["observed_at_tw"] is None for r in result["rows"])

    # A directly observed exchange holiday is distinct from a missing quote.
    closed_data = copy.deepcopy(data)
    closed_data["global_markets"]["日經225"]["display"] = "休市"
    closed_data["global_markets"]["日經225"]["change_display"] = "—"
    closed_observations = {
        ("global_markets", "日經225"): {
            "read_status": "MARKET_CLOSED",
            "finished_at_tw": "2026-11-23T18:00:00+08:00",
        }
    }
    closed_manifest = build_manifest(closed_data, "2026-11-23", closed_observations)
    nikkei_row = next(r for r in closed_manifest["rows"]
                      if r["group"] == "global_markets" and r["name"] == "日經225")
    assert nikkei_row["verification_status"] == "CLOSED"
    assert nikkei_row["evidence_status"] == "MARKET_CLOSED"
    assert closed_manifest["verified_count"] == 0
    assert closed_manifest["closed_count"] == 1
    assert closed_manifest["pending_count"] == 43
    assert closed_manifest["status"] == "PENDING"
    closed_render = copy.deepcopy(closed_data)
    closed_overlay = apply_market_source_verification_manifest(closed_render, closed_manifest)
    assert closed_render["global_markets"]["日經225"]["display"] == "休市"
    assert closed_render["global_markets"]["日經225"]["change_display"] == "—"
    assert closed_render["global_markets"]["日經225"]["qa_status"] == "market_closed"
    assert closed_overlay["closed_count"] == 1

    # Synthetic-only positive case: this validates the manifest contract,
    # not real source evidence and must never be used for report production.
    synthetic_observations = {}
    for group in ("global_markets", "bonds", "fx", "energy", "metals", "risk"):
        for name, item in (data.get(group) or {}).items():
            source = item.get("source") or {}
            value = source.get("history_close") or source.get("close_value") or source.get("score_value")
            change = source.get("history_change") or source.get("daily_change_percent") or source.get("band")
            if name == "fear_greed":
                value = "9.67368421052632"
            from build_market_source_verification_manifest import IDENTITY_ALIASES, _identity_matches
            assert _identity_matches("fx", "歐元／美元", "EUR USD")
            assert _identity_matches("global_markets", "澳洲 S&P/ASX 200", "S&P/ASX200")
            identity = IDENTITY_ALIASES.get(name, [name])[0]
            is_cnn = group == "risk" and name == "fear_greed"
            synthetic_observations[(group, name)] = {
                "status": "VERIFIED", "http_status": 200, "source_page_fetched": True,
                "read_status": "API_RESPONSE_READ_SUCCESS" if is_cnn else "PAGE_CONTENT_READ_SUCCESS",
                "source_url": source.get("url"), "target_date": source.get("data_date"),
                "observed_date": source.get("data_date"), "instrument_identity_status": "VERIFIED",
                "field_mapping_status": "VERIFIED", "display_value_match": True,
                "display_change_match": True, "observed_value": value, "observed_change": change,
                "instrument_identity": identity,
                "observed_value_field": "fear_and_greed.previous_close" if is_cnn else "Price",
                "observed_change_field": "derived_from_fear_and_greed.previous_close_using_cnn_bands" if is_cnn else "Change %",
                "finished_at_utc": "2026-11-23T11:00:00Z", "finished_at_tw": "2026-11-23T19:00:00+08:00",
                "read_method": "SYNTHETIC_TEST_ONLY", "provenance": "SYNTHETIC_TEST_ONLY",
                "data_endpoint_url": "https://production.dataviz.cnn.io/index/fearandgreed/graphdata" if is_cnn else None,
                "previous_close_target_date": source.get("data_date") if is_cnn else None,
                "source_timestamp_utc": "2026-11-23T11:00:00+00:00" if is_cnn else None,
                "raw_response_sha256": "b" * 64 if is_cnn else None,
            }
    for name, source_display in (data.get("sectors") or {}).items():
        source = (data.get("sector_sources") or {}).get(name) or {}
        synthetic_observations[("sectors", name)] = {
            "status": "VERIFIED", "http_status": 200, "source_page_fetched": True,
            "read_status": "PAGE_CONTENT_READ_SUCCESS", "source_url": source.get("url"),
            "target_date": source.get("data_date"), "observed_date": source.get("data_date"),
            "instrument_identity_status": "VERIFIED", "field_mapping_status": "VERIFIED",
            "display_value_match": True, "display_change_match": True,
            "observed_value": source.get("history_close"), "observed_change": source.get("history_change"),
            "instrument_identity": name, "observed_value_field": "Price", "observed_change_field": "Change %",
            "finished_at_utc": "2026-11-23T11:00:00Z", "finished_at_tw": "2026-11-23T19:00:00+08:00",
            "read_method": "SYNTHETIC_TEST_ONLY", "provenance": "SYNTHETIC_TEST_ONLY",
        }
    positive = build_manifest(data, "2026-11-23", synthetic_observations)
    if positive["status"] != "PASS":
        pending_rows = [
            {key: row.get(key) for key in ("group", "name", "verification_status", "source_page_fetched", "display_value_reconciled", "observation_provenance", "raw_response_sha256", "observed_at_tw")}
            for row in positive["rows"] if row.get("verification_status") not in ("VERIFIED", "BACKUP_VERIFIED")
        ]
        raise AssertionError("synthetic positive manifest did not pass: " + json.dumps(pending_rows, ensure_ascii=False))
    assert positive["verified_count"] == 44 and positive["pending_count"] == 0
    assert positive["prior_observation_reused_count"] == 0
    assert positive["source_pages_fetched"] is True
    assert positive["displayed_values_independently_reconciled"] is True
    assert all(r["observation_provenance"] == "SYNTHETIC_TEST_ONLY" for r in positive["rows"])
    assert all(len(r["observation_record_sha256"]) == 64 for r in positive["rows"])
    print("PASS: 44 unique rows; all fixture-carried observations remain pending and cannot pass Stage 2")
    print("PASS: no false claim of current-run source-page fetching or independent numeric reconciliation")
    print("PASS: synthetic test-only current-run observation bundle exercises the positive manifest path")

if __name__=="__main__": main()
