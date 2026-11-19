#!/usr/bin/env python3
"""Merge verified append-only S&P 500 daily observations into Chart 3 compact data."""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import subprocess
import zlib
from pathlib import Path

def canonical(value: dict) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")

def read_varint(raw: bytes, offset: int):
    value, shift = 0, 0
    while True:
        if offset >= len(raw) or shift > 49:
            raise ValueError("S&P 500 compact varint truncated or overflow")
        byte = raw[offset]
        offset += 1
        value += (byte & 127) * (2 ** shift)
        if not (byte & 128):
            return value, offset
        shift += 7

def write_varint(value: int, output: bytearray):
    if value < 0:
        raise ValueError("varint cannot encode a negative value")
    while value >= 0x80:
        output.append((value & 0x7f) | 0x80)
        value >>= 7
    output.append(value)

def decode_compact(path: Path):
    compact = json.loads(path.read_text(encoding="utf-8"))
    if compact.get("schema_version") != "1.0.0" or compact.get("encoding") != "zlib+base64":
        raise ValueError("Unexpected recent compact S&P 500 schema")
    raw = zlib.decompress(base64.b64decode(compact["payload"]))
    offset = 0
    day_ordinal = dt.date.fromisoformat(compact["start"]).toordinal()
    close_cents = 0
    rows = []
    for _ in range(int(compact["rows"])):
        gap, offset = read_varint(raw, offset)
        day_ordinal += gap
        zigzag, offset = read_varint(raw, offset)
        delta = zigzag // 2 if zigzag % 2 == 0 else -(zigzag // 2) - 1
        close_cents += delta
        rows.append((dt.date.fromordinal(day_ordinal).isoformat(), close_cents))
    if offset != len(raw) or len(rows) != int(compact["rows"]):
        raise ValueError("Recent compact S&P 500 row count or payload length mismatch")
    if rows[0][0] != compact["start"] or rows[-1][0] != compact["end"]:
        raise ValueError("Recent compact S&P 500 first/last date mismatch")
    if any(rows[i][0] >= rows[i+1][0] for i in range(len(rows)-1)):
        raise ValueError("Recent compact S&P 500 dates are not strictly increasing")
    return rows, compact

def encode_compact(rows: list[tuple[str, int]], previous: dict):
    if not rows or any(rows[i][0] >= rows[i+1][0] for i in range(len(rows)-1)):
        raise ValueError("Merged S&P 500 observations must be nonempty and strictly ascending")
    canonical_csv = "Date,Close\n" + "".join(f"{day},{cents / 100:.2f}\n" for day, cents in rows)
    dataset_sha = hashlib.sha256(canonical_csv.encode("utf-8")).hexdigest()
    packed = bytearray()
    prev_day = dt.date.fromisoformat(rows[0][0]).toordinal()
    prev_close = 0
    for day_text, close_cents in rows:
        day_ordinal = dt.date.fromisoformat(day_text).toordinal()
        write_varint(day_ordinal - prev_day, packed)
        delta = close_cents - prev_close
        write_varint(2 * delta if delta >= 0 else -2 * delta - 1, packed)
        prev_day, prev_close = day_ordinal, close_cents
    return {
        "schema_version": "1.0.0",
        "encoding": "zlib+base64",
        "fields": previous["fields"],
        "start": rows[0][0],
        "end": rows[-1][0],
        "rows": len(rows),
        "close_scale": 100,
        "source_dataset_sha256": dataset_sha,
        "payload": base64.b64encode(zlib.compress(bytes(packed), level=9)).decode("ascii"),
    }

def load_increment_ledger(path: Path):
    raw = path.read_bytes()
    rows, seen = [], set()
    for line_no, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        digest = row.get("record_sha256")
        body = {k: v for k, v in row.items() if k != "record_sha256"}
        if digest != hashlib.sha256(canonical(body)).hexdigest():
            raise ValueError(f"Increment ledger SHA-256 mismatch at line {line_no}")
        day = row.get("observation_date")
        if day in seen:
            raise ValueError(f"Duplicate increment date: {day}")
        seen.add(day)
        if row.get("series_id") != "SP500" or row.get("instrument") != "S&P 500 cash price index":
            raise ValueError(f"Invalid S&P 500 instrument at line {line_no}")
        note = (row.get("source_note") or "").lower()
        if "cfd" in note and "非cfd" not in note:
            raise ValueError(f"CFD observation is prohibited at line {line_no}")
        if row.get("source_name") != "Yahoo Finance S&P 500 (^GSPC) Historical Data":
            raise ValueError(f"Unexpected increment source at line {line_no}")
        if row.get("source_url") != "https://finance.yahoo.com/quote/%5EGSPC/history/":
            raise ValueError(f"Unexpected Yahoo Finance source URL at line {line_no}")
        stamp = dt.datetime.fromisoformat(row["observed_at"])
        if stamp.utcoffset() != dt.timedelta(hours=8):
            raise ValueError(f"Invalid Taipei observation timestamp at line {line_no}")
        if stamp.date().isoformat() != row.get("report_date"):
            raise ValueError(f"Report date does not match observed_at at line {line_no}")
        rows.append((day, int(round(float(row["close"]) * 100))))
    if not rows or any(rows[i][0] >= rows[i+1][0] for i in range(len(rows)-1)):
        raise ValueError("Increment ledger must be nonempty and strictly ascending")
    return rows, raw

def merge_recent(recent_path: Path, ledger_path: Path):
    base_rows, compact = decode_compact(recent_path)
    increments, ledger_raw = load_increment_ledger(ledger_path)
    last_day = base_rows[-1][0]
    if any(day <= last_day for day, _ in increments):
        raise ValueError("Increment ledger contains dates already present in the recent compact baseline")
    if len({d for d, _ in base_rows + increments}) != len(base_rows) + len(increments):
        raise ValueError("Duplicate dates between baseline and increment ledger")
    merged = base_rows + increments
    result = encode_compact(merged, compact)
    recent_path.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return result, ledger_raw, increments

def git_blob_sha1(path: Path):
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\\0" + data).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=Path("data/tac-chart3"))
    ap.add_argument("--builder", type=Path, default=Path(".github/scripts/build_sp500_daily_compact.py"))
    args = ap.parse_args()
    recent = args.data_dir / "sp500_daily_close_1993-2026.compact.json"
    full = args.data_dir / "sp500_daily_close_1927-2026.compact.json"
    ledger = args.data_dir / "sp500_daily_increment.jsonl"
    manifest_path = args.data_dir / "manifest.json"
    result, ledger_raw, increments = merge_recent(recent, ledger)
    subprocess.run(["python", str(args.builder), "--recent-compact", str(recent),
                    "--output", str(full)], check=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sp = manifest.setdefault("sp500_data", {})
    full_compact = json.loads(full.read_text(encoding="utf-8"))
    sp.update({
        "path": str(full),
        "git_blob_sha1": git_blob_sha1(full),
        "dataset_sha256": full_compact["source_dataset_sha256"],
        "start": full_compact["start"],
        "end": full_compact["end"],
        "rows": full_compact["rows"],
        "encoding": full_compact["encoding"],
        "recent_snapshot_source": "Validated FJA/FRED compact baseline through 2026-11-10 plus verified Yahoo Finance ^GSPC historical Close increments through 2026-11-18.",
        "merge_rule": "Use FJA observations strictly before 1993-12-31; retain validated recent compact observations and append only SHA-256-verified daily increments; no interpolation or forward-fill.",
        "increment_ledger": {
            "path": str(ledger),
            "sha256": hashlib.sha256(ledger_raw).hexdigest(),
            "first": increments[0][0],
            "last": increments[-1][0],
            "rows": len(increments),
            "source_name": "Yahoo Finance S&P 500 (^GSPC) Historical Data",
            "source_url": "https://finance.yahoo.com/quote/%5EGSPC/history/",
            "observed_at": json.loads(ledger_raw.decode("utf-8").splitlines()[-1])["observed_at"],
        },
    })
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"recent_end": result["end"], "recent_rows": result["rows"],
                      "full_end": full_compact["end"], "full_rows": full_compact["rows"],
                      "increment_rows": len(increments), "ledger_sha256": hashlib.sha256(ledger_raw).hexdigest()},
                     ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
