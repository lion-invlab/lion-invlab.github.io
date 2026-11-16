#!/usr/bin/env python3
"""Download free public U.S. MMF source data and archive immutable snapshots.

No API keys or paid subscriptions are required.
The script deliberately stores OFR's complete raw JSON response before any
series selection, so subsequent mapping decisions remain auditable.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "us-mmf"
RAW_DIR = DATA_DIR / "raw"
FRED_SERIES = "MMMFFAQ027S"
FRED_URL = (
    "https://fred.stlouisfed.org/graph/fredgraph.csv"
    f"?id={FRED_SERIES}&cosd=1974-01-01"
)
OFR_URL = "https://data.financialresearch.gov/v1/series/dataset?dataset=mmf"
USER_AGENT = "TAC-US-MMF-Research/1.0 (public-data archival)"


def fetch(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=90) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status} for {url}")
        return response.read()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def build_fred_clean_csv(raw: bytes) -> tuple[bytes, dict]:
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or "DATE" not in reader.fieldnames:
        raise ValueError(f"Unexpected FRED CSV header: {reader.fieldnames}")
    value_col = FRED_SERIES if FRED_SERIES in reader.fieldnames else next(
        (x for x in reader.fieldnames if x != "DATE"), None
    )
    if not value_col:
        raise ValueError("FRED CSV has no value column")

    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow([
        "fred_observation_date", "value_raw_millions_usd",
        "value_usd_trillion", "quarter_label"
    ])
    rows = []
    for row in reader:
        date = (row.get("DATE") or "").strip()
        raw_value = (row.get(value_col) or "").strip()
        if not date or raw_value in ("", ".", "NA", "nan"):
            continue
        value = float(raw_value)
        if value <= 0:
            continue
        year, month, _ = date.split("-")
        quarter = (int(month) - 1) // 3 + 1
        writer.writerow([
            date, f"{value:.0f}", f"{value / 1_000_000:.6f}",
            f"{year} Q{quarter}"
        ])
        rows.append((date, value))

    if not rows:
        raise ValueError("No positive FRED observations found")
    if rows[-1][0] < "2026-04-01":
        raise ValueError(f"FRED latest observation unexpectedly old: {rows[-1][0]}")
    return out.getvalue().encode("utf-8"), {
        "series_id": FRED_SERIES,
        "observation_count": len(rows),
        "first_positive_observation": rows[0][0],
        "latest_observation": rows[-1][0],
        "latest_value_raw_millions_usd": rows[-1][1],
    }


def main() -> None:
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    fred_raw = fetch(FRED_URL)
    fred_clean, fred_info = build_fred_clean_csv(fred_raw)
    fred_raw_path = RAW_DIR / f"fred_{FRED_SERIES}_{stamp}.csv"
    fred_clean_path = DATA_DIR / "fed_mmmffaq027s_latest.csv"
    write_bytes(fred_raw_path, fred_raw)
    write_bytes(fred_clean_path, fred_clean)

    ofr_raw = fetch(OFR_URL)
    # Validate JSON before archiving; retain the complete payload unchanged.
    ofr_obj = json.loads(ofr_raw.decode("utf-8"))
    if not isinstance(ofr_obj, dict) or "mmf" not in ofr_obj:
        raise ValueError("OFR API response does not contain the expected 'mmf' dataset")
    ofr_path = RAW_DIR / f"ofr_mmf_dataset_{stamp}.json"
    write_bytes(ofr_path, ofr_raw)

    manifest = {
        "retrieved_at_utc": fetched_at,
        "policy": "free_public_sources_only",
        "fred": {
            **fred_info,
            "source_url": FRED_URL,
            "raw_snapshot": str(fred_raw_path.relative_to(ROOT)),
            "processed_file": str(fred_clean_path.relative_to(ROOT)),
            "raw_sha256": sha256(fred_raw),
            "processed_sha256": sha256(fred_clean),
        },
        "ofr": {
            "dataset_key": "mmf",
            "source_url": OFR_URL,
            "raw_snapshot": str(ofr_path.relative_to(ROOT)),
            "raw_sha256": sha256(ofr_raw),
            "top_level_keys": sorted(ofr_obj.keys()),
        },
    }
    manifest_path = DATA_DIR / "latest_manifest.json"
    write_bytes(
        manifest_path,
        (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8"),
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
