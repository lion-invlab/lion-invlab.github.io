#!/usr/bin/env python3
"""Regression tests: distinguish prior observations from current source-page fetching."""
import json
from pathlib import Path
from build_market_source_verification_manifest import build_manifest

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
    assert result["prior_observation_missing_time_count"]==0
    assert result["browser_observation_records_complete"] is False
    assert result["observation_record_hash_missing_count"]==0
    assert result["raw_response_sha256_saved_count"]==0
    assert len({(r["group"],r["name"]) for r in result["rows"]})==44
    assert all(r["verification_status"]=="PENDING_CURRENT_RUN_BROWSER_OBSERVATION" for r in result["rows"])
    backup_rows={r["name"]:r for r in result["rows"] if r["verification_status"]=="BACKUP_VERIFIED"}
    assert set(backup_rows)=={"Brent原油期貨","fear_greed"}
    assert backup_rows["Brent原油期貨"]["source_role"]=="BACKUP_1"
    assert "ICE public historical settlement row was not exposed" in backup_rows["Brent原油期貨"]["notes"]
    assert backup_rows["fear_greed"]["source_role"]=="FALLBACK_1"
    assert "CNN Business" in backup_rows["fear_greed"]["notes"]
    pending=[r for r in result["rows"] if r["verification_status"]=="PENDING_OBSERVATION_TIMESTAMP"]
    assert len(pending)==44
    verified=[r for r in result["rows"] if r["verification_status"] in ("VERIFIED","BACKUP_VERIFIED")]
    assert all(r["source_page_fetched"] is False for r in result["rows"])
    assert all(r["display_value_reconciled"] is False for r in result["rows"])
    assert verified==[]
    assert all(r["observation_provenance"]=="NO_CURRENT_RUN_BROWSER_OBSERVATION" for r in result["rows"])
    assert all(r["evidence_status"]=="BROWSER_OBSERVATION_SAVED" for r in verified)
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
    assert "本輪未重新擷取來源頁" in result["warning"]
    assert all(r["observed_at_tw"]=="2026-11-22T17:48:21+08:00" for r in result["rows"] if r["group"]=="bonds")
    print("PASS: 44 unique rows; all fixture-carried observations remain pending and cannot pass Stage 2")
    print("PASS: no false claim of current-run source-page fetching or independent numeric reconciliation")
    print("PASS: prior fixture records are not promoted to verified evidence")

if __name__=="__main__": main()
