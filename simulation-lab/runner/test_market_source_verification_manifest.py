#!/usr/bin/env python3
"""Regression tests: distinguish prior observations from current source-page fetching."""
import json
from pathlib import Path
from build_market_source_verification_manifest import build_manifest

def main():
    data=json.loads(Path("simulation-lab/fixtures/report-data-2026-11-23.json").read_text(encoding="utf-8"))
    result=build_manifest(data,"2026-11-23")
    assert result["row_count"]==44
    assert result["verified_count"]==44
    assert result["pending_count"]==0
    assert result["status"]=="PASS"
    assert result["source_pages_fetched"] is False
    assert result["displayed_values_independently_reconciled"] is False
    assert result["prior_observation_reused_count"]==44
    assert result["prior_observation_missing_time_count"]==0
    assert result["browser_observation_records_complete"] is True
    assert result["observation_record_hash_missing_count"]==0
    assert result["raw_response_sha256_saved_count"]==0
    assert len({(r["group"],r["name"]) for r in result["rows"]})==44
    assert sum(r["verification_status"]=="VERIFIED" for r in result["rows"])==43
    assert sum(r["verification_status"]=="BACKUP_VERIFIED" for r in result["rows"])==1
    pending=[r for r in result["rows"] if r["verification_status"]=="PENDING_OBSERVATION_TIMESTAMP"]
    assert pending==[]
    verified=[r for r in result["rows"] if r["verification_status"] in ("VERIFIED","BACKUP_VERIFIED")]
    assert all(r["source_page_fetched"] is False for r in result["rows"])
    assert all(r["display_value_reconciled"] is False for r in result["rows"])
    assert all(r["display_value_matches_saved_observation"] for r in verified)
    assert all(r["observation_provenance"]=="FIXTURE_PRIOR_VERIFICATION_RECORD" for r in verified)
    assert all(r["evidence_status"]=="BROWSER_OBSERVATION_SAVED" for r in verified)
    assert all(len(r["observation_record_sha256"])==64 for r in verified)
    assert all(r["browser_observation_record"]["data_date"]=="2026-11-20" for r in verified)
    assert all(r["browser_observation_record"]["observed_value"] is not None for r in verified)
    assert all(r["browser_observation_record"]["observed_change"] is not None for r in verified)
    assert all(r["browser_observation_record"]["checked_at_tw"]==r["observed_at_tw"] for r in verified)
    assert all(r["observed_at_tw"]!=r["source_record_updated_at_tw"] for r in verified if r["source_record_updated_at_tw"])
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
    print("PASS: 44 unique rows; 44 fixture-carried observations complete; all three Treasury rows have explicit source observation time")
    print("PASS: no false claim of current-run source-page fetching or independent numeric reconciliation")
    print("PASS: observation-record SHA integrity; raw HTTP body hash remains optional")

if __name__=="__main__": main()
