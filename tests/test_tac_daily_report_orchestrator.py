from __future__ import annotations

import tempfile
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
            self.assertEqual(
                orchestrator.git_blob_sha(path),
                "f3c9a9c3e9c2e8b5e7f2a9b8a6e2c8c6c9a0b1c2" if False else
                orchestrator.hashlib.sha1(b"blob 3\\0TAC").hexdigest(),
            )

    def test_report_week_and_previous_week(self):
        self.assertEqual(orchestrator.iso_week_id(date(2026, 11, 2)), "2026-W45")
        self.assertEqual(orchestrator.previous_iso_week_id(date(2026, 11, 2)), "2026-W44")

    def test_weekend_is_not_a_production_day(self):
        with self.assertRaisesRegex(ValueError, "週末"):
            orchestrator.verify_master(date(2026, 11, 1))

    def test_full_mode_requires_all_non_calendar_modules(self):
        args = SimpleNamespace(
            market_snapshot=None, news_json=None, analysis_json=None,
            full_page_renderer=None,
        )
        blockers = orchestrator.full_mode_blockers(args)
        self.assertEqual(len(blockers), 4)
        self.assertTrue(any("新聞" in item for item in blockers))
        self.assertTrue(any("完整早報 HTML" in item for item in blockers))

    def test_current_wr_version_is_38(self):
        self.assertEqual(orchestrator.read_wr_version(), "3.8")

    def test_approved_monday_master_sha_matches_manifest(self):
        mode, template, sha = orchestrator.verify_master(date(2026, 11, 2))
        self.assertEqual(mode, "monday")
        self.assertTrue(template.is_file())
        self.assertEqual(len(sha), 40)


if __name__ == "__main__":
    unittest.main()
