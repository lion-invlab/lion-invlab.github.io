#!/usr/bin/env python3
"""Normalize OFR MMF repo collateral, tenor, and counterparty dimensions."""
from __future__ import annotations
import csv, gzip, json, sys, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "us-mmf" / "raw"
OUT = ROOT / "data" / "us-mmf" / "fed_mmf_ofr_repo_dimensions_latest.csv"
RAW = sorted(RAW_DIR.glob("ofr_mmf_dataset_*.json.gz"))
if not RAW:
    raise SystemExit("No archived OFR MMF gzip snapshot found")
raw_path = RAW[-1]
with gzip.open(raw_path, "rt", encoding="utf-8") as f:
    payload = json.load(f)
series = payload["timeseries"]

groups = {
    "counterparty": {
        "MMF-MMF_RP_wDFI-M": "U.S. financial institutions",
        "MMF-MMF_RP_wFFI-M": "Foreign financial institutions",
        "MMF-MMF_RP_wFICC-M": "FICC-cleared",
        "MMF-MMF_RP_wFR-M": "Federal Reserve",
        "MMF-MMF_RP_wOCP-M": "Other counterparties",
    },
    "tenor": {
        "MMF-MMF_RP_OO-M": "Overnight / open",
        "MMF-MMF_RP_LE30-M": "Term: 2–30 days",
        "MMF-MMF_RP_G30-M": "Term: >30 days",
    },
    "collateral": {
        "MMF-MMF_RP_T_TOT-M": "U.S. Treasury collateral",
        "MMF-MMF_RP_AG_TOT-M": "Agency / GSE collateral",
        "MMF-MMF_RP_OA_TOT-M": "Other collateral",
    },
}
total_key = "MMF-MMF_RP_TOT-M"
required = {total_key} | {k for g in groups.values() for k in g}
missing = required - set(series)
if missing:
    raise SystemExit(f"Missing required OFR repo series: {sorted(missing)}")

values = {}
for key in required:
    obs = series[key].get("timeseries", {}).get("aggregation")
    if not isinstance(obs, list) or not obs:
        raise SystemExit(f"No aggregation observations for {key}")
    values[key] = {str(d): float(v) for d, v in obs if d and v is not None}

total_dates = set(values[total_key])
rows = []
qa = {}
for dimension, members in groups.items():
    common = sorted(total_dates.intersection(*(set(values[k]) for k in members)))
    if not common:
        raise SystemExit(f"No common observations for {dimension}")
    max_diff = 0.0
    for date in common:
        total = values[total_key][date]
        subtotal = sum(values[k][date] for k in members)
        diff = subtotal - total
        max_diff = max(max_diff, abs(diff))
        if abs(diff) > 1.0:
            raise SystemExit(f"{dimension} fails repo-total reconciliation at {date}: {diff}")
    qa[dimension] = {
        "common_observations": len(common),
        "first_common_date": common[0],
        "latest_common_date": common[-1],
        "max_abs_reconciliation_difference_usd": max_diff,
    }
    for key, label in members.items():
        for date, value in sorted(values[key].items()):
            if date not in total_dates:
                continue
            total = values[total_key][date]
            rows.append({
                "date": date,
                "dimension": dimension,
                "category": label,
                "mnemonic": key,
                "value_usd": f"{value:.2f}",
                "value_usd_trillion": f"{value / 1e12:.9f}",
                "share_of_repo_total": f"{value / total:.9f}" if total else "0",
                "complete_dimension_month": str(date in common).lower(),
            })

OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(sorted(rows, key=lambda r: (r["dimension"], r["date"], r["category"])))
manifest_path = ROOT / "data" / "us-mmf" / "latest_manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest.setdefault("ofr", {})["repo_dimensions"] = {
    "status": "downloaded_normalized_and_reconciled",
    "normalized_file": str(OUT.relative_to(ROOT)),
    "normalized_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
    "raw_source_snapshot": str(raw_path.relative_to(ROOT)),
    "rows": len(rows),
    "repo_total_observations": len(total_dates),
    "dimensions": qa,
    "note": "Counterparty, collateral, and tenor are separate overlapping classifications of the same repo holdings; never sum across dimensions.",
}
manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8")
print(json.dumps({"source": raw_path.name, "output": str(OUT.relative_to(ROOT)), "rows": len(rows), "repo_total_observations": len(total_dates), "qa": qa}, indent=2))
