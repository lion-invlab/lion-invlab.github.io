import unittest

from tac_calendar_dataset import SCHEMA_VERSION
from tac_calendar_group_inventory import inventory_mother
from tac_calendar_prepare import prepare_calendar_update


def source(field_label="資料來源"):
    return [{
        "source_name": "Official",
        "field_label": field_label,
        "label": "Official source",
        "url": "https://example.com/event",
        "accessed_at": "2026-10-31T12:00:00+08:00",
    }]


def econ(event_id, status_group, event_date="2026-11-02"):
    return {
        "event_id": event_id, "event_date": event_date, "event_time": "09:00",
        "event_timezone": "Asia/Taipei", "status_group": status_group,
        "country": "美國", "event_name": "CPI", "importance": 5,
        "source_records": source(),
    }


def earnings(event_id, status_group, event_date="2026-11-02"):
    return {
        "event_id": event_id, "event_date": event_date, "event_time": "08:30",
        "event_timezone": "America/New_York", "status_group": status_group,
        "taiwan_display_date": event_date, "company_name": "Example Corp",
        "subtitle": "EX｜軟體", "importance": 5, "release_session": "pre_market",
        "source_records": source("來源"),
    }


def dataset(template, economic, earnings_rows, prior_economic=None, prior_earnings=None):
    return {
        "schema_version": SCHEMA_VERSION, "report_date": "2026-11-02",
        "template": template, "economic_events": economic,
        "earnings_events": earnings_rows,
        "prior_week_economic_events": prior_economic or [],
        "prior_week_earnings_events": prior_earnings or [],
    }


class CalendarPrepareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.monday = inventory_mother("monday")
        cls.weekdays = inventory_mother("weekdays")

    def test_monday_payload_preparation_passes_with_supported_groups(self):
        raw = dataset(
            "monday",
            [econ("econ-upcoming", "upcoming")],
            [earnings("earn-upcoming", "upcoming")],
            [econ("econ-prior", "prior_week_published", "2026-10-30")],
            [earnings("earn-prior", "prior_week_published", "2026-10-30")],
        )
        prepared = prepare_calendar_update(raw, self.monday)
        self.assertTrue(prepared["ready"], prepared["plan"])
        self.assertEqual(prepared["stage"], "validated_payload_ready")
        self.assertFalse(prepared["mutation_performed"])
        self.assertEqual(len(prepared["payloads"]["weekly_economic"]["upcoming"]), 1)
        self.assertEqual(len(prepared["payloads"]["prior_week_earnings"]["prior_week_published"]), 1)

    def test_monday_blocked_group_withholds_all_payloads(self):
        raw = dataset(
            "monday", [econ("econ-today", "today")], [],
            [econ("econ-prior", "prior_week_published", "2026-10-30")],
            [earnings("earn-prior", "prior_week_published", "2026-10-30")],
        )
        prepared = prepare_calendar_update(raw, self.monday)
        self.assertFalse(prepared["ready"])
        self.assertEqual(prepared["stage"], "blocked_before_dom_write")
        self.assertIsNone(prepared["payloads"])

    def test_weekday_payload_preparation_passes_with_all_groups_populated(self):
        raw = dataset(
            "weekdays",
            [econ("econ-today", "today"), econ("econ-upcoming", "upcoming"), econ("econ-published", "published")],
            [earnings("earn-today", "today"), earnings("earn-upcoming", "upcoming"), earnings("earn-published", "published")],
        )
        prepared = prepare_calendar_update(raw, self.weekdays)
        self.assertTrue(prepared["ready"], prepared["plan"])
        self.assertEqual(len(prepared["payloads"]["weekly_economic"]["today"]), 1)
        self.assertEqual(len(prepared["payloads"]["weekly_earnings"]["published"]), 1)

    def test_weekday_empty_group_withholds_all_payloads(self):
        raw = dataset(
            "weekdays",
            [econ("econ-upcoming", "upcoming"), econ("econ-published", "published")],
            [earnings("earn-today", "today"), earnings("earn-upcoming", "upcoming"), earnings("earn-published", "published")],
        )
        prepared = prepare_calendar_update(raw, self.weekdays)
        self.assertFalse(prepared["ready"])
        self.assertIsNone(prepared["payloads"])

    def test_prepare_does_not_mutate_input(self):
        raw = dataset(
            "monday",
            [econ("econ-upcoming", "upcoming")],
            [earnings("earn-upcoming", "upcoming")],
            [econ("econ-prior", "prior_week_published", "2026-10-30")],
            [earnings("earn-prior", "prior_week_published", "2026-10-30")],
        )
        before = repr(raw)
        prepare_calendar_update(raw, self.monday)
        self.assertEqual(repr(raw), before)


if __name__ == "__main__":
    unittest.main()
