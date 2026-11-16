#!/usr/bin/env python3
"""Download and normalize free public U.S. MMF data from Federal Reserve Z.1.

The Z.1 S123.s table is the common source for total AUM and fund-type split.
Raw source snapshots are archived separately; normalized files are reproducible.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
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
FRED_URL = "https://fred.stlouisfed.org/data/MMMFFAQ027S"
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
    with urlopen(req, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status} for {url}")
        return response.read()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def parse_quarter(label: str) -> tuple[int, int, str]:
    year_text, quarter_text = label.split(":Q")
    year, quarter = int(year_text), int(quarter_text)
    if quarter not in (1, 2, 3, 4):
        raise ValueError(f"Invalid Z.1 quarter label: {label}")
    month = (quarter - 1) * 3 + 1
    return year, quarter, f"{year}-{month:02d}-01"


def normalize_z1_s123(raw_csv: bytes) -> tuple[bytes, bytes, dict]:
    reader = csv.DictReader(io.StringIO(raw_csv.decode("utf-8-sig")))
    required = {
        "date", "FL634090005.Q", "FL634090033.Q",
        "FL634090043.Q", "FL634090053.Q",
    }
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise ValueError(f"Unexpected Z.1 S123.s columns: {reader.fieldnames}")

    total_out = io.StringIO()
    total_writer = csv.writer(total_out, lineterminator="\n")
    total_writer.writerow([
        "fred_observation_date", "value_raw_millions_usd",
        "value_usd_trillion", "quarter_label",
    ])

    type_out = io.StringIO()
    type_writer = csv.writer(type_out, lineterminator="\n")
    type_writer.writerow([
        "date", "quarter_label", "total_aum_millions_usd",
        "government_millions_usd", "prime_millions_usd",
        "tax_exempt_millions_usd", "category_sum_millions_usd",
        "difference_millions_usd",
    ])

    total_rows, type_rows, max_abs_diff = 0, 0, 0
    first_total, last_total, first_types, last_types = None, None, None, None

    for row in reader:
        label = (row.get("date") or "").strip()
        if not label or ":Q" not in label:
            continue
        year, quarter, iso_date = parse_quarter(label)
        total_raw = (row.get("FL634090005.Q") or "").strip()
        if total_raw not in ("", ".", "ND"):
            total = int(float(total_raw))
            if total > 0:
                total_writer.writerow([
                    iso_date, total, f"{total / 1_000_000:.6f}",
                    f"{year} Q{quarter}",
                ])
                total_rows += 1
                first_total = first_total or iso_date
                last_total = iso_date

        if (year, quarter) >= (2010, 4):
            vals = [
                int(float((row.get(code) or "0").strip() or "0"))
                for code in (
                    "FL634090033.Q", "FL634090043.Q", "FL634090053.Q",
                )
            ]
            gov, prime, tax_exempt = vals
            if total_raw in ("", ".", "ND"):
                raise ValueError(f"Missing total AUM for fund-type row {label}")
            total = int(float(total_raw))
            category_sum = gov + prime + tax_exempt
            diff = category_sum - total
            if abs(diff) > 1:
                raise ValueError(
                    f"Z.1 category split fails reconciliation at {label}: {diff}m"
                )
            type_writer.writerow([
                iso_date, f"{year} Q{quarter}", total, gov, prime,
                tax_exempt, category_sum, diff,
            ])
            type_rows += 1
            first_types = first_types or iso_date
            last_types = iso_date
            max_abs_diff = max(max_abs_diff, abs(diff))

    if total_rows != 210 or last_total != "2026-04-01":
        raise ValueError(
            f"Unexpected Z.1 total history: {total_rows} rows, last={last_total}"
        )
    if type_rows != 63 or last_types != "2026-04-01":
        raise ValueError(
            f"Unexpected Z.1 category history: {type_rows} rows, last={last_types}"
        )

    return total_out.getvalue().encode(), type_out.getvalue().encode(), {
        "total_observations": total_rows,
        "total_first_observation": first_total,
        "total_latest_observation": last_total,
        "category_observations": type_rows,
        "category_first_observation": first_types,
        "category_latest_observation": last_types,
        "max_category_reconciliation_difference_millions_usd": max_abs_diff,
    }


def normalize_z1_s123_transactions(raw_csv: bytes) -> tuple[bytes, dict]:
    """Normalize S123.t net acquisition transactions; retain SAAR units."""
    reader = csv.DictReader(io.StringIO(raw_csv.decode("utf-8-sig")))
    required = {"date", "FA634090005.Q"}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise ValueError(f"Unexpected Z.1 S123.t columns: {reader.fieldnames}")

    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["date", "quarter_label", "net_acquisition_millions_usd_saar", "net_acquisition_usd_trillion_saar"])
    rows, first_date, last_date = 0, None, None
    for row in reader:
        label = (row.get("date") or "").strip()
        if not label or ":Q" not in label:
            continue
        year, quarter, iso_date = parse_quarter(label)
        raw = (row.get("FA634090005.Q") or "").strip()
        if raw in ("", ".", "ND"):
            continue
        value = int(float(raw))
        writer.writerow([iso_date, f"{year} Q{quarter}", value, f"{value / 1_000_000:.6f}"])
        rows += 1
        first_date = first_date or iso_date
        last_date = iso_date

    if rows < 4 or not last_date:
        raise ValueError(f"Unexpectedly short S123.t transaction history: {rows}")
    return out.getvalue().encode(), {
        "observations": rows, "first_observation": first_date, "latest_observation": last_date,
        "series_id": "MMMFTAQ027S", "series_code": "FA634090005",
        "units": "Millions of U.S. dollars, seasonally adjusted annual rate",
        "interpretation": "Net acquisition of financial assets by money market funds; financial-account transactions, not investor net subscriptions/redemptions.",
    }


def main() -> None:
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Federal Reserve Z.1 official release CSV package.
    z1_raw = fetch(Z1_CSV_URL)
    z1_path = RAW_DIR / f"fed_z1_csv_package_{stamp}.zip"
    write_bytes(z1_path, z1_raw)
    with zipfile.ZipFile(io.BytesIO(z1_raw)) as archive:
        z1_names = archive.namelist()
        s123_name = next(
            (n for n in z1_names if n.lower().endswith("/s123_s.csv")),
            None,
        )
        s123_t_name = next(
            (n for n in z1_names if n.lower().endswith("/s123_t.csv")),
            None,
        )
        if not s123_name or not s123_t_name:
            raise ValueError("Z.1 CSV package must contain both S123_s.csv and S123_t.csv")
        s123_raw = archive.read(s123_name)
        s123_t_raw = archive.read(s123_t_name)

    s123_path = RAW_DIR / f"fed_z1_S123_s_{stamp}.csv"
    s123_t_path = RAW_DIR / f"fed_z1_S123_t_{stamp}.csv"
    write_bytes(s123_path, s123_raw)
    write_bytes(s123_t_path, s123_t_raw)
    total_csv, types_csv, z1_stats = normalize_z1_s123(s123_raw)
    transactions_csv, transaction_stats = normalize_z1_s123_transactions(s123_t_raw)
    transactions_path = DATA_DIR / "fed_mmf_transactions_latest.csv"
    write_bytes(transactions_path, transactions_csv)

    total_path = DATA_DIR / "fed_mmmffaq027s_latest.csv"
    types_path = DATA_DIR / "fed_mmf_aum_by_fund_type_latest.csv"
    write_bytes(total_path, total_csv)
    write_bytes(types_path, types_csv)

    z1_info = {
        "status": "downloaded_and_normalized",
        "source_url": Z1_CSV_URL,
        "table": "S123.s",
        "table_member": s123_name,
        "raw_zip_snapshot": str(z1_path.relative_to(ROOT)),
        "raw_zip_sha256": sha256(z1_raw),
        "raw_table_snapshot": str(s123_path.relative_to(ROOT)),
        "raw_table_sha256": sha256(s123_raw),
        "normalized_total_file": str(total_path.relative_to(ROOT)),
        "normalized_total_sha256": sha256(total_csv),
        "normalized_fund_type_file": str(types_path.relative_to(ROOT)),
        "normalized_fund_type_sha256": sha256(types_csv),
        "archive_member_count": len(z1_names),
        **z1_stats,
    }
    z1_transactions_info = {
        "status": "downloaded_and_normalized",
        "source_url": Z1_CSV_URL,
        "table": "S123.t",
        "table_member": s123_t_name,
        "raw_table_snapshot": str(s123_t_path.relative_to(ROOT)),
        "raw_table_sha256": sha256(s123_t_raw),
        "normalized_file": str(transactions_path.relative_to(ROOT)),
        "normalized_sha256": sha256(transactions_csv),
        **transaction_stats,
    }

    fed_efa_info = {}
    for category, url in FED_EFA_URLS.items():
        try:
            payload = fetch(url)
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
        ofr_json_bytes = (
            gzip.decompress(ofr_raw)
            if ofr_raw.startswith(bytes([31, 139]))
            else ofr_raw
        )
        ofr_obj = json.loads(ofr_json_bytes.decode("utf-8"))
        if not isinstance(ofr_obj, dict) or "timeseries" not in ofr_obj:
            raise ValueError("OFR API response does not contain dataset timeseries")
        ofr_path = RAW_DIR / f"ofr_mmf_dataset_{stamp}.json.gz"
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
        ofr_info.update({"status": "download_failed", "error": repr(exc)})

    manifest = {
        "retrieved_at_utc": fetched_at,
        "github_actions_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_actions_run_url": (
            f"https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/{os.environ.get('GITHUB_RUN_ID')}"
            if os.environ.get("GITHUB_RUN_ID") else None
        ),
        "policy": "free_public_sources_only",
        "fed_z1_release": z1_info,
        "fed_z1_transactions": z1_transactions_info,
        "fred_crosscheck_reference": {
            "series_id": "MMMFFAQ027S",
            "url": FRED_URL,
            "note": "The normalized primary data are parsed from the Federal Reserve Z.1 S123.s CSV package; FRED is a cross-check reference.",
        },
        "fed_efa_monthly_holdings_by_type": {
            "source_page": "https://www.federalreserve.gov/releases/efa/efa-project-money-market-funds-investment-holdings-detail.htm",
            "coverage_expected_from": "2010-12",
            "files": fed_efa_info,
            "note": "Portfolio investment holdings by fund type; separate from Z.1 total financial assets.",
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
