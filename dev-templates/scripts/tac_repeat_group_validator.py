#!/usr/bin/env python3
"""Validate dynamic repeat groups without relaxing their fixed DOM shell."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable

import cssselect2
import html5lib

STABLE_ATTRS = {
    "type", "name", "role", "for", "tabindex", "disabled", "multiple",
    "required", "open", "aria-controls", "aria-expanded", "aria-label",
    "aria-hidden", "aria-selected", "data-template-note",
}


@dataclass(frozen=True)
class GroupSpec:
    name: str
    wrapper_selector: str
    child_selector: str
    allow_count_change: bool = True


def _tag(element):
    tag = element.tag
    return tag.rsplit("}", 1)[-1].lower() if isinstance(tag, str) else "#text"


def _attrs(element):
    attrs = element.attrib
    return {
        "id": attrs.get("id", ""),
        "classes": sorted((attrs.get("class") or "").split()),
        "stable": sorted(
            (key, value) for key, value in attrs.items()
            if key in STABLE_ATTRS or key.startswith(("aria-", "data-", "on"))
        ),
    }


def _parse(source):
    return html5lib.parse(source, treebuilder="etree", namespaceHTMLElements=False)


def _query(root, selector):
    wrapped = cssselect2.ElementWrapper.from_html_root(root)
    return [item.etree_element for item in wrapped.query_all(selector)]


def _signature(element, excluded=frozenset()):
    children = []
    for child in list(element):
        if child in excluded:
            continue
        children.append(_signature(child, excluded))
    return {
        "tag": _tag(element),
        **_attrs(element),
        "children": children,
    }


def _direct_children(wrapper, selector):
    matches = _query(wrapper, selector)
    return [node for node in matches if node.getparent() is wrapper]


def _assets(root):
    result = []
    for node in root.iter():
        if _tag(node) in {"style", "script"}:
            payload = node.text or ""
            result.append((_tag(node), node.attrib.get("id", ""),
                           hashlib.sha256(payload.encode("utf-8")).hexdigest()))
    return result


def validate_repeat_groups(baseline_html: str, candidate_html: str,
                           specs: Iterable[GroupSpec]):
    """Compare fixed document structure while allowing registered child counts to vary.

    Each candidate card must match a complete card skeleton from the same
    corresponding baseline list. Wrapper count/order and all non-card DOM stay fixed.
    """
    base_root, candidate_root = _parse(baseline_html), _parse(candidate_html)
    specs = list(specs)
    base_dynamic, candidate_dynamic = set(), set()
    group_results = {}

    for spec in specs:
        base_wrappers = _query(base_root, spec.wrapper_selector)
        candidate_wrappers = _query(candidate_root, spec.wrapper_selector)
        wrapper_count_ok = len(base_wrappers) == len(candidate_wrappers)
        per_wrapper = []
        if wrapper_count_ok:
            for index, (base_wrapper, candidate_wrapper) in enumerate(
                zip(base_wrappers, candidate_wrappers)
            ):
                base_children = _direct_children(base_wrapper, spec.child_selector)
                candidate_children = _direct_children(candidate_wrapper, spec.child_selector)
                base_dynamic.update(base_children)
                candidate_dynamic.update(candidate_children)

                wrapper_ok = _signature(base_wrapper, set(base_children)) == _signature(
                    candidate_wrapper, set(candidate_children)
                )
                if base_children:
                    prototypes = {_freeze(_signature(child)) for child in base_children}
                    skeleton_ok = all(
                        _freeze(_signature(child)) in prototypes
                        for child in candidate_children
                    )
                else:
                    skeleton_ok = not candidate_children
                count_ok = spec.allow_count_change or len(base_children) == len(candidate_children)
                per_wrapper.append({
                    "index": index,
                    "baseline_child_count": len(base_children),
                    "candidate_child_count": len(candidate_children),
                    "wrapper_shell_equal": wrapper_ok,
                    "child_skeletons_valid": skeleton_ok,
                    "count_policy_pass": count_ok,
                    "pass": wrapper_ok and skeleton_ok and count_ok,
                })
        group_results[spec.name] = {
            "baseline_wrapper_count": len(base_wrappers),
            "candidate_wrapper_count": len(candidate_wrappers),
            "wrapper_count_equal": wrapper_count_ok,
            "wrappers": per_wrapper,
            "pass": wrapper_count_ok and all(item["pass"] for item in per_wrapper),
        }

    fixed_dom_equal = _signature(base_root, base_dynamic) == _signature(
        candidate_root, candidate_dynamic
    )
    assets_equal = _assets(base_root) == _assets(candidate_root)
    checks = {
        "fixed_dom_outside_repeat_children_equal": fixed_dom_equal,
        "inline_css_js_equal": assets_equal,
        "all_repeat_groups_valid": all(item["pass"] for item in group_results.values()),
    }
    return {"groups": group_results, "checks": checks, "pass": all(checks.values())}


def _freeze(value):
    if isinstance(value, dict):
        return tuple((key, _freeze(item)) for key, item in sorted(value.items()))
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value
