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

def editorial():
    return {"run_id":CONTEXT["run_id"],"report_date":CONTEXT["report_date"],
            "trading_date":CONTEXT["trading_date"],"market_snapshot_sha256":"a"*64,
            "research_bundle_sha256":"b"*64}

def stage5():
    return {"status":"REVIEW_READY","run_id":CONTEXT["run_id"],"report_date":CONTEXT["report_date"],
            "trading_date":CONTEXT["trading_date"],"html_sha256":"c"*64,"qa_sidecar_sha256":"d"*64,
            "render_manifest_sha256":"e"*64,"builder_blob_sha":"f"*40,
            "stage4_receipt_sha256":"1"*64,"research_bundle_sha256":"b"*64,
            "market_snapshot_sha256":"a"*64}

class Stage56HandoffTests(unittest.TestCase):
    def test_stage5_accepts_exact_stage4_run_dates_and_snapshot(self):
        result=validate_stage4_handoff(stage4(),{"market_snapshot_sha256":"a"*64},CONTEXT,editorial(),"b"*64)
        self.assertEqual(result["research_bundle_sha256"],"b"*64)

    def test_stage5_rejects_wrong_trading_date(self):
        doc=stage4();doc["trading_date"]="2026-11-24"
        with self.assertRaisesRegex(ValueError,"identity mismatch"):
            validate_stage4_handoff(doc,{"market_snapshot_sha256":"a"*64},CONTEXT,editorial(),"b"*64)

    def test_stage5_rejects_changed_market_snapshot(self):
        with self.assertRaisesRegex(ValueError,"Stage 2 frozen snapshot"):
            validate_stage4_handoff(stage4(),{"market_snapshot_sha256":"0"*64},CONTEXT,editorial(),"b"*64)

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

if __name__=="__main__":unittest.main()
