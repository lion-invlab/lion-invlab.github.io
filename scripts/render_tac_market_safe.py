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
    class_value_span: tuple[int, int] | None = None
    attr_value_spans: dict[str, tuple[int, int]] = field(default_factory=dict)

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
        class_match = re.search(r"""\bclass\s*=\s*(["'])(.*?)\1""", raw_tag, re.I | re.S)
        if class_match:
            node.class_value_span = (start + class_match.start(2), start + class_match.end(2))
        for attr_name in ("style", "aria-label"):
            attr_match = re.search(r"""\b""" + re.escape(attr_name) + r"""\s*=\s*(["'])(.*?)\1""", raw_tag, re.I | re.S)
            if attr_match:
                node.attr_value_spans[attr_name] = (start + attr_match.start(2), start + attr_match.end(2))
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
    required = {"probabilities", "target_meeting", "updated_at", "target_rate_range", "audit_text"}
    if not isinstance(data, dict) or set(data) != required:
        raise ValueError("fedwatch snapshot must contain probabilities, target_meeting, updated_at, target_rate_range, audit_text")
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
        parsed[key] = (float(p), f"{p:.1f}%", item["rate_range"])
    total = sum(x[0] for x in parsed.values())
    if abs(total - 100.0) > 0.11:
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
        if ident in used:
            raise ValueError(f"fedwatch.{key}: overlapping width slot")
        used.add(ident)
        edits.append((ident[0], ident[1], f"width:{p:.1f}%"))

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
    aria = f"維持利率 {parsed['hold'][1]}，升息一碼 {parsed['hike_one'][1]}；CME FedWatch 快照時間 {data['updated_at']}"
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
