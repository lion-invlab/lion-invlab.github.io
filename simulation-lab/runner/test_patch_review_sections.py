#!/usr/bin/env python3
"""Tests proving summary/analysis edits do not rebuild unrelated review sections."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from bs4 import BeautifulSoup

from patch_review_sections import patch_section

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "simulation-lab" / "baseline"
FIXTURE = ROOT / "simulation-lab" / "fixtures" / "report-data-2026-11-23.json"
MANIFEST = ROOT / "simulation-lab" / "baseline" / "mother-template-manifest.json"


def run_patch(section: str, mother_name: str) -> tuple[dict, BeautifulSoup]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        html_in = tmp_path / "input.html"
        html_out = tmp_path / "output.html"
        receipt_path = tmp_path / "receipt.json"
        html_in.write_bytes((BASELINE / mother_name).read_bytes())
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        if section == "summary":
            fixture["summary_title"] = "測試總結標題：市場風險重新定價"
            fixture["summary_points"][0]["text"] = "只更新總結文字，不重新擷取行情、新聞或行事曆。"
        fixture_path = tmp_path / "fixture.json"
        fixture_path.write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
        result = patch_section(html_in, fixture_path, MANIFEST, section, html_out, receipt_path)
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


if __name__ == "__main__":
    test_summary_patch_is_local_on_both_mothers()
    test_market_analysis_patch_hides_sources_but_keeps_internal_receipt()
    print("PASS: local summary/analysis patching, unchanged non-target DOM, internal evidence retention")
