#!/usr/bin/env python3
"""Browser-normalized structural fingerprint for TAC development templates.

Daily text, href/src/value payloads are excluded. DOM hierarchy, IDs, classes,
interaction attributes and inline CSS/JS hashes are retained. HTML5 parsing is
used so the fingerprint follows browser tree-repair rules instead of treating
HTMLParser stack heuristics as authoritative.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import html5lib

STABLE_ATTRS = {
    "type", "name", "role", "for", "tabindex", "disabled", "multiple",
    "required", "open", "aria-controls", "aria-expanded", "aria-label",
    "aria-hidden", "aria-selected", "data-template-note",
}

class Node:
    def __init__(self, tag: str, attrs=None, raw_text=""):
        self.tag = tag
        self.attrs = dict(attrs or {})
        self.children = []
        self.raw_text = raw_text or ""

def local_name(tag):
    if not isinstance(tag, str):
        return None
    return tag.rsplit("}", 1)[-1].lower()

def from_element(element):
    tag = local_name(element.tag)
    if tag is None:
        return None
    node = Node(tag, element.attrib, element.text if tag in {"style", "script"} else "")
    for child in list(element):
        converted = from_element(child)
        if converted is not None:
            node.children.append(converted)
    return node

def walk(node):
    yield node
    for child in node.children:
        yield from walk(child)

def node_signature(node):
    attrs = node.attrs
    return {
        "tag": node.tag,
        "id": attrs.get("id", ""),
        "classes": sorted((attrs.get("class") or "").split()),
        "stable_attrs": sorted(
            (key, attrs[key]) for key in STABLE_ATTRS if key in attrs
        ),
        "children": [node_signature(child) for child in node.children],
    }

def inspect_html(source: str, label: str = "<memory>"):
    parser = html5lib.HTMLParser(
        tree=html5lib.getTreeBuilder("etree"),
        namespaceHTMLElements=False,
        strict=False,
    )
    document = parser.parse(source)
    root = from_element(document)
    if root is None:
        raise ValueError(f"HTML5 parser returned no document root for {label}")

    nodes = list(walk(root))
    ids = [n.attrs["id"] for n in nodes if n.attrs.get("id")]
    counts = Counter(ids)
    duplicates = sorted(value for value, count in counts.items() if count > 1)
    assets = []
    for node in nodes:
        if node.tag in {"style", "script"}:
            assets.append({
                "tag": node.tag,
                "id": node.attrs.get("id", ""),
                "sha256": hashlib.sha256(
                    node.raw_text.encode("utf-8")
                ).hexdigest(),
            })
    parse_errors = [
        {"line": position[0], "column": position[1], "code": code}
        for position, code, _data in parser.errors
    ]
    return {
        "path": label,
        "node_count": len(nodes) - 1,
        "duplicate_ids": duplicates,
        "html5_parse_error_count": len(parse_errors),
        "html5_parse_errors_sample": parse_errors[:30],
        "inline_assets": assets,
        "structure": node_signature(root),
    }

def inspect(path: str):
    return inspect_html(Path(path).read_text(encoding="utf-8"), path)

def compare(base, candidate):
    checks = {
        "fixed_dom_structure_equal": base["structure"] == candidate["structure"],
        "inline_css_js_equal": base["inline_assets"] == candidate["inline_assets"],
        "duplicate_id_set_equal": base["duplicate_ids"] == candidate["duplicate_ids"],
        "baseline_html5_dom_built": base["node_count"] > 0,
        "candidate_html5_dom_built": candidate["node_count"] > 0,
    }
    return {
        "baseline": {k: v for k, v in base.items() if k != "structure"},
        "candidate": {k: v for k, v in candidate.items() if k != "structure"},
        "checks": checks,
        "pass": all(checks.values()),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--report")
    args = ap.parse_args()
    result = compare(inspect(args.baseline), inspect(args.candidate))
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        Path(args.report).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    raise SystemExit(0 if result["pass"] else 1)

if __name__ == "__main__":
    main()
