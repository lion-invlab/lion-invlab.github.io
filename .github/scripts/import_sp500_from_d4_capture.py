#!/usr/bin/env python3
"""Append one S&P 500 close from an existing TAC D4 capture or report record.

This adapter never fetches market data. It consumes a machine-readable capture
already produced by TAC and preserves the actual per-observation source.
"""
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
            raise ValueError("S&P 500 item must include close or an OHLC string with C value")
        value = float(match.group(1).replace(",", ""))
    if not math.isfinite(value) or value <= 0:
        raise ValueError("S&P 500 close must be positive and finite")
    return round(value, 2)

def parse_display(value: str) -> float:
    try:
        result = float(str(value).replace(",", "").replace("$", "").strip())
    except Exception as exc:
        raise ValueError("TAC report S&P 500 display must contain a numeric close") from exc
    if not math.isfinite(result) or result <= 0:
        raise ValueError("TAC report S&P 500 close must be positive and finite")
    return round(result, 2)

def aware_timestamp(value: str) -> dt.datetime:
    try:
        stamp = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception as exc:
        raise ValueError("retrieved_at must be ISO-8601") from exc
    if stamp.tzinfo is None:
        raise ValueError("retrieved_at must include timezone")
    return stamp

def build_from_d4_capture(capture: dict) -> dict:
    captured_at = capture.get("captured_at_taipei") or capture.get("captured_at")
    if not captured_at:
        raise ValueError("D4 capture timestamp must include captured_at_taipei/captured_at")
    stamp = aware_timestamp(captured_at)
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
    host = (urlparse(source_url).hostname or "").lower()
    if host == "finance.yahoo.com" and "yahoo" not in source_name.lower():
        raise ValueError("Yahoo URL/source_name mismatch")
    if (host == "investing.com" or host.endswith(".investing.com")) and "investing.com" not in source_name.lower():
        raise ValueError("Investing.com URL/source_name mismatch")
    close = parse_close(item)
    method = "tac_d4_yfinance_daily_history" if "yahoo" in source_name.lower() else "tac_d4_source_verified_daily_history"
    return make_record(report_date, trading_date, close, source_name, source_url,
                       f"S&P 500 cash index; quote_type=cash_index; source symbol {symbol}.",
                       stamp, method,
                       "TAC D4 collector batch capture timestamp; per-request timestamp is not separately exposed.",
                       symbol)

def build_from_report_data(report: dict) -> dict:
    report_date = str(report.get("report_date") or "")
    trading_date = str(report.get("trading_date") or "")
    dt.date.fromisoformat(report_date)
    dt.date.fromisoformat(trading_date)

    # Prefer D4's same-session OHLC source record when it exists.
    override = (report.get("key_levels_overrides") or {}).get("sp500")
    if isinstance(override, dict):
        if override.get("trading_date") != trading_date:
            raise ValueError("TAC report S&P 500 override trading_date mismatch")
        source_name = str(override.get("source_name") or "").strip()
        source_url = str(override.get("source_url") or "").strip()
        note = str(override.get("note") or "")
        if not ("現金指數" in note or "cash index" in note.lower()):
            raise ValueError("TAC report S&P 500 override must explicitly identify a cash index")
        close = parse_close(override)
        symbol = "^SPX" if "^SPX" in (source_name + " " + note) else None
        stamp_value = override.get("retrieved_at") or report.get("market_data_captured_at")
        if not stamp_value:
            raise ValueError("TAC report override requires exact retrieved_at or market_data_captured_at")
        stamp = aware_timestamp(stamp_value)
        method = override.get("retrieval_method") or "tac_report_verified_ohlc_source_record"
        timestamp_semantics = ("source record's explicit retrieval timestamp" if override.get("retrieved_at")
                               else "explicit TAC market-data capture timestamp; per-request timestamp is not separately exposed")
        return make_record(report_date, trading_date, close, source_name, source_url, note,
                           stamp, method, timestamp_semantics, symbol)

    market = (report.get("global_markets") or {}).get("標普500指數")
    if not isinstance(market, dict) or not isinstance(market.get("source"), dict):
        raise ValueError("TAC report has no global_markets['標普500指數'].source record")
    source = market["source"]
    data_date = str(source.get("data_date") or "")
    if data_date != trading_date:
        raise ValueError("TAC report S&P 500 source data_date does not match trading_date")
    quote_type = str(source.get("quote_type") or "")
    if quote_type not in ("cash_index", "cash_index_close"):
        raise ValueError(f"TAC report S&P 500 quote_type is not a cash index close: {quote_type!r}")
    source_name = str(source.get("name") or "").strip()
    source_url = str(source.get("url") or "").strip()
    note = str(source.get("note") or f"TAC report explicitly classifies this as {quote_type}.")
    stamp_value = source.get("retrieved_at") or market.get("retrieved_at") or report.get("market_data_captured_at")
    if not stamp_value:
        raise ValueError("TAC report source requires exact retrieved_at or market_data_captured_at")
    stamp = aware_timestamp(stamp_value)
    method = source.get("retrieval_method") or "tac_report_verified_market_close_source_record"
    timestamp_semantics = ("source record's explicit retrieval timestamp" if source.get("retrieved_at")
                           else "explicit TAC market-data capture timestamp; per-request timestamp is not separately exposed")
    return make_record(report_date, trading_date, parse_display(market.get("display")), source_name,
                       source_url, note, stamp, method, timestamp_semantics, source.get("symbol"))

def make_record(report_date, trading_date, close, source_name, source_url, note,
                stamp, method, timestamp_semantics, symbol=None):
    parsed = urlparse(source_url)
    if not source_name or parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("S&P 500 source_name and valid HTTPS source_url are required")
    lower_note = str(note).lower()
    if not ("現金指數" in str(note) or "cash index" in lower_note or "cash_index" in lower_note):
        raise ValueError("S&P 500 source note must identify a cash index")
    if "cfd" in lower_note and not any(x in lower_note for x in ("非cfd", "non-cfd", "not cfd")):
        raise ValueError("CFD observations cannot enter the S&P 500 cash-index history")
    record = {
        "schema_version": "1.0",
        "series_id": "SP500",
        "instrument": "S&P 500 cash price index",
        "report_date": report_date,
        "observation_date": trading_date,
        "close": round(float(close), 2),
        "source_name": source_name,
        "source_url": source_url,
        "source_note": str(note),
        "retrieved_at": stamp.astimezone(dt.timezone.utc).isoformat(),
        "retrieval_method": str(method),
        "retrieval_timestamp_semantics": timestamp_semantics
    }
    if symbol:
        record["symbol"] = str(symbol)
    record["record_sha256"] = hashlib.sha256(canonical(record)).hexdigest()
    return record

def build_record(capture: dict) -> dict:
    if isinstance(capture.get("key_levels"), dict):
        return build_from_d4_capture(capture)
    return build_from_report_data(capture)

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
        stable = ("series_id", "instrument", "observation_date", "close",
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
    p.add_argument("--capture", type=Path, required=True,
                   help="TAC D4 collector output or TAC report-data JSON")
    p.add_argument("--output", type=Path, default=Path("data/tac-chart3/sp500_tac_d4_close.jsonl"))
    a = p.parse_args()
    record = build_record(json.loads(a.capture.read_text(encoding="utf-8")))
    status = append_record(a.output, record)
    print(json.dumps({"status": status, "observation_date": record["observation_date"],
                      "close": record["close"], "source_name": record["source_name"],
                      "record_sha256": record["record_sha256"]}, ensure_ascii=False))

if __name__ == "__main__":
    main()
