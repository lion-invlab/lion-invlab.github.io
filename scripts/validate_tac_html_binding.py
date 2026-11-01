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
    if selector.startswith("#"):
        return by_id(root, selector[1:])
    if selector.startswith("."):
        return by_class(root, selector[1:])
    return [node for node in root.descendants() if node.tag == selector]


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

        if "records" in spec:
            for key, record in spec["records"].items():
                row_class = record["row"].lstrip(".")
                rows = [node for node in by_class(container, row_class) if any(normalize(label.text) == record["key_text"] for label in by_class(node, "label-en"))]
                if len(rows) != 1:
                    errors.append(f"{group}.{key}: expected one row containing '{record['key_text']}', found {len(rows)}")
                    continue
                if not selector_nodes(rows[0], record["value_selector"]):
                    errors.append(f"{group}.{key}: value selector {record['value_selector']} missing")

        if "outcomes" in spec:
            if "row" in spec:
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
            else:
                for key, outcome in spec["outcomes"].items():
                    rows = selector_nodes(container, outcome["row"])
                    if len(rows) != 1:
                        errors.append(f"{group}.{key}: expected one outcome row, found {len(rows)}")
                        continue
                    row = rows[0]
                    if not selector_nodes(row, outcome["probability_selector"]):
                        errors.append(f"{group}.{key}: probability selector missing")
                    if not selector_nodes(row, outcome["rate_range_selector"]):
                        errors.append(f"{group}.{key}: rate range selector missing")
                    if not selector_nodes(container, outcome["bar_selector"]):
                        errors.append(f"{group}.{key}: distribution bar selector missing")
                for selector_key in ("split_bar_selector", "legend_selector", "audit_container_selector"):
                    if not selector_nodes(container, spec[selector_key]):
                        errors.append(f"{group}: {selector_key} missing")
                for key in ("meeting_row", "rate_row"):
                    if not selector_nodes(container, spec["fomc"][key]):
                        errors.append(f"{group}: FOMC {key} missing")


        if group == "editorial":
            summary = spec["summary"]
            summary_containers = selector_nodes(root, summary["container"])
            if len(summary_containers) != 1:
                errors.append("editorial: summary container missing or duplicated")
            else:
                summary_nodes = selector_nodes(summary_containers[0], summary["headline_selector"])
                body_nodes = selector_nodes(summary_containers[0], summary["body_selector"])
                if len(summary_nodes) != 1:
                    errors.append("editorial: summary headline slot missing or duplicated")
                if len(body_nodes) != 1:
                    errors.append("editorial: summary body slot missing or duplicated")
                elif sum(1 for child in body_nodes[0].children if isinstance(child, str) and child.strip()) < 1:
                    errors.append("editorial: summary body has no direct text segments")
            observation = spec["observation"]
            for field, panel_key, content_key, min_segments in (
                ("market", "market_panel", "market_text_selector", 1),
                ("levels", "levels_panel", "levels_text_selector", 2),
                ("core", "core_panel", "core_text_selector", 1),
            ):
                panels = selector_nodes(root, observation[panel_key])
                if len(panels) != 1:
                    errors.append(f"editorial.{field}: observation panel missing or duplicated")
                    continue
                content = selector_nodes(panels[0], observation[content_key])
                if len(content) != 1:
                    errors.append(f"editorial.{field}: text container missing or duplicated")
                    continue
                direct_texts = [child for child in content[0].children if isinstance(child, str) and child.strip()]
                if len(direct_texts) < min_segments:
                    errors.append(f"editorial.{field}: expected at least {min_segments} direct text segments, found {len(direct_texts)}")


        if group == "news":
            for panel_key, panel_spec in spec["panels"].items():
                panel_nodes = selector_nodes(root, panel_spec["container"])
                if len(panel_nodes) != 1:
                    errors.append(f"news.{panel_key}: panel container missing or duplicated")
                    continue
                panel = panel_nodes[0]
                for selector_key in ("meta_selector", "item_selector"):
                    if not selector_nodes(panel, panel_spec[selector_key]):
                        errors.append(f"news.{panel_key}: {selector_key} missing")
                items = selector_nodes(panel, panel_spec["item_selector"])
                if not items:
                    errors.append(f"news.{panel_key}: no news cards")
                for index, item in enumerate(items):
                    for selector_key in ("title_selector", "summary_selector", "sources_container_selector"):
                        if len(selector_nodes(item, panel_spec[selector_key])) != 1:
                            errors.append(f"news.{panel_key}[{index}]: {selector_key} missing or duplicated")
                    source_containers = selector_nodes(item, panel_spec["sources_container_selector"])
                    if source_containers and not selector_nodes(source_containers[0], panel_spec["source_selector"]):
                        errors.append(f"news.{panel_key}[{index}]: no source links")

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
    expected_fedwatch = {"probabilities": "probabilities", "meeting": "target_meeting", "updated_at": "updated_at", "target_rate_range": "target_rate_range", "audit_text": "audit_text", "aria_label": "aria_label"}
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
