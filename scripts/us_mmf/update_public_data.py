#!/usr/bin/env python3
"""Download free public U.S. MMF source data and archive immutable snapshots.

No API keys or paid subscriptions are required.
The script deliberately stores OFR's complete raw JSON response before any
series selection, so subsequent mapping decisions remain auditable.
"""
from __future__ import annotations

import csv
import hashlib
import gzip
import io
import json
import os
import zipfile
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
Z1_CSV_URL = "https://www.federalreserve.gov/releases/z1/current/z1_csv_files.zip"
OFR_URL = "https://data.financialresearch.gov/v1/series/dataset?dataset=mmf"
FED_EFA_URLS = {
    "total": "https://www.federalreserve.gov/releases/efa/total-money-market-funds-investment-holdings-historical.csv",
    "prime": "https://www.federalreserve.gov/releases/efa/prime-money-market-funds-investment-holdings-historical.csv",
    "government": "https://www.federalreserve.gov/releases/efa/government-money-market-funds-investment-holdings-historical.csv",
    "tax_exempt": "https://www.federalreserve.gov/releases/efa/exempt-money-market-funds-investment-holdings-historical.csv",
}
USER_AGENT = "TAC-US-MMF-Research/1.0 (public-data archival)"


def fetch(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    print(f"Fetching public source: {url}", flush=True)
    with urlopen(req, timeout=25) as response:
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
    if not reader.fieldnames:
        raise ValueError("FRED CSV is missing its header")
    date_col = next(
        (x for x in reader.fieldnames if x.strip().lower() in ("date", "observation_date")),
        None,
    )
    if not date_col:
        raise ValueError(f"Unexpected FRED CSV date column: {reader.fieldnames}")
    value_col = next(
        (x for x in reader.fieldnames if x != date_col and x.strip() == FRED_SERIES),
        None,
    ) or next((x for x in reader.fieldnames if x != date_col), None)
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
        date = (row.get(date_col) or "").strip()
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

    # Archive the Federal Reserve's official Z.1 CSV package. FRED's graph CSV
    # endpoint has timed out from the runner, so use the Board's own release files.
    z1_raw = fetch(Z1_CSV_URL)
    z1_path = RAW_DIR / f"fed_z1_csv_package_{stamp}.zip"
    write_bytes(z1_path, z1_raw)
    with zipfile.ZipFile(io.BytesIO(z1_raw)) as archive:
        z1_names = archive.namelist()
        s123_candidates = [
            name for name in z1_names
            if "S123" in Path(name).name.upper() and name.lower().endswith(".csv")
        ]
        extracted_s123 = []
        for name in s123_candidates:
            target = RAW_DIR / f"fed_z1_{Path(name).name}_{stamp}"
            write_bytes(target, archive.read(name))
            extracted_s123.append(str(target.relative_to(ROOT)))

    # Until the official Z.1 CSV table is parsed into the normalized series,
    # retain the independently checked 1974Q1-2026Q2 FRED table snapshot.
    fallback = DATA_DIR / "fed_mmmffaq027s_1974q1_2026q2.csv"
    fallback_bytes = fallback.read_bytes()
    fred_clean_path = DATA_DIR / "fed_mmmffaq027s_latest.csv"
    write_bytes(fred_clean_path, fallback_bytes)
    fred_info = {
        "status": "verified_branch_snapshot_pending_z1_csv_parser",
        "series_id": FRED_SERIES,
        "source_url": FRED_URL,
        "processed_file": str(fred_clean_path.relative_to(ROOT)),
        "processed_sha256": sha256(fallback_bytes),
        "note": "Existing historical snapshot retained; live FRED graph CSV endpoint timed out. Official Z.1 CSV package archived separately.",
    }
    z1_info = {
        "status": "downloaded",
        "source_url": Z1_CSV_URL,
        "raw_snapshot": str(z1_path.relative_to(ROOT)),
        "raw_sha256": sha256(z1_raw),
        "size_bytes": len(z1_raw),
        "archive_member_count": len(z1_names),
        "s123_csv_members": s123_candidates,
        "extracted_s123_files": extracted_s123,
    }

    fed_efa_info = {}
    for category, url in FED_EFA_URLS.items():
        try:
            payload = fetch(url)
            # Preserve the source CSV bytes unchanged; parsing and summation are a later QA stage.
            path = RAW_DIR / f"fed_efa_{category}_{stamp}.csv"
            write_bytes(path, payload)
            fed_efa_info[category] = {
                "status": "downloaded",
                "source_url": url,
                "raw_snapshot": str(path.relative_to(ROOT)),
                "raw_sha256": sha256(payload),
                "size_bytes": len(payload),
            }
        except Exception as exc:
            fed_efa_info[category] = {
                "status": "download_failed",
                "source_url": url,
                "error": repr(exc),
            }

    ofr_info = {"dataset_key": "mmf", "source_url": OFR_URL}
    try:
        ofr_raw = fetch(OFR_URL)
        # OFR serves the API payload with gzip content encoding.
        ofr_json_bytes = gzip.decompress(ofr_raw) if ofr_raw[:2] == b"\\x1f\\x8b" else ofr_raw
        ofr_obj = json.loads(ofr_json_bytes.decode("utf-8"))
        if not isinstance(ofr_obj, dict) or "timeseries" not in ofr_obj:
            raise ValueError("OFR API response does not contain the expected dataset timeseries object")
        ofr_path = RAW_DIR / f"ofr_mmf_dataset_{stamp}.json"
        write_bytes(ofr_path, ofr_raw)
        ofr_info.update({
            "status": "downloaded",
            "raw_snapshot": str(ofr_path.relative_to(ROOT)),
            "raw_sha256": sha256(ofr_raw),
            "decompressed_sha256": sha256(ofr_json_bytes),
            "top_level_keys": sorted(ofr_obj.keys()),
            "series_count": len(ofr_obj.get("timeseries", {})),
        })
    except Exception as exc:
        # Keep the Fed dataset and its QA usable if the separate OFR service is temporarily unavailable.
        ofr_info.update({"status": "download_failed", "error": repr(exc)})

    manifest = {
        "retrieved_at_utc": fetched_at,
        "policy": "free_public_sources_only",
        "fed_z1_release": z1_info,
        "fred_reference_series": fred_info,
        "fed_efa_monthly_holdings_by_type": {
            "source_page": "https://www.federalreserve.gov/releases/efa/efa-project-money-market-funds-investment-holdings-detail.htm",
            "coverage_expected_from": "2010-12",
            "files": fed_efa_info,
            "note": "These are portfolio investment holdings by type, not the Z.1 total financial assets series; Federal Reserve notes scope differences.",
        },
        "ofr": ofr_info,
    }
    manifest_path = DATA_DIR / "latest_manifest.json"
    write_bytes(
        manifest_path,
        (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8"),
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
