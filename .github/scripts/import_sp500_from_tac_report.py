#!/usr/bin/env python3
"""Import the S&P 500 OHLC already verified for a TAC daily report.

This is an adapter, not a market-data downloader. It preserves the exact
provider/source recorded by the report and appends one auditable cash-index
observation to a Chart 3 staging JSONL file.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def build_record(report: dict, retrieved_at: str) -> dict:
    try:
        stamp = dt.datetime.fromisoformat(retrieved_at.replace("Z", "+00:00"))
    except Exception as exc:
        raise ValueError("retrieved_at must be an ISO-8601 timestamp with timezone") from exc
    if stamp.tzinfo is None:
        raise ValueError("retrieved_at must include an explicit timezone")
    report_date = report.get("report_date")
    trading_date = report.get("trading_date")
    try:
        dt.date.fromisoformat(str(report_date))
        dt.date.fromisoformat(str(trading_date))
    except Exception as exc:
        raise ValueError("report_date and trading_date must be ISO dates") from exc
    levels = report.get("key_levels_overrides")
    if not isinstance(levels, dict) or not isinstance(levels.get("sp500"), dict):
        raise ValueError("report has no key_levels_overrides.sp500 OHLC record")
    item = levels["sp500"]
    if item.get("trading_date") != trading_date:
        raise ValueError("S&P 500 OHLC trading_date does not match report trading_date")
    source_name = str(item.get("source_name") or "").strip()
    source_url = str(item.get("source_url") or "").strip()
    note = str(item.get("note") or "").lower()
    parsed = urlparse(source_url)
    if not source_name or parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("S&P 500 source_name and HTTPS source_url are required")
    if not ("現金指數" in note or "cash index" in note):
        raise ValueError("source note must explicitly identify a cash index")
    explicitly_non_cfd = ("非cfd" in note or "non-cfd" in note or "not cfd" in note or "非差價合約" in note)
    explicitly_cfd = (("cfd" in note and not explicitly_non_cfd) or ("差價合約" in note and not explicitly_non_cfd))
    if explicitly_cfd:
        raise ValueError("CFD observations cannot enter the S&P 500 cash-index history")
    values = {}
    for field in ("open", "high", "low", "close"):
        try:
            value = float(item[field])
        except Exception as exc:
            raise ValueError(f"missing/invalid OHLC field: {field}") from exc
        if not (value > 0 and value < float("inf")):
            raise ValueError(f"OHLC {field} must be positive and finite")
        values[field] = round(value, 2)
    if values["high"] < max(values["open"], values["close"]) or values["low"] > min(values["open"], values["close"]) or values["high"] < values["low"]:
        raise ValueError("inconsistent S&P 500 OHLC relationships")
    record = {
        "schema_version": "1.0",
        "series_id": "SP500",
        "instrument": "S&P 500 cash price index",
        "report_date": report_date,
        "observation_date": trading_date,
        "open": values["open"],
        "high": values["high"],
        "low": values["low"],
        "close": values["close"],
        "source_name": source_name,
        "source_url": source_url,
        "source_note": str(item.get("note") or ""),
        "retrieved_at": stamp.astimezone(dt.timezone.utc).isoformat(timespec="seconds"),
        "retrieval_method": "reused_from_tac_daily_report_verified_ohlc"
    }
    record["record_sha256"] = hashlib.sha256(canonical(record)).hexdigest()
    return record

def append_record(path: Path, record: dict) -> str:
    existing = {}
    if path.exists():
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                old = json.loads(line)
            except Exception as exc:
                raise ValueError(f"invalid existing JSONL at line {line_no}") from exc
            day = old.get("observation_date")
            if day in existing:
                raise ValueError(f"duplicate observation_date already exists: {day}")
            existing[day] = old
    day = record["observation_date"]
    if day in existing:
        old = existing[day]
        stable_fields = ("series_id", "instrument", "report_date", "observation_date",
                         "open", "high", "low", "close", "source_name", "source_url",
                         "source_note", "retrieval_method")
        if all(old.get(key) == record.get(key) for key in stable_fields):
            # Preserve the first captured retrieval timestamp and its immutable hash.
            return "NOOP_IDENTICAL_OBSERVATION"
        raise ValueError(f"conflicting S&P 500 observation/source already exists for {day}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return "APPENDED"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-data", type=Path, required=True)
    parser.add_argument("--retrieved-at", required=True, help="ISO-8601 timestamp including timezone")
    parser.add_argument("--output", type=Path, default=Path("data/tac-chart3/sp500_tac_report_ohlc.jsonl"))
    args = parser.parse_args()
    report = json.loads(args.report_data.read_text(encoding="utf-8"))
    record = build_record(report, args.retrieved_at)
    status = append_record(args.output, record)
    print(json.dumps({"status": status, "observation_date": record["observation_date"], "close": record["close"], "source_name": record["source_name"], "record_sha256": record["record_sha256"]}, ensure_ascii=False))

if __name__ == "__main__":
    main()
