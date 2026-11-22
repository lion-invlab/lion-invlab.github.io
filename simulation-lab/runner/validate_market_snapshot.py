#!/usr/bin/env python3
"""Fail-closed per-indicator source/date/quote metadata validation for TAC's 44-row snapshot."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse
import re


EXPECTED_COUNTS = {
    "global_markets": 17,
    "sectors": 11,
    "bonds": 3,
    "fx": 6,
    "energy": 2,
    "metals": 2,
    "risk": 3,
}
EXPECTED_TOTAL = 44


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _validate_source(group: str, name: str, source: dict, trading_date: str) -> dict:
    for field in ("name", "url", "data_date", "quote_type", "note"):
        _require(bool(source.get(field)), f"{group}/{name}: source.{field} missing")
    parsed = urlparse(str(source["url"]))
    _require(parsed.scheme == "https" and bool(parsed.netloc), f"{group}/{name}: source URL must be HTTPS")
    _require(source["data_date"] == trading_date,
             f"{group}/{name}: source date {source['data_date']} != trading_date {trading_date}")
    raw_verification_time = (
        source.get("checked_at_tw")
        or source.get("checked_at")
        or source.get("read_at_taipei")
        or source.get("verified_at_tw")
    )
    has_clock_time = bool(
        isinstance(raw_verification_time, str)
        and re.search(r"\\d{4}-\\d{2}-\\d{2}[T ]\\d{2}:\\d{2}", raw_verification_time)
    )
    timestamp_status = (
        "EXACT_TIME" if has_clock_time
        else "DATE_ONLY" if raw_verification_time
        else "MISSING"
    )
    return {
        "group": group,
        "name": name,
        "data_date": source["data_date"],
        "quote_type": source["quote_type"],
        "source_name": source["name"],
        "source_url": source["url"],
        "verified_at_tw": raw_verification_time,
        "timestamp_status": timestamp_status,
    }


def validate_market_snapshot(data: dict, report_date: str) -> dict:
    _require(data.get("report_date") == report_date,
             f"report_date mismatch: {data.get('report_date')!r} != {report_date!r}")
    trading_date = str(data.get("trading_date") or "")
    _require(len(trading_date) == 10, "trading_date missing or malformed")

    rows = []
    counts = {}
    for group, expected in EXPECTED_COUNTS.items():
        if group == "sectors":
            values = data.get("sectors") or {}
            sources = data.get("sector_sources") or {}
            _require(set(values) == set(sources),
                     f"sectors/sector_sources key mismatch: values={sorted(values)} sources={sorted(sources)}")
            _require(len(values) == expected, f"sectors count {len(values)} != {expected}")
            for name, value in values.items():
                source = sources[name]
                row = _validate_source(group, name, source, trading_date)
                _require(source.get("quote_type") == "ETF_daily_close",
                         f"sectors/{name}: quote_type must be ETF_daily_close")
                _require(source.get("change_display") == value,
                         f"sectors/{name}: source change {source.get('change_display')!r} != display {value!r}")
                _require(isinstance(value, str) and value.endswith("%"),
                         f"sectors/{name}: display must be a percentage string")
                row["display"] = value
                rows.append(row)
        else:
            values = data.get(group) or {}
            _require(len(values) == expected, f"{group} count {len(values)} != {expected}")
            for name, item in values.items():
                _require(isinstance(item, dict), f"{group}/{name}: row must be an object")
                source = item.get("source") or {}
                row = _validate_source(group, name, source, trading_date)
                display = item.get("display")
                _require(display is not None and str(display).strip() != "",
                         f"{group}/{name}: display missing")
                row["display"] = display
                if item.get("change_display") is not None:
                    row["change_display"] = item["change_display"]

                if group == "global_markets":
                    quote_type = str(source.get("quote_type", "")).lower()
                    if "cfd" in quote_type:
                        _require(display == "待核實" and item.get("change_display") == "待核實",
                                 f"global_markets/{name}: CFD reference must be suppressed as 待核實")

                if group in ("energy", "metals"):
                    _require(source.get("quote_type") == "investing_historical_close",
                             f"{group}/{name}: commodity quote_type must be investing_historical_close")
                    _require(source.get("url") == item.get("instrument_url"),
                             f"{group}/{name}: source.url and instrument_url must match")
                    _require(source.get("history_close") == str(display),
                             f"{group}/{name}: history_close must equal displayed close")
                    _require(source.get("history_change") == item.get("change_display"),
                             f"{group}/{name}: history_change must equal displayed change")
                    _require(bool(item.get("contract_label")),
                             f"{group}/{name}: selected contract label missing")
                rows.append(row)
        counts[group] = expected

    _require(len(rows) == EXPECTED_TOTAL, f"total indicator rows {len(rows)} != {EXPECTED_TOTAL}")
    dates = sorted({row["data_date"] for row in rows})
    _require(dates == [trading_date], f"44-row common-date mismatch: {dates} != {[trading_date]}")

    timestamped = sum(1 for row in rows if row["timestamp_status"] == "EXACT_TIME")
    date_only = sum(1 for row in rows if row["timestamp_status"] == "DATE_ONLY")
    timestamp_missing = sum(1 for row in rows if row["timestamp_status"] == "MISSING")
    quote_types = {}
    for row in rows:
        quote_types[row["quote_type"]] = quote_types.get(row["quote_type"], 0) + 1
    return {
        "status": "PASS",
        "report_date": report_date,
        "trading_date": trading_date,
        "indicator_count": len(rows),
        "group_counts": counts,
        "common_data_dates": dates,
        "source_metadata_complete_count": len(rows),
        "per_item_timestamp_count": timestamped,
        "per_item_date_only_count": date_only,
        "per_item_timestamp_gap": len(rows) - timestamped,
        "per_item_timestamp_missing_count": timestamp_missing,
        "quote_type_counts": quote_types,
        "rows": rows,
        "timestamp_note": (
            "Only source records carrying a clock time count as exact per-item timestamps; "
            "date-only verification markers are reported separately. The batch acquisition window "
            "must remain documented separately and must not be inferred."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--report-date", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    data = json.loads(Path(args.data).read_text(encoding="utf-8"))
    result = validate_market_snapshot(data, args.report_date)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
