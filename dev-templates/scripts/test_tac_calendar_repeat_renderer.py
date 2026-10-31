import unittest

from tac_calendar_group_inventory import MOTHERS, inventory_mother
from tac_calendar_dataset import SCHEMA_VERSION
from tac_calendar_repeat_renderer import render_weekly_calendar_updates
from tac_field_write_guard import parse_html, select_wrappers


def _prototype_details(template, section_selector, list_selector, card_selector, field_class):
    from tac_calendar_repeat_renderer import _group_targets, _field_map, _parse, SECTION_CONFIG
    source = MOTHERS[template].read_text(encoding="utf-8")
    root = _parse(source)
    config = SECTION_CONFIG["weekly_economic" if field_class == "econ-field" else "weekly_earnings"]
    targets = _group_targets(root, section_selector, list_selector, card_selector)
    result = {}
    for status, target in targets.items():
        if not target["cards"]:
            continue
        candidates = []
        for card in target["cards"]:
            fields = _field_map(card, field_class,
                                "econ-value" if field_class == "econ-field" else "earnings-detail-value")
            source_labels = {
                label: len(list(value)) for label, value in fields.items()
                if list(value) and all(child.tag.lower() == "a" for child in list(value))
            }
            details = [label for label, value in fields.items() if label not in source_labels]
            candidates.append({"details": details, "sources": source_labels})
            if source_labels:
                break
        result[status] = candidates[-1]
    return result


def _records(template):
    econ_schema = _prototype_details(
        template, "#calendar", ".econ-event-list", ".econ-event", "econ-field"
    )
    earnings_schema = _prototype_details(
        template, "#earnings", ".earnings-accordion-list", ".earnings-accordion",
        "earnings-detail-field",
    )
    statuses = ("today", "upcoming", "published") if template == "weekdays" else ("upcoming",)

    def make_sources(schema, field_label):
        rows = []
        for label, count in schema["sources"].items():
            for index in range(count):
                rows.append({
                    "source_name": "Fixture source",
                    "field_label": label,
                    "label": f"Fixture {index + 1}",
                    "url": f"https://example.com/{field_label}/{index + 1}",
                    "accessed_at": "2026-10-31T12:00:00+08:00",
                })
        return rows

    economic, earnings = [], []
    for status in statuses:
        e_schema = econ_schema[status]
        economic.append({
            "event_id": f"econ-{status}", "event_date": "2026-11-03",
            "event_time": "09:00", "event_timezone": "Asia/Taipei",
            "status_group": status, "country": "美國", "event_name": f"CPI {status}",
            "importance": 5,
            "details": {label: f"{label} {status}" for label in e_schema["details"]},
            "source_records": make_sources(e_schema, "econ"),
        })
        r_schema = earnings_schema[status]
        earnings.append({
            "event_id": f"earn-{status}", "event_date": "2026-11-03",
            "event_time": "08:30", "event_timezone": "America/New_York",
            "taiwan_display_date": "2026-11-03", "status_group": status,
            "company_name": f"Example {status}", "subtitle": "EX｜軟體",
            "importance": 5, "release_session": "pre_market",
            "details": {label: f"{label} {status}" for label in r_schema["details"]},
            "source_records": make_sources(r_schema, "earn"),
        })
    return {
        "schema_version": SCHEMA_VERSION, "report_date": "2026-11-02",
        "template": template, "economic_events": economic, "earnings_events": earnings,
        "prior_week_economic_events": [], "prior_week_earnings_events": [],
    }


def _prior_week_economic_record():
    schema = _prototype_details(
        "monday", "#last-week-calendar", ".econ-event-list", ".econ-event", "econ-field"
    )["prior_week_published"]
    sources = []
    for label, count in schema["sources"].items():
        for index in range(count):
            sources.append({
                "source_name": "Fixture prior-week source",
                "field_label": label,
                "label": f"Prior fixture {index + 1}",
                "url": f"https://example.com/prior-econ/{index + 1}",
                "accessed_at": "2026-10-31T12:00:00+08:00",
            })
    return {
        "event_id": "prior-econ-1", "event_date": "2026-10-27",
        "event_time": "20:30", "event_timezone": "Asia/Taipei",
        "status_group": "prior_week_published", "country": "美國",
        "event_name": "Prior-week CPI", "importance": 5,
        "details": {label: f"{label} prior-week" for label in schema["details"]},
        "source_records": sources,
    }


class CalendarRepeatRendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.monday_html = MOTHERS["monday"].read_text(encoding="utf-8")
        cls.weekdays_html = MOTHERS["weekdays"].read_text(encoding="utf-8")
        cls.monday_inventory = inventory_mother("monday")
        cls.weekdays_inventory = inventory_mother("weekdays")

    def test_weekday_all_three_status_groups_render_and_validate(self):
        result = render_weekly_calendar_updates(
            self.weekdays_html, _records("weekdays"), self.weekdays_inventory
        )
        self.assertTrue(result["report"]["structural_validation"]["pass"])
        self.assertTrue(result["report"]["mutation_performed"])
        root = parse_html(result["html"])
        self.assertEqual(len(select_wrappers(root, "#calendar .econ-event")), 3)
        self.assertEqual(len(select_wrappers(root, "#earnings .earnings-accordion")), 3)

    def test_monday_upcoming_groups_render_without_touching_prior_week_sections(self):
        result = render_weekly_calendar_updates(
            self.monday_html, _records("monday"), self.monday_inventory
        )
        self.assertTrue(result["report"]["structural_validation"]["pass"])
        self.assertIn('id="last-week-calendar"', result["html"])
        self.assertIn('id="last-week-earnings"', result["html"])
        self.assertEqual(result["report"]["sections"]["weekly_economic"]["today"]["action"], "keep_empty_state")
        self.assertEqual(result["report"]["sections"]["weekly_earnings"]["published"]["action"], "keep_empty_state")

    def test_multiple_events_clone_same_group_prototype_and_shrink_existing_list(self):
        data = _records("weekdays")
        econ_rows = data["economic_events"]
        earnings_rows = data["earnings_events"]
        data["economic_events"] = [
            econ_rows[0],
            dict(econ_rows[1], event_id="econ-up-1"),
            dict(econ_rows[1], event_id="econ-up-2"),
            econ_rows[2],
        ]
        data["earnings_events"] = [
            earnings_rows[0],
            dict(earnings_rows[1], event_id="earn-up-1"),
            dict(earnings_rows[1], event_id="earn-up-2"),
            earnings_rows[2],
        ]
        result = render_weekly_calendar_updates(
            self.weekdays_html, data, self.weekdays_inventory
        )
        root = parse_html(result["html"])
        self.assertEqual(len(select_wrappers(root, "#calendar .econ-event")), 4)
        self.assertEqual(len(select_wrappers(root, "#earnings .earnings-accordion")), 4)

    def test_monday_prior_week_economic_cards_render_from_same_group_prototype(self):
        data = _records("monday")
        data["prior_week_economic_events"] = [_prior_week_economic_record()]
        result = render_weekly_calendar_updates(
            self.monday_html, data, self.monday_inventory
        )
        root = parse_html(result["html"])
        cards = select_wrappers(root, "#last-week-calendar .econ-event")
        self.assertEqual(len(cards), 1)
        self.assertEqual(
            select_wrappers(root, "#last-week-calendar .econ-name")[0].etree_element.text,
            "Prior-week CPI",
        )
        source = select_wrappers(root, "#last-week-calendar .econ-value a")[0].etree_element
        self.assertTrue(source.attrib["href"].startswith("https://example.com/prior-econ/"))
        self.assertEqual(len(select_wrappers(root, "#last-week-earnings .earnings-accordion")), 7)

    def test_monday_today_card_is_blocked_without_same_group_prototype(self):
        data = _records("monday")
        data["economic_events"].append(dict(data["economic_events"][0], event_id="econ-today", status_group="today"))
        with self.assertRaisesRegex(PermissionError, "prototype is unavailable|no today group"):
            render_weekly_calendar_updates(self.monday_html, data, self.monday_inventory)

    def test_empty_transition_is_blocked_without_approved_empty_state(self):
        data = _records("weekdays")
        data["economic_events"] = [row for row in data["economic_events"] if row["status_group"] != "today"]
        with self.assertRaisesRegex(PermissionError, "empty-state transition"):
            render_weekly_calendar_updates(self.weekdays_html, data, self.weekdays_inventory)

    def test_prior_week_earnings_payload_is_blocked_without_result_grid_mapping(self):
        data = _records("monday")
        prior = dict(data["earnings_events"][0], event_id="prior-earnings",
                     status_group="prior_week_published")
        data["prior_week_earnings_events"] = [prior]
        with self.assertRaisesRegex(PermissionError, "prior-week earnings cards require"):
            render_weekly_calendar_updates(self.monday_html, data, self.monday_inventory)

    def test_detail_schema_mismatch_is_rejected(self):
        data = _records("weekdays")
        data["economic_events"][1]["details"]["未授權欄位"] = "value"
        with self.assertRaisesRegex(PermissionError, "non-allowlisted labels|no same-group prototype"):
            render_weekly_calendar_updates(self.weekdays_html, data, self.weekdays_inventory)

    def test_source_anchor_count_mismatch_is_rejected(self):
        data = _records("weekdays")
        original = data["economic_events"][1]["source_records"][0]
        data["economic_events"][1]["source_records"] = [
            dict(original, label=f"Extra source {index}") for index in range(99)
        ]
        with self.assertRaisesRegex(PermissionError, "no same-group prototype"):
            render_weekly_calendar_updates(self.weekdays_html, data, self.weekdays_inventory)

    def test_stale_inventory_is_rejected_against_source_html(self):
        data = _records("weekdays")
        stale = dict(self.weekdays_inventory)
        stale["sections"] = dict(stale["sections"])
        stale["sections"]["weekly_economic"] = dict(stale["sections"]["weekly_economic"])
        stale["sections"]["weekly_economic"]["groups"] = list(
            stale["sections"]["weekly_economic"]["groups"]
        )
        stale["sections"]["weekly_economic"]["groups"][0] = dict(
            stale["sections"]["weekly_economic"]["groups"][0]
        )
        stale["sections"]["weekly_economic"]["groups"][0]["card_count"] += 1
        with self.assertRaisesRegex(ValueError, "does not match"):
            render_weekly_calendar_updates(self.weekdays_html, data, stale)

    def test_unsafe_source_url_is_rejected_before_returning_html(self):
        data = _records("weekdays")
        data["economic_events"][1]["source_records"][0]["url"] = "javascript:alert(1)"
        with self.assertRaisesRegex(ValueError, "HTTP"):
            render_weekly_calendar_updates(self.weekdays_html, data, self.weekdays_inventory)


if __name__ == "__main__":
    unittest.main()
