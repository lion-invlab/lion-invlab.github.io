#!/usr/bin/env python3
"""Live smoke test for the Investing.com S&P 500 daily historical endpoint.

This test intentionally fetches only a recent window. It verifies the real
endpoint, response schema, numeric closes, and freshness without rewriting
the long historical dataset.
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import update_sp500_daily_incremental as updater


def main() -> None:
    today = dt.datetime.now(updater.ET).date()
    end_exclusive = today + dt.timedelta(days=1)
    start = today - dt.timedelta(days=45)
    response = updater.fetch_chart(start, end_exclusive, retries=3)
    rows = updater.parse_chart(response)
    if len(rows) < 10:
        raise RuntimeError(f"Live Investing.com response too short: {len(rows)} rows")
    latest = max(rows)
    age = (today - dt.date.fromisoformat(latest)).days
    if age > 10:
        raise RuntimeError(f"Live Investing.com S&P 500 data stale: latest={latest}, today={today}")
    if not all(isinstance(v, int) and v > 0 for v in rows.values()):
        raise RuntimeError("Live Investing.com response contains invalid close values")
    print({
        "status": "PASS",
        "source": "Investing.com",
        "instrument_id": updater.INVESTING_INSTRUMENT_ID,
        "requested_start": start.isoformat(),
        "requested_end_exclusive": end_exclusive.isoformat(),
        "rows": len(rows),
        "latest_date": latest,
        "latest_close": rows[latest] / 100,
        "raw_response_sha256": response["raw_sha256"],
    })


if __name__ == "__main__":
    main()
