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
                "paragraphs": [f"{title}｜測試分析內容。", f"{title}｜條件與風險。"],
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
        for node, (key, title) in zip(container.select(":scope > .market-analysis-layer"), EXPECTED):
            content = node.select_one(".market-analysis-content")
            assert len(content.find_all("p", recursive=False)) == 3
            assert title in content.get_text(" ", strip=True)
            link = content.select_one("a")
            assert link and link["href"] == "https://example.com/source"
            assert "noopener" in link.get("rel", [])


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
    test_builder_rejects_invalid_source_url_and_missing_timestamp()
    print("PASS: five-layer market analysis mother slots, evidence binding and fail-closed tests")
