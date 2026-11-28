import json
import tempfile
import unittest
from pathlib import Path

import accept_stage_submission as acceptor
from run_state import initial_run_state, transition_state


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_run(root):
    run_id = "TAC-2026-11-30-123456-1"
    run = root / "production" / "runs" / run_id
    context = {
        "run_id": run_id, "report_date": "2026-11-30",
        "production_date": "2026-11-28", "trading_date": "2026-11-27",
        "main_commit_sha": "1" * 40, "workflow_run_id": "123456",
    }
    put(run / "run-context.json", context)
    stage1_receipt = {"status": "PASS", "run_id": run_id,
                      "report_date": context["report_date"],
                      "trading_date": context["trading_date"]}
    state = initial_run_state(context, stage1_receipt, "a" * 64,
                              now="2026-11-28T00:00:00Z")
    put(run / "run-state.json", state)
    return run, context


def mark_stage2_and_stage3_pass(run):
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
        expected_status="RUNNING", new_status="PASS",
        receipt_path=f"production/runs/{run.name}/stage3-calendar-receipt.json",
        now="2026-11-28T00:05:00Z")
    put(state_path, state)


class AcceptStageSubmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.run, self.context = make_run(self.root)
        self.patcher = __import__("unittest").mock.patch.object(acceptor, "ROOT", self.root)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.temp.cleanup()

    def test_stage2_acceptance_checks_only_run_identity_and_dates(self):
        payload = {
            "run_id": self.context["run_id"],
            "report_date": self.context["report_date"],
            "trading_date": self.context["trading_date"],
            "observations": [{"group": "partial", "name": "incomplete"}],
        }
        put(self.run / "market-history-web-observations.json", payload)
        result = acceptor.accept_stage_submission(self.run, "STAGE_2")
        state = json.loads((self.run / "run-state.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "SUBMITTED")
        self.assertEqual(state["stages"]["STAGE_2"]["status"], "SUBMITTED")

    def test_stage2_corrected_submission_can_be_reaccepted_before_processing(self):
        artifact = self.run / "market-history-web-observations.json"
        payload = {"run_id": self.context["run_id"],
                   "report_date": self.context["report_date"],
                   "trading_date": self.context["trading_date"]}
        put(artifact, payload)
        acceptor.accept_stage_submission(self.run, "STAGE_2")
        payload["revision"] = 2
        put(artifact, payload)
        result = acceptor.accept_stage_submission(self.run, "STAGE_2")
        state = json.loads((self.run / "run-state.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "SUBMITTED")
        self.assertEqual(state["stages"]["STAGE_2"]["status"], "SUBMITTED")
        self.assertEqual(state["stages"]["STAGE_2"]["attempt"], 2)

    def test_stage2_rejects_artifact_from_another_run(self):
        put(self.run / "market-history-web-observations.json", {
            "run_id": "TAC-OTHER-RUN",
            "report_date": self.context["report_date"],
            "trading_date": self.context["trading_date"],
        })
        with self.assertRaisesRegex(ValueError, "run_id"):
            acceptor.accept_stage_submission(self.run, "STAGE_2")

    def test_stage4_acceptance_checks_run_identity_after_stage3_completes(self):
        mark_stage2_and_stage3_pass(self.run)
        put(self.run / "stage4-editorial-content.json", {
            "run_id": self.context["run_id"],
            "report_date": self.context["report_date"],
            "trading_date": self.context["trading_date"],
        })
        result = acceptor.accept_stage_submission(self.run, "STAGE_4")
        state = json.loads((self.run / "run-state.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "SUBMITTED")
        self.assertEqual(state["stages"]["STAGE_4"]["status"], "SUBMITTED")

    def test_stage4_rejects_wrong_run_identity(self):
        mark_stage2_and_stage3_pass(self.run)
        put(self.run / "stage4-editorial-content.json", {
            "run_id": "TAC-OTHER-RUN",
            "report_date": self.context["report_date"],
            "trading_date": self.context["trading_date"],
        })
        with self.assertRaisesRegex(ValueError, "run_id"):
            acceptor.accept_stage_submission(self.run, "STAGE_4")


if __name__ == "__main__":
    unittest.main()
