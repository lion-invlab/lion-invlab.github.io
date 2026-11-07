#!/usr/bin/env python3
"""Collect the latest completed NYSE cash-index OHLC for TAC key levels.

This is a live-data collector, separate from the deterministic fixture tests.
It fails closed unless all five cash indices have the same latest completed
NYSE session and complete, valid daily OHLC bars.
"""
from __future__ import annotations

import json
import math
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

import pandas_market_calendars as mcal
import yfinance as yf

from key_levels_builder import REQUIRED, EXPECTED, build

SYMBOLS = {
    "dow": ("^DJI", "%5EDJI"),
    "sp500": ("^GSPC", "%5EGSPC"),
    "nasdaq": ("^IXIC", "%5EIXIC"),
    "sox": ("^SOX", "%5ESOX"),
    "russell2000": ("^RUT", "%5ERUT"),
}
TAIPEI = ZoneInfo("Asia/Taipei")
NEW_YORK = ZoneInfo("America/New_York")


def number(value: object, label: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ValueError(f"{label}: invalid OHLC number {value!r}")
    return result


def expected_capture_slot(now_taipei: datetime) -> str:
    # TAC report is assembled at 05:00 in US daylight time and 05:25 in
    # US standard time. Capture ten minutes before the report.
    is_dst = bool(now_taipei.astimezone(NEW_YORK).dst())
    return "04:50" if is_dst else "05:15"


def collect(now: datetime | None = None, allow_manual: bool = False, report_date_override: str | None = None) -> dict:
    now = now or datetime.now(TAIPEI)
    now = now.astimezone(TAIPEI)
    slot = expected_capture_slot(now)
    expected_time = datetime.combine(
        now.date(), datetime.strptime(slot, "%H:%M").time(), tzinfo=TAIPEI
    )
    # GitHub scheduled workflows can start late; allow a 10-minute window.
    if not allow_manual and abs((now - expected_time).total_seconds()) > 600:
        raise ValueError(
            f"wrong schedule slot: Taipei={now:%Y-%m-%d %H:%M:%S}; "
            f"expected {slot} +/- 10 minutes for current US DST regime"
        )
    report_date = date.fromisoformat(report_date_override) if report_date_override else now.date()
    if report_date.weekday() > 4:
        raise ValueError(f"report date is not a weekday: {report_date}")

    # Determine the previous actual NYSE session (handles weekends and
    # exchange holidays); do not infer the date by subtracting one day.
    cal = mcal.get_calendar("NYSE")
    schedule = cal.schedule(
        start_date=(report_date - timedelta(days=14)).isoformat(),
        end_date=(report_date - timedelta(days=1)).isoformat(),
    )
    if schedule.empty:
        raise ValueError("NYSE calendar returned no prior session")
    trading_date = schedule.index[-1].date().isoformat()

    items = []
    for key in REQUIRED:
        symbol, url_symbol = SYMBOLS[key]
        start = (date.fromisoformat(trading_date) - timedelta(days=2)).isoformat()
        end = (date.fromisoformat(trading_date) + timedelta(days=1)).isoformat()
        frame = yf.Ticker(symbol).history(
            start=start, end=end, interval="1d",
            auto_adjust=False, actions=False
        )
        if frame is None or frame.empty:
            raise ValueError(f"{key}: Yahoo Finance returned no daily bars")
        rows = [(idx.date().isoformat(), row) for idx, row in frame.iterrows()]
        matches = [(day, row) for day, row in rows if day == trading_date]
        if len(matches) != 1:
            available = [day for day, _ in rows]
            raise ValueError(
                f"{key}: expected exactly one bar for {trading_date}; got {available}"
            )
        _, row = matches[0]
        values = {
            field: number(row[field], f"{key}.{field}")
            for field in ("Open", "High", "Low", "Close")
        }
        if values["High"] < values["Low"]:
            raise ValueError(f"{key}: High is below Low")
        if not values["Low"] <= values["Open"] <= values["High"]:
            raise ValueError(f"{key}: Open outside High/Low")
        if not values["Low"] <= values["Close"] <= values["High"]:
            raise ValueError(f"{key}: Close outside High/Low")
        items.append({
            "key": key,
            "name": EXPECTED[key],
            "symbol": symbol,
            "trading_date": trading_date,
            **{field.lower(): value for field, value in values.items()},
            "source_name": "Yahoo Finance historical data",
            "source_url": f"https://finance.yahoo.com/quote/{url_symbol}/history/?frequency=1d",
            "quote_type": "cash_index",
        })

    payload = {
        "report_date": report_date.isoformat(),
        "trading_date": trading_date,
        "timezone": "America/New_York",
        "formula": "P=(H+L+C)/3; S1=2P-H; R1=2P-L",
        "items": items,
    }
    levels = build(payload, report_date.isoformat())
    return {
        "schema_version": "1.0",
        "report_date": report_date.isoformat(),
        "trading_date": trading_date,
        "captured_at_taipei": now.isoformat(),
        "timezone": "Asia/Taipei",
        "source": "Yahoo Finance historical daily cash-index OHLC",
        "key_levels": levels,
    }


def self_test() -> None:
    winter = datetime(2026, 1, 12, 5, 15, tzinfo=TAIPEI)
    summer = datetime(2026, 7, 13, 4, 50, tzinfo=TAIPEI)
    assert expected_capture_slot(winter) == "05:15"
    assert expected_capture_slot(summer) == "04:50"
    sample = {
        "report_date": "2026-11-09", "trading_date": "2026-11-06",
        "items": [{
            "key": key, "name": EXPECTED[key], "symbol": SYMBOLS[key][0],
            "trading_date": "2026-11-06", "high": 110, "low": 90, "close": 100,
            "source_name": "test source", "source_url": "https://example.com/ohlc",
            "quote_type": "cash_index"
        } for key in REQUIRED]
    }
    result = build(sample, "2026-11-09")
    assert len(result["items"]) == 5 and result["items"][0]["p"] == "100.00"
    print("collect_key_levels_ohlc self-test: PASS")


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    ap.add_argument("--allow-manual", action="store_true", help="bypass clock-slot guard for an intentional manual run")
    ap.add_argument("--report-date", help="report date to build for; defaults to today's Taipei date")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return
    if not args.output:
        ap.error("--output is required unless --self-test is used")
    result = collect(
        allow_manual=(args.allow_manual or os.getenv('GITHUB_EVENT_NAME') == 'workflow_dispatch'),
        report_date_override=args.report_date,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"live_key_levels_capture: PASS report_date={result['report_date']} "
        f"trading_date={result['trading_date']} items={len(result['key_levels']['items'])}"
    )


if __name__ == "__main__":
    main()
