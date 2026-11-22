#!/usr/bin/env python3
"""Regression tests for the Manifest-bound five-layer market analysis slots."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "simulation-lab" / "runner"))
import build_review_html as builder

EXPECTED = [
    ("political", "一、政治與地緣政治局勢"),
    ("policy_industry", "二、政策傳導與企業／產業鏈影響"),
    ("macro", "三、宏觀經濟傳導"),
    ("markets", "四、金融市場定價、情緒與風險"),
    ("strategy", "五、機構資金動向與投資策略"),
]


def sample_data():
    return {
        "market_analysis": {
            key: {
                "paragraphs": [
                    f"{title}｜這是一段用來驗證桌面與手機排版的合成測試文字，包含政策變化、產業傳導、經濟影響與市場定價等較長中文內容，必須在窄螢幕自然換行，不得產生水平溢位。",
                    f"{title}｜若後續條件與來源證據出現變化，應重新評估傳導方向、受影響資產、領先指標及策略失效條件；這段文字刻意拉長以測試 320px 到桌面寬度的閱讀版面。",
                ],
                "sources": [{
                    "label": "官方來源測試",
                    "url": "https://example.com/source",
                    "published_at": "2026-11-22T08:00:00+08:00",
                    "checked_at": "2026-11-22T08:10:00+08:00",
                    "status": "VERIFIED",
                }],
            }
            for key, title in EXPECTED
        },
        "political_scan": {
            "checked_at": "2026-11-22T08:10:00+08:00",
            "domains_checked": ["us_policy", "us_china", "geopolitics", "trade_sanctions", "major_economies", "energy_resources"],
            "findings": [],
            "no_material_change_note": "本測試日未發現足以改變市場定價的重大已核實政治／地緣政治變化。",
        },
    }


def load_assets(name):
    manifest = json.loads((ROOT / "simulation-lab/baseline/mother-template-manifest.json").read_text(encoding="utf-8"))
    soup = BeautifulSoup((ROOT / "simulation-lab/baseline" / name).read_text(encoding="utf-8"), "html.parser")
    return soup, manifest


def test_both_mothers_have_one_ordered_slot_between_summary_and_sentiment():
    for name in ("monday-mother-template.html", "weekday-mother-template.html"):
        soup, manifest = load_assets(name)
        container = soup.select("#market-analysis")
        assert len(container) == 1, (name, len(container))
        container = container[0]
        assert container.parent is soup.select_one("#overview")
        assert container.find_next(id="sentiment") is soup.select_one("#sentiment")
        layers = container.select(":scope > .market-analysis-layer")
        assert [x.get("data-analysis-layer") for x in layers] == [x[0] for x in EXPECTED]
        assert [x.find(["h2", "h3", "h4"], recursive=False).get_text(" ", strip=True) for x in layers] == [x[1] for x in EXPECTED]
        assert manifest["analysis_slots"]["market_analysis"]["required"] is True


def test_builder_populates_only_five_content_slots_and_preserves_mother_wrappers():
    for name in ("monday-mother-template.html", "weekday-mother-template.html"):
        soup, manifest = load_assets(name)
        container = soup.select_one("#market-analysis")
        before = [
            (tuple(node.get("class", [])), node.get("data-analysis-layer"),
             tuple(node.find(["h2", "h3", "h4"], recursive=False).attrs.items()),
             tuple(node.select_one(".market-analysis-content").attrs.items()))
            for node in container.select(":scope > .market-analysis-layer")
        ]
        receipt = builder.populate_market_analysis_preserving_dom(soup, sample_data(), manifest)
        after = [
            (tuple(node.get("class", [])), node.get("data-analysis-layer"),
             tuple(node.find(["h2", "h3", "h4"], recursive=False).attrs.items()),
             tuple(node.select_one(".market-analysis-content").attrs.items()))
            for node in container.select(":scope > .market-analysis-layer")
        ]
        assert before == after, (name, "mother wrapper/headings/slot attributes changed")
        assert receipt["layer_order"] == [x[0] for x in EXPECTED]
        assert len(receipt["layers"]) == 5
        assert receipt["visible_sources"] is False
        assert receipt["source_evidence_retained_in_receipt"] is True
        for node, (key, title), layer_receipt in zip(
            container.select(":scope > .market-analysis-layer"), EXPECTED, receipt["layers"]
        ):
            content = node.select_one(".market-analysis-content")
            assert len(content.find_all("p", recursive=False)) == 2
            assert content.select_one("details.market-analysis-source-details") is None
            assert content.select_one("a") is None
            assert "資料來源" not in content.get_text(" ", strip=True)
            assert title in content.get_text(" ", strip=True)
            assert layer_receipt["source_count"] == 1
            assert len(layer_receipt["sources"]) == 1
            assert layer_receipt["sources"][0]["url"] == "https://example.com/source"
            assert layer_receipt["sources"][0]["label"] == "官方來源測試"


def test_builder_fails_closed_on_missing_layer_or_source_evidence():
    soup, manifest = load_assets("monday-mother-template.html")
    with_error = sample_data()
    del with_error["market_analysis"]["political"]
    try:
        builder.populate_market_analysis_preserving_dom(soup, with_error, manifest)
        raise AssertionError("missing layer should fail closed")
    except ValueError as exc:
        assert "keys must be exactly" in str(exc)

    soup, manifest = load_assets("weekday-mother-template.html")
    with_error = sample_data()
    with_error["market_analysis"]["political"]["sources"] = []
    try:
        builder.populate_market_analysis_preserving_dom(soup, with_error, manifest)
        raise AssertionError("missing source evidence should fail closed")
    except ValueError as exc:
        assert "at least one evidence source" in str(exc)


def test_political_scan_requires_classification_transmission_and_three_scenarios():
    data = sample_data()
    data["political_scan"]["findings"] = [{
        "title": "政策測試事件",
        "domain": "us_policy",
        "classification": "announced_not_implemented",
        "source_url": "https://example.com/policy",
        "published_at": "2026-11-22T08:00:00+08:00",
        "checked_at": "2026-11-22T08:10:00+08:00",
        "transmission": {
            "policy": "政策已宣布但尚未實施",
            "industry": "可能影響受規範產業，實際範圍待執行細則",
            "macro": "未知",
            "markets": "市場尚未形成一致定價",
            "strategy": "維持風險控管，等待實施細則",
        },
        "scenarios": {
            key: {
                "triggers": f"{key} 情境觸發條件",
                "affected_assets": "相關產業與市場資產",
                "leading_indicators": "官方執行細則與企業公告",
                "strategy": f"{key} 情境策略",
                "invalidation": f"{key} 情境失效條件",
            }
            for key in ("baseline", "risk", "severe")
        },
    }]
    receipt = builder.validate_political_scan(data)
    assert receipt["status"] == "PASS"
    assert receipt["domains_checked"] == [
        "us_policy", "us_china", "geopolitics", "trade_sanctions",
        "major_economies", "energy_resources",
    ]
    assert receipt["policy_transmission_completeness"] == 1
    assert receipt["scenario_analysis_coverage"] == 1

    incomplete = sample_data()
    incomplete["political_scan"]["findings"] = data["political_scan"]["findings"]
    incomplete["political_scan"]["findings"][0]["scenarios"]["severe"]["invalidation"] = ""
    try:
        builder.validate_political_scan(incomplete)
        raise AssertionError("incomplete severe scenario should fail closed")
    except ValueError as exc:
        assert "scenarios.severe is incomplete" in str(exc)


def test_builder_rejects_invalid_source_url_and_missing_timestamp():
    soup, manifest = load_assets("monday-mother-template.html")
    data = sample_data()
    data["market_analysis"]["political"]["sources"][0]["url"] = "javascript:alert(1)"
    try:
        builder.populate_market_analysis_preserving_dom(soup, data, manifest)
        raise AssertionError("invalid URL should fail closed")
    except ValueError as exc:
        assert "invalid label, URL or status" in str(exc)

    soup, manifest = load_assets("monday-mother-template.html")
    data = sample_data()
    data["market_analysis"]["political"]["sources"][0].pop("published_at")
    data["market_analysis"]["political"]["sources"][0].pop("checked_at")
    try:
        builder.populate_market_analysis_preserving_dom(soup, data, manifest)
        raise AssertionError("missing source timestamp should fail closed")
    except ValueError as exc:
        assert "needs published_at or checked_at" in str(exc)


if __name__ == "__main__":
    test_both_mothers_have_one_ordered_slot_between_summary_and_sentiment()
    test_builder_populates_only_five_content_slots_and_preserves_mother_wrappers()
    test_builder_fails_closed_on_missing_layer_or_source_evidence()
    test_political_scan_requires_classification_transmission_and_three_scenarios()
    test_builder_rejects_invalid_source_url_and_missing_timestamp()
    print("PASS: five-layer market analysis mother slots, evidence binding and fail-closed tests")
