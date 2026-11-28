#!/usr/bin/env python3
"""Synthetic integration test: Stage 1 -> Stage 2 worker submission/validation -> Stage 3."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "production" / "runner"
sys.path.insert(0, str(RUNNER))

from create_run_fixture import build, stable_run_id, write_run_files
from stage_wr_preflight import stage_wr_preflight
from accept_stage_submission import accept_stage_submission
import run_stage2
import run_stage3
import prepare_stage4_research_bundle
import run_stage4
from test_stage4_content_validation import sample as sample_stage4_content
from test_validate_chatgpt_web_observations import make_bundle

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

class Stage1To3SyntheticE2ETests(unittest.TestCase):
    def test_stage1_to_stage4_uses_one_run_and_no_live_market_or_calendar_writes(self):
        report_date = date(2026, 11, 24)
        token = os.environ.get("GITHUB_RUN_ID") or str(900000000 + os.getpid())
        run_id = stable_run_id(report_date, token)
        run_dir = ROOT / "production" / "runs" / run_id
        if run_dir.exists():
            self.fail(f"Refusing to reuse existing synthetic Run directory: {run_dir}")
        original_ref = os.environ.get("GITHUB_REF")
        original_run_id = os.environ.get("GITHUB_RUN_ID")
        os.environ["GITHUB_REF"] = "refs/heads/main"
        os.environ["GITHUB_RUN_ID"] = token
        try:
            result = build(report_date, run_id, date(2026, 11, 23))
            stage1 = write_run_files(run_dir, run_id, result, ROOT)
            context = json.loads((run_dir / "run-context.json").read_text(encoding="utf-8"))
            self.assertEqual(stage1["status"], "PASS")
            self.assertEqual(context["run_id"], run_id)
            self.assertEqual(context["report_date"], "2026-11-24")
            self.assertEqual(context["trading_date"], "2026-11-23")

            wr = stage_wr_preflight("STAGE_2", context)
            sample_data = json.loads((ROOT / "production/testdata/report-data-2026-11-24.json").read_text(encoding="utf-8"))
            synthetic_seed = copy.deepcopy(json.loads((run_dir / "stage1-fixture.json").read_text(encoding="utf-8")))
            # Keep current Main source policy/URLs from the blank-first Stage 1 fixture;
            # import only synthetic numeric values from the historical test fixture.
            for group in ("global_markets", "bonds", "fx", "energy", "metals", "risk"):
                for name, item in synthetic_seed[group].items():
                    old_source = (sample_data.get(group, {}).get(name) or {}).get("source") or {}
                    source = item.setdefault("source", {})
                    for field in ("close_value", "history_close", "score_value", "backup_source_score_value",
                                  "daily_change_percent", "history_change", "band"):
                        if old_source.get(field) is not None:
                            source[field] = old_source[field]
            for name, source in synthetic_seed["sector_sources"].items():
                old_source = (sample_data.get("sector_sources") or {}).get(name) or {}
                for field in ("history_close", "history_change"):
                    if old_source.get(field) is not None:
                        source[field] = old_source[field]
            bundle = make_bundle(synthetic_seed)
            for row in bundle["observations"]:
                if row.get("group") in ("energy", "metals"):
                    row["contract_label"] = sample_data[row["group"]][row["name"]].get("contract_label")
            bundle.update({
                "schema_version": "1.1",
                "run_id": run_id,
                "stage1_receipt_sha256": digest(run_dir / "stage1-receipt.json"),
                "run_context_sha256": digest(run_dir / "run-context.json"),
                "stage1_fixture_sha256": digest(run_dir / "stage1-fixture.json"),
                "stage2_wr_sha256": wr["wr_sha256"],
            })
            bundle["fedwatch"] = {
                "status": "SOURCE_NO_DATA",
                "source_name": "Investing.com Fed Rate Monitor",
                "source_url": "https://www.investing.com/central-banks/fed-rate-monitor",
                "report_date": context["report_date"],
                "trading_date": context["trading_date"],
                "captured_at_utc": bundle["captured_at_utc"],
                "target_meeting": None,
                "current_target_range": None,
                "updated_at_tw": None,
                "probabilities": [],
                "web_reader_ref": None,
                "web_line_start": None,
                "web_line_end": None,
                "reason": "Synthetic E2E fixture; no live FedWatch read was performed.",
                "stage2_wr_sha256": wr["wr_sha256"],
            }
            observation_path = run_dir / "market-history-web-observations.json"
            observation_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            submitted = accept_stage_submission(run_dir, "STAGE_2")
            self.assertEqual(submitted["status"], "SUBMITTED")
            state = json.loads((run_dir / "run-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["stages"]["STAGE_2"]["status"], "SUBMITTED")

            with patch.object(run_stage2, "append_chart3_sp500_increment", return_value={"status": "SKIPPED_SYNTHETIC_E2E"}):
                with patch.object(sys, "argv", ["run_stage2.py", "--run-dir", str(run_dir.relative_to(ROOT))]):
                    run_stage2.main()

            state = json.loads((run_dir / "run-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["stages"]["STAGE_2"]["status"], "PASS")
            stage2_receipt = json.loads((run_dir / "stage2-market-snapshot-receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(stage2_receipt["run_id"], run_id)
            self.assertEqual(stage2_receipt["row_count"], 44)
            self.assertEqual(stage2_receipt["pending_count"], 0)

            with patch.object(sys, "argv", ["run_stage3.py", "--run-dir", str(run_dir.relative_to(ROOT))]):
                run_stage3.main()

            state = json.loads((run_dir / "run-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["stages"]["STAGE_3"]["status"], "PASS")
            stage3_receipt = json.loads((run_dir / "stage3-calendar-receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(stage3_receipt["run_id"], run_id)
            self.assertEqual(stage3_receipt["current_week"]["week_id"], "2026-W48")
            self.assertEqual(state["last_passed_stage"], "STAGE_3")

            with patch.object(sys, "argv", ["prepare_stage4_research_bundle.py", "--run-dir", str(run_dir.relative_to(ROOT))]):
                prepare_stage4_research_bundle.main()
            bundle_receipt = json.loads((run_dir / "stage4-research-bundle-receipt.json").read_text(encoding="utf-8"))
            stage4_wr = stage_wr_preflight("STAGE_4", context)
            wr_path = ROOT / "production" / "stages" / "STAGE_4_NEWS_ANALYSIS.md"
            wr_text = wr_path.read_bytes().decode("utf-8")
            capture = {
                "schema_version": "1.0",
                "status": "AWAITING_EDITORIAL_INPUT",
                "stage4_work_instructions": {
                    "path": "production/stages/STAGE_4_NEWS_ANALYSIS.md",
                    "sha256": stage4_wr["wr_sha256"],
                    "git_blob_sha": stage4_wr["wr_git_blob_sha"],
                    "full_text": wr_text,
                },
                "run_id": run_id,
                "report_date": context["report_date"],
                "trading_date": context["trading_date"],
                "market_snapshot_sha256": bundle_receipt["market_snapshot_sha256"],
                "stage3_receipt_sha256": digest(run_dir / "stage3-calendar-receipt.json"),
                "stage2_status": stage2_receipt["status"],
                "stage2_pending_rows": stage2_receipt.get("pending_rows", []),
                "capture_trigger": {"event_name": "synthetic_e2e", "dispatch_mode": "synthetic", "workflow_run_id": token},
            }
            (run_dir / "capture-stage-receipt.json").write_text(json.dumps(capture, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")

            editorial = sample_stage4_content()
            editorial.update({
                "run_id": run_id,
                "report_date": context["report_date"],
                "trading_date": context["trading_date"],
                "market_snapshot_sha256": bundle_receipt["market_snapshot_sha256"],
                "research_bundle_sha256": bundle_receipt["bundle_sha256"],
                "stage3_receipt_sha256": digest(run_dir / "stage3-calendar-receipt.json"),
                "stage4_wr_sha256": stage4_wr["wr_sha256"],
                "news_cutoff_taipei": "2026-11-24 05:25",
                "sentiment": "Fear & Greed FGScore 備援 17；此為合成 E2E 測試敘述，不代表即時市場判斷。",
            })
            for item in editorial["focus_news"] + editorial["headlines"]:
                item["published_at_tw"] = "2026-11-23 13:00"
                item["published_at_source"] = "Nov 23, 2026 1:00 PM"
                item["updated_at_source"] = "Nov 23, 2026 1:10 PM"
            editorial["political_scan"]["checked_at"] = "2026-11-24T05:00:00+08:00"
            editorial["market_analysis"]["markets"]["paragraphs"] = [
                "合成市場分析：Fear & Greed FGScore 備援 17；內容僅驗證同一 Run 的分析交接。"
            ]
            for layer in editorial["market_analysis"].values():
                for source in layer["sources"]:
                    source["checked_at"] = "2026-11-24T05:00:00+08:00"
            editorial_path = run_dir / "stage4-editorial-content.json"
            editorial_path.write_text(json.dumps(editorial, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
            submitted4 = accept_stage_submission(run_dir, "STAGE_4")
            self.assertEqual(submitted4["status"], "SUBMITTED")

            with patch.object(sys, "argv", ["run_stage4.py", "--run-dir", str(run_dir.relative_to(ROOT))]):
                run_stage4.main()
            state = json.loads((run_dir / "run-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["stages"]["STAGE_4"]["status"], "PASS")
            self.assertEqual(state["last_passed_stage"], "STAGE_4")
            stage4_receipt = json.loads((run_dir / "stage4-analysis-receipt.json").read_text(encoding="utf-8"))
            self.assertTrue(stage4_receipt["market_snapshot_unchanged"])
            self.assertEqual(stage4_receipt["editorial_run_binding"]["run_id"], run_id)
        finally:
            import shutil
            shutil.rmtree(run_dir, ignore_errors=True)
            if original_ref is None:
                os.environ.pop("GITHUB_REF", None)
            else:
                os.environ["GITHUB_REF"] = original_ref
            if original_run_id is None:
                os.environ.pop("GITHUB_RUN_ID", None)
            else:
                os.environ["GITHUB_RUN_ID"] = original_run_id

if __name__ == "__main__":
    unittest.main()
