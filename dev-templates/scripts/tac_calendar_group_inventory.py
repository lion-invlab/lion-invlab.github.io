"""Read-only inventory of template-native calendar repeat-group prototypes.

The inventory never edits HTML. It reports where the same status group has a
real card prototype available for a future guarded repeat-group updater.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cssselect2
import html5lib

ROOT = Path(__file__).resolve().parents[2]
MOTHERS = {
    "monday": ROOT / "母版專區/TAC_母版_週一_2026-10-28_最終定版.html",
    "weekdays": ROOT / "母版專區/TAC_母版_週二至週五_2026-10-28_最終定版.html",
}
SECTIONS = {
    "weekly_economic": ("#calendar", ".econ-event-list", ".econ-event"),
    "weekly_earnings": ("#earnings", ".earnings-accordion-list", ".earnings-accordion"),
    "prior_week_economic": ("#last-week-calendar", ".econ-event-list", ".econ-event"),
    "prior_week_earnings": ("#last-week-earnings", ".earnings-accordion-list", ".earnings-accordion"),
}
STATUS_CLASSES = {"today", "upcoming", "published"}


def _semantic_status(heading_text):
    text = " ".join(heading_text.split())
    if text.startswith("上週已公布"):
        return "prior_week_published"
    if text.startswith(("今日公布", "今日及今晚")):
        return "today"
    if text.startswith("即將公布"):
        return "upcoming"
    if text.startswith("已公布"):
        return "published"
    return None


def _parse(source):
    return html5lib.parse(source, treebuilder="etree", namespaceHTMLElements=False)


def _query(root, selector):
    wrapped = cssselect2.ElementWrapper.from_html_root(root)
    return [item.etree_element for item in wrapped.query_all(selector)]


def _direct(root, parent, selector):
    wrapped = cssselect2.ElementWrapper.from_html_root(root)
    return [
        item.etree_element for item in wrapped.query_all(selector)
        if item.parent is not None and item.parent.etree_element is parent
    ]


def inventory_calendar_groups(source, template):
    if template not in {"monday", "weekdays"}:
        raise ValueError("template must be monday or weekdays")
    root = _parse(source)
    report = {"template": template, "sections": {}, "pass": True}

    for name, (section_selector, list_selector, card_selector) in SECTIONS.items():
        if name.startswith("prior_week_") and template == "weekdays":
            report["sections"][name] = {"present": False, "groups": [], "pass": True}
            continue

        sections = _query(root, section_selector)
        if len(sections) != 1:
            report["sections"][name] = {
                "present": bool(sections), "groups": [], "pass": False,
                "reason": f"expected_one_section_got_{len(sections)}",
            }
            report["pass"] = False
            continue

        groups = _query(sections[0], ".calendar-status-group")
        group_rows = []
        for index, group in enumerate(groups):
            headings = _direct(root, group, ".calendar-status-heading")
            lists = _direct(root, group, list_selector)
            empties = _direct(root, group, ".calendar-status-empty")
            status_class = None
            heading_text = ""
            status_key = None
            if len(headings) == 1:
                classes = set(headings[0].attrib.get("class", "").split())
                matches = classes & STATUS_CLASSES
                if len(matches) == 1:
                    status_class = next(iter(matches))
                heading_text = " ".join("".join(headings[0].itertext()).split())
                status_key = _semantic_status(heading_text)
            cards = _direct(root, lists[0], card_selector) if len(lists) == 1 else []
            variant_valid = (
                len(headings) == 1
                and status_class is not None
                and status_key is not None
                and ((len(lists) == 1 and len(empties) == 0 and len(cards) > 0)
                     or (len(lists) == 0 and len(empties) == 1))
            )
            group_rows.append({
                "index": index,
                "status_class": status_class,
                "status_key": status_key,
                "heading_text": heading_text,
                "heading_count": len(headings),
                "list_count": len(lists),
                "empty_state_count": len(empties),
                "card_count": len(cards),
                "has_same_group_card_prototype": len(cards) > 0,
                "can_clone_without_cross_group_prototype": len(cards) > 0 and variant_valid,
                "variant_valid": variant_valid,
            })

        section_pass = bool(groups) and all(row["variant_valid"] for row in group_rows)
        report["sections"][name] = {
            "present": True,
            "groups": group_rows,
            "pass": section_pass,
        }
        report["pass"] = report["pass"] and section_pass

    return report


def inventory_mother(template):
    path = MOTHERS[template]
    return inventory_calendar_groups(path.read_text(encoding="utf-8"), template)


def main():
    parser = argparse.ArgumentParser(description="Inventory template-native calendar repeat-group prototypes")
    parser.add_argument("--output", help="Optional JSON report path")
    args = parser.parse_args()
    report = {template: inventory_mother(template) for template in ("monday", "weekdays")}
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
