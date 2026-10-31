"""Deterministic calendar sorting helpers for TAC test data.

The functions sort normalized records only; they do not parse or mutate mother
template HTML and are not a production data importer.
"""
from datetime import date, time


SESSION_ORDER = {
    "pre_market": 0,
    "during_market": 1,
    "after_market": 2,
    "unspecified": 3,
}


def _required_date(value):
    if not isinstance(value, str):
        raise ValueError("event_date must be an ISO YYYY-MM-DD string")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid event_date: {value}") from exc


def _optional_time(value):
    if value in (None, ""):
        return time.max
    if not isinstance(value, str):
        raise ValueError("event_time must be HH:MM, HH:MM:SS, or null")
    try:
        return time.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid event_time: {value}") from exc


def sort_economic_events(events):
    """Sort by event date then local publication time; unknown times come last."""
    indexed = list(enumerate(events))
    indexed.sort(
        key=lambda pair: (
            _required_date(pair[1]["event_date"]),
            _optional_time(pair[1].get("event_time")),
            pair[0],
        )
    )
    return [item for _, item in indexed]


def sort_earnings_events(events):
    """Sort by US publication date, then release session, then known US time."""
    indexed = list(enumerate(events))
    indexed.sort(
        key=lambda pair: (
            _required_date(pair[1]["event_date"]),
            SESSION_ORDER.get(pair[1].get("release_session", "unspecified"), 3),
            _optional_time(pair[1].get("event_time")),
            pair[0],
        )
    )
    return [item for _, item in indexed]
