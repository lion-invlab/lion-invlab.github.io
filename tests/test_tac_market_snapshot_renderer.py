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

    def test_verified_quotes_render_values_and_sector_ranking(self):
        _, schema = snapshot_validator.load_validator()
        snapshot = snapshot_validator.sample_snapshot(schema)
        for group in ("global_indices", "sectors", "bonds", "fx", "energy", "precious_metals", "risk_indicators"):
            for index, (key, row) in enumerate(snapshot[group].items()):
                row.update({
                    "value": 100.0 + index,
                    "change": (index + 1) / 10 if index % 2 == 0 else -(index + 1) / 10,
                    "change_unit": "%",
                    "status": "verified",
                    "source": {
                        "name": "Investing.com Hong Kong",
                        "url": "https://hk.investing.com/",
                        "observed_at": "2026-11-01T09:00:00+08:00",
                        "data_date": "2026-10-30",
                        "quote_type": "historical_close",
                        "instrument": key.upper(),
                    },
                })
        sector_changes = {
            "xlk": 2.0, "xly": 1.0, "xlb": 0.0, "xlu": -1.0, "xli": 0.5,
            "xlv": -0.5, "xlf": 1.5, "xlc": 0.25, "xlre": -1.5, "xlp": 0.75, "xle": 3.0,
        }
        for key, change in sector_changes.items():
            snapshot["sectors"][key].update({"value":change,"change":change,"unit":"%","change_unit":"%"})
        snapshot["fedwatch"] = {
            "target_meeting":"2026-12-16","updated_at":"2026-11-01T08:55:00+08:00",
            "source":{"name":"CME FedWatch","url":"https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool"},
            "probabilities":[{"rate_range":"維持不變","probability":80.0},{"rate_range":"降息一碼","probability":20.0}],
            "status":"verified","notes":"Test fixture only."
        }
        monday = ROOT / "母版專區" / "TAC_母版_週一_2026-10-28_最終定版.html"
        with tempfile.TemporaryDirectory() as tmp:
            snapshot_path = Path(tmp) / "snapshot.json"
            output_path = Path(tmp) / "review.html"
            snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
            renderer.render(monday, snapshot_path, ROOT / "scripts" / "tac_html_binding_map.json", output_path, "monday")
            rendered = output_path.read_text(encoding="utf-8")
        self.assertIn("100.00", rendered)
        self.assertIn("+3.00%", rendered)
        sector_start = rendered.index('<div class="sector-list">')
        self.assertLess(rendered.index("XLE", sector_start), rendered.index("XLK", sector_start))
        self.assertIn('class="r down"', rendered)


if __name__ == "__main__":
    unittest.main()
