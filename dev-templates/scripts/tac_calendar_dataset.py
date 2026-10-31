"""Canonical, provenance-preserving calendar dataset contract for TAC.

Validation and deterministic ordering only: no fetching, fact inference, HTML
mutation, or production-write authorization.
"""
from __future__ import annotations

from datetime import date, datetime, time
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from tac_calendar_sort import sort_economic_events, sort_earnings_events

SCHEMA_VERSION = "tac-calendar-dataset-v1"
TEMPLATES = {"monday", "weekdays"}
SESSIONS = {"pre_market", "during_market", "after_market", "unspecified"}
WEEKLY_STATUS_ORDER = ("today", "upcoming", "published")
PRIOR_WEEK_STATUS = "prior_week_published"


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
    try:
        parsed = time.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be HH:MM or HH:MM:SS") from exc
    if parsed.tzinfo is not None:
        raise ValueError(f"{field} must be a local wall-clock time without an offset")


def _validate_sources(sources, field):
    if not isinstance(sources, list) or not sources:
        raise ValueError(f"{field} must contain at least one provenance record")
    for index, source in enumerate(sources):
        prefix = f"{field}[{index}]"
        if not isinstance(source, dict):
            raise ValueError(f"{prefix} must be an object")
        _required_text(source.get("source_name"), f"{prefix}.source_name")
        _required_text(source.get("field_label"), f"{prefix}.field_label")
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


def _validate_common(event, index, group, allowed_statuses):
    prefix = f"{group}[{index}]"
    if not isinstance(event, dict):
        raise ValueError(f"{prefix} must be an object")
    _required_text(event.get("event_id"), f"{prefix}.event_id")
    _iso_date(event.get("event_date"), f"{prefix}.event_date")
    timezone_name = _required_text(event.get("event_timezone"), f"{prefix}.event_timezone")
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"{prefix}.event_timezone must be a valid IANA timezone") from exc
    status = event.get("status_group")
    if not isinstance(status, str) or status not in allowed_statuses:
        raise ValueError(f"{prefix}.status_group must be one of {sorted(allowed_statuses)}")
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


def _validate_group(events, group, kind, allowed_statuses):
    if not isinstance(events, list):
        raise ValueError(f"{group} must be an array")
    for index, event in enumerate(events):
        _validate_common(event, index, group, allowed_statuses)
        if kind == "economic":
            if event["event_timezone"] != "Asia/Taipei":
                raise ValueError(f"{group}[{index}].event_timezone must be Asia/Taipei after display-time normalization")
            _required_text(event.get("country"), f"{group}[{index}].country")
            _required_text(event.get("event_name"), f"{group}[{index}].event_name")
        else:
            _iso_date(event.get("taiwan_display_date"), f"{group}[{index}].taiwan_display_date")
            _required_text(event.get("company_name"), f"{group}[{index}].company_name")
            subtitle = event.get("subtitle", "")
            if not isinstance(subtitle, str):
                raise ValueError(f"{group}[{index}].subtitle must be a string")
            session = event.get("release_session", "unspecified")
            if not isinstance(session, str) or session not in SESSIONS:
                raise ValueError(f"{group}[{index}].release_session is invalid")
            if event.get("event_time") not in (None, ""):
                local_date = date.fromisoformat(event["event_date"])
                local_time = time.fromisoformat(event["event_time"])
                announced_at = datetime.combine(
                    local_date, local_time, tzinfo=ZoneInfo(event["event_timezone"])
                )
                converted_date = announced_at.astimezone(ZoneInfo("Asia/Taipei")).date().isoformat()
                if converted_date != event["taiwan_display_date"]:
                    raise ValueError(
                        f"{group}[{index}].taiwan_display_date does not match the event-time conversion"
                    )
    ids = [event["event_id"] for event in events]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{group} contains duplicate event_id values")


def _sort_status_groups(events, sorter):
    result = []
    for status in WEEKLY_STATUS_ORDER:
        subset = [event for event in events if event["status_group"] == status]
        result.extend(sorter(subset))
    return result


def validate_calendar_dataset(dataset):
    """Validate and return a sorted shallow-copy dataset; never fill missing data."""
    if not isinstance(dataset, dict):
        raise ValueError("dataset must be an object")
    if dataset.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
    _iso_date(dataset.get("report_date"), "report_date")
    template = dataset.get("template")
    if not isinstance(template, str) or template not in TEMPLATES:
        raise ValueError("template must be monday or weekdays")

    economic = dataset.get("economic_events")
    earnings = dataset.get("earnings_events")
    prior_economic = dataset.get("prior_week_economic_events", [])
    prior_earnings = dataset.get("prior_week_earnings_events", [])

    _validate_group(economic, "economic_events", "economic", set(WEEKLY_STATUS_ORDER))
    _validate_group(earnings, "earnings_events", "earnings", set(WEEKLY_STATUS_ORDER))
    _validate_group(prior_economic, "prior_week_economic_events", "economic", {PRIOR_WEEK_STATUS})
    _validate_group(prior_earnings, "prior_week_earnings_events", "earnings", {PRIOR_WEEK_STATUS})

    if template == "weekdays" and (prior_economic or prior_earnings):
        raise ValueError("weekdays template cannot contain prior-week calendar events")

    result = dict(dataset)
    result["economic_events"] = _sort_status_groups(economic, sort_economic_events)
    result["earnings_events"] = _sort_status_groups(earnings, sort_earnings_events)
    result["prior_week_economic_events"] = sort_economic_events(prior_economic)
    result["prior_week_earnings_events"] = sort_earnings_events(prior_earnings)
    return result
