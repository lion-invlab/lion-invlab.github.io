#!/usr/bin/env python3
"""Append one verified TAC S&P 500 cash-index close to the Chart 3 increment ledger.

Input may be either:
1) a minimal report handoff JSON with report_date/trading_date/sp500; or
2) the existing normalized TAC market snapshot shape with meta/global_indices.sp500.

This script never fetches market data. It records only values already checked by
the daily TAC report producer and preserves the source's actual observed_at time.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_OUTPUT = Path("data/tac-chart3/sp500_daily_increment.jsonl")


def canonical(value: dict) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def parse_date(value: str, field: str) -> dt.date:
    try:
        return dt.date.fromisoformat(str(value))
    except Exception as exc:
        raise ValueError(f"{field} must be an ISO-8601 date") from exc


def parse_timestamp(value: str) -> dt.datetime:
    try:
        stamp = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception as exc:
        raise ValueError("source.observed_at must be ISO-8601 date-time") from exc
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("source.observed_at must include an explicit timezone")
    if stamp.utcoffset() != dt.timedelta(hours=8):
        raise ValueError("source.observed_at must use Asia/Taipei UTC+08:00")
    return stamp


def extract_handoff(payload: dict) -> dict:
    if "meta" in payload:
        meta = payload.get("meta") or {}
        market = (payload.get("global_indices") or {}).get("sp500") or {}
        report_date = meta.get("report_date")
        trading_date = meta.get("trading_date")
    else:
        report_date = payload.get("report_date")
        trading_date = payload.get("trading_date")
        market = payload.get("sp500") or {}

    if market.get("status", "verified") != "verified":
        raise ValueError("S&P 500 handoff status must be verified")
    source = market.get("source")
    if not isinstance(source, dict):
        raise ValueError("S&P 500 source record is required")

    report_day = parse_date(report_date, "report_date")
    trading_day = parse_date(trading_date, "trading_date")
    data_day = parse_date(source.get("data_date"), "source.data_date")
    if data_day != trading_day:
        raise ValueError("source.data_date must match trading_date")

    observed_at = parse_timestamp(source.get("observed_at"))
    if observed_at.date() != report_day:
        raise ValueError("source.observed_at local date must match report_date")
    close = market.get("value", market.get("close"))
    try:
        close = float(close)
    except Exception as exc:
        raise ValueError("S&P 500 close must be numeric") from exc
    if not math.isfinite(close) or close <= 0:
        raise ValueError("S&P 500 close must be positive and finite")

    source_name = str(source.get("name") or "").strip()
    source_url = str(source.get("url") or "").strip()
    instrument = str(source.get("instrument") or "").strip()
    quote_type = str(source.get("quote_type") or "").strip()
    note = str(market.get("notes") or source.get("note") or "").strip()
    parsed = urlparse(source_url)
    if not source_name or parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("S&P 500 source requires a name and valid HTTPS URL")

    identity = (instrument + " " + source_name).lower()
    if not any(token in identity for token in ("s&p 500", "sp500", "標普500", "標準普爾500")):
        raise ValueError("source.instrument/name must identify the S&P 500")
    if "cfd" in identity or "cfd" in quote_type.lower():
        raise ValueError("CFD quote cannot enter the S&P 500 cash-index increment ledger")
    if not any(token in quote_type.lower() for token in ("close", "cash_index")):
        raise ValueError("source.quote_type must identify a close/cash-index observation")

    return {
        "schema_version": "1.0",
        "series_id": "SP500",
        "instrument": "S&P 500 cash price index",
        "report_date": report_day.isoformat(),
        "observation_date": trading_day.isoformat(),
        "close": round(close, 2),
        "source_name": source_name,
        "source_url": source_url,
        "source_note": f"S&P 500現金指數；非CFD；quote_type={quote_type}；instrument={instrument}；{note}",
        "observed_at": observed_at.isoformat(),
        "retrieved_at": observed_at.astimezone(dt.timezone.utc).isoformat(),
        "retrieval_method": "tac_daily_report_direct_source_check",
        "retrieval_timestamp_semantics": "source.observed_at records the actual Taipei-local time the daily report producer checked the source page",
    }


def seal_record(record: dict) -> dict:
    result = dict(record)
    result["record_sha256"] = hashlib.sha256(canonical(result)).hexdigest()
    return result


def load_existing(path: Path) -> tuple[list[dict], bytes]:
    if not path.exists():
        return [], b""
    raw = path.read_bytes()
    records = []
    seen = set()
    for line_no, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception as exc:
            raise ValueError(f"Invalid JSONL at line {line_no}") from exc
        expected = row.get("record_sha256")
        body = {k: v for k, v in row.items() if k != "record_sha256"}
        actual = hashlib.sha256(canonical(body)).hexdigest()
        if expected != actual:
            raise ValueError(f"Record SHA-256 mismatch at line {line_no}")
        day = row.get("observation_date")
        if day in seen:
            raise ValueError(f"Duplicate existing observation date: {day}")
        seen.add(day)
        records.append(row)
    if any(records[i]["observation_date"] >= records[i + 1]["observation_date"]
           for i in range(len(records) - 1)):
        raise ValueError("Existing S&P 500 increment ledger must be strictly ascending")
    return records, raw


def append_handoff(payload: dict, output: Path = DEFAULT_OUTPUT) -> dict:
    record = seal_record(extract_handoff(payload))
    records, old_raw = load_existing(output)
    day = record["observation_date"]
    existing = next((row for row in records if row["observation_date"] == day), None)
    if existing is not None:
        stable_fields = (
            "series_id", "instrument", "observation_date", "close",
            "source_name", "source_url", "source_note",
        )
        if all(existing.get(key) == record.get(key) for key in stable_fields):
            return {"status": "NOOP_IDENTICAL_OBSERVATION", "record": existing,
                    "ledger_sha256": hashlib.sha256(old_raw).hexdigest()}
        raise ValueError(f"Conflicting S&P 500 observation/source already exists for {day}")
    if records and day <= records[-1]["observation_date"]:
        raise ValueError("New S&P 500 observation must be later than the last ledger date")

    output.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
    with output.open("ab") as stream:
        stream.write(line.encode("utf-8"))
    new_raw = output.read_bytes()
    return {"status": "APPENDED", "record": record,
            "ledger_sha256": hashlib.sha256(new_raw).hexdigest()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff", type=Path, required=True,
                        help="JSON file containing the verified S&P 500 report handoff")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = json.loads(args.handoff.read_text(encoding="utf-8"))
    result = append_handoff(payload, args.output)
    print(json.dumps({
        "status": result["status"],
        "observation_date": result["record"]["observation_date"],
        "close": result["record"]["close"],
        "source_name": result["record"]["source_name"],
        "observed_at": result["record"]["observed_at"],
        "ledger_sha256": result["ledger_sha256"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
