#!/usr/bin/env python3
"""Verify earnings calendar cards populate approved mother slots without rebuilding wrappers."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "simulation-lab" / "runner"))
from build_review_html import (
    update_actual_results_grid,
    update_published_earnings_detail_fields,
    update_upcoming_earnings_detail_fields,
)


def mother(name):
    return BeautifulSoup((ROOT / "simulation-lab" / "baseline" / name).read_text(encoding="utf-8"), "lxml")


def counts(details):
    grid = details.select_one(".earnings-results-grid")
    cards = grid.find_all("div", class_="earnings-actual-card", recursive=False) if grid else []
    fields = details.find_all("div", class_="earnings-detail-field", recursive=False)
    return {
        "grid": grid is not None,
        "cards": len(cards),
        "card_lines": [len(card.select(".earnings-actual-line")) for card in cards],
        "card_status": [len(card.select(".earnings-actual-status")) for card in cards],
        "card_notes": [len(card.select(".earnings-actual-note")) for card in cards],
        "fields": len(fields),
        "field_labels": [field.select_one("label") is not None for field in fields],
        "field_values": [field.select_one(".earnings-detail-value") is not None for field in fields],
    }


def main():
    fixture = json.loads((ROOT / "simulation-lab" / "fixtures" / "report-data-2026-11-23.json").read_text(encoding="utf-8"))
    upcoming = fixture["earnings"]["events"][0]
    published = fixture["last_week_earnings"]["events"][0]

    # Monday mother: one approved upcoming detail field and a three-field
    # retrospective published card prototype.
    mon = mother("monday-mother-template.html")
    mon_upcoming = next(
        card for card in mon.select("#earnings details.earnings-accordion")
        if card.select_one(".earnings-results-grid") is None
    )
    mon_details = mon_upcoming.select_one(".earnings-accordion-details")
    before = counts(mon_details)
    update_upcoming_earnings_detail_fields(mon_details, upcoming, "11/24", "時間待核實", "盤後", "時間待核實")
    after = counts(mon_details)
    assert before == after and before["fields"] == 1, ("Monday upcoming shell changed", before, after)
    assert "EPS 預估" in mon_details.get_text(" ", strip=True)
    assert "營收預估" in mon_details.get_text(" ", strip=True)

    mon_published = mon.select_one("#last-week-earnings .earnings-accordion-list details.earnings-accordion")
    mon_details = mon_published.select_one(".earnings-accordion-details")
    mon_grid = mon_details.select_one(".earnings-results-grid")
    before = counts(mon_details)
    update_actual_results_grid(mon_grid, published)
    update_published_earnings_detail_fields(mon_details, published, "時間待核實")
    after = counts(mon_details)
    assert before == after and before["cards"] == 2 and before["fields"] == 3, ("Monday published shell changed", before, after)

    # Weekday mother: five forecast/detail fields and a five-field actual card
    # prototype. Use the same sealed actual event as a shape-only regression case.
    wd = mother("weekday-mother-template.html")
    wd_cards = wd.select("#earnings details.earnings-accordion")
    wd_published = next(card for card in wd_cards if card.select_one(".earnings-results-grid") is not None)
    wd_details = wd_published.select_one(".earnings-accordion-details")
    before = counts(wd_details)
    update_actual_results_grid(wd_details.select_one(".earnings-results-grid"), published)
    update_published_earnings_detail_fields(wd_details, published, "時間待核實")
    after = counts(wd_details)
    assert before == after and before["cards"] == 2 and before["fields"] == 5, ("Weekday published shell changed", before, after)

    wd_upcoming = next(card for card in wd_cards if card.select_one(".earnings-results-grid") is None)
    wd_details = wd_upcoming.select_one(".earnings-accordion-details")
    before = counts(wd_details)
    update_upcoming_earnings_detail_fields(wd_details, upcoming, "11/24", "時間待核實", "盤後", "時間待核實")
    after = counts(wd_details)
    assert before == after and before["fields"] == 5, ("Weekday upcoming shell changed", before, after)
    assert "EPS 預估" in wd_details.get_text(" ", strip=True)
    assert "營收預估" in wd_details.get_text(" ", strip=True)

    builder = (ROOT / "simulation-lab" / "runner" / "build_review_html.py").read_text(encoding="utf-8")
    assert "details.clear()" not in builder and "grid.clear()" not in builder
    print("PASS: Monday/weekday upcoming and published earnings cards update existing mother slots; card and field wrappers remain intact")


if __name__ == "__main__":
    main()
