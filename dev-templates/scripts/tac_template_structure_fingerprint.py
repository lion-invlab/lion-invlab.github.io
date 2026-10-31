#!/usr/bin/env python3
"""Fail-closed structural fingerprint for TAC development templates.

Daily text and href/src/value payloads are excluded. DOM hierarchy, IDs,
classes, interaction attributes and inline CSS/JS hashes are retained.
This is a structural gate only; browser/visual regression remains mandatory.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}
STABLE_ATTRS = {
    "type", "name", "role", "for", "tabindex", "disabled", "multiple",
    "required", "open", "aria-controls", "aria-expanded", "aria-label",
    "aria-hidden", "aria-selected", "data-template-note",
}

class Node:
    def __init__(self, tag: str, attrs=None):
        self.tag = tag
        self.attrs = dict(attrs or [])
        self.children = []
        self.raw_text = ""

class TACParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#document")
        self.stack = [self.root]
        self.warnings = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag.lower(), attrs))

    def handle_endtag(self, tag):
        tag = tag.lower()
        if len(self.stack) == 1:
            self.warnings.append(f"unexpected closing tag: </{tag}>")
            return
        if self.stack[-1].tag == tag:
            self.stack.pop()
            return
        open_tags = [n.tag for n in self.stack[1:]]
        if tag not in open_tags:
            self.warnings.append(f"unexpected closing tag: </{tag}>")
            return
        self.warnings.append(
            f"misnested closing tag </{tag}> while <{self.stack[-1].tag}> is open"
        )
        while len(self.stack) > 1:
            current = self.stack.pop()
            if current.tag == tag:
                break

    def handle_data(self, data):
        if self.stack[-1].tag in {"style", "script"}:
            self.stack[-1].raw_text += data

    def finish(self):
        self.close()
        if len(self.stack) > 1:
            self.warnings.append(
                "unclosed tags: " + ", ".join(n.tag for n in self.stack[1:])
            )

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
    parser = TACParser()
    parser.feed(source)
    parser.finish()
    nodes = list(walk(parser.root))
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
    return {
        "path": label,
        "node_count": sum(n.tag != "#document" for n in nodes),
        "duplicate_ids": duplicates,
        "parse_warnings": parser.warnings,
        "inline_assets": assets,
        "structure": node_signature(parser.root),
    }

def inspect(path: str):
    return inspect_html(Path(path).read_text(encoding="utf-8"), path)

def compare(base, candidate):
    checks = {
        "fixed_dom_structure_equal": base["structure"] == candidate["structure"],
        "inline_css_js_equal": base["inline_assets"] == candidate["inline_assets"],
        "duplicate_id_set_equal": base["duplicate_ids"] == candidate["duplicate_ids"],
        "baseline_has_no_parse_warnings": not base["parse_warnings"],
        "candidate_has_no_parse_warnings": not candidate["parse_warnings"],
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
