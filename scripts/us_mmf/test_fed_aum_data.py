#!/usr/bin/env python3
"""Structural QA for the archived Fed MMF AUM quarterly CSV."""
from __future__ import annotations
import csv
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "data/us-mmf/fed_mmmffaq027s_1974q1_2026q2.csv"


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    required = {
        "fred_observation_date", "value_raw_millions_usd",
        "value_usd_trillion", "quarter_label",
    }
    if not rows or not required.issubset(rows[0]):
        raise SystemExit("FAIL: missing rows or required columns")

    dates = [date.fromisoformat(r["fred_observation_date"]) for r in rows]
    if dates != sorted(dates) or len(dates) != len(set(dates)):
        raise SystemExit("FAIL: dates are not strictly increasing and unique")

    for i, d in enumerate(dates):
        if d.month not in (1, 4, 7, 10) or d.day != 1:
            raise SystemExit(f"FAIL: unexpected FRED quarterly date {d}")
        if i and (d.year * 4 + (d.month - 1) // 3) != (
            dates[i-1].year * 4 + (dates[i-1].month - 1) // 3 + 1
        ):
            raise SystemExit(f"FAIL: quarterly gap before {d}")

    for r in rows:
        raw = float(r["value_raw_millions_usd"])
        tn = float(r["value_usd_trillion"])
        if raw <= 0 or abs(tn - raw / 1_000_000) > 0.00000051:
            raise SystemExit(f"FAIL: invalid value/conversion at {r['fred_observation_date']}")
        year, month = int(r["fred_observation_date"][:4]), int(r["fred_observation_date"][5:7])
        q = (month - 1) // 3 + 1
        if r["quarter_label"] != f"{year} Q{q}":
            raise SystemExit(f"FAIL: quarter label mismatch at {r['fred_observation_date']}")

    latest = rows[-1]
    if latest["fred_observation_date"] != "2026-04-01":
        raise SystemExit(f"FAIL: unexpected latest date {latest['fred_observation_date']}")
    if int(latest["value_raw_millions_usd"]) != 8441374:
        raise SystemExit("FAIL: latest value does not match FRED Q2 2026")

    print(
        f"PASS: {len(rows)} quarterly observations; "
        f"{rows[0]['quarter_label']} to {latest['quarter_label']}; "
        f"latest USD {float(latest['value_usd_trillion']):.6f}tn"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
