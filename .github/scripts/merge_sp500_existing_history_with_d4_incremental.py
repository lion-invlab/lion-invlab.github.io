#!/usr/bin/env python3
"""Merge the existing S&P 500 compact history with append-only TAC D4 close records."""
from __future__ import annotations
import argparse, base64, datetime as dt, hashlib, json, zlib
from pathlib import Path
from build_tac_chart3_synchronized_release import decode_sp500
from build_sp500_from_tac_report_history import load_records

DEFAULT_BASELINE_URL = (
    "https://raw.githubusercontent.com/lion-invlab/lion-invlab.github.io/"
    "research/chart3-synchronized-release-20261118/"
    "data/tac-chart3/sp500_daily_close_1927-2026.compact.json"
)

def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def varint(value: int) -> bytes:
    if value < 0:
        raise ValueError("varint accepts non-negative integers only")
    out = bytearray()
    while value >= 128:
        out.append((value & 127) | 128)
        value >>= 7
    out.append(value)
    return bytes(out)

def encode_rows(rows: list[dict]) -> bytes:
    packed = bytearray()
    previous_day = dt.date.fromisoformat(rows[0]["date"]).toordinal()
    previous_close = 0
    for row in rows:
        ordinal = dt.date.fromisoformat(row["date"]).toordinal()
        cents = int(round(float(row["value"]) * 100))
        if cents <= 0:
            raise ValueError(f"Invalid S&P 500 close for {row['date']}")
        packed.extend(varint(ordinal - previous_day))
        delta = cents - previous_close
        packed.extend(varint(2 * delta if delta >= 0 else -2 * delta - 1))
        previous_day, previous_close = ordinal, cents
    return zlib.compress(bytes(packed))

def merge(baseline_path: Path, incremental_jsonl: Path, compact_path: Path,
          provenance_path: Path, baseline_source_url: str = DEFAULT_BASELINE_URL) -> dict:
    baseline_raw = baseline_path.read_bytes()
    baseline = json.loads(baseline_raw.decode("utf-8"))
    baseline_rows = decode_sp500(baseline)
    if not baseline_rows:
        raise ValueError("Existing S&P 500 baseline is empty")
    baseline_start, baseline_end = baseline_rows[0]["date"], baseline_rows[-1]["date"]
    source_details = baseline.get("source_details")
    if not isinstance(source_details, dict):
        raise ValueError("Existing baseline must preserve its source_details")
    incremental_raw, records = load_records(incremental_jsonl)
    incremental_rows = [
        {"date": day, "value": round(float(item["close"]), 2)}
        for day, item in sorted(records.items())
    ]
    if not incremental_rows:
        raise ValueError("No incremental S&P 500 close records supplied")
    baseline_dates = {x["date"] for x in baseline_rows}
    overlaps = sorted(baseline_dates.intersection(x["date"] for x in incremental_rows))
    if overlaps:
        raise ValueError(f"Incremental records overlap the existing baseline: {overlaps[:5]}")
    if incremental_rows[0]["date"] <= baseline_end:
        raise ValueError("Incremental S&P 500 rows must be strictly newer than baseline end")
    combined = baseline_rows + incremental_rows
    if any(combined[i]["date"] >= combined[i + 1]["date"] for i in range(len(combined) - 1)):
        raise ValueError("Merged S&P 500 dates must be strictly ascending")

    merged_dataset_sha = sha256(canonical([
        {"date": x["date"], "value": round(float(x["value"]), 2)} for x in combined
    ]))
    packed = encode_rows(combined)
    compact = {
        "schema_version": "1.0.0",
        "encoding": "zlib+base64",
        "fields": "per row: unsigned-varint day-gap from previous date ordinal; unsigned-varint zigzag(close delta in cents)",
        "start": combined[0]["date"],
        "end": combined[-1]["date"],
        "rows": len(combined),
        "close_scale": 100,
        "source_dataset_sha256": merged_dataset_sha,
        "source_details": {
            "merge_method": "append_only_tac_d4_incremental",
            "historical_baseline_file": baseline_path.name,
            "historical_baseline_file_sha256": sha256(baseline_raw),
            "historical_baseline_source_dataset_sha256": baseline.get("source_dataset_sha256"),
            "historical_baseline_source_details": source_details,
            "historical_baseline_span": {"start": baseline_start, "end": baseline_end},
            "incremental_jsonl_file": incremental_jsonl.name,
            "incremental_jsonl_sha256": sha256(incremental_raw),
            "incremental_rows": len(incremental_rows),
            "incremental_span": {"start": incremental_rows[0]["date"], "end": incremental_rows[-1]["date"]},
            "merge_rule": "preserve every baseline row; append only strictly newer, non-overlapping daily closes; no interpolation or forward-fill"
        },
        "payload": base64.b64encode(packed).decode("ascii")
    }
    baseline_meta = {
        "start": baseline_start,
        "end": baseline_end,
        "source_name": "Existing TAC Chart 3 validated historical compact baseline",
        "source_url": baseline_source_url,
        "source_note": (
            "Inherited historical compact baseline. Original source_details are preserved in the compact artifact, "
            "but provider attribution and retrieval timestamps are not retained for every individual observation."
        ),
        "retrieval_method": "inherited_existing_validated_compact_snapshot",
        "retrieval_timestamp_semantics": "not retained in inherited historical baseline; no timestamp is inferred",
        "source_dataset_sha256": baseline.get("source_dataset_sha256"),
        "baseline_file_sha256": sha256(baseline_raw),
        "source_details": source_details
    }
    observations = []
    for day, item in sorted(records.items()):
        observations.append({
            "date": day,
            "source_name": item["source_name"],
            "source_url": item["source_url"],
            "source_note": item.get("source_note", ""),
            "retrieved_at": item["retrieved_at"],
            "retrieval_method": item["retrieval_method"],
            "record_sha256": item["record_sha256"]
        })
    provenance = {
        "schema_version": "2.1",
        "source": "Existing TAC Chart 3 historical compact baseline + TAC daily report D4 incremental observations",
        "source_sha256": merged_dataset_sha,
        "method": "merge_existing_compact_history_with_append_only_tac_d4_records",
        "historical_baseline": baseline_meta,
        "observations": observations
    }
    compact_path.parent.mkdir(parents=True, exist_ok=True)
    provenance_path.parent.mkdir(parents=True, exist_ok=True)
    compact_path.write_text(json.dumps(compact, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    provenance_path.write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "rows": len(combined), "start": combined[0]["date"], "end": combined[-1]["date"],
        "baseline_rows": len(baseline_rows), "incremental_rows": len(incremental_rows),
        "baseline_end": baseline_end, "incremental_start": incremental_rows[0]["date"],
        "source_dataset_sha256": merged_dataset_sha,
        "incremental_sources": sorted({x["source_name"] for x in observations})
    }

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--incremental-jsonl", type=Path, required=True)
    p.add_argument("--compact", type=Path, required=True)
    p.add_argument("--provenance", type=Path, required=True)
    p.add_argument("--baseline-source-url", default=DEFAULT_BASELINE_URL)
    a = p.parse_args()
    print(json.dumps(merge(a.baseline, a.incremental_jsonl, a.compact, a.provenance,
                           a.baseline_source_url), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
