"""Prepare calendar update payloads only after template repeat-plan approval.

The preparation stage validates, sorts, plans and maps data. It never edits HTML.
If any status group is blocked, it withholds all card payloads.
"""
from __future__ import annotations

from tac_calendar_field_mapper import map_calendar_dataset
from tac_calendar_repeat_plan import plan_calendar_repeat_updates


def prepare_calendar_update(dataset, template_inventory):
    plan = plan_calendar_repeat_updates(dataset, template_inventory)
    if not plan["pass"]:
        return {
            "ready": False,
            "stage": "blocked_before_dom_write",
            "plan": plan,
            "payloads": None,
            "mutation_performed": False,
        }

    payloads = map_calendar_dataset(dataset)
    return {
        "ready": True,
        "stage": "validated_payload_ready",
        "plan": plan,
        "payloads": payloads,
        "mutation_performed": False,
    }
