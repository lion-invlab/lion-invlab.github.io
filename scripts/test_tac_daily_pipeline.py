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
from run_tac_daily_pipeline import build_preview, scenario_for, validate_content_fragments, load_capture_bundle

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
        self.assertGreaterEqual(len(body_spans), 1)
        editorial = {
            "headline": "整合測試摘要標題",
            "body_segments": [f"整合測試摘要段落 {i + 1}" for i in range(len(body_spans))],
            "market_text": "整合測試盤面觀察",
            "core_text": "整合測試核心結論",
        }
        return {"news": news, "editorial": editorial}

    def test_monday_pipeline_produces_review_only_and_updates_report_dates(self):
        key_ohlc = {
            "dow": ("DJI", "us-30", 52383.90, 52383.90, 51563.76, 51770.31),
            "sp500": ("SPX", "us-spx-500", 7631.07, 7637.48, 7527.56, 7580.07),
            "nasdaq_composite": ("IXIC", "nasdaq-composite", 25592.49, 25673.00, 25177.33, 25437.00),
            "sox": ("SOX", "phlx-semiconductor", 10855.80, 10957.30, 10439.00, 10688.80),
            "russell_2000": ("RUT", "smallcap-2000", 2838.77, 2843.00, 2787.12, 2811.84),
        }
        global_indices = {}
        key_level_indices = {}
        for key, (ticker, slug, open_value, high_value, low_value, close_value) in key_ohlc.items():
            source = {
                "name": "Investing.com 香港站",
                "url": f"https://hk.investing.com/indices/{slug}-historical-data",
                "observed_at": "2026-11-02T05:00:00+08:00",
                "data_date": "2026-10-30",
                "quote_type": "investing_com_hk_historical_close_pct_change",
                "instrument": f"Synthetic {ticker}",
            }
            global_indices[key] = {
                "value": close_value, "unit": "index_points",
                "change": -1.0, "change_unit": "percent",
                "status": "verified", "source": source,
                "fallback_used": False, "fallback_reason": None,
                "notes": "Synthetic integration test only",
            }
            key_level_indices[key] = {
                "status": "verified",
                "ohlc": {"open": open_value, "high": high_value, "low": low_value, "close": close_value},
                "source": source,
                "notes": "Synthetic integration test only",
            }
        market_fragment = {
            "report_date": "2026-11-02",
            "trading_date": "2026-10-30",
            "global_indices": global_indices,
            "key_levels": {
                "report_date": "2026-11-02", "trading_date": "2026-10-30",
                "fetched_at": "2026-11-02T05:00:00+08:00",
                "method": "classic_pivot_p=(H+L+C)/3_s1=2P-H_r1=2P-L",
                "indices": key_level_indices,
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
                self.assertIn('content="2026-11-02" name="report-date"', rendered)
                self.assertIn("整合測試摘要標題", rendered)
                self.assertIn("測試新聞 global_focus 1", rendered)
                self.assertIn("7,580.07", rendered)
                self.assertIn("51,428.08", rendered)
                self.assertIn("基準交易日：</b>2026-10-30", rendered)
                self.assertIn("Investing.com 香港站歷史資料", rendered)
                self.assertNotIn("基準交易日：2026/10/23", rendered)
                self.assertIn("待核實", rendered)
                # Real W44/W45 databases must flow through the Monday pipeline:
                # prior-week five-star events and current-week four/five-star events.
                self.assertIn("日本央行（BOJ）利率決策及10月展望報告", rendered)
                self.assertIn("Visa", rendered)
                self.assertIn("美國 ISM 製造業 PMI（10月）", rendered)
                self.assertIn("英格蘭銀行利率決策、MPC 會議紀錄及貨幣政策報告", rendered)
                self.assertIn("Apple", rendered)
                self.assertIn("Palantir", rendered)
            finally:
                if output.exists():
                    output.unlink()
        protected_after = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in self.protected if path.exists()
        }
        self.assertEqual(protected_before, protected_after)


    def test_capture_bundle_manifest_resolves_four_date_matched_market_fragments(self):
        artifacts = ROOT / "artifacts"
        artifacts.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=artifacts) as temp:
            bundle = Path(temp)
            fragments = {
                "global-indices.json": {"report_date": "2026-11-02", "trading_date": "2026-10-30", "global_indices": {}},
                "sectors.json": {"report_date": "2026-11-02", "trading_date": "2026-10-30", "sectors": {}},
                "treasury.json": {"report_date": "2026-11-02", "trading_date": "2026-10-30", "bonds": {}},
                "secondary.json": {"report_date": "2026-11-02", "trading_date": "2026-10-30", "fx": {}, "energy": {}, "precious_metals": {}, "risk_indicators": {}},
            }
            names = []
            for name, value in fragments.items():
                (bundle / name).write_text(json.dumps(value), encoding="utf-8")
                names.append(str((bundle / name).relative_to(ROOT)))
            fedwatch = bundle / "fedwatch.json"
            fedwatch.write_text(json.dumps({"status": "pending_verification"}), encoding="utf-8")
            manifest = {
                "report_date": "2026-11-02", "trading_date": "2026-10-30",
                "market_fragments": names,
                "fedwatch_capture": str(fedwatch.relative_to(ROOT)),
            }
            (bundle / "capture_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            market_paths, fedwatch_path = load_capture_bundle(bundle, "2026-11-02", "2026-10-30")
            self.assertEqual(len(market_paths), 4)
            self.assertEqual(fedwatch_path, fedwatch.resolve())
            with self.assertRaisesRegex(ValueError, "dates do not match"):
                load_capture_bundle(bundle, "2026-11-03", "2026-11-02")

    def test_key_levels_without_same_day_ohlc_fail_closed(self):
        segments, source = __import__("run_tac_daily_pipeline").derive_key_levels(
            [{"report_date": "2026-11-02", "trading_date": "2026-10-30", "global_indices": {}}],
            "2026-11-02", "2026-10-30"
        )
        self.assertEqual(len(segments), 5)
        self.assertTrue(all("待核實" in item for item in segments))
        self.assertTrue(all(item["status"] == "pending_verification" for item in source["items"]))

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
