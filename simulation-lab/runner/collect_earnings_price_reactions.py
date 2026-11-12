#!/usr/bin/env python3
"""Read-only Yahoo Finance earnings reaction capture for the simulation review."""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from calendar_source_guard import load_authoritative_calendar

NY = ZoneInfo("America/New_York")


def reaction_window(event: dict) -> tuple[date, str] | None:
    if event.get("status") != "released":
        return None
    if not event.get("us_exchange_listed") or not event.get("us_listing_ticker"):
        return None
    session = event.get("session")
    if session not in ("before_market", "after_market"):
        return None
    stamp = event.get("event_date")
    if not stamp:
        return None
    dt = datetime.fromisoformat(stamp)
    if dt.tzinfo is None:
        return None
    return dt.astimezone(NY).date(), session


def calculate_reaction(close_by_date: dict[date, float], release_date: date, session: str):
    dates = sorted(close_by_date)
    if session == "before_market":
        reaction_days = [d for d in dates if d >= release_date]
    elif session == "after_market":
        reaction_days = [d for d in dates if d > release_date]
    else:
        return None
    if not reaction_days:
        return None
    reaction_day = reaction_days[0]
    previous_days = [d for d in dates if d < reaction_day]
    if not previous_days:
        return None
    previous_day = previous_days[-1]
    previous_close = close_by_date[previous_day]
    reaction_close = close_by_date[reaction_day]
    if not previous_close or not reaction_close:
        return None
    change = (reaction_close / previous_close - 1.0) * 100.0
    return {
        "reaction_date": reaction_day.isoformat(),
        "previous_date": previous_day.isoformat(),
        "previous_close": round(previous_close, 4),
        "reaction_close": round(reaction_close, 4),
        "change_pct": round(change, 2),
        "display": f"公告後首個交易日收盤 {change:+.2f}%（{previous_day:%m/%d}→{reaction_day:%m/%d}）",
        "source": f"Yahoo Finance historical daily close｜{previous_day.isoformat()}→{reaction_day.isoformat()}",
        "source_name": "Yahoo Finance歷史日收盤",
        "source_url": None,
    }


def extract_close_frame(frame, ticker: str):
    import pandas as pd

    if frame is None or frame.empty:
        return None
    if isinstance(frame.columns, pd.MultiIndex):
        level0 = list(frame.columns.get_level_values(0))
        level1 = list(frame.columns.get_level_values(1))
        if ticker in level0:
            sub = frame[ticker]
            if "Close" not in sub:
                return None
            series = sub["Close"]
        elif ticker in level1:
            sub = frame.xs(ticker, axis=1, level=1)
            if "Close" not in sub:
                return None
            series = sub["Close"]
        else:
            return None
    else:
        if "Close" not in frame:
            return None
        series = frame["Close"]
    series = series.dropna()
    out = {}
    for stamp, value in series.items():
        day = stamp.date() if hasattr(stamp, "date") else stamp
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number > 0:
            out[day] = number
    return out or None


def collect(report_date: str, output: str):
    import yfinance as yf

    bundle = load_authoritative_calendar(report_date)
    events = bundle["current"]["payload"]["events"]["earnings"]
    candidates = []
    for event in events:
        window = reaction_window(event)
        if window:
            candidates.append((event, window[0], window[1]))
    tickers = sorted({event["us_listing_ticker"] for event, _, _ in candidates})
    if not tickers:
        raise RuntimeError("no eligible released earnings with verified US listing and session")

    event_dates = [d for _, d, _ in candidates]
    start = min(event_dates) - timedelta(days=7)
    end = max(event_dates) + timedelta(days=8)
    frame = yf.download(
        tickers=tickers,
        start=start.isoformat(),
        end=end.isoformat(),
        auto_adjust=False,
        actions=False,
        group_by="ticker",
        progress=False,
        threads=True,
    )
    reactions = {}
    unavailable = {}
    for event, release_date, session in candidates:
        ticker = event["us_listing_ticker"]
        closes = extract_close_frame(frame, ticker)
        result = calculate_reaction(closes, release_date, session) if closes else None
        if not result:
            # Per-ticker fallback avoids losing valid closes when a batch response omits a symbol/date.
            try:
                single = yf.Ticker(ticker).history(
                    start=start.isoformat(), end=end.isoformat(), auto_adjust=False
                )
                closes = extract_close_frame(single, ticker)
                result = calculate_reaction(closes, release_date, session) if closes else None
            except Exception:
                result = None
        if not result:
            available = sorted(closes) if closes else []
            unavailable[event["id"]] = (
                "無法建立公告後首個交易日與前一交易日收盤配對；"
                f"可用日期={','.join(x.isoformat() for x in available)}"
            )
            continue
        result.update({
            "ticker": ticker,
            "company": event.get("company"),
            "session": session,
            "release_date_ny": release_date.isoformat(),
            "source_name": "Yahoo Finance歷史日收盤",
            "source_url": f"https://finance.yahoo.com/quote/{ticker}/history/",
        })
        reactions[event["id"]] = result

    # Apply independently sourced, date-locked overrides only to Yahoo gaps.
    # Every override is tied to the same authoritative main calendar SHA.
    override_path = Path(f"simulation-lab/fixtures/earnings-price-reaction-overrides-{report_date}.json")
    if override_path.exists():
        override_doc = json.loads(override_path.read_text(encoding="utf-8"))
        if override_doc.get("report_date") != report_date or override_doc.get("calendar_blob_sha") != bundle["current"]["blob_sha"]:
            raise RuntimeError("manual price-reaction override does not match report date/main calendar blob SHA")
        event_map = {event["id"]: event for event in events}
        for override in override_doc.get("overrides", []):
            event_id = override["event_id"]
            if event_id in reactions:
                continue
            event = event_map.get(event_id)
            if event is None or event_id not in unavailable:
                raise RuntimeError(f"manual override target is not an unresolved main earnings event: {event_id}")
            window = reaction_window(event)
            if not window:
                raise RuntimeError(f"manual override event is not eligible for price reaction: {event_id}")
            release_date, session = window
            if (override.get("ticker") != event.get("us_listing_ticker")
                    or override.get("session") != session
                    or override.get("release_date_ny") != release_date.isoformat()):
                raise RuntimeError(f"manual override event identity/session/date mismatch: {event_id}")
            previous_date = date.fromisoformat(override["previous_date"])
            reaction_date = date.fromisoformat(override["reaction_date"])
            expected_reaction_date = release_date if session == "before_market" else release_date + timedelta(days=1)
            if reaction_date != expected_reaction_date or previous_date >= reaction_date:
                raise RuntimeError(f"manual override reaction window mismatch: {event_id}")
            if not override.get("source_url", "").startswith("https://") or not override.get("source_name"):
                raise RuntimeError(f"manual override source URL/name missing: {event_id}")
            previous_close = float(override["previous_close"])
            reaction_close = float(override["reaction_close"])
            if previous_close <= 0 or reaction_close <= 0:
                raise RuntimeError(f"manual override prices must be positive: {event_id}")
            change = round((reaction_close / previous_close - 1.0) * 100.0, 2)
            reactions[event_id] = {
                "ticker": override["ticker"],
                "company": event.get("company"),
                "session": session,
                "release_date_ny": release_date.isoformat(),
                "previous_date": previous_date.isoformat(),
                "reaction_date": reaction_date.isoformat(),
                "previous_close": round(previous_close, 4),
                "reaction_close": round(reaction_close, 4),
                "change_pct": change,
                "display": f"公告後首個交易日收盤 {change:+.2f}%（{previous_date:%m/%d}→{reaction_date:%m/%d}）",
                "source": f"{override['source_name']}｜{previous_date.isoformat()}→{reaction_date.isoformat()}",
                "source_name": override["source_name"],
                "source_url": override["source_url"],
            }
            unavailable.pop(event_id, None)

    doc = {
        "report_date": report_date,
        "repository": "lion-invlab/lion-invlab.github.io",
        "branch": "main",
        "main_commit_sha": bundle["main_commit_sha"],
        "calendar_blob_sha": bundle["current"]["blob_sha"],
        "source": "Yahoo Finance historical daily close",
        "method": "before_market: release-day close vs previous trading-day close; after_market: next trading-day close vs release-day close",
        "eligible_count": len(candidates),
        "reaction_count": len(reactions),
        "unavailable_count": len(unavailable),
        "reactions": reactions,
        "unavailable": unavailable,
    }
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: doc[k] for k in ("report_date","main_commit_sha","calendar_blob_sha","eligible_count","reaction_count","unavailable_count")}, ensure_ascii=False))


def self_test():
    sample = {
        date(2026, 11, 6): 100.0,
        date(2026, 11, 9): 102.0,
        date(2026, 11, 10): 101.0,
        date(2026, 11, 11): 105.0,
    }
    pre = calculate_reaction(sample, date(2026, 11, 9), "before_market")
    post = calculate_reaction(sample, date(2026, 11, 9), "after_market")
    assert pre and pre["change_pct"] == 2.0
    assert post and post["change_pct"] == -0.98
    assert reaction_window({"status":"upcoming","us_exchange_listed":True,"us_listing_ticker":"ABC","session":"before_market","event_date":"2026-11-12T08:00:00-05:00"}) is None
    print("PASS: earnings reaction window and close-to-close calculation")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-date")
    parser.add_argument("--output")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    else:
        if not args.report_date or not args.output:
            parser.error("--report-date and --output are required unless --self-test is used")
        collect(args.report_date, args.output)
