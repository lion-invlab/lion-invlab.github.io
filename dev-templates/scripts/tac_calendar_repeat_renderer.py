"""Materialize weekly economic/earnings repeat cards from same-group prototypes.

This is a test-branch renderer. It never edits official mother files. It builds
all clones off-document, validates every field and source anchor, then swaps
only registered card children and verifies the resulting repeat-group DOM.
Prior-week earnings are intentionally excluded until their result-grid schema
has a dedicated mapping.
"""
from __future__ import annotations

from copy import deepcopy
from urllib.parse import urlsplit

import cssselect2
import html5lib

from tac_calendar_dataset import validate_calendar_dataset
from tac_field_write_guard import load_registry
from tac_calendar_field_mapper import map_calendar_dataset
from tac_calendar_group_inventory import inventory_calendar_groups
from tac_repeat_group_validator import GroupSpec, validate_repeat_groups

SECTION_CONFIG = {
    "weekly_economic": {
        "section": "#calendar",
        "list": ".econ-event-list",
        "card": ".econ-event",
        "field_class": "econ-field",
        "value_class": "econ-value",
        "registry_name": "weekly_economic_events",
        "fixed_detail_labels": {"前值", "市場預估", "實際"},
        "summary": {
            "date": "econ-date", "time": "econ-time", "country": "econ-country",
            "name": "econ-name", "stars": "econ-stars",
        },
    },
    "weekly_earnings": {
        "section": "#earnings",
        "list": ".earnings-accordion-list",
        "card": ".earnings-accordion",
        "field_class": "earnings-detail-field",
        "value_class": "earnings-detail-value",
        "registry_name": "weekly_earnings_cards",
        "fixed_detail_labels": set(),
        "summary": {
            "us_date": "earnings-us-date", "taiwan_date": "earnings-tw-date",
            "company_name": "earnings-company-name", "subtitle": "earnings-company-sub",
            "stars": "earnings-stars",
        },
    },
}
STATUSES = ("today", "upcoming", "published")


def _parse(source):
    return html5lib.parse(source, treebuilder="etree", namespaceHTMLElements=False)


def _serialize(root):
    return html5lib.serialize(
        root, tree="etree", omit_optional_tags=False,
        quote_attr_values="always", alphabetical_attributes=False,
    )


def _query(root, selector):
    wrapped = cssselect2.ElementWrapper.from_html_root(root)
    return [item.etree_element for item in wrapped.query_all(selector)]


def _direct(root, parent, selector):
    wrapped = cssselect2.ElementWrapper.from_html_root(root)
    return [
        item.etree_element for item in wrapped.query_all(selector)
        if item.parent is not None and item.parent.etree_element is parent
    ]


def _classes(node):
    return set(node.attrib.get("class", "").split())


def _status_key(group):
    headings = _direct(group.getroottree().getroot(), group, ".calendar-status-heading")
    if len(headings) != 1:
        raise ValueError("each calendar status group must have exactly one heading")
    heading = " ".join("".join(headings[0].itertext()).split())
    if heading.startswith(("今日公布", "今日及今晚")):
        return "today"
    if heading.startswith("即將公布"):
        return "upcoming"
    if heading.startswith("已公布"):
        return "published"
    return None


def _field_map(card, field_class, value_class):
    fields = {}
    for field in card.iter():
        if field_class not in _classes(field):
            continue
        labels = [child for child in list(field) if child.tag.lower() == "label"]
        values = [child for child in list(field) if value_class in _classes(child)]
        if len(labels) != 1 or len(values) != 1:
            raise PermissionError("calendar detail field must have one direct label and one direct value")
        label = (labels[0].text or "").strip()
        if not label or label in fields:
            raise PermissionError("calendar detail labels must be non-empty and unique per card")
        fields[label] = values[0]
    return fields


def _safe_source(href, label):
    if not isinstance(href, str) or not isinstance(label, str) or not label.strip():
        raise ValueError("each source link requires an absolute URL and non-empty label")
    parsed = urlsplit(href)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("source links must use absolute HTTP(S) URLs")
    if parsed.username or parsed.password or any(ord(ch) < 32 for ch in href):
        raise ValueError("unsafe source URL")


def _summary_nodes(card, summary_classes):
    nodes = {}
    for key, class_name in summary_classes.items():
        matches = [node for node in card.iter() if class_name in _classes(node)]
        if len(matches) != 1 or len(list(matches[0])):
            raise PermissionError(f"summary field {class_name} must be one unique text leaf")
        nodes[key] = matches[0]
    return nodes


def _prototype_matches(card, config, payload):
    fields = _field_map(card, config["field_class"], config["value_class"])
    source_labels = set(payload["sources"])
    detail_labels = set(payload["details"])
    if set(fields) != source_labels | detail_labels:
        return False
    for label, links in payload["sources"].items():
        value = fields[label]
        anchors = list(value)
        if not anchors or len(anchors) != len(links):
            return False
        if any(anchor.tag.lower() != "a" or len(list(anchor)) for anchor in anchors):
            return False
    try:
        _summary_nodes(card, config["summary"])
    except PermissionError:
        return False
    return True


def _apply_payload(card, config, payload):
    fields = _field_map(card, config["field_class"], config["value_class"])
    if set(fields) != set(payload["details"]) | set(payload["sources"]):
        raise PermissionError("card detail labels do not exactly match the supplied payload")

    summary_nodes = _summary_nodes(card, config["summary"])
    for key, value in payload["summary"].items():
        if key not in summary_nodes or not isinstance(value, str):
            raise PermissionError(f"unregistered summary payload field: {key}")
    if set(summary_nodes) != set(payload["summary"]):
        raise PermissionError("summary payload must populate every registered summary leaf")

    prepared_text = []
    for label, value in payload["details"].items():
        if label not in fields or not isinstance(value, str):
            raise PermissionError(f"unregistered or non-text detail field: {label}")
        target = fields[label]
        if len(list(target)):
            raise PermissionError(f"detail value {label} is not a text leaf")
        prepared_text.append((target, value))

    prepared_sources = []
    for label, links in payload["sources"].items():
        if label not in fields or not isinstance(links, list) or not links:
            raise PermissionError(f"invalid source field payload: {label}")
        target = fields[label]
        anchors = list(target)
        if len(anchors) != len(links):
            raise ValueError(f"source anchor count mismatch for {label}: {len(anchors)} != {len(links)}")
        if any(anchor.tag.lower() != "a" or len(list(anchor)) for anchor in anchors):
            raise PermissionError(f"source field {label} contains a non-leaf anchor")
        for anchor, link in zip(anchors, links):
            href, link_label = link.get("href"), link.get("label")
            _safe_source(href, link_label)
            prepared_sources.append((anchor, href, link_label))

    # All validation is complete before the cloned card is modified.
    for key, value in payload["summary"].items():
        summary_nodes[key].text = value
    for target, value in prepared_text:
        target.text = value
    for anchor, href, label in prepared_sources:
        anchor.attrib["href"] = href
        anchor.text = label


def _group_targets(root, section_selector, list_selector, card_selector):
    sections = _query(root, section_selector)
    if len(sections) != 1:
        raise ValueError(f"calendar section must match exactly once: {section_selector}")
    groups = _query(sections[0], ".calendar-status-group")
    result = {}
    for group in groups:
        headings = _direct(root, group, ".calendar-status-heading")
        if len(headings) != 1:
            raise ValueError("calendar status group heading cardinality mismatch")
        heading = " ".join("".join(headings[0].itertext()).split())
        if heading.startswith(("今日公布", "今日及今晚")):
            status = "today"
        elif heading.startswith("即將公布"):
            status = "upcoming"
        elif heading.startswith("已公布"):
            status = "published"
        else:
            continue
        if status in result:
            raise ValueError(f"duplicate {status} group in {section_selector}")
        lists = _direct(root, group, list_selector)
        empties = _direct(root, group, ".calendar-status-empty")
        if len(lists) > 1 or len(empties) > 1 or (lists and empties):
            raise ValueError(f"invalid list/empty-state structure for {status}")
        cards = _direct(root, lists[0], card_selector) if lists else []
        result[status] = {
            "group": group, "list": lists[0] if lists else None,
            "empty": empties[0] if empties else None, "cards": cards,
        }
    return result


def render_weekly_calendar_updates(source_html, dataset, template_inventory):
    """Return a rendered HTML string after preflight, clone/write and DOM validation.

    Supports weekly economic and earnings status groups. Monday prior-week
    groups are kept untouched; supplying prior-week records is rejected until
    their specialized result-card mapping is implemented.
    """
    validated = validate_calendar_dataset(dataset)
    template = validated["template"]
    if not isinstance(template_inventory, dict) or template_inventory.get("template") != template:
        raise ValueError("template inventory must match dataset template")
    actual_inventory = inventory_calendar_groups(source_html, template)
    if not actual_inventory["pass"]:
        raise PermissionError("source HTML does not contain a valid calendar repeat-group inventory")
    if template_inventory != actual_inventory:
        raise ValueError("template inventory does not match the supplied source HTML")
    if validated["prior_week_economic_events"] or validated["prior_week_earnings_events"]:
        raise PermissionError("prior-week cards require their dedicated result-card mapping; no partial render allowed")

    mapped = map_calendar_dataset(validated)
    registry = load_registry()
    root = _parse(source_html)
    pending_replacements = []
    report = {"template": template, "sections": {}, "mutation_performed": False}

    for section_name, config in SECTION_CONFIG.items():
        registrations = [
            item for item in registry["selectors"]
            if item.get("name") == config["registry_name"]
            and item.get("selector") == config["section"] + " " + config["card"]
            and item.get("kind") == "repeat"
        ]
        if len(registrations) != 1:
            raise PermissionError(f"{section_name}: exactly one matching repeat selector registration is required")
        registration = registrations[0]
        if registration.get("detail_field_class") != config["field_class"] or registration.get("detail_value_class") != config["value_class"]:
            raise PermissionError(f"{section_name}: registered detail field classes do not match renderer")
        allowed_details = set(registration.get("writable_detail_labels", [])) | set(config["fixed_detail_labels"])
        allowed_sources = set(registration.get("writable_source_labels", []))
        targets = _group_targets(root, config["section"], config["list"], config["card"])
        payload_section = mapped[section_name]
        section_report = {}
        for status in STATUSES:
            target = targets.get(status)
            payloads = payload_section[status]
            count = len(payloads)
            if target is None:
                if count:
                    raise PermissionError(f"{section_name} has no {status} group in this template")
                section_report[status] = {"count": 0, "action": "not_applicable"}
                continue
            if count == 0:
                if target["empty"] is not None and target["list"] is None:
                    section_report[status] = {"count": 0, "action": "keep_empty_state"}
                    continue
                raise PermissionError(
                    f"{section_name}/{status}: empty-state transition is not approved for this template"
                )
            if target["list"] is None or target["empty"] is not None or not target["cards"]:
                raise PermissionError(f"{section_name}/{status}: same-group card prototype is unavailable")

            original_cards = target["cards"]
            direct_children = list(target["list"])
            if len(direct_children) != len(original_cards) or any(
                child not in original_cards for child in direct_children
            ):
                raise PermissionError(f"{section_name}/{status}: list contains unregistered non-card children")

            clones = []
            for payload in payloads:
                unknown_details = set(payload["details"]) - allowed_details
                unknown_sources = set(payload["sources"]) - allowed_sources
                if unknown_details or unknown_sources:
                    raise PermissionError(
                        f"{section_name}/{status}: non-allowlisted labels "
                        f"details={sorted(unknown_details)} sources={sorted(unknown_sources)}"
                    )
                prototypes = [
                    card for card in original_cards
                    if _prototype_matches(card, config, payload)
                ]
                if not prototypes:
                    raise PermissionError(
                        f"{section_name}/{status}: no same-group prototype matches detail labels/source anchors"
                    )
                clone = deepcopy(prototypes[0])
                _apply_payload(clone, config, payload)
                clones.append(clone)
            pending_replacements.append((target["list"], original_cards, clones))
            section_report[status] = {
                "count": count, "action": "replace_cards",
                "baseline_count": len(original_cards),
            }
        report["sections"][section_name] = section_report

    # Commit to the private parsed document only after every group is prepared.
    for list_node, old_cards, new_cards in pending_replacements:
        for card in old_cards:
            list_node.remove(card)
        for card in new_cards:
            list_node.append(card)

    rendered = _serialize(root)
    specs = [
        GroupSpec("weekly_economic", "#calendar .econ-event-list", ".econ-event"),
        GroupSpec("weekly_earnings", "#earnings .earnings-accordion-list", ".earnings-accordion"),
    ]
    structural = validate_repeat_groups(source_html, rendered, specs)
    if not structural["pass"]:
        raise ValueError(f"rendered calendar repeat-group DOM validation failed: {structural}")
    report["structural_validation"] = structural
    report["mutation_performed"] = True
    return {"html": rendered, "report": report}
