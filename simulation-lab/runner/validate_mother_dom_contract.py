#!/usr/bin/env python3
"""Compare stable mother-owned DOM contracts between a locked mother and a built review."""
from __future__ import annotations
import argparse
from collections import Counter
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString


def parse(path: str):
    return BeautifulSoup(Path(path).read_text(encoding="utf-8"), "lxml")


def shape(node, omit_dynamic_fed_rows=False, include_style=False):
    if isinstance(node, NavigableString):
        return "#text" if str(node).strip() else None
    if not getattr(node, "name", None):
        return None
    if omit_dynamic_fed_rows and "fc-fomc-weekly-event" in node.get("class", []) and "fc-fomc-weekly-event-template" not in node.get("class", []):
        return None
    attrs = {}
    keys = ("id", "class", "name", "type", "for", "role", "style") if include_style else ("id", "class", "name", "type", "for", "role")
    for key in keys:
        if node.has_attr(key):
            value = node.get(key)
            attrs[key] = tuple(value) if isinstance(value, list) else str(value)
    children = [shape(child, omit_dynamic_fed_rows, include_style) for child in node.children]
    return (node.name, tuple(sorted(attrs.items())), tuple(child for child in children if child is not None))


def require_one(soup, selector, context):
    nodes = soup.select(selector)
    if len(nodes) != 1:
        raise ValueError(f"{context}: expected one {selector}, found {len(nodes)}")
    return nodes[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mother", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--template", choices=("monday", "weekdays"), required=True)
    args = ap.parse_args()
    mother, report = parse(args.mother), parse(args.report)

    # The page's static code and CSS are immutable during daily data assembly.
    for tag in ("style", "script"):
        left = [(dict(x.attrs), x.get_text()) for x in mother.find_all(tag)]
        right = [(dict(x.attrs), x.get_text()) for x in report.find_all(tag)]
        if left != right:
            raise ValueError(f"{tag} nodes or contents differ from the approved mother")
    # IDs and navigation/tab wiring are part of the fixed mother contract.
    left_ids = Counter(x.get("id") for x in mother.find_all(id=True))
    right_ids = Counter(x.get("id") for x in report.find_all(id=True))
    if left_ids != right_ids:
        missing, added = list((left_ids - right_ids).elements()), list((right_ids - left_ids).elements())
        raise ValueError(f"ID inventory changed; missing={missing[:12]}, added={added[:12]}")

    stable_selectors = [
        ("#overview > section.grid.two > article.card.bluf > p", "summary paragraph"),
        ("#fed .fc-fomc-observation", "FOMC core observation slot"),
        ("#fed .fed-live-tab-labels", "Fed live tab labels"),
        ("#fed .fc-fomc-meeting", "FOMC meeting slot"),
        ("#fed .fc-fomc-press", "FOMC press conference slot"),
        ("#fed .fc-fomc-rate", "FOMC policy rate slot"),
        ("#fed .fc-probs", "FedWatch probability cards"),
        ("#fed .fc-split-wrap", "FedWatch distribution bar and legend"),
        ("#fed .fc-fomc-weekly-events", "Fed weekly agenda wrapper"),
        ("#sp500-earnings-health", "S&P 500 earnings-health dashboard"),
        ("#sentiment .sent > .sbox:last-child", "market sentiment interpretation card"),
        ("#sentiment .cnn-fg-preview .fg6-score", "CNN Fear & Greed score wrapper"),
        ("#view .focus-panel.focus-market .key", "Today Focus market observation slot"),
        ("#tac-side-tools", "QUICK ACCESS toolbar"),
    ]
    for selector, context in stable_selectors:
        left = require_one(mother, selector, "mother " + context)
        right = require_one(report, selector, "review " + context)
        omit = selector == "#fed .fc-fomc-weekly-events"
        include_style = selector in {"#sp500-earnings-health", "#sentiment .sent > .sbox:last-child", "#sentiment .cnn-fg-preview .fg6-score", "#view .focus-panel.focus-market .key"}
        if shape(left, omit_dynamic_fed_rows=omit, include_style=include_style) != shape(right, omit_dynamic_fed_rows=omit, include_style=include_style):
            raise ValueError(f"{context} DOM skeleton changed from the approved mother")

    # Market commentary is dynamic text only; preserve every mother-owned note skeleton and inline style.
    left_notes = mother.select(".market-reason")
    right_notes = report.select(".market-reason")
    if len(left_notes) != len(right_notes) or [
        shape(node, include_style=True) for node in left_notes
    ] != [
        shape(node, include_style=True) for node in right_notes
    ]:
        raise ValueError("market observation DOM skeleton or inline styles changed from the approved mother")

    # Verify the two tab radio controls and label wiring without diffing their dynamic panel contents.
    for soup, label in ((mother, "mother"), (report, "review")):
        radios = soup.select("#fed .fed-live-tabs > input[type=radio]")
        labels = soup.select("#fed .fed-live-tab-labels > label")
        if len(radios) != 2 or len(labels) != 2:
            raise ValueError(f"{label}: Fed live tabs must retain exactly two radio controls and two labels")
        if [(x.get("id"), x.get("name"), x.get("type")) for x in radios] != [
            ("fed-live-tab-watch", "fed-live-tab", "radio"),
            ("fed-live-tab-fomc", "fed-live-tab", "radio"),
        ]:
            raise ValueError(f"{label}: Fed live radio IDs/order changed")
        if [x.get("for") for x in labels] != ["fed-live-tab-watch", "fed-live-tab-fomc"]:
            raise ValueError(f"{label}: Fed live tab label wiring changed")

    # The weekly agenda's generated rows are dynamic, but its four fixed slots must remain.
    for soup, label in ((mother, "mother"), (report, "review")):
        box = require_one(soup, "#fed .fc-fomc-weekly-events", label + " Fed agenda")
        for selector in (".fc-fomc-weekly-events-title", ".fc-fomc-weekly-events-list",
                         ".fc-fomc-weekly-event-template", ".fc-fomc-weekly-events-empty"):
            require_one(box, selector, label + " Fed agenda slot")
    # Today Focus is a mother-owned three-tab component. Its data text may
    # change, but tab wiring, panel shells, the core callout tree, and the
    # key-level disclosure controls must remain the approved mother structure.
    expected_focus_panels = [
        ["focus-panel", "focus-market"],
        ["focus-panel", "focus-levels"],
        ["focus-panel", "focus-core"],
    ]
    for soup, label in ((mother, "mother"), (report, "review")):
        view = require_one(soup, "#view", label + " Today Focus")
        tabs = require_one(view, ".focus-tabs", label + " Today Focus tabs")
        radios = tabs.select(":scope > input[type=radio]")
        labels = tabs.select(":scope > .focus-tab-labels > label")
        panels = tabs.select(":scope > .focus-panels > .focus-panel")
        if len(radios) != 3 or len(labels) != 3 or len(panels) != 3:
            raise ValueError(f"{label}: Today Focus must retain exactly three radios, labels and panels")
        if [(x.get("id"), x.get("name"), x.get("type")) for x in radios] != [
            ("focus-tab-market", "focus-tab", "radio"),
            ("focus-tab-levels", "focus-tab", "radio"),
            ("focus-tab-core", "focus-tab", "radio"),
        ]:
            raise ValueError(f"{label}: Today Focus radio IDs/order changed")
        if [x.get("for") for x in labels] != [
            "focus-tab-market", "focus-tab-levels", "focus-tab-core"
        ]:
            raise ValueError(f"{label}: Today Focus label wiring changed")
        if [x.get("class") for x in panels] != expected_focus_panels:
            raise ValueError(f"{label}: Today Focus panel order/classes changed")
        levels_key = require_one(view, ".focus-panel.focus-levels > .key", label + " key levels slot")
        levels_disclosure = require_one(
            levels_key, "details.compact-disclosure", label + " key levels disclosure"
        )
        require_one(levels_disclosure, "summary", label + " key levels disclosure summary")
        if len(levels_disclosure.find_all("div", recursive=False)) != 1:
            raise ValueError(f"{label}: key levels disclosure body wrapper changed")
        core_callout = require_one(
            view, ".focus-panel.focus-core > .callout", label + " core observation callout"
        )
        if len(core_callout.find_all("b", recursive=False)) != 1:
            raise ValueError(f"{label}: core observation heading slot missing or duplicated")
        if args.template == "monday":
            core_disclosure = require_one(
                core_callout, "details.compact-disclosure", label + " core observation disclosure"
            )
            if len(core_disclosure.find_all("div", recursive=False)) != 2:
                raise ValueError(f"{label}: core observation disclosure must retain two mother detail slots")
    left_core = require_one(mother, "#view .focus-panel.focus-core > .callout", "mother core callout")
    right_core = require_one(report, "#view .focus-panel.focus-core > .callout", "review core callout")
    if shape(left_core) != shape(right_core):
        raise ValueError("Today Focus core callout DOM skeleton changed from the approved mother")
    left_levels = require_one(mother, "#view .focus-panel.focus-levels > .key", "mother key levels slot")
    right_levels = require_one(report, "#view .focus-panel.focus-levels > .key", "review key levels slot")
    if (left_levels.name, tuple(sorted((k, tuple(v) if isinstance(v, list) else str(v))
                                      for k, v in left_levels.attrs.items()))) != (
        right_levels.name, tuple(sorted((k, tuple(v) if isinstance(v, list) else str(v))
                                        for k, v in right_levels.attrs.items()))
    ):
        raise ValueError("Today Focus key levels content-slot wrapper changed")

    if args.template == "monday":
        for selector in ("#last-week-calendar details.last-week-calendar-collapse > summary",
                         "#last-week-earnings details.last-week-earnings-collapse > summary"):
            if shape(require_one(mother, selector, "mother Monday disclosure")) != shape(require_one(report, selector, "review Monday disclosure")):
                raise ValueError(f"Monday disclosure DOM changed: {selector}")
    elif mother.select("#last-week-calendar, #last-week-earnings") or report.select("#last-week-calendar, #last-week-earnings"):
        raise ValueError("weekday report unexpectedly contains Monday-only disclosure sections")

    print(f"PASS: mother-owned DOM contract unchanged ({args.template}); style/script, ID inventory, summary, Fed, toolbar and disclosures verified")


if __name__ == "__main__":
    main()
