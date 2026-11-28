"""Wait until the exact Run trading date's US regular-session close."""
from __future__ import annotations

import json
import sys
import time
from datetime import date, datetime, time as wall_time
from pathlib import Path
from zoneinfo import ZoneInfo

NEW_YORK = ZoneInfo("America/New_York")


def seconds_until_trading_close(trading_date: str, now: datetime) -> float:
    """Return seconds until 16:00 New York time on trading_date; never negative."""
    target_date = date.fromisoformat(trading_date)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    target_close = datetime.combine(target_date, wall_time(16, 0), tzinfo=NEW_YORK)
    return max(0.0, (target_close - now.astimezone(NEW_YORK)).total_seconds())


def main(context_path: str) -> int:
    context = json.loads(Path(context_path).read_text(encoding="utf-8"))
    trading_date = context.get("trading_date")
    if not trading_date:
        raise SystemExit("Run context is missing trading_date; refusing an unbounded Stage 2 wait.")
    remaining = seconds_until_trading_close(trading_date, datetime.now(NEW_YORK))
    print(
        f"Run trading_date={trading_date}; target_close=16:00 America/New_York; "
        f"remaining_seconds={int(remaining)}",
        flush=True,
    )
    if remaining > 0:
        time.sleep(remaining)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
