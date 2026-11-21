#!/usr/bin/env python3
"""Regression tests for elapsed earnings releases with unverified issuer actuals."""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_review_html import apply_report_layer_earnings_status, classify_calendar_group, calendar_actual_display, earnings_status_label, earnings_commentary

EVENT = {
    "id": "current-rost-20261120",
    "ticker": "ROST",
    "event_date": "2026-11-20T05:00:00+08:00",
    "status": "upcoming",
    "eps_actual": None,
    "revenue_actual": None,
    "judgment": "",
}

def fixture(status="pending_verification", event_date=EVENT["event_date"]):
    event = dict(EVENT, event_date=event_date)
    return {
        "report_cutoff_taipei": "2026-11-20 05:25",
        "earnings": {"events": [event]},
        "report_layer_earnings_status": [{
            "event_id": EVENT["id"],
            "ticker": "ROST",
            "event_date": event_date,
            "status": status,
            "status_source": {
                "name": "Investing.com（轉述Reuters；僅核對發布狀態）",
                "url": "https://hk.investing.com/news/earnings/article-1768330",
            },
            "note": "公告時間已過；第三方報導指出結果已發布，但官方實際值待核實。",
        }],
    }

def main():
    data = fixture()
    assert apply_report_layer_earnings_status(data) == 1
    event = data["earnings"]["events"][0]
    assert event["status"] == "pending_verification"
    assert event["eps_actual"] is None and event["revenue_actual"] is None
    assert earnings_status_label(event, "eps", "pending") == "公告已發布；實際值待核實"
    assert "官方實際值待核實" in earnings_commentary(event)

    # Calendar grouping must compare aware event timestamps with a Taipei-local cutoff.
    assert classify_calendar_group(event, "2026-11-20", "2026-11-20 05:25") == "published"
    assert event["_calendar_publication_state"] == "pending_verification"
    assert earnings_status_label(event, "eps", "pending") == "公告已發布；實際值待核實"
    assert calendar_actual_display(event, "2026-11-20 05:25") == "公告已發布；實際值待核實"

    # A report-layer flag must not force a future event into the published group.
    future = dict(EVENT, event_date="2026-11-20T06:00:00+08:00", status="pending_verification",
                  report_layer_status_only=True, report_layer_status_source={"url": "https://example.com/status"},
                  time_known=True)
    assert classify_calendar_group(future, "2026-11-20", "2026-11-20 05:25") == "today"

    # Source timestamps in another timezone must be converted before deriving the Taiwan event date.
    cross_tz = dict(EVENT, event_date="2026-11-22T17:00:00-05:00", status="upcoming", time_known=True)
    assert classify_calendar_group(cross_tz, "2026-11-23", "2026-11-23 05:25") == "today"

    # An elapsed but unverified event remains pending; it is never promoted to released.
    stale = dict(EVENT, event_date="2026-11-19T09:00:00+08:00", status="upcoming", time_known=True)
    assert classify_calendar_group(stale, "2026-11-20", "2026-11-20 05:25") == "published"
    assert stale["_calendar_publication_state"] == "pending_verification"
    assert earnings_status_label(stale, "eps", "pending") == "公布狀態待核實"
    assert calendar_actual_display(stale, "2026-11-20 05:25") == "公布狀態待核實"

    cancelled = dict(EVENT, event_date="2026-11-20T07:00:00+08:00", status="cancelled", time_known=True)
    assert classify_calendar_group(cancelled, "2026-11-20", "2026-11-20 05:25") == "upcoming"
    assert cancelled["_calendar_publication_state"] == "cancelled"
    assert earnings_status_label(cancelled, "eps", "pending") == "已取消"
    assert calendar_actual_display(cancelled, "2026-11-20 05:25") == "已取消"

    late = fixture(event_date="2026-11-20T06:00:00+08:00")
    try:
        apply_report_layer_earnings_status(late)
    except ValueError as exc:
        assert "later than report cutoff" in str(exc)
    else:
        raise AssertionError("late status overlay must be rejected")

    invalid = fixture(status="released")
    try:
        apply_report_layer_earnings_status(invalid)
    except ValueError as exc:
        assert "only set pending_verification" in str(exc)
    else:
        raise AssertionError("status overlay must not claim released actuals")

    print("PASS: report-layer pending-verification status is cutoff-bound and does not fabricate actuals")

if __name__ == "__main__":
    main()
