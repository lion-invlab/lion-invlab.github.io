"""Map validated calendar records into explicit per-card write payloads.

This layer formats values and source anchors only. It never selects or mutates
HTML nodes; DOM writes remain the responsibility of guarded updater functions.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from tac_calendar_dataset import (
    PRIOR_WEEK_STATUS, WEEKLY_STATUS_ORDER, validate_calendar_dataset,
)

WEEKDAY_ZH = "一二三四五六日"
SESSION_LABELS = {
    "pre_market": "盤前",
    "during_market": "盤中",
    "after_market": "盤後",
    "unspecified": "",
}


def format_calendar_date(value):
    parsed = date.fromisoformat(value)
    return f"{parsed.month:02d}/{parsed.day:02d}（{WEEKDAY_ZH[parsed.weekday()]}）"


def format_stars(importance):
    return "★" * importance + "☆" * (5 - importance)


def _format_time(value):
    if value in (None, ""):
        return "待核實"
    parsed = time.fromisoformat(value)
    return f"{parsed.hour:02d}:{parsed.minute:02d}"


def _source_payload(records):
    grouped = defaultdict(list)
    provenance = []
    for source in records:
        grouped[source["field_label"]].append({
            "href": source["url"],
            "label": source["label"],
        })
        provenance.append({
            "source_name": source["source_name"],
            "field_label": source["field_label"],
            "url": source["url"],
            "accessed_at": source["accessed_at"],
        })
    return dict(grouped), provenance


def map_economic_event(event):
    sources, provenance = _source_payload(event["source_records"])
    return {
        "event_id": event["event_id"],
        "status_group": event["status_group"],
        "summary": {
            "date": format_calendar_date(event["event_date"]),
            "time": _format_time(event.get("event_time")),
            "country": event["country"],
            "name": event["event_name"],
            "stars": format_stars(event["importance"]),
        },
        "details": dict(event.get("details", {})),
        "sources": sources,
        "provenance": provenance,
    }


def map_earnings_event(event):
    sources, provenance = _source_payload(event["source_records"])
    session_label = SESSION_LABELS[event.get("release_session", "unspecified")]
    us_date = format_calendar_date(event["event_date"])
    if session_label:
        us_date = f"{us_date} {session_label}"

    taiwan_date = format_calendar_date(event["taiwan_display_date"])
    taiwan_label = f"台灣時間 {taiwan_date}"
    if event.get("event_time") not in (None, ""):
        announced_at = datetime.combine(
            date.fromisoformat(event["event_date"]),
            time.fromisoformat(event["event_time"]),
            tzinfo=ZoneInfo(event["event_timezone"]),
        )
        taiwan_at = announced_at.astimezone(ZoneInfo("Asia/Taipei"))
        taiwan_label = (
            f"台灣時間 {format_calendar_date(taiwan_at.date().isoformat())} "
            f"{taiwan_at.hour:02d}:{taiwan_at.minute:02d}"
        )

    return {
        "event_id": event["event_id"],
        "status_group": event["status_group"],
        "summary": {
            "us_date": us_date,
            "taiwan_date": taiwan_label,
            "company_name": event["company_name"],
            "subtitle": event.get("subtitle", ""),
            "stars": format_stars(event["importance"]),
        },
        "details": dict(event.get("details", {})),
        "sources": sources,
        "provenance": provenance,
    }


def map_calendar_dataset(dataset):
    """Return status-grouped card payloads from a validated dataset."""
    validated = validate_calendar_dataset(dataset)

    def group_events(events, mapper, statuses):
        grouped = {status: [] for status in statuses}
        for event in events:
            grouped[event["status_group"]].append(mapper(event))
        return grouped

    return {
        "template": validated["template"],
        "weekly_economic": group_events(
            validated["economic_events"], map_economic_event, WEEKLY_STATUS_ORDER
        ),
        "weekly_earnings": group_events(
            validated["earnings_events"], map_earnings_event, WEEKLY_STATUS_ORDER
        ),
        "prior_week_economic": group_events(
            validated["prior_week_economic_events"], map_economic_event,
            (PRIOR_WEEK_STATUS,),
        ),
        "prior_week_earnings": group_events(
            validated["prior_week_earnings_events"], map_earnings_event,
            (PRIOR_WEEK_STATUS,),
        ),
    }
