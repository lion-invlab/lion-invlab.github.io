#!/usr/bin/env python3
"""Regression tests: browser observation evidence is mandatory; raw HTTP body hash is optional."""
import json
from pathlib import Path
from build_market_source_verification_manifest import build_manifest

def main():
    data=json.loads(Path("simulation-lab/fixtures/report-data-2026-11-23.json").read_text(encoding="utf-8"))
    result=build_manifest(data,"2026-11-23")
    assert result["row_count"]==44 and result["pending_count"]==0 and result["verified_count"]==44
    assert result["status"]=="PASS"
    assert result["source_pages_fetched"] is True
    assert result["displayed_values_independently_reconciled"] is True
    assert result["browser_observation_records_complete"] is True
    assert result["observation_record_hash_missing_count"]==0
    assert result["raw_response_sha256_saved_count"]==0
    assert len({(r["group"],r["name"]) for r in result["rows"]})==44
    assert sum(r["verification_status"]=="VERIFIED" for r in result["rows"])==43
    assert sum(r["verification_status"]=="BACKUP_VERIFIED" for r in result["rows"])==1
    assert sum(r["verification_status"]=="PENDING_SOURCE_PAGE_CAPTURE" for r in result["rows"])==0
    assert all(r["display_value_reconciled"] for r in result["rows"] if r["verification_status"] in ("VERIFIED","BACKUP_VERIFIED"))
    assert all(r["source_url"].startswith("https://") for r in result["rows"])
    assert all(r["evidence_status"]=="BROWSER_OBSERVATION_SAVED" for r in result["rows"])
    assert all(len(r["observation_record_sha256"])==64 for r in result["rows"])
    assert all(r["browser_observation_record"]["data_date"]=="2026-11-20" for r in result["rows"])
    bond_rows = {r["name"]: r for r in result["rows"] if r["group"] == "bonds"}
    expected = {
        "2年期美債殖利率": "https://www.investing.com/rates-bonds/u.s.-2-year-bond-yield-historical-data",
        "10年期美債殖利率": "https://www.investing.com/rates-bonds/u.s.-10-year-bond-yield-historical-data",
        "30年期美債殖利率": "https://www.investing.com/rates-bonds/u.s.-30-year-bond-yield-historical-data",
    }
    assert set(bond_rows) == set(expected)
    for name, url in expected.items():
        assert bond_rows[name]["source_url"] == url
        assert bond_rows[name]["source_role"] == "PRIMARY"
        assert "home.treasury.gov" in bond_rows[name]["cross_check_url"]
        assert bond_rows[name]["cross_check_role"] == "CROSS_CHECK_ONLY"
    # Missing raw response SHA must not downgrade a fully reconciled browser observation.
    assert all(r["raw_response_sha256"] is None for r in result["rows"])
    print("PASS: 44 unique source tasks; 43 primary and 1 fallback verified; browser observation hashes complete; raw HTTP body optional")

if __name__=="__main__": main()
