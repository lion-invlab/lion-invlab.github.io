#!/usr/bin/env python3
"""Regression tests for the source-verification worklist."""
import json
from pathlib import Path
from build_market_source_verification_manifest import build_manifest
def main():
    data=json.loads(Path("simulation-lab/fixtures/report-data-2026-11-23.json").read_text(encoding="utf-8"))
    result=build_manifest(data,"2026-11-23")
    assert result["row_count"]==44 and result["pending_count"]==0 and result["verified_count"]==44
    assert result["status"]=="PARTIAL"
    assert result["source_pages_fetched"] is True
    assert result["displayed_values_independently_reconciled"] is True
    assert result["raw_response_sha256_complete"] is False
    assert result["evidence_hash_missing_count"]==44
    assert len({(r["group"],r["name"]) for r in result["rows"]})==44
    assert sum(r["verification_status"]=="VERIFIED" for r in result["rows"])==43
    assert sum(r["verification_status"]=="BACKUP_VERIFIED" for r in result["rows"])==1
    assert sum(r["verification_status"]=="PENDING_SOURCE_PAGE_CAPTURE" for r in result["rows"])==0
    assert all(r["display_value_reconciled"] for r in result["rows"] if r["verification_status"]=="VERIFIED")
    assert all(r["source_url"].startswith("https://") for r in result["rows"])
    assert all(r["raw_response_sha256"] is None for r in result["rows"])
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
    print("PASS: 44 unique source tasks; no row falsely marked source-verified")
if __name__=="__main__": main()
