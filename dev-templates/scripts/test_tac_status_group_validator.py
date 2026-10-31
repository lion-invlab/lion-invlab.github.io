"""Synthetic and real-mother tests for calendar status-group variants."""
from copy import deepcopy
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

import cssselect2
import html5lib

from tac_status_group_validator import StatusGroupSpec, validate_status_group_variants


ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = {
    "monday": ROOT / "母版專區/TAC_母版_週一_2026-10-28_最終定版.html",
    "weekdays": ROOT / "母版專區/TAC_母版_週二至週五_2026-10-28_最終定版.html",
}
SPECS = [
    StatusGroupSpec("weekly_economic", "#calendar", list_selector=".econ-event-list", card_selector=".econ-event"),
    StatusGroupSpec("weekly_earnings", "#earnings", list_selector=".earnings-accordion-list", card_selector=".earnings-accordion"),
    StatusGroupSpec("last_week_economic", "#last-week-calendar", list_selector=".econ-event-list", card_selector=".econ-event"),
    StatusGroupSpec("last_week_earnings", "#last-week-earnings", list_selector=".earnings-accordion-list", card_selector=".earnings-accordion"),
]


def parse(source):
    return html5lib.parse(source, treebuilder="etree", namespaceHTMLElements=False)


def serialize(root):
    return html5lib.serialize(
        root, tree="etree", omit_optional_tags=False,
        quote_attr_values="always", alphabetical_attributes=True,
    )


def query(root, selector):
    wrapped = cssselect2.ElementWrapper.from_html_root(root)
    return [item.etree_element for item in wrapped.query_all(selector)]


def direct(root, parent, selector):
    wrapped = cssselect2.ElementWrapper.from_html_root(root)
    return [
        item.etree_element for item in wrapped.query_all(selector)
        if item.parent is not None and item.parent.etree_element is parent
    ]


def within(root, ancestor, selector):
    wrapped = cssselect2.ElementWrapper.from_html_root(root)
    matches = []
    for item in wrapped.query_all(selector):
        parent = item.parent
        while parent is not None:
            if parent.etree_element is ancestor:
                matches.append(item.etree_element)
                break
            parent = parent.parent
    return matches


def synthetic_page():
    return """<!doctype html><html><head><style>.calendar-status-empty{padding:10px}</style></head><body>
    <section id="calendar"><div class="calendar-status-group"><h4 class="calendar-status-heading upcoming">Today</h4><div class="calendar-status-empty">No events</div></div>
    <div class="calendar-status-group"><h4 class="calendar-status-heading upcoming">Upcoming</h4><div class="econ-event-list"><details class="econ-event"><summary><span class="econ-name">CPI</span></summary><div class="econ-details">Details</div></details></div></div></section>
    <footer id="fixed">unchanged</footer></body></html>"""


class SyntheticStatusGroupTests(unittest.TestCase):
    SPEC = StatusGroupSpec("economic", "#calendar")

    def test_list_can_switch_to_existing_empty_prototype(self):
        baseline = synthetic_page()
        root = parse(baseline)
        groups = query(root, "#calendar .calendar-status-group")
        list_node = direct(root, groups[1], ".econ-event-list")[0]
        empty_node = direct(root, groups[0], ".calendar-status-empty")[0]
        groups[1].remove(list_node)
        groups[1].append(deepcopy(empty_node))
        result = validate_status_group_variants(baseline, serialize(root), [self.SPEC])
        self.assertTrue(result["pass"], result)

    def test_empty_can_switch_to_existing_list_prototype(self):
        baseline = synthetic_page()
        root = parse(baseline)
        groups = query(root, "#calendar .calendar-status-group")
        empty_node = direct(root, groups[0], ".calendar-status-empty")[0]
        list_node = direct(root, groups[1], ".econ-event-list")[0]
        groups[0].remove(empty_node)
        groups[0].append(deepcopy(list_node))
        result = validate_status_group_variants(baseline, serialize(root), [self.SPEC])
        self.assertTrue(result["pass"], result)

    def test_empty_rejected_when_baseline_has_no_empty_prototype(self):
        baseline = synthetic_page().replace('<div class="calendar-status-empty">No events</div>', '<div class="econ-event-list"><details class="econ-event"><summary><span class="econ-name">A</span></summary></details></div>')
        candidate = baseline.replace('<div class="econ-event-list"><details class="econ-event"><summary><span class="econ-name">CPI</span></summary><div class="econ-details">Details</div></details></div>', '<div class="calendar-status-empty">No events</div>', 1)
        result = validate_status_group_variants(baseline, candidate, [self.SPEC])
        self.assertFalse(result["pass"])

    def test_status_heading_text_can_update_without_structure_change(self):
        baseline = synthetic_page()
        candidate = baseline.replace(">Upcoming</h4>", ">Upcoming｜10/31</h4>")
        result = validate_status_group_variants(baseline, candidate, [self.SPEC])
        self.assertTrue(result["pass"], result)

    def test_status_heading_class_change_is_rejected(self):
        baseline = synthetic_page()
        candidate = baseline.replace("calendar-status-heading upcoming", "calendar-status-heading altered")
        result = validate_status_group_variants(baseline, candidate, [self.SPEC])
        self.assertFalse(result["pass"])

    def test_empty_list_wrapper_without_cards_is_rejected(self):
        baseline = synthetic_page()
        candidate = baseline.replace('<details class="econ-event"><summary><span class="econ-name">CPI</span></summary><div class="econ-details">Details</div></details>', "")
        result = validate_status_group_variants(baseline, candidate, [self.SPEC])
        self.assertFalse(result["pass"])

    def test_fixed_document_change_is_rejected(self):
        baseline = synthetic_page()
        candidate = baseline.replace('id="fixed"', 'id="changed"')
        result = validate_status_group_variants(baseline, candidate, [self.SPEC])
        self.assertFalse(result["pass"])


class RealMotherStatusGroupTests(unittest.TestCase):
    def _load(self, name):
        path = TEMPLATES[name]
        self.assertTrue(path.exists(), f"Missing locked mother template: {path}")
        source = path.read_text(encoding="utf-8")
        return source, parse(source)

    def _switch_list_to_empty(self, source, root, section_selector, list_selector, card_selector):
        candidate = deepcopy(root)
        section = query(candidate, section_selector)[0]
        groups = within(candidate, section, ".calendar-status-group")
        empty_prototypes = [
            node for group in groups for node in direct(candidate, group, ".calendar-status-empty")
        ]
        target = next((group for group in groups if direct(candidate, group, list_selector)), None)
        if target is None or not empty_prototypes:
            return None
        list_node = direct(candidate, target, list_selector)[0]
        target.remove(list_node)
        target.append(deepcopy(empty_prototypes[0]))
        return validate_status_group_variants(source, serialize(candidate), [
            StatusGroupSpec("target", section_selector, list_selector=list_selector, card_selector=card_selector)
        ])

    def _switch_empty_to_list(self, source, root, section_selector, list_selector, card_selector):
        candidate = deepcopy(root)
        section = query(candidate, section_selector)[0]
        groups = direct(candidate, section, ".calendar-status-group")
        list_prototypes = [
            node for group in groups for node in direct(candidate, group, list_selector)
        ]
        target = next((group for group in groups if direct(candidate, group, ".calendar-status-empty")), None)
        if target is None or not list_prototypes:
            return None
        empty_node = direct(candidate, target, ".calendar-status-empty")[0]
        target.remove(empty_node)
        target.append(deepcopy(list_prototypes[0]))
        return validate_status_group_variants(source, serialize(candidate), [
            StatusGroupSpec("target", section_selector, list_selector=list_selector, card_selector=card_selector)
        ])

    def test_monday_economic_and_earnings_support_existing_empty_state_transitions(self):
        source, root = self._load("monday")
        for section, list_selector, card_selector in (
            ("#calendar", ".econ-event-list", ".econ-event"),
            ("#earnings", ".earnings-accordion-list", ".earnings-accordion"),
        ):
            with self.subTest(section=section, direction="list_to_empty"):
                result = self._switch_list_to_empty(source, root, section, list_selector, card_selector)
                self.assertIsNotNone(result, f"{section}: expected baseline list and empty prototypes")
                self.assertTrue(result["pass"], result)
            with self.subTest(section=section, direction="empty_to_list"):
                result = self._switch_empty_to_list(source, root, section, list_selector, card_selector)
                self.assertIsNotNone(result, f"{section}: expected baseline list and empty prototypes")
                self.assertTrue(result["pass"], result)

    def test_weekday_mother_does_not_gain_unapproved_empty_markup(self):
        source, root = self._load("weekdays")
        for section, list_selector, card_selector in (
            ("#calendar", ".econ-event-list", ".econ-event"),
            ("#earnings", ".earnings-accordion-list", ".earnings-accordion"),
        ):
            with self.subTest(section=section):
                candidate = deepcopy(root)
                section_node = query(candidate, section)[0]
                groups = within(candidate, section_node, ".calendar-status-group")
                target = next(group for group in groups if direct(candidate, group, list_selector))
                list_node = direct(candidate, target, list_selector)[0]
                target.remove(list_node)
                empty = ET.Element("div", {"class": "calendar-status-empty"})
                empty.text = "No verified events"
                target.append(empty)
                result = validate_status_group_variants(source, serialize(candidate), [
                    StatusGroupSpec("target", section, list_selector=list_selector, card_selector=card_selector)
                ])
                self.assertFalse(result["pass"], result)


if __name__ == "__main__":
    unittest.main()
