import json
import tempfile
import unittest
from pathlib import Path
from scripts.tac_weekly_calendar_db import validate_week, quality_report, cmd_init, cmd_snapshot, cmd_upsert, cmd_apply_snapshot, cmd_approve_snapshot

def load_for_test(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

class WeeklyCalendarDbTests(unittest.TestCase):
    def event(self, eid, when, stars=4, status="upcoming"):
        return {"id":eid,"event_date":when,"region":"US","event_name":eid,
                "importance_stars":stars,"status":status,
                "source":{"name":"official","url":"https://example.com/source"}}

    def week(self, week_id="2026-W45", start="2026-11-02", end="2026-11-06", events=None):
        return {"schema_version":1,"timezone":"Asia/Taipei","week_id":week_id,
                "week_start":start,"week_end":end,"wr_version":"3.7",
                "status":"prototype","events":events or {"economic":[],"earnings":[]},
                "coverage":{"economic":{"status":"incomplete"},"earnings":{"status":"incomplete"}},
                "audit":[]}

    def test_valid_week_and_duplicate_ids(self):
        w=self.week(events={"economic":[self.event("e1","2026-11-02T10:00:00+08:00")],
                            "earnings":[self.event("r1","2026-11-03T10:00:00+08:00")]})
        self.assertEqual(validate_week(w),[])
        w["events"]["economic"].append(self.event("e1","2026-11-04T10:00:00+08:00"))
        self.assertTrue(any("duplicate id" in e for e in validate_week(w)))

    def test_offset_required_and_week_range_enforced(self):
        w=self.week(events={"economic":[self.event("e1","2026-11-07T10:00:00+08:00")],"earnings":[]})
        errors=validate_week(w)
        self.assertTrue(any("outside declared week" in e for e in errors))
        w["events"]["economic"]=[self.event("e2","2026-11-03T10:00:00")]
        self.assertTrue(any("UTC offset" in e for e in validate_week(w)))

    def test_snapshot_filters_current_four_five_and_prior_five_released(self):
        current=self.week(events={"economic":[
            self.event("e4","2026-11-03T10:00:00+08:00",4),
            self.event("e5","2026-11-04T10:00:00+08:00",5)],
            "earnings":[self.event("r5","2026-11-04T10:00:00+08:00",5)]})
        previous=self.week("2026-W44","2026-10-26","2026-10-30",{
            "economic":[{**self.event("p5","2026-10-30T10:00:00+08:00",5,"released"),"actual":"2.5%"}],
            "earnings":[]})
        previous["status"]="archive_candidate"
        with tempfile.TemporaryDirectory() as td:
            current_path=Path(td)/"current.json"; prev_path=Path(td)/"prev.json"; out=Path(td)/"snapshot.json"
            current_path.write_text(json.dumps(current),encoding="utf-8")
            prev_path.write_text(json.dumps(previous),encoding="utf-8")
            args=type("Args",(),{"file":str(current_path),"report_date":"2026-11-02",
                                 "output":str(out),"previous_week_file":str(prev_path)})()
            self.assertEqual(cmd_snapshot(args),0)
            snap=json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual([x["id"] for x in snap["economic_calendar"]],["e4","e5"])
            self.assertEqual([x["id"] for x in snap["previous_economic_calendar"]],["p5"])
            self.assertEqual(snap["previous_earnings_calendar"],[])
            with self.assertRaisesRegex(FileExistsError,"refusing to overwrite existing daily snapshot"):
                cmd_snapshot(args)

    def test_upsert_is_idempotent_and_audited_only_on_change(self):
        w=self.week(events={"economic":[self.event("same","2026-11-02T10:00:00+08:00")],"earnings":[]})
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"week.json"; event=Path(td)/"event.json"
            db.write_text(json.dumps(w),encoding="utf-8")
            event.write_text(json.dumps(self.event("same","2026-11-02T10:00:00+08:00")),encoding="utf-8")
            args=type("Args",(),{"file":str(db),"kind":"economic","event":str(event),"at":"2026-11-01T09:00:00+08:00"})()
            self.assertEqual(cmd_upsert(args),0)
            first=load_for_test(db)
            self.assertEqual(len(first["audit"]),0)
            changed=self.event("same","2026-11-02T10:00:00+08:00")
            changed["event_name"]="revised name"
            event.write_text(json.dumps(changed),encoding="utf-8")
            self.assertEqual(cmd_upsert(args),0)
            second=load_for_test(db)
            self.assertEqual(len(second["events"]["economic"]),1)
            self.assertEqual(len(second["audit"]),1)
            self.assertEqual(second["audit"][0]["action"],"event_updated")


    def test_apply_snapshot_preserves_non_calendar_content(self):
        content={"meta":{"report_date":"2026-11-02","wr_version":"3.7"},
                 "focus_news":[{"id":"keep-me"}],"analysis":{"summary":"preserve"},
                 "economic_calendar":[],"earnings_calendar":[],
                 "previous_economic_calendar":[],"previous_earnings_calendar":[],
                 "coverage":{}}
        arrays=("economic_calendar","earnings_calendar","previous_economic_calendar","previous_earnings_calendar")
        snap={"meta":{"report_date":"2026-11-02","week_id":"2026-W45","previous_week_id":"2026-W44",
                      "database_updated_at":"2026-11-01T00:00:00+08:00","wr_version":"3.7"},
              "coverage":{key:{"status":"incomplete"} for key in arrays}}
        for key in arrays: snap[key]=[{"id":key+"-event"}]
        with tempfile.TemporaryDirectory() as td:
            cp=Path(td)/"content.json"; sp=Path(td)/"snapshot.json"; out=Path(td)/"merged.json"
            cp.write_text(json.dumps(content),encoding="utf-8")
            sp.write_text(json.dumps(snap),encoding="utf-8")
            args=type("Args",(),{"content":str(cp),"snapshot":str(sp),"output":str(out)})()
            self.assertEqual(cmd_apply_snapshot(args),0)
            merged=load_for_test(out)
            self.assertEqual(merged["focus_news"],content["focus_news"])
            self.assertEqual(merged["analysis"],content["analysis"])
            self.assertEqual(merged["economic_calendar"],snap["economic_calendar"])
            self.assertEqual(merged["meta"],content["meta"])
            self.assertEqual(merged["coverage"]["previous_economic_calendar"]["status"],"incomplete")

    def test_snapshot_without_previous_week_still_exports_empty_previous_arrays(self):
        current=self.week()
        with tempfile.TemporaryDirectory() as td:
            current_path=Path(td)/"current.json"; out=Path(td)/"snapshot.json"
            current_path.write_text(json.dumps(current),encoding="utf-8")
            args=type("Args",(),{"file":str(current_path),"report_date":"2026-11-02",
                                 "output":str(out),"previous_week_file":None})()
            self.assertEqual(cmd_snapshot(args),0)
            snap=json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(snap["previous_economic_calendar"],[])
            self.assertEqual(snap["previous_earnings_calendar"],[])
            self.assertEqual(snap["coverage"]["previous_economic_calendar"]["status"],"not_applicable")

    def test_released_events_require_actual_financial_fields(self):
        economic=self.event("e1","2026-11-02T10:00:00+08:00",5,"released")
        errors=validate_week(self.week(events={"economic":[economic],"earnings":[]}))
        self.assertTrue(any("requires actual" in e for e in errors))
        earnings=self.event("r1","2026-11-02T10:00:00+08:00",5,"released")
        errors=validate_week(self.week(events={"economic":[],"earnings":[earnings]}))
        self.assertTrue(any("requires numeric eps_actual" in e for e in errors))

    def test_released_event_cannot_regress_to_upcoming(self):
        released={**self.event("e1","2026-11-02T10:00:00+08:00",5,"released"),"actual":"3.2%"}
        w=self.week(events={"economic":[released],"earnings":[]})
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"week.json"; event=Path(td)/"event.json"
            db.write_text(json.dumps(w),encoding="utf-8")
            event.write_text(json.dumps(self.event("e1","2026-11-02T10:00:00+08:00",5,"upcoming")),encoding="utf-8")
            args=type("Args",(),{"file":str(db),"kind":"economic","event":str(event),"at":"2026-11-03T09:00:00+08:00"})()
            with self.assertRaisesRegex(ValueError,"cannot regress to upcoming"):
                cmd_upsert(args)
            self.assertEqual(load_for_test(db)["events"]["economic"][0]["status"],"released")

    def test_unknown_time_must_be_explicit_boolean(self):
        event=self.event("e1","2026-11-02T10:00:00+08:00")
        event["time_known"]="false"
        errors=validate_week(self.week(events={"economic":[event],"earnings":[]}))
        self.assertTrue(any("time_known must be boolean" in e for e in errors))

    def test_week_init_creates_iso_week_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/"2026-W46.json"
            args=type("Args",(),{"week_of":"2026-11-09","output":str(out),"wr_version":"3.7",
                                 "at":"2026-11-08T09:00:00+08:00"})()
            self.assertEqual(cmd_init(args),0)
            data=load_for_test(out)
            self.assertEqual(data["week_id"],"2026-W46")
            self.assertEqual(data["week_start"],"2026-11-09")
            self.assertEqual(data["week_end"],"2026-11-13")
            self.assertEqual(data["coverage"]["economic"]["status"],"incomplete")
            with self.assertRaisesRegex(FileExistsError,"refusing to overwrite"):
                cmd_init(args)

    def test_approved_snapshot_cannot_be_replaced(self):
        current=self.week(events={"economic":[self.event("e1","2026-11-02T10:00:00+08:00",4)],"earnings":[]})
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"week.json"; out=Path(td)/"snapshot.json"
            db.write_text(json.dumps(current),encoding="utf-8")
            args=type("Args",(),{"file":str(db),"report_date":"2026-11-02","output":str(out),
                                 "previous_week_file":None,"replace":False})()
            self.assertEqual(cmd_snapshot(args),0)
            approve=type("Args",(),{"file":str(out),"at":"2026-11-02T08:00:00+08:00"})()
            self.assertEqual(cmd_approve_snapshot(approve),0)
            before=out.read_text(encoding="utf-8")
            args.replace=True
            with self.assertRaisesRegex(PermissionError,"approved daily snapshot is immutable"):
                cmd_snapshot(args)
            self.assertEqual(out.read_text(encoding="utf-8"),before)

    def test_two_week_lifecycle_keeps_approved_snapshot_isolated(self):
        w45=self.week(events={"economic":[self.event("monday","2026-11-02T10:00:00+08:00",4)],"earnings":[]})
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); db45=root/"2026-W45.json"; mon=root/"2026-11-02.json"; tue=root/"2026-11-03.json"
            db45.write_text(json.dumps(w45),encoding="utf-8")
            monday_args=type("Args",(),{"file":str(db45),"report_date":"2026-11-02","output":str(mon),
                                        "previous_week_file":None,"replace":False})()
            self.assertEqual(cmd_snapshot(monday_args),0)
            approve=type("Args",(),{"file":str(mon),"at":"2026-11-02T08:00:00+08:00"})()
            self.assertEqual(cmd_approve_snapshot(approve),0)
            monday_before=mon.read_text(encoding="utf-8")
            incoming=self.event("tuesday","2026-11-03T10:00:00+08:00",5)
            event_path=root/"event.json"; event_path.write_text(json.dumps(incoming),encoding="utf-8")
            upsert=type("Args",(),{"file":str(db45),"kind":"economic","event":str(event_path),
                                   "at":"2026-11-03T08:00:00+08:00"})()
            self.assertEqual(cmd_upsert(upsert),0)
            tuesday_args=type("Args",(),{"file":str(db45),"report_date":"2026-11-03","output":str(tue),
                                         "previous_week_file":None,"replace":False})()
            self.assertEqual(cmd_snapshot(tuesday_args),0)
            self.assertEqual(mon.read_text(encoding="utf-8"),monday_before)
            w46_path=root/"2026-W46.json"
            init=type("Args",(),{"week_of":"2026-11-09","output":str(w46_path),"wr_version":"3.7",
                                 "at":"2026-11-08T09:00:00+08:00"})()
            self.assertEqual(cmd_init(init),0)
            w46=load_for_test(w46_path)
            self.assertEqual(w46["week_id"],"2026-W46")
            self.assertEqual(w46["events"],{"economic":[],"earnings":[]})
            self.assertEqual(len(load_for_test(db45)["events"]["economic"]),2)
            self.assertEqual(load_for_test(mon)["meta"]["approval_status"],"approved")
            self.assertEqual(load_for_test(tue)["meta"]["approval_status"],"draft")

    def test_snapshot_adds_only_released_five_star_previous_week_events(self):
        current=self.week(events={"economic":[
            self.event("current-four","2026-11-02T10:00:00+08:00",4),
            self.event("current-five","2026-11-03T10:00:00+08:00",5)
        ],"earnings":[]})
        root=Path(__file__).resolve().parents[1]
        previous_path=root/"data/calendar/weeks/2026-W44.json"
        previous=load_for_test(previous_path)
        self.assertIn(previous["status"],("archive_candidate","archived"))
        with tempfile.TemporaryDirectory() as td:
            db=Path(td)/"W45.json"; out=Path(td)/"2026-11-02.json"
            db.write_text(json.dumps(current),encoding="utf-8")
            args=type("Args",(),{"file":str(db),"report_date":"2026-11-02","output":str(out),
                                 "previous_week_file":str(previous_path),"replace":False})()
            self.assertEqual(cmd_snapshot(args),0)
            snapshot=load_for_test(out)
            self.assertEqual({x["importance_stars"] for x in snapshot["economic_calendar"]},{4,5})
            for key in ("previous_economic_calendar","previous_earnings_calendar"):
                self.assertTrue(all(x["importance_stars"]==5 and x["status"]=="released"
                                    for x in snapshot[key]))

    def test_approved_mother_templates_keep_calendar_anchors(self):
        root=Path(__file__).resolve().parents[1]
        monday=(root/"index_母版_週一_首頁基準.html").read_text(encoding="utf-8")
        weekdays=(root/"index_母版_週二至週五_首頁基準.html").read_text(encoding="utf-8")
        common=("calendar","earnings","week-econ-today","week-econ-upcoming",
                "week-econ-published","week-earnings-today","week-earnings-upcoming",
                "week-earnings-published")
        for anchor in common:
            self.assertIn(f'id="{anchor}"',monday)
            self.assertIn(f'id="{anchor}"',weekdays)
        self.assertIn('id="last-week-calendar"',monday)
        self.assertIn('id="last-week-earnings"',monday)
        self.assertNotIn('id="last-week-calendar"',weekdays)
        self.assertNotIn('id="last-week-earnings"',weekdays)

    def test_quality_report_excludes_non_applicable_economic_fields(self):
        data=self.week(events={"economic":[
            {**self.event("election","2026-11-03T12:00:00+08:00",5),
             "previous_applicable":False,"forecast_applicable":False},
            self.event("jolts","2026-11-03T23:00:00+08:00",4)
        ],"earnings":[]})
        report=quality_report(data)["streams"]["economic"]
        self.assertEqual(report["missing_fields"]["previous"],1)
        self.assertEqual(report["missing_fields"]["forecast"],1)
        self.assertEqual(report["not_applicable_fields"]["previous"],1)
        self.assertEqual(report["not_applicable_fields"]["forecast"],1)

    def test_quality_report_counts_missing_consensus_and_unknown_times(self):
        economic=self.event("e1","2026-11-02T12:00:00+08:00")
        economic["time_known"]=False
        earnings=self.event("r1","2026-11-03T12:00:00+08:00")
        earnings.update({"company":"Example Co","time_known":False})
        report=quality_report(self.week(events={"economic":[economic],"earnings":[earnings]}))
        self.assertEqual(report["streams"]["economic"]["unknown_time_or_session"],1)
        self.assertEqual(report["streams"]["earnings"]["missing_fields"]["revenue_estimate"],1)
        self.assertEqual(report["streams"]["earnings"]["missing_fields"]["consensus_source"],1)

    def test_tac_star_and_archive_policy(self):
        low=self.week(events={"economic":[self.event("low","2026-11-02T10:00:00+08:00",3)],"earnings":[]})
        self.assertTrue(any("TAC 4 or 5" in e for e in validate_week(low)))
        low_earnings=self.week(events={"economic":[],
            "earnings":[self.event("low-earnings","2026-11-02T10:00:00+08:00",3)]})
        self.assertTrue(any("TAC 4 or 5" in e for e in validate_week(low_earnings)))
        archived=self.week("2026-W44","2026-10-26","2026-10-30",{
            "economic":[self.event("four","2026-10-30T10:00:00+08:00",4,"released")],"earnings":[]})
        archived["status"]="archive_candidate"
        self.assertTrue(any("5-star only" in e for e in validate_week(archived)))
        archived["events"]["economic"]=[self.event("unreleased","2026-10-30T10:00:00+08:00",5,"upcoming")]
        self.assertTrue(any("must be released" in e for e in validate_week(archived)))

if __name__=="__main__": unittest.main()
