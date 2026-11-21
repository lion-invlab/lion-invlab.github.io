#!/usr/bin/env python3
"""Pre-build contract checks for the 2026-11-23 Monday report fixture."""
from datetime import datetime
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "simulation-lab" / "fixtures" / "report-data-2026-11-23.json"


def main():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert data["report_date"] == "2026-11-23"
    assert data["trading_date"] == "2026-11-20"
    assert data["report_cutoff_taipei"] == "2026-11-23 05:25"
    assert data["news_cutoff_taipei"] == "2026-11-21 17:57:31"
    assert data["report_cutoff_taipei"] != data["news_cutoff_taipei"]
    assert "2026/11/20 12:00" in data["news_window_taipei"]
    assert "2026/11/21 17:57:31" in data["news_window_taipei"]

    counts = {
        "global_indices": len(data["global_markets"]),
        "sectors": len(data["sectors"]),
        "bonds": len(data["bonds"]),
        "fx": len(data["fx"]),
        "energy": len(data["energy"]),
        "metals": len(data["metals"]),
        "risk": len(data["risk"]),
    }
    total = sum(counts.values())
    assert counts == {
        "global_indices": 17, "sectors": 11, "bonds": 3,
        "fx": 6, "energy": 2, "metals": 2, "risk": 3,
    }, counts
    assert total == 44, total

    for group in ("global_markets", "bonds", "fx", "energy", "metals", "risk"):
        for name, item in data[group].items():
            assert item.get("source", {}).get("url", "").startswith("https://"), (group, name)
    assert len(data["sector_sources"]) == 11
    for ticker, item in data["sector_sources"].items():
        assert item.get("url", "").startswith("https://"), ticker
        assert item.get("change_display") == data["sectors"][ticker], ticker
    # ETF insertion order is already sorted by one-day percentage return, high to low.
    def pct(value):
        return float(str(value).replace("%", "").replace("+", ""))
    sector_values = [pct(v) for v in data["sectors"].values()]
    assert sector_values == sorted(sector_values, reverse=True), sector_values

    news = data["focus_news"] + data["headlines"]
    assert len(data["focus_news"]) == 5
    assert len(data["headlines"]) == 10
    assert len(news) == 15
    assert len({item["url"] for item in news}) == 15
    start = datetime.strptime("2026/11/20 12:00", "%Y/%m/%d %H:%M")
    end = datetime.strptime(data["news_cutoff_taipei"], "%Y-%m-%d %H:%M:%S")
    for item in news:
        assert item.get("url", "").startswith("https://"), item.get("title")
        assert item.get("published_at_source"), item.get("title")
        assert item.get("source_timezone"), item.get("title")
        assert item.get("published_at_tw"), item.get("title")
        assert item.get("updated_at_source"), item.get("title")
        assert item.get("summary"), item.get("title")
        published = datetime.strptime(item["published_at_tw"], "%Y/%m/%d %H:%M")
        assert start <= published <= end, (item["title"], item["published_at_tw"])

    assert sum(x["probability"] for x in data["fedwatch"]["probabilities"]) == 100
    assert data["earnings_health"]["as_of_date"] == "2026-11-20"
    assert data["earnings_health"]["source_url"].startswith("https://")
    assert data["earnings_health"]["mag7_eps_growth"]
    assert data["earnings_health"]["other_493_eps_growth"]

    # Market-source audit: exact 2026-11-20 source dates and approved official FX quote.
    for group in ("global_markets", "bonds", "fx", "energy", "metals", "risk"):
        for name, item in data[group].items():
            assert item["source"]["data_date"] == data["trading_date"], (group, name)
    for ticker, item in data["sector_sources"].items():
        assert item["data_date"] == data["trading_date"], ticker
    assert data["fx"]["美元指數"]["display"] == "103.81"
    assert data["fx"]["美元指數"]["change_display"] == "-0.08%"
    assert data["fx"]["美元／新台幣"]["display"] == "32.936"
    assert data["fx"]["美元／新台幣"]["source"]["quote_type"] == "official_interbank_close"
    assert data["metals"]["白銀期貨 SI"]["change_display"] == "-7.42%"
    assert data["energy"]["WTI原油期貨"]["contract_label"].startswith("CLF27")
    assert data["energy"]["Brent原油期貨"]["source"]["change_points"] == "+0.59"
    assert data["energy"]["Brent原油期貨"]["source"]["ice_official_last"] == "92.49"
    assert data["fedwatch"]["updated_at_tw"] == "2026/11/21 13:35"

    levels = data["key_levels"]
    assert levels["source"].startswith("ChatGPT direct manual verification")
    assert levels["baseline_date"] == data["trading_date"]
    assert [x["key"] for x in levels["items"]] == ["dow", "sp500", "nasdaq", "sox", "russell2000"]
    for item in levels["items"]:
        assert item["trading_date"] == data["trading_date"]
        assert item["quote_type"] == "cash_index"
        assert item["url"].startswith("https://")
        assert all(item.get(k) for k in ("ohlc", "s2", "s1", "p", "r1", "r2"))
    current_calendar = data["calendar"]
    current_earnings = data["earnings"]
    previous_calendar = data["last_week_calendar"]
    previous_earnings = data["last_week_earnings"]
    assert current_calendar["week_id"] == "2026-W48"
    assert current_earnings["week_id"] == "2026-W48"
    assert len(current_calendar["events"]) == 27
    assert len(current_earnings["events"]) == 11
    assert len(previous_calendar["events"]) == 2
    assert len(previous_earnings["events"]) == 1
    assert all(x["stars"] == 5 for x in previous_calendar["events"])
    assert all(x["stars"] == 5 for x in previous_earnings["events"])
    for event in current_calendar["events"] + current_earnings["events"] + previous_calendar["events"] + previous_earnings["events"]:
        assert event["source_url"].startswith("https://"), event.get("id")
    assert all(x["eps_estimate"] is None and x["revenue_estimate"] is None for x in current_earnings["events"])
    nvda = previous_earnings["events"][0]
    assert nvda["ticker"] == "NVDA"
    assert nvda["eps_actual"] == 2.7 and nvda["revenue_actual"] == 115.8
    assert "2.89%" in nvda["price_reaction"] and "下跌" in nvda["price_reaction"]
    assert nvda["price_reaction_source"].startswith("https://")

    assert len(data["last_week_economic_overrides"]) == 6
    assert len(data["last_week_earnings_actuals"]) == 3
    assert len(data["calendar_impact_overrides"]) == 5
    assert len(data["review_ready_blockers"]) >= 2
    assert any("新聞窗口尚未封口" in x for x in data["review_ready_blockers"])

    builder = (ROOT / "simulation-lab" / "runner" / "build_review_html.py").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "tac-simulation-lab.yml").read_text(encoding="utf-8")
    assert "key-level-row" in builder
    for label in ("第二支撐", "第一支撐", "中樞", "第一壓力", "第二壓力"):
        assert label in builder
    assert "if: false # Do not use repo collector" in workflow
    assert "--key-levels-live" not in workflow


    print("PASS: 11/23 fixture contract")
    print(f"PASS: 44 market indicators = {counts}")
    print("PASS: 5 focus news + 10 headlines; source timezones, updates and links complete")
    print("PASS: 6 W47 economic, 3 W47 earnings, 5 W48 display-layer overrides")
    print("PASS: news window remains open through Monday 05:25 cutoff; final build remains blocked")
    print("PASS: five same-day cash-index OHLC key-level sets and source links")
    print("PASS: W48 27 economic + 11 earnings; W47 five-star retrospective 2 + 1")
    print("PASS: NVDA actuals and first-session price reaction; no unsupported PIT Beat/Miss")


if __name__ == "__main__":
    main()
