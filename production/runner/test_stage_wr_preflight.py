from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import stage_wr_preflight
from run_stage2 import validate_stage2_worker_wr_attestation

class StageWRPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.rel = stage_wr_preflight.STAGE_WR_PATHS["STAGE_3"]
        target = self.root / self.rel
        target.parent.mkdir(parents=True)
        target.write_text("# Stage 3 rules\nRead calendar only.\n", encoding="utf-8")
        self.raw = target.read_bytes()
        self.blob = "a" * 40
        self.root_patch = patch.object(stage_wr_preflight, "ROOT", self.root)
        self.git_patch = patch.object(stage_wr_preflight, "_git_blob", return_value=self.blob)
        self.root_patch.start()
        self.git_patch.start()

    def tearDown(self):
        self.git_patch.stop()
        self.root_patch.stop()
        self.tmp.cleanup()

    def test_reads_complete_wr_and_returns_sha_evidence(self):
        result = stage_wr_preflight.stage_wr_preflight("STAGE_3")
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["wr_loaded"])
        self.assertEqual(result["wr_bytes_read"], len(self.raw))
        self.assertEqual(result["wr_git_blob_sha"], self.blob)
        self.assertEqual(len(result["wr_sha256"]), 64)

    def test_missing_wr_blocks_stage(self):
        (self.root / self.rel).unlink()
        with self.assertRaises(SystemExit):
            stage_wr_preflight.stage_wr_preflight("STAGE_3")

    def test_empty_wr_blocks_stage(self):
        (self.root / self.rel).write_bytes(b"")
        with self.assertRaises(SystemExit):
            stage_wr_preflight.stage_wr_preflight("STAGE_3")

    def test_unpinned_wr_blocks_stage(self):
        context = {"main_commit_sha": "commit", "governance": {"commit_sha": "commit", "blob_shas": {}}}
        with self.assertRaises(SystemExit):
            stage_wr_preflight.stage_wr_preflight("STAGE_3", context)

    def test_valid_stage1_pinned_blob_passes(self):
        context = {"main_commit_sha": "commit", "governance": {
            "commit_sha": "commit", "blob_shas": {self.rel: self.blob}}}
        with patch.object(stage_wr_preflight, "_git_blob", side_effect=[self.blob, self.blob]):
            result = stage_wr_preflight.stage_wr_preflight("STAGE_3", context)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["stage1_pinned_git_blob_sha"], self.blob)

    def test_blob_mismatch_blocks_stage(self):
        context = {"main_commit_sha": "commit", "governance": {"commit_sha": "commit", "blob_shas": {self.rel: "b" * 40}}}
        with patch.object(stage_wr_preflight, "_git_blob", side_effect=[self.blob, "b" * 40]):
            with self.assertRaises(SystemExit):
                stage_wr_preflight.stage_wr_preflight("STAGE_3", context)

    def test_stage2_worker_requires_exact_stage_wr_sha(self):
        preflight = {"wr_sha256":"e"*64}
        result = validate_stage2_worker_wr_attestation({"stage2_wr_sha256":"e"*64},preflight)
        self.assertEqual(result["status"],"PASS")
        with self.assertRaisesRegex(ValueError,"exact Stage 2 WR"):
            validate_stage2_worker_wr_attestation({},preflight)
        with self.assertRaisesRegex(ValueError,"exact Stage 2 WR"):
            validate_stage2_worker_wr_attestation({"stage2_wr_sha256":"f"*64},preflight)

    def test_upstream_receipt_requires_valid_wr_proof(self):
        evidence = {"status":"PASS","stage":"STAGE_2","wr_loaded":True,"rules_text_loaded":True,
                    "wr_path":"production/stages/STAGE_2_MARKET.md","wr_sha256":"c"*64,
                    "wr_git_blob_sha":"d"*40,"stage1_pinned_git_blob_sha":"d"*40,"stage1_pinned_commit":"commit"}
        context = {"main_commit_sha":"commit","governance":{"blob_shas":{stage_wr_preflight.STAGE_WR_PATHS["STAGE_2"]:"d"*40}}}
        receipt = {"wr_preflight":evidence,"worker_wr_attestation":{"status":"PASS","stage2_wr_sha256":evidence["wr_sha256"]}}
        result = stage_wr_preflight.require_stage_wr_receipt(receipt,"STAGE_2",context)
        self.assertEqual(result,evidence)
        with self.assertRaises(SystemExit):
            stage_wr_preflight.require_stage_wr_receipt({"wr_preflight":{}}, "STAGE_2", context)

    def test_stage4_upstream_requires_editorial_worker_wr_proof(self):
        path = stage_wr_preflight.STAGE_WR_PATHS["STAGE_4"]
        digest = "c" * 64
        blob = "e" * 40
        context = {"main_commit_sha":"commit","governance":{"blob_shas":{path:blob}}}
        evidence = {"status":"PASS","stage":"STAGE_4","wr_loaded":True,"rules_text_loaded":True,
                    "wr_path":path,"wr_sha256":digest,"wr_git_blob_sha":blob,
                    "stage1_pinned_git_blob_sha":blob,"stage1_pinned_commit":"commit"}
        receipt = {"wr_preflight":evidence,
                   "editorial_worker_wr_attestation":{"status":"PASS","stage4_wr_sha256":digest}}
        self.assertEqual(stage_wr_preflight.require_stage_wr_receipt(receipt,"STAGE_4",context),evidence)
        receipt["editorial_worker_wr_attestation"]["stage4_wr_sha256"] = "f" * 64
        with self.assertRaises(SystemExit):
            stage_wr_preflight.require_stage_wr_receipt(receipt,"STAGE_4",context)

    def test_unknown_stage_blocks(self):
        with self.assertRaises(ValueError):
            stage_wr_preflight.stage_wr_preflight("STAGE_7")

if __name__ == "__main__":
    unittest.main()
