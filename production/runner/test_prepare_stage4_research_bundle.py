import json, tempfile, unittest, hashlib
from pathlib import Path
from prepare_stage4_research_bundle import build_bundle, market_digest

class Stage4ResearchBundleTests(unittest.TestCase):
    def test_builds_exact_run_bound_bundle_and_marks_unresolved_rows(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); run=root/"TAC-2026-11-26-test-1"; run.mkdir()
            context={"run_id":run.name,"report_date":"2026-11-26","trading_date":"2026-11-25",
                     "main_commit_sha":"abc","workflow_run_id":"12345"}
            evidence=root/"screenshots"/"sp500.png"; evidence.parent.mkdir(parents=True)
            evidence.write_bytes(b"fake screenshot evidence")
            evidence_sha=hashlib.sha256(evidence.read_bytes()).hexdigest()
            sidecar_path=root/"production/input/market-screenshot-observations-2026-11-26.json"
            sidecar_path.parent.mkdir(parents=True)
            sidecar={"report_date":"2026-11-26","trading_date":"2026-11-25","observations":[
                {"group":"global_markets","name":"指數0","data_date":"2026-11-25",
                 "source_url":"https://hk.investing.com/indices/us-spx-500-historical-data",
                 "instrument_identity":"S&P 500 cash index",
                 "fields":{"close":{"value":"100","field_name":"Price","evidence_path":"screenshots/sp500.png",
                                   "evidence_sha256":evidence_sha,"captured_at":"2026-11-26T05:00:00+08:00"}}}]}
            sidecar_path.write_text(json.dumps(sidecar),encoding="utf-8")
            context["screenshot_input"]={"present":True,"path":str(sidecar_path.relative_to(root)),
                                         "sha256":hashlib.sha256(sidecar_path.read_bytes()).hexdigest()}
            data={"report_date":"2026-11-26","trading_date":"2026-11-25",
                  "global_markets":{},"sectors":{},"sector_sources":{},"bonds":{},"fx":{},
                  "energy":{},"metals":{},"risk":{},"fedwatch":{"status":"PENDING"}}
            groups={"global_markets":17,"bonds":3,"fx":6,"energy":2,"metals":2,"risk":3}
            all_rows=[]
            for group,count in groups.items():
                for i in range(count):
                    name=("指數"+str(i)) if group=="global_markets" else group+str(i)
                    verified=not (group=="risk" and i==2)
                    source={"verification_status":"VERIFIED" if verified else "PENDING",
                            "data_date":"2026-11-25","quote_type":"daily_close",
                            "url":"https://example.com/"+group+"/"+str(i)}
                    data[group][name]={"display":"100" if verified else "待核實",
                                       "change_display":"+1.0%" if verified else "待核實",
                                       "source":source}
                    all_rows.append({"group":group,"name":name,"source_url":source["url"],
                                     "trading_date":"2026-11-25",
                                     "status":"VERIFIED" if verified else "PENDING_CURRENT_RUN_BROWSER_OBSERVATION",
                                     "market_data_status":"VERIFIED" if verified else "TOOL_READ_FAILURE"})
            for i in range(11):
                name="ETF"+str(i); verified=True
                data["sectors"][name]="+1.0%"
                data["sector_sources"][name]={"verification_status":"VERIFIED","data_date":"2026-11-25",
                    "quote_type":"daily_close","url":"https://example.com/sectors/"+str(i),"change_display":"+1.0%"}
                all_rows.append({"group":"sectors","name":name,"source_url":data["sector_sources"][name]["url"],
                                 "trading_date":"2026-11-25","status":"VERIFIED","market_data_status":"VERIFIED"})
            data["global_markets"]["指數0"]["source"]["instrument_identity"]="S&P 500 cash index"
            for name,doc in {
                "run-context.json":context,"stage1-receipt.json":{"status":"PASS","run_id":run.name},
                "report-data.json":data,
                "stage3-calendar-receipt.json":{"status":"PASS","run_id":run.name,"report_date":"2026-11-26","main_commit_sha":"abc"},
                "calendar-source-bundle.json":{},"calendar.json":{"events":[]},"earnings.json":{"events":[]},
                "last-week-calendar.json":{"events":[]},"last-week-earnings.json":{"events":[]},
                "market-history-browser-observations.json":{},"market-snapshot-audit.json":{}
            }.items():
                (run/name).write_text(json.dumps(doc),encoding="utf-8")
            manifest={"rows":[{"group":x["group"],"name":x["name"],"market_data_status":x["market_data_status"],
                               "verification_status":x["status"]} for x in all_rows]}
            (run/"market-source-verification-manifest.json").write_text(json.dumps(manifest),encoding="utf-8")
            counts={"VERIFIED":43,"TOOL_READ_FAILURE":1}
            receipt_rows=[{"group":x["group"],"name":x["name"],"status":x["status"],
                           "market_data_status":x["market_data_status"]} for x in all_rows]
            inputs={}
            for key,filename in (("fixture","report-data.json"),("manifest","market-source-verification-manifest.json"),
                                 ("audit","market-snapshot-audit.json"),("observations","market-history-browser-observations.json")):
                path_obj=run/filename
                inputs[key]={"path":str(path_obj.relative_to(root)),"sha256":hashlib.sha256(path_obj.read_bytes()).hexdigest()}
            stage2={"status":"PARTIAL","workflow_run_id":"12345","report_date":"2026-11-26","trading_date":"2026-11-25",
                    "market_status_counts":counts,"rows":receipt_rows,"input_files":inputs}
            (run/"stage2-market-snapshot-receipt.json").write_text(json.dumps(stage2),encoding="utf-8")
            stage2_summary={"run_id":run.name,"report_date":"2026-11-26","trading_date":"2026-11-25",
                            "market_snapshot_sha256":market_digest(data),"market_status_counts":counts}
            (run/"stage2-run-summary.json").write_text(json.dumps(stage2_summary),encoding="utf-8")
            bundle=build_bundle(run,root)
            self.assertEqual(bundle["run_id"],run.name)
            self.assertEqual(bundle["market_snapshot"]["row_count"],44)
            self.assertEqual(len(bundle["market_snapshot"]["unresolved_rows"]),1)
            self.assertEqual(bundle["market_snapshot_sha256"],market_digest(data))
            self.assertEqual(bundle["market_snapshot"]["unresolved_rows"][0]["market_data_status"],"TOOL_READ_FAILURE")
            self.assertEqual(bundle["editorial_contract"]["summary_points"],3)
            self.assertEqual(len(bundle["screenshot_evidence"]),1)
            self.assertEqual(bundle["screenshot_evidence"][0]["sha256"],evidence_sha)
            self.assertIn("market-screenshot-sidecar",bundle["input_refs"])
    def test_rejects_cross_run_stage3_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); run=root/"TAC-2026-11-26-test-1"; run.mkdir()
            data={"report_date":"2026-11-26","trading_date":"2026-11-25"}
            context={"run_id":run.name,"report_date":"2026-11-26","trading_date":"2026-11-25","main_commit_sha":"abc"}
            for name,doc in {
                "run-context.json":context,"stage1-receipt.json":{"status":"PASS","run_id":run.name},"report-data.json":data,
                "stage2-market-snapshot-receipt.json":{"status":"PASS"},
                "stage2-run-summary.json":{"run_id":run.name,"market_snapshot_sha256":market_digest(data)},
                "stage3-calendar-receipt.json":{"status":"PASS","run_id":"other","main_commit_sha":"abc"}
            }.items():
                (run/name).write_text(json.dumps(doc),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"Stage 3 receipt"):
                build_bundle(run,root)

if __name__=="__main__":unittest.main()
