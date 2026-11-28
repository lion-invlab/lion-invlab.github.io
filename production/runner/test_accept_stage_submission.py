import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import accept_stage_submission as acceptor
from run_state import initial_run_state, transition_state


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture_44():
    return {
        "global_markets": {f"index_{i}": {} for i in range(17)},
        "sectors": {f"sector_{i}": {} for i in range(11)},
        "bonds": {f"bond_{i}": {} for i in range(3)},
        "fx": {f"fx_{i}": {} for i in range(6)},
        "energy": {f"energy_{i}": {} for i in range(2)},
        "metals": {f"metal_{i}": {} for i in range(2)},
        "risk": {f"risk_{i}": {} for i in range(3)},
    }


def make_run(root):
    run_id = "TAC-2026-11-30-123456-1"
    run = root / "production" / "runs" / run_id
    context = {
        "run_id": run_id, "report_date": "2026-11-30",
        "production_date": "2026-11-28", "trading_date": "2026-11-27",
        "main_commit_sha": "1" * 40, "workflow_run_id": "123456",
    }
    put(run / "run-context.json", context)
    put(run / "stage1-fixture.json", fixture_44())
    stage1_receipt = {"status": "PASS", "run_id": run_id,
                      "report_date": context["report_date"],
                      "trading_date": context["trading_date"]}
    put(run / "stage1-receipt.json", stage1_receipt)
    state = initial_run_state(context, stage1_receipt, sha(run / "stage1-receipt.json"),
                              now="2026-11-28T00:00:00Z")
    put(run / "run-state.json", state)
    return run, context


def mark_stage2_and_stage3_pass(run, context):
    state_path = run / "run-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state = transition_state(state, stage="STAGE_2", expected_version=state["state_version"],
        expected_status="READY", new_status="RUNNING", lease_owner="test",
        lease_expires_at="2026-11-28T00:10:00Z", now="2026-11-28T00:01:00Z")
    state = transition_state(state, stage="STAGE_2", expected_version=state["state_version"],
        expected_status="RUNNING", new_status="SUBMITTED", output_sha256="a"*64,
        now="2026-11-28T00:02:00Z")
    state = transition_state(state, stage="STAGE_2", expected_version=state["state_version"],
        expected_status="SUBMITTED", new_status="PASS", output_sha256="b"*64,
        receipt_path=f"production/runs/{run.name}/stage2-market-snapshot-receipt.json",
        now="2026-11-28T00:03:00Z")
    state = transition_state(state, stage="STAGE_3", expected_version=state["state_version"],
        expected_status="READY", new_status="RUNNING", lease_owner="test",
        lease_expires_at="2026-11-28T00:10:00Z", now="2026-11-28T00:04:00Z")
    state = transition_state(state, stage="STAGE_3", expected_version=state["state_version"],
        expected_status="RUNNING", new_status="PASS", receipt_path=f"production/runs/{run.name}/stage3-calendar-receipt.json",
        now="2026-11-28T00:05:00Z")
    put(state_path, state)


class AcceptStageSubmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.run, self.context = make_run(self.root)
        self.patcher = patch.object(acceptor, "ROOT", self.root)
        self.patcher.start()
        self.wr = {"status": "PASS", "wr_sha256": "c"*64, "wr_git_blob_sha": "d"*40}

    def tearDown(self):
        self.patcher.stop()
        self.temp.cleanup()

    def test_stage2_accepts_only_exact_run_bound_44_row_bundle(self):
        fixture = json.loads((self.run / "stage1-fixture.json").read_text(encoding="utf-8"))
        rows = [{"group": group, "name": name} for group, items in fixture.items() for name in items]
        payload = {
            "schema_version": "1.1", "run_id": self.context["run_id"],
            "report_date": self.context["report_date"], "trading_date": self.context["trading_date"],
            "stage1_receipt_sha256": sha(self.run / "stage1-receipt.json"),
            "run_context_sha256": sha(self.run / "run-context.json"),
            "stage1_fixture_sha256": sha(self.run / "stage1-fixture.json"),
            "stage2_wr_sha256": self.wr["wr_sha256"],
            "captured_at_utc": "2026-11-28T00:06:00Z",
            "observations": rows, "fedwatch": {"stage2_wr_sha256": self.wr["wr_sha256"]},
        }
        put(self.run / "market-history-web-observations.json", payload)
        with patch.object(acceptor, "stage_wr_preflight", return_value=self.wr):
            result = acceptor.accept_stage_submission(self.run, "STAGE_2")
        state = json.loads((self.run / "run-state.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "SUBMITTED")
        self.assertEqual(state["stages"]["STAGE_2"]["status"], "SUBMITTED")
        self.assertEqual(state["stages"]["STAGE_2"]["output_sha256"],
                         sha(self.run / "market-history-web-observations.json"))

    def test_stage2_reaccepts_corrected_bundle_only_before_snapshot_receipt(self):
        fixture = json.loads((self.run / "stage1-fixture.json").read_text(encoding="utf-8"))
        rows = [{"group": group, "name": name} for group, items in fixture.items() for name in items]
        payload = {
            "schema_version": "1.1", "run_id": self.context["run_id"],
            "report_date": self.context["report_date"], "trading_date": self.context["trading_date"],
            "stage1_receipt_sha256": sha(self.run / "stage1-receipt.json"),
            "run_context_sha256": sha(self.run / "run-context.json"),
            "stage1_fixture_sha256": sha(self.run / "stage1-fixture.json"),
            "stage2_wr_sha256": self.wr["wr_sha256"],
            "captured_at_utc": "2026-11-28T00:06:00Z",
            "observations": rows, "fedwatch": {"stage2_wr_sha256": self.wr["wr_sha256"]},
        }
        artifact = self.run / "market-history-web-observations.json"
        put(artifact, payload)
        with patch.object(acceptor, "stage_wr_preflight", return_value=self.wr):
            acceptor.accept_stage_submission(self.run, "STAGE_2")
            payload["observations"][0]["correction_revision"] = 2
            put(artifact, payload)
            result = acceptor.accept_stage_submission(self.run, "STAGE_2")
        state = json.loads((self.run / "run-state.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "SUBMITTED")
        self.assertEqual(state["stages"]["STAGE_2"]["status"], "SUBMITTED")
        self.assertEqual(state["stages"]["STAGE_2"]["attempt"], 2)
        self.assertEqual(state["stages"]["STAGE_2"]["output_sha256"], sha(artifact))

    def test_stage2_rejects_43_rows(self):
        payload = {"schema_version": "1.1", "run_id": self.context["run_id"],
            "report_date": self.context["report_date"], "trading_date": self.context["trading_date"],
            "stage1_receipt_sha256": sha(self.run / "stage1-receipt.json"),
            "run_context_sha256": sha(self.run / "run-context.json"),
            "stage1_fixture_sha256": sha(self.run / "stage1-fixture.json"),
            "stage2_wr_sha256": self.wr["wr_sha256"], "captured_at_utc": "2026-11-28T00:06:00Z",
            "observations": [{}]*43, "fedwatch": {"stage2_wr_sha256": self.wr["wr_sha256"]}}
        put(self.run / "market-history-web-observations.json", payload)
        with patch.object(acceptor, "stage_wr_preflight", return_value=self.wr):
            with self.assertRaisesRegex(ValueError, "exactly 44"):
                acceptor.accept_stage_submission(self.run, "STAGE_2")

    def test_stage4_accepts_exact_stage3_and_bundle_binding(self):
        mark_stage2_and_stage3_pass(self.run, self.context)
        stage3 = {"status": "PASS", "run_id": self.context["run_id"]}
        put(self.run / "stage3-calendar-receipt.json", stage3)
        bundle_sha = "e"*64
        put(self.run / "stage4-research-bundle-receipt.json", {"bundle_sha256": bundle_sha})
        market_sha = "f"*64
        put(self.run / "stage2-run-summary.json", {"market_snapshot_sha256": market_sha})
        full_wr_text = "complete Stage 4 WR test text"
        wr4 = {"status": "PASS", "wr_sha256": hashlib.sha256(full_wr_text.encode()).hexdigest(),
               "wr_git_blob_sha": "d"*40}
        put(self.run / "stage4-work-instructions.json", {
            "status": "AWAITING_EDITORIAL_INPUT", "run_id": self.context["run_id"],
            "report_date": self.context["report_date"],
            "stage4_work_instructions": {
                "path": "production/stages/STAGE_4_NEWS_ANALYSIS.md",
                "sha256": wr4["wr_sha256"], "git_blob_sha": wr4["wr_git_blob_sha"],
                "full_text": full_wr_text
            }
        })
        content = {
            "run_id": self.context["run_id"], "report_date": self.context["report_date"],
            "trading_date": self.context["trading_date"], "market_snapshot_sha256": market_sha,
            "research_bundle_sha256": bundle_sha,
            "stage3_receipt_sha256": sha(self.run / "stage3-calendar-receipt.json"),
            "stage4_wr_sha256": wr4["wr_sha256"],
        }
        put(self.run / "stage4-editorial-content.json", content)
        with patch.object(acceptor, "stage_wr_preflight", return_value=wr4):
            result = acceptor.accept_stage_submission(self.run, "STAGE_4")
        state = json.loads((self.run / "run-state.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "SUBMITTED")
        self.assertEqual(state["stages"]["STAGE_4"]["status"], "SUBMITTED")

    def test_stage4_rejects_wrong_research_bundle_sha(self):
        mark_stage2_and_stage3_pass(self.run, self.context)
        put(self.run / "stage3-calendar-receipt.json", {"status": "PASS", "run_id": self.context["run_id"]})
        put(self.run / "stage4-research-bundle-receipt.json", {"bundle_sha256": "e"*64})
        put(self.run / "stage2-run-summary.json", {"market_snapshot_sha256": "f"*64})
        full_wr_text = "complete Stage 4 WR test text"
        wr4 = {"status": "PASS", "wr_sha256": hashlib.sha256(full_wr_text.encode()).hexdigest(),
               "wr_git_blob_sha": "d"*40}
        put(self.run / "stage4-work-instructions.json", {"status": "AWAITING_EDITORIAL_INPUT",
            "run_id": self.context["run_id"], "report_date": self.context["report_date"],
            "stage4_work_instructions": {"path": "production/stages/STAGE_4_NEWS_ANALYSIS.md",
                "sha256": wr4["wr_sha256"], "git_blob_sha": wr4["wr_git_blob_sha"],
                "full_text": full_wr_text}})
        put(self.run / "stage4-editorial-content.json", {
            "run_id": self.context["run_id"], "report_date": self.context["report_date"],
            "trading_date": self.context["trading_date"], "market_snapshot_sha256": "f"*64,
            "research_bundle_sha256": "0"*64,
            "stage3_receipt_sha256": sha(self.run / "stage3-calendar-receipt.json"),
            "stage4_wr_sha256": wr4["wr_sha256"]})
        with patch.object(acceptor, "stage_wr_preflight", return_value=wr4):
            with self.assertRaisesRegex(ValueError, "research_bundle_sha256"):
                acceptor.accept_stage_submission(self.run, "STAGE_4")


if __name__ == "__main__":
    unittest.main()
