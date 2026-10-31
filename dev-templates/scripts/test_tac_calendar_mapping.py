import unittest
from tac_calendar_dataset import SCHEMA_VERSION
from tac_calendar_mapping import build_calendar_card_plan


def source(label="資料來源"):
    return [{"source_name": "Official", "label": label,
             "url": "https://example.com/event",
             "accessed_at": "2026-10-31T10:00:00+08:00"}]


def economic(status="upcoming", details=None):
    return {
        "event_id": "econ-1", "event_date": "2026-11-03", "event_time": "09:00",
        "event_timezone": "Asia/Taipei", "country": "US", "event_name": "CPI",
        "importance": 5, "source_records": source(), "status_group": status,
        "summary": {"date": "11/03（二）", "time": "09:00", "country": "美國",
                    "name": "CPI", "stars": "★★★★★"},
        "details": details or {"市場影響": "關注通膨與利率預期"},
    }


def earnings(status="published"):
    return {
        "event_id": "earn-1", "event_date": "2026-11-03", "event_time": "08:30",
        "event_timezone": "America/New_York", "taiwan_display_date": "2026-11-03",
        "company_name": "Example Corp", "subtitle": "EX｜科技",
        "importance": 5, "release_session": "pre_market",
        "source_records": source("來源"), "status_group": status,
        "summary": {"us_date": "11/03（二）", "tw_date": "台灣時間 11/03",
                    "company": "Example Corp", "subtitle": "EX｜科技", "stars": "★★★★★"},
        "details": {"EPS 預估／實際": "預估 1.20；實際 1.35"},
    }


def dataset(economic_rows=None, earnings_rows=None):
    return {"schema_version": SCHEMA_VERSION, "report_date": "2026-11-02",
            "template": "weekdays",
            "economic_events": [economic()] if economic_rows is None else economic_rows,
            "earnings_events": [earnings()] if earnings_rows is None else earnings_rows}


class CalendarMappingTests(unittest.TestCase):
    def test_maps_status_groups(self):
        plan = build_calendar_card_plan(dataset())
        self.assertEqual(plan["economic"]["upcoming"][0]["event_id"], "econ-1")
        self.assertEqual(plan["earnings"]["published"][0]["event_id"], "earn-1")
        self.assertFalse(plan["write_authorized"])

    def test_missing_status_rejected(self):
        row = economic()
        del row["status_group"]
        with self.assertRaisesRegex(ValueError, "status_group"):
            build_calendar_card_plan(dataset(economic_rows=[row]))

    def test_unknown_status_rejected(self):
        with self.assertRaisesRegex(ValueError, "status_group"):
            build_calendar_card_plan(dataset(economic_rows=[economic("archived")]))

    def test_incomplete_summary_rejected(self):
        row = economic()
        del row["summary"]["time"]
        with self.assertRaisesRegex(ValueError, "exactly"):
            build_calendar_card_plan(dataset(economic_rows=[row]))

    def test_unknown_detail_label_rejected(self):
        with self.assertRaisesRegex(PermissionError, "not allowlisted"):
            build_calendar_card_plan(dataset(economic_rows=[economic(details={"前值": "1.2"})]))

    def test_earnings_detail_allowlist_enforced(self):
        row = earnings()
        row["details"] = {"未登記欄位": "不可寫入"}
        with self.assertRaisesRegex(PermissionError, "not allowlisted"):
            build_calendar_card_plan(dataset(earnings_rows=[row]))

    def test_source_labels_must_be_registered(self):
        row = economic()
        row["source_records"] = source("非登記來源標籤")
        with self.assertRaisesRegex(PermissionError, "source labels"):
            build_calendar_card_plan(dataset(economic_rows=[row]))

    def test_source_url_is_preserved(self):
        plan = build_calendar_card_plan(dataset())
        self.assertEqual(plan["economic"]["upcoming"][0]["sources"][0],
                         {"label": "資料來源", "href": "https://example.com/event"})

    def test_empty_groups_are_not_fabricated(self):
        plan = build_calendar_card_plan(dataset(economic_rows=[], earnings_rows=[]))
        self.assertEqual(plan["economic"], {})
        self.assertEqual(plan["earnings"], {})


if __name__ == "__main__":
    unittest.main()
