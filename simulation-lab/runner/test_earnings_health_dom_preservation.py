#!/usr/bin/env python3
"""Verify FactSet data updates preserve both approved earnings-health dashboard DOMs."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "simulation-lab" / "runner"))
from build_review_html import (
    populate_earnings_health_dashboard_preserving_dom,
    update_market_sentiment_interpretation_preserving_dom,
    set_market_observation,
    set_leaf_text_preserving_dom,
    set_text,
    set_text_preserving_child_elements,
)


def shape(node):
    if isinstance(node, NavigableString):
        return "#text" if str(node).strip() else None
    if not getattr(node, "name", None):
        return None
    attrs = {}
    for key in ("id", "class", "style", "name", "type", "for", "role", "href"):
        if node.has_attr(key):
            value = node.get(key)
            attrs[key] = "<dynamic>" if key == "href" else (tuple(value) if isinstance(value, list) else str(value))
    children = [shape(child) for child in node.children]
    return (node.name, tuple(sorted(attrs.items())), tuple(x for x in children if x is not None))


def run(template_key: str, fixture_date: str, monday: bool, expected_cards: int):
    template_name = "monday-mother-template.html" if monday else "weekday-mother-template.html"
    template_path = ROOT / "simulation-lab" / "baseline" / template_name
    fixture_path = ROOT / "simulation-lab" / "fixtures" / f"report-data-{fixture_date}.json"
    soup = BeautifulSoup(template_path.read_text(encoding="utf-8"), "lxml")
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    health = soup.select_one("#sp500-earnings-health")
    if health is None:
        raise AssertionError(f"{template_key}: earnings-health section missing")
    before = shape(health)
    score_wrapper = soup.select_one("#sentiment .cnn-fg-preview .fg6-score")
    score_main = score_wrapper.select_one(".fg6-score-main") if score_wrapper else None
    score_before = shape(score_wrapper)
    set_leaf_text_preserving_dom(score_main, "42", f"{template_key} CNN score")
    if score_before != shape(score_wrapper) or score_wrapper.select_one(".fg6-outof").get_text(strip=True) != "/100":
        raise AssertionError(f"{template_key}: CNN score wrapper or /100 suffix was destroyed")
    source_box = BeautifulSoup('<div class="source">old source note <a href="https://example.com">FactSet</a> trailing text</div>', "html.parser").div
    source_shape = shape(source_box)
    set_text_preserving_child_elements(source_box, "new source note")
    if source_shape != shape(source_box) or source_box.select_one("a").get("href") != "https://example.com":
        raise AssertionError("source note update destroyed the existing source link DOM")
    guard = BeautifulSoup("<div><span>mother child</span></div>", "html.parser").div
    try:
        set_text(guard, "unsafe")
    except ValueError:
        pass
    else:
        raise AssertionError("generic set_text did not fail closed on nested DOM")
    if guard.select_one("span").get_text(strip=True) != "mother child":
        raise AssertionError("generic set_text destroyed nested child DOM")
    target_sections = [
        "#tac-global-panel-0", "#tac-global-panel-1", "#tac-global-panel-2",
        "#asia", "#tac-region-panel-2", "#tac-assets-panel-0",
        "#bonds", "#fx", "#tac-assets-panel-3", "#tac-assets-panel-4",
    ]
    seen_notes = set()
    tested_notes = 0
    for selector in target_sections:
        section = soup.select_one(selector)
        note = section.select_one(".market-reason") if section else None
        if note is None or id(note) in seen_notes:
            continue
        seen_notes.add(id(note))
        tested_notes += 1
        before_note = shape(note)
        heading_node = note.find("b", recursive=False)
        heading_text = heading_node.get_text(" ", strip=True) if heading_node else "DOM 測試觀察"
        set_market_observation(note, heading_text, f"DOM preservation test {tested_notes}")
        if before_note != shape(note):
            raise AssertionError(f"{template_key}: {selector} market observation DOM/style skeleton changed")
    if tested_notes < 3:
        raise AssertionError(f"{template_key}: expected at least three market observation slots, got {tested_notes}")
    focus_key = soup.select_one("#view .focus-panel.focus-market .key")
    if focus_key is not None:
        before_focus = shape(focus_key)
        heading_node = focus_key.find("b", recursive=False)
        if heading_node is None:
            raise AssertionError(f"{template_key}: market focus card lacks mother bold heading")
        set_market_observation(focus_key, heading_node.get_text(" ", strip=True), "DOM preservation test")
        if before_focus != shape(focus_key):
            raise AssertionError(f"{template_key}: market focus DOM/style skeleton changed")
    sentiment = soup.select_one("#sentiment")
    sentiment_card = sentiment.select(".sbox")[-1]
    sentiment_before = shape(sentiment_card)
    update_market_sentiment_interpretation_preserving_dom(sentiment, data["sentiment"])
    if sentiment_before != shape(sentiment.select(".sbox")[-1]):
        raise AssertionError(f"{template_key}: sentiment interpretation DOM/style skeleton changed")
    if data["sentiment"] not in sentiment.select(".sbox")[-1].get_text(" ", strip=True):
        raise AssertionError(f"{template_key}: sentiment interpretation text did not update")
    result = populate_earnings_health_dashboard_preserving_dom(health, data["earnings_health"], monday)
    after = shape(health)
    if before != after:
        raise AssertionError(f"{template_key}: DOM tags/classes/inline styles changed during data population")
    cards = health.select(":scope > div:nth-of-type(3) > div")
    if len(cards) != expected_cards or result["cards"] != expected_cards:
        raise AssertionError(f"{template_key}: card count changed: {len(cards)} != {expected_cards}")
    if data["earnings_health"]["forward_pe"] not in health.get_text(" ", strip=True):
        raise AssertionError(f"{template_key}: forward P/E value missing from the existing dashboard slots")
    for key in ("mag7_eps_growth", "other_493_eps_growth"):
        if str(data["earnings_health"][key]) not in health.get_text(" ", strip=True):
            raise AssertionError(f"{template_key}: {key} missing from the existing dashboard interpretation slot")
    if data["earnings_health"]["as_of_date"] not in health.select_one(".title small").get_text(" ", strip=True):
        raise AssertionError(f"{template_key}: FactSet snapshot date did not update")
    link = health.select_one("details a")
    if link is None or link.get("href") != data["earnings_health"]["source_url"]:
        raise AssertionError(f"{template_key}: FactSet source link did not update in its existing slot")
    print(f"PASS {template_key}: {expected_cards} earnings-health cards; earnings and sentiment DOM/style skeletons preserved; source date/link refreshed")


def main():
    run("monday", "2026-11-23", True, 4)
    run("weekdays", "2026-11-20", False, 3)


if __name__ == "__main__":
    main()
