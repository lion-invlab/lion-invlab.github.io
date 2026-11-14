#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, csv, datetime as dt, hashlib, io, json, urllib.request, zlib
from pathlib import Path

FJA_URL = "https://raw.githubusercontent.com/fja05680/dow-sp500-100-years/master/SP500.csv"
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=SP500"
EXPECTED_START = "1927-12-30"
MIN_ROWS = 24000
MIN_OVERLAP = 750
MIN_LATEST = "2026-11-10"

def download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "TAC-Chart3-data-builder/1.0"})
    with urllib.request.urlopen(req, timeout=120) as response:
        payload = response.read()
    if not payload:
        raise RuntimeError(f"Empty download: {url}")
    return payload

def parse_rows(payload: bytes, date_col: str, close_col: str):
    text = payload.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or date_col not in reader.fieldnames or close_col not in reader.fieldnames:
        raise ValueError(f"Unexpected CSV schema; expected {date_col}/{close_col}, got {reader.fieldnames}")
    out = {}
    for row in reader:
        date_text = (row.get(date_col) or "").strip()[:10]
        close_text = (row.get(close_col) or "").strip()
        if not date_text or not close_text or close_text == ".":
            continue
        date = dt.date.fromisoformat(date_text)
        close = float(close_text)
        if not (close > 0):
            raise ValueError(f"Non-positive close: {date_text}={close_text}")
        if date_text in out:
            raise ValueError(f"Duplicate date in source: {date_text}")
        out[date_text] = int(round(close * 100))
    if not out:
        raise ValueError(f"No valid rows in {date_col}/{close_col}")
    return out

def varint(value: int, output: bytearray):
    if value < 0:
        raise ValueError("varint cannot encode a negative value")
    while value >= 0x80:
        output.append((value & 0x7f) | 0x80)
        value >>= 7
    output.append(value)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    fja = parse_rows(download(FJA_URL), "Date", "Close")
    fred = parse_rows(download(FRED_URL), "observation_date", "SP500")
    overlap_dates = sorted(set(fja) & set(fred))
    if len(overlap_dates) < MIN_OVERLAP:
        raise ValueError(f"Insufficient FJA/FRED overlap: {len(overlap_dates)}")
    differences = []
    for day in overlap_dates:
        delta = abs(fja[day] - fred[day]) / 100
        if delta > 0.02:
            differences.append({"date": day, "fja_close": fja[day] / 100, "fred_close": fred[day] / 100, "abs_diff": round(delta, 4)})
    # Keep the long historical FJA series and let FRED replace every date in its official coverage.
    merged = dict(fja)
    merged.update(fred)
    rows = sorted(merged.items())
    if len(rows) < MIN_ROWS:
        raise ValueError(f"Unexpectedly short merged history: {len(rows)}")
    if rows[0][0] != EXPECTED_START:
        raise ValueError(f"Unexpected first date: {rows[0][0]}")
    if rows[-1][0] < MIN_LATEST:
        raise ValueError(f"Latest date too old: {rows[-1][0]}")
    # Canonical source hash: sorted Date,Close rows rounded to cents, no index column.
    canonical = "Date,Close\n" + "".join(f"{day},{cents / 100:.2f}\n" for day, cents in rows)
    source_sha256 = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    packed = bytearray()
    previous_day = dt.date.fromisoformat(rows[0][0]).toordinal()
    previous_close = 0
    for day_text, close_cents in rows:
        day_ordinal = dt.date.fromisoformat(day_text).toordinal()
        varint(day_ordinal - previous_day, packed)
        delta = close_cents - previous_close
        zigzag = 2 * delta if delta >= 0 else -2 * delta - 1
        varint(zigzag, packed)
        previous_day, previous_close = day_ordinal, close_cents
    compressed = zlib.compress(bytes(packed), level=9)
    result = {
        "schema_version": "1.0.0",
        "encoding": "zlib+base64",
        "fields": "per row: unsigned-varint day-gap from previous date ordinal; unsigned-varint zigzag(close delta in cents)",
        "start": rows[0][0],
        "end": rows[-1][0],
        "rows": len(rows),
        "close_scale": 100,
        "source_dataset_sha256": source_sha256,
        "source_details": {
            "long_history_source": FJA_URL,
            "recent_official_source": FRED_URL,
            "fja_rows": len(fja),
            "fred_rows": len(fred),
            "overlap_rows": len(overlap_dates),
            "overlap_differences_over_0_02_points": differences,
            "merge_rule": "FRED SP500 replaces FJA values on every overlapping/recent FRED date; no interpolation or forward-fill"
        },
        "payload": base64.b64encode(compressed).decode("ascii")
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "payload"} | {"compressed_bytes": len(compressed), "output_bytes": args.output.stat().st_size}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
