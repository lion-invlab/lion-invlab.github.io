import unittest

from tac_calendar_group_inventory import MOTHERS, SECTIONS, inventory_calendar_groups


class CalendarGroupInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._monday = inventory_calendar_groups(
            MOTHERS["monday"].read_text(encoding="utf-8"), "monday"
        )["sections"]
        cls._weekdays = inventory_calendar_groups(
            MOTHERS["weekdays"].read_text(encoding="utf-8"), "weekdays"
        )["sections"]

    def test_both_locked_mothers_are_available(self):
        for path in MOTHERS.values():
            self.assertTrue(path.is_file(), str(path))

    def test_monday_has_prior_week_sections(self):
        html = MOTHERS["monday"].read_text(encoding="utf-8")
        result = inventory_calendar_groups(html, "monday")
        self.assertTrue(result["sections"]["prior_week_economic"]["present"])
        self.assertTrue(result["sections"]["prior_week_earnings"]["present"])

    def test_weekdays_do_not_invent_prior_week_sections(self):
        html = MOTHERS["weekdays"].read_text(encoding="utf-8")
        result = inventory_calendar_groups(html, "weekdays")
        self.assertFalse(result["sections"]["prior_week_economic"]["present"])
        self.assertFalse(result["sections"]["prior_week_earnings"]["present"])

    def test_inventory_reports_every_applicable_section(self):
        monday = inventory_calendar_groups(
            MOTHERS["monday"].read_text(encoding="utf-8"), "monday"
        )
        weekdays = inventory_calendar_groups(
            MOTHERS["weekdays"].read_text(encoding="utf-8"), "weekdays"
        )
        self.assertEqual(set(monday["sections"]), set(SECTIONS))
        self.assertEqual(set(weekdays["sections"]), set(SECTIONS))

    def test_each_existing_status_group_is_explicitly_inventoried(self):
        for template, path in MOTHERS.items():
            report = inventory_calendar_groups(path.read_text(encoding="utf-8"), template)
            self.assertTrue(report["pass"], f"{template}: {report}")
            for section in report["sections"].values():
                if section["present"]:
                    self.assertTrue(section["groups"])
                    for group in section["groups"]:
                        self.assertIn(group["status_key"], {"today", "upcoming", "published", "prior_week_published"})
                        self.assertTrue(group["heading_text"])
                        self.assertIn("has_same_group_card_prototype", group)
                        self.assertIn("can_clone_without_cross_group_prototype", group)

    def test_monday_weekly_groups_distinguish_today_upcoming_and_published(self):
        for section_name in ("weekly_economic", "weekly_earnings"):
            section = self._monday[section_name]
            self.assertEqual(
                [group["status_key"] for group in section["groups"]],
                ["today", "upcoming", "published"],
            )
            self.assertFalse(section["groups"][0]["has_same_group_card_prototype"])
            self.assertTrue(section["groups"][1]["has_same_group_card_prototype"])
            self.assertFalse(section["groups"][2]["has_same_group_card_prototype"])

    def test_weekday_weekly_groups_have_same_group_prototypes(self):
        for section_name in ("weekly_economic", "weekly_earnings"):
            section = self._weekdays[section_name]
            self.assertEqual(
                [group["status_key"] for group in section["groups"]],
                ["today", "upcoming", "published"],
            )
            self.assertTrue(all(
                group["can_clone_without_cross_group_prototype"]
                for group in section["groups"]
            ))

    def test_monday_prior_week_groups_have_same_group_prototypes(self):
        for section_name in ("prior_week_economic", "prior_week_earnings"):
            section = self._monday[section_name]
            self.assertEqual(
                [group["status_key"] for group in section["groups"]],
                ["prior_week_published"],
            )
            self.assertTrue(all(
                group["can_clone_without_cross_group_prototype"]
                for group in section["groups"]
            ))

    def test_invalid_template_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "template"):
            inventory_calendar_groups("<html></html>", "both")


if __name__ == "__main__":
    unittest.main()
