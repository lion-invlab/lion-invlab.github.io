#!/usr/bin/env python3
"""Fail-fast structural regression checks for current TAC daily review reports.

This checks HTML structure and the correct weekday-specific approved master.
It does not validate market-data accuracy or visual layout; those require separate
source and browser checks.
"""
from __future__ import annotations

from datetime import date
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MONDAY_MASTER = ROOT / "母版專區" / "TAC_母版_週一_2026-10-28_最終定版.html"
WEEKDAY_MASTER = ROOT / "母版專區" / "TAC_母版_週二至週五_2026-10-28_最終定版.html"
DATE_RE = re.compile(r"^2026-\d{2}-\d{2}\.html$")
REVIEW_DATE_RE = re.compile(r"^(2026-\d{2}-\d{2})-review\.html$")

# This is a legacy 10/23 test report from before the currently approved dual-master
# workflow. Keep the file intact, but do not apply today's master gate to it.
LEGACY_EXCLUDED = {"2026-10-23.html"}

COMMON_REQUIRED_IDS = {
    "overview",
    "sentiment",
    "news-scan",
    "global-markets",
    "industry-bonds-fx-commodities",
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
MONDAY_ONLY_IDS = {"last-week-calendar", "last-week-earnings"}

class AuditParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.tags = {}
        self.tab_inputs = 0
        self.details = 0
        self.styles = 0
        self.scripts = 0
        self.local_anchors = []

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
        if tag == "a":
            href = attrs.get("href", "")
            if href.startswith("#") and len(href) > 1:
                self.local_anchors.append(href[1:])

def selected_master(report_date: date) -> tuple[Path, set[str]]:
    if report_date.weekday() == 0:
        return MONDAY_MASTER, COMMON_REQUIRED_IDS | MONDAY_ONLY_IDS
    if 1 <= report_date.weekday() <= 4:
        return WEEKDAY_MASTER, COMMON_REQUIRED_IDS
    raise ValueError(f"daily report date falls on a weekend: {report_date.isoformat()}")

def parse_ids(path: Path) -> tuple[str, AuditParser]:
    source = path.read_text(encoding="utf-8")
    parser = AuditParser()
    parser.feed(source)
    parser.close()
    return source, parser

def report_date_for_path(path: Path) -> date:
    """Accept dated root reports, review files, and canonical Pages previews."""
    if path.parent in {ROOT, ROOT / "preview"} and DATE_RE.match(path.name):
        return date.fromisoformat(path.stem)
    match = REVIEW_DATE_RE.match(path.name) if path.parent == ROOT / "review" else None
    if match:
        return date.fromisoformat(match.group(1))
    raise ValueError(f"unsupported report path: {path.relative_to(ROOT)}")


def inspect(path: Path) -> list[str]:
    errors = []
    try:
        report_date = report_date_for_path(path)
        master_path, required_ids = selected_master(report_date)
    except ValueError as exc:
        return [str(exc)]

    # Integrate the authoritative fail-closed master guard into each dated report
    # check, so structural validation cannot silently use a stale/renamed master.
    guard = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_mother_template.py"), "--date", report_date.isoformat()],
        cwd=ROOT, text=True, capture_output=True,
    )
    if guard.returncode != 0:
        detail = (guard.stdout + "\n" + guard.stderr).strip()
        return [f"approved master guard failed for {report_date.isoformat()}: {detail}"]

    if not master_path.exists():
        return [f"approved master not found: {master_path.relative_to(ROOT)}"]

    try:
        master_source, master_parser = parse_ids(master_path)
        source, parser = parse_ids(path)
    except Exception as exc:
        return [f"HTML parser/read error: {exc}"]

    ids = set(parser.ids)
    duplicate_ids = sorted({x for x in parser.ids if parser.ids.count(x) > 1})
    if duplicate_ids:
        errors.append("duplicate IDs: " + ", ".join(duplicate_ids[:20]))

    missing = sorted(required_ids - ids)
    if missing:
        errors.append("missing required template anchors/controls: " + ", ".join(missing))

    missing_from_master = sorted((required_ids & set(master_parser.ids)) - ids)
    if missing_from_master:
        errors.append("approved-master regression: " + ", ".join(missing_from_master))

    for anchor in sorted(set(parser.local_anchors) - ids):
        errors.append("unmatched local navigation anchor: #" + anchor)

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
    if report_date.isoformat() not in source and report_date.strftime("%Y/%m/%d") not in source:
        errors.append(f"report date {path.stem} not found in file content")

    return errors

def main() -> int:
    missing_masters = [p for p in (MONDAY_MASTER, WEEKDAY_MASTER) if not p.exists()]
    if missing_masters:
        print("FAIL: approved master(s) not found: " + ", ".join(str(p.relative_to(ROOT)) for p in missing_masters))
        return 2

    reports = [
        p for p in ROOT.iterdir()
        if p.is_file() and DATE_RE.match(p.name) and p.name not in LEGACY_EXCLUDED
    ]
    review_dir = ROOT / "review"
    if review_dir.is_dir():
        reports.extend(
            p for p in review_dir.iterdir()
            if p.is_file() and REVIEW_DATE_RE.match(p.name)
        )
    # Validate only the most recently changed canonical Pages preview. The
    # preview directory also contains historical experiments and dated archives;
    # rechecking every old preview would incorrectly block today's report.
    preview_dir = ROOT / "preview"
    if preview_dir.is_dir():
        previews = [
            p for p in preview_dir.iterdir()
            if p.is_file() and DATE_RE.match(p.name)
        ]
        if previews:
            def last_changed(path: Path) -> int:
                result = subprocess.run(
                    ["git", "log", "-1", "--format=%ct", "--", str(path.relative_to(ROOT))],
                    cwd=ROOT, text=True, capture_output=True,
                )
                try:
                    return int(result.stdout.strip())
                except ValueError:
                    return 0
            reports.append(max(previews, key=last_changed))

    reports = sorted(set(reports))
    if not reports:
        print("FAIL: no active dated report files found")
        return 2

    failed = False
    for report in reports:
        errors = inspect(report)
        if errors:
            failed = True
            print(f"FAIL {report.name}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"PASS {report.name}: correct weekday master anchors, structure and local links")

    if failed:
        print("\nSTRUCTURAL GATE FAILED. Do not label the report ready for review.")
        return 1
    print("\nSTRUCTURAL GATE PASSED. This is not a browser/visual or data-verification pass.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
