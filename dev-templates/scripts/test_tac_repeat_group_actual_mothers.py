"""Integration tests: mutate repeat cards in copies of the locked mother templates."""
from copy import deepcopy
from pathlib import Path
import unittest

import cssselect2
import html5lib

from tac_repeat_group_validator import GroupSpec, validate_repeat_groups


ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = {
    "monday": ROOT / "母版專區/TAC_母版_週一_2026-10-28_最終定版.html",
    "weekdays": ROOT / "母版專區/TAC_母版_週二至週五_2026-10-28_最終定版.html",
}
GROUPS = [
    GroupSpec("weekly_economic", "#calendar .econ-event-list", ".econ-event"),
    GroupSpec("weekly_earnings", "#earnings .earnings-accordion-list", ".earnings-accordion"),
    GroupSpec("last_week_economic", "#last-week-calendar .econ-event-list", ".econ-event"),
    GroupSpec("last_week_earnings", "#last-week-earnings .earnings-accordion-list", ".earnings-accordion"),
]


def query(root, selector):
    wrapper = cssselect2.ElementWrapper.from_html_root(root)
    return [item.etree_element for item in wrapper.query_all(selector)]


def direct_cards(root, wrapper, selector):
    wrapped = cssselect2.ElementWrapper.from_html_root(root)
    return [
        item.etree_element for item in wrapped.query_all(selector)
        if item.parent is not None and item.parent.etree_element is wrapper
    ]


def serialize(root):
    return html5lib.serialize(
        root, tree="etree", omit_optional_tags=False,
        quote_attr_values="always", alphabetical_attributes=True,
    )


def clone_root(source):
    return html5lib.parse(source, treebuilder="etree", namespaceHTMLElements=False)


class ActualMotherRepeatGroupTests(unittest.TestCase):
    def _load(self, path):
        self.assertTrue(path.exists(), f"Missing locked mother template: {path}")
        source = path.read_text(encoding="utf-8")
        return source, clone_root(source)

    def _applicable_groups(self, root, template_name):
        return [
            spec for spec in GROUPS
            if query(root, spec.wrapper_selector)
        ]

    def test_real_mother_all_repeat_groups_allow_exact_clone_addition(self):
        for template_name, path in TEMPLATES.items():
            with self.subTest(template=template_name):
                source, root = self._load(path)
                candidate = deepcopy(root)
                specs = self._applicable_groups(root, template_name)
                self.assertTrue(specs, "No calendar repeat groups located")
                changed = 0
                for spec in specs:
                    for wrapper in query(candidate, spec.wrapper_selector):
                        cards = direct_cards(candidate, wrapper, spec.child_selector)
                        if cards:
                            wrapper.append(deepcopy(cards[0]))
                            changed += 1
                self.assertGreater(changed, 0, "No real event cards available to clone")
                result = validate_repeat_groups(source, serialize(candidate), specs)
                self.assertTrue(result["pass"], result)

    def test_real_mother_repeat_groups_allow_removal_without_emptying_list(self):
        for template_name, path in TEMPLATES.items():
            with self.subTest(template=template_name):
                source, root = self._load(path)
                candidate = deepcopy(root)
                specs = self._applicable_groups(root, template_name)
                removed = 0
                for spec in specs:
                    for wrapper in query(candidate, spec.wrapper_selector):
                        cards = direct_cards(candidate, wrapper, spec.child_selector)
                        if len(cards) > 1:
                            wrapper.remove(cards[0])
                            removed += 1
                self.assertGreater(removed, 0, "No list with multiple cards available for removal test")
                result = validate_repeat_groups(source, serialize(candidate), specs)
                self.assertTrue(result["pass"], result)


if __name__ == "__main__":
    unittest.main()
