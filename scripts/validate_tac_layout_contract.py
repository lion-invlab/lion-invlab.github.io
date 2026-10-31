#!/usr/bin/env python3
"""Fail-closed DOM layout contract for TAC daily previews.

Text and market values may change. Element hierarchy, layout classes, IDs,
inline layout styles and interaction-control attributes must remain aligned
with the approved weekday-specific master. Repeated identical sibling cards
may be added/removed without changing their component schema.
"""
from __future__ import annotations
import argparse
import sys
from html.parser import HTMLParser
from pathlib import Path

VOID = {"area","base","br","col","embed","hr","img","input","link","meta",
        "param","source","track","wbr"}
STATE_CLASSES = {"up","down","flat","warn","active","selected","open","closed",
                 "published","upcoming","today","is-active","is-open"}
KEEP_ATTRS = {"id","style","type","name","role","aria-controls","aria-labelledby",
              "aria-expanded","aria-selected","aria-hidden"}

class Node:
    def __init__(self, tag, attrs):
        self.tag = tag
        self.attrs = tuple(sorted(self._attrs(attrs)))
        self.children = []
    @staticmethod
    def _attrs(attrs):
        result = []
        for key, value in attrs:
            key = key.lower()
            if key == "class":
                tokens = [x for x in (value or "").split() if x not in STATE_CLASSES]
                result.append(("class", " ".join(sorted(tokens))))
            elif key in KEEP_ATTRS:
                result.append((key, value or ""))
        return result
    def signature(self):
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

def signature(path: Path):
    parser = TreeParser()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    return parser.root.signature()

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
    print("PASS: text-only update and repeated cards accepted")
    print("PASS: DOM element mutation rejected")
    print("PASS: inline layout-style mutation rejected")

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
    if signature(master) != signature(report):
        print("FAIL: report DOM layout contract differs from approved master", file=sys.stderr)
        print("Protected: element hierarchy, IDs, layout classes, inline styles and interaction controls.")
        print("Allowed: text/value changes and repeated identical sibling components.")
        return 1
    print("PASS: report DOM layout contract matches approved master")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
