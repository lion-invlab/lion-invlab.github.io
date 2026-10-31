import unittest

from tac_calendar_dataset import SCHEMA_VERSION, validate_calendar_dataset


def source():
    return [{
        "source_name": "Official source",
        "label": "Official",
        "url": "https://example.com/event",
        "accessed_at": "2026-10-31T10:00:00+08:00",
    }]


def econ(event_id="e1", event_date="2026-11-03", event_time="09:00", **extra):
    return {
        "event_id": event_id, "event_date": event_date, "event_time": event_time,
        "event_timezone": "Asia/Taipei", "country": "US", "event_name": "CPI",
        "importance": 5, "source_records": source(), **extra,
    }


def earnings(event_id="r1", event_date="2026-11-03", event_time="08:30", **extra):
    return {
        "event_id": event_id, "event_date": event_date, "event_time": event_time,
        "event_timezone": "America/New_York", "taiwan_display_date": "2026-11-03",
        "company_name": "Example Corp", "subtitle": "Quarterly results",
        "importance": 5, "release_session": "pre_market",
        "source_records": source(), **extra,
    }


def dataset(economic=None, earnings_rows=None):
    return {
        "schema_version": SCHEMA_VERSION, "report_date": "2026-11-02",
        "template": "monday",
        "economic_events": economic if economic is not None else [econ()],
        "earnings_events": earnings_rows if earnings_rows is not None else [earnings()],
    }


class CalendarDatasetTests(unittest.TestCase):
    def test_valid_dataset_and_sorted_output(self):
        raw = dataset(
            economic=[econ("late", "2026-11-04", "10:00"), econ("early", "2026-11-03", "08:00")],
            earnings_rows=[
                earnings("after", "2026-11-03", "16:00", release_session="after_market"),
                earnings("before", "2026-11-03", "08:00", release_session="pre_market"),
            ],
        )
        result = validate_calendar_dataset(raw)
        self.assertEqual([x["event_id"] for x in result["economic_events"]], ["early", "late"])
        self.assertEqual([x["event_id"] for x in result["earnings_events"]], ["before", "after"])
        self.assertEqual([x["event_id"] for x in raw["economic_events"]], ["late", "early"])

    def test_unknown_time_sorts_after_known_same_day(self):
        result = validate_calendar_dataset(dataset(economic=[
            econ("unknown", event_time=None), econ("known", event_time="12:00")
        ]))
        self.assertEqual([x["event_id"] for x in result["economic_events"]], ["known", "unknown"])

    def test_duplicate_event_id_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate event_id"):
            validate_calendar_dataset(dataset(economic=[econ("same"), econ("same")]))

    def test_invalid_importance_rejected(self):
        with self.assertRaisesRegex(ValueError, "importance"):
            validate_calendar_dataset(dataset(economic=[econ(importance=6)]))

    def test_boolean_importance_rejected(self):
        with self.assertRaisesRegex(ValueError, "importance"):
            validate_calendar_dataset(dataset(economic=[econ(importance=True)]))

    def test_missing_source_rejected(self):
        row = econ()
        row["source_records"] = []
        with self.assertRaisesRegex(ValueError, "source_records"):
            validate_calendar_dataset(dataset(economic=[row]))

    def test_invalid_source_url_rejected(self):
        row = econ()
        row["source_records"] = [dict(source()[0], url="javascript:alert(1)")]
        with self.assertRaisesRegex(ValueError, "HTTP"):
            validate_calendar_dataset(dataset(economic=[row]))

    def test_access_timestamp_requires_timezone(self):
        row = econ()
        row["source_records"] = [dict(source()[0], accessed_at="2026-10-31T10:00:00")]
        with self.assertRaisesRegex(ValueError, "timezone"):
            validate_calendar_dataset(dataset(economic=[row]))

    def test_invalid_event_date_rejected(self):
        with self.assertRaisesRegex(ValueError, "event_date"):
            validate_calendar_dataset(dataset(economic=[econ(event_date="11/03/2026")]))

    def test_missing_event_timezone_rejected(self):
        row = econ()
        del row["event_timezone"]
        with self.assertRaisesRegex(ValueError, "event_timezone"):
            validate_calendar_dataset(dataset(economic=[row]))

    def test_invalid_release_session_rejected(self):
        with self.assertRaisesRegex(ValueError, "release_session"):
            validate_calendar_dataset(dataset(earnings_rows=[earnings(release_session="overnight")]))

    def test_invalid_template_rejected(self):
        raw = dataset()
        raw["template"] = "both"
        with self.assertRaisesRegex(ValueError, "template"):
            validate_calendar_dataset(raw)

    def test_invalid_details_type_rejected(self):
        row = econ(details={"觀察重點": 123})
        with self.assertRaisesRegex(ValueError, "details"):
            validate_calendar_dataset(dataset(economic=[row]))

    def test_economic_and_earnings_are_separate(self):
        raw = dataset(economic=[], earnings_rows=[earnings()])
        result = validate_calendar_dataset(raw)
        self.assertEqual(result["economic_events"], [])
        self.assertEqual(len(result["earnings_events"]), 1)

    def test_taiwan_display_date_is_not_us_publication_date(self):
        row = earnings(event_date="2026-11-02", taiwan_display_date="2026-11-03")
        result = validate_calendar_dataset(dataset(earnings_rows=[row]))
        self.assertEqual(result["earnings_events"][0]["event_date"], "2026-11-02")
        self.assertEqual(result["earnings_events"][0]["taiwan_display_date"], "2026-11-03")


if __name__ == "__main__":
    unittest.main()
