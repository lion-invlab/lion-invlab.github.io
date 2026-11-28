#!/usr/bin/env python3
import unittest
from run_stage5 import validate_stage4_handoff
from run_stage6 import validate_stage5_handoff, allowed_paths

CONTEXT={"run_id":"TAC-2026-11-26-test-1","report_date":"2026-11-26","trading_date":"2026-11-25"}

def stage4():
    return {"status":"PASS","run_id":CONTEXT["run_id"],"report_date":CONTEXT["report_date"],
            "trading_date":CONTEXT["trading_date"],"market_snapshot_unchanged":True,
            "market_snapshot_sha256_before":"a"*64,"market_snapshot_sha256_after":"a"*64,
            "editorial_run_binding":{"run_id":CONTEXT["run_id"],"market_snapshot_sha256":"a"*64,
                                     "research_bundle_sha256":"b"*64},
            "research_bundle":{"sha256":"b"*64}}

def stage5():
    return {"status":"REVIEW_READY","run_id":CONTEXT["run_id"],"report_date":CONTEXT["report_date"],
            "trading_date":CONTEXT["trading_date"],"html_sha256":"c"*64,"qa_sidecar_sha256":"d"*64,
            "render_manifest_sha256":"e"*64,"builder_blob_sha":"f"*40,
            "stage4_receipt_sha256":"1"*64,"research_bundle_sha256":"b"*64,
            "market_snapshot_sha256":"a"*64}

class Stage56HandoffTests(unittest.TestCase):
    def test_stage5_accepts_exact_stage4_run_dates_and_snapshot(self):
        result=validate_stage4_handoff(stage4(),{"market_snapshot_sha256":"a"*64},CONTEXT)
        self.assertEqual(result["research_bundle_sha256"],"b"*64)

    def test_stage5_rejects_wrong_trading_date(self):
        doc=stage4();doc["trading_date"]="2026-11-24"
        with self.assertRaisesRegex(ValueError,"identity mismatch"):
            validate_stage4_handoff(doc,{"market_snapshot_sha256":"a"*64},CONTEXT)

    def test_stage5_rejects_changed_market_snapshot(self):
        with self.assertRaisesRegex(ValueError,"Stage 2 frozen snapshot"):
            validate_stage4_handoff(stage4(),{"market_snapshot_sha256":"0"*64},CONTEXT)

    def test_stage6_rerun_uses_separate_preview_triplet(self):
        rerun_context={**CONTEXT,"supersedes_run_id":"TAC-2026-11-27-45937649928-1"}
        self.assertEqual(allowed_paths("2026-11-27",rerun_context),[
            "preview/main/2026-11-27-rerun-review.html",
            "preview/main/2026-11-27-rerun-review.qa.json",
            "preview/main/2026-11-27-rerun-review.delivery.json",
        ])

    def test_stage6_normal_run_keeps_standard_preview_triplet(self):
        self.assertEqual(allowed_paths("2026-11-27",CONTEXT),[
            "preview/main/2026-11-27-review.html",
            "preview/main/2026-11-27-review.qa.json",
            "preview/main/2026-11-27-review.delivery.json",
        ])

    def test_stage6_accepts_exact_stage5_and_stage4_evidence(self):
        s5=stage5()
        qa={"status":"REVIEW_READY","run_id":CONTEXT["run_id"],"report_date":CONTEXT["report_date"],"trading_date":CONTEXT["trading_date"]}
        render={"run_id":CONTEXT["run_id"],"report_date":CONTEXT["report_date"],"trading_date":CONTEXT["trading_date"],
                "output":{"sha256":"c"*64},"builder_blob_sha":"f"*40}
        s4=stage4()
        validate_stage5_handoff(s5,qa,render,CONTEXT,"c"*64,"e"*64,s4,"1"*64)

    def test_stage6_rejects_cross_run_qa(self):
        s5=stage5()
        qa={"status":"REVIEW_READY","run_id":"OTHER-RUN","report_date":CONTEXT["report_date"],"trading_date":CONTEXT["trading_date"]}
        render={"run_id":CONTEXT["run_id"],"report_date":CONTEXT["report_date"],"trading_date":CONTEXT["trading_date"],
                "output":{"sha256":"c"*64},"builder_blob_sha":"f"*40}
        with self.assertRaisesRegex(ValueError,"QA sidecar"):
            validate_stage5_handoff(s5,qa,render,CONTEXT,"c"*64,"e"*64,stage4(),"1"*64)

    def test_stage6_rejects_render_builder_sha_mismatch(self):
        s5=stage5()
        qa={"status":"REVIEW_READY","run_id":CONTEXT["run_id"],"report_date":CONTEXT["report_date"],"trading_date":CONTEXT["trading_date"]}
        render={"run_id":CONTEXT["run_id"],"report_date":CONTEXT["report_date"],"trading_date":CONTEXT["trading_date"],
                "output":{"sha256":"c"*64},"builder_blob_sha":"0"*40}
        with self.assertRaisesRegex(ValueError,"render manifest"):
            validate_stage5_handoff(s5,qa,render,CONTEXT,"c"*64,"e"*64,stage4(),"1"*64)


    def test_stage6_accepts_only_complete_same_run_verified_existing_triplet(self):
        import hashlib, json, tempfile
        from pathlib import Path
        from run_stage6 import validate_existing_preview_triplet, blob, sha

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            report="preview/main/2026-11-26-review.html"
            qa="preview/main/2026-11-26-review.qa.json"
            delivery="preview/main/2026-11-26-review.delivery.json"
            for rel in (report,qa,delivery):
                (root/rel).parent.mkdir(parents=True,exist_ok=True)
            html=b"<html><meta name='report-date' content='2026-11-26'></html>"
            (root/report).write_bytes(html)
            qa_doc={"status":"REVIEW_READY","run_id":CONTEXT["run_id"],"report_date":CONTEXT["report_date"],
                    "delivery":{"status":"DELIVERED_AND_PUBLICLY_VERIFIED","run_id":CONTEXT["run_id"],
                                "html_sha256":sha(html),"public_url_verified":True}}
            delivery_doc={"status":"DELIVERED_AND_PUBLICLY_VERIFIED","run_id":CONTEXT["run_id"],
                          "report_date":CONTEXT["report_date"],
                          "targets":{"html":report,"qa":qa,"delivery_receipt":delivery},
                          "public_url_verified":True,
                          "html":{"sha256":sha(html),"git_blob_sha":blob(html)},
                          "formal_homepage_modified":False,"history_archive_modified":False}
            (root/qa).write_text(json.dumps(qa_doc),encoding="utf-8")
            (root/delivery).write_text(json.dumps(delivery_doc),encoding="utf-8")
            self.assertTrue(validate_existing_preview_triplet(root,report,qa,delivery,CONTEXT))

    def test_stage6_rejects_existing_preview_from_another_run(self):
        import json, tempfile
        from pathlib import Path
        from run_stage6 import validate_existing_preview_triplet

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            report="preview/main/2026-11-26-review.html"
            qa="preview/main/2026-11-26-review.qa.json"
            delivery="preview/main/2026-11-26-review.delivery.json"
            for rel in (report,qa,delivery):
                (root/rel).parent.mkdir(parents=True,exist_ok=True)
                (root/rel).write_text("{}",encoding="utf-8")
            with self.assertRaisesRegex(SystemExit,"another Run/date"):
                validate_existing_preview_triplet(root,report,qa,delivery,CONTEXT)

    def test_stage6_rejects_incomplete_existing_preview_triplet(self):
        import tempfile
        from pathlib import Path
        from run_stage6 import validate_existing_preview_triplet

        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            report="preview/main/2026-11-26-review.html"
            qa="preview/main/2026-11-26-review.qa.json"
            delivery="preview/main/2026-11-26-review.delivery.json"
            (root/report).parent.mkdir(parents=True,exist_ok=True)
            (root/report).write_text("existing",encoding="utf-8")
            with self.assertRaisesRegex(SystemExit,"incomplete"):
                validate_existing_preview_triplet(root,report,qa,delivery,CONTEXT)

if __name__=="__main__":unittest.main()
