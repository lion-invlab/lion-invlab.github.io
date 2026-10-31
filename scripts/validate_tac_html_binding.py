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
                rows = [node for node in by_class(container, row_class) if record["key_text"] in normalize(node.text)]
                if len(rows) != 1:
                    errors.append(f"{group}.{key}: expected one row containing '{record['key_text']}', found {len(rows)}")
                    continue
                if not by_class(rows[0], record["value_selector"].lstrip(".")):
                    errors.append(f"{group}.{key}: value selector {record['value_selector']} missing")

        if "outcomes" in spec:
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

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    contract = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    templates = contract["templates"]
    failures = []
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
