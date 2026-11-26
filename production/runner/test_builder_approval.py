import json
import tempfile
import unittest
from pathlib import Path
from builder_approval import require_approved_builder, verify_governance_snapshot, GOVERNANCE_PATHS

class BuilderApprovalTests(unittest.TestCase):
    def write(self, path, doc):
        path.write_text(json.dumps(doc),encoding="utf-8")
    def test_candidate_is_not_approved(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"approval.json"
            self.write(p,{"status":"CANDIDATE_PENDING_OWNER_APPROVAL","approved_by_owner":False,
                          "builder_path":"production/runner/build_review_html.py","builder_blob_sha":"abc"})
            with self.assertRaisesRegex(ValueError,"pending explicit owner approval"):
                require_approved_builder(approval_path=p,actual_sha="abc")
    def test_exact_sha_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"approval.json"
            self.write(p,{"status":"APPROVED_MAIN","approved_by_owner":True,
                          "builder_path":"production/runner/build_review_html.py","builder_blob_sha":"old"})
            with self.assertRaisesRegex(ValueError,"exact current Builder blob SHA"):
                require_approved_builder(approval_path=p,actual_sha="new")
    def test_governance_snapshot_requires_every_pinned_file(self):
        context={"governance":{"blob_shas":{path:"sha" for path in GOVERNANCE_PATHS}}}
        result=verify_governance_snapshot(context,actual_blobs={path:"sha" for path in GOVERNANCE_PATHS})
        self.assertEqual(result["status"],"PASS")
        self.assertEqual(result["file_count"],len(GOVERNANCE_PATHS))
    def test_governance_snapshot_rejects_changed_file(self):
        pinned={path:"sha" for path in GOVERNANCE_PATHS}
        actual=dict(pinned); actual["production/MASTER_WR.md"]="changed"
        with self.assertRaisesRegex(ValueError,"changed after Stage 1"):
            verify_governance_snapshot({"governance":{"blob_shas":pinned}},actual_blobs=actual)
    def test_approved_exact_sha_passes(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"approval.json"
            self.write(p,{"status":"APPROVED_MAIN","approved_by_owner":True,
                          "builder_path":"production/runner/build_review_html.py","builder_blob_sha":"abc",
                          "approved_at":"2026-11-26T12:00:00+08:00"})
            result=require_approved_builder(approval_path=p,actual_sha="abc")
            self.assertEqual(result["status"],"APPROVED_MAIN")
            self.assertEqual(result["builder_blob_sha"],"abc")

if __name__=="__main__": unittest.main()
