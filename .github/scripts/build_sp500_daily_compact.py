#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, csv, datetime as dt, hashlib, io, json, urllib.request, zlib
from pathlib import Path

FJA_URL = "https://raw.githubusercontent.com/fja05680/dow-sp500-100-years/master/SP500.csv"
EXPECTED_START = "1927-12-30"
EXPECTED_RECENT_START = "1993-12-31"
MIN_ROWS = 24000
MIN_LATEST = "2026-11-10"

def download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "TAC-Chart3-data-builder/1.0"})
    with urllib.request.urlopen(req, timeout=120) as response:
        payload = response.read()
    if not payload:
        raise RuntimeError(f"Empty download: {url}")
    return payload

def parse_fja(payload: bytes):
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
    if not reader.fieldnames or "Date" not in reader.fieldnames or "Close" not in reader.fieldnames:
        raise ValueError(f"Unexpected FJA CSV schema: {reader.fieldnames}")
    out = {}
    for row in reader:
        day = (row.get("Date") or "").strip()[:10]
        raw = (row.get("Close") or "").strip()
        if not day or not raw or raw == ".":
            continue
        dt.date.fromisoformat(day)
        cents = int(round(float(raw) * 100))
        if cents <= 0 or day in out:
            raise ValueError(f"Invalid or duplicate FJA observation: {day}")
        out[day] = cents
    if not out:
        raise ValueError("FJA history contains no valid observations")
    return out

def read_varint(raw: bytes, offset: int):
    value, shift = 0, 0
    while True:
        if offset >= len(raw) or shift > 49:
            raise ValueError("Recent S&P 500 varint truncated or overflow")
        byte = raw[offset]
        offset += 1
        value += (byte & 127) * (2 ** shift)
        if not (byte & 128):
            return value, offset
        shift += 7

def decode_recent(path: Path):
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

def varint(value: int, output: bytearray):
    if value < 0:
        raise ValueError("varint cannot encode a negative value")
    while value >= 0x80:
        output.append((value & 0x7f) | 0x80)
        value >>= 7
    output.append(value)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--recent-compact", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    fja = parse_fja(download(FJA_URL))
    recent_rows, recent_meta = decode_recent(args.recent_compact)
    recent_start = recent_rows[0][0]
    if recent_start != EXPECTED_RECENT_START:
        raise ValueError(f"Unexpected recent snapshot start: {recent_start}")
    pre = sorted((day, cents) for day, cents in fja.items() if day < recent_start)
    if not pre or pre[0][0] != EXPECTED_START:
        raise ValueError(f"Unexpected long-history start: {pre[0][0] if pre else 'missing'}")
    boundary = fja.get(recent_start)
    boundary_diff = None if boundary is None else abs(boundary - recent_rows[0][1]) / 100
    if boundary_diff is not None and boundary_diff > 0.02:
        raise ValueError(f"FJA/recent snapshot boundary mismatch: {boundary_diff:.4f} points")
    rows = pre + recent_rows
    if len(rows) < MIN_ROWS:
        raise ValueError(f"Unexpectedly short merged history: {len(rows)}")
    if rows[-1][0] < MIN_LATEST:
        raise ValueError(f"Latest date too old: {rows[-1][0]}")
    if any(rows[i][0] >= rows[i+1][0] for i in range(len(rows)-1)):
        raise ValueError("Merged S&P 500 dates are not strictly increasing")
    canonical = "Date,Close\n" + "".join(f"{day},{cents / 100:.2f}\n" for day, cents in rows)
    source_sha256 = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    packed = bytearray()
    previous_day = dt.date.fromisoformat(rows[0][0]).toordinal()
    previous_close = 0
    for day_text, close_cents in rows:
        day_ordinal = dt.date.fromisoformat(day_text).toordinal()
        varint(day_ordinal - previous_day, packed)
        delta = close_cents - previous_close
        varint(2 * delta if delta >= 0 else -2 * delta - 1, packed)
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
            "recent_snapshot_source": "Previously validated 1993-12-31–2026-11-10 FJA/FRED merged compact snapshot",
            "fja_rows": len(fja),
            "fja_used_rows_before_recent_snapshot": len(pre),
            "recent_snapshot_rows": len(recent_rows),
            "boundary_overlap_date": recent_start if boundary is not None else None,
            "boundary_abs_difference_points": boundary_diff,
            "merge_rule": "Use FJA observations strictly before 1993-12-31; retain all validated recent compact observations from 1993-12-31 onward; no interpolation or forward-fill"
        },
        "payload": base64.b64encode(compressed).decode("ascii")
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "payload"} | {"compressed_bytes": len(compressed), "output_bytes": args.output.stat().st_size}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
