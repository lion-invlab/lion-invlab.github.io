from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import stage_wr_preflight
from run_stage2 import validate_stage2_worker_wr_attestation

class StageWRPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.rel=stage_wr_preflight.STAGE_WR_PATHS["STAGE_3"]
        target=self.root/self.rel
        target.parent.mkdir(parents=True)
        target.write_text("# Stage 3 rules\nRead calendar only.\n",encoding="utf-8")
        self.raw=target.read_bytes()
        self.root_patch=patch.object(stage_wr_preflight,"ROOT",self.root)
        self.root_patch.start()

    def tearDown(self):
        self.root_patch.stop()
        self.tmp.cleanup()

    def test_stage1_to_4_read_full_wr_without_git_or_sha_pin(self):
        with patch.object(stage_wr_preflight,"_git_blob",side_effect=AssertionError("must not call git")):
            result=stage_wr_preflight.stage_wr_preflight("STAGE_3",{"governance":{}})
        self.assertEqual(result["status"],"PASS")
        self.assertTrue(result["wr_loaded"])
        self.assertEqual(result["wr_bytes_read"],len(self.raw))
        self.assertTrue(result["rules_text_loaded"])
        self.assertNotIn("wr_git_blob_sha",result)
        self.assertNotIn("wr_sha256",result)

    def test_missing_wr_blocks_work(self):
        (self.root/self.rel).unlink()
        with self.assertRaises(SystemExit):
            stage_wr_preflight.stage_wr_preflight("STAGE_3")

    def test_empty_wr_blocks_work(self):
        (self.root/self.rel).write_bytes(b"")
        with self.assertRaises(SystemExit):
            stage_wr_preflight.stage_wr_preflight("STAGE_3")

    def test_stage2_worker_does_not_need_wr_hash_attestation(self):
        evidence={"wr_path":stage_wr_preflight.STAGE_WR_PATHS["STAGE_2"],"wr_loaded":True}
        result=validate_stage2_worker_wr_attestation({},evidence)
        self.assertEqual(result["status"],"LOADED")
        self.assertTrue(result["wr_loaded"])

    def test_upstream_receipt_sha_is_not_a_handoff_gate(self):
        receipt={"run_id":"TAC-2026-11-28-123-1"}
        context={"run_id":"TAC-2026-11-28-123-1","governance":{}}
        result=stage_wr_preflight.require_stage_wr_receipt(receipt,"STAGE_2",context)
        self.assertEqual(result["status"],"LOADED")
        self.assertEqual(result["stage"],"STAGE_2")

    def test_cross_run_receipt_is_still_rejected(self):
        with self.assertRaisesRegex(SystemExit,"different Run"):
            stage_wr_preflight.require_stage_wr_receipt(
                {"run_id":"TAC-OTHER"},"STAGE_2",{"run_id":"TAC-2026-11-28-123-1"})

    def test_stage5_and_stage6_keep_governance_pin(self):
        path=stage_wr_preflight.STAGE_WR_PATHS["STAGE_5"]
        target=self.root/path
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text("# Stage 5 QA\n",encoding="utf-8")
        blob="a"*40
        context={"main_commit_sha":"commit","governance":{"commit_sha":"commit","blob_shas":{path:blob}}}
        with patch.object(stage_wr_preflight,"_git_blob",side_effect=[blob,blob]):
            result=stage_wr_preflight.stage_wr_preflight("STAGE_5",context)
        self.assertEqual(result["status"],"PASS")
        self.assertEqual(result["stage1_pinned_git_blob_sha"],blob)

    def test_unknown_stage_blocks(self):
        with self.assertRaises(ValueError):
            stage_wr_preflight.stage_wr_preflight("STAGE_7")

if __name__=="__main__": unittest.main()
