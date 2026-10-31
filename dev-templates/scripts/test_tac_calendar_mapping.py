import unittest

from tac_calendar_field_mapper import map_calendar_dataset
from test_tac_calendar_field_mapper import dataset


class CalendarMappingIntegrationTests(unittest.TestCase):
    def test_mapping_adapter_uses_canonical_field_mapper(self):
        mapped = map_calendar_dataset(dataset())
        self.assertEqual(mapped["template"], "monday")
        self.assertEqual(len(mapped["weekly_economic"]["upcoming"]), 1)
        self.assertEqual(len(mapped["weekly_earnings"]["upcoming"]), 1)
        self.assertEqual(mapped["weekly_economic"]["upcoming"][0]["summary"]["name"], "CPI")

    def test_mapping_keeps_prior_week_groups_separate(self):
        mapped = map_calendar_dataset(dataset())
        self.assertIn("prior_week_published", mapped["prior_week_economic"])
        self.assertEqual(mapped["prior_week_economic"]["prior_week_published"], [])


if __name__ == "__main__":
    unittest.main()
