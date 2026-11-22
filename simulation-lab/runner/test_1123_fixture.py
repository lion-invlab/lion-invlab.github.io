#!/usr/bin/env python3
"""[build-tac-report:2026-11-23] Monday fixture contract plus three screenshot regression checks."""
# [build-tac-report:2026-11-23] rebuild after dated mother earnings note and HPE block-row fix.
# Trigger final 11/23 true-content build after official Treasury bond deltas and TAC timestamp provenance were corrected.
# [build-tac-report:2026-11-23] trigger full Monday rebuild after earnings/Fed mobile fixes.
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

    weekday_data = json.loads((ROOT / "simulation-lab" / "fixtures" / "report-data-2026-11-20.json").read_text(encoding="utf-8"))
    weekday_wti = weekday_data["energy"]["WTI原油期貨"]
    assert weekday_wti["display"] == weekday_wti["source"]["history_close"] == "83.21"
    assert weekday_wti["volume"] == "92.36K"
    assert weekday_wti["source"]["volume"] == 92360
    assert weekday_wti["source"]["name"].startswith("Investing.com HK")
    assert weekday_wti["instrument_url"] == weekday_wti["source"]["url"]

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
    monday_risk = data["summary_points"][1]["text"]
    assert "11/23 17:00" in monday_risk and "22:45" in monday_risk and "11/25 21:30" in monday_risk
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
    assert data["global_markets"]["法國 CAC 40"]["display"] == "7,927.75"
    assert data["global_markets"]["法國 CAC 40"]["change_display"] == "-1.89%"
    assert data["fx"]["澳幣／美元"]["display"] == "0.6617"
    assert data["fx"]["澳幣／美元"]["change_display"] == "-0.63%"
    assert data["fx"]["美元／日圓"]["display"] == "158.54"
    assert data["fx"]["美元／日圓"]["change_display"] == "-0.73%"
    assert data["sectors"]["XLB"] == "-2.19%"
    assert data["sector_sources"]["XLB"]["change_display"] == "-2.19%"
    assert data["risk"]["vix"]["source"]["quote_type"] == "cash_index_close"
    assert data["risk"]["vix"]["source"]["url"] == "https://www.investing.com/indices/volatility-s-p-500-historical-data?cid=1096487"
    assert data["metals"]["白銀期貨 SI"]["change_display"] == "-7.41%"
    assert data["metals"]["黃金期貨 GC"]["display_name"] == "黃金期貨"
    assert data["metals"]["白銀期貨 SI"]["display_name"] == "白銀期貨"
    assert data["energy"]["WTI原油期貨"]["contract_label"].startswith("CLF27")
    assert data["energy"]["WTI原油期貨"]["display"] == "83.98"
    assert data["energy"]["WTI原油期貨"]["change_display"] == "+0.93%"
    assert data["energy"]["WTI原油期貨"]["source"]["volume"] == 275340
    assert "成交量 275.34K" in data["energy"]["WTI原油期貨"]["source"]["note"]
    assert data["energy"]["WTI原油期貨"]["source"]["url"] == "https://hk.investing.com/commodities/crude-oil-historical-data?cid=1178037"
    assert data["energy"]["WTI原油期貨"]["display_name"] == "WTI 原油期貨"
    assert data["energy"]["Brent原油期貨"]["display_name"] == "Brent 原油期貨"
    assert "Investing.com WTI 期貨合約歷史數據頁所列 CLF27" in data["energy"]["WTI原油期貨"]["source"]["note"]
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
            assert "cid=" in source["url"], (group, name)

    # Weekday fixture must use the same source contract and the prior trading day's historical close.
    weekday = json.loads((ROOT / "simulation-lab" / "fixtures" / "report-data-2026-11-20.json").read_text(encoding="utf-8"))
    assert weekday["report_date"] == "2026-11-20"
    assert weekday["trading_date"] == "2026-11-19"
    assert "WTI、Brent、GCZ6、SIZ6的11/19價格均採Investing.com HK" in weekday["warning_note"]
    assert weekday["metals"]["黃金期貨 GC"]["display_name"] == "黃金期貨"
    assert weekday["metals"]["白銀期貨 SI"]["display_name"] == "白銀期貨"
    assert weekday["energy"]["WTI原油期貨"]["display_name"] == "WTI 原油期貨"
    assert weekday["energy"]["Brent原油期貨"]["display_name"] == "Brent 原油期貨"
    assert "平台收盤/Last" not in weekday["warning_note"]
    expected_weekday = {
        ("energy", "WTI原油期貨"): ("83.21", "-0.06%"),
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

    # Five-layer analysis must distinguish enacted policy, market pricing and official Fed guidance.
    analysis = data["market_analysis"]
    all_analysis_text = " ".join(
        [point["text"] for point in data["summary_points"]]
        + [paragraph for layer in analysis.values() for paragraph in layer["paragraphs"]]
    )
    for generic_phrase in ("後續觀察", "值得持續關注", "市場仍需觀察", "審慎觀望"):
        assert generic_phrase not in all_analysis_text, generic_phrase
    assert set(analysis) == {"political", "policy_industry", "macro", "markets", "strategy"}
    political = analysis["political"]
    assert "11月19日發布並生效" in political["paragraphs"][0]
    assert "既有資料中心" in political["paragraphs"][0] and "90日" in political["paragraphs"][0]
    assert political["sources"][0]["url"] == "https://www.govinfo.gov/content/pkg/FR-2026-11-19/html/2026-23529.htm"
    assert political["sources"][1]["published_at"] == "2026-11-21T16:40:00+08:00"
    assert "ukmto_warning_215-26.pdf" in political["sources"][2]["url"]
    assert "Reuters" in political["sources"][3]["label"]
    macro = analysis["macro"]
    assert "僅兩位成員主張升息25個基點" in macro["paragraphs"][0]
    assert "不是Fed已承諾的決策" in macro["paragraphs"][0]
    assert macro["sources"][1]["url"] == "https://www.federalreserve.gov/monetarypolicy/fomcminutes20261028.htm"

    # AI financing-chain analysis must be evidence-based and distinguish credit repricing from default.
    policy = analysis["policy_industry"]
    policy_text = " ".join(policy["paragraphs"])
    assert "3,900億美元" in policy_text and "多年度記憶體採購" in policy_text
    assert "1,158億美元" in policy_text and "1,076億美元" in policy_text
    assert "475億美元" in policy_text and "年增195%" in policy_text
    assert "1,020億美元" in policy_text and "自身研發" in policy_text
    assert "320億美元" in policy_text and "取得融資" in policy_text
    assert "超過其資產負債表與長期信用狀況可支持的程度" in policy_text
    assert "1,180億美元" in policy_text and "尚未支付任何保證款" in policy_text
    assert "1,050億美元" in policy_text and "4.25GW" in policy_text and "20年租約" in policy_text
    assert "FY2029" in policy_text and "3.8GW" in policy_text
    assert "810億美元" in policy_text and "64天" in policy_text and "60天" in policy_text
    assert "合計約占應收帳款70%" in policy_text and "90天至一年" in policy_text
    assert "33億美元" in policy_text and "47億美元" in policy_text
    assert "Microsoft" in policy_text and "67%" in policy_text
    assert "不等於替其全部約500億美元債務提供擔保" in policy_text
    assert any(x["url"] == "https://s201.q4cdn.com/141608511/files/doc_financials/2027/Q327/Q3FY27-CFO-Commentary.pdf" for x in policy["sources"])
    assert any(x["label"] == "NVIDIA｜FY2027 Q3 CFO Commentary（2026/11/17）" for x in policy["sources"])
    assert any(x["url"] == "https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Announces-Financial-Results-for-Third-Quarter-Fiscal-2027/" for x in policy["sources"])
    assert any(x["url"] == "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000088/nvda-20261117.htm" for x in policy["sources"])
    assert any(x["label"] == "NVIDIA｜FY2027 Q2 Form 10-Q（SEC）" for x in policy["sources"])
    assert any(x["url"] == "https://www.reuters.com/business/nvidia-turmoil-marks-end-easy-money-ai-trade-2026-11-17/" for x in policy["sources"])
    market_text = " ".join(analysis["markets"]["paragraphs"])
    assert "近15%" in market_text and "超過12%" in market_text
    assert "不能據此推論相關業者已違約或整條AI融資鏈瓦解" in market_text
    strategy_text = " ".join(analysis["strategy"]["paragraphs"])
    assert "融資展期失敗" in strategy_text and "保證條款被觸發" in strategy_text
    assert "風險重新定價" in strategy_text and "主要客戶削減長約" in strategy_text
    assert any(x["url"] == "https://www.reuters.com/legal/transactional/coreweaves-ai-contracts-lenders-financing-its-build-out-2026-10-15/" for x in analysis["strategy"]["sources"])

    scan = data["political_scan"]
    assert scan["domains_checked"] == ["us_policy", "us_china", "geopolitics", "trade_sanctions", "major_economies", "energy_resources"]
    assert scan["findings"][0]["classification"] == "formally_effective"
    assert scan["findings"][0]["source_url"] == "https://www.govinfo.gov/content/pkg/FR-2026-11-19/html/2026-23529.htm"
    assert scan["findings"][0]["published_at"] == "2026-11-19"
    assert "D:5" in scan["findings"][0]["transmission"]["policy"] and "90日" in scan["findings"][0]["transmission"]["policy"]
    assert scan["findings"][1]["published_at"] == "2026-11-21T16:40:00+08:00"
    no_forecast = [event for event in data["calendar"]["events"] if event["forecast"] is None]
    assert len(no_forecast) == 7
    assert all(event["source_notes"] for event in no_forecast)
    assert "Investing.com" in next(x for x in no_forecast if x["id"] == "current-au-flash-pmi-20261123")["source_notes"]
    assert "Investing.com" in next(x for x in no_forecast if x["id"] == "current-jp-flash-pmi-20261124")["source_notes"]
    assert "不適用" in next(x for x in no_forecast if x["id"] == "current-fed-beige-book-20261125")["source_notes"]
    assert "暫定" in next(x for x in no_forecast if x["id"] == "current-au-flash-pmi-20261123")["source_notes"]
    assert "06:00" in next(x for x in no_forecast if x["id"] == "current-au-flash-pmi-20261123")["source_notes"]
    assert "08:30" in next(x for x in no_forecast if x["id"] == "current-jp-flash-pmi-20261124")["source_notes"]
    assert "03:00" in next(x for x in no_forecast if x["id"] == "current-fed-beige-book-20261125")["source_notes"]
    assert "21:30" in next(x for x in no_forecast if x["id"] == "current-canada-seph-202609")["source_notes"]
    ecb = next(x for x in no_forecast if x["id"] == "current-ecb-account-20261028")
    assert ecb["source_url"] == "https://www.ecb.europa.eu/press/calendars/weekly/html/index.en.html"
    assert "20:30" in ecb["source_notes"]
    assert "13:00 ET" in next(x for x in no_forecast if x["id"] == "current-us-thanksgiving-market-20261126")["source_notes"]
    assert "05:00" in next(x for x in no_forecast if x["id"] == "current-fed-williams-20261123")["source_notes"]
    assert all(x["stars"] == 5 for x in previous_calendar["events"])
    assert all(x["stars"] == 5 for x in previous_earnings["events"])
    for event in current_calendar["events"] + current_earnings["events"] + previous_calendar["events"] + previous_earnings["events"]:
        assert event["source_url"].startswith("https://"), event.get("id")
    assert all(x["eps_estimate"] is None and x["revenue_estimate"] is None for x in current_earnings["events"])
    nvda = previous_earnings["events"][0]
    assert nvda["ticker"] == "NVDA"
    assert nvda["eps_actual"] == 2.7 and nvda["revenue_actual"] == 115.8
    assert "3.30%" in nvda["price_reaction"] and "下跌" in nvda["price_reaction"]
    assert nvda["price_reaction_source"].startswith("https://")

    assert len(data["last_week_economic_overrides"]) == 6
    assert len(data["last_week_earnings_actuals"]) == 3
    assert len(data["calendar_impact_overrides"]) == 4
    blockers = data["review_ready_blockers"]
    assert len(blockers) == 1, blockers
    assert all(item.startswith("PARTIAL｜") for item in blockers), blockers
    assert "W47五星財報回顧" in blockers[0] and "NVDA Q3 FY2027一筆" in blockers[0], blockers
    assert not any("W48" in item for item in blockers), blockers
    assert not any("raw_response_sha256" in item for item in blockers)
    rut = data["global_markets"]["羅素2000指數"]
    assert rut["display"] == "2,581.79" and rut["change_display"] == "-2.76%"
    assert rut["source"]["quote_type"] == "cash_index_close"
    assert rut["source"]["url"] == "https://ca.investing.com/indices/smallcap-2000-historical-data?cid=53095"
    assert rut["source"]["verified_at_tw"]
    assert "NYSE" in rut["source"]["note"] and "不使用 CFD" in rut["source"]["note"]
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
    blockers = data["review_ready_blockers"]
    assert len(blockers) == 1, blockers
    assert all(item.startswith("PARTIAL｜") for item in blockers), blockers
    assert "W47五星財報回顧" in blockers[0] and "NVDA Q3 FY2027一筆" in blockers[0], blockers
    assert not any("W48" in item for item in blockers), blockers
    assert not any("raw_response_sha256" in item for item in blockers)
    assert not any(any(term in x for term in ("VIX", "MOVE", "Fear & Greed", "FedWatch", "raw_response_sha256")) for x in data["review_ready_blockers"])
    assert any("原始HTTP response body未封存" in x and "可選證據" in x for x in data["pending_items"])
    assert not any(x.startswith("NVDA Q3 FY2027") for x in data["pending_items"])
    assert "不要求週日刷新" in data["quality_note"]
    assert "不要求週日刷新" in data["warning_note"]
    assert not any("審核版 HTML 尚未產出" in x for x in data["review_ready_blockers"])

    builder = (ROOT / "simulation-lab" / "runner" / "build_review_html.py").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "tac-simulation-lab.yml").read_text(encoding="utf-8")
    assert "key-level-row" not in builder
    assert "key-level-index" not in builder
    assert "def populate_key_levels_preserving_dom(" in builder
    assert "populate_key_levels_preserving_dom(levels_box, level_items, disclosure)" in builder
    assert "disclosure.extract()" not in builder
    assert "for child in list(levels_box.contents)" not in builder
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
    print("PASS: 17 global index rows use non-CFD source contracts")
    for bond_name, close, change in (
        ("2年期美債殖利率", "4.613%", "-16.6 bp"),
        ("10年期美債殖利率", "4.912%", "-14.0 bp"),
        ("30年期美債殖利率", "5.302%", "-9.9 bp"),
    ):
        item = data["bonds"][bond_name]
        assert item["display"] == close and item["change_display"] == change
        assert item["source"]["verification_status"] == "VERIFIED"
        assert item["source"]["verified_at_tw"] == "2026-11-22T17:48:21+08:00"
    print("PARTIAL as expected: two genuine Stage 3 data gaps remain; all 44 market observations have per-item evidence; raw HTTP body hash is optional")
    print("PASS: five same-day cash-index OHLC key-level sets and source links")
    print("PASS: W48 27 economic + 11 earnings; W47 five-star retrospective 2 + 1")
    print("PASS: NVDA actuals and first-session price reaction; no unsupported PIT Beat/Miss")


if __name__ == "__main__":
    main()
