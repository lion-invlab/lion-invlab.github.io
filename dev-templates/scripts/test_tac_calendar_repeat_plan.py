import unittest

from tac_calendar_dataset import SCHEMA_VERSION
from tac_calendar_group_inventory import MOTHERS, inventory_mother
from tac_calendar_repeat_plan import plan_calendar_repeat_updates


def source():
    return [{
        "source_name": "Official",
        "field_label": "資料來源",
        "label": "Official",
        "url": "https://example.com/source",
        "accessed_at": "2026-10-31T12:00:00+08:00",
    }]


def econ(event_id, status_group):
    return {
        "event_id": event_id, "event_date": "2026-11-02",
        "event_time": "09:00", "event_timezone": "Asia/Taipei",
        "status_group": status_group, "country": "US",
        "event_name": "CPI", "importance": 5, "source_records": source(),
    }


def earnings(event_id, status_group):
    return {
        "event_id": event_id, "event_date": "2026-11-02",
        "event_time": "08:30", "event_timezone": "America/New_York",
        "status_group": status_group, "taiwan_display_date": "2026-11-02",
        "company_name": "Example Corp", "subtitle": "Results",
        "importance": 5, "release_session": "pre_market",
        "source_records": source(),
    }


def dataset(template, economic, earnings_rows, prior_economic=None, prior_earnings=None):
    return {
        "schema_version": SCHEMA_VERSION,
        "report_date": "2026-11-02",
        "template": template,
        "economic_events": economic,
        "earnings_events": earnings_rows,
        "prior_week_economic_events": prior_economic or [],
        "prior_week_earnings_events": prior_earnings or [],
    }


class CalendarRepeatPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.monday_inventory = inventory_mother("monday")
        cls.weekdays_inventory = inventory_mother("weekdays")

    def test_monday_valid_existing_group_plan_passes(self):
        data = dataset(
            "monday",
            [econ("upcoming-e", "upcoming")],
            [earnings("upcoming-r", "upcoming")],
            [econ("prior-e", "prior_week_published")],
            [earnings("prior-r", "prior_week_published")],
        )
        plan = plan_calendar_repeat_updates(data, self.monday_inventory)
        self.assertTrue(plan["pass"], plan)
        self.assertFalse(plan["mutation_performed"])
        self.assertEqual(
            plan["sections"]["weekly_economic"]["groups"][0]["action"],
            "keep_empty_state",
        )
        self.assertEqual(
            plan["sections"]["weekly_economic"]["groups"][1]["action"],
            "render_list",
        )

    def test_monday_blocks_new_today_cards_without_same_group_prototype(self):
        data = dataset("monday", [econ("today-e", "today")], [], [], [])
        plan = plan_calendar_repeat_updates(data, self.monday_inventory)
        self.assertFalse(plan["pass"])
        today = plan["sections"]["weekly_economic"]["groups"][0]
        self.assertEqual(today["reason"], "same_group_card_prototype_missing")

    def test_monday_blocks_new_published_cards_without_same_group_prototype(self):
        data = dataset("monday", [econ("published-e", "published")], [], [], [])
        plan = plan_calendar_repeat_updates(data, self.monday_inventory)
        self.assertFalse(plan["pass"])
        published = plan["sections"]["weekly_economic"]["groups"][2]
        self.assertEqual(published["reason"], "same_group_card_prototype_missing")

    def test_monday_prior_week_existing_prototypes_allow_card_plan(self):
        data = dataset(
            "monday",
            [econ("weekly-e", "upcoming")],
            [earnings("weekly-r", "upcoming")],
            [econ("prior-e", "prior_week_published")],
            [earnings("prior-r", "prior_week_published")],
        )
        plan = plan_calendar_repeat_updates(data, self.monday_inventory)
        self.assertTrue(plan["pass"], plan)

    def test_monday_prior_week_empty_is_blocked_without_empty_state_prototype(self):
        data = dataset("monday", [], [], [], [])
        plan = plan_calendar_repeat_updates(data, self.monday_inventory)
        self.assertFalse(plan["pass"])
        self.assertEqual(
            plan["sections"]["prior_week_economic"]["groups"][0]["reason"],
            "same_section_empty_state_prototype_missing",
        )

    def test_monday_blocks_empty_transition_without_status_specific_message_mapping(self):
        data = dataset(
            "monday",
            [econ("upcoming-e", "upcoming")],
            [earnings("upcoming-r", "upcoming")],
            [econ("prior-e", "prior_week_published")],
            [earnings("prior-r", "prior_week_published")],
        )
        data["economic_events"] = []
        plan = plan_calendar_repeat_updates(data, self.monday_inventory)
        self.assertFalse(plan["pass"])
        upcoming = plan["sections"]["weekly_economic"]["groups"][1]
        self.assertEqual(upcoming["reason"], "empty_state_text_mapping_missing")

    def test_weekdays_all_three_status_groups_can_be_populated(self):
        data = dataset(
            "weekdays",
            [econ("today-e", "today"), econ("upcoming-e", "upcoming"), econ("published-e", "published")],
            [earnings("today-r", "today"), earnings("upcoming-r", "upcoming"), earnings("published-r", "published")],
        )
        plan = plan_calendar_repeat_updates(data, self.weekdays_inventory)
        self.assertTrue(plan["pass"], plan)

    def test_weekdays_empty_status_group_is_blocked_without_empty_prototype(self):
        data = dataset(
            "weekdays",
            [econ("upcoming-e", "upcoming"), econ("published-e", "published")],
            [earnings("today-r", "today"), earnings("upcoming-r", "upcoming"), earnings("published-r", "published")],
        )
        plan = plan_calendar_repeat_updates(data, self.weekdays_inventory)
        self.assertFalse(plan["pass"])
        today = plan["sections"]["weekly_economic"]["groups"][0]
        self.assertEqual(today["reason"], "same_section_empty_state_prototype_missing")

    def test_inventory_template_mismatch_is_rejected(self):
        data = dataset("monday", [], [], [econ("prior-e", "prior_week_published")], [earnings("prior-r", "prior_week_published")])
        with self.assertRaisesRegex(ValueError, "must match"):
            plan_calendar_repeat_updates(data, self.weekdays_inventory)


if __name__ == "__main__":
    unittest.main()
