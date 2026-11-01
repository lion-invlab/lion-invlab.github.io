#!/usr/bin/env python3
"""Contract-driven, fail-closed renderer for approved TAC content slots and dynamic lists.

Static market/editorial slots are text-only. News and calendar cards may be
added or removed only inside explicitly mapped list containers, using approved
mother-template prototypes. All markup, attributes, CSS, scripts, and controls
outside those dynamic regions remain byte-for-byte protected.
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


@dataclass(eq=False)
class Node:
    tag: str
    attrs: dict[str, str | None]
    parent: "Node | None" = None
    children: list["Node | TextSpan"] = field(default_factory=list)
    class_value_span: tuple[int, int] | None = None
    attr_value_spans: dict[str, tuple[int, int]] = field(default_factory=dict)
    start_tag_end: int | None = None
    end_tag_start: int | None = None
    end_tag_end: int | None = None
    source_start: int | None = None

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
        start = self.source_offset()
        raw_tag = self.get_starttag_text() or ""
        node = Node(tag.lower(), dict(attrs), self.stack[-1])
        node.start_tag_end = start + len(raw_tag)
        node.source_start = start
        if tag.lower() in VOID:
            node.end_tag_start = node.start_tag_end
            node.end_tag_end = node.start_tag_end
        class_match = re.search(r"""\bclass\s*=\s*(["'])(.*?)\1""", raw_tag, re.I | re.S)
        if class_match:
            node.class_value_span = (start + class_match.start(2), start + class_match.end(2))
        for attr_name in ("style", "aria-label", "href"):
            attr_match = re.search(r"""\b""" + re.escape(attr_name) + r"""\s*=\s*(["'])(.*?)\1""", raw_tag, re.I | re.S)
            if attr_match:
                node.attr_value_spans[attr_name] = (start + attr_match.start(2), start + attr_match.end(2))
        self.stack[-1].children.append(node)
        if tag.lower() not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        start = self.source_offset()
        raw_tag = self.get_starttag_text() or ""
        node = Node(tag.lower(), dict(attrs), self.stack[-1])
        node.source_start = start
        node.start_tag_end = start + len(raw_tag)
        node.end_tag_start = node.start_tag_end
        node.end_tag_end = node.start_tag_end
        self.stack[-1].children.append(node)

    def handle_endtag(self, tag):
        tag = tag.lower()
        end_start = self.source_offset()
        end_end = self.source.find(">", end_start)
        if end_end < 0:
            raise ValueError("malformed closing tag; refusing source splice")
        end_end += 1
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                self.stack[i].end_tag_start = end_start
                self.stack[i].end_tag_end = end_end
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


def status_group_for(node: Node) -> Node | None:
    current = node.parent
    while current is not None:
        if "calendar-status-group" in current.classes:
            return current
        current = current.parent
    return None


def inner_bounds(node: Node) -> tuple[int, int]:
    """Return the source interval inside one parsed element, never including its tags."""
    if node.start_tag_end is None or node.end_tag_start is None or node.end_tag_end is None:
        raise ValueError(f"{node.tag}: source boundaries unavailable; refusing dynamic-region edit")
    if node.start_tag_end > node.end_tag_start:
        raise ValueError(f"{node.tag}: invalid source boundaries; refusing dynamic-region edit")
    return node.start_tag_end, node.end_tag_start


def replace_sibling_sequence(source: str, parser: SourceTreeParser,
                            nodes: list[Node], desired_count: int,
                            label: str) -> str:
    """Resize a contiguous approved card run without rewriting existing cards."""
    if not isinstance(desired_count, int) or desired_count < 0:
        raise ValueError(f"{label}: desired card count must be a non-negative integer")
    if not nodes:
        if desired_count == 0:
            return source
        raise ValueError(f"{label}: no approved card prototype exists")
    parent = nodes[0].parent
    if parent is None or any(node.parent is not parent for node in nodes):
        raise ValueError(f"{label}: cards are not siblings; refusing dynamic resize")
    positions = [next(i for i, child in enumerate(parent.children) if child is node) for node in nodes]
    if positions != sorted(positions):
        raise ValueError(f"{label}: card sequence order is invalid")
    for child in parent.children[positions[0]:positions[-1] + 1]:
        if isinstance(child, Node) and child not in nodes:
            raise ValueError(f"{label}: non-card element inside dynamic sequence")
        if isinstance(child, TextSpan) and child.text.strip():
            raise ValueError(f"{label}: non-whitespace text inside dynamic sequence")
    for node in nodes:
        if node.source_start is None or node.end_tag_end is None or node.source_start > node.end_tag_end:
            raise ValueError(f"{label}: card source range unavailable")
    current_count = len(nodes)
    if desired_count == current_count:
        return source
    if desired_count < current_count:
        # Keep the first desired_count cards byte-for-byte; remove only the tail.
        remove_start = nodes[desired_count].source_start if desired_count else nodes[0].source_start
        remove_end = nodes[-1].end_tag_end
        return source[:remove_start] + source[remove_end:]
    # Growth appends clones of the approved first-card prototype after all existing cards.
    prototype = source[nodes[0].source_start:nodes[0].end_tag_end]
    if not prototype:
        raise ValueError(f"{label}: empty approved card prototype")
    extra = desired_count - current_count
    insertion = "\n" + "\n".join(prototype for _ in range(extra))
    insert_at = nodes[-1].end_tag_end
    return source[:insert_at] + insertion + source[insert_at:]


def spans_inside(node: Node, spans: list[TextSpan]) -> list[TextSpan]:
    result = []
    for span in spans:
        current = span.parent
        while current is not None and current is not node:
            current = current.parent
        if current is node:
            result.append(span)
    return result



def coalesce_spans(spans: list[TextSpan]) -> list[TextSpan]:
    """Join adjacent source text/entity spans into one logical text slot."""
    ordered = sorted(spans, key=lambda item: item.start)
    if not ordered:
        return []
    result: list[TextSpan] = []
    start, end = ordered[0].start, ordered[0].end
    text_parts = [ordered[0].text]
    parent = ordered[0].parent
    for span in ordered[1:]:
        if span.parent is parent and span.start == end:
            end = span.end
            text_parts.append(span.text)
        else:
            result.append(TextSpan(start, end, "".join(text_parts), parent))
            start, end, text_parts, parent = span.start, span.end, [span.text], span.parent
    result.append(TextSpan(start, end, "".join(text_parts), parent))
    return result

def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def label_key(text: str) -> str:
    return "".join(ch.casefold() for ch in unescape(text) if ch.isalnum())


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


def direction(value: str, rules: dict[str, Any]) -> str | None:
    stripped = value.strip()
    status_map = rules.get("status_class_map", {})
    if stripped == rules.get("pending_value_text", "待核實"):
        return status_map.get("warning", "warn")
    if stripped.startswith("+"):
        return status_map.get("positive", "up")
    if stripped.startswith(("-", "−")):
        return status_map.get("negative", "down")
    if re.match(r"^0+(?:\.0+)?%?$", stripped):
        return status_map.get("neutral", "flat")
    return None


def render_risk_indicators(html: str, parser: SourceTreeParser,
                           snapshot: dict[str, Any], binding: dict[str, Any],
                           edits: list[tuple[int, int, str]],
                           used: set[tuple[int, int]]) -> None:
    spec = binding.get("groups", {}).get("risk_indicators")
    data = snapshot.get("risk_indicators")
    if spec is None or data is None:
        return
    if not isinstance(data, dict):
        raise ValueError("risk_indicators snapshot must be an object")
    containers = select(parser.root, spec["container"])
    if len(containers) != 1:
        raise ValueError(f"risk_indicators: expected one container, found {len(containers)}")
    container = containers[0]
    records = spec.get("records", {})
    if set(data) != set(records):
        missing, extra = sorted(set(records) - set(data)), sorted(set(data) - set(records))
        raise ValueError(f"risk_indicators: key mismatch; missing={missing}, extra={extra}")

    for key, record_spec in records.items():
        record = data[key]
        if not isinstance(record, dict):
            raise ValueError(f"risk_indicators.{key}: record must be an object")
        needle = label_key(record_spec["key_text"])
        rows = select(container, record_spec["row"])
        def has_key(row: Node) -> bool:
            key_selector = record_spec.get("key_selector")
            key_nodes = select(row, key_selector) if key_selector else [row]
            if len(key_nodes) != 1:
                return False
            key_text = "".join(span.text for span in spans_inside(key_nodes[0], parser.spans))
            normalized_key = label_key(key_text)
            return needle == normalized_key if key_selector else needle in normalized_key
        hits = [row for row in rows if has_key(row)]
        if len(hits) != 1:
            raise ValueError(f"risk_indicators.{key}: expected one row, found {len(hits)}")
        row = hits[0]
        value_nodes = select(row, record_spec["value_selector"])
        if len(value_nodes) != 1:
            raise ValueError(f"risk_indicators.{key}: expected one value node, found {len(value_nodes)}")
        value_spans = [span for span in spans_inside(value_nodes[0], parser.spans) if span.text.strip()]
        if len(value_spans) != 1:
            raise ValueError(f"risk_indicators.{key}: expected one value text node, found {len(value_spans)}")
        value_text = record.get("value")
        if not isinstance(value_text, str) or not value_text:
            raise ValueError(f"risk_indicators.{key}: value must be a non-empty string")
        value_span = value_spans[0]
        identity = (value_span.start, value_span.end)
        if identity in used:
            raise ValueError(f"risk_indicators.{key}: overlapping value target")
        used.add(identity)
        edits.append((value_span.start, value_span.end, escape(value_text, quote=False)))

        change_selector = record_spec.get("change_selector")
        if not change_selector:
            continue
        change_nodes = select(row, change_selector)
        if len(change_nodes) != 1:
            raise ValueError(f"risk_indicators.{key}: expected one change node, found {len(change_nodes)}")
        change_spans = [span for span in spans_inside(change_nodes[0], parser.spans) if span.text.strip()]
        if len(change_spans) != 1:
            raise ValueError(f"risk_indicators.{key}: expected one change text node, found {len(change_spans)}")
        change_text = record.get("change")
        if not isinstance(change_text, str) or not change_text:
            raise ValueError(f"risk_indicators.{key}: change must be a non-empty string")
        change_span = change_spans[0]
        identity = (change_span.start, change_span.end)
        if identity in used:
            raise ValueError(f"risk_indicators.{key}: overlapping change target")
        used.add(identity)
        edits.append((change_span.start, change_span.end, escape(change_text, quote=False)))

        status_map = record_spec.get("status_class_map", binding.get("rules", {}).get("status_class_map", {}))
        local_rules = dict(binding.get("rules", {}))
        local_rules["status_class_map"] = status_map
        new_status = direction(change_text, local_rules)
        if new_status is not None and change_span.text != change_text:
            old_tokens = [token for token in ("up", "down", "flat", "warn") if token in change_nodes[0].classes]
            if len(old_tokens) != 1:
                raise ValueError(f"risk_indicators.{key}: expected exactly one existing status class token, found {old_tokens}")
            old_status = old_tokens[0]
            if new_status != old_status:
                if not binding.get("rules", {}).get("allow_mapped_status_class_token_transition", False):
                    raise ValueError(f"risk_indicators.{key}: status class transition is not authorized")
                class_span = change_nodes[0].class_value_span
                if class_span is None:
                    raise ValueError(f"risk_indicators.{key}: class attribute source span is missing")
                class_start, class_end = class_span
                raw_class = html[class_start:class_end]
                token_matches = list(re.finditer(r"(?<!\S)" + re.escape(old_status) + r"(?!\S)", raw_class))
                if len(token_matches) != 1:
                    raise ValueError(f"risk_indicators.{key}: status class token is not unique")
                token = token_matches[0]
                edits.append((class_start + token.start(), class_start + token.end(), new_status))


def render_fedwatch(html: str, parser: SourceTreeParser,
                    snapshot: dict[str, Any], binding: dict[str, Any],
                    edits: list[tuple[int, int, str]],
                    used: set[tuple[int, int]]) -> None:
    spec = binding.get("groups", {}).get("fedwatch")
    data = snapshot.get("fedwatch")
    if spec is None or data is None:
        return
    pending = isinstance(data, dict) and data.get("status") == "pending_verification"
    required = {"probabilities", "target_meeting", "updated_at", "target_rate_range", "audit_text", "aria_label"}
    expected = required | {"status"} if pending else required
    if not isinstance(data, dict) or set(data) != expected:
        raise ValueError("fedwatch snapshot has an invalid renderer contract")
    probabilities = data["probabilities"]
    if not isinstance(probabilities, dict) or set(probabilities) != set(spec["outcomes"]):
        raise ValueError("fedwatch probabilities must contain exactly the mapped outcomes")
    parsed = {}
    for key, outcome in spec["outcomes"].items():
        item = probabilities[key]
        if not isinstance(item, dict) or set(item) != {"probability", "rate_range"}:
            raise ValueError(f"fedwatch.{key}: expected probability and rate_range")
        p = item["probability"]
        if not isinstance(p, (int, float)) or not 0 <= p <= 100:
            raise ValueError(f"fedwatch.{key}: probability out of range")
        if not isinstance(item["rate_range"], str) or not item["rate_range"]:
            raise ValueError(f"fedwatch.{key}: rate range missing")
        if pending:
            if p != 0 or item["rate_range"] != "待核實":
                raise ValueError(f"fedwatch.{key}: pending state must not contain an implied probability or rate range")
            parsed[key] = (0.0, "待核實", "待核實")
        else:
            parsed[key] = (float(p), f"{p:.1f}%", item["rate_range"])
    total = sum(x[0] for x in parsed.values())
    if not pending and abs(total - 100.0) > 0.11:
        raise ValueError(f"fedwatch probabilities sum to {total:.2f}, not 100")
    containers = select(parser.root, spec["container"])
    if len(containers) != 1:
        raise ValueError("fedwatch container missing or duplicated")
    container = containers[0]

    def add_text(node: Node, text: str, label: str):
        spans = [x for x in spans_inside(node, parser.spans) if x.text.strip()]
        if len(spans) != 1:
            raise ValueError(f"{label}: expected one text node, found {len(spans)}")
        span = spans[0]
        ident = (span.start, span.end)
        if ident in used:
            raise ValueError(f"{label}: overlapping text slot")
        used.add(ident)
        edits.append((span.start, span.end, escape(text, quote=False)))

    for key, outcome in spec["outcomes"].items():
        rows = select(container, outcome["row"])
        if len(rows) != 1:
            raise ValueError(f"fedwatch.{key}: outcome row missing or duplicated")
        row = rows[0]
        labels = [n for n in descendants(row) if n.tag == "span" and label_key("".join(x.text for x in spans_inside(n, parser.spans))) == label_key(outcome["label"])]
        if len(labels) != 1:
            raise ValueError(f"fedwatch.{key}: label mismatch")
        p_nodes, range_nodes = select(row, outcome["probability_selector"]), select(row, outcome["rate_range_selector"])
        if len(p_nodes) != 1 or len(range_nodes) != 1:
            raise ValueError(f"fedwatch.{key}: probability/range slot ambiguous")
        p, p_text, rate_text = parsed[key]
        add_text(p_nodes[0], p_text, f"fedwatch.{key}.probability")
        add_text(range_nodes[0], rate_text, f"fedwatch.{key}.rate_range")
        bar_nodes = select(container, outcome["bar_selector"])
        if len(bar_nodes) != 1:
            raise ValueError(f"fedwatch.{key}: bar missing or duplicated")
        style_span = bar_nodes[0].attr_value_spans.get("style")
        if style_span is None:
            raise ValueError(f"fedwatch.{key}: style attribute missing")
        raw_style = html[style_span[0]:style_span[1]]
        widths = list(re.finditer(r"(?i)(?<![\w-])width\s*:\s*[^;]+", raw_style))
        if len(widths) != 1:
            raise ValueError(f"fedwatch.{key}: width token ambiguous")
        w = widths[0]
        ident = (style_span[0] + w.start(), style_span[0] + w.end())
        current_width = re.search(r"([0-9]+(?:\.[0-9]+)?)%", raw_style)
        if current_width is None:
            raise ValueError(f"fedwatch.{key}: existing width value is not a percentage")
        if abs(float(current_width.group(1)) - p) > 0.001:
            if ident in used:
                raise ValueError(f"fedwatch.{key}: overlapping width slot")
            used.add(ident)
            edits.append((ident[0], ident[1], f"width:{p:g}%"))

    legend = select(container, spec["legend_selector"])
    if len(legend) != 1:
        raise ValueError("fedwatch legend missing or duplicated")
    legend_rows = [n for n in descendants(legend[0]) if n.tag == "span"]
    if len(legend_rows) != len(spec["outcomes"]):
        raise ValueError("fedwatch legend outcome count mismatch")
    for key, outcome in spec["outcomes"].items():
        idx = int(outcome["legend_index"])
        bold = select(legend_rows[idx], "b")
        if len(bold) != 1:
            raise ValueError(f"fedwatch.{key}: legend value missing")
        add_text(bold[0], parsed[key][1], f"fedwatch.{key}.legend")

    split = select(container, spec["split_bar_selector"])
    if len(split) != 1 or "aria-label" not in split[0].attr_value_spans:
        raise ValueError("fedwatch split bar aria-label missing or duplicated")
    a, b = split[0].attr_value_spans["aria-label"]
    aria = data["aria_label"]
    if not isinstance(aria, str) or not aria:
        raise ValueError("fedwatch aria_label must be a non-empty string")
    if (a, b) in used:
        raise ValueError("fedwatch aria-label overlap")
    used.add((a, b))
    edits.append((a, b, escape(aria, quote=True)))

    fomc = spec["fomc"]
    for row_key, selector, value in (
        ("meeting", fomc["meeting_row"], data["target_meeting"]),
        ("rate", fomc["rate_row"], data["target_rate_range"])
    ):
        rows = select(container, selector)
        if len(rows) != 1:
            raise ValueError(f"fedwatch FOMC {row_key} row missing or duplicated")
        vals = select(rows[0], "b")
        if len(vals) != 1:
            raise ValueError(f"fedwatch FOMC {row_key} value ambiguous")
        add_text(vals[0], value, f"fedwatch.{row_key}")

    audit_containers = select(container, spec["audit_container_selector"])
    if len(audit_containers) != 1:
        raise ValueError("fedwatch audit container missing or duplicated")
    details = select(audit_containers[0], spec["audit_selector"])
    if len(details) != 1:
        raise ValueError("fedwatch audit disclosure missing or duplicated")
    audit_divs = [n for n in descendants(details[0]) if n.tag == "div" and spans_inside(n, parser.spans)]
    if len(audit_divs) != 1:
        raise ValueError("fedwatch audit text target ambiguous")
    add_text(audit_divs[0], data["audit_text"], "fedwatch.audit_text")


def render_editorial(html: str, parser: SourceTreeParser,
                     snapshot: dict[str, Any], binding: dict[str, Any],
                     edits: list[tuple[int, int, str]],
                     used: set[tuple[int, int]]) -> None:
    spec = binding.get("groups", {}).get("editorial")
    data = snapshot.get("editorial")
    if spec is None or data is None:
        return
    required = {"headline", "body_segments", "market_text", "levels_segments", "core_text"}
    if not isinstance(data, dict) or set(data) != required:
        raise ValueError("editorial snapshot must contain headline, body_segments, market_text, levels_segments, core_text")

    def add_text(span: TextSpan, text: str, label: str):
        if not isinstance(text, str) or not text:
            raise ValueError(f"{label}: text must be non-empty")
        ident = (span.start, span.end)
        if ident in used:
            raise ValueError(f"{label}: overlapping mapped text slot")
        used.add(ident)
        edits.append((span.start, span.end, escape(text, quote=False)))

    summary = spec["summary"]
    summary_nodes = select(parser.root, summary["container"])
    if len(summary_nodes) != 1:
        raise ValueError("editorial summary container missing or duplicated")
    headlines = select(summary_nodes[0], summary["headline_selector"])
    body_nodes = select(summary_nodes[0], summary["body_selector"])
    if len(headlines) != 1 or len(body_nodes) != 1:
        raise ValueError("editorial summary headline/body slot ambiguous")
    headline_spans = [x for x in spans_inside(headlines[0], parser.spans) if x.text.strip()]
    if len(headline_spans) != 1:
        raise ValueError("editorial summary headline must be one text node")
    add_text(headline_spans[0], data["headline"], "editorial.headline")
    body_spans = coalesce_spans([x for x in spans_inside(body_nodes[0], parser.spans) if x.parent is body_nodes[0] and x.text.strip()])
    if not isinstance(data["body_segments"], list) or len(body_spans) != len(data["body_segments"]):
        raise ValueError(f"editorial summary segment count mismatch: template={len(body_spans)}, snapshot={len(data.get('body_segments', []))}")
    for i, (span, text) in enumerate(zip(body_spans, data["body_segments"])):
        add_text(span, text, f"editorial.body_segments[{i}]")

    observation = spec["observation"]
    panels = {
        "market_text": observation["market_panel"],
        "levels_segments": observation["levels_panel"],
        "core_text": observation["core_panel"]
    }
    selectors = {
        "market_text": observation["market_text_selector"],
        "levels_segments": observation["levels_text_selector"],
        "core_text": observation["core_text_selector"]
    }
    for field_name, panel_selector in panels.items():
        panel_nodes = select(parser.root, panel_selector)
        if len(panel_nodes) != 1:
            raise ValueError(f"editorial.{field_name}: panel missing or duplicated")
        content_nodes = select(panel_nodes[0], selectors[field_name])
        if len(content_nodes) != 1:
            raise ValueError(f"editorial.{field_name}: content slot missing or duplicated")
        direct_spans = coalesce_spans([x for x in spans_inside(content_nodes[0], parser.spans)
                        if x.parent is content_nodes[0] and x.text.strip()])
        value = data[field_name]
        if isinstance(value, list):
            if len(direct_spans) != len(value):
                raise ValueError(f"editorial.{field_name}: segment count mismatch; template={len(direct_spans)}, snapshot={len(value)}")
            for i, (span, text) in enumerate(zip(direct_spans, value)):
                add_text(span, text, f"editorial.{field_name}[{i}]")
        else:
            if len(direct_spans) != 1:
                raise ValueError(f"editorial.{field_name}: expected one direct text node, found {len(direct_spans)}")
            add_text(direct_spans[0], value, f"editorial.{field_name}")


def render_news(html: str, parser: SourceTreeParser,
                snapshot: dict[str, Any], binding: dict[str, Any],
                edits: list[tuple[int, int, str]],
                used: set[tuple[int, int]]) -> None:
    spec = binding.get("groups", {}).get("news")
    data = snapshot.get("news")
    if spec is None or data is None:
        return
    if not isinstance(data, dict) or set(data) != set(spec["panels"]):
        raise ValueError("news snapshot must contain exactly the mapped news panels")

    def add_text(node: Node, text: str, label: str):
        spans = coalesce_spans([x for x in spans_inside(node, parser.spans) if x.text.strip()])
        if not spans:
            raise ValueError(f"{label}: text slot is empty")
        # Some approved prototype values contain nested inline markup and therefore
        # multiple text spans. Preserve every element/attribute; place the new text
        # in the first span and clear only the remaining text spans.
        for index, span in enumerate(spans):
            ident = (span.start, span.end)
            if ident in used:
                raise ValueError(f"{label}: overlapping text slot")
            used.add(ident)
            replacement = escape(text, quote=False) if index == 0 else ""
            edits.append((span.start, span.end, replacement))

    def add_href(node: Node, url: str, label: str):
        if not isinstance(url, str) or not url.startswith("https://") or any(ch in url for ch in ('"', "'", "<", ">")):
            raise ValueError(f"{label}: source URL must be a valid https URL")
        span = node.attr_value_spans.get("href")
        if span is None:
            raise ValueError(f"{label}: existing href attribute missing")
        if span in used:
            raise ValueError(f"{label}: overlapping href slot")
        used.add(span)
        edits.append((span[0], span[1], escape(url, quote=True)))

    for panel_key, panel_spec in spec["panels"].items():
        panel_data = data[panel_key]
        if not isinstance(panel_data, dict) or not {"meta_text", "items"} <= set(panel_data) or set(panel_data) - {"meta_text", "items", "window_text"}:
            raise ValueError(f"news.{panel_key}: invalid snapshot fields")
        containers = select(parser.root, panel_spec["container"])
        if len(containers) != 1:
            raise ValueError(f"news.{panel_key}: container missing or duplicated")
        container = containers[0]
        meta_nodes = select(container, panel_spec["meta_selector"])
        if len(meta_nodes) != 1:
            raise ValueError(f"news.{panel_key}: tab metadata missing or duplicated")
        add_text(meta_nodes[0], panel_data["meta_text"], f"news.{panel_key}.meta")
        warning_nodes = select(container, panel_spec["warning_selector"])
        if len(warning_nodes) == 1:
            if "window_text" not in panel_data:
                raise ValueError(f"news.{panel_key}: required time-window warning text missing")
            add_text(warning_nodes[0], panel_data["window_text"], f"news.{panel_key}.window")
        elif len(warning_nodes) > 1 or "window_text" in panel_data:
            raise ValueError(f"news.{panel_key}: unexpected or duplicated time-window warning slot")

        item_nodes = select(container, panel_spec["item_selector"])
        items = panel_data["items"]
        if not isinstance(items, list) or len(item_nodes) != len(items):
            raise ValueError(f"news.{panel_key}: card count mismatch; template={len(item_nodes)}, snapshot={len(items) if isinstance(items, list) else 'invalid'}")
        for index, (item_node, item) in enumerate(zip(item_nodes, items)):
            label = f"news.{panel_key}.items[{index}]"
            if not isinstance(item, dict) or set(item) != {"title", "summary", "sources"}:
                raise ValueError(f"{label}: expected title, summary, sources")
            titles = select(item_node, panel_spec["title_selector"])
            summaries = select(item_node, panel_spec["summary_selector"])
            source_containers = select(item_node, panel_spec["sources_container_selector"])
            if len(titles) != 1 or len(summaries) != 1 or len(source_containers) != 1:
                raise ValueError(f"{label}: title, summary or source container ambiguous")
            add_text(titles[0], item["title"], f"{label}.title")
            add_text(summaries[0], item["summary"], f"{label}.summary")
            anchors = select(source_containers[0], panel_spec["source_selector"])
            sources = item["sources"]
            if not isinstance(sources, list) or len(anchors) != len(sources):
                raise ValueError(f"{label}: source link count mismatch")
            for source_index, (anchor, source) in enumerate(zip(anchors, sources)):
                if not isinstance(source, dict) or set(source) != {"url", "text"}:
                    raise ValueError(f"{label}.sources[{source_index}]: expected url and text")
                add_href(anchor, source["url"], f"{label}.sources[{source_index}].url")
                add_text(anchor, source["text"], f"{label}.sources[{source_index}].text")


def update_optional_class(node: Node, allowed_tokens: set[str], desired_token: str | None,
                         html: str, edits: list[tuple[int, int, str]],
                         used: set[tuple[int, int]], label: str) -> None:
    """Change only explicitly mapped optional status tokens in one class attribute."""
    span = node.class_value_span
    if span is None:
        raise ValueError(f"{label}: class attribute source span missing")
    if span in used:
        raise ValueError(f"{label}: overlapping class attribute edit")
    raw = html[span[0]:span[1]]
    tokens = raw.split()
    existing = [token for token in tokens if token in allowed_tokens]
    if len(existing) > 1:
        raise ValueError(f"{label}: multiple mapped status classes present")
    if desired_token is not None and desired_token not in allowed_tokens:
        raise ValueError(f"{label}: unsupported mapped status class")
    kept = [token for token in tokens if token not in allowed_tokens]
    if desired_token is not None:
        kept.append(desired_token)
    replacement = " ".join(kept)
    if replacement == raw:
        return
    used.add(span)
    edits.append((span[0], span[1], replacement))


def add_link_list(node: Node, links: list[dict[str, str]], html: str,
                  edits: list[tuple[int, int, str]], used: set[tuple[int, int]],
                  label: str) -> None:
    """Replace only the inner content of one approved source-value slot with its links."""
    if not isinstance(links, list) or not links:
        raise ValueError(f"{label}: source links must be a non-empty list")
    start, end = inner_bounds(node)
    ident = (start, end)
    if ident in used:
        raise ValueError(f"{label}: overlapping source-link content slot")
    rendered = []
    for index, source in enumerate(links):
        if not isinstance(source, dict) or set(source) != {"url", "text"}:
            raise ValueError(f"{label}[{index}]: source must contain url and text")
        url = source["url"]
        text = source["text"]
        if not isinstance(url, str) or not url.startswith("https://") or any(ch in url for ch in ('"', "'", "<", ">")):
            raise ValueError(f"{label}[{index}]: invalid https URL")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"{label}[{index}]: source text is required")
        rendered.append(f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener">{escape(text, quote=False)}</a>')
    used.add(ident)
    edits.append((start, end, "；".join(rendered)))


def render_economic_calendar(html: str, parser: SourceTreeParser,
                             snapshot: dict[str, Any], binding: dict[str, Any],
                             edits: list[tuple[int, int, str]],
                             used: set[tuple[int, int]]) -> None:
    spec = binding.get("groups", {}).get("economic_calendar")
    data = snapshot.get("economic_calendar")
    if spec is None or data is None:
        return
    if not isinstance(data, dict) or set(data) != {"panels"} or not isinstance(data["panels"], dict):
        raise ValueError("economic_calendar snapshot must contain a panels object")
    selectors = spec["selectors"]

    def add_text(node: Node, text: str, label: str):
        spans = coalesce_spans([x for x in spans_inside(node, parser.spans) if x.text.strip()])
        if not spans:
            raise ValueError(f"{label}: text slot is empty")
        # Some approved prototype values contain nested inline markup and therefore
        # multiple text spans. Preserve every element/attribute; place the new text
        # in the first span and clear only the remaining text spans.
        for index, span in enumerate(spans):
            ident = (span.start, span.end)
            if ident in used:
                raise ValueError(f"{label}: overlapping text slot")
            used.add(ident)
            replacement = escape(text, quote=False) if index == 0 else ""
            edits.append((span.start, span.end, replacement))

    def add_link(anchor: Node, source: dict[str, str], label: str):
        if not isinstance(source, dict) or set(source) != {"url", "text"}:
            raise ValueError(f"{label}: source must contain url and text")
        url = source["url"]
        if not isinstance(url, str) or not url.startswith("https://") or any(ch in url for ch in ('"', "'", "<", ">")):
            raise ValueError(f"{label}: invalid https URL")
        href_span = anchor.attr_value_spans.get("href")
        if href_span is None or href_span in used:
            raise ValueError(f"{label}: href slot missing or overlapping")
        used.add(href_span)
        edits.append((href_span[0], href_span[1], escape(url, quote=True)))
        add_text(anchor, source["text"], f"{label}.text")

    for panel_key, panel_spec in spec["panels"].items():
        containers = select(parser.root, panel_spec["container"])
        panel_data = data["panels"].get(panel_key)
        if not containers:
            if panel_data is not None:
                raise ValueError(f"economic_calendar.{panel_key}: panel not present in this template")
            continue
        if len(containers) != 1:
            raise ValueError(f"economic_calendar.{panel_key}: container missing or duplicated")
        if panel_data is None:
            raise ValueError(f"economic_calendar.{panel_key}: snapshot panel missing")
        if not isinstance(panel_data, dict) or not (
            set(panel_data) == {"items"} and isinstance(panel_data["items"], list)
            or set(panel_data) == {"lists"} and isinstance(panel_data["lists"], list)
        ):
            raise ValueError(f"economic_calendar.{panel_key}: invalid panel snapshot")
        if "lists" in panel_data:
            if not isinstance(panel_data["lists"], list):
                raise ValueError(f"economic_calendar.{panel_key}: lists must be an array")
            groups = select(containers[0], ".calendar-status-group")
            legacy_mode = False
            if len(groups) != len(panel_data["lists"]):
                existing_lists = select(containers[0], panel_spec["list_selector"])
                if len(existing_lists) == len(panel_data["lists"]):
                    legacy_mode = True
                else:
                    raise ValueError(f"economic_calendar.{panel_key}: status-group count mismatch")
            event_nodes, items = [], []
            for group_index, list_data in enumerate(panel_data["lists"]):
                if not isinstance(list_data, dict) or set(list_data) != {"items"} or not isinstance(list_data["items"], list):
                    raise ValueError(f"economic_calendar.{panel_key}.lists[{group_index}]: invalid items list")
                group_lists = [existing_lists[group_index]] if legacy_mode else select(groups[group_index], panel_spec["list_selector"])
                if len(group_lists) > 1:
                    raise ValueError(f"economic_calendar.{panel_key}.lists[{group_index}]: duplicate list container")
                if not group_lists:
                    if list_data["items"]:
                        raise ValueError(f"economic_calendar.{panel_key}.lists[{group_index}]: populated list container missing after resize")
                    continue
                group_events = select(group_lists[0], panel_spec["event_selector"])
                if len(group_events) != len(list_data["items"]):
                    raise ValueError(f"economic_calendar.{panel_key}.lists[{group_index}]: event count mismatch")
                event_nodes.extend(group_events)
                items.extend(list_data["items"])
        else:
            event_nodes = select(containers[0], panel_spec["event_selector"])
            items = panel_data.get("items", [])
        if len(event_nodes) != len(items):
            raise ValueError(f"economic_calendar.{panel_key}: event count mismatch; template={len(event_nodes)}, snapshot={len(items)}")
        for index, (event_node, item) in enumerate(zip(event_nodes, items)):
            label = f"economic_calendar.{panel_key}.items[{index}]"
            required = {"expected_name", "date", "time", "country", "name", "stars_text", "fields"}
            if not isinstance(item, dict) or set(item) != required:
                raise ValueError(f"{label}: invalid event fields")
            name_nodes = select(event_node, selectors["name"])
            if len(name_nodes) != 1:
                raise ValueError(f"{label}: event name slot missing or duplicated")
            current_name = normalize(unescape("".join(x.text for x in spans_inside(name_nodes[0], parser.spans))))
            if item["expected_name"] not in (None, "") and current_name != normalize(item["expected_name"]):
                raise ValueError(f"{label}: event identity mismatch; expected template '{current_name}', snapshot '{item['expected_name']}'")
            for field_name in ("date", "time", "country", "name"):
                nodes = select(event_node, selectors[field_name])
                if len(nodes) != 1:
                    raise ValueError(f"{label}.{field_name}: slot missing or duplicated")
                add_text(nodes[0], item[field_name], f"{label}.{field_name}")
            star_nodes = select(event_node, selectors["stars"])
            if len(star_nodes) != 1:
                raise ValueError(f"{label}.stars_text: slot missing or duplicated")
            if not isinstance(item["stars_text"], str):
                raise ValueError(f"{label}: stars_text must be text")
            add_text(star_nodes[0], item["stars_text"], f"{label}.stars_text")
            star_count = item["stars_text"].count("★")
            if item["expected_name"] in (None, ""):
                desired_star_class = "five-star" if star_count == 5 else "four-star" if star_count == 4 else None
                update_optional_class(event_node, {"four-star", "five-star"}, desired_star_class,
                                      html, edits, used, f"{label}.star_class")
            detail_nodes = select(event_node, selectors["details"])
            if len(detail_nodes) != 1:
                raise ValueError(f"{label}: details container missing or duplicated")
            field_nodes = select(detail_nodes[0], selectors["field"])
            if len(field_nodes) != len(item["fields"]):
                raise ValueError(f"{label}: detail field count mismatch")
            for field_index, (field_node, field_data) in enumerate(zip(field_nodes,item["fields"])):
                field_label_nodes = select(field_node, selectors["field_label"])
                value_nodes = select(field_node, selectors["field_value"])
                if len(field_label_nodes) != 1 or len(value_nodes) != 1:
                    raise ValueError(f"{label}.fields[{field_index}]: label/value slot ambiguous")
                if not isinstance(field_data,dict) or not isinstance(field_data.get("label"), str):
                    raise ValueError(f"{label}.fields[{field_index}]: field label must be text")
                add_text(field_label_nodes[0], field_data["label"], f"{label}.fields[{field_index}].label")
                anchors = select(value_nodes[0],selectors["source_link"])
                if set(field_data) == {"label","links"}:
                    if anchors and len(anchors) == len(field_data["links"]):
                        for link_index,(anchor,source) in enumerate(zip(anchors,field_data["links"])):
                            add_link(anchor,source,f"{label}.fields[{field_index}].links[{link_index}]")
                    else:
                        add_link_list(value_nodes[0],field_data["links"],html,edits,used,f"{label}.fields[{field_index}].links")
                elif set(field_data) == {"label","text"}:
                    add_text(value_nodes[0],field_data["text"],f"{label}.fields[{field_index}].text")
                else:
                    raise ValueError(f"{label}.fields[{field_index}]: expected text or links field")


def render_earnings_calendar(html: str, parser: SourceTreeParser,
                             snapshot: dict[str, Any], binding: dict[str, Any],
                             edits: list[tuple[int, int, str]],
                             used: set[tuple[int, int]]) -> None:
    spec = binding.get("groups", {}).get("earnings_calendar")
    data = snapshot.get("earnings_calendar")
    if spec is None or data is None:
        return
    if not isinstance(data, dict) or set(data) != {"panels"} or not isinstance(data["panels"], dict):
        raise ValueError("earnings_calendar snapshot must contain a panels object")
    selectors = spec["selectors"]

    def add_text(node: Node, text: str, label: str):
        spans = coalesce_spans([x for x in spans_inside(node, parser.spans) if x.text.strip()])
        if not spans:
            raise ValueError(f"{label}: text slot is empty")
        # Keep approved inline elements and attributes; update only their text nodes.
        for index, span in enumerate(spans):
            ident = (span.start, span.end)
            if ident in used:
                raise ValueError(f"{label}: overlapping text slot")
            used.add(ident)
            replacement = escape(text, quote=False) if index == 0 else ""
            edits.append((span.start, span.end, replacement))

    def add_href(anchor: Node, source: dict[str, str], label: str):
        if not isinstance(source,dict) or set(source) != {"url","text"}:
            raise ValueError(f"{label}: source must contain url and text")
        url = source["url"]
        if not isinstance(url,str) or not url.startswith("https://") or any(ch in url for ch in ('"', "'", "<", ">")):
            raise ValueError(f"{label}: invalid https URL")
        href = anchor.attr_value_spans.get("href")
        if href is None or href in used:
            raise ValueError(f"{label}: href missing or overlapping")
        used.add(href)
        edits.append((href[0],href[1],escape(url,quote=True)))
        add_text(anchor,source["text"],f"{label}.text")

    def update_status_class(node: Node, new_status: str, label: str):
        allowed = {"beat","miss","pending"}
        if new_status not in allowed:
            raise ValueError(f"{label}: invalid earnings status class")
        old = [token for token in allowed if token in node.classes]
        if len(old) != 1:
            raise ValueError(f"{label}: expected exactly one existing earnings status class")
        if old[0] == new_status:
            return
        span = node.class_value_span
        if span is None:
            raise ValueError(f"{label}: class source span missing")
        raw_class = html[span[0]:span[1]]
        matches = list(re.finditer(r"(?<!\S)"+re.escape(old[0])+r"(?!\S)",raw_class))
        if len(matches) != 1:
            raise ValueError(f"{label}: earnings status class token ambiguous")
        m = matches[0]
        ident = (span[0]+m.start(),span[0]+m.end())
        if ident in used:
            raise ValueError(f"{label}: overlapping status class slot")
        used.add(ident)
        edits.append((ident[0],ident[1],new_status))

    for panel_key,panel_spec in spec["panels"].items():
        containers = select(parser.root,panel_spec["container"])
        panel_data = data["panels"].get(panel_key)
        if not containers:
            if panel_data is not None:
                raise ValueError(f"earnings_calendar.{panel_key}: panel not present in this template")
            continue
        if len(containers) != 1:
            raise ValueError(f"earnings_calendar.{panel_key}: container missing or duplicated")
        if panel_data is None or not isinstance(panel_data,dict) or not (
            set(panel_data) == {"items"} and isinstance(panel_data["items"],list)
            or set(panel_data) == {"lists"} and isinstance(panel_data["lists"],list)
        ):
            raise ValueError(f"earnings_calendar.{panel_key}: invalid or missing panel snapshot")
        if "lists" in panel_data:
            if not isinstance(panel_data["lists"], list):
                raise ValueError(f"earnings_calendar.{panel_key}: lists must be an array")
            groups = select(containers[0], ".calendar-status-group")
            legacy_mode = False
            if len(groups) != len(panel_data["lists"]):
                existing_lists = select(containers[0], panel_spec["list_selector"])
                if len(existing_lists) == len(panel_data["lists"]):
                    legacy_mode = True
                else:
                    raise ValueError(f"earnings_calendar.{panel_key}: status-group count mismatch")
            item_nodes, items = [], []
            for group_index, list_data in enumerate(panel_data["lists"]):
                if not isinstance(list_data, dict) or set(list_data) != {"items"} or not isinstance(list_data["items"], list):
                    raise ValueError(f"earnings_calendar.{panel_key}.lists[{group_index}]: invalid items list")
                group_lists = [existing_lists[group_index]] if legacy_mode else select(groups[group_index], panel_spec["list_selector"])
                if len(group_lists) > 1:
                    raise ValueError(f"earnings_calendar.{panel_key}.lists[{group_index}]: duplicate list container")
                if not group_lists:
                    if list_data["items"]:
                        raise ValueError(f"earnings_calendar.{panel_key}.lists[{group_index}]: populated list container missing after resize")
                    continue
                group_items = select(group_lists[0], panel_spec["item_selector"])
                if len(group_items) != len(list_data["items"]):
                    raise ValueError(f"earnings_calendar.{panel_key}.lists[{group_index}]: accordion count mismatch")
                item_nodes.extend(group_items)
                items.extend(list_data["items"])
        else:
            item_nodes = select(containers[0],panel_spec["item_selector"])
            items = panel_data.get("items", [])
        if len(item_nodes) != len(items):
            raise ValueError(f"earnings_calendar.{panel_key}: accordion count mismatch; template={len(item_nodes)}, snapshot={len(items)}")
        for index,(item_node,item) in enumerate(zip(item_nodes,items)):
            label=f"earnings_calendar.{panel_key}.items[{index}]"
            required={"expected_company","us_date","tw_date","company","company_sub","stars_text","fields","results"}
            if not isinstance(item,dict) or set(item) != required:
                raise ValueError(f"{label}: invalid item fields")
            company_nodes=select(item_node,selectors["company"])
            if len(company_nodes)!=1:
                raise ValueError(f"{label}: company slot missing or duplicated")
            current_company=normalize(unescape("".join(x.text for x in spans_inside(company_nodes[0],parser.spans))))
            if item["expected_company"] not in (None, "") and current_company != normalize(item["expected_company"]):
                raise ValueError(f"{label}: company identity mismatch")
            for field_name in ("us_date","tw_date","company","company_sub"):
                nodes=select(item_node,selectors[field_name])
                if len(nodes)!=1:
                    raise ValueError(f"{label}.{field_name}: slot missing or duplicated")
                add_text(nodes[0],item[field_name],f"{label}.{field_name}")
            star_nodes=select(item_node,selectors["stars"])
            if len(star_nodes)!=1:
                raise ValueError(f"{label}.stars_text: slot missing or duplicated")
            if not isinstance(item["stars_text"],str):
                raise ValueError(f"{label}: stars_text must be text")
            add_text(star_nodes[0],item["stars_text"],f"{label}.stars_text")
            star_count=item["stars_text"].count("★")
            if item["expected_company"] in (None, ""):
                update_optional_class(item_node, {"five-star-earnings"},
                                      "five-star-earnings" if star_count==5 else None,
                                      html, edits, used, f"{label}.star_class")
                update_optional_class(company_nodes[0], {"five-star-company"},
                                      "five-star-company" if star_count==5 else None,
                                      html, edits, used, f"{label}.company_star_class")
            details=select(item_node,selectors["details"])
            if len(details)!=1:
                raise ValueError(f"{label}: details container missing or duplicated")
            detail_fields=select(details[0],selectors["detail_field"])
            if len(detail_fields)!=len(item["fields"]):
                raise ValueError(f"{label}: detail field count mismatch")
            for field_index,(field_node,field_data) in enumerate(zip(detail_fields,item["fields"])):
                labels=select(field_node,selectors["detail_label"])
                values=select(field_node,selectors["detail_value"])
                if len(labels)!=1 or len(values)!=1:
                    raise ValueError(f"{label}.fields[{field_index}]: label/value ambiguous")
                if not isinstance(field_data,dict) or not isinstance(field_data.get("label"),str):
                    raise ValueError(f"{label}.fields[{field_index}]: label must be text")
                add_text(labels[0],field_data["label"],f"{label}.fields[{field_index}].label")
                anchors=select(values[0],"a")
                if set(field_data)=={"label","links"}:
                    if anchors and len(anchors)==len(field_data["links"]):
                        for link_index,(anchor,source) in enumerate(zip(anchors,field_data["links"])):
                            add_href(anchor,source,f"{label}.fields[{field_index}].links[{link_index}]")
                    else:
                        add_link_list(values[0],field_data["links"],html,edits,used,f"{label}.fields[{field_index}].links")
                elif set(field_data)=={"label","text"}:
                    add_text(values[0],field_data["text"],f"{label}.fields[{field_index}].text")
                else:
                    raise ValueError(f"{label}.fields[{field_index}]: expected text or links field")

            result_cards=select(details[0],selectors["result_card"])
            results=item["results"]
            if not isinstance(results,list) or len(result_cards)!=len(results):
                raise ValueError(f"{label}: EPS/revenue result card count mismatch")
            for result_index,(card,result) in enumerate(zip(result_cards,results)):
                result_label=f"{label}.results[{result_index}]"
                if not isinstance(result,dict) or set(result)!={"title","actual","expected","status_text","card_class","status_class","note"}:
                    raise ValueError(f"{result_label}: invalid result fields")
                title_nodes=select(card,selectors["result_title"])
                lines=select(card,selectors["result_line"])
                status_nodes=select(card,selectors["result_status"])
                note_nodes=select(card,selectors["result_note"])
                if len(title_nodes)!=1 or len(lines)!=2 or len(status_nodes)!=1 or len(note_nodes)!=1:
                    raise ValueError(f"{result_label}: result card slots ambiguous")
                add_text(title_nodes[0],result["title"],f"{result_label}.title")
                for line_index,expected_label,field_name in ((0,"實際","actual"),(1,"預期","expected")):
                    line_labels=[n for n in descendants(lines[line_index]) if n.tag=="span"]
                    strong=select(lines[line_index],"strong")
                    if len(line_labels)!=1 or len(strong)!=1:
                        raise ValueError(f"{result_label}.{field_name}: actual/expected slot ambiguous")
                    label_text=normalize(unescape("".join(x.text for x in spans_inside(line_labels[0],parser.spans))))
                    if label_text!=expected_label:
                        raise ValueError(f"{result_label}.{field_name}: label mismatch")
                    add_text(strong[0],result[field_name],f"{result_label}.{field_name}")
                add_text(status_nodes[0],result["status_text"],f"{result_label}.status_text")
                add_text(note_nodes[0],result["note"],f"{result_label}.note")
                update_status_class(card,result["card_class"],f"{result_label}.card")
                update_status_class(status_nodes[0],result["status_class"],f"{result_label}.status")

def create_empty_status_list(source: str, parser: SourceTreeParser,
                               container: Node, group: Node, list_selector: str,
                               card_selector: str, empty_state_selector: str,
                               desired_count: int, label: str) -> str:
    """Replace one approved empty-state node with a list cloned from a sibling prototype."""
    if desired_count <= 0:
        return source
    existing = select(group, list_selector)
    placeholders = select(group, empty_state_selector)
    if existing or len(placeholders) != 1:
        raise ValueError(f"{label}: expected one empty-state placeholder and no list")
    prototype_lists = [node for node in select(container, list_selector) if node.parent is not group]
    if len(prototype_lists) < 1:
        raise ValueError(f"{label}: no sibling approved list-container prototype")
    prototype_list = prototype_lists[0]
    prototype_cards = select(prototype_list, card_selector)
    if not prototype_cards:
        raise ValueError(f"{label}: approved list prototype has no card")
    card = prototype_cards[0]
    if card.parent is not prototype_list:
        raise ValueError(f"{label}: card prototype is not a direct child of its list")
    if any(value is None for value in (prototype_list.source_start, prototype_list.start_tag_end,
                                       prototype_list.end_tag_start, prototype_list.end_tag_end,
                                       card.source_start, card.end_tag_end,
                                       placeholders[0].source_start, placeholders[0].end_tag_end)):
        raise ValueError(f"{label}: source boundaries unavailable; refusing to create list")
    open_tag = source[prototype_list.source_start:prototype_list.start_tag_end]
    close_tag = source[prototype_list.end_tag_start:prototype_list.end_tag_end]
    card_markup = source[card.source_start:card.end_tag_end]
    if not open_tag.startswith("<div") or not close_tag.startswith("</div") or not card_markup:
        raise ValueError(f"{label}: prototype source markup is not a safe div/card sequence")
    rendered_cards = "\\n".join(card_markup for _ in range(desired_count))
    replacement = open_tag + "\\n" + rendered_cards + "\\n" + close_tag
    placeholder = placeholders[0]
    start, end = placeholder.source_start, placeholder.end_tag_end
    return source[:start] + replacement + source[end:]


def resize_calendar_lists(html: str, binding: dict[str, Any], snapshot: dict[str, Any]) -> str:
    """Resize mapped card runs; create a missing list only by replacing its approved empty state."""
    for group_name in ("economic_calendar", "earnings_calendar"):
        spec = binding.get("groups", {}).get(group_name)
        data = snapshot.get(group_name)
        if spec is None or data is None:
            continue
        if not isinstance(data, dict) or not isinstance(data.get("panels"), dict):
            raise ValueError(f"{group_name}: panels object required for dynamic lists")
        for panel_key, panel_spec in spec.get("panels", {}).items():
            panel_data = data["panels"].get(panel_key)
            if panel_data is None:
                continue
            lists_data = panel_data.get("lists") if isinstance(panel_data, dict) else None
            if not isinstance(lists_data, list):
                continue
            parser = SourceTreeParser(html)
            parser.feed(html)
            parser.close()
            containers = select(parser.root, panel_spec["container"])
            if len(containers) != 1:
                raise ValueError(f"{group_name}.{panel_key}: panel container missing or duplicated")
            container = containers[0]
            groups = select(container, ".calendar-status-group")
            legacy_mode = False
            if len(groups) != len(lists_data):
                existing_lists = select(container, panel_spec["list_selector"])
                if len(existing_lists) == len(lists_data):
                    legacy_mode = True
                    group_entries = [(None, node) for node in existing_lists]
                else:
                    raise ValueError(f"{group_name}.{panel_key}: status-group count mismatch; template={len(groups)}, snapshot={len(lists_data)}")
            else:
                group_entries = [(group, (select(group, panel_spec["list_selector"]) or [None])[0])
                                 for group in groups]
            item_selector = panel_spec.get("event_selector", panel_spec.get("item_selector"))
            for list_index, ((group, list_node), list_data) in enumerate(zip(group_entries, lists_data)):
                if legacy_mode:
                    group = status_group_for(list_node)
                else:
                    parser = SourceTreeParser(html)
                    parser.feed(html)
                    parser.close()
                    containers = select(parser.root, panel_spec["container"])
                    container = containers[0]
                    groups = select(container, ".calendar-status-group")
                    group = groups[list_index]
                    group_lists = select(group, panel_spec["list_selector"])
                    list_node = group_lists[0] if group_lists else None
                if not isinstance(list_data, dict) or set(list_data) != {"items"} or not isinstance(list_data["items"], list):
                    raise ValueError(f"{group_name}.{panel_key}.lists[{list_index}]: invalid list payload")
                group_lists = [list_node] if legacy_mode else select(group, panel_spec["list_selector"])
                if len(group_lists) > 1:
                    raise ValueError(f"{group_name}.{panel_key}.lists[{list_index}]: duplicate list containers")
                if not group_lists:
                    if list_data["items"] and not legacy_mode:
                        html = create_empty_status_list(html, parser, container, group,
                                                        panel_spec["list_selector"], item_selector,
                                                        panel_spec.get("empty_state_selector", ".calendar-status-empty"),
                                                        len(list_data["items"]),
                                                        f"{group_name}.{panel_key}.lists[{list_index}]")
                        parser = SourceTreeParser(html)
                        parser.feed(html)
                        parser.close()
                        containers = select(parser.root, panel_spec["container"])
                        container = containers[0]
                        groups = select(container, ".calendar-status-group")
                        group = groups[list_index]
                        group_lists = select(group, panel_spec["list_selector"])
                    else:
                        # Keep the original empty-state message byte-for-byte.
                        continue
                if len(group_lists) != 1:
                    raise ValueError(f"{group_name}.{panel_key}.lists[{list_index}]: list creation failed")
                list_node = group_lists[0]
                parser = SourceTreeParser(html)
                parser.feed(html)
                parser.close()
                containers = select(parser.root, panel_spec["container"])
                if legacy_mode:
                    group_lists = select(containers[0], panel_spec["list_selector"])
                    group_lists = [group_lists[list_index]]
                else:
                    groups = select(containers[0], ".calendar-status-group")
                    group_lists = select(groups[list_index], panel_spec["list_selector"])
                cards = select(group_lists[0], item_selector)
                if len(cards) != len(list_data["items"]):
                    html = replace_sibling_sequence(html, parser, cards, len(list_data["items"]),
                                                    f"{group_name}.{panel_key}.lists[{list_index}]")
                # Resize nested detail rows only inside the card prototypes.
                for item_index, item_data in enumerate(list_data["items"]):
                    parser = SourceTreeParser(html)
                    parser.feed(html)
                    parser.close()
                    containers = select(parser.root, panel_spec["container"])
                    if legacy_mode:
                        group_lists = select(containers[0], panel_spec["list_selector"])
                        group_lists = [group_lists[list_index]]
                    else:
                        groups = select(containers[0], ".calendar-status-group")
                        group_lists = select(groups[list_index], panel_spec["list_selector"])
                    cards_now = select(group_lists[0], item_selector)
                    if item_index >= len(cards_now) or not isinstance(item_data, dict) or not isinstance(item_data.get("fields"), list):
                        raise ValueError(f"{group_name}.{panel_key}.lists[{list_index}].items[{item_index}]: fields array required")
                    detail_nodes = select(cards_now[item_index], spec["selectors"]["details"])
                    if len(detail_nodes) != 1:
                        raise ValueError(f"{group_name}.{panel_key}.lists[{list_index}].items[{item_index}]: details container missing or duplicated")
                    field_selector = spec["selectors"]["field"] if group_name == "economic_calendar" else spec["selectors"]["detail_field"]
                    fields_now = select(detail_nodes[0], field_selector)
                    if len(fields_now) != len(item_data["fields"]):
                        html = replace_sibling_sequence(html, parser, fields_now, len(item_data["fields"]),
                                                        f"{group_name}.{panel_key}.lists[{list_index}].items[{item_index}].fields")
    return html

def render_market_html(html: str, snapshot: dict[str, Any], binding: dict[str, Any]) -> str:
    if not isinstance(snapshot, dict):
        raise ValueError("snapshot must be an object")
    # Schema and assembler define market groups at the snapshot root.
    # Accept the former nested shape temporarily for isolated legacy fixtures.
    market_groups = snapshot.get("groups", snapshot)
    if not isinstance(market_groups, dict):
        raise ValueError("snapshot market groups must be an object")
    # Calendar event cards may change count only inside mapped status-list containers.
    html = resize_calendar_lists(html, binding, snapshot)
    # Resize only explicitly mapped news-card sibling runs, preserving panel
    # metadata and warning elements outside each card sequence.
    news_spec = binding.get("groups", {}).get("news")
    news_data = snapshot.get("news")
    if news_spec is not None and isinstance(news_data, dict):
        pre_parser = SourceTreeParser(html)
        pre_parser.feed(html)
        pre_parser.close()
        for panel_key, panel_spec in news_spec.get("panels", {}).items():
            panel_data = news_data.get(panel_key)
            if not isinstance(panel_data, dict) or not isinstance(panel_data.get("items"), list):
                continue
            containers = select(pre_parser.root, panel_spec["container"])
            if len(containers) != 1:
                raise ValueError(f"news.{panel_key}: container missing or duplicated during dynamic resize")
            cards = select(containers[0], panel_spec["item_selector"])
            if len(cards) != len(panel_data["items"]):
                html = replace_sibling_sequence(html, pre_parser, cards, len(panel_data["items"]), f"news.{panel_key}")
                pre_parser = SourceTreeParser(html)
                pre_parser.feed(html)
                pre_parser.close()

    parser = SourceTreeParser(html)
    parser.feed(html)
    parser.close()
    edits: list[tuple[int, int, str]] = []
    used: set[tuple[int, int]] = set()

    for group_name, spec in binding["groups"].items():
        if group_name not in {"global_indices", "sectors", "bonds", "fx", "energy", "precious_metals"}:
            continue
        group_data = market_groups.get(group_name)
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
                old_tokens = [c for c in ("up", "down", "flat", "warn") if c in change_node.classes]
                new_direction = direction(change_text, binding.get("rules", {}))
                if new_direction is not None and change_span.text != change_text:
                    if len(old_tokens) != 1:
                        raise ValueError(
                            f"{group_name}.{key}: expected exactly one existing status class token, found {old_tokens}"
                        )
                    old_direction = old_tokens[0]
                    if new_direction != old_direction:
                        if not binding.get("rules", {}).get("allow_mapped_status_class_token_transition", False):
                            raise ValueError(f"{group_name}.{key}: status class transition is not authorized")
                        if change_node.class_value_span is None:
                            raise ValueError(f"{group_name}.{key}: class attribute source span is missing")
                        class_start, class_end = change_node.class_value_span
                        raw_class = html[class_start:class_end]
                        token_matches = list(re.finditer(r"(?<!\S)" + re.escape(old_direction) + r"(?!\S)", raw_class))
                        if len(token_matches) != 1:
                            raise ValueError(f"{group_name}.{key}: status class token is not unique in source")
                        token = token_matches[0]
                        edits.append((class_start + token.start(), class_start + token.end(), new_direction))
                targets.append((change_span, change_text, change_node, "change"))

            for span, value, _node, slot_name in targets:
                identity = (span.start, span.end)
                if identity in used:
                    raise ValueError(f"overlapping text target at {group_name}.{key}.{slot_name}")
                used.add(identity)
                edits.append((span.start, span.end, escape(value, quote=False)))

    render_risk_indicators(html, parser, snapshot, binding, edits, used)
    render_fedwatch(html, parser, snapshot, binding, edits, used)
    render_editorial(html, parser, snapshot, binding, edits, used)
    render_news(html, parser, snapshot, binding, edits, used)
    render_economic_calendar(html, parser, snapshot, binding, edits, used)
    render_earnings_calendar(html, parser, snapshot, binding, edits, used)

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
    print(f"PASS: wrote {output.relative_to(ROOT)}; mapped slots and approved dynamic lists updated; protected outer structure retained")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
