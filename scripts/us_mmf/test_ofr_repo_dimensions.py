#!/usr/bin/env python3
"""QA for OFR MMF repo dimension normalization."""
import csv, sys
from collections import defaultdict
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else "data/us-mmf/fed_mmf_ofr_repo_dimensions_latest.csv")
rows = list(csv.DictReader(path.open(encoding="utf-8")))
assert rows, "No normalized repo dimension rows"
by_dim_date = defaultdict(dict)
for row in rows:
    by_dim_date[(row["dimension"], row["date"])][row["mnemonic"]] = float(row["value_usd"])
expected = {
    "tenor": {"MMF-MMF_RP_OO-M", "MMF-MMF_RP_LE30-M", "MMF-MMF_RP_G30-M"},
    "collateral": {"MMF-MMF_RP_T_TOT-M", "MMF-MMF_RP_AG_TOT-M", "MMF-MMF_RP_OA_TOT-M"},
    "counterparty": {"MMF-MMF_RP_wDFI-M", "MMF-MMF_RP_wFFI-M", "MMF-MMF_RP_wFICC-M", "MMF-MMF_RP_wFR-M", "MMF-MMF_RP_wOCP-M"},
}
for dim, members in expected.items():
    dates = sorted(d for d in {date for d, x in by_dim_date if d == dim} if set(by_dim_date[(dim,d)]) == members)
    assert dates, f"No complete dates for {dim}"
    assert dates[-1] == "2026-09-30", f"{dim} latest date mismatch: {dates[-1]}"
    for date in dates:
        total = sum(by_dim_date[(dim,date)].values())
        # Compare with the canonical repo total stored in the row shares.
        dim_rows = [r for r in rows if r["dimension"] == dim and r["date"] == date]
        implied = [float(r["value_usd"]) / float(r["share_of_repo_total"]) for r in dim_rows if float(r["share_of_repo_total"]) > 0]
        assert implied and max(implied) - min(implied) <= 2.0, f"Inconsistent repo total implied by {dim} at {date}"
        assert abs(total - implied[0]) <= 2.0, f"{dim} does not reconcile at {date}"
    print(f"PASS {dim}: {len(dates)} fully reconciled months, {dates[0]} to {dates[-1]}")
latest = {r["mnemonic"]: r for r in rows if r["date"] == "2026-09-30"}
for key in expected["counterparty"] | expected["tenor"] | expected["collateral"]:
    assert key in latest, f"Missing latest series {key}"
print(f"PASS latest categories: {len(latest)}")
