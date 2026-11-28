#!/usr/bin/env python3
import unittest
from run_state import initial_run_state, transition_state, validate_state

CTX = {
    "run_id": "TAC-2026-11-30-46069359215",
    "report_date": "2026-11-30",
    "production_date": "2026-11-28",
    "trading_date": "2026-11-27",
    "main_commit_sha": "a" * 40,
    "workflow_run_id": "46069359215",
    "started_at": "2026-11-28T04:45:00+08:00",
}
S1 = {"status": "PASS", "run_id": CTX["run_id"], "run_context_sha256": "b" * 64}


def step(state, stage, old, new, **kwargs):
    return transition_state(
        state, stage=stage, expected_version=state["state_version"],
        expected_status=old, new_status=new, now="2026-11-28T00:00:00Z", **kwargs
    )


class RunStateTests(unittest.TestCase):
    def setUp(self):
        self.state = initial_run_state(CTX, S1, "c" * 64, now="2026-11-28T00:00:00Z")

    def test_initial_state_starts_at_stage2_after_stage1_pass(self):
        self.assertEqual(self.state["stages"]["STAGE_1"]["status"], "PASS")
        self.assertEqual(self.state["stages"]["STAGE_2"]["status"], "READY")
        self.assertEqual(self.state["current_stage"], "STAGE_2")
        self.assertEqual(self.state["last_passed_stage"], "STAGE_1")

    def test_stage2_submission_does_not_unlock_stage3_until_validation_pass(self):
        state = step(self.state, "STAGE_2", "READY", "RUNNING",
                     lease_owner="chatgpt-stage2", lease_expires_at="2026-11-28T00:15:00Z")
        state = step(state, "STAGE_2", "RUNNING", "SUBMITTED", output_sha256="c" * 64)
        self.assertEqual(state["stages"]["STAGE_2"]["status"], "SUBMITTED")
        self.assertEqual(state["stages"]["STAGE_3"]["status"], "NOT_STARTED")
        state = step(state, "STAGE_2", "SUBMITTED", "PASS",
                     receipt_path="production/runs/x/stage2-market-snapshot-receipt.json",
                     output_sha256="d" * 64)
        self.assertEqual(state["stages"]["STAGE_3"]["status"], "READY")

    def test_stage3_pass_unlocks_stage4(self):
        state = step(self.state, "STAGE_2", "READY", "RUNNING",
                     lease_owner="chatgpt-stage2", lease_expires_at="2026-11-28T00:15:00Z")
        state = step(state, "STAGE_2", "RUNNING", "SUBMITTED", output_sha256="c" * 64)
        state = step(state, "STAGE_2", "SUBMITTED", "PASS",
                     receipt_path="stage2-receipt.json", output_sha256="d" * 64)
        state = step(state, "STAGE_3", "READY", "RUNNING",
                     lease_owner="github-stage3", lease_expires_at="2026-11-28T00:10:00Z")
        state = step(state, "STAGE_3", "RUNNING", "PASS",
                     receipt_path="stage3-calendar-receipt.json", output_sha256="e" * 64)
        self.assertEqual(state["stages"]["STAGE_4"]["status"], "READY")

    def test_stage4_submission_does_not_unlock_stage5_until_validation_pass(self):
        state = step(self.state, "STAGE_2", "READY", "RUNNING",
                     lease_owner="chatgpt-stage2", lease_expires_at="2026-11-28T00:15:00Z")
        state = step(state, "STAGE_2", "RUNNING", "SUBMITTED", output_sha256="c" * 64)
        state = step(state, "STAGE_2", "SUBMITTED", "PASS",
                     receipt_path="stage2-receipt.json", output_sha256="d" * 64)
        state = step(state, "STAGE_3", "READY", "RUNNING",
                     lease_owner="github-stage3", lease_expires_at="2026-11-28T00:10:00Z")
        state = step(state, "STAGE_3", "RUNNING", "PASS",
                     receipt_path="stage3-receipt.json", output_sha256="e" * 64)
        state = step(state, "STAGE_4", "READY", "RUNNING",
                     lease_owner="chatgpt-stage4", lease_expires_at="2026-11-28T00:30:00Z")
        state = step(state, "STAGE_4", "RUNNING", "SUBMITTED", output_sha256="f" * 64)
        self.assertEqual(state["stages"]["STAGE_5"]["status"], "NOT_STARTED")
        state = step(state, "STAGE_4", "SUBMITTED", "PASS",
                     receipt_path="stage4-analysis-receipt.json", output_sha256="1" * 64)
        self.assertEqual(state["stages"]["STAGE_5"]["status"], "READY")

    def test_stage5_partial_skips_stage6_and_keeps_run_partial(self):
        state = step(self.state, "STAGE_2", "READY", "RUNNING",
                     lease_owner="chatgpt-stage2", lease_expires_at="2026-11-28T00:15:00Z")
        state = step(state, "STAGE_2", "RUNNING", "SUBMITTED", output_sha256="c" * 64)
        state = step(state, "STAGE_2", "SUBMITTED", "PARTIAL",
                     receipt_path="stage2-receipt.json", output_sha256="d" * 64)
        state = step(state, "STAGE_3", "READY", "RUNNING",
                     lease_owner="github-stage3", lease_expires_at="2026-11-28T00:10:00Z")
        state = step(state, "STAGE_3", "RUNNING", "PASS",
                     receipt_path="stage3-receipt.json", output_sha256="e" * 64)
        state = step(state, "STAGE_4", "READY", "RUNNING",
                     lease_owner="chatgpt-stage4", lease_expires_at="2026-11-28T00:30:00Z")
        state = step(state, "STAGE_4", "RUNNING", "SUBMITTED", output_sha256="f" * 64)
        state = step(state, "STAGE_4", "SUBMITTED", "PASS",
                     receipt_path="stage4-receipt.json", output_sha256="1" * 64)
        state = step(state, "STAGE_5", "READY", "RUNNING",
                     lease_owner="github-stage5", lease_expires_at="2026-11-28T00:45:00Z")
        state = step(state, "STAGE_5", "RUNNING", "PARTIAL",
                     receipt_path="stage5-receipt.json", output_sha256="2" * 64)
        self.assertEqual(state["overall_status"], "PARTIAL")
        self.assertEqual(state["stages"]["STAGE_6"]["status"], "SKIPPED")

    def test_stage6_pass_means_delivered_awaiting_approval_not_published(self):
        state = step(self.state, "STAGE_2", "READY", "RUNNING",
                     lease_owner="chatgpt-stage2", lease_expires_at="2026-11-28T00:15:00Z")
        state = step(state, "STAGE_2", "RUNNING", "SUBMITTED", output_sha256="c" * 64)
        state = step(state, "STAGE_2", "SUBMITTED", "PASS",
                     receipt_path="stage2-receipt.json", output_sha256="d" * 64)
        state = step(state, "STAGE_3", "READY", "RUNNING",
                     lease_owner="github-stage3", lease_expires_at="2026-11-28T00:10:00Z")
        state = step(state, "STAGE_3", "RUNNING", "PASS",
                     receipt_path="stage3-receipt.json", output_sha256="e" * 64)
        state = step(state, "STAGE_4", "READY", "RUNNING",
                     lease_owner="chatgpt-stage4", lease_expires_at="2026-11-28T00:30:00Z")
        state = step(state, "STAGE_4", "RUNNING", "SUBMITTED", output_sha256="f" * 64)
        state = step(state, "STAGE_4", "SUBMITTED", "PASS",
                     receipt_path="stage4-receipt.json", output_sha256="1" * 64)
        state = step(state, "STAGE_5", "READY", "RUNNING",
                     lease_owner="github-stage5", lease_expires_at="2026-11-28T00:45:00Z")
        state = step(state, "STAGE_5", "RUNNING", "PASS",
                     receipt_path="stage5-receipt.json", output_sha256="2" * 64)
        self.assertEqual(state["overall_status"], "REVIEW_READY")
        state = step(state, "STAGE_6", "READY", "RUNNING",
                     lease_owner="github-stage6", lease_expires_at="2026-11-28T01:00:00Z")
        self.assertEqual(state["overall_status"], "RUNNING")
        state = step(state, "STAGE_6", "RUNNING", "PASS",
                     receipt_path="stage6-delivery-receipt.json", output_sha256="3" * 64)
        self.assertEqual(state["overall_status"], "AWAITING_APPROVAL")
        self.assertEqual(state["last_passed_stage"], "STAGE_6")

    def test_rejects_stale_state_version(self):
        with self.assertRaisesRegex(ValueError, "Stale state_version"):
            transition_state(self.state, stage="STAGE_2", expected_version=0,
                             expected_status="READY", new_status="RUNNING",
                             lease_owner="worker", lease_expires_at="2026-11-28T00:15:00Z")

    def test_rejects_wrong_expected_status(self):
        with self.assertRaisesRegex(ValueError, "Expected STAGE_2"):
            transition_state(self.state, stage="STAGE_2", expected_version=1,
                             expected_status="RUNNING", new_status="SUBMITTED",
                             output_sha256="c" * 64)

    def test_rejects_stage5_before_stage4_pass(self):
        with self.assertRaisesRegex(ValueError, "Expected STAGE_5=READY"):
            transition_state(self.state, stage="STAGE_5", expected_version=1,
                             expected_status="READY", new_status="RUNNING",
                             lease_owner="worker", lease_expires_at="2026-11-28T00:15:00Z")

    def test_recovery_from_failed_requires_explicit_flag_and_does_not_rewind_passed_stage(self):
        state = step(self.state, "STAGE_2", "READY", "RUNNING",
                     lease_owner="worker", lease_expires_at="2026-11-28T00:15:00Z")
        state = step(state, "STAGE_2", "RUNNING", "FAILED", error_code="WORKER_INTERRUPTED")
        with self.assertRaisesRegex(ValueError, "Illegal stage transition"):
            step(state, "STAGE_2", "FAILED", "READY")
        recovered = transition_state(state, stage="STAGE_2",
            expected_version=state["state_version"], expected_status="FAILED",
            new_status="READY", recovery=True)
        self.assertEqual(recovered["stages"]["STAGE_1"]["status"], "PASS")
        self.assertEqual(recovered["stages"]["STAGE_2"]["status"], "READY")

    def test_recovery_from_unvalidated_submitted_stage2_requires_explicit_flag(self):
        state = step(self.state, "STAGE_2", "READY", "RUNNING",
                     lease_owner="worker", lease_expires_at="2026-11-28T00:15:00Z")
        state = step(state, "STAGE_2", "RUNNING", "SUBMITTED",
                     input_sha256="a" * 64, output_sha256="b" * 64,
                     receipt_path="market-history-web-observations.json")
        with self.assertRaisesRegex(ValueError, "Illegal stage transition"):
            step(state, "STAGE_2", "SUBMITTED", "READY")
        recovered = transition_state(state, stage="STAGE_2",
            expected_version=state["state_version"], expected_status="SUBMITTED",
            new_status="READY", recovery=True)
        item = recovered["stages"]["STAGE_2"]
        self.assertEqual(item["status"], "READY")
        self.assertEqual(item["attempt"], 1)
        self.assertIsNone(item["output_sha256"])
        self.assertIsNone(item["receipt_path"])

    def test_partial_stage_is_terminal_and_cannot_be_reopened(self):
        state = step(self.state, "STAGE_2", "READY", "RUNNING",
                     lease_owner="worker", lease_expires_at="2026-11-28T00:15:00Z")
        state = step(state, "STAGE_2", "RUNNING", "SUBMITTED", output_sha256="c" * 64)
        state = step(state, "STAGE_2", "SUBMITTED", "PARTIAL",
                     receipt_path="stage2-receipt.json", output_sha256="d" * 64)
        with self.assertRaisesRegex(ValueError, "Illegal stage transition"):
            transition_state(state, stage="STAGE_2", expected_version=state["state_version"],
                expected_status="PARTIAL", new_status="READY", recovery=True)

    def test_rejects_more_than_one_running_stage(self):
        state = dict(self.state)
        state["stages"] = {k: dict(v) for k, v in self.state["stages"].items()}
        state["stages"]["STAGE_2"].update({"status":"RUNNING","lease_owner":"a","lease_expires_at":"x"})
        state["stages"]["STAGE_3"].update({"status":"RUNNING","lease_owner":"b","lease_expires_at":"x"})
        with self.assertRaisesRegex(ValueError, "Only one stage"):
            validate_state(state)


if __name__ == "__main__":
    unittest.main()
