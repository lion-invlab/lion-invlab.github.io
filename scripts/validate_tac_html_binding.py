#!/usr/bin/env python3
"""Validate snapshot-to-DOM binding slots in both protected TAC mother templates.

This is a read-only structural check. It does not modify HTML, CSS, scripts or data.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = ROOT / "scripts" / "tac_html_binding_map.json"


class Node:
    def __init__(self, tag: str, attrs: dict[str, str | None]):
        self.tag = tag
        self.attrs = attrs
        self.children: list[Node | str] = []

    @property
    def classes(self) -> set[str]:
        return set((self.attrs.get("class") or "").split())

    @property
    def text(self) -> str:
        return "".join(child.text if isinstance(child, Node) else child for child in self.children)

    def descendants(self):
        for child in self.children:
            if isinstance(child, Node):
                yield child
                yield from child.descendants()


class TreeParser(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("document", {})
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, dict(attrs)))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def by_id(root: Node, element_id: str) -> list[Node]:
    return [node for node in root.descendants() if node.attrs.get("id") == element_id]


def by_class(root: Node, class_name: str) -> list[Node]:
    return [node for node in root.descendants() if class_name in node.classes]


def selector_nodes(root: Node, selector: str) -> list[Node]:
    parts = selector.split()
    if len(parts) == 1:
        if parts[0].startswith("."):
            return by_class(root, parts[0][1:])
        return [node for node in root.descendants() if node.tag == parts[0]]
    if len(parts) == 2 and parts[0].startswith("."):
        result = []
        for parent in by_class(root, parts[0][1:]):
            target = parts[1]
            result.extend(node for node in parent.descendants()
                          if (node.tag == target if not target.startswith(".") else target[1:] in node.classes))
        return result
    return []


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def check_template(path: Path, contract: dict) -> list[str]:
    parser = TreeParser()
    parser.feed(path.read_text(encoding="utf-8"))
    root = parser.root
    errors: list[str] = []

    for group, spec in contract["groups"].items():
        container_id = spec["container"].lstrip("#")
        containers = by_id(root, container_id)
        if len(containers) != 1:
            errors.append(f"{group}: expected one #{container_id}, found {len(containers)}")
            continue
        container = containers[0]

        if "key_by_label" in spec or "key_by_ticker" in spec:
            row_class = spec["row"].lstrip(".")
            rows = by_class(container, row_class)
            expected = len(spec.get("key_by_label", spec.get("key_by_ticker", {})))
            if len(rows) != expected:
                errors.append(f"{group}: expected {expected} .{row_class} rows, found {len(rows)}")
            for key, label in spec.get("key_by_label", {}).items():
                matches = [row for row in rows if label in normalize(row.text)]
                if len(matches) != 1:
                    errors.append(f"{group}.{key}: label '{label}' expected once, found {len(matches)}")
                    continue
                value_nodes = [node for node in matches[0].descendants() if "r" in node.classes]
                if len(value_nodes) < 2:
                    errors.append(f"{group}.{key}: expected value and change slots, found {len(value_nodes)}")
            for key, ticker in spec.get("key_by_ticker", {}).items():
                matches = [row for row in rows if re.search(r"(?<![A-Z0-9])" + re.escape(ticker) + r"(?![A-Z0-9])", normalize(row.text))]
                if len(matches) != 1:
                    errors.append(f"{group}.{key}: ticker '{ticker}' expected once, found {len(matches)}")
                    continue
                value_nodes = [node for node in matches[0].descendants() if "r" in node.classes]
                if len(value_nodes) != 1:
                    errors.append(f"{group}.{key}: expected one percentage slot, found {len(value_nodes)}")
                rank_selector = spec.get("rank_selector")
                if rank_selector and not selector_nodes(matches[0], rank_selector):
                    errors.append(f"{group}.{key}: rank slot {rank_selector} missing")

        if "records" in spec:
            for key, record in spec["records"].items():
                row_class = record["row"].lstrip(".")
                rows = [node for node in by_class(container, row_class) if any(normalize(label.text) == record["key_text"] for label in by_class(node, "label-en"))]
                if len(rows) != 1:
                    errors.append(f"{group}.{key}: expected one row containing '{record['key_text']}', found {len(rows)}")
                    continue
                if not selector_nodes(rows[0], record["value_selector"]):
                    errors.append(f"{group}.{key}: value selector {record['value_selector']} missing")
                for selector_key in ("source_selector", "category_selector", "category_zh_selector", "marker_selector"):
                    selector = record.get(selector_key)
                    if selector and not selector_nodes(rows[0], selector):
                        errors.append(f"{group}.{key}: {selector_key} {selector} missing")

        if "outcomes" in spec:
            meeting_selector = spec.get("fomc_meeting_selector")
            if meeting_selector and len(selector_nodes(container, meeting_selector)) != 1:
                errors.append(f"{group}: FOMC meeting date slot {meeting_selector} missing or duplicated")
            row_class = spec["row"].lstrip(".")
            rows = by_class(container, row_class)
            if len(rows) != len(spec["outcomes"]):
                errors.append(f"{group}: expected {len(spec['outcomes'])} probability rows, found {len(rows)}")
            for key, outcome in spec["outcomes"].items():
                matches = [row for row in rows if outcome["label"] in normalize(row.text)]
                if len(matches) != 1:
                    errors.append(f"{group}.{key}: expected one '{outcome['label']}' row, found {len(matches)}")
                    continue
                if not by_class(matches[0], "fc-range"):
                    errors.append(f"{group}.{key}: .fc-range slot missing")
                if not any(node.tag == "strong" for node in matches[0].descendants()):
                    errors.append(f"{group}.{key}: probability <strong> slot missing")
            for selector_key in ("split_bar_selector", "split_hold_selector", "split_hike_selector",
                                 "split_legend_value_selector", "split_timestamp_selector"):
                selector = spec.get(selector_key)
                if selector:
                    found = selector_nodes(container, selector)
                    expected_count = 2 if selector_key == "split_legend_value_selector" else (1, 2) if selector_key == "split_timestamp_selector" else 1
                    valid_count = len(found) in expected_count if isinstance(expected_count, tuple) else len(found) == expected_count
                    if not valid_count:
                        errors.append(f"{group}: {selector_key} expected {expected_count} slot(s), found {len(found)}")
            if not selector_nodes(container, spec.get("audit_content_selector", "")):
                audit_details = [node for node in container.descendants() if node.tag == "details"
                                 and any(child.tag == "summary" and "資料時間與快照口徑" in normalize(child.text)
                                         for child in node.children if isinstance(child, Node))]
                if len(audit_details) != 1 or len([child for child in audit_details[0].children
                                                   if isinstance(child, Node) and child.tag == "div"]) != 1:
                    errors.append(f"{group}: FedWatch audit content slot missing or duplicated")
            bar_selector = spec.get("split_bar_selector")
            if bar_selector:
                bars = selector_nodes(container, bar_selector)
                if len(bars) == 1 and not bars[0].attrs.get(spec.get("aria_label_attribute", "aria-label")):
                    errors.append(f"{group}: split bar accessible aria-label missing")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    contract = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    templates = contract["templates"]
    failures = []

    # Explicit semantic mapping prevents a renderer from confusing a sector's
    # displayed daily return with the ETF's underlying close value.
    expected_fields = {
        "global_indices": {"display_value": "value", "display_change": "change"},
        "bonds": {"display_value": "value", "display_change": "change"},
        "fx": {"display_value": "value", "display_change": "change"},
        "energy": {"display_value": "value", "display_change": "change"},
        "precious_metals": {"display_value": "value", "display_change": "change"},
        "sectors": {"display_value": "change", "display_change": None, "display_unit": "change_unit"},
    }
    for group, expected in expected_fields.items():
        actual = contract["groups"].get(group, {}).get("snapshot_fields")
        if actual != expected:
            failures.append(f"{group}: snapshot_fields must be {expected}, got {actual}")
    expected_risk = {
        "vix": {"display_value": "value", "display_change": "change"},
        "move": {"display_value": "value", "display_change": "change"},
        "cnn_fear_greed": {"display_value": "value", "display_change": None},
    }
    actual_risk = contract["groups"].get("risk_indicators", {}).get("snapshot_fields")
    if actual_risk != expected_risk:
        failures.append(f"risk_indicators: snapshot_fields must be {expected_risk}, got {actual_risk}")
    expected_fedwatch = {"probability_array": "probabilities", "meeting": "target_meeting", "updated_at": "updated_at"}
    actual_fedwatch = contract["groups"].get("fedwatch", {}).get("snapshot_fields")
    if actual_fedwatch != expected_fedwatch:
        failures.append(f"fedwatch: snapshot_fields must be {expected_fedwatch}, got {actual_fedwatch}")
    for label, relative in templates.items():
        path = ROOT / relative
        if not path.exists():
            failures.append(f"{label}: template not found: {relative}")
            continue
        errors = check_template(path, contract)
        if errors:
            failures.extend(f"{label}: {error}" for error in errors)
        else:
            print(f"PASS: {label} mother contains all mapped binding slots")
    if failures:
        for failure in failures:
            print("FAIL: " + failure, file=sys.stderr)
        return 1
    print("PASS: dual-mother HTML binding contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
