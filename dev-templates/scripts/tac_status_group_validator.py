#!/usr/bin/env python3
"""Validate calendar status-group transitions between event lists and approved empty states."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import cssselect2
import html5lib

from tac_repeat_group_validator import (
    _assets, _duplicate_id_counts, _freeze, _signature, _tag,
)


@dataclass(frozen=True)
class StatusGroupSpec:
    name: str
    section_selector: str
    group_selector: str = ".calendar-status-group"
    list_selector: str = ".econ-event-list"
    card_selector: str = ".econ-event"
    empty_selector: str = ".calendar-status-empty"
    allow_empty_state: bool = True


def _parse(source):
    parsed = html5lib.parse(source, treebuilder="etree", namespaceHTMLElements=False)
    normalized = html5lib.serialize(
        parsed, tree="etree", omit_optional_tags=False,
        quote_attr_values="always", alphabetical_attributes=True,
    )
    return html5lib.parse(normalized, treebuilder="etree", namespaceHTMLElements=False)


def _query(root, selector):
    wrapped = cssselect2.ElementWrapper.from_html_root(root)
    return list(wrapped.query_all(selector))


def _direct(root, parent, selector):
    return [
        item.etree_element for item in _query(parent, selector)
        if item.parent is not None and item.parent.etree_element is parent
    ]


def _card_prototypes(root, groups, spec):
    prototypes = set()
    for group in groups:
        for list_node in _direct(root, group, spec.list_selector):
            cards = _direct(root, list_node, spec.card_selector)
            prototypes.update(_freeze(_signature(card, ignore_href=True)) for card in cards)
    return prototypes


def validate_status_group_variants(baseline_html: str, candidate_html: str,
                                   specs: Iterable[StatusGroupSpec]):
    """Validate fixed status groups while allowing only approved list/empty variants.

    Empty-state markup must already exist in the same baseline section. A weekday
    template with only the CSS class but no actual empty-state node cannot silently
    acquire a new markup variant.
    """
    base_root, candidate_root = _parse(baseline_html), _parse(candidate_html)
    base_dynamic, candidate_dynamic = set(), set()
    results = {}

    for spec in specs:
        base_sections = [item.etree_element for item in _query(base_root, spec.section_selector)]
        candidate_sections = [item.etree_element for item in _query(candidate_root, spec.section_selector)]
        if len(base_sections) != len(candidate_sections):
            results[spec.name] = {
                "baseline_sections": len(base_sections),
                "candidate_sections": len(candidate_sections),
                "pass": False,
                "reason": "section_count_changed",
            }
            continue

        section_results = []
        for section_index, (base_section, candidate_section) in enumerate(zip(base_sections, candidate_sections)):
            base_groups = [item.etree_element for item in _query(base_section, spec.group_selector)]
            candidate_groups = [item.etree_element for item in _query(candidate_section, spec.group_selector)]
            if len(base_groups) != len(candidate_groups):
                section_results.append({
                    "section_index": section_index,
                    "baseline_group_count": len(base_groups),
                    "candidate_group_count": len(candidate_groups),
                    "pass": False,
                    "reason": "status_group_count_changed",
                })
                continue

            baseline_empty_prototypes = []
            baseline_list_prototypes = []
            baseline_card_prototypes = _card_prototypes(base_root, base_groups, spec)
            for group in base_groups:
                for empty in _direct(base_root, group, spec.empty_selector):
                    baseline_empty_prototypes.append(_freeze(_signature(empty)))
                for list_node in _direct(base_root, group, spec.list_selector):
                    cards = _direct(base_root, list_node, spec.card_selector)
                    baseline_list_prototypes.append(
                        _freeze(_signature(list_node, set(cards)))
                    )

            group_results = []
            for group_index, (base_group, candidate_group) in enumerate(zip(base_groups, candidate_groups)):
                base_lists = _direct(base_root, base_group, spec.list_selector)
                base_empties = _direct(base_root, base_group, spec.empty_selector)
                candidate_lists = _direct(candidate_root, candidate_group, spec.list_selector)
                candidate_empties = _direct(candidate_root, candidate_group, spec.empty_selector)

                base_variants = base_lists + base_empties
                candidate_variants = candidate_lists + candidate_empties
                variant_count_ok = len(base_variants) == 1 and len(candidate_variants) == 1
                if not variant_count_ok:
                    group_results.append({
                        "group_index": group_index,
                        "baseline_variant_count": len(base_variants),
                        "candidate_variant_count": len(candidate_variants),
                        "pass": False,
                        "reason": "expected_exactly_one_list_or_empty_variant",
                    })
                    continue

                base_dynamic.add(base_variants[0])
                candidate_dynamic.add(candidate_variants[0])
                shell_equal = _signature(base_group, set(base_variants)) == _signature(
                    candidate_group, set(candidate_variants)
                )

                if candidate_empties:
                    variant_kind = "empty"
                    variant_valid = (
                        spec.allow_empty_state
                        and bool(baseline_empty_prototypes)
                        and _freeze(_signature(candidate_empties[0])) in baseline_empty_prototypes
                    )
                    card_count = 0
                else:
                    variant_kind = "list"
                    candidate_cards = _direct(candidate_root, candidate_lists[0], spec.card_selector)
                    wrapper_valid = (
                        bool(baseline_list_prototypes)
                        and _freeze(_signature(candidate_lists[0], set(candidate_cards)))
                        in baseline_list_prototypes
                    )
                    cards_valid = bool(candidate_cards) and all(
                        _freeze(_signature(card, ignore_href=True)) in baseline_card_prototypes
                        for card in candidate_cards
                    )
                    variant_valid = wrapper_valid and cards_valid
                    card_count = len(candidate_cards)

                group_results.append({
                    "group_index": group_index,
                    "baseline_variant": "list" if base_lists else "empty",
                    "candidate_variant": variant_kind,
                    "candidate_card_count": card_count,
                    "status_group_shell_equal": shell_equal,
                    "variant_matches_same_template_prototype": variant_valid,
                    "pass": shell_equal and variant_valid,
                })

            section_results.append({
                "section_index": section_index,
                "baseline_group_count": len(base_groups),
                "candidate_group_count": len(candidate_groups),
                "groups": group_results,
                "pass": len(group_results) == len(base_groups) and all(item["pass"] for item in group_results),
            })

        results[spec.name] = {
            "baseline_sections": len(base_sections),
            "candidate_sections": len(candidate_sections),
            "sections": section_results,
            "pass": len(section_results) == len(base_sections) and all(item["pass"] for item in section_results),
        }

    fixed_dom_equal = _signature(base_root, base_dynamic) == _signature(candidate_root, candidate_dynamic)
    assets_equal = _assets(base_root) == _assets(candidate_root)
    duplicate_ids_equal = _duplicate_id_counts(base_root) == _duplicate_id_counts(candidate_root)
    checks = {
        "fixed_dom_outside_status_content_equal": fixed_dom_equal,
        "inline_css_js_equal": assets_equal,
        "duplicate_id_counts_equal": duplicate_ids_equal,
        "all_status_groups_valid": all(item["pass"] for item in results.values()),
    }
    return {"groups": results, "checks": checks, "pass": all(checks.values())}
