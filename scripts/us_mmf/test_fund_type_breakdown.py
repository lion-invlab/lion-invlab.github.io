#!/usr/bin/env python3
"""QA for the Federal Reserve Z.1 quarterly MMF AUM fund-type split."""
from __future__ import annotations
import csv
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "data/us-mmf/fed_mmf_aum_by_fund_type_2010q4_2026q2.csv"
CATEGORIES = (
    "government_millions_usd",
    "prime_millions_usd",
    "tax_exempt_millions_usd",
)


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 63:
        raise SystemExit(f"FAIL: expected 63 quarterly rows, got {len(rows)}")

    dates = [date.fromisoformat(r["date"]) for r in rows]
    if dates != sorted(dates) or len(dates) != len(set(dates)):
        raise SystemExit("FAIL: dates are not strictly increasing and unique")

    max_abs_diff = 0
    for i, row in enumerate(rows):
        d = dates[i]
        if d.month not in (1, 4, 7, 10) or d.day != 1:
            raise SystemExit(f"FAIL: invalid quarterly date {d}")
        if i:
            prev = dates[i-1]
            current_idx = d.year * 4 + (d.month - 1) // 3
            prev_idx = prev.year * 4 + (prev.month - 1) // 3
            if current_idx != prev_idx + 1:
                raise SystemExit(f"FAIL: quarterly gap before {d}")

        total = int(row["total_aum_millions_usd"])
        category_sum = sum(int(row[k]) for k in CATEGORIES)
        recorded_sum = int(row["category_sum_millions_usd"])
        diff = int(row["difference_millions_usd"])
        if category_sum != recorded_sum or diff != category_sum - total:
            raise SystemExit(f"FAIL: sum or difference mismatch at {d}")
        max_abs_diff = max(max_abs_diff, abs(diff))
        if abs(diff) > 1:
            raise SystemExit(f"FAIL: category totals diverge from total by >1m at {d}")

    latest = rows[-1]
    if latest["date"] != "2026-04-01":
        raise SystemExit("FAIL: latest quarter is not 2026 Q2")
    if int(latest["total_aum_millions_usd"]) != 8441374:
        raise SystemExit("FAIL: latest total does not match Z.1")
    if [int(latest[k]) for k in CATEGORIES] != [6893476, 1393709, 154189]:
        raise SystemExit("FAIL: latest category split does not match Z.1")

    print(
        f"PASS: {len(rows)} quarterly fund-type rows; "
        f"{rows[0]['quarter_label']} to {latest['quarter_label']}; "
        f"max category reconciliation difference USD {max_abs_diff}m."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
