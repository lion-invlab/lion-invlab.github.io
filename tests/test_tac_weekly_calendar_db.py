import json
import tempfile
import unittest
from pathlib import Path
from scripts.tac_weekly_calendar_db import validate_week, cmd_snapshot

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
            self.event("e3","2026-11-02T10:00:00+08:00",3),
            self.event("e4","2026-11-03T10:00:00+08:00",4)],
            "earnings":[self.event("r5","2026-11-04T10:00:00+08:00",5)]})
        previous=self.week("2026-W44","2026-10-26","2026-10-30",{
            "economic":[self.event("p4","2026-10-29T10:00:00+08:00",4,"released"),
                        self.event("p5","2026-10-30T10:00:00+08:00",5,"released")],
            "earnings":[self.event("pe5","2026-10-28T10:00:00+08:00",5,"upcoming")]})
        with tempfile.TemporaryDirectory() as td:
            current_path=Path(td)/"current.json"; prev_path=Path(td)/"prev.json"; out=Path(td)/"snapshot.json"
            current_path.write_text(json.dumps(current),encoding="utf-8")
            prev_path.write_text(json.dumps(previous),encoding="utf-8")
            args=type("Args",(),{"file":str(current_path),"report_date":"2026-11-02",
                                 "output":str(out),"previous_week_file":str(prev_path)})()
            self.assertEqual(cmd_snapshot(args),0)
            snap=json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual([x["id"] for x in snap["economic_calendar"]],["e4"])
            self.assertEqual([x["id"] for x in snap["previous_economic_calendar"]],["p5"])
            self.assertEqual(snap["previous_earnings_calendar"],[])

if __name__=="__main__": unittest.main()
