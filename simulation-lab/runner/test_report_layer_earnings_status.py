#!/usr/bin/env python3
"""Regression tests for elapsed earnings releases with unverified issuer actuals."""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_review_html import apply_report_layer_earnings_status, earnings_status_label, earnings_commentary

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
