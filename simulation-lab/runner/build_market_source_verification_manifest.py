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


def build_manifest(data: dict, report_date: str) -> dict:
    audit = validate_market_snapshot(data, report_date)
    rows = []
    for group in ("global_markets", "bonds", "fx", "energy", "metals", "risk"):
        for name, item in (data.get(group) or {}).items():
            source = item.get("source") or {}
            rows.append({
                "group": group,
                "name": name,
                "display": item.get("display"),
                "change_display": item.get("change_display"),
                "trading_date": source.get("data_date"),
                "quote_type": source.get("quote_type"),
                "source_name": source.get("name"),
                "source_url": source.get("url"),
                "checked_at_tw": source.get("checked_at_tw") or source.get("verified_at_tw") or source.get("checked_at"),
                "verification_status": "PENDING_SOURCE_PAGE_CAPTURE",
                "source_page_fetched": False,
                "display_value_reconciled": False,
                "raw_response_sha256": None,
                "captured_at_tw": None,
                "notes": "待擷取來源歷史資料列並逐項核對；目前僅有 Fixture 內來源中繼資料。",
            })
    for name, display in (data.get("sectors") or {}).items():
        source = (data.get("sector_sources") or {}).get(name) or {}
        rows.append({
            "group": "sectors",
            "name": name,
            "display": display,
            "change_display": source.get("change_display"),
            "trading_date": source.get("data_date"),
            "quote_type": source.get("quote_type"),
            "source_name": source.get("name"),
            "source_url": source.get("url"),
            "checked_at_tw": source.get("checked_at_tw") or source.get("verified_at_tw") or source.get("checked_at"),
            "verification_status": "PENDING_SOURCE_PAGE_CAPTURE",
            "source_page_fetched": False,
            "display_value_reconciled": False,
            "raw_response_sha256": None,
            "captured_at_tw": None,
            "notes": "待擷取來源歷史資料列並逐項核對；目前僅有 Fixture 內來源中繼資料。",
        })
    rows.sort(key=lambda row: (row["group"], row["name"]))
    if len(rows) != 44:
        raise ValueError(f"expected 44 source-verification rows, got {len(rows)}")
    return {
        "schema_version": "1.0",
        "report_date": report_date,
        "trading_date": audit["trading_date"],
        "verification_scope": "SOURCE_PAGE_CAPTURE_AND_VALUE_RECONCILIATION_PENDING",
        "source_pages_fetched": False,
        "displayed_values_independently_reconciled": False,
        "row_count": len(rows),
        "pending_count": len(rows),
        "verified_count": 0,
        "rows": rows,
        "warning": "此清單是來源核驗工作台，不是來源核驗結果；不得據此標示行情數值已核實。",
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
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
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
