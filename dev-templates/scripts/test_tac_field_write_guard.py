import unittest
from pathlib import Path

from tac_field_write_guard import (
    load_registry,
    parse_html,
    select_wrappers,
    update_registered_leaf_text,
    update_registered_source_links,
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
