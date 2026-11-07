#!/usr/bin/env python3
"""Collect the latest completed NYSE cash-index OHLC for TAC key levels.

This is a live-data collector, separate from the deterministic fixture tests.
It fails closed unless all five cash indices have the same latest completed
NYSE session and complete, valid daily OHLC bars.
"""
from __future__ import annotations

import json
import math
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


def collect(now: datetime | None = None) -> dict:
    now = now or datetime.now(TAIPEI)
    now = now.astimezone(TAIPEI)
    slot = expected_capture_slot(now)
    if now.strftime("%H:%M") != slot:
        raise ValueError(
            f"wrong schedule slot: Taipei={now:%Y-%m-%d %H:%M}; "
            f"expected {slot} for current US DST regime"
        )
    report_date = now.date()
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


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    result = collect()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"live_key_levels_capture: PASS report_date={result['report_date']} "
        f"trading_date={result['trading_date']} items={len(result['key_levels']['items'])}"
    )


if __name__ == "__main__":
    main()
