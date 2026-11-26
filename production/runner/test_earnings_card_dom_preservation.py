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
    apply_earnings_star_style,
    classify_calendar_group,
    reset_calendar_listing,
    update_contract_link_label,
    populate_fed_weekly_agenda,
    update_earnings_calendar_source_note,
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


def test_commodity_link_uses_investing_instrument_url_not_quote_source():
    link = BeautifulSoup('<a href="https://www.cmegroup.com/bulletin.pdf">WTI 原油期貨（CLF27）</a>', "html.parser").a
    source = {"url": "https://www.cmegroup.com/bulletin.pdf"}
    instrument = "https://hk.investing.com/commodities/crude-oil-historical-data?cid=1178037"
    update_contract_link_label(link, "CLF27（2027年1月）", source, instrument)
    assert link.get_text(" ", strip=True) == "WTI 原油期貨"
    assert link["href"] == instrument
    assert source["url"].startswith("https://www.cmegroup.com/")


def test_monday_earnings_source_note_matches_approved_mother_dom():
    soup = mother("monday-mother-template.html")
    earnings = soup.select_one("#earnings")
    assert earnings is not None
    calendar_card = earnings.select_one(":scope > article.calendar-card")
    source_notes = calendar_card.find_all("div", class_="source", recursive=False) if calendar_card else []
    assert len(source_notes) >= 2, "Monday calendar card must retain its two mother-owned source notes"
    assert source_notes[-1].find("a") is not None, "dated mother source note must remain available for stale-link suppression"

def test_earnings_calendar_source_note_is_mother_specific():
    fixture = json.loads((ROOT / "simulation-lab" / "fixtures" / "report-data-2026-11-23.json").read_text(encoding="utf-8"))
    monday = mother("monday-mother-template.html")
    monday_earnings = monday.select_one("#earnings")
    monday_card = monday_earnings.select_one(":scope > article.calendar-card")
    monday_notes = monday_card.find_all("div", class_="source", recursive=False)
    assert len(monday_notes) >= 2
    original_anchor = monday_notes[-1].find("a")
    assert original_anchor is not None
    update_earnings_calendar_source_note(monday_earnings, fixture, True)
    assert "本週財報期間：" in monday_notes[-1].get_text(" ", strip=True)
    assert original_anchor.has_attr("hidden") and not original_anchor.has_attr("href")

    weekday = mother("weekday-mother-template.html")
    weekday_earnings = weekday.select_one("#earnings")
    weekday_card = weekday_earnings.select_one(":scope > article.calendar-card")
    assert weekday_card.find_all("div", class_="source", recursive=False) == []
    before = str(weekday_earnings)
    update_earnings_calendar_source_note(weekday_earnings, fixture, False)
    assert str(weekday_earnings) == before, "weekday mother source-note handling must be a no-op"


def test_earnings_star_style_matches_each_card_rating():
    soup = mother("monday-mother-template.html")
    card = next(x for x in soup.select("#earnings details.earnings-accordion") if "five-star-earnings" in x.get("class", []))
    four_star = {"stars": 4}
    apply_earnings_star_style(card, four_star)
    assert "five-star-earnings" not in card.get("class", [])
    assert "five-star-company" not in card.select_one(".earnings-company-name").get("class", [])
    apply_earnings_star_style(card, {"stars": 5})
    assert "five-star-earnings" in card.get("class", [])
    assert "five-star-company" in card.select_one(".earnings-company-name").get("class", [])


def test_calendar_grouping_respects_publication_status_and_report_cutoff():
    cutoff = "2026-11-23T05:25:00+08:00"
    assert classify_calendar_group({"status": "upcoming", "event_date": "2026-11-23T06:00:00+08:00", "time_known": True}, "2026-11-23", cutoff) == "today"
    assert classify_calendar_group({"status": "upcoming", "event_date": "2026-11-24T10:00:00+08:00", "time_known": True}, "2026-11-23", cutoff) == "upcoming"
    assert classify_calendar_group({"status": "released", "event_date": "2026-11-24T10:00:00+08:00", "time_known": True}, "2026-11-23", cutoff) == "published"
    assert classify_calendar_group({"status": "pending_verification", "event_date": "2026-11-24T10:00:00+08:00", "time_known": True}, "2026-11-23", cutoff) == "upcoming"
    assert classify_calendar_group({"status": "pending_verification", "event_date": "2026-11-23T04:00:00+08:00", "time_known": True}, "2026-11-23", cutoff) == "published"
    assert classify_calendar_group({"status": "postponed", "event_date": "2026-11-22T10:00:00+08:00", "time_known": True}, "2026-11-23", cutoff) == "upcoming"


def test_calendar_listing_removes_stale_copy_and_prototypes():
    soup = BeautifulSoup('<div class="earnings-accordion-list">舊版今日無事件<details class="earnings-accordion"></details></div>', "html.parser")
    listing = soup.div
    reset_calendar_listing(listing, "earnings-accordion", "目前沒有事件", False)
    assert listing.get_text(" ", strip=True) == "目前沒有事件"
    assert not listing.select("details.earnings-accordion")


def main():
    fixture = json.loads((ROOT / "simulation-lab" / "fixtures" / "report-data-2026-11-23.json").read_text(encoding="utf-8"))
    upcoming = fixture["earnings"]["events"][0]
    published = fixture["last_week_earnings"]["events"][0]

    test_commodity_link_uses_investing_instrument_url_not_quote_source()
    test_monday_earnings_source_note_matches_approved_mother_dom()
    test_earnings_calendar_source_note_is_mother_specific()
    test_earnings_star_style_matches_each_card_rating()
    test_calendar_grouping_respects_publication_status_and_report_cutoff()
    test_calendar_listing_removes_stale_copy_and_prototypes()

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
    monday_rows = mon_details.select(".earnings-detail-value > .earnings-detail-line")
    assert len(monday_rows) == 5, f"Monday earnings detail should have five labelled rows, got {len(monday_rows)}"
    assert [row.select_one("strong").get_text(strip=True) for row in monday_rows] == [
        "發布資訊", "EPS 預估", "營收預估", "共識時間", "資料判讀"
    ]
    assert all(row.parent is mon_details.select_one(".earnings-detail-value") for row in monday_rows)
    assert not mon_details.select(".earnings-detail-value > br"), "Monday HPE rows must not have injected br separators"

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

    # Fed weekly agenda clones the approved prototype without changing its
    # two-column date/content grid or any child inline styles.
    fed_soup = mother("monday-mother-template.html")
    fed_data = fixture
    fed_template = fed_soup.select_one("#fed .fc-fomc-weekly-event-template")
    assert fed_template is not None
    template_style = fed_template.get("style")
    template_child_styles = {
        selector: fed_template.select_one(selector).get("style")
        for selector in (".fc-fomc-weekly-event-date", ".fc-fomc-weekly-event-name", ".fc-fomc-weekly-event-impact")
    }
    populate_fed_weekly_agenda(fed_soup, fed_data)
    fed_rows = fed_soup.select("#fed .fc-fomc-weekly-events-list > .fc-fomc-weekly-event")
    assert fed_rows, "Fed weekly agenda fixture should render at least one verified event"
    assert all(row.get("style") == template_style for row in fed_rows), "Fed event row must preserve mother grid style"
    assert all({
        selector: row.select_one(selector).get("style")
        for selector in template_child_styles
    } == template_child_styles for row in fed_rows), "Fed event child styles must remain mother-owned"
    builder = (ROOT / "simulation-lab" / "runner" / "build_review_html.py").read_text(encoding="utf-8")
    assert "grid-template-columns:minmax(0,1fr)!important" not in builder, "Builder must not force a single-column Fed agenda layout"
    mother_html = (ROOT / "simulation-lab" / "baseline" / "monday-mother-template.html").read_text(encoding="utf-8")
    assert "FIX v2: remove parent two-column grid constraint" not in mother_html
    assert "FIX v3: force the EPS/revenue grid" not in mother_html
    assert mother_html.count('id="earnings-card-preview-v1-applied"') == 1
    assert "grid-template-columns:repeat(2,minmax(0,1fr))!important" in mother_html
    assert "#last-week-earnings .earnings-actual-line strong{display:block!important" in mother_html
    assert "@media(max-width:700px){html body #last-week-earnings .earnings-results-grid{grid-template-columns:repeat(2,minmax(0,1fr))!important" in mother_html
    assert "html body #last-week-earnings .earnings-results-grid{grid-template-columns:minmax(0,1fr)!important" not in mother_html
    assert "white-space:normal!important;overflow-wrap:anywhere!important;word-break:normal!important" in mother_html
    assert ".fc-fomc>.fc-fomc-weekly-events{grid-column:1/-1!important" in mother_html
    assert ".fc-fomc-weekly-event{display:grid!important;grid-template-columns:94px minmax(0,1fr)!important" in mother_html
    assert all(row.select_one(".fc-fomc-weekly-event-date") and row.select_one(".fc-fomc-weekly-event-name") and row.select_one(".fc-fomc-weekly-event-impact") for row in fed_rows)

    builder = (ROOT / "simulation-lab" / "runner" / "build_review_html.py").read_text(encoding="utf-8")
    assert "details.clear()" not in builder and "grid.clear()" not in builder
    print("PASS: Monday/weekday upcoming and published earnings cards update existing mother slots; card and field wrappers remain intact")


if __name__ == "__main__":
    main()
