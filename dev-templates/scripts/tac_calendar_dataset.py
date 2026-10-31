"""Canonical, provenance-preserving calendar dataset contract for TAC.

This is a validation/ordering layer only. It does not fetch data, infer missing
facts, mutate HTML, or authorize production writes.
"""
from __future__ import annotations

from datetime import date, datetime
from urllib.parse import urlsplit

from tac_calendar_sort import sort_economic_events, sort_earnings_events

SCHEMA_VERSION = "tac-calendar-dataset-v1"
TEMPLATES = {"monday", "weekdays"}
SESSIONS = {"pre_market", "during_market", "after_market", "unspecified"}


def _required_text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _iso_date(value, field):
    _required_text(value, field)
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO YYYY-MM-DD") from exc


def _optional_time(value, field):
    if value in (None, ""):
        return
    if not isinstance(value, str):
        raise ValueError(f"{field} must be HH:MM, HH:MM:SS, or null")
    from datetime import time
    try:
        time.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be HH:MM or HH:MM:SS") from exc


def _validate_sources(sources, field):
    if not isinstance(sources, list) or not sources:
        raise ValueError(f"{field} must contain at least one provenance record")
    for index, source in enumerate(sources):
        prefix = f"{field}[{index}]"
        if not isinstance(source, dict):
            raise ValueError(f"{prefix} must be an object")
        _required_text(source.get("source_name"), f"{prefix}.source_name")
        _required_text(source.get("label"), f"{prefix}.label")
        url = _required_text(source.get("url"), f"{prefix}.url")
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"{prefix}.url must be an absolute HTTP(S) URL")
        if parsed.username or parsed.password or any(ord(ch) < 32 for ch in url):
            raise ValueError(f"{prefix}.url is unsafe")
        accessed_at = _required_text(source.get("accessed_at"), f"{prefix}.accessed_at")
        try:
            stamp = datetime.fromisoformat(accessed_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{prefix}.accessed_at must be ISO-8601 with timezone") from exc
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise ValueError(f"{prefix}.accessed_at must include a timezone offset")


def _validate_common(event, index, group):
    prefix = f"{group}[{index}]"
    if not isinstance(event, dict):
        raise ValueError(f"{prefix} must be an object")
    _required_text(event.get("event_id"), f"{prefix}.event_id")
    _iso_date(event.get("event_date"), f"{prefix}.event_date")
    _required_text(event.get("event_timezone"), f"{prefix}.event_timezone")
    importance = event.get("importance")
    if isinstance(importance, bool) or not isinstance(importance, int) or not 1 <= importance <= 5:
        raise ValueError(f"{prefix}.importance must be an integer from 1 to 5")
    _optional_time(event.get("event_time"), f"{prefix}.event_time")
    if "details" in event:
        details = event["details"]
        if not isinstance(details, dict) or any(
            not isinstance(label, str) or not label.strip()
            or not isinstance(value, str) for label, value in details.items()
        ):
            raise ValueError(f"{prefix}.details must map labels to strings")
    _validate_sources(event.get("source_records"), f"{prefix}.source_records")


def validate_calendar_dataset(dataset):
    """Validate and return a sorted shallow-copy dataset; never fill missing data."""
    if not isinstance(dataset, dict):
        raise ValueError("dataset must be an object")
    if dataset.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
    _iso_date(dataset.get("report_date"), "report_date")
    if dataset.get("template") not in TEMPLATES:
        raise ValueError("template must be monday or weekdays")

    economic = dataset.get("economic_events")
    earnings = dataset.get("earnings_events")
    if not isinstance(economic, list) or not isinstance(earnings, list):
        raise ValueError("economic_events and earnings_events must be arrays")

    for index, event in enumerate(economic):
        _validate_common(event, index, "economic_events")
        _required_text(event.get("country"), f"economic_events[{index}].country")
        _required_text(event.get("event_name"), f"economic_events[{index}].event_name")

    for index, event in enumerate(earnings):
        _validate_common(event, index, "earnings_events")
        _iso_date(event.get("taiwan_display_date"), f"earnings_events[{index}].taiwan_display_date")
        _required_text(event.get("company_name"), f"earnings_events[{index}].company_name")
        subtitle = event.get("subtitle", "")
        if not isinstance(subtitle, str):
            raise ValueError(f"earnings_events[{index}].subtitle must be a string")
        if event.get("release_session", "unspecified") not in SESSIONS:
            raise ValueError(f"earnings_events[{index}].release_session is invalid")

    for group_name, events in (("economic_events", economic), ("earnings_events", earnings)):
        ids = [event["event_id"] for event in events]
        if len(ids) != len(set(ids)):
            raise ValueError(f"{group_name} contains duplicate event_id values")

    result = dict(dataset)
    result["economic_events"] = sort_economic_events(economic)
    result["earnings_events"] = sort_earnings_events(earnings)
    return result
