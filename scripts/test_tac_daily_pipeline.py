#!/usr/bin/env python3
"""End-to-end tests for the TAC daily review-preview orchestrator."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from render_tac_market_safe import SourceTreeParser, select, spans_inside, coalesce_spans
from run_tac_daily_pipeline import build_preview, scenario_for, validate_content_fragments

class TacDailyPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template_path = ROOT / "母版專區/TAC_母版_週一_2026-10-28_最終定版.html"
        cls.template = cls.template_path.read_text(encoding="utf-8")
        cls.binding = json.loads((ROOT / "scripts/tac_html_binding_map.json").read_text(encoding="utf-8"))
        cls.protected = [ROOT / "index.html", ROOT / "TAC_WORK_RULES.md",
                         ROOT / "母版專區/TAC_母版_週一_2026-10-28_最終定版.html",
                         ROOT / "母版專區/TAC_母版_週二至週五_2026-10-28_最終定版.html"]

    def make_content_fragment(self):
        parser = SourceTreeParser(self.template)
        parser.feed(self.template)
        parser.close()
        news = {}
        for panel_key, panel_spec in self.binding["groups"]["news"]["panels"].items():
            containers = select(parser.root, panel_spec["container"])
            self.assertEqual(len(containers), 1)
            cards = select(containers[0], panel_spec["item_selector"])
            expected = 5 if panel_key == "global_focus" else 10
            self.assertEqual(len(cards), expected, f"approved template card count for {panel_key}")
            items = []
            for index, card in enumerate(cards):
                source_containers = select(card, panel_spec["sources_container_selector"])
                self.assertEqual(len(source_containers), 1)
                anchors = select(source_containers[0], panel_spec["source_selector"])
                sources = [
                    {"url": f"https://example.com/tac-test/{panel_key}/{index}/{source_index}",
                     "text": f"測試來源 {source_index + 1}"}
                    for source_index, _anchor in enumerate(anchors)
                ]
                items.append({
                    "title": f"測試新聞 {panel_key} {index + 1}",
                    "summary": "此內容僅供自動化整合測試，不代表真實市場新聞。",
                    "sources": sources,
                })
            panel = {"meta_text": "合成測試資料｜非正式新聞", "items": items}
            if len(select(containers[0], panel_spec["warning_selector"])) == 1:
                panel["window_text"] = "合成測試時間窗｜非正式資料"
            news[panel_key] = panel

        editorial_spec = self.binding["groups"]["editorial"]
        summary_container = select(parser.root, editorial_spec["summary"]["container"])[0]
        body_node = select(summary_container, editorial_spec["summary"]["body_selector"])[0]
        body_spans = coalesce_spans([
            span for span in spans_inside(body_node, parser.spans)
            if span.parent is body_node and span.text.strip()
        ])
        levels_panel = select(parser.root, editorial_spec["observation"]["levels_panel"])[0]
        levels_node = select(levels_panel, editorial_spec["observation"]["levels_text_selector"])[0]
        level_spans = coalesce_spans([
            span for span in spans_inside(levels_node, parser.spans)
            if span.parent is levels_node and span.text.strip()
        ])
        self.assertGreaterEqual(len(body_spans), 1)
        self.assertGreaterEqual(len(level_spans), 1)
        editorial = {
            "headline": "整合測試摘要標題",
            "body_segments": [f"整合測試摘要段落 {i + 1}" for i in range(len(body_spans))],
            "market_text": "整合測試盤面觀察",
            "levels_segments": [f"整合測試價位觀察 {i + 1}" for i in range(len(level_spans))],
            "core_text": "整合測試核心結論",
        }
        return {"news": news, "editorial": editorial}

    def test_monday_pipeline_produces_review_only_and_updates_report_dates(self):
        market_fragment = {
            "report_date": "2026-11-02",
            "trading_date": "2026-10-30",
            "global_indices": {
                "sp500": {
                    "value": 7000.0, "unit": "index_points",
                    "change": 1.25, "change_unit": "percent",
                    "status": "verified",
                    "source": {
                        "name": "Synthetic integration test source",
                        "url": "https://example.com/tac-test/market",
                        "observed_at": "2026-11-02T05:00:00+08:00",
                        "data_date": "2026-10-30",
                        "quote_type": "daily_close",
                        "instrument": "S&P 500",
                    },
                    "fallback_used": False, "fallback_reason": None,
                    "notes": "Synthetic test only",
                }
            },
        }
        protected_before = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in self.protected if path.exists()
        }
        output = ROOT / "review/2026-11-02-review.html"
        self.assertFalse(output.exists(), "test output must not overwrite an existing review")
        with tempfile.TemporaryDirectory() as temp:
            market_path = Path(temp) / "market-fragment.json"
            content_path = Path(temp) / "content-fragment.json"
            market_path.write_text(json.dumps(market_fragment), encoding="utf-8")
            content_path.write_text(json.dumps(self.make_content_fragment(), ensure_ascii=False), encoding="utf-8")
            try:
                result = build_preview(
                    "2026-11-02", "2026-10-30",
                    [market_path], [content_path], output,
                    "2026-11-02T05:00:00+08:00"
                )
                rendered = result.read_text(encoding="utf-8")
                self.assertIn("<title>TAC 投資早報｜2026/11/02（一）審核版</title>", rendered)
                self.assertIn('name="report-date" content="2026-11-02"', rendered)
                self.assertIn("整合測試摘要標題", rendered)
                self.assertIn("測試新聞 global_focus 1", rendered)
                self.assertIn("42,000.00", rendered)
                self.assertIn("待核實", rendered)
            finally:
                if output.exists():
                    output.unlink()
        protected_after = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in self.protected if path.exists()
        }
        self.assertEqual(protected_before, protected_after)

    def test_weekend_report_date_is_rejected(self):
        for value in ("2026-11-07", "2026-11-08"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    scenario_for(__import__("datetime").date.fromisoformat(value))

    def test_content_contract_rejects_stale_or_incomplete_sections(self):
        with self.assertRaisesRegex(ValueError, "exactly news and editorial"):
            validate_content_fragments([{"news": {}}])

if __name__ == "__main__":
    unittest.main(verbosity=2)
