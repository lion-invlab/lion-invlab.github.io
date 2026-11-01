from __future__ import annotations
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import render_tac_market_snapshot as renderer
import validate_tac_daily_snapshot as snapshot_validator


class MarketSnapshotRendererTests(unittest.TestCase):
    def test_renders_only_existing_market_slots_without_mutating_master(self):
        _, schema = snapshot_validator.load_validator()
        snapshot = snapshot_validator.sample_snapshot(schema)
        monday = ROOT / "母版專區" / "TAC_母版_週一_2026-10-28_最終定版.html"
        original = monday.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            snapshot_path = Path(tmp) / "snapshot.json"
            output_path = Path(tmp) / "review.html"
            snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
            renderer.render(monday, snapshot_path, ROOT / "scripts" / "tac_html_binding_map.json", output_path, "monday")
            rendered = output_path.read_text(encoding="utf-8")
        self.assertEqual(monday.read_text(encoding="utf-8"), original)
        self.assertIn("待核實", rendered)
        self.assertIn('id="global-markets"', rendered)
        self.assertIn('id="sentiment"', rendered)
        self.assertIn("2026/10/30", rendered)

    def test_status_class_uses_tac_red_up_green_down_convention(self):
        self.assertEqual(renderer.status_class({"status":"verified","change":1.0}), "up")
        self.assertEqual(renderer.status_class({"status":"verified","change":-1.0}), "down")
        self.assertEqual(renderer.status_class({"status":"pending_verification","change":1.0}), "warn")


if __name__ == "__main__":
    unittest.main()
