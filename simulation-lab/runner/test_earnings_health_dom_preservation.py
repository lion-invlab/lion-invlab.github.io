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
