"""Dry-run planner for status-group repeat-card updates.

This module never mutates template DOM. It blocks card creation when the exact
status group lacks a same-template, same-group card prototype and blocks empty
transitions when the same section has no native empty-state prototype.
"""
from __future__ import annotations

from tac_calendar_dataset import validate_calendar_dataset

SECTION_CONFIG = {
    "weekly_economic": ("economic_events",),
    "weekly_earnings": ("earnings_events",),
    "prior_week_economic": ("prior_week_economic_events",),
    "prior_week_earnings": ("prior_week_earnings_events",),
}


def plan_calendar_repeat_updates(dataset, template_inventory):
    validated = validate_calendar_dataset(dataset)
    template = validated["template"]
    if not isinstance(template_inventory, dict) or template_inventory.get("template") != template:
        raise ValueError("template inventory must match dataset template")

    section_reports = {}
    all_pass = True
    for section_name, (data_key,) in SECTION_CONFIG.items():
        records = validated[data_key]
        section = template_inventory.get("sections", {}).get(section_name)
        if not section or not section.get("present"):
            if records:
                section_reports[section_name] = {
                    "pass": False, "action": "blocked",
                    "reason": "target_section_missing_for_template",
                    "event_count": len(records),
                }
                all_pass = False
            else:
                section_reports[section_name] = {
                    "pass": True, "action": "not_applicable", "event_count": 0,
                }
            continue

        groups = section.get("groups", [])
        by_status = {}
        duplicate_statuses = set()
        for group in groups:
            status = group.get("status_key")
            if status in by_status:
                duplicate_statuses.add(status)
            by_status[status] = group
        section_empty_prototype = any(
            group.get("empty_state_count", 0) > 0 for group in groups
        )
        statuses = (
            ("prior_week_published",)
            if data_key.startswith("prior_week_")
            else ("today", "upcoming", "published")
        )
        group_reports = []
        section_pass = not duplicate_statuses

        for status in statuses:
            group = by_status.get(status)
            count = sum(1 for event in records if event["status_group"] == status)
            if group is None:
                ok = count == 0
                group_reports.append({
                    "status_group": status, "event_count": count,
                    "action": "not_applicable" if ok else "blocked",
                    "pass": ok,
                    "reason": None if ok else "status_group_missing_from_template",
                })
                section_pass = section_pass and ok
                continue

            has_prototype = bool(group.get("has_same_group_card_prototype"))
            baseline_empty = group.get("empty_state_count", 0) == 1
            baseline_list = group.get("list_count", 0) == 1
            if count > 0:
                ok = has_prototype
                action = "render_list" if ok else "blocked"
                reason = None if ok else "same_group_card_prototype_missing"
            elif baseline_empty:
                ok, action, reason = True, "keep_empty_state", None
            elif baseline_list and section_empty_prototype:
                ok, action, reason = True, "switch_to_existing_empty_state", None
            else:
                ok, action = False, "blocked"
                reason = "same_section_empty_state_prototype_missing"

            group_reports.append({
                "status_group": status,
                "event_count": count,
                "baseline_card_count": group.get("card_count", 0),
                "has_same_group_card_prototype": has_prototype,
                "action": action,
                "pass": ok,
                "reason": reason,
            })
            section_pass = section_pass and ok

        if duplicate_statuses:
            section_pass = False
        section_reports[section_name] = {
            "pass": section_pass,
            "event_count": len(records),
            "duplicate_template_status_keys": sorted(
                str(value) for value in duplicate_statuses
            ),
            "groups": group_reports,
        }
        all_pass = all_pass and section_pass

    return {
        "template": template,
        "pass": all_pass,
        "sections": section_reports,
        "mutation_performed": False,
    }
