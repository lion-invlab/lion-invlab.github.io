from __future__ import annotations

import tempfile
import json
import subprocess
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import tac_daily_report_orchestrator as orchestrator


class DailyReportOrchestratorTests(unittest.TestCase):
    def test_git_blob_sha_matches_git_object_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.txt"
            path.write_bytes(b"TAC")
            expected = orchestrator.hashlib.sha1(b"blob 3" + bytes([0]) + b"TAC").hexdigest()
            self.assertEqual(orchestrator.git_blob_sha(path), expected)

    def test_report_week_and_previous_week(self):
        self.assertEqual(orchestrator.iso_week_id(date(2026, 11, 2)), "2026-W45")
        self.assertEqual(orchestrator.previous_iso_week_id(date(2026, 11, 2)), "2026-W44")

    def test_weekend_is_not_a_production_day(self):
        with self.assertRaisesRegex(ValueError, "週末"):
            orchestrator.verify_master(date(2026, 11, 1))

    def test_full_mode_requires_all_non_calendar_modules(self):
        args = SimpleNamespace(
            market_snapshot=None, content_json=None,
        )
        blockers = orchestrator.full_mode_blockers(args)
        self.assertEqual(len(blockers), 2)
        self.assertTrue(any("市場快照" in item for item in blockers))
        self.assertTrue(any("新聞與 AI 分析內容包" in item for item in blockers))

    def test_current_wr_version_is_310(self):
        self.assertEqual(orchestrator.read_wr_version(), "3.10")

    def test_approved_monday_master_sha_matches_manifest(self):
        mode, template, sha = orchestrator.verify_master(date(2026, 11, 2))
        self.assertEqual(mode, "monday")
        self.assertTrue(template.is_file())
        self.assertEqual(len(sha), 40)

    def test_full_mode_renders_market_only_preview_but_fails_closed_without_other_modules(self):
        import validate_tac_daily_snapshot as market_schema
        _, schema = market_schema.load_validator()
        snapshot = market_schema.sample_snapshot(schema)
        for group in ("global_indices", "sectors", "bonds", "fx", "energy", "precious_metals", "risk_indicators"):
            for key, row in snapshot[group].items():
                row.update({
                    "value": 100.0, "change": 0.25, "change_unit": "%",
                    "status": "verified",
                    "source": {
                        "name": "Investing.com Hong Kong", "url": "https://hk.investing.com/",
                        "observed_at": "2026-11-01T09:00:00+08:00", "data_date": "2026-10-30",
                        "quote_type": "historical_close", "instrument": key.upper()
                    }
                })
        snapshot["fedwatch"] = {
            "target_meeting":"2026-12-16","updated_at":"2026-11-01T08:55:00+08:00",
            "source":{"name":"CME FedWatch","url":"https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool"},
            "probabilities":[{"rate_range":"維持不變","probability":80.0},{"rate_range":"降息一碼","probability":20.0}],
            "status":"verified","notes":"Test fixture only."
        }
        with tempfile.TemporaryDirectory() as tmp:
            snapshot_path = Path(tmp) / "market.json"
            output_dir = Path(tmp) / "out"
            snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([
                sys.executable, str(orchestrator.ROOT / "scripts" / "tac_daily_report_orchestrator.py"),
                "--report-date", "2026-11-02", "--mode", "full",
                "--market-snapshot", str(snapshot_path), "--output-dir", str(output_dir)
            ], cwd=orchestrator.ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            status = json.loads((output_dir / "2026-11-02-orchestrator-status.json").read_text(encoding="utf-8"))
            self.assertFalse(status["publish_allowed"])
            self.assertTrue(Path(status["market_only_preview"]).is_file())
            self.assertTrue(any("新聞" in blocker for blocker in status["blockers"]))
            self.assertTrue(any("AI 分析" in blocker for blocker in status["blockers"]))


if __name__ == "__main__":
    unittest.main()
