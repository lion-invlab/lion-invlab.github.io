#!/usr/bin/env python3
"""Append the S&P 500 close from an existing TAC D4 capture; never fetch prices."""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import math
import re
from pathlib import Path
from urllib.parse import urlparse

def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def parse_close(item: dict) -> float:
    if item.get("close") is not None:
        value = float(item["close"])
    else:
        text = str(item.get("ohlc") or "")
        match = re.search(r"(?:^|[｜|])\s*C\s+([\d,]+(?:\.\d+)?)", text)
        if not match:
            raise ValueError("D4 S&P 500 item must include close or an OHLC string with C value")
        value = float(match.group(1).replace(",", ""))
    if not math.isfinite(value) or value <= 0:
        raise ValueError("S&P 500 close must be positive and finite")
    return round(value, 2)

def build_record(capture: dict) -> dict:
    captured_at = capture.get("captured_at_taipei") or capture.get("captured_at")
    if not captured_at:
        raise ValueError("D4 capture must include captured_at_taipei/captured_at")
    try:
        stamp = dt.datetime.fromisoformat(str(captured_at).replace("Z", "+00:00"))
    except Exception as exc:
        raise ValueError("D4 capture timestamp must be ISO-8601") from exc
    if stamp.tzinfo is None:
        raise ValueError("D4 capture timestamp must include timezone")
    report_date = str(capture.get("report_date") or "")
    trading_date = str(capture.get("trading_date") or "")
    dt.date.fromisoformat(report_date)
    dt.date.fromisoformat(trading_date)
    key_levels = capture.get("key_levels")
    if not isinstance(key_levels, dict) or key_levels.get("baseline_date") != trading_date:
        raise ValueError("D4 key_levels baseline_date must match capture trading_date")
    items = key_levels.get("items")
    if not isinstance(items, list):
        raise ValueError("D4 key_levels.items must be an array")
    matches = [x for x in items if x.get("key") == "sp500"]
    if len(matches) != 1:
        raise ValueError(f"D4 capture must contain exactly one S&P 500 item; found {len(matches)}")
    item = matches[0]
    if item.get("name") != "S&P 500" or item.get("trading_date") != trading_date:
        raise ValueError("D4 S&P 500 identity/date mismatch")
    symbol = str(item.get("symbol") or "").strip()
    if symbol not in ("^SPX", "^GSPC"):
        raise ValueError(f"Unexpected S&P 500 cash-index symbol: {symbol!r}")
    if item.get("quote_type") != "cash_index":
        raise ValueError("Only explicitly identified cash-index observations are accepted")
    source_name = str(item.get("source_name") or "").strip()
    source_url = str(item.get("url") or item.get("source_url") or "").strip()
    parsed = urlparse(source_url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host:
        raise ValueError("D4 source URL must be valid HTTPS")
    if host != "finance.yahoo.com" and host != "investing.com" and not host.endswith(".investing.com"):
        raise ValueError(f"Unapproved D4 source host: {host}")
    if not source_name:
        raise ValueError("D4 source_name is required")
    if host == "finance.yahoo.com" and "yahoo" not in source_name.lower():
        raise ValueError("Yahoo URL/source_name mismatch")
    if "investing.com" in host and "investing.com" not in source_name.lower():
        raise ValueError("Investing.com URL/source_name mismatch")
    close = parse_close(item)
    method = "tac_d4_yfinance_daily_history" if host == "finance.yahoo.com" else "tac_d4_source_verified_daily_history"
    record = {
        "schema_version": "1.0",
        "series_id": "SP500",
        "instrument": "S&P 500 cash price index",
        "symbol": symbol,
        "report_date": report_date,
        "observation_date": trading_date,
        "close": close,
        "source_name": source_name,
        "source_url": source_url,
        "source_note": f"S&P 500 cash index; quote_type=cash_index; non-CFD; source symbol {symbol}.",
        "retrieved_at": stamp.astimezone(dt.timezone.utc).isoformat(timespec="seconds"),
        "retrieval_method": method,
        "retrieval_timestamp_semantics": "TAC D4 collector batch capture timestamp; per-request timestamp is not separately exposed."
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
                raise ValueError(f"Invalid existing JSONL at line {line_no}") from exc
            day = old.get("observation_date")
            if day in existing:
                raise ValueError(f"Duplicate existing observation date: {day}")
            existing[day] = old
    day = record["observation_date"]
    if day in existing:
        old = existing[day]
        if old == record:
            return "NOOP_IDENTICAL_OBSERVATION"
        stable = ("series_id", "instrument", "symbol", "observation_date", "close",
                  "source_name", "source_url", "source_note", "retrieval_method")
        if all(old.get(k) == record.get(k) for k in stable):
            return "NOOP_IDENTICAL_OBSERVATION"
        raise ValueError(f"Conflicting S&P 500 observation/source already exists for {day}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return "APPENDED"

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--d4-capture", type=Path, required=True)
    p.add_argument("--output", type=Path, default=Path("data/tac-chart3/sp500_tac_d4_close.jsonl"))
    a = p.parse_args()
    record = build_record(json.loads(a.d4_capture.read_text(encoding="utf-8")))
    status = append_record(a.output, record)
    print(json.dumps({"status": status, "observation_date": record["observation_date"],
                      "close": record["close"], "source_name": record["source_name"],
                      "record_sha256": record["record_sha256"]}, ensure_ascii=False))

if __name__ == "__main__":
    main()
