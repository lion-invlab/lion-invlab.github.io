#!/usr/bin/env python3
"""Tests for weekly calendar snapshot assembly and renderer integration."""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from assemble_tac_calendar_snapshot import build_calendar_snapshot, currency_amount
from render_tac_market_safe import (
    SourceTreeParser, select, resize_calendar_lists,
    render_economic_calendar, render_earnings_calendar,
)


class CalendarSnapshotAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binding = json.loads((ROOT / "scripts/tac_html_binding_map.json").read_text(encoding="utf-8"))
        cls.current = json.loads((ROOT / "data/calendar/weeks/2026-W45.json").read_text(encoding="utf-8"))
        cls.previous = json.loads((ROOT / "data/calendar/weeks/2026-W44.json").read_text(encoding="utf-8"))
        cls.monday = (ROOT / "母版專區/TAC_母版_週一_2026-10-28_最終定版.html").read_text(encoding="utf-8")
        cls.weekday = (ROOT / "母版專區/TAC_母版_週二至週五_2026-10-28_最終定版.html").read_text(encoding="utf-8")

    def render_calendar_groups(self, template, snapshot):
        html = resize_calendar_lists(template, self.binding, snapshot)
        parser = SourceTreeParser(html)
        parser.feed(html)
        parser.close()
        edits, used = [], set()
        render_economic_calendar(html, parser, snapshot, self.binding, edits, used)
        render_earnings_calendar(html, parser, snapshot, self.binding, edits, used)
        for start, end, replacement in sorted(edits, reverse=True):
            html = html[:start] + replacement + html[end:]
        return html

    def test_weekday_snapshot_renders_all_status_lists(self):
        current = json.loads(json.dumps(self.current))
        for row in current["events"]["economic"]:
            if row["event_date"].startswith("2026-11-02"):
                row["status"] = "released"
                row["actual"] = "Synthetic actual"
        snapshot = build_calendar_snapshot(current, None, "2026-11-03", self.weekday, self.binding)
        econ = snapshot["economic_calendar"]["panels"]["current_week"]["lists"]
        earn = snapshot["earnings_calendar"]["panels"]["current_week"]["lists"]
        self.assertEqual([len(x["items"]) for x in econ], [4, 11, 2])
        self.assertEqual([len(x["items"]) for x in earn], [5, 25, 0])
        html = self.render_calendar_groups(self.weekday, snapshot)
        self.assertIn("日本央行｜經濟活動與物價展望報告（全文）", html)
        self.assertIn("美國 ISM 製造業 PMI（10月）", html)
        self.assertIn("Apple", html)
        self.assertIn("Palantir", html)
        self.assertEqual(len(re.findall(r'class="econ-event(?:\s|")', html)), 17)
        self.assertEqual(len(re.findall(r'class="earnings-accordion(?:\s|")', html)), 30)
        self.assertIn('href="https://investor.apple.com/"', html)

    def test_monday_previous_week_and_upcoming_lists_render(self):
        current = json.loads(json.dumps(self.current))
        # The approved Monday mother has only the upcoming list in the current-week
        # panel. Remove today's events from this fixture to test all available slots.
        for row in current["events"]["economic"]:
            if row["event_date"].startswith("2026-11-02"):
                row["importance_stars"] = 3
        snapshot = build_calendar_snapshot(current, self.previous, "2026-11-02", self.monday, self.binding)
        econ_prior = snapshot["economic_calendar"]["panels"]["last_week"]["lists"]
        earn_prior = snapshot["earnings_calendar"]["panels"]["last_week"]["lists"]
        self.assertEqual(len(econ_prior), 1)
        self.assertEqual(len(econ_prior[0]["items"]), 8)
        self.assertEqual(len(earn_prior), 1)
        self.assertEqual(len(earn_prior[0]["items"]), 8)
        self.assertEqual(len(snapshot["economic_calendar"]["panels"]["current_week"]["lists"]), 3)
        self.assertEqual([len(x["items"]) for x in snapshot["economic_calendar"]["panels"]["current_week"]["lists"]], [0, 15, 0])
        html = self.render_calendar_groups(self.monday, snapshot)
        self.assertIn("目前沒有已核實、排定於 10/26（台灣時間）公布的本週重要經濟事件", html)
        self.assertIn("日本央行（BOJ）利率決策及10月展望報告", html)
        self.assertIn("AstraZeneca", html)
        self.assertIn("Visa", html)
        self.assertEqual(len(re.findall(r'class="econ-event(?:\s|")', html)), 23)
        self.assertEqual(len(re.findall(r'class="earnings-accordion(?:\s|")', html)), 38)

    def test_monday_creates_today_and_published_lists_from_approved_empty_states(self):
        snapshot = build_calendar_snapshot(self.current, self.previous, "2026-11-02", self.monday, self.binding)
        econ_lists = snapshot["economic_calendar"]["panels"]["current_week"]["lists"]
        earnings_lists = snapshot["earnings_calendar"]["panels"]["current_week"]["lists"]
        self.assertEqual(len(econ_lists), 3)
        self.assertGreater(len(econ_lists[0]["items"]), 0)
        self.assertEqual(len(earnings_lists), 3)
        before = SourceTreeParser(self.monday)
        before.feed(self.monday)
        before.close()
        econ_before = select(before.root, "#calendar")[0]
        earnings_before = select(before.root, "#earnings")[0]
        before_econ_lists = len(select(econ_before, ".econ-event-list"))
        before_earnings_lists = len(select(earnings_before, ".earnings-accordion-list"))
        html = self.render_calendar_groups(self.monday, snapshot)
        after = SourceTreeParser(html)
        after.feed(html)
        after.close()
        econ_after = select(after.root, "#calendar")[0]
        earnings_after = select(after.root, "#earnings")[0]
        self.assertEqual(len(select(econ_after, ".calendar-status-group")), 3)
        self.assertEqual(len(select(econ_after, ".econ-event-list")), before_econ_lists + 1)
        today_group = select(econ_after, ".calendar-status-group")[0]
        today_list = select(today_group, ".econ-event-list")
        self.assertEqual(len(today_list), 1)
        self.assertEqual(len(select(today_list[0], ".econ-event")), len(econ_lists[0]["items"]))
        self.assertEqual(len(select(earnings_after, ".earnings-accordion-list")), before_earnings_lists)
        self.assertIn("目前沒有已核實、排定於 10/26（台灣時間）公布的本週重要公司財報", html)
        self.assertNotIn("目前沒有已核實、排定於 10/26（台灣時間）公布的本週重要經濟事件", html)

    def test_released_earnings_have_two_actual_result_cards(self):
        # Move all earnings to the previous day within this ISO week and mark
        # them released; the weekday mother has a published-list prototype.
        current = json.loads(json.dumps(self.current))
        for row in current["events"]["economic"]:
            if row["event_date"].startswith("2026-11-02"):
                row["status"] = "released"
                row["actual"] = "Synthetic actual"
        for row in current["events"]["earnings"]:
            row["event_date"] = "2026-11-02T10:00:00+08:00"
            row["status"] = "released"
            row["eps_actual"] = row.get("eps_estimate")
            row["revenue_actual"] = row.get("revenue_estimate")
            row["eps_comparison_status"] = "beat"
            row["revenue_comparison_status"] = "miss"
        released = build_calendar_snapshot(current, None, "2026-11-03", self.weekday, self.binding)
        published = released["earnings_calendar"]["panels"]["current_week"]["lists"][2]["items"]
        self.assertEqual(len(published), 30)
        self.assertEqual(len(published[0]["results"]), 2)
        self.assertEqual(published[0]["results"][0]["status_class"], "beat")
        self.assertEqual(published[0]["results"][1]["status_class"], "miss")

    def test_same_day_released_events_are_bucketed_as_published(self):
        current = json.loads(json.dumps(self.current))
        econ = next(row for row in current["events"]["economic"]
                    if row["event_date"].startswith("2026-11-02"))
        econ["status"] = "released"
        econ["actual"] = "Synthetic actual"
        earnings = current["events"]["earnings"][0]
        earnings["event_date"] = "2026-11-02T10:00:00+08:00"
        earnings["status"] = "released"
        earnings["eps_actual"] = earnings.get("eps_estimate")
        earnings["revenue_actual"] = earnings.get("revenue_estimate")

        snapshot = build_calendar_snapshot(current, self.previous, "2026-11-02",
                                           self.monday, self.binding)
        econ_lists = snapshot["economic_calendar"]["panels"]["current_week"]["lists"]
        earnings_lists = snapshot["earnings_calendar"]["panels"]["current_week"]["lists"]
        self.assertTrue(any(item["name"] == econ["event_name"] for item in econ_lists[2]["items"]))
        self.assertFalse(any(item["name"] == econ["event_name"] for item in econ_lists[0]["items"]))
        self.assertTrue(any(item["company"] == earnings["company"] for item in earnings_lists[2]["items"]))
        self.assertFalse(any(item["company"] == earnings["company"] for item in earnings_lists[0]["items"]))

    def test_previous_week_panels_exclude_four_star_events(self):
        previous = json.loads(json.dumps(self.previous))
        for kind in ("economic", "earnings"):
            four_star = json.loads(json.dumps(previous["events"][kind][0]))
            four_star["id"] = f"four-star-{kind}-should-not-render"
            if kind == "economic":
                four_star["event_name"] = "four-star-economic-should-not-render"
            else:
                four_star["company"] = "four-star-earnings-should-not-render"
            four_star["importance_stars"] = 4
            previous["events"][kind].append(four_star)

        snapshot = build_calendar_snapshot(self.current, previous, "2026-11-02",
                                           self.monday, self.binding)
        econ_prior = snapshot["economic_calendar"]["panels"]["last_week"]["lists"]
        earnings_prior = snapshot["earnings_calendar"]["panels"]["last_week"]["lists"]
        self.assertEqual(sum(len(group["items"]) for group in econ_prior), 8)
        self.assertEqual(sum(len(group["items"]) for group in earnings_prior), 8)
        self.assertFalse(any(item.get("name") == "four-star-economic-should-not-render"
                             for group in econ_prior for item in group["items"]))
        self.assertFalse(any(item.get("company") == "four-star-earnings-should-not-render"
                             for group in earnings_prior for item in group["items"]))

    def test_currency_format_preserves_units(self):
        self.assertEqual(currency_amount(2.79, "USD"), "US$2.79")
        self.assertEqual(currency_amount(16.209, "USD", "USD billions"), "US$16.209B")
        self.assertEqual(currency_amount(None, "USD", missing="尚未公布"), "尚未公布")

    def test_missing_source_does_not_silently_generate_fake_link(self):
        broken = json.loads(json.dumps(self.current))
        for row in broken["events"]["economic"]:
            if row["event_date"].startswith("2026-11-02"):
                row["status"] = "released"
                row["actual"] = "Synthetic actual"
        broken["events"]["economic"][0]["source"] = None
        broken["events"]["economic"][0]["data_reference"] = None
        broken["events"]["economic"][0]["consensus_source"] = None
        with self.assertRaisesRegex(ValueError, "no valid HTTPS source link"):
            build_calendar_snapshot(broken, None, "2026-11-03", self.weekday, self.binding)


if __name__ == "__main__":
    unittest.main(verbosity=2)
