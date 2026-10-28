#!/usr/bin/env python3
"""Daily read-only TAC key-level collector. Writes a dated JSON report for CI artifacts only."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

TAIPEI = ZoneInfo("Asia/Taipei")
TICKERS = {
    "道瓊工業指數": "^DJI",
    "S&P 500": "^GSPC",
    "Nasdaq Composite": "^IXIC",
    "費城半導體指數（SOX）": "^SOX",
    "Russell 2000": "^RUT",
}
OUT = Path("artifacts/tac_key_levels_daily.json")


def get_history(symbol):
    df = yf.download(symbol, period="10d", interval="1d", auto_adjust=False,
                     progress=False, threads=False, group_by="column")
    if df is None or df.empty:
        raise ValueError(f"{symbol}: source returned no rows")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = pd.to_datetime(df.index).date
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fetched = datetime.now(timezone.utc)
    histories, errors = {}, []
    for name, symbol in TICKERS.items():
        try:
            histories[name] = (symbol, get_history(symbol))
        except Exception as exc:
            errors.append(f"{name} ({symbol}): {type(exc).__name__}: {exc}")

    result = {
        "schema_version": 1,
        "fetched_at_utc": fetched.isoformat(timespec="seconds"),
        "fetched_at_taipei": fetched.astimezone(TAIPEI).isoformat(timespec="seconds"),
        "source": "Yahoo Finance via yfinance; CI validation only, not production publication",
        "status": "incomplete",
        "session_date": None,
        "indexes": {},
        "errors": errors,
        "method": {
            "pivot": "(High + Low + Close) / 3",
            "support_s1": "2 * Pivot - High",
            "resistance_r1": "2 * Pivot - Low",
            "rounding": "2 decimal places for display; calculations use full precision",
        },
    }

    if not errors and len(histories) == len(TICKERS):
        latest_dates = {name: max(df.index) for name, (_, df) in histories.items() if len(df.index)}
        if len(latest_dates) != len(TICKERS):
            errors.append("At least one index has no dated rows.")
        elif len(set(latest_dates.values())) != 1:
            details = ", ".join(f"{name}={day.isoformat()}" for name, day in latest_dates.items())
            errors.append("Latest trading dates do not match across all five indexes: " + details)
        else:
            session = next(iter(latest_dates.values()))
            result["session_date"] = session.isoformat()
            for name, (symbol, df) in histories.items():
                row = df.loc[session]
                if isinstance(row, pd.DataFrame):
                    row = row.iloc[-1]
                try:
                    o, h, l, c = (float(row[k]) for k in ("Open", "High", "Low", "Close"))
                    if not all(pd.notna(v) and v > 0 for v in (o, h, l, c)):
                        raise ValueError(f"missing/non-positive OHLC: O={o}, H={h}, L={l}, C={c}")
                    if h < l or not (l <= o <= h and l <= c <= h):
                        raise ValueError(f"invalid OHLC bounds: O={o}, H={h}, L={l}, C={c}")
                    p = (h + l + c) / 3
                    result["indexes"][name] = {
                        "symbol": symbol, "date": session.isoformat(),
                        "open": o, "high": h, "low": l, "close": c,
                        "S1": 2 * p - h, "P": p, "R1": 2 * p - l,
                        "source": "Yahoo Finance via yfinance", "status": "ok",
                    }
                except Exception as exc:
                    errors.append(f"{name} ({symbol}) on {session}: {exc}")
                    result["indexes"][name] = {"symbol": symbol, "date": session.isoformat(), "status": "missing", "error": str(exc)}
            if not errors and len(result["indexes"]) == len(TICKERS):
                result["status"] = "complete"
    result["errors"] = errors
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"TAC Daily Key Levels | status={result['status']} | session={result['session_date']} | fetched_taipei={result['fetched_at_taipei']}")
    for name, item in result["indexes"].items():
        if item.get("status") == "ok":
            print(f"PASS | {name} | {item['date']} | S1 {item['S1']:,.2f} | P {item['P']:,.2f} | R1 {item['R1']:,.2f}")
        else:
            print(f"FAIL | {name} | {item.get('error', 'missing data')}")
    if result["status"] != "complete":
        print("Validation failed closed: do not use partial or stale values in the report.")
        for error in errors:
            print(f"ERROR | {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
