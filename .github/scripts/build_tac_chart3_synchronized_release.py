#!/usr/bin/env python3
"""Publish Chart 3 only when all five native series share a real observation date."""
from __future__ import annotations
import argparse, base64, datetime as dt, hashlib, json, os, socket, tempfile, zlib
from pathlib import Path
from urllib.parse import urlparse

EXPECTED_FRED = ("VIXCLS", "NFCI", "NFCICREDIT", "STLFSI4")
SP500_ID = "SP500"
SCHEMA = "1.0"

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def decode_varint(raw: bytes, offset: int):
    value = shift = 0
    while True:
        if offset >= len(raw) or shift > 56:
            raise ValueError("Malformed S&P 500 compact payload (truncated/overflow varint)")
        b = raw[offset]; offset += 1
        value |= (b & 127) << shift
        if not b & 128:
            return value, offset
        shift += 7

def decode_sp500(compact: dict):
    if compact.get("schema_version") != "1.0.0" or compact.get("encoding") != "zlib+base64":
        raise ValueError("Unsupported S&P 500 compact schema")
    raw = zlib.decompress(base64.b64decode(compact["payload"], validate=True))
    ordinal = dt.date.fromisoformat(compact["start"]).toordinal()
    close_cents = 0
    rows = []
    offset = 0
    for _ in range(int(compact["rows"])):
        gap, offset = decode_varint(raw, offset)
        ordinal += gap
        zigzag, offset = decode_varint(raw, offset)
        delta = zigzag // 2 if zigzag % 2 == 0 else -(zigzag // 2) - 1
        close_cents += delta
        day = dt.date.fromordinal(ordinal).isoformat()
        if close_cents <= 0 or (rows and day <= rows[-1]["date"]):
            raise ValueError("S&P 500 compact data has invalid close or non-increasing dates")
        rows.append({"date": day, "value": close_cents / 100.0, "value_raw": f"{close_cents / 100.0:.2f}"})
    if offset != len(raw) or len(rows) != int(compact["rows"]):
        raise ValueError("S&P 500 compact payload length/row count mismatch")
    if not rows or rows[0]["date"] != compact["start"] or rows[-1]["date"] != compact["end"]:
        raise ValueError("S&P 500 compact date boundaries mismatch")
    return rows

def validate_sp500_provenance(provenance: dict, compact: dict):
    source_url = provenance.get("source_url", "")
    parsed = urlparse(source_url)
    host = (parsed.hostname or "").lower()
    if host != "investing.com" and not host.endswith(".investing.com"):
        raise ValueError("S&P 500 source must be an Investing.com URL; current source provenance is not accepted")
    if parsed.scheme != "https":
        raise ValueError("S&P 500 source URL must use HTTPS")
    if not provenance.get("retrieved_at") or not provenance.get("source_sha256"):
        raise ValueError("S&P 500 provenance requires retrieved_at and source_sha256")
    try:
        dt.datetime.fromisoformat(provenance["retrieved_at"].replace("Z", "+00:00"))
    except (TypeError, ValueError):
        raise ValueError("S&P 500 retrieved_at must be an ISO-8601 timestamp")
    digest = provenance["source_sha256"]
    if len(digest) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in digest):
        raise ValueError("S&P 500 source_sha256 must be a 64-character SHA-256 hex digest")
    if not provenance.get("method"):
        raise ValueError("S&P 500 provenance requires a retrieval method")
    if provenance.get("source_sha256") != compact.get("source_dataset_sha256"):
        raise ValueError("S&P 500 provenance source_sha256 does not match the compact dataset source hash")
    return {
        "source": "Investing.com",
        "source_url": source_url,
        "retrieved_at": provenance["retrieved_at"],
        "source_sha256": provenance["source_sha256"],
        "method": provenance["method"],
        "source_observation_date": provenance.get("source_observation_date"),
    }

def load_fred_series(dataset: dict):
    by_id = {x.get("series_id"): x for x in dataset.get("series", [])}
    missing = [sid for sid in EXPECTED_FRED if sid not in by_id]
    if missing:
        raise ValueError(f"FRED dataset missing required series: {missing}")
    result = {}
    for sid in EXPECTED_FRED:
        item = by_id[sid]
        values = {}
        for obs in item.get("observations", []):
            day = obs.get("date")
            value = obs.get("value")
            if not day:
                raise ValueError(f"{sid}: observation without date")
            dt.date.fromisoformat(day)
            if day in values:
                raise ValueError(f"{sid}: duplicate observation date {day}")
            if value is not None:
                number = float(value)
                if not (number == number and abs(number) != float("inf")):
                    raise ValueError(f"{sid}: non-finite value on {day}")
                values[day] = number
        if not values:
            raise ValueError(f"{sid}: no valid observations")
        result[sid] = {
            "meta": item,
            "values": values,
            "latest_observation_date": max(values),
        }
    return result

def build_candidate(fred_dataset: dict, sp500_compact: dict, sp500_provenance: dict):
    provenance = validate_sp500_provenance(sp500_provenance, sp500_compact)
    fred = load_fred_series(fred_dataset)
    sp_rows = decode_sp500(sp500_compact)
    sp_values = {x["date"]: x["value"] for x in sp_rows}
    if len(sp_values) != len(sp_rows):
        raise ValueError("S&P 500 duplicate dates")
    valid_sets = [set(x["values"]) for x in fred.values()] + [set(sp_values)]
    common = set.intersection(*valid_sets)
    if not common:
        raise ValueError("No exact common native observation date exists across all five series")
    common_date = max(common)

    series = []
    for sid in EXPECTED_FRED:
        item = fred[sid]
        meta = item["meta"]
        native = [
            {"date": day, "value": value}
            for day, value in sorted(item["values"].items()) if day <= common_date
        ]
        series.append({
            "series_id": sid,
            "label": meta.get("label", sid),
            "frequency": meta.get("frequency"),
            "unit": meta.get("unit"),
            "source": meta.get("source", "Federal Reserve Bank of St. Louis FRED/ALFRED"),
            "source_series_id": meta.get("source_series_id", sid),
            "source_file_sha256": meta.get("source_file_sha256"),
            "vintage_events_sha256": meta.get("vintage_events_sha256"),
            "retrieved_at": meta.get("retrieved_at"),
            "latest_observation_date": item["latest_observation_date"],
            "observations": native,
            "alignment": "native_observations_only_no_forward_fill_no_interpolation",
        })
    sp_native = [x for x in sp_rows if x["date"] <= common_date]
    series.append({
        "series_id": SP500_ID,
        "label": "S&P 500",
        "frequency": "daily",
        "unit": "index points",
        "source": "Investing.com",
        "source_url": provenance["source_url"],
        "source_sha256": provenance["source_sha256"],
        "retrieved_at": provenance["retrieved_at"],
        "latest_observation_date": sp_rows[-1]["date"],
        "observations": sp_native,
        "alignment": "native_observations_only_no_forward_fill_no_interpolation",
    })
    payload = {
        "schema_version": SCHEMA,
        "dataset_id": "TAC_CHART3_SYNCHRONIZED_RELEASE",
        "common_observation_date": common_date,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "publication_rule": "All five series must contain a native non-missing observation on common_observation_date; no imputation or date rewriting.",
        "series": series,
        "source_provenance": {"sp500": provenance},
        "quality": {
            "status": "PASS",
            "series_count": 5,
            "common_observation_date": common_date,
            "native_observation_intersection": True,
            "forward_fill": False,
            "interpolation": False,
            "resampling": False,
        },
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["snapshot_id"] = sha256_bytes(canonical)
    return payload

def atomic_write(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw); f.flush(); os.fsync(f.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return sha256_bytes(raw), len(raw)

def publish(candidate: dict, output: Path, previous: Path | None):
    common = candidate["common_observation_date"]
    if previous and previous.exists():
        old = read_json(previous)
        old_date = old.get("common_observation_date")
        if old_date and common <= old_date:
            return {"status": "NO_NEW_COMMON_DATE", "common_observation_date": common,
                    "previous_common_observation_date": old_date, "published": False}
    digest, size = atomic_write(output, candidate)
    return {"status": "PUBLISHED", "common_observation_date": common,
            "snapshot_id": candidate["snapshot_id"], "sha256": digest,
            "bytes": size, "published": True, "output": str(output)}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fred-dataset", type=Path, required=True)
    p.add_argument("--sp500-compact", type=Path, required=True)
    p.add_argument("--sp500-provenance", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--previous-release", type=Path)
    a = p.parse_args()
    candidate = build_candidate(read_json(a.fred_dataset), read_json(a.sp500_compact), read_json(a.sp500_provenance))
    print(json.dumps(publish(candidate, a.output, a.previous_release), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
