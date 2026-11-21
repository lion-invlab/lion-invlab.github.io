#!/usr/bin/env python3
"""Regression tests for the SIM-1.4 cash-index versus CFD render boundary."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "simulation-lab" / "runner"))
from bs4 import BeautifulSoup
from build_review_html import reject_cfd_cash_index_quotes, earnings_status_label, normalize_market_label, populate_fed_weekly_agenda, populate_fedwatch_two_slots, populate_summary_points_preserving_dom, set_market_observation, set_text_preserving_child_elements


def record(value, change, quote_type):
    return {
        "display": value,
        "change_display": change,
        "source": {
            "name": "Investing.com historical data",
            "url": "https://example.invalid/historical",
            "data_date": "2026-11-20",
            "quote_type": quote_type,
        },
    }


def test_fed_agenda_slots():
    fixtures = [
        {
            "name": "Waller delivers remarks",
            "date": "2026-11-18T09:00:00",
            "status": "completed",
            "impact": "觀察對通膨與政策路徑的看法",
            "source_url": "https://www.federalreserve.gov/newsevents.htm",
        },
        {
            "name": "Bowman speaks on banking",
            "date": "2026-11-19T14:30:00",
            "status": "upcoming",
            "impact": "留意銀行監理政策訊號",
            "source_url": "https://www.federalreserve.gov/newsevents.htm",
        },
    ]
    for filename in ("monday-mother-template.html", "weekday-mother-template.html"):
        html = (ROOT / "simulation-lab" / "baseline" / filename).read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "html.parser")
        box = soup.select_one("#fed .fc-fomc-weekly-events")
        assert box is not None, filename
        observation_slot = soup.select_one("#fed .fc-fomc-observation")
        assert observation_slot is not None and "fc-fomc-weekly-events" not in observation_slot.get("class", [])
        observation_before = (observation_slot.name, tuple(observation_slot.get("class", [])), observation_slot.get_text(" ", strip=True))
        assert len(soup.select("#fed .fc-fomc-weekly-events")) == 1
        outer_children = [(child.name, tuple(child.get("class", []))) for child in box.find_all(recursive=False)]
        list_node = box.select_one(".fc-fomc-weekly-events-list")
        list_children_before = [(child.name, tuple(child.get("class", []))) for child in list_node.find_all(recursive=False)]
        count = populate_fed_weekly_agenda(soup, {
            "calendar": {"week_start": "2026-11-16", "week_end": "2026-11-22", "events": fixtures}
        })
        assert count == 2, (filename, count)
        assert "Waller delivers remarks" in box.get_text(" ", strip=True)
        assert "Bowman speaks on banking" in box.get_text(" ", strip=True)
        assert [(child.name, tuple(child.get("class", []))) for child in box.find_all(recursive=False)] == outer_children
        assert (observation_slot.name, tuple(observation_slot.get("class", [])), observation_slot.get_text(" ", strip=True)) == observation_before
        assert [(child.name, tuple(child.get("class", []))) for child in list_node.find_all(recursive=False)][0] == list_children_before[0]
        assert len(list_node.select(":scope > .fc-fomc-weekly-event")) == 2
        assert list_node.select_one(".fc-fomc-weekly-event-template[hidden]") is not None
        # No-event weeks preserve the same fixed outer structure and show the explicit empty state.
        count = populate_fed_weekly_agenda(soup, {
            "calendar": {"week_start": "2026-11-16", "week_end": "2026-11-22", "events": []}
        })
        assert count == 0
        assert box.select_one(".fc-fomc-weekly-events-empty").has_attr("hidden") is False
        assert len(box.select(".fc-fomc-weekly-events")) == 0


def test_1123_fixture_uses_cash_index_historical_sources():
    fixture_path = ROOT / "simulation-lab" / "fixtures" / "report-data-2026-11-23.json"
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    rejected = reject_cfd_cash_index_quotes(data)
    assert rejected == [], rejected
    expected = {
        "標普500指數": ("6,910.39", "-3.70%"),
        "日經225": ("56,436.65", "-5.06%"),
        "香港恆生指數": ("22,410.80", "-1.89%"),
        "英國 FTSE 100": ("10,346.34", "-1.02%"),
        "德國 DAX": ("24,802.78", "-2.60%"),
        "STOXX Europe 600": ("625.65", "-2.00%"),
    }
    for name, (close, change) in expected.items():
        row = data["global_markets"][name]
        assert row["display"] == close, (name, row["display"])
        assert row["change_display"] == change, (name, row["change_display"])
        assert row["source"]["quote_type"] == "cash_index_close", (name, row["source"])
        assert "historical-data" in row["source"]["url"]
        assert "rejected_reference" not in row and row.get("qa_status") != "cfd_index_reference_rejected"


def test_structured_market_observation():
    soup = BeautifulSoup('<div class="key"><b>舊標題</b><br/>舊觀察文字</div>', "html.parser")
    node = soup.select_one(".key")
    before = [(child.name, child.get("class")) if getattr(child, "name", None) else "#text" for child in node.contents]
    set_market_observation(node, "fallback", {"heading": "盤面觀察重點", "text": "測試觀察內容"})
    after = [(child.name, child.get("class")) if getattr(child, "name", None) else "#text" for child in node.contents]
    assert before == after
    assert node.select_one("b").get_text(strip=True) == "盤面觀察重點"
    assert "測試觀察內容" in node.get_text(" ", strip=True)
    wrapped = BeautifulSoup('<div class="key"><span>old</span></div>', "html.parser").select_one(".key")
    wrapped_before = [child.name for child in wrapped.contents]
    set_market_observation(wrapped, "fallback", {"heading": "盤面觀察重點", "text": "測試觀察內容"})
    assert [child.name for child in wrapped.contents] == wrapped_before
    assert wrapped.select_one("span").get_text(strip=True) == "盤面觀察重點｜測試觀察內容"


def test_fedwatch_two_card_contract():
    for filename in ("monday-mother-template.html", "weekday-mother-template.html"):
        html = (ROOT / "simulation-lab" / "baseline" / filename).read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "html.parser")
        panel = soup.select_one("#fed .fed-live-watch")
        assert panel is not None
        before = (len(panel.select(".fc-prob")), len(panel.select(".fc-split-bar > span")), len(panel.select(".fc-split-legend > span")))
        note = populate_fedwatch_two_slots(panel, {
            "fedwatch": {
                "current_target_range": "3.75-4.00%",
                "probabilities": [
                    {"outcome": "hold", "rate_range": "3.75-4.00%", "probability": 13.6},
                    {"outcome": "hike", "rate_range": "4.00-4.25%", "probability": 86.4},
                ],
            }
        })
        assert note is None
        assert before == (2, 2, 2)
        assert (len(panel.select(".fc-prob")), len(panel.select(".fc-split-bar > span")), len(panel.select(".fc-split-legend > span"))) == before
        assert panel.select(".fc-prob strong")[0].get_text(strip=True) == "13.6%"
        assert panel.select(".fc-prob strong")[1].get_text(strip=True) == "86.4%"
        note = populate_fedwatch_two_slots(panel, {
            "fedwatch": {
                "current_target_range": "3.75-4.00%",
                "probabilities": [
                    {"outcome": "cut", "rate_range": "3.50-3.75%", "probability": 8.0},
                    {"outcome": "hold", "rate_range": "3.75-4.00%", "probability": 70.0},
                    {"outcome": "hike", "rate_range": "4.00-4.25%", "probability": 22.0},
                ],
            }
        })
        assert "cut" in note and "hike" in note
        assert len(panel.select(".fc-prob")) == 2
        assert panel.select_one(".fc-split-bar").has_attr("hidden")
        assert "待核實" in panel.get_text(" ", strip=True)




def test_summary_content_fills_existing_mother_slots():
    soup = BeautifulSoup(
        '<p><b>舊標籤一</b><br/>舊文字一<br/><b>舊標籤二</b><br/>舊文字二</p>',
        "html.parser",
    )
    node = soup.p
    before = [(child.name, str(child) if child.name is None else tuple(child.get("class", []))) for child in node.contents]
    populate_summary_points_preserving_dom(node, [
        {"label": "新標籤一", "text": "新文字一"},
        {"label": "新標籤二", "text": "新文字二"},
    ])
    after = [(child.name, str(child) if child.name is None else tuple(child.get("class", []))) for child in node.contents]
    assert [x[0] for x in after] == [x[0] for x in before]
    assert node.get_text(" ", strip=True) == "新標籤一 新文字一 新標籤二 新文字二"
    weekday = BeautifulSoup(
        '<p><b>舊標籤一</b>舊文字一<br/><b>舊標籤二</b>舊文字二</p>',
        "html.parser",
    ).p
    weekday_before = [child.name for child in weekday.contents]
    populate_summary_points_preserving_dom(weekday, [
        {"label": "新標籤一", "text": "新文字一"},
        {"label": "新標籤二", "text": "新文字二"},
    ])
    assert [child.name for child in weekday.contents] == weekday_before
    assert weekday.get_text(" ", strip=True) == "新標籤一 新文字一 新標籤二 新文字二"
    try:
        populate_summary_points_preserving_dom(node, [{"label": "只有一項", "text": "不匹配母版"}])
    except ValueError as exc:
        assert "does not match mother template slots" in str(exc)
    else:
        raise AssertionError("summary slot count mismatch must fail closed")

def test_builder_preserves_mother_owned_fed_agenda_and_css():
    builder = (ROOT / "simulation-lab" / "runner" / "build_review_html.py").read_text(encoding="utf-8")
    # Fed agenda content may change, but the mother-owned outer DOM must never be cleared.
    assert "fed_events_box.clear()" not in builder
    assert "final_fed_box.clear()" not in builder
    assert "populate_fed_weekly_agenda(soup, data)" in builder
    # Layout and typography are owned by the mother templates, not daily Builder patches.
    for forbidden_id in (
        "tac-summary-heading-size-alignment",
        "tac-last-week-disclosure-unified-v1",
        "tac-simulation-layout-authority-v1",
        "tac-energy-quote-mobile-overlap-fix-v2",
    ):
        assert forbidden_id not in builder, forbidden_id


def test_market_observation_supports_existing_text_slot_shapes():
    plain = BeautifulSoup('<div class="plain">舊文字</div>', "html.parser").div
    set_market_observation(plain, "盤面觀察", "新文字")
    assert plain.get_text(" ", strip=True) == "盤面觀察｜新文字"
    assert len(plain.find_all(recursive=False)) == 0

    wrapped = BeautifulSoup('<div class="wrapped"><b>舊標題</b><br/><span>舊文字</span></div>', "html.parser").div
    before = [(child.name, tuple(child.get("class", [])) if child.name else None) for child in wrapped.contents]
    set_market_observation(wrapped, "新標題", "新文字")
    after = [(child.name, tuple(child.get("class", [])) if child.name else None) for child in wrapped.contents]
    assert before == after
    assert wrapped.get_text(" ", strip=True) == "新標題 新文字"


def test_text_update_preserves_source_link_elements():
    node = BeautifulSoup(
        '<div class="source">舊說明 <a href="https://example.com">原始來源</a> 舊尾註</div>',
        "html.parser",
    ).div
    before = [(child.name, child.get("href")) if getattr(child, "name", None) else "#text" for child in node.contents]
    set_text_preserving_child_elements(node, "新說明")
    after = [(child.name, child.get("href")) if getattr(child, "name", None) else "#text" for child in node.contents]
    assert before == after
    assert node.get_text(" ", strip=True) == "新說明 原始來源 舊尾註"
    assert node.select_one("a").get("href") == "https://example.com"


def test_link_only_source_container_is_left_intact():
    node = BeautifulSoup('<div class="source"><a href="https://example.com">原始來源</a></div>', "html.parser").div
    before = [(child.name, child.get("href")) if getattr(child, "name", None) else "#text" for child in node.contents]
    changed = set_text_preserving_child_elements(node, "不應覆蓋連結")
    after = [(child.name, child.get("href")) if getattr(child, "name", None) else "#text" for child in node.contents]
    assert changed is False
    assert before == after
    assert node.select_one("a").get_text(strip=True) == "原始來源"

def main():
    data = {
        "global_markets": {
            "S&P 500 CFD": record("6,500.00", "-3.70%", "cfd_index_reference_series"),
            "Dow cash index": record("48,147.33", "-1.93%", "cash_index_close"),
            "Nasdaq provider series": record("22,617.73", "-5.28%", "provider_index_reference_series"),
        }
    }
    rejected = reject_cfd_cash_index_quotes(data)
    assert rejected == ["S&P 500 CFD"], rejected
    cfd = data["global_markets"]["S&P 500 CFD"]
    assert cfd["display"] == "待核實" and cfd["change_display"] == "待核實"
    assert cfd["qa_status"] == "cfd_index_reference_rejected"
    assert cfd["rejected_reference"]["display"] == "6,500.00"
    assert data["global_markets"]["Dow cash index"]["display"] == "48,147.33"
    assert data["global_markets"]["Nasdaq provider series"]["display"] == "22,617.73"
    # Idempotence: a second pass must not reintroduce the rejected numeric quote.
    assert reject_cfd_cash_index_quotes(data) == ["S&P 500 CFD"]
    assert cfd["display"] == "待核實"
    assert normalize_market_label("日經225") == normalize_market_label("日經 225")
    assert normalize_market_label("日經　225") == normalize_market_label("日經225")
    assert earnings_status_label({"eps_actual": 2.70, "eps_estimate": None}, "eps", "pending") == "比較資料尚未齊備"
    assert earnings_status_label({"status": "pending_verification"}, "eps", "pending") == "公告已發布；實際值待核實"
    assert earnings_status_label({}, "eps", "pending") == "尚未公布"
    test_fed_agenda_slots()
    test_builder_preserves_mother_owned_fed_agenda_and_css()
    test_summary_content_fills_existing_mother_slots()
    test_market_observation_supports_existing_text_slot_shapes()
    test_text_update_preserves_source_link_elements()
    test_link_only_source_container_is_left_intact()
    test_fedwatch_two_card_contract()
    test_structured_market_observation()
    test_1123_fixture_uses_cash_index_historical_sources()
    print("PASS: CFD guard, six cash-index sources, label normalization, earnings labels, and fixed Fed agenda slots")


if __name__ == "__main__":
    main()
