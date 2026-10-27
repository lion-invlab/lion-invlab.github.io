#!/usr/bin/env python3
"""Fail-fast structural regression checks for TAC daily HTML reports.

This deliberately checks structural invariants, not whether market data is correct
or whether a human-visible layout is aesthetically acceptable. Browser tests are
a separate gate.
"""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "demo-2026-10-26.html"
DATE_RE = re.compile(r"^2026-\d{2}-\d{2}\.html$")

# Stable template anchors and controls that must survive every daily copy.
REQUIRED_IDS = {
    "news-scan",
    "global-markets",
    "industry-bonds-fx-commodities",
    "last-week-calendar",
    "last-week-earnings",
    "calendar",
    "earnings",
    "sp500-earnings-health",
    "fed",
    "view",
    "tac-news-0",
    "tac-global-0",
    "tac-assets-0",
    "week-econ-today",
    "week-earnings-today",
    "focus-tab-core",
}

class AuditParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.tags = {}
        self.tab_inputs = 0
        self.details = 0
        self.styles = 0
        self.scripts = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags[tag] = self.tags.get(tag, 0) + 1
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "input" and "tac-tab-radio" in attrs.get("class", "").split():
            self.tab_inputs += 1
        if tag == "details":
            self.details += 1
        if tag == "style":
            self.styles += 1
        if tag == "script":
            self.scripts += 1

def inspect(path: Path, master_ids: set[str]) -> list[str]:
    errors = []
    source = path.read_text(encoding="utf-8")
    parser = AuditParser()
    try:
        parser.feed(source)
        parser.close()
    except Exception as exc:
        return [f"HTML parser error: {exc}"]

    duplicate_ids = sorted({x for x in parser.ids if parser.ids.count(x) > 1})
    if duplicate_ids:
        errors.append("duplicate IDs: " + ", ".join(duplicate_ids[:20]))

    missing = sorted(REQUIRED_IDS - set(parser.ids))
    if missing:
        errors.append("missing required template anchors/controls: " + ", ".join(missing))

    missing_from_master = sorted((REQUIRED_IDS & master_ids) - set(parser.ids))
    if missing_from_master:
        errors.append("master regression: " + ", ".join(missing_from_master))

    for tag in ("html", "head", "body"):
        if parser.tags.get(tag, 0) != 1:
            errors.append(f"expected exactly one <{tag}>; found {parser.tags.get(tag, 0)}")
    if parser.styles < 1:
        errors.append("no inline style block found")
    if parser.scripts < 1:
        errors.append("no script block found")
    if parser.tab_inputs < 3:
        errors.append(f"too few TAC tab controls: {parser.tab_inputs}")
    if "</html>" not in source.lower():
        errors.append("missing closing </html>")

    title_match = re.search(r"<title[^>]*>(.*?)</title>", source, re.I | re.S)
    if not title_match or "TAC 投資早報" not in title_match.group(1):
        errors.append("missing TAC report title")
    if path.stem not in source:
        errors.append(f"report date {path.stem} not found in file content")

    return errors

def main() -> int:
    if not MASTER.exists():
        print(f"FAIL: template not found: {MASTER}")
        return 2
    master_source = MASTER.read_text(encoding="utf-8")
    master_parser = AuditParser()
    master_parser.feed(master_source)
    master_ids = set(master_parser.ids)

    reports = sorted(p for p in ROOT.iterdir() if p.is_file() and DATE_RE.match(p.name))
    if not reports:
        print("FAIL: no dated report files found")
        return 2

    failed = False
    for report in reports:
        errors = inspect(report, master_ids)
        if errors:
            failed = True
            print(f"FAIL {report.name}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"PASS {report.name}: required structure checks passed")

    if failed:
        print("\nSTRUCTURAL GATE FAILED. Do not label the report ready for review.")
        return 1
    print("\nSTRUCTURAL GATE PASSED. This is not a browser/visual or data-verification pass.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
