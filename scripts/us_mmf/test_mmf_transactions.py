#!/usr/bin/env python3
"""QA for Federal Reserve Z.1 S123.t MMF net acquisition transactions."""
from __future__ import annotations
import csv
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "data/us-mmf/fed_mmf_transactions_latest.csv"


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    required = {
        "date", "quarter_label", "net_acquisition_millions_usd_saar",
        "net_acquisition_usd_trillion_saar",
    }
    if len(rows) < 4 or not required.issubset(rows[0]):
        raise SystemExit("FAIL: missing rows or required columns")
    dates = [date.fromisoformat(r["date"]) for r in rows]
    if dates != sorted(dates) or len(dates) != len(set(dates)):
        raise SystemExit("FAIL: dates are not strictly increasing and unique")
    for d in dates:
        if d.month not in (1, 4, 7, 10) or d.day != 1:
            raise SystemExit(f"FAIL: invalid quarterly date {d}")
    # Preserve genuine missing observations; never interpolate transaction data.
    gap_count = sum(
        (dates[i].year * 4 + (dates[i].month - 1) // 3)
        - (dates[i - 1].year * 4 + (dates[i - 1].month - 1) // 3) - 1
        for i in range(1, len(dates))
    )
    for row in rows:
        raw = int(row["net_acquisition_millions_usd_saar"])
        tn = float(row["net_acquisition_usd_trillion_saar"])
        if abs(tn - raw / 1_000_000) > 0.00000051:
            raise SystemExit(f"FAIL: unit conversion mismatch at {row['date']}")
        d = date.fromisoformat(row["date"])
        if row["quarter_label"] != f"{d.year} Q{(d.month - 1) // 3 + 1}":
            raise SystemExit(f"FAIL: quarter label mismatch at {row['date']}")
    latest = rows[-1]
    if latest["date"] != "2026-04-01" or int(latest["net_acquisition_millions_usd_saar"]) != 723692:
        raise SystemExit("FAIL: latest 2026 Q2 value does not match official Z.1 S123.t")
    print(f"PASS: {len(rows)} transaction observations; {rows[0]['quarter_label']} to {latest['quarter_label']}; {gap_count} missing quarters preserved; latest USD {float(latest['net_acquisition_usd_trillion_saar']):.6f}tn SAAR")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
