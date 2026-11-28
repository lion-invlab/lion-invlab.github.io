#!/usr/bin/env python3
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

class MainWorkflowContractTests(unittest.TestCase):
    def test_stage4_to_stage6_is_same_scheduled_workflow_run(self):
        workflow=(ROOT/".github/workflows/tac-production.yml").read_text(encoding="utf-8")
        self.assertIn("outputs:",workflow)
        self.assertIn("run_id: ${{ steps.resolve.outputs.run_id }}",workflow)
        self.assertIn("report_date: ${{ steps.resolve.outputs.report_date }}",workflow)
        self.assertIn("needs: [schedule-window, capture-and-calendar]",workflow)
        self.assertIn("needs['capture-and-calendar'].result == 'success'",workflow)
        self.assertIn("Resolve exact Run and wait for Stage 4 submission",workflow)
        self.assertNotIn("github.event_name == 'push' && contains(github.event.head_commit.message, '[tac-stage4-submit:')",workflow)

    def test_editorial_commit_is_not_a_workflow_trigger(self):
        workflow=(ROOT/".github/workflows/tac-production.yml").read_text(encoding="utf-8")
        self.assertNotIn('      - "production/runs/**/stage4-editorial-content.json"',workflow)
        self.assertIn("[tac-stage4-submit:<run_id>]",(ROOT/"production/contracts/HANDOFF_CONTRACT.md").read_text(encoding="utf-8"))

    def test_main_preview_is_isolated_from_simulation_root_preview(self):
        runner=(ROOT/"production/runner/run_stage6.py").read_text(encoding="utf-8")
        master=(ROOT/"production/MASTER_WR.md").read_text(encoding="utf-8")
        self.assertIn('preview/main/{report_date}',runner)
        self.assertIn('preview/main/YYYY-MM-DD-review.html',master)

    def test_pages_uses_explicit_preview_and_chart3_handoffs(self):
        pages=(ROOT/".github/workflows/pages.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:",pages)
        self.assertIn("TAC Chart 3 incremental update (main branch trigger)",pages)
        self.assertIn("TAC Chart 3 merge verified S&P 500 daily increments",pages)
        self.assertIn("TAC Chart 3 bootstrap baseline from completed run",pages)
        self.assertNotIn('      - "preview/*.html"',pages)
        self.assertNotIn('      - "data/tac-chart3/**"',pages)

    def test_chart3_resolves_exact_main_run_not_commit_marker(self):
        for name in ("tac-chart3-incremental.yml","tac-chart3-sp500-increment-merge.yml"):
            workflow=(ROOT/".github/workflows"/name).read_text(encoding="utf-8")
            self.assertIn("workflow_run_id",workflow)
            self.assertIn('"STAGE_2"',workflow)
            self.assertIn('"STAGE_3"',workflow)
            self.assertIn("resolve-main-run",workflow)
            self.assertNotIn("contains(github.event.workflow_run.head_commit.message, '[tac-stage4-submit:')",workflow)

    def test_chart3_bootstrap_shares_data_maintenance_lock(self):
        workflow=(ROOT/".github/workflows/tac-chart3-bootstrap.yml").read_text(encoding="utf-8")
        self.assertIn("group: tac-chart3-data-maintenance",workflow)

if __name__=="__main__":
    unittest.main()
