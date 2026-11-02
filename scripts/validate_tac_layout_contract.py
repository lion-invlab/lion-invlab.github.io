#!/usr/bin/env python3
"""Fail-closed DOM layout contract for TAC daily previews.

Text and market values may change. Element hierarchy, layout classes, IDs,
inline layout styles and interaction-control attributes must remain aligned
with the approved weekday-specific master. Repeated identical sibling cards
may be added/removed without changing their component schema.
"""
from __future__ import annotations
import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

VOID = {"area","base","br","col","embed","hr","img","input","link","meta",
        "param","source","track","wbr"}
STATE_CLASSES = {"up","down","flat","warn","active","selected","open","closed",
                 "published","upcoming","today","is-active","is-open",
                 "beat","miss","pending","five-star","five-star-earnings","five-star-company"}
DYNAMIC_LIST_CLASSES = {"econ-event-list", "earnings-accordion-list"}
KEEP_ATTRS = {"id","style","type","name","role","aria-controls","aria-labelledby",
              "aria-expanded","aria-selected","aria-hidden"}

class Node:
    def __init__(self, tag, attrs):
        self.tag = tag
        self.attrs = tuple(sorted(self._attrs(tag, attrs)))
        self.children = []
    @staticmethod
    def _attrs(tag, attrs):
        result = []
        class_tokens = set()
        for key, value in attrs:
            if key.lower() == "class":
                class_tokens = set((value or "").split())
                break
        for key, value in attrs:
            key = key.lower()
            if key == "class":
                tokens = [x for x in (value or "").split() if x not in STATE_CLASSES]
                result.append(("class", " ".join(sorted(tokens))))
            elif key in KEEP_ATTRS:
                normalized = value or ""
                if key == "style" and tag == "div":
                    # Only explicitly allowlisted chart properties are data slots.
                    dynamic_properties = set()
                    if "fg6-marker" in class_tokens:
                        dynamic_properties.add("left")
                    if {"fc-split-hold", "fc-split-hike"} & class_tokens:
                        dynamic_properties.add("width")
                    for prop in dynamic_properties:
                        normalized = re.sub(
                            rf"(?i)(^|;)(\s*{re.escape(prop)}\s*:\s*)[^;]+",
                            r"\1\2<DATA>",
                            normalized,
                        )
                result.append((key, normalized))
        return result
    @property
    def class_tokens(self):
        value = dict(self.attrs).get("class", "")
        return set(value.split())

    def signature(self):
        # Event lists are data slots: they may be empty or contain any number
        # of cards. Their contents are validated separately against approved
        # card prototypes, so an empty-to-populated transition is safe.
        if self.class_tokens & DYNAMIC_LIST_CLASSES or "calendar-status-empty" in self.class_tokens:
            # An empty-state placeholder occupies the same slot as a populated
            # event list; card internals are still checked against master prototypes.
            return ("div", (("class", "__dynamic_calendar_list__"),), ())
        child_sigs = []
        for child in self.children:
            sig = child.signature()
            # Repeated identical cards/rows are data-driven; their schema is
            # checked once, while their order relative to other components stays fixed.
            if not child_sigs or child_sigs[-1] != sig:
                child_sigs.append(sig)
        return (self.tag, self.attrs, tuple(child_sigs))

class TreeParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("__root__", [])
        self.stack = [self.root]
    def handle_starttag(self, tag, attrs):
        node = Node(tag.lower(), attrs)
        self.stack[-1].children.append(node)
        if tag.lower() not in VOID:
            self.stack.append(node)
    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag.lower(), attrs))
    def handle_endtag(self, tag):
        tag = tag.lower()
        for index in range(len(self.stack)-1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

def parse_tree(path: Path):
    parser = TreeParser()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    return parser.root

def signature(path: Path):
    return parse_tree(path).signature()

def walk(node):
    yield node
    for child in node.children:
        yield from walk(child)

def card_kind(node):
    classes = node.class_tokens
    if node.tag == "details" and "econ-event" in classes:
        return "economic"
    if node.tag == "details" and "earnings-accordion" in classes:
        return "earnings"
    return None

def validate_dynamic_lists(master_root, report_root):
    prototypes = {"economic": set(), "earnings": set()}
    for node in walk(master_root):
        kind = card_kind(node)
        if kind:
            prototypes[kind].add(node.signature())

    errors = []
    for node in walk(report_root):
        classes = node.class_tokens
        if "econ-event-list" in classes:
            expected = "economic"
        elif "earnings-accordion-list" in classes:
            expected = "earnings"
        else:
            continue
        if not node.children:
            errors.append(f"{expected} dynamic list is missing cards and an explicit empty-state placeholder")
            continue
        for index, child in enumerate(node.children):
            if card_kind(child) != expected:
                if child.tag == "div" and "calendar-status-empty" in child.class_tokens:
                    continue
                errors.append(
                    f"{expected} dynamic list contains unexpected child "
                    f"{child.tag} classes={sorted(child.class_tokens)}"
                )
                continue
            if child.signature() not in prototypes[expected]:
                errors.append(
                    f"{expected} card schema differs from every approved-master prototype "
                    f"(list child {index})"
                )
    return errors

def first_difference(left, right, path='root'):
    if left[0] != right[0]:
        return f"{path}: tag {left[0]!r} != {right[0]!r}"
    if left[1] != right[1]:
        return f"{path}/{left[0]}: protected attributes differ: {left[1]!r} != {right[1]!r}"
    if len(left[2]) != len(right[2]):
        return f"{path}/{left[0]}: child component count differs ({len(left[2])} != {len(right[2])})"
    for index, pair in enumerate(zip(left[2], right[2])):
        result = first_difference(pair[0], pair[1], f"{path}/{left[0]}[{index}]")
        if result:
            return result
    return None

def self_test():
    import tempfile
    with tempfile.TemporaryDirectory() as directory:
        a = Path(directory) / "master.html"
        b = Path(directory) / "report.html"
        a.write_text('<html><body><main class="wrap"><article class="card"><b>old</b></article></main></body></html>', encoding="utf-8")
        b.write_text('<html><body><main class="wrap"><article class="card"><b>new</b></article><article class="card"><b>newer</b></article></main></body></html>', encoding="utf-8")
        assert signature(a) == signature(b), "text changes and repeated card count should pass"
        b.write_text('<html><body><main class="wrap"><section class="card"><b>new</b></section></main></body></html>', encoding="utf-8")
        assert signature(a) != signature(b), "tag/layout mutation must fail"
        b.write_text('<html><body><main class="wrap" style="display:none"><article class="card"><b>new</b></article></main></body></html>', encoding="utf-8")
        assert signature(a) != signature(b), "inline layout style mutation must fail"
        a.write_text('<html><body><div class="fg6-marker" style="left:20.98%"></div></body></html>', encoding="utf-8")
        b.write_text('<html><body><div class="fg6-marker" style="left:26%"></div></body></html>', encoding="utf-8")
        assert signature(a) == signature(b), "data-driven Fear & Greed marker position should pass"
        b.write_text('<html><body><div class="fg6-marker" style="left:26%;top:1px"></div></body></html>', encoding="utf-8")
        assert signature(a) != signature(b), "non-data marker style mutation must still fail"
        a.write_text('<html><body><div class="fc-split-hold" style="width:90%"></div></body></html>', encoding="utf-8")
        b.write_text('<html><body><div class="fc-split-hold" style="width:30.2%"></div></body></html>', encoding="utf-8")
        assert signature(a) == signature(b), "FedWatch probability bar width should be data-driven"
        b.write_text('<html><body><div class="fc-split-hold" style="width:30.2%;background:red"></div></body></html>', encoding="utf-8")
        assert signature(a) != signature(b), "non-data FedWatch bar style mutation must still fail"
        a.write_text('<html><body><div class="fc-split-hike" style="width:10%"></div></body></html>', encoding="utf-8")
        b.write_text('<html><body><div class="fc-split-hike" style="width:69.8%"></div></body></html>', encoding="utf-8")
        assert signature(a) == signature(b), "FedWatch hike bar width should be data-driven"
        a.write_text('<html><body><div class="earnings-actual-card beat"><b class="earnings-actual-status beat">Beat</b></div><div class="earnings-actual-card pending"><b class="earnings-actual-status pending">Pending</b></div></body></html>', encoding="utf-8")
        b.write_text('<html><body><div class="earnings-actual-card miss"><b class="earnings-actual-status miss">Miss</b></div><div class="earnings-actual-card beat"><b class="earnings-actual-status beat">Beat</b></div><div class="earnings-actual-card pending"><b class="earnings-actual-status pending">Pending</b></div></body></html>', encoding="utf-8")
        assert signature(a) == signature(b), "earnings outcome states and repeated results should be data-driven"
        a.write_text('<html><body><div class="earnings-accordion-list"><div class="calendar-status-empty">Empty</div></div><div class="earnings-accordion-list"><details class="earnings-accordion"><summary><span>Prototype</span></summary></details></div></body></html>', encoding="utf-8")
        b.write_text('<html><body><div class="earnings-accordion-list"><details class="earnings-accordion"><summary><span>Today</span></summary></details></div><div class="earnings-accordion-list"><details class="earnings-accordion"><summary><span>One</span></summary></details><details class="earnings-accordion"><summary><span>Two</span></summary></details></div></body></html>', encoding="utf-8")
        master_tree, report_tree = parse_tree(a), parse_tree(b)
        assert master_tree.signature() == report_tree.signature(), "dynamic list empty-to-populated transition should be accepted"
        assert not validate_dynamic_lists(master_tree, report_tree), "dynamic cards must match a master prototype"
        b.write_text('<html><body><div class="earnings-accordion-list"><details class="earnings-accordion"><summary><span>Today</span><i>Unexpected</i></summary></details></div><div class="earnings-accordion-list"><details class="earnings-accordion"><summary><span>One</span></summary></details></div></body></html>', encoding="utf-8")
        assert validate_dynamic_lists(master_tree, parse_tree(b)), "mutated dynamic card schema must be rejected"
    print("PASS: text-only update and repeated cards accepted")
    print("PASS: DOM element mutation rejected")
    print("PASS: inline layout-style mutation rejected")
    print("PASS: dynamic Fear & Greed marker position accepted")
    print("PASS: other Fear & Greed marker styles remain protected")
    print("PASS: dynamic FedWatch probability bar widths accepted")
    print("PASS: other FedWatch bar styles remain protected")
    print("PASS: dynamic event lists accept empty-to-populated and variable card counts")
    print("PASS: dynamic event card schema mutations are rejected")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--master")
    parser.add_argument("--report")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.master or not args.report:
        parser.error("--master and --report are required unless --self-test is used")
    master, report = Path(args.master), Path(args.report)
    if not master.is_file() or not report.is_file():
        print("FAIL: master or report file is missing", file=sys.stderr)
        return 2
    master_tree = parse_tree(master)
    report_tree = parse_tree(report)
    master_sig = master_tree.signature()
    report_sig = report_tree.signature()
    if master_sig != report_sig:
        print("FAIL: report DOM layout contract differs from approved master", file=sys.stderr)
        print(first_difference(master_sig, report_sig) or "DOM signatures differ", file=sys.stderr)
        print("Protected: element hierarchy, IDs, layout classes, inline styles and interaction controls.")
        print("Allowed: text/value changes and repeated identical sibling components.")
        return 1
    dynamic_errors = validate_dynamic_lists(master_tree, report_tree)
    if dynamic_errors:
        print("FAIL: dynamic calendar card contract failed", file=sys.stderr)
        for error in dynamic_errors:
            print(" - " + error, file=sys.stderr)
        return 1
    print("PASS: report DOM layout contract matches approved master")
    print("PASS: all dynamic calendar cards match approved-master prototypes")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
