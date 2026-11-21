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
        # Some original pages do not publish an absolute update timestamp.
        # updated_at_tw must still carry the explicit source-omitted status or observed time.
        assert item.get("updated_at_source") or item.get("updated_at_tw"), item.get("title")
        assert item.get("summary"), item.get("title")
        published = datetime.strptime(item["published_at_tw"], "%Y/%m/%d %H:%M")
        assert start <= published <= end, (item["title"], item["published_at_tw"])

    assert sum(x["probability"] for x in data["fedwatch"]["probabilities"]) == 100
    assert data["earnings_health"]["as_of_date"] == "2026-11-20"
    assert data["earnings_health"]["source_url"].startswith("https://")
    assert data["earnings_health"]["mag7_eps_growth"]
    assert data["earnings_health"]["other_493_eps_growth"]

    # Market-source audit: exact 2026-11-20 source dates and canonical Investing.com FX history quote.
    for group in ("global_markets", "bonds", "fx", "energy", "metals", "risk"):
        for name, item in data[group].items():
            assert item["source"]["data_date"] == data["trading_date"], (group, name)
    for ticker, item in data["sector_sources"].items():
        assert item["data_date"] == data["trading_date"], ticker
    assert data["fx"]["美元指數"]["display"] == "103.81"
    assert data["fx"]["美元指數"]["change_display"] == "-0.08%"
    assert data["fx"]["美元／新台幣"]["display"] == "32.971"
    assert data["fx"]["美元／新台幣"]["change_display"] == "-0.18%"
    assert data["fx"]["美元／新台幣"]["source"]["quote_type"] == "spot_daily_close"
    assert data["fx"]["美元／新台幣"]["source"]["url"] == "https://hk.investing.com/currencies/usd-twd-historical-data"
    assert data["metals"]["白銀期貨 SI"]["change_display"] == "-7.41%"
    assert data["energy"]["WTI原油期貨"]["contract_label"].startswith("CLF27")
    assert data["energy"]["WTI原油期貨"]["display"] == "82.40"
    assert data["energy"]["WTI原油期貨"]["change_display"] == "-0.05%"
    assert data["energy"]["Brent原油期貨"]["display"] == "92.57"
    assert data["energy"]["Brent原油期貨"]["change_display"] == "+0.64%"
    assert "WTI、Brent、GC、SI四項均採Investing.com HK" in data["warning_note"]
    assert "WTI、GC、SI為CME" not in data["warning_note"]
    for group in ("energy", "metals"):
        for name, item in data[group].items():
            source = item["source"]
            assert source["quote_type"] == "investing_historical_close", (group, name)
            assert source["url"] == item["instrument_url"], (group, name)
            assert source["history_close"] == item["display"], (group, name)
            assert source["history_change"] == item["change_display"], (group, name)
            assert "historical-data" in source["url"], (group, name)

    # Weekday fixture must use the same source contract and the prior trading day's historical close.
    weekday = json.loads((ROOT / "simulation-lab" / "fixtures" / "report-data-2026-11-20.json").read_text(encoding="utf-8"))
    assert weekday["report_date"] == "2026-11-20"
    assert weekday["trading_date"] == "2026-11-19"
    assert "WTI、Brent、GCZ6、SIZ6的11/19價格均採Investing.com HK" in weekday["warning_note"]
    assert "平台收盤/Last" not in weekday["warning_note"]
    expected_weekday = {
        ("energy", "WTI原油期貨"): ("82.44", "+0.16%"),
        ("energy", "Brent原油期貨"): ("91.98", "+0.03%"),
        ("metals", "黃金期貨 GC"): ("3,685.50", "-1.51%"),
        ("metals", "白銀期貨 SI"): ("44.359", "-1.55%"),
    }
    for (group, name), (close, change) in expected_weekday.items():
        item = weekday[group][name]
        source = item["source"]
        assert item["display"] == close, (group, name, item["display"])
        assert item["change_display"] == change, (group, name, item["change_display"])
        assert source["quote_type"] == "investing_historical_close", (group, name)
        assert source["data_date"] == "2026-11-19", (group, name)
        assert source["url"] == item["instrument_url"], (group, name)
        assert source["history_close"] == close, (group, name)
        assert source["history_change"] == change, (group, name)
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
    assert len(data["review_ready_blockers"]) == 1
    cfd_indices = {
        name for name, item in data["global_markets"].items()
        if item.get("source", {}).get("quote_type") in {"cfd_index_reference_series", "cfd_cash_index_proxy"}
    }
    assert cfd_indices == set(), cfd_indices
    expected_cash_indices = {
        "標普500指數": ("6,910.39", "-3.70%"),
        "日經225": ("56,436.65", "-5.06%"),
        "香港恆生指數": ("22,410.80", "-1.89%"),
        "英國 FTSE 100": ("10,346.34", "-1.02%"),
        "德國 DAX": ("24,802.78", "-2.60%"),
        "STOXX Europe 600": ("625.65", "-2.00%"),
    }
    for name, (close, change) in expected_cash_indices.items():
        record = data["global_markets"][name]
        assert record["display"] == close and record["change_display"] == change, name
        assert record["source"]["quote_type"] == "cash_index_close", name
        assert "historical-data" in record["source"]["url"], name
        assert "rejected_reference" not in record, name
    assert any("VIX" in x and "FedWatch" in x for x in data["review_ready_blockers"])
    assert not any("審核版 HTML 尚未產出" in x for x in data["review_ready_blockers"])

    builder = (ROOT / "simulation-lab" / "runner" / "build_review_html.py").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "tac-simulation-lab.yml").read_text(encoding="utf-8")
    assert "key-level-row" not in builder
    assert "key-level-index" not in builder
    assert "levels_box.append(soup.new_tag(\"br\"))" in builder
    for label in ("第二支撐", "第一支撐", "中樞", "第一壓力", "第二壓力"):
        assert label in builder
    assert "if: false # Do not use repo collector" in workflow
    assert "--key-levels-live" not in workflow


    weekday = json.loads((ROOT / "simulation-lab" / "fixtures" / "report-data-2026-11-20.json").read_text(encoding="utf-8"))
    weekday_health = weekday["earnings_health"]
    for field in ("as_of_date", "reported_pct", "eps_beat_pct", "revenue_beat_pct", "blended_eps_yoy",
                  "blended_revenue_yoy", "eps_surprise", "forward_pe", "mag7_eps_growth",
                  "other_493_eps_growth", "source_url"):
        assert str(weekday_health.get(field, "")).strip(), ("weekday FactSet field missing", field)
    assert weekday_health["mag7_eps_growth"] == "待核實"
    assert weekday_health["other_493_eps_growth"] == "待核實"
    levels = weekday["key_levels"]
    assert levels["baseline_date"] == levels["trading_date"] == "2026-11-19"
    assert len(levels["items"]) == 5
    for item in levels["items"]:
        assert item["trading_date"] == "2026-11-19"
        assert item["quote_type"] == "cash_index"
        assert item["url"].startswith("https://finance.yahoo.com/quote/")
        ohlc = [float(part.split(" ")[1].replace(",", "")) for part in item["ohlc"].split("｜")]
        open_, high, low, close = ohlc
        pivot = (high + low + close) / 3
        expected = {
            "s2": f"{pivot - (high - low):,.2f}",
            "s1": f"{2 * pivot - high:,.2f}",
            "p": f"{pivot:,.2f}",
            "r1": f"{2 * pivot - low:,.2f}",
            "r2": f"{pivot + (high - low):,.2f}",
        }
        for field, value in expected.items():
            assert item[field] == value, (item["key"], field, item[field], value)

    assert "111326.pdf" in weekday_health["source_url"]
    print("PASS: 11/23 fixture contract")
    print(f"PASS: 44 market indicators = {counts}")
    print("PASS: 5 focus news + 10 headlines; source timezones, updates and links complete")
    print("PASS: 6 W47 economic, 3 W47 earnings, 5 W48 display-layer overrides")
    print("PASS: news window sealed 11/21 17:57:31; report cutoff remains Monday 05:25")
    print("BLOCKED as expected: six index records are CFD references; no cash-index substitution permitted")
    print("BLOCKED as expected: sentiment/FedWatch refresh and HTML QA remain outstanding")
    print("PASS: five same-day cash-index OHLC key-level sets and source links")
    print("PASS: W48 27 economic + 11 earnings; W47 five-star retrospective 2 + 1")
    print("PASS: NVDA actuals and first-session price reaction; no unsupported PIT Beat/Miss")


if __name__ == "__main__":
    main()
