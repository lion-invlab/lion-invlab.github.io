"""Map validated TAC calendar records into explicit repeat-card payloads.

This module prepares data only. It does not clone HTML, mutate DOM nodes, or
write production files. Status placement is explicit input, never inferred.
"""
from __future__ import annotations

from collections import defaultdict

from tac_calendar_dataset import validate_calendar_dataset
from tac_field_write_guard import load_registry

STATUS_GROUPS = {"today", "upcoming", "published"}
ECONOMIC_SUMMARY_KEYS = {"date", "time", "country", "name", "stars"}
EARNINGS_SUMMARY_KEYS = {"us_date", "tw_date", "company", "subtitle", "stars"}


def _validate_summary(summary, required, prefix):
    if not isinstance(summary, dict) or set(summary) != required:
        raise ValueError(
            f"{prefix}.summary must contain exactly: {', '.join(sorted(required))}"
        )
    for key, value in summary.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{prefix}.summary.{key} must be a non-empty string")


def _selector_item(registry, name):
    matches = [item for item in registry["selectors"] if item.get("name") == name]
    if len(matches) != 1:
        raise PermissionError(f"registry must contain exactly one {name!r} entry")
    return matches[0]


def _map_group(events, kind, registry):
    summary_keys = ECONOMIC_SUMMARY_KEYS if kind == "economic" else EARNINGS_SUMMARY_KEYS
    selector_name = (
        "weekly_economic_events" if kind == "economic" else "weekly_earnings_cards"
    )
    registration = _selector_item(registry, selector_name)
    allowed_details = set(registration.get("writable_detail_labels", []))
    allowed_sources = set(registration.get("writable_source_labels", []))
    grouped = defaultdict(list)

    for index, event in enumerate(events):
        prefix = f"{kind}_events[{index}]"
        status = event.get("status_group")
        if status not in STATUS_GROUPS:
            raise ValueError(f"{prefix}.status_group must be today, upcoming, or published")
        _validate_summary(event.get("summary"), summary_keys, prefix)

        details = event.get("details", {})
        if not isinstance(details, dict):
            raise ValueError(f"{prefix}.details must be a label/value object")
        unknown_details = set(details) - allowed_details
        if unknown_details:
            raise PermissionError(
                f"{prefix} has labels not allowlisted by the registry: {sorted(unknown_details)}"
            )
        for label, value in details.items():
            if not isinstance(value, str):
                raise ValueError(f"{prefix}.details[{label!r}] must be a string")

        source_records = event["source_records"]
        unknown_source_labels = {source["label"] for source in source_records} - allowed_sources
        if unknown_source_labels:
            raise PermissionError(
                f"{prefix} has source labels not allowlisted by the registry: "
                f"{sorted(unknown_source_labels)}"
            )

        grouped[status].append({
            "event_id": event["event_id"],
            "summary": dict(event["summary"]),
            "details": dict(details),
            "sources": [
                {"label": source["label"], "href": source["url"]}
                for source in source_records
            ],
            "event_date": event["event_date"],
            "event_time": event.get("event_time"),
            "importance": event["importance"],
        })
    return dict(grouped)


def build_calendar_card_plan(dataset, registry=None):
    """Validate, sort and map both calendar families into status-group payloads."""
    normalized = validate_calendar_dataset(dataset)
    registry = registry or load_registry()
    return {
        "schema_version": "tac-calendar-card-plan-v1",
        "report_date": normalized["report_date"],
        "template": normalized["template"],
        "economic": _map_group(normalized["economic_events"], "economic", registry),
        "earnings": _map_group(normalized["earnings_events"], "earnings", registry),
        "write_authorized": False,
    }
