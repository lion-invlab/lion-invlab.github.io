import unittest

from tac_calendar_sort import sort_economic_events, sort_earnings_events


class CalendarSortTests(unittest.TestCase):
    def test_economic_events_sort_by_iso_date_and_local_time(self):
        events = [
            {"name": "late", "event_date": "2026-10-28", "event_time": "22:00"},
            {"name": "next-day", "event_date": "2026-10-29", "event_time": "02:00"},
            {"name": "early", "event_date": "2026-10-28", "event_time": "08:30"},
            {"name": "unknown-time", "event_date": "2026-10-28", "event_time": None},
        ]
        result = sort_economic_events(events)
        self.assertEqual([x["name"] for x in result], ["early", "late", "unknown-time", "next-day"])
        self.assertEqual(events[0]["name"], "late", "sorting must not mutate the input list")

    def test_economic_sort_handles_year_boundary(self):
        events = [
            {"name": "jan", "event_date": "2027-01-02", "event_time": "09:00"},
            {"name": "dec", "event_date": "2026-12-31", "event_time": "23:00"},
        ]
        self.assertEqual(
            [x["name"] for x in sort_economic_events(events)],
            ["dec", "jan"],
        )

    def test_earnings_sort_uses_us_publication_date_and_session(self):
        events = [
            {"name": "after", "event_date": "2026-10-28", "release_session": "after_market", "event_time": None, "taiwan_display_date": "10/29"},
            {"name": "pre", "event_date": "2026-10-28", "release_session": "pre_market", "event_time": None, "taiwan_display_date": "10/28"},
            {"name": "prior", "event_date": "2026-10-27", "release_session": "after_market", "event_time": None, "taiwan_display_date": "10/28"},
            {"name": "unknown", "event_date": "2026-10-28", "release_session": "unspecified", "event_time": None, "taiwan_display_date": "10/29"},
        ]
        self.assertEqual(
            [x["name"] for x in sort_earnings_events(events)],
            ["prior", "pre", "after", "unknown"],
        )

    def test_earnings_same_session_sorts_by_known_time_stably(self):
        events = [
            {"name": "later", "event_date": "2026-10-28", "release_session": "pre_market", "event_time": "08:30"},
            {"name": "earlier", "event_date": "2026-10-28", "release_session": "pre_market", "event_time": "06:00"},
            {"name": "unknown", "event_date": "2026-10-28", "release_session": "pre_market", "event_time": None},
            {"name": "same-time-first", "event_date": "2026-10-28", "release_session": "after_market", "event_time": "16:00"},
            {"name": "same-time-second", "event_date": "2026-10-28", "release_session": "after_market", "event_time": "16:00"},
        ]
        self.assertEqual(
            [x["name"] for x in sort_earnings_events(events)],
            ["earlier", "later", "unknown", "same-time-first", "same-time-second"],
        )

    def test_invalid_dates_and_times_are_rejected(self):
        with self.assertRaises(ValueError):
            sort_economic_events([{"event_date": "10/28", "event_time": "08:00"}])
        with self.assertRaises(ValueError):
            sort_economic_events([{"event_date": "2026-10-28", "event_time": "25:61"}])


if __name__ == "__main__":
    unittest.main()
