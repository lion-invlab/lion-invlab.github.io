#!/usr/bin/env python3
"""Regression tests for the source-verification worklist."""
import json
from pathlib import Path
from build_market_source_verification_manifest import build_manifest
def main():
    data=json.loads(Path("simulation-lab/fixtures/report-data-2026-11-23.json").read_text(encoding="utf-8"))
    result=build_manifest(data,"2026-11-23")
    assert result["row_count"]==44 and result["pending_count"]==44 and result["verified_count"]==0
    assert result["source_pages_fetched"] is False
    assert result["displayed_values_independently_reconciled"] is False
    assert len({(r["group"],r["name"]) for r in result["rows"]})==44
    assert all(r["verification_status"]=="PENDING_SOURCE_PAGE_CAPTURE" for r in result["rows"])
    assert all(r["source_url"].startswith("https://") for r in result["rows"])
    assert all(r["raw_response_sha256"] is None for r in result["rows"])
    print("PASS: 44 unique source tasks; no row falsely marked source-verified")
if __name__=="__main__": main()
