#!/usr/bin/env python3
"""Incremental S&P 500 price-index close updater for TAC Chart 3.

Primary refresh endpoint: Investing.com Finance chart API (^GSPC), unadjusted close.
This is an unofficial endpoint, so every response is schema- and freshness-checked.
Long-history pre-1993 base is assembled separately from a pinned FJA snapshot.
"""
from __future__ import annotations
import argparse, base64, datetime as dt, hashlib, json, math, os, time, urllib.parse, urllib.request, zlib
from pathlib import Path
from zoneinfo import ZoneInfo

SYMBOL = "^GSPC"
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(SYMBOL, safe="")
BOOTSTRAP_START = dt.date(1993, 12, 31)
OVERLAP_CALENDAR_DAYS = 30
MIN_BOOTSTRAP_ROWS = 7000
ET = ZoneInfo("America/New_York")

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def fetch_chart(start: dt.date, end_exclusive: dt.date, retries: int = 5) -> dict:
    params = urllib.parse.urlencode({
        "start-date": start.isoformat(),
        "end-date": (end_exclusive - dt.timedelta(days=1)).isoformat(),
        "time-frame": "Daily", "add-missing-rows": "false"
    })
    url = INVESTING_URL + "?" + params
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "domain-id": "www",
                "Origin": "https://www.investing.com",
                "Referer": "https://www.investing.com/indices/us-spx-500-historical-data"
            })
            with urllib.request.urlopen(req, timeout=60) as response:
                raw = response.read()
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, (dict, list)):
                raise RuntimeError("Investing.com response is not a JSON object/array")
            return {"payload": payload, "raw_sha256": sha256(raw), "url": url}
        except Exception as exc:
            last = exc
            if attempt + 1 < retries:
                time.sleep(min(2 ** attempt * 3, 30))
    raise RuntimeError(f"Investing.com historical endpoint failed after {retries} attempts: {last}")

def parse_chart(response: dict) -> dict[str, int]:
    payload = response["payload"]
    rows = payload if isinstance(payload, list) else (payload.get("data") or payload.get("historical") or payload.get("prices"))
    if isinstance(rows, dict):
        rows = rows.get("historical") or rows.get("data")
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("Investing.com response has no historical rows; verify S&P 500 instrument ID/schema")
    out = {}
    for row in rows:
        if isinstance(row, dict):
            raw_day = row.get("date") or row.get("datetime") or row.get("time")
            close = row.get("close") or row.get("last")
        elif isinstance(row, (list, tuple)) and len(row) >= 5:
            raw_day, close = row[0], row[4]
        else:
            raise RuntimeError(f"Unrecognized Investing.com historical row: {row!r}")
        if raw_day is None or close in (None, "", "."):
            continue
        if isinstance(raw_day, (int, float)):
            day = dt.datetime.fromtimestamp(int(raw_day), dt.timezone.utc).date().isoformat()
        else:
            raw_text = str(raw_day).strip()
            try:
                day = dt.date.fromisoformat(raw_text[:10]).isoformat()
            except ValueError:
                parsed = None
                for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%b %d, %Y", "%d %b %Y"):
                    try:
                        parsed = dt.datetime.strptime(raw_text, fmt).date()
                        break
                    except ValueError:
                        pass
                if parsed is None:
                    raise RuntimeError(f"Unrecognized Investing.com date: {raw_day!r}")
                day = parsed.isoformat()
        value = float(str(close).replace(",", "").strip())
        if not math.isfinite(value) or value <= 0:
            raise RuntimeError(f"Invalid S&P 500 close {close!r} on {day}")
        cents = int(round(value * 100))
        if day in out and out[day] != cents:
            raise RuntimeError(f"Conflicting duplicate Investing.com observation: {day}")
        out[day] = cents
    if not out:
        raise RuntimeError("Investing.com historical response contains no valid closes")
    return out

def decode_compact(path: Path) -> dict[str, int]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if obj.get("schema_version") != "1.0.0" or obj.get("encoding") != "zlib+base64":
        raise RuntimeError("Existing recent S&P 500 compact schema is unsupported")
    raw = zlib.decompress(base64.b64decode(obj["payload"], validate=True))
    offset = 0
    ordinal = dt.date.fromisoformat(obj["start"]).toordinal()
    close_cents = 0
    rows = {}
    for _ in range(int(obj["rows"])):
        gap, offset = read_varint(raw, offset)
        ordinal += gap
        zigzag, offset = read_varint(raw, offset)
        delta = zigzag // 2 if zigzag % 2 == 0 else -(zigzag // 2) - 1
        close_cents += delta
        day = dt.date.fromordinal(ordinal).isoformat()
        if day in rows:
            raise RuntimeError(f"Duplicate compact date: {day}")
        rows[day] = close_cents
    if offset != len(raw) or len(rows) != int(obj["rows"]):
        raise RuntimeError("Existing compact row count/payload length mismatch")
    if min(rows) != obj["start"] or max(rows) != obj["end"]:
        raise RuntimeError("Existing compact date boundaries mismatch")
    return rows

def read_varint(raw: bytes, offset: int):
    value, shift = 0, 0
    while True:
        if offset >= len(raw) or shift > 49:
            raise RuntimeError("Truncated/overflow compact varint")
        byte = raw[offset]; offset += 1
        value += (byte & 127) * (2 ** shift)
        if not byte & 128:
            return value, offset
        shift += 7

def write_varint(value: int, out: bytearray):
    if value < 0:
        raise ValueError("varint cannot encode negative values")
    while value >= 128:
        out.append((value & 127) | 128); value >>= 7
    out.append(value)

def encode_compact(rows: dict[str, int], source_meta: dict) -> dict:
    ordered = sorted(rows.items())
    if len(ordered) < MIN_BOOTSTRAP_ROWS or ordered[0][0] != BOOTSTRAP_START.isoformat():
        raise RuntimeError(f"Recent S&P history coverage invalid: rows={len(ordered)}, start={ordered[0][0] if ordered else None}")
    if any(ordered[i][0] >= ordered[i+1][0] for i in range(len(ordered)-1)):
        raise RuntimeError("Recent S&P dates are not strictly increasing")
    packed = bytearray()
    prev_day = dt.date.fromisoformat(ordered[0][0]).toordinal()
    prev_close = 0
    for day_text, close in ordered:
        day = dt.date.fromisoformat(day_text).toordinal()
        write_varint(day - prev_day, packed)
        delta = close - prev_close
        write_varint(2 * delta if delta >= 0 else -2 * delta - 1, packed)
        prev_day, prev_close = day, close
    canonical = ("Date,Close\n" + "".join(f"{d},{c/100:.2f}\n" for d,c in ordered)).encode()
    return {
        "schema_version": "1.0.0", "encoding": "zlib+base64",
        "fields": "per row: unsigned-varint day-gap from previous date ordinal; unsigned-varint zigzag(close delta in cents)",
        "start": ordered[0][0], "end": ordered[-1][0], "rows": len(ordered), "close_scale": 100,
        "source_dataset_sha256": sha256(canonical),
        "source_details": source_meta,
        "payload": base64.b64encode(zlib.compress(bytes(packed), level=9)).decode("ascii")
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=Path("data/tac-chart3"))
    ap.add_argument("--overlap-calendar-days", type=int, default=OVERLAP_CALENDAR_DAYS)
    args = ap.parse_args()
    if args.overlap_calendar_days < 7 or args.overlap_calendar_days > 90:
        raise SystemExit("--overlap-calendar-days must be between 7 and 90")
    root = args.data_dir
    root.mkdir(parents=True, exist_ok=True)
    recent_path = root / "sp500_daily_close_1993-2026.compact.json"
    today_et = dt.datetime.now(ET).date()
    end_exclusive = today_et + dt.timedelta(days=1)
    old = decode_compact(recent_path) if recent_path.exists() else {}
    if old:
        start = max(BOOTSTRAP_START, dt.date.fromisoformat(max(old)) - dt.timedelta(days=args.overlap_calendar_days))
        mode = "incremental_overlap"
    else:
        start = BOOTSTRAP_START
        mode = "full_bootstrap"
    response = fetch_chart(start, end_exclusive)
    fresh = parse_chart(response)
    merged = dict(old)
    changed = []
    for day, close in fresh.items():
        if day < BOOTSTRAP_START.isoformat():
            continue
        if day in merged and merged[day] != close:
            changed.append({"date": day, "old_close": merged[day]/100, "new_close": close/100})
        merged[day] = close
    # Investing.com must return the current recent window, including at least one observation in the last 10 calendar days.
    latest = max(fresh)
    if (today_et - dt.date.fromisoformat(latest)).days > 10:
        raise RuntimeError(f"Investing.com data stale: latest={latest}, today_ET={today_et}")
    if old and not set(old).intersection(fresh):
        raise RuntimeError("No overlap between stored and fetched Investing.com dates; refusing blind append")
    source_meta = {
        "daily_source": "Investing.com historical data endpoint; S&P 500 index close",
        "daily_source_url": response["url"],
        "daily_response_sha256": response["raw_sha256"],
        "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "update_mode": mode,
        "requested_start": start.isoformat(),
        "requested_end_exclusive": end_exclusive.isoformat(),
        "overlap_calendar_days": args.overlap_calendar_days,
        "latest_source_date": latest,
        "changed_existing_observations": changed,
        "source_license_note": "Yahoo Finance terms and index-data redistribution rights must be reviewed before public redistribution; this workflow preserves provenance but does not grant a data licence."
    }
    compact = encode_compact(merged, source_meta)
    tmp = recent_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(compact, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    # Round-trip validation before replacing the durable dataset.
    check = decode_compact(tmp)
    if check != merged:
        raise RuntimeError("Compact encode/decode round-trip mismatch")
    os.replace(tmp, recent_path)
    report = {
        "status": "PASS", "mode": mode, "rows_before": len(old), "rows_after": len(merged),
        "fetched_rows": len(fresh), "latest_date": latest, "changed_existing_observations": changed,
        "recent_file": str(recent_path), "recent_file_sha256": sha256(recent_path.read_bytes()),
        "source_response_sha256": response["raw_sha256"], "retrieved_at_utc": source_meta["retrieved_at_utc"]
    }
    (root / "sp500_incremental_qa.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    # Append-only audit trail: preserve every retrieval hash and every corrected close.
    with (root / "sp500_update_log.jsonl").open("a", encoding="utf-8") as audit:
        audit.write(json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n")
    manifest = {
        "dataset_id": "TAC_CHART3_SP500_DAILY_CLOSE",
        "instrument": "^GSPC",
        "measure": "unadjusted S&P 500 price index close",
        "start": min(merged), "end": max(merged), "rows": len(merged),
        "recent_file": "sp500_daily_close_1993-2026.compact.json",
        "recent_file_sha256": report["recent_file_sha256"],
        "full_history_file": "sp500_daily_close_1927-2026.compact.json",
        "source": "Investing.com historical data endpoint (instrument ID configurable)",
        "long_history_source": "Pinned FJA historical CSV for dates before 1993-12-31",
        "latest_source_date": latest,
        "retrieved_at_utc": source_meta["retrieved_at_utc"],
        "latest_response_sha256": response["raw_sha256"],
        "update_log": "sp500_update_log.jsonl",
        "qa_report": "sp500_incremental_qa.json",
        "method": "30-calendar-day overlap; date-keyed upsert; changed closes recorded; no interpolation or forward-fill",
        "licensing": "Public redistribution rights require separate review; source provenance is recorded but no licence is implied."
    }
    (root / "sp500_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
