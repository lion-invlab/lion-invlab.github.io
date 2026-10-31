import unittest
from pathlib import Path

from tac_field_write_guard import (
    load_registry,
    parse_html,
    select_wrappers,
    update_registered_leaf_text,
    update_registered_source_links,
    update_registered_text_segments,
)


ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = {
    "monday": ROOT / "母版專區/TAC_母版_週一_2026-10-28_最終定版.html",
    "weekdays": ROOT / "母版專區/TAC_母版_週二至週五_2026-10-28_最終定版.html",
}
FIELD_PREFIXES = (
    "energy_card_",
    "precious_metals_",
    "fomc_",
    "last_week_econ_",
    "last_week_earnings_",
    "weekly_econ_",
    "weekly_earnings_",
)


class FieldWriteGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = load_registry()

    def _source(self, template):
        return TEMPLATES[template].read_text(encoding="utf-8")

    def _item(self, name):
        return next(x for x in self.registry["selectors"] if x["name"] == name)

    def test_new_field_selectors_match_expected_and_target_leaf_nodes(self):
        for template in ("monday", "weekdays"):
            root = parse_html(self._source(template))
            expected_key = "monday" if template == "monday" else "weekdays"
            for item in self.registry["selectors"]:
                if not item["name"].startswith(FIELD_PREFIXES):
                    continue
                if item["kind"] != "content":
                    continue
                with self.subTest(template=template, selector=item["name"]):
                    matches = select_wrappers(root, item["selector"])
                    self.assertEqual(
                        len(matches), item[expected_key],
                        f"{template}: {item['name']} cardinality changed",
                    )
                    for match in matches:
                        self.assertEqual(
                            len(list(match.etree_element)), 0,
                            f"{template}: {item['name']} is not a leaf node",
                        )

    def test_weekly_economic_calendar_fields_are_writable_leaves_in_both_mothers(self):
        field_names = (
            "weekly_econ_dates",
            "weekly_econ_times",
            "weekly_econ_countries",
            "weekly_econ_names",
            "weekly_econ_stars",
            "weekly_econ_prior_values",
            "weekly_econ_forecast_values",
            "weekly_econ_actual_values",
        )
        for template in ("monday", "weekdays"):
            expected_key = "monday" if template == "monday" else "weekdays"
            for name in field_names:
                with self.subTest(template=template, field=name):
                    root = parse_html(self._source(template))
                    item = self._item(name)
                    matches = select_wrappers(root, item["selector"])
                    self.assertEqual(len(matches), item[expected_key])
                    self.assertTrue(all(len(list(x.etree_element)) == 0 for x in matches))
                    count = update_registered_leaf_text(
                        root, item["selector"], "TEST WEEKLY ECON VALUE", self.registry
                    )
                    self.assertEqual(count, item[expected_key])
                    self.assertTrue(all(
                        x.etree_element.text == "TEST WEEKLY ECON VALUE"
                        for x in matches
                    ))

    def test_weekly_earnings_summary_fields_are_writable_leaves_in_both_mothers(self):
        field_names = (
            "weekly_earnings_us_dates",
            "weekly_earnings_tw_dates",
            "weekly_earnings_company_names",
            "weekly_earnings_company_subtitles",
            "weekly_earnings_stars",
        )
        for template in ("monday", "weekdays"):
            expected_key = "monday" if template == "monday" else "weekdays"
            for name in field_names:
                with self.subTest(template=template, field=name):
                    root = parse_html(self._source(template))
                    item = self._item(name)
                    matches = select_wrappers(root, item["selector"])
                    self.assertEqual(len(matches), item[expected_key])
                    self.assertTrue(all(len(list(x.etree_element)) == 0 for x in matches))
                    count = update_registered_leaf_text(
                        root, item["selector"], "TEST WEEKLY EARNINGS VALUE", self.registry
                    )
                    self.assertEqual(count, item[expected_key])
                    self.assertTrue(all(
                        x.etree_element.text == "TEST WEEKLY EARNINGS VALUE"
                        for x in matches
                    ))

    def test_positive_write_updates_only_registered_leaf(self):
        root = parse_html(self._source("monday"))
        selector = self._item("fomc_meeting_value")["selector"]
        target = select_wrappers(root, selector)
        self.assertEqual(len(target), 1)
        before = target[0].etree_element.text
        updated = update_registered_leaf_text(root, selector, "TEST VALUE", self.registry)
        self.assertEqual(updated, 1)
        self.assertEqual(target[0].etree_element.text, "TEST VALUE")
        self.assertNotEqual(before, "TEST VALUE")

    def test_monday_prior_week_economic_event_fields_are_independent_leaves(self):
        cases = (
            ("last_week_econ_times", "TEST TIME", 3),
            ("last_week_econ_countries", "TEST COUNTRY", 3),
            ("last_week_econ_names", "TEST EVENT NAME", 3),
            ("last_week_econ_prior_values", "TEST PRIOR", 3),
            ("last_week_econ_forecast_values", "TEST FORECAST", 3),
            ("last_week_econ_actual_values", "TEST ACTUAL", 3),
        )
        for name, value, expected in cases:
            with self.subTest(field=name):
                root = parse_html(self._source("monday"))
                selector = self._item(name)["selector"]
                matches = select_wrappers(root, selector)
                self.assertEqual(len(matches), expected)
                self.assertTrue(all(len(list(x.etree_element)) == 0 for x in matches))
                self.assertEqual(update_registered_leaf_text(root, selector, value, self.registry), expected)
                self.assertTrue(all(x.etree_element.text == value for x in matches))

    def test_monday_prior_week_economic_field_labels_are_fixed(self):
        root = parse_html(self._source("monday"))
        selector = self._item("last_week_econ_detail_labels")["selector"]
        labels = select_wrappers(root, selector)
        self.assertEqual(len(labels), 12)
        with self.assertRaises(PermissionError):
            update_registered_leaf_text(root, selector, "replace fixed label", self.registry)

    def test_monday_prior_week_date_leaf_can_be_updated(self):
        root = parse_html(self._source("monday"))
        selector = self._item("last_week_econ_dates")["selector"]
        updated = update_registered_leaf_text(root, selector, "TEST DATE", self.registry)
        self.assertEqual(updated, 3)
        self.assertEqual(
            [x.etree_element.text for x in select_wrappers(root, selector)],
            ["TEST DATE", "TEST DATE", "TEST DATE"],
        )

    def test_monday_earnings_actual_values_are_leaf_nodes(self):
        root = parse_html(self._source("monday"))
        selector = self._item("last_week_earnings_actual_values")["selector"]
        updated = update_registered_leaf_text(root, selector, "TEST VALUE", self.registry)
        self.assertEqual(updated, 28)
        self.assertTrue(all(
            x.etree_element.text == "TEST VALUE"
            for x in select_wrappers(root, selector)
        ))

    def test_monday_earnings_analysis_and_stock_reaction_are_distinct_leaves(self):
        root = parse_html(self._source("monday"))
        for name in ("last_week_earnings_analysis_text_leaf", "last_week_earnings_stock_reaction_text_leaf"):
            selector = self._item(name)["selector"]
            with self.subTest(field=name):
                matches = select_wrappers(root, selector)
                self.assertEqual(len(matches), 7)
                self.assertTrue(all(len(list(x.etree_element)) == 0 for x in matches))
                self.assertEqual(
                    update_registered_leaf_text(root, selector, "TEST FIELD", self.registry),
                    7,
                )
                self.assertTrue(all(x.etree_element.text == "TEST FIELD" for x in matches))

    def test_monday_earnings_source_link_container_is_protected(self):
        root = parse_html(self._source("monday"))
        selector = self._item("last_week_earnings_source_link_container")["selector"]
        matches = select_wrappers(root, selector)
        self.assertEqual(len(matches), 7)
        self.assertTrue(any(list(x.etree_element) for x in matches))
        with self.assertRaises(PermissionError):
            update_registered_leaf_text(root, selector, "overwrite links", self.registry)

    def test_source_links_update_href_and_label_without_replacing_anchor_structure(self):
        root = parse_html(self._source("monday"))
        selector = self._item("last_week_earnings_source_link_leaves")["selector"]
        anchors = select_wrappers(root, selector)
        self.assertEqual(len(anchors), 13)
        first = anchors[0].etree_element
        first.attrib["target"] = "_blank"
        first.attrib["rel"] = "noopener"
        count = update_registered_source_links(
            root,
            selector,
            [{"href": "https://example.com/updated", "label": "Updated source"}]
            + [{"href": f"https://example.com/{i}", "label": f"Source {i}"} for i in range(1, 13)],
            self.registry,
        )
        self.assertEqual(count, 13)
        self.assertEqual(first.attrib["href"], "https://example.com/updated")
        self.assertEqual(first.text, "Updated source")
        self.assertEqual(first.attrib["target"], "_blank")
        self.assertEqual(first.attrib["rel"], "noopener")

    def test_source_link_updater_rejects_unsafe_urls_and_wrong_selectors(self):
        root = parse_html(self._source("monday"))
        selector = self._item("last_week_earnings_source_link_leaves")["selector"]
        links = [{"href": "javascript:alert(1)", "label": "bad"}] + [
            {"href": f"https://example.com/{i}", "label": f"Source {i}"} for i in range(1, 13)
        ]
        with self.assertRaises(ValueError):
            update_registered_source_links(root, selector, links, self.registry)
        with self.assertRaises(PermissionError):
            update_registered_source_links(root, self._item("last_week_earnings_source_link_container")["selector"], [], self.registry)
        with self.assertRaises(ValueError):
            update_registered_source_links(root, selector, links[:-1], self.registry)

    def test_monday_economic_source_links_are_four_registered_anchor_leaves(self):
        root = parse_html(self._source("monday"))
        selector = self._item("last_week_econ_source_link_leaves")["selector"]
        anchors = select_wrappers(root, selector)
        self.assertEqual(len(anchors), 4)
        self.assertTrue(all(x.etree_element.tag.lower() == "a" for x in anchors))
        self.assertTrue(all(len(list(x.etree_element)) == 0 for x in anchors))
        count = update_registered_source_links(
            root,
            selector,
            [{"href": f"https://example.com/econ-{i}", "label": f"Economic source {i}"} for i in range(4)],
            self.registry,
        )
        self.assertEqual(count, 4)
        self.assertEqual(
            [x.etree_element.attrib["href"] for x in anchors],
            [f"https://example.com/econ-{i}" for i in range(4)],
        )

    def test_sentiment_change_cnn_status_and_core_text_leaves_are_writable(self):
        root = parse_html(self._source("monday"))
        names = (
            "vix_sentiment_change",
            "move_sentiment_change",
            "cnn_fear_greed_status_english",
            "cnn_fear_greed_status_chinese",
            "sentiment_core_interpretation_text",
        )
        for name in names:
            selector = self._item(name)["selector"]
            with self.subTest(field=name):
                matches = select_wrappers(root, selector)
                self.assertEqual(len(matches), 1)
                self.assertTrue(all(len(list(x.etree_element)) == 0 for x in matches))
                self.assertEqual(
                    update_registered_leaf_text(root, selector, "TEST LEAF", self.registry),
                    1,
                )
                self.assertEqual(matches[0].etree_element.text, "TEST LEAF")

    def test_composite_sentiment_and_focus_containers_are_protected(self):
        root = parse_html(self._source("monday"))
        names = (
            "today_market_focus",
            "cnn_fear_greed_status",
            "cnn_fear_greed_marker",
            "sentiment_core_interpretation",
        )
        for name in names:
            selector = self._item(name)["selector"]
            with self.subTest(field=name):
                with self.assertRaises(PermissionError):
                    update_registered_leaf_text(root, selector, "overwrite", self.registry)

    def test_registry_has_no_duplicate_css_selectors(self):
        selectors = [item["selector"] for item in self.registry["selectors"]]
        self.assertEqual(len(selectors), len(set(selectors)))

    def test_today_observation_text_segments_update_without_replacing_markup(self):
        root = parse_html(self._source("monday"))
        cases = (
            ("today_market_focus", ["Updated market view"]),
            ("today_key_levels", [
                "Updated Dow levels", "Updated S&P levels", "Updated Nasdaq levels",
                "Updated SOX levels", "Updated Russell levels",
            ]),
            ("today_core_callout", ["Updated core observation"]),
        )
        for name, values in cases:
            with self.subTest(field=name):
                selector = self._item(name)["selector"]
                matches = select_wrappers(root, selector)
                self.assertEqual(len(matches), 1)
                parent = matches[0].etree_element
                original_tags = [child.tag.lower() for child in list(parent)]
                count = update_registered_text_segments(root, selector, values, self.registry)
                self.assertEqual(count, len(values))
                self.assertEqual([child.tag.lower() for child in list(parent)], original_tags)
                segments = self._item(name)["segments"]
                self.assertEqual(
                    [list(parent)[x["child_index"]].tail for x in segments],
                    values,
                )

    def test_text_segment_updater_rejects_bad_count_structure_and_leaf_writer(self):
        root = parse_html(self._source("monday"))
        item = self._item("today_key_levels")
        with self.assertRaises(ValueError):
            update_registered_text_segments(root, item["selector"], ["only one"], self.registry)
        with self.assertRaises(PermissionError):
            update_registered_leaf_text(root, item["selector"], "overwrite", self.registry)
        broken = parse_html(self._source("monday"))
        parent = select_wrappers(broken, item["selector"])[0].etree_element
        parent[0].tag = "span"
        with self.assertRaises(PermissionError):
            update_registered_text_segments(
                broken, item["selector"], ["a", "b", "c", "d", "e"], self.registry
            )

    def test_summary_headline_is_writable_but_composite_body_is_protected(self):
        root = parse_html(self._source("monday"))
        headline = self._item("summary_title")["selector"]
        matches = select_wrappers(root, headline)
        self.assertEqual(len(matches), 1)
        self.assertEqual(len(list(matches[0].etree_element)), 0)
        self.assertEqual(update_registered_leaf_text(root, headline, "TEST HEADLINE", self.registry), 1)
        self.assertEqual(matches[0].etree_element.text, "TEST HEADLINE")

        body = self._item("summary_body")["selector"]
        with self.assertRaises(PermissionError):
            update_registered_leaf_text(root, body, "overwrite all summary text", self.registry)

    def test_protected_observation_container_is_rejected(self):
        root = parse_html(self._source("monday"))
        selector = self._item("energy_card_observation")["selector"]
        with self.assertRaises(PermissionError):
            update_registered_leaf_text(root, selector, "overwrite", self.registry)

    def test_fixed_calendar_labels_are_rejected(self):
        root = parse_html(self._source("monday"))
        selectors = (
            self._item("last_week_econ_detail_labels")["selector"],
            self._item("last_week_earnings_result_labels")["selector"],
            self._item("last_week_earnings_analysis_labels")["selector"],
            self._item("last_week_earnings_analysis_values")["selector"],
        )
        for selector in selectors:
            with self.subTest(selector=selector):
                with self.assertRaises(PermissionError):
                    update_registered_leaf_text(root, selector, "overwrite", self.registry)

    def test_toggle_and_unknown_selectors_are_rejected(self):
        root = parse_html(self._source("monday"))
        for selector in (
            "#last-week-earnings .earnings-accordion-toggle",
            "#last-week-calendar details.last-week-calendar-collapse > summary",
            ".not-registered",
        ):
            with self.subTest(selector=selector):
                with self.assertRaises(PermissionError):
                    update_registered_leaf_text(root, selector, "overwrite", self.registry)

    def test_nested_target_is_rejected_even_if_selector_is_allowlisted(self):
        root = parse_html("<html><body><div class='slot'><span>protected child</span></div></body></html>")
        synthetic = {"selectors": [{"name": "synthetic", "selector": ".slot", "kind": "content"}]}
        with self.assertRaises(PermissionError):
            update_registered_leaf_text(root, ".slot", "overwrite", synthetic)


if __name__ == "__main__":
    unittest.main()
