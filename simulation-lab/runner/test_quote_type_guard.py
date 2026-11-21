#!/usr/bin/env python3
"""Regression tests for the SIM-1.4 cash-index versus CFD render boundary."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "simulation-lab" / "runner"))
from bs4 import BeautifulSoup
from build_review_html import reject_cfd_cash_index_quotes, earnings_status_label, normalize_market_label, populate_fed_weekly_agenda, populate_fedwatch_two_slots, set_market_observation


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


def test_structured_market_observation():
    soup = BeautifulSoup('<div class="key"><span>old</span></div>', "html.parser")
    node = soup.select_one(".key")
    set_market_observation(node, "fallback", {"heading": "盤面觀察重點", "text": "測試觀察內容"})
    assert node.select_one("b").get_text(strip=True) == "盤面觀察重點"
    assert "測試觀察內容" in node.get_text(" ", strip=True)


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
    test_fedwatch_two_card_contract()
    test_structured_market_observation()
    print("PASS: CFD guard, label normalization, earnings labels, and fixed Fed agenda slots")


if __name__ == "__main__":
    main()
