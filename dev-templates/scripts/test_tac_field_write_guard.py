import unittest
from pathlib import Path

from tac_field_write_guard import (
    load_registry,
    parse_html,
    select_wrappers,
    update_registered_leaf_text,
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
