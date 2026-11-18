#!/usr/bin/env python3
"""Convert a user-supplied Investing.com S&P 500 CSV export into Chart 3 compact data.

This is an explicit import utility, not an unattended website scraper.
"""
from __future__ import annotations
import argparse, base64, csv, datetime as dt, hashlib, json, zlib
from pathlib import Path
from urllib.parse import urlparse

DATE_FORMATS = ("%b %d, %Y", "%d %b %Y", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d")
DEFAULT_COMPACT_PATH = Path("data/tac-chart3/sp500_investing_daily.compact.json")
DEFAULT_PROVENANCE_PATH = Path("data/tac-chart3/sp500_investing_daily.provenance.json")

def varint(value: int) -> bytes:
    if value < 0:
        raise ValueError("varint only accepts non-negative integers")
    out = bytearray()
    while value >= 128:
        out.append((value & 127) | 128)
        value >>= 7
    out.append(value)
    return bytes(out)

def parse_date(value: str) -> dt.date:
    value = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return dt.datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Unsupported date value: {value!r}")

def parse_close(value: str) -> int:
    normalized = value.strip().replace(",", "").replace("$", "")
    if not normalized or normalized in {"-", "--", "N/A"}:
        raise ValueError("S&P 500 close contains a missing value")
    try:
        cents = round(float(normalized) * 100)
    except ValueError as exc:
        raise ValueError(f"Invalid S&P 500 close value: {value!r}") from exc
    if cents <= 0:
        raise ValueError(f"S&P 500 close must be positive: {value!r}")
    return cents

def convert(csv_path: Path, compact_path: Path, provenance_path: Path,
            source_url: str, retrieved_at: str, date_column: str = "Date",
            close_column: str = "Price") -> dict:
    parsed_url = urlparse(source_url)
    host = (parsed_url.hostname or "").lower()
    if parsed_url.scheme != "https" or (host != "investing.com" and not host.endswith(".investing.com")):
        raise ValueError("Source URL must be an HTTPS Investing.com URL")
    if "us-spx-500" not in parsed_url.path.lower():
        raise ValueError("Source URL must identify the Investing.com S&P 500 cash-index history page")
    try:
        retrieval_stamp = dt.datetime.fromisoformat(retrieved_at.replace("Z", "+00:00"))
        if retrieval_stamp.tzinfo is None or retrieval_stamp.utcoffset() is None:
            raise ValueError("timezone missing")
    except ValueError as exc:
        raise ValueError("retrieved_at must be a timezone-aware ISO-8601 timestamp") from exc

    raw = csv_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(text.splitlines())
    if not reader.fieldnames or date_column not in reader.fieldnames or close_column not in reader.fieldnames:
        raise ValueError(f"CSV must contain columns {date_column!r} and {close_column!r}")

    rows = []
    seen = set()
    for line_no, row in enumerate(reader, start=2):
        day = parse_date(row.get(date_column) or "")
        cents = parse_close(row.get(close_column) or "")
        if day in seen:
            raise ValueError(f"Duplicate S&P 500 date {day.isoformat()} at CSV line {line_no}")
        seen.add(day)
        rows.append((day, cents))
    if not rows:
        raise ValueError("CSV contains no S&P 500 observations")
    rows.sort(key=lambda item: item[0])

    packed = bytearray()
    previous_day = rows[0][0].toordinal()
    previous_close = 0
    for day, cents in rows:
        ordinal = day.toordinal()
        gap = ordinal - previous_day
        delta = cents - previous_close
        zigzag = 2 * delta if delta >= 0 else -2 * delta - 1
        packed.extend(varint(gap))
        packed.extend(varint(zigzag))
        previous_day, previous_close = ordinal, cents

    compact = {
        "schema_version": "1.0.0",
        "encoding": "zlib+base64",
        "start": rows[0][0].isoformat(),
        "end": rows[-1][0].isoformat(),
        "rows": len(rows),
        "payload": base64.b64encode(zlib.compress(bytes(packed))).decode("ascii"),
        "source_dataset_sha256": digest,
    }
    provenance = {
        "source": "Investing.com",
        "source_url": source_url,
        "retrieved_at": retrieved_at,
        "source_sha256": digest,
        "method": "manual_csv_export_import",
        "source_filename": csv_path.name,
        "source_observation_date": rows[-1][0].isoformat(),
    }
    compact_path.parent.mkdir(parents=True, exist_ok=True)
    provenance_path.parent.mkdir(parents=True, exist_ok=True)
    compact_path.write_text(json.dumps(compact, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    provenance_path.write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"rows": len(rows), "start": compact["start"], "end": compact["end"], "source_sha256": digest}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--compact", type=Path, default=DEFAULT_COMPACT_PATH)
    parser.add_argument("--provenance", type=Path, default=DEFAULT_PROVENANCE_PATH)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--retrieved-at", required=True)
    parser.add_argument("--date-column", default="Date")
    parser.add_argument("--close-column", default="Price")
    args = parser.parse_args()
    print(json.dumps(convert(args.csv, args.compact, args.provenance, args.source_url,
                             args.retrieved_at, args.date_column, args.close_column),
                     ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
