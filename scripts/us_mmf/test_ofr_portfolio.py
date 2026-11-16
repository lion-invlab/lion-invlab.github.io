#!/usr/bin/env python3
"""QA for OFR broad U.S. MMF portfolio allocation series."""
from __future__ import annotations
import csv, sys
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "data/us-mmf/fed_mmf_ofr_portfolio_latest.csv"
EXPECTED = {"Total", "U.S. Treasury securities", "Federal Agency and GSE securities", "Bank-related assets", "Other assets", "Repurchase agreements"}
def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    with path.open(newline="", encoding="utf-8") as f: rows = list(csv.DictReader(f))
    if len(rows) != 191 * 6: raise SystemExit(f"FAIL: expected 1146 rows, got {len(rows)}")
    by_date = defaultdict(dict)
    for r in rows:
        value, share = float(r["value_usd"]), float(r["share_of_total"])
        if value < 0 or share < 0 or share > 1.000001: raise SystemExit(f"FAIL: invalid value/share {r['date']} {r['asset_class']}")
        if abs(float(r["value_usd_trillion"]) - value / 1e12) > 0.000000001: raise SystemExit(f"FAIL: unit mismatch {r['date']} {r['asset_class']}")
        if r["asset_class"] in by_date[r["date"]]: raise SystemExit(f"FAIL: duplicate asset class {r['date']} {r['asset_class']}")
        by_date[r["date"]][r["asset_class"]] = value
    dates = sorted(by_date)
    if len(dates) != 191 or dates[0] != "2010-11-30" or dates[-1] != "2026-09-30": raise SystemExit(f"FAIL: coverage {len(dates)} {dates[0]} to {dates[-1]}")
    max_diff = 0.0
    for d in dates:
        if set(by_date[d]) != EXPECTED: raise SystemExit(f"FAIL: missing categories {d}")
        total = by_date[d]["Total"]
        diff = sum(v for k,v in by_date[d].items() if k != "Total") - total
        max_diff = max(max_diff, abs(diff))
        if abs(diff) > 1.0: raise SystemExit(f"FAIL: asset categories do not reconcile {d}: {diff} USD")
    latest_total = by_date[dates[-1]]["Total"]
    if abs(latest_total - 8_396_822_287_018.74) > 1: raise SystemExit(f"FAIL: latest total mismatch {latest_total}")
    print(f"PASS: 191 monthly observations; 2010-11 to 2026-09; 5 broad asset classes; max reconciliation difference USD {max_diff:.6f}; latest total USD {latest_total/1e12:.6f}tn")
    return 0
if __name__ == "__main__": raise SystemExit(main())
