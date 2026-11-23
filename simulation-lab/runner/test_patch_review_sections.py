#!/usr/bin/env python3
"""Tests proving summary/analysis edits do not rebuild unrelated review sections."""
from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

from bs4 import BeautifulSoup

from patch_review_sections import patch_section

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "simulation-lab" / "baseline"
FIXTURE = ROOT / "simulation-lab" / "fixtures" / "report-data-2026-11-23.json"
MANIFEST = ROOT / "simulation-lab" / "baseline" / "mother-template-manifest.json"
PREVIEW = ROOT / "preview" / "2026-11-23-simulation.html"


def run_patch(section: str, mother_name: str) -> tuple[dict, BeautifulSoup]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        html_in = tmp_path / "input.html"
        html_out = tmp_path / "output.html"
        receipt_path = tmp_path / "receipt.json"
        html_in.write_bytes((BASELINE / mother_name).read_bytes())
        if section == "summary":
            # Seed a legacy visible source disclosure to prove the local patch removes it.
            mother_soup = BeautifulSoup(html_in.read_bytes(), "lxml")
            card = mother_soup.select_one("#overview > section.grid.two > article.card.bluf")
            details = mother_soup.new_tag("details", attrs={"class": "source-details"})
            summary_tag = mother_soup.new_tag("summary")
            summary_tag.string = "資料來源"
            source_box = mother_soup.new_tag("div", attrs={"class": "source"})
            source_link = mother_soup.new_tag("a", href="https://example.com/summary-source")
            source_link.string = "舊版總結來源"
            source_box.append(source_link)
            details.append(summary_tag)
            details.append(source_box)
            card.append(details)
            standalone_source = mother_soup.new_tag("div", attrs={"class": "source"})
            standalone_source.string = "舊版總結來源文字"
            card.append(standalone_source)
            html_in.write_text(str(mother_soup), encoding="utf-8")
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        if section == "summary":
            fixture["summary_title"] = "測試總結標題：市場風險重新定價"
            fixture["summary_points"][0]["text"] = "只更新總結文字，不重新擷取行情、新聞或行事曆。"
            # Monday mother has three summary slots; weekday mother has five.
            if mother_name == "weekday-mother-template.html":
                fixture["summary_points"].extend([
                    {"label": "測試補充一｜", "text": "週二至週五母版第五槽位測試文字。"},
                    {"label": "測試補充二｜", "text": "週二至週五母版第五槽位測試文字。"},
                ])
        fixture_path = tmp_path / "fixture.json"
        fixture_path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
        result = patch_section(html_in, fixture_path, MANIFEST, section, html_out, receipt_path, test_only=True)
        assert result["status"] == "PASS"
        assert result["non_target_dom_unchanged"] is True
        assert result["full_report_rebuild"] is False
        assert result["market_data_refresh"] is False
        assert result["news_refresh"] is False
        assert result["calendar_refresh"] is False
        output = BeautifulSoup(html_out.read_bytes(), "lxml")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert receipt["output_html_sha256"] == result["output_html_sha256"]
        return result, output


def test_summary_patch_is_local_on_both_mothers():
    for mother in ("monday-mother-template.html", "weekday-mother-template.html"):
        result, soup = run_patch("summary", mother)
        assert soup.select_one("#overview h1").get_text(" ", strip=True) == "測試總結標題：市場風險重新定價"
        assert soup.select_one("#market-analysis")
        assert soup.select_one("#sentiment")
        assert soup.select_one("#fed .fc-fomc-weekly-events")
        summary_card = soup.select_one("#overview > section.grid.two > article.card.bluf")
        assert summary_card.select("a, details.source-details, details.market-analysis-source-details, .source, .source-list, .summary-source, .summary-sources, p.market-analysis-sources") == []
        assert "資料來源" not in summary_card.get_text(" ", strip=True)
        assert "舊版總結來源文字" not in summary_card.get_text(" ", strip=True)


def test_last_week_nvda_consensus_overlay_is_local_and_evidence_backed():
    assert PREVIEW.is_file(), "committed 11/23 preview is required as the real NVDA card DOM fixture"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        html_in = tmp_path / "input.html"
        html_out = tmp_path / "output.html"
        receipt_path = tmp_path / "receipt.json"
        mother_soup = BeautifulSoup((BASELINE / "monday-mother-template.html").read_bytes(), "lxml")
        preview_soup = BeautifulSoup(PREVIEW.read_bytes(), "lxml")
        nvda_card = next(
            card for card in preview_soup.select("#last-week-earnings details.earnings-accordion.five-star-earnings")
            if "NVDA" in (card.select_one(".earnings-company-sub").get_text(" ", strip=True) if card.select_one(".earnings-company-sub") else "")
        )
        target_list = mother_soup.select_one("#last-week-earnings .earnings-accordion-list")
        assert target_list is not None
        target_list.append(copy.deepcopy(nvda_card))
        html_in.write_text(str(mother_soup), encoding="utf-8")
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        fixture_path = tmp_path / "fixture.json"
        fixture_path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")

        result = patch_section(
            html_in, fixture_path, MANIFEST, "last_week_earnings",
            html_out, receipt_path, test_only=True,
        )
        assert result["status"] == "PASS"
        assert result["non_target_dom_unchanged"] is True
        assert result["full_report_rebuild"] is False
        assert result["market_data_refresh"] is False
        assert result["news_refresh"] is False
        assert result["calendar_refresh"] is False

        output = BeautifulSoup(html_out.read_bytes(), "lxml")
        card = next(
            item for item in output.select("#last-week-earnings details.earnings-accordion.five-star-earnings")
            if "NVDA" in (item.select_one(".earnings-company-sub").get_text(" ", strip=True) if item.select_one(".earnings-company-sub") else "")
        )
        assert card.get("data-consensus-overlay") == "sim14-w47-yahoo"
        eps_card = next(x for x in card.select(".earnings-actual-card") if x.select_one(".earnings-actual-card-title").get_text(" ", strip=True) == "EPS")
        revenue_card = next(x for x in card.select(".earnings-actual-card") if x.select_one(".earnings-actual-card-title").get_text(" ", strip=True) == "營收")
        assert any(x.get_text(" ", strip=True) == "US$2.47" for x in eps_card.select(".earnings-actual-line strong"))
        assert any(x.get_text(" ", strip=True) == "US$108.73B" for x in revenue_card.select(".earnings-actual-line strong"))
        assert "beat" in eps_card.get("class", [])
        assert "beat" in revenue_card.get("class", [])
        assert "beat" in eps_card.select_one(".earnings-actual-status").get("class", [])
        assert "beat" in revenue_card.select_one(".earnings-actual-status").get("class", [])
        assert eps_card.select_one(".earnings-actual-status").get_text(" ", strip=True) == "優於預期"
        assert revenue_card.select_one(".earnings-actual-status").get_text(" ", strip=True) == "優於預期"
        assert "非嚴格同口徑" in eps_card.select_one(".earnings-actual-note").get_text(" ", strip=True)
        assert "非嚴格同口徑" in revenue_card.select_one(".earnings-actual-note").get_text(" ", strip=True)
        judgment = next(
            x.select_one(".earnings-detail-value") for x in card.select(".earnings-detail-field")
            if x.select_one("label") and x.select_one("label").get_text(" ", strip=True) == "財報判讀"
        ).get_text(" ", strip=True)
        assert "9.26%" in judgment and "6.50%" in judgment and "-2.89%" in judgment
        sources = next(
            x.select_one(".earnings-detail-value") for x in card.select(".earnings-detail-field")
            if x.select_one("label") and x.select_one("label").get_text(" ", strip=True) == "來源"
        )
        assert sources.select_one('a[href="https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Announces-Financial-Results-for-Third-Quarter-Fiscal-2027/"]')
        assert sources.select_one('a[href="https://finance.yahoo.com/quote/NVDA/analysis/"]')
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        overlay = receipt["internal_receipt"]
        assert overlay["status"] == "PASS" and overlay["judgment_audit"] == "PASS"
        assert overlay["raw_response_sha256"] == "5a20857e65c628b2ce0236b48a1414e8b361eef6e90c446a875b8ed1e3773a2a"
        assert overlay["non_target_cards_unchanged"] is True
        assert receipt["output_html_sha256"] == result["output_html_sha256"]


def test_production_paths_are_confined_to_simulation_output():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        html_in = tmp_path / "input.html"
        html_in.write_text("<html><body></body></html>", encoding="utf-8")
        try:
            patch_section(
                html_in, FIXTURE, MANIFEST, "summary",
                tmp_path / "output.html", tmp_path / "receipt.json",
            )
        except ValueError as exc:
            assert "input review HTML must remain inside" in str(exc)
        else:
            raise AssertionError("production local patcher accepted an HTML input outside simulation-lab/output")

    output_root = ROOT / "simulation-lab" / "output" / "candidate-validation"
    same_path = output_root / "same.html"
    try:
        patch_section(
            same_path, FIXTURE, MANIFEST, "summary",
            output_root / "result.html", same_path,
        )
    except ValueError as exc:
        assert "three distinct paths" in str(exc)
    else:
        raise AssertionError("production local patcher accepted colliding input and receipt paths")


def test_market_analysis_patch_hides_sources_but_keeps_internal_receipt():
    for mother in ("monday-mother-template.html", "weekday-mother-template.html"):
        result, soup = run_patch("market_analysis", mother)
        container = soup.select_one("#market-analysis")
        assert len(container.select(":scope > .market-analysis-layer")) == 5
        for content in container.select(".market-analysis-content"):
            assert content.find_all("p", recursive=False)
            assert content.select_one("a") is None
            assert content.select_one("details.market-analysis-source-details") is None
            assert "資料來源" not in content.get_text(" ", strip=True)
        layers = result["internal_receipt"]["layers"]
        assert len(layers) == 5
        assert all(layer["source_count"] > 0 for layer in layers)
        assert all(layer["sources"] for layer in layers)
        assert all(all(src.get("label") and src.get("url") and src.get("status") and (src.get("published_at") or src.get("checked_at")) for src in layer["sources"]) for layer in layers)


if __name__ == "__main__":
    test_summary_patch_is_local_on_both_mothers()
    test_market_analysis_patch_hides_sources_but_keeps_internal_receipt()
    test_last_week_nvda_consensus_overlay_is_local_and_evidence_backed()
    test_production_paths_are_confined_to_simulation_output()
    print("PASS: local summary/analysis/W47 earnings patching, unchanged non-target DOM, internal evidence retention and simulation-only output guard")
