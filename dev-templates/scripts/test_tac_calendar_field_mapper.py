import unittest

from tac_calendar_dataset import SCHEMA_VERSION
from tac_calendar_field_mapper import (
    format_calendar_date, format_stars, map_calendar_dataset,
    map_economic_event, map_earnings_event,
)


def source(field_label="資料來源"):
    return [{
        "source_name": "Official",
        "field_label": field_label,
        "label": "Official release",
        "url": "https://example.com/release",
        "accessed_at": "2026-10-31T10:00:00+08:00",
    }]


def econ(event_id="econ-1", event_time="08:30", **extra):
    return {
        "event_id": event_id, "event_date": "2026-11-03",
        "event_time": event_time, "event_timezone": "Asia/Taipei",
        "status_group": "upcoming", "country": "美國",
        "event_name": "CPI", "importance": 4,
        "source_records": source(), **extra,
    }


def earnings(event_id="earn-1", event_time="16:00", **extra):
    return {
        "event_id": event_id, "event_date": "2026-11-03",
        "event_time": event_time, "event_timezone": "America/New_York",
        "status_group": "upcoming", "taiwan_display_date": "2026-11-04",
        "company_name": "Example Corp", "subtitle": "EX｜軟體",
        "importance": 5, "release_session": "after_market",
        "source_records": source("來源"), **extra,
    }


def dataset():
    return {
        "schema_version": SCHEMA_VERSION, "report_date": "2026-11-02",
        "template": "monday",
        "economic_events": [econ(details={"前值": "3.0%", "市場預估": "3.1%"})],
        "earnings_events": [earnings(details={"EPS 共識": "US$1.20"})],
        "prior_week_economic_events": [],
        "prior_week_earnings_events": [],
    }


class CalendarFieldMapperTests(unittest.TestCase):
    def test_format_calendar_date_uses_chinese_weekday(self):
        self.assertEqual(format_calendar_date("2026-11-02"), "11/02（一）")

    def test_format_stars_preserves_five_star_scale(self):
        self.assertEqual(format_stars(4), "★★★★☆")
        self.assertEqual(format_stars(5), "★★★★★")

    def test_economic_event_maps_summary_details_and_sources(self):
        mapped = map_economic_event(econ(details={"前值": "3.0%"}))
        self.assertEqual(mapped["summary"]["date"], "11/03（二）")
        self.assertEqual(mapped["summary"]["time"], "08:30")
        self.assertEqual(mapped["summary"]["stars"], "★★★★☆")
        self.assertEqual(mapped["details"]["前值"], "3.0%")
        self.assertEqual(mapped["sources"]["資料來源"][0]["href"], "https://example.com/release")
        self.assertEqual(mapped["provenance"][0]["source_name"], "Official")

    def test_unknown_economic_time_is_explicit_not_guessed(self):
        mapped = map_economic_event(econ(event_time=None))
        self.assertEqual(mapped["summary"]["time"], "待核實")

    def test_earnings_event_converts_us_time_to_taiwan_time(self):
        mapped = map_earnings_event(earnings())
        self.assertEqual(mapped["summary"]["us_date"], "11/03（二） 盤後")
        self.assertEqual(mapped["summary"]["taiwan_date"], "台灣時間 11/04（三） 05:00")
        self.assertEqual(mapped["sources"]["來源"][0]["label"], "Official release")

    def test_earnings_without_exact_time_keeps_explicit_taiwan_date(self):
        mapped = map_earnings_event(earnings(event_time=None))
        self.assertEqual(mapped["summary"]["taiwan_date"], "台灣時間 11/04（三）")

    def test_dataset_mapping_keeps_template_and_status_groups_separate(self):
        mapped = map_calendar_dataset(dataset())
        self.assertEqual(mapped["template"], "monday")
        self.assertEqual(len(mapped["weekly_economic"]["upcoming"]), 1)
        self.assertEqual(len(mapped["weekly_earnings"]["upcoming"]), 1)
        self.assertEqual(mapped["prior_week_economic"]["prior_week_published"], [])

    def test_mapping_does_not_mutate_input(self):
        raw = dataset()
        before = repr(raw)
        map_calendar_dataset(raw)
        self.assertEqual(repr(raw), before)


if __name__ == "__main__":
    unittest.main()
