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



    def test_stage6_payload_change_set_accepts_only_three_preview_files(self):
        from run_stage6 import validate_preview_change_set
        expected = allowed_paths(CONTEXT["report_date"], CONTEXT)
        validate_preview_change_set(expected, *expected)

    def test_stage6_payload_change_set_rejects_homepage_calendar_archive_and_template(self):
        from run_stage6 import validate_preview_change_set
        expected = allowed_paths(CONTEXT["report_date"], CONTEXT)
        for protected in ("index.html", "history/2026-11-26.html",
                          "data/calendar/weeks/2026-W48.json",
                          "production/templates/monday-mother-template.html",
                          "production/config/mother-template-manifest.json"):
            with self.subTest(protected=protected):
                with self.assertRaisesRegex(ValueError, "allowlist violation"):
                    validate_preview_change_set([*expected[:2], protected], *expected)

    def test_stage6_payload_change_set_rejects_missing_duplicate_and_unexpected_paths(self):
        from run_stage6 import validate_preview_change_set
        expected = allowed_paths(CONTEXT["report_date"], CONTEXT)
        cases = ([*expected[:2]], [expected[0], expected[0], expected[2]],
                 [*expected[:2], "preview/main/other-review.html"])
        for paths in cases:
            with self.subTest(paths=paths):
                with self.assertRaisesRegex(ValueError, "allowlist violation"):
                    validate_preview_change_set(paths, *expected)

    def test_stage6_preview_payload_does_not_mutate_protected_files_in_isolated_tree(self):
        import tempfile
        from pathlib import Path
        from run_stage6 import validate_preview_change_set
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protected = {
                "index.html": b"official homepage baseline",
                "data/calendar/weeks/2026-W48.json": b"calendar baseline",
                "production/templates/monday-mother-template.html": b"monday mother baseline",
                "production/templates/weekday-mother-template.html": b"weekday mother baseline",
                "production/config/mother-template-manifest.json": b"manifest baseline",
                "history/2026-11-26.html": b"history baseline",
            }
            for rel, raw in protected.items():
                target = root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
            expected = allowed_paths(CONTEXT["report_date"], CONTEXT)
            (root / expected[0]).parent.mkdir(parents=True, exist_ok=True)
            (root / expected[0]).write_bytes(b"synthetic review bytes")
            (root / expected[1]).write_bytes(b'{"status":"REVIEW_READY"}')
            (root / expected[2]).write_bytes(b'{"status":"PAGES_DEPLOY_PENDING"}')
            validate_preview_change_set(expected, *expected)
            for rel, raw in protected.items():
                self.assertEqual((root / rel).read_bytes(), raw, rel)


    def test_stage6_pages_wait_selects_only_new_dispatch_for_exact_payload_commit(self):
        from run_stage6 import wait_for_pages_success
        old_ids={10,11}
        docs=[
            {"workflow_runs":[
                {"id":10,"head_sha":"payload","event":"workflow_dispatch","status":"completed","conclusion":"success"},
                {"id":12,"head_sha":"other","event":"workflow_dispatch","status":"completed","conclusion":"success"},
                {"id":13,"head_sha":"payload","event":"push","status":"completed","conclusion":"success"},
                {"id":14,"head_sha":"payload","event":"workflow_dispatch","status":"in_progress"},
            ]},
            {"workflow_runs":[
                {"id":14,"head_sha":"payload","event":"workflow_dispatch","status":"completed","conclusion":"success",
                 "created_at":"2026-11-28T06:00:00Z"}
            ]}
        ]
        sleeps=[]
        result=wait_for_pages_success(old_ids,"payload",lambda:docs.pop(0),sleeps.append,timeout_seconds=30,poll_seconds=5)
        self.assertEqual(result["id"],14)
        self.assertEqual(sleeps,[5])

    def test_stage6_pages_wait_rejects_failed_dispatch(self):
        from run_stage6 import wait_for_pages_success
        with self.assertRaisesRegex(SystemExit,"without success"):
            wait_for_pages_success(set(),"payload",lambda:{"workflow_runs":[
                {"id":21,"head_sha":"payload","event":"workflow_dispatch","status":"completed","conclusion":"failure"}
            ]},lambda _:None,timeout_seconds=30)

    def test_stage6_pages_wait_times_out_without_matching_dispatch(self):
        from run_stage6 import wait_for_pages_success
        ticks=iter([0,0,0,2,2,2,4,4,4])
        with self.assertRaisesRegex(SystemExit,"timeout"):
            wait_for_pages_success(set(),"payload",lambda:{"workflow_runs":[]},lambda _:None,
                                   timeout_seconds=3,poll_seconds=1,clock=lambda:next(ticks))

    def test_stage6_public_preview_verifies_http_date_bytes_and_run(self):
        from run_stage6 import verify_public_preview
        from io import BytesIO
        html=b"<html><head><meta name='report-date' content='2026-11-30'></head><body>RUN-MONDAY-1</body></html>"
        class FakeResponse:
            status=200
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def read(self):return html
        seen={}
        def opener(request,timeout):
            seen["url"]=request.full_url
            seen["timeout"]=timeout
            return FakeResponse()
        result=verify_public_preview("https://example.test/review.html","2026-11-30","RUN-MONDAY-1",html,opener)
        self.assertEqual(result["http_status"],200)
        self.assertEqual(result["html_sha256"],__import__("hashlib").sha256(html).hexdigest())
        self.assertEqual(seen["timeout"],30)

    def test_stage6_public_preview_rejects_wrong_date_bytes_and_run(self):
        from run_stage6 import verify_public_preview
        cases=[
            (200,b"<meta name='report-date' content='2026-11-29'>RUN-MONDAY-1","date"),
            (200,b"<meta name='report-date' content='2026-11-30'>OTHER-RUN","bytes"),
            (200,b"<meta name='report-date' content='2026-11-30'>WRONG-RUN","Run ID"),
            (404,b"<meta name='report-date' content='2026-11-30'>RUN-MONDAY-1","HTTP/date"),
        ]
        for status,body,message in cases:
            with self.subTest(message=message):
                class FakeResponse:
                    def __enter__(self):return self
                    def __exit__(self,*args):return False
                    def read(self):return body
                FakeResponse.status=status
                with self.assertRaisesRegex(SystemExit,message):
                    verify_public_preview("https://example.test/review.html","2026-11-30","RUN-MONDAY-1",
                                          b"<meta name='report-date' content='2026-11-30'>RUN-MONDAY-1",
                                          lambda request,timeout:FakeResponse())

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
