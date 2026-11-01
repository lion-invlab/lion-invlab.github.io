#!/usr/bin/env python3
"""Contract-driven, fail-closed text renderer for approved TAC market slots.

Only existing text nodes inside selectors defined by tac_html_binding_map.json
are editable. The renderer never creates, removes, moves, or reserializes HTML
elements or attributes. Direction-class mismatches are rejected rather than
silently leaving a stale red/green presentation.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}


@dataclass
class Node:
    tag: str
    attrs: dict[str, str | None]
    parent: "Node | None" = None
    children: list["Node | TextSpan"] = field(default_factory=list)

    @property
    def classes(self) -> set[str]:
        return set((self.attrs.get("class") or "").split())


@dataclass(frozen=True)
class TextSpan:
    start: int
    end: int
    text: str
    parent: Node


class SourceTreeParser(HTMLParser):
    def __init__(self, source: str):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.offsets = [0]
        for line in source.splitlines(keepends=True):
            self.offsets.append(self.offsets[-1] + len(line))
        self.root = Node("#document", {})
        self.stack = [self.root]
        self.spans: list[TextSpan] = []

    def source_offset(self) -> int:
        line, col = self.getpos()
        return self.offsets[line - 1] + col

    def handle_starttag(self, tag, attrs):
        node = Node(tag.lower(), dict(attrs), self.stack[-1])
        self.stack[-1].children.append(node)
        if tag.lower() not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag.lower(), dict(attrs), self.stack[-1]))

    def handle_endtag(self, tag):
        tag = tag.lower()
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_entityref(self, name):
        raw = "&" + name + ";"
        start = self.source_offset()
        span = TextSpan(start, start + len(raw), raw, self.stack[-1])
        self.stack[-1].children.append(span)
        self.spans.append(span)

    def handle_charref(self, name):
        raw = "&#" + name + ";"
        start = self.source_offset()
        span = TextSpan(start, start + len(raw), raw, self.stack[-1])
        self.stack[-1].children.append(span)
        self.spans.append(span)

    def handle_data(self, data):
        if not data:
            return
        start = self.source_offset()
        end = start + len(data)
        if self.source[start:end] != data:
            raise ValueError("source offset mismatch; refusing to render")
        span = TextSpan(start, end, data, self.stack[-1])
        self.stack[-1].children.append(span)
        self.spans.append(span)


def descendants(node: Node):
    for child in node.children:
        if isinstance(child, Node):
            yield child
            yield from descendants(child)


def node_text(node: Node, spans: list[TextSpan]) -> str:
    allowed = {id(x) for x in spans}
    return "".join(x.text for x in spans if id(x.parent) in allowed)


def matches(node: Node, selector: str) -> bool:
    selector = selector.strip()
    if not selector:
        return False
    if selector.startswith("#"):
        return node.attrs.get("id") == selector[1:]
    if selector.startswith("."):
        return selector[1:] in node.classes
    if "." in selector:
        tag, cls = selector.split(".", 1)
        return node.tag == tag.lower() and cls in node.classes
    return node.tag == selector.lower()


def select(root: Node, selector: str) -> list[Node]:
    parts = [part.strip() for part in selector.split(",") if part.strip()]
    return [n for n in descendants(root) if any(matches(n, p) for p in parts)]


def spans_inside(node: Node, spans: list[TextSpan]) -> list[TextSpan]:
    result = []
    for span in spans:
        current = span.parent
        while current is not None and current is not node:
            current = current.parent
        if current is node:
            result.append(span)
    return result


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def resolve_row(group: str, key: str, spec: dict, container: Node,
                all_spans: list[TextSpan]) -> Node:
    candidates = [n for n in select(container, spec["row"]) if n is not container]
    if "key_by_label" in spec:
        label = spec["key_by_label"][key]
        needle = label_key(label)
        hits = [n for n in candidates if needle in label_key("".join(
            s.text for s in spans_inside(n, all_spans)
        ))]
    else:
        ticker = spec["key_by_ticker"][key]
        hits = [n for n in candidates if re.search(
            r"(?<![A-Z0-9])" + re.escape(ticker) + r"(?![A-Z0-9])",
            normalize("".join(s.text for s in spans_inside(n, all_spans)))
        )]
    if len(hits) != 1:
        raise ValueError(f"{group}.{key}: expected exactly one row, found {len(hits)}")
    return hits[0]


def slot_text_span(row: Node, selector: str, index: int,
                   all_spans: list[TextSpan], label: str) -> tuple[TextSpan, Node]:
    nodes = select(row, selector)
    if index >= len(nodes):
        raise ValueError(f"{label}: selector {selector!r} has {len(nodes)} matches; index {index} missing")
    target = nodes[index]
    texts = [s for s in spans_inside(target, all_spans) if s.text.strip()]
    if len(texts) != 1:
        raise ValueError(f"{label}: expected one editable text node in slot, found {len(texts)}")
    return texts[0], target


def direction(value: str) -> str | None:
    stripped = value.strip()
    if stripped.startswith("+"):
        return "up"
    if stripped.startswith(("-", "−")):
        return "down"
    if re.match(r"^0+(?:\.0+)?%?$", stripped):
        return "flat"
    return None


def render_market_html(html: str, snapshot: dict[str, Any], binding: dict[str, Any]) -> str:
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("groups"), dict):
        raise ValueError("snapshot must contain a groups object")
    parser = SourceTreeParser(html)
    parser.feed(html)
    parser.close()
    edits: list[tuple[int, int, str]] = []
    used: set[tuple[int, int]] = set()

    for group_name, spec in binding["groups"].items():
        if group_name not in {"global_indices", "sectors", "bonds", "fx", "energy", "precious_metals"}:
            continue
        group_data = snapshot["groups"].get(group_name)
        if not isinstance(group_data, dict):
            raise ValueError(f"snapshot group missing: {group_name}")
        container_selector = spec["container"]
        containers = select(parser.root, container_selector)
        if len(containers) != 1:
            raise ValueError(f"{group_name}: expected one container {container_selector}, found {len(containers)}")
        container = containers[0]
        keys = spec.get("key_by_label", spec.get("key_by_ticker", {}))
        if set(group_data) != set(keys):
            missing, extra = sorted(set(keys) - set(group_data)), sorted(set(group_data) - set(keys))
            raise ValueError(f"{group_name}: key mismatch; missing={missing}, extra={extra}")

        for key in keys:
            record = group_data[key]
            if not isinstance(record, dict):
                raise ValueError(f"{group_name}.{key}: record must be an object")
            row = resolve_row(group_name, key, spec, container, parser.spans)
            value_field = spec["snapshot_fields"]["display_value"]
            value_text = record.get(value_field)
            if not isinstance(value_text, str) or not value_text:
                raise ValueError(f"{group_name}.{key}: {value_field} must be a non-empty string")
            value_index = int(spec.get("value_index", 0))
            value_span, value_node = slot_text_span(
                row, spec["value_selector"], value_index, parser.spans,
                f"{group_name}.{key}.value"
            )
            targets = [(value_span, value_text, value_node, "value")]

            change_field = spec["snapshot_fields"].get("display_change")
            if change_field:
                change_text = record.get(change_field)
                if not isinstance(change_text, str) or not change_text:
                    raise ValueError(f"{group_name}.{key}: {change_field} must be a non-empty string")
                change_index = int(spec.get("change_index", 1))
                change_span, change_node = slot_text_span(
                    row, spec["change_selector"], change_index, parser.spans,
                    f"{group_name}.{key}.change"
                )
                old_direction = next((c for c in ("up", "down", "flat", "warn") if c in change_node.classes), None)
                new_direction = direction(change_text)
                if new_direction and old_direction and new_direction != old_direction:
                    raise ValueError(
                        f"{group_name}.{key}: direction class would be stale "
                        f"({old_direction} -> {new_direction}); attribute mutation is not authorized"
                    )
                targets.append((change_span, change_text, change_node, "change"))

            for span, value, _node, slot_name in targets:
                identity = (span.start, span.end)
                if identity in used:
                    raise ValueError(f"overlapping text target at {group_name}.{key}.{slot_name}")
                used.add(identity)
                edits.append((span.start, span.end, escape(value, quote=False)))

    result = html
    for start, end, replacement in sorted(edits, reverse=True):
        result = result[:start] + replacement + result[end:]
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--template", required=True)
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--binding", default="scripts/tac_html_binding_map.json")
    args = ap.parse_args()
    template = (ROOT / args.template).resolve()
    snapshot_path = (ROOT / args.snapshot).resolve()
    output = (ROOT / args.output).resolve()
    protected = {
        (ROOT / "index.html").resolve(),
        (ROOT / "母版專區/TAC_母版_週一_2026-10-28_最終定版.html").resolve(),
        (ROOT / "母版專區/TAC_母版_週二至週五_2026-10-28_最終定版.html").resolve(),
        (ROOT / "母版專區/mother-template-manifest.json").resolve(),
        (ROOT / "TAC_WORK_RULES.md").resolve(),
    }
    if output in protected or output == template or output == snapshot_path:
        raise SystemExit("refusing to overwrite a protected/input path")
    try:
        binding = json.loads((ROOT / args.binding).read_text(encoding="utf-8"))
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        original = template.read_text(encoding="utf-8")
        rendered = render_market_html(original, snapshot, binding)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    except Exception as exc:
        print(f"RENDER BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(f"PASS: wrote {output.relative_to(ROOT)}; only mapped text nodes changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
