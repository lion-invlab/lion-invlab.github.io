#!/usr/bin/env python3
"""QA for Federal Reserve EFA monthly MMF investment holdings."""
from __future__ import annotations
import csv, sys, calendar
from collections import defaultdict
from datetime import date
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "data/us-mmf/fed_mmf_holdings_by_type_latest.csv"
EXPECTED = {"Total": 6, "Government": 5, "Prime": 6, "Tax-exempt": 3}
def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 188 * sum(EXPECTED.values()):
        raise SystemExit(f"FAIL: expected {188 * sum(EXPECTED.values())} rows, got {len(rows)}")
    by_month = defaultdict(lambda: defaultdict(list))
    for r in rows:
        d = date.fromisoformat(r["date"])
        last_day = date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])
        while last_day.weekday() >= 5:
            last_day = date.fromordinal(last_day.toordinal() - 1)
        if d != last_day: raise SystemExit(f"FAIL: not last business day of month {d}")
        value, share = float(r["value_millions_usd"]), float(r["share_of_fund_type"])
        if value < 0 or share < 0 or share > 1.000001: raise SystemExit(f"FAIL: invalid value/share at {d}")
        if abs(float(r["value_usd_trillion"]) - value / 1_000_000) > 0.000000001: raise SystemExit(f"FAIL: unit conversion mismatch at {d}")
        by_month[r["date"]][r["fund_type"]].append((r["instrument"], value, share))
    dates = sorted(by_month)
    if len(dates) != 188 or dates[0] != "2010-12-31" or dates[-1] != "2026-07-31": raise SystemExit(f"FAIL: unexpected coverage {len(dates)} {dates[0]} to {dates[-1]}")
    max_diff = 0.0
    for d in dates:
        if set(by_month[d]) != set(EXPECTED): raise SystemExit(f"FAIL: missing fund type at {d}")
        totals = {}
        for fund_type, count in EXPECTED.items():
            items = by_month[d][fund_type]
            if len(items) != count or len({x[0] for x in items}) != count: raise SystemExit(f"FAIL: instrument count mismatch {fund_type} {d}")
            if abs(sum(x[2] for x in items) - 1) > 0.00001: raise SystemExit(f"FAIL: portfolio shares do not sum to 100% {fund_type} {d}")
            totals[fund_type] = sum(x[1] for x in items)
        diff = totals["Government"] + totals["Prime"] + totals["Tax-exempt"] - totals["Total"]
        max_diff = max(max_diff, abs(diff))
        if abs(diff) > 5: raise SystemExit(f"FAIL: fund-type reconciliation mismatch {d}: {diff}m")
    latest = {k: sum(x[1] for x in by_month[dates[-1]][k]) for k in EXPECTED}
    if abs(latest["Total"] - 8_411_936) > 5: raise SystemExit(f"FAIL: unexpected latest EFA total {latest['Total']}m")
    print(f"PASS: 188 monthly observations; 2010-12 to 2026-07; 20 instrument series; max reconciliation diff {max_diff:.3f}m; latest total USD {latest['Total']/1e6:.6f}tn")
    return 0
if __name__ == "__main__": raise SystemExit(main())
