"""Headless Chromium smoke tests for the two locked mother templates."""
from pathlib import Path
import unittest

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = {
    "monday": ROOT / "母版專區/TAC_母版_週一_2026-10-28_最終定版.html",
    "weekdays": ROOT / "母版專區/TAC_母版_週二至週五_2026-10-28_最終定版.html",
}


class MotherTemplateBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def _open(self, path):
        self.assertTrue(path.exists(), f"Missing locked mother template: {path}")
        page = self.browser.new_page(viewport={"width": 1280, "height": 900})
        page.set_default_timeout(6000)
        page.route("https://**/*", lambda route: route.abort())
        page.route("http://**/*", lambda route: route.abort())
        page.goto(path.resolve().as_uri(), wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(300)
        dialog = page.locator("#tac-fund-notice")
        if dialog.is_visible():
            page.locator("#tfn-close").click(force=True)
            page.wait_for_timeout(100)
        return page

    def _activate_upcoming_tabs(self, page):
        page.locator('label[for="week-econ-upcoming"]').click()
        page.locator('label[for="week-earnings-upcoming"]').click()

    def _assert_toggle_group(self, page, template, card_selector, toggle_selector):
        cards = page.locator(card_selector)
        self.assertGreater(cards.count(), 0, f"{template}: missing cards for {card_selector}")

        for index in range(cards.count()):
            card = cards.nth(index)
            toggle = card.locator(f":scope > summary {toggle_selector}")
            self.assertEqual(
                toggle.count(), 1,
                f"{template}: card {index} must have exactly one {toggle_selector}",
            )
            before = toggle.evaluate(
                "(el) => { const s=getComputedStyle(el); return {width:parseFloat(s.width),height:parseFloat(s.height),flexBasis:s.flexBasis,radius:s.borderRadius,background:s.backgroundColor,content:getComputedStyle(el,'::before').content}; }"
            )
            self.assertEqual(before["width"], 32, f"{template}: card {index} plus width must be 32px {before}")
            self.assertEqual(before["height"], 32, f"{template}: card {index} plus height must be 32px {before}")
            self.assertEqual(before["flexBasis"], "32px", f"{template}: card {index} flex-basis must be 32px {before}")
            self.assertEqual(before["width"], before["height"], f"{template}: card {index} plus is not square {before}")
            self.assertEqual(before["radius"], "50%", f"{template}: card {index} plus is not circular {before}")
            self.assertIn("198, 40, 40", before["background"], f"{template}: card {index} plus is not TAC red {before}")

            card.locator(":scope > summary").click()
            after = toggle.evaluate(
                "(el) => { const s=getComputedStyle(el); const p=getComputedStyle(el,'::before'); return {background:s.backgroundColor,pseudoBackground:p.backgroundColor,content:p.content}; }"
            )
            self.assertIn("−", after["content"], f"{template}: card {index} plus did not become minus {after}")
            if toggle_selector == ".econ-toggle":
                self.assertEqual(after["pseudoBackground"], "rgb(32, 35, 40)", f"{template}: open economic toggle state is wrong {after}")
            else:
                self.assertEqual(after["background"], "rgb(32, 35, 40)", f"{template}: open toggle state is wrong {after}")

            card.locator(":scope > summary").click()
            self.assertFalse(card.evaluate("(el) => el.open"), f"{template}: card {index} did not close")

    def test_economic_and_earnings_cards_toggle_in_real_browser(self):
        for name, path in TEMPLATES.items():
            with self.subTest(template=name):
                page = self._open(path)
                self._activate_upcoming_tabs(page)
                for selector in (
                    "#calendar .econ-event-list details.econ-event:visible",
                    "#earnings .earnings-accordion-list details.earnings-accordion:visible",
                ):
                    cards = page.locator(selector)
                    self.assertGreater(cards.count(), 0, f"{name}: no cards for {selector}")
                    card = cards.first
                    before = card.evaluate("(el) => el.open")
                    card.locator(":scope > summary").click()
                    self.assertNotEqual(card.evaluate("(el) => el.open"), before)
                    card.locator(":scope > summary").click()
                    self.assertEqual(card.evaluate("(el) => el.open"), before)
                page.close()

    def test_red_plus_controls_render_and_change_to_minus(self):
        for name, path in TEMPLATES.items():
            with self.subTest(template=name):
                page = self._open(path)
                self._activate_upcoming_tabs(page)

                # Both templates: current-week economic and earnings cards.
                # The locked Monday mother currently has no toggle
                # element in its current-week economic cards. Do not invent
                # one in tests or mutate the formal template; verify this gap
                # explicitly in a separate diagnostic test below.
                if name == "weekdays":
                    self._assert_toggle_group(
                        page, name,
                        "#calendar .econ-event-list details.econ-event:visible",
                        ".econ-toggle",
                    )
                self._assert_toggle_group(
                    page, name,
                    "#earnings .earnings-accordion-list details.earnings-accordion:visible",
                    ".earnings-accordion-toggle",
                )

                # Monday has two additional prior-week groups. Expand their
                # outer disclosures before checking every card control.
                if name == "monday":
                    prior_econ = page.locator("#last-week-calendar details.last-week-calendar-collapse")
                    self.assertEqual(prior_econ.count(), 1, "monday: missing prior-week economic disclosure")
                    prior_econ.locator(":scope > summary").click()
                    self._assert_toggle_group(
                        page, name,
                        "#last-week-calendar .econ-event-list details.econ-event",
                        ".econ-event-toggle",
                    )

                    prior_earnings = page.locator("#last-week-earnings details.last-week-earnings-collapse")
                    self.assertEqual(prior_earnings.count(), 1, "monday: missing prior-week earnings disclosure")
                    prior_earnings.locator(":scope > summary").click()
                    self._assert_toggle_group(
                        page, name,
                        "#last-week-earnings .earnings-accordion-list details.earnings-accordion",
                        ".earnings-accordion-toggle",
                    )
                page.close()

    def test_monday_current_week_economic_toggle_gap_is_explicit(self):
        path = TEMPLATES["monday"]
        page = self._open(path)
        self._activate_upcoming_tabs(page)
        cards = page.locator("#calendar .econ-event-list details.econ-event:visible")
        self.assertGreater(cards.count(), 0, "monday: expected current-week economic cards")
        for index in range(cards.count()):
            self.assertEqual(
                cards.nth(index).locator(":scope > summary .econ-toggle").count(), 0,
                f"monday: card {index} unexpectedly changed; re-audit the locked mother before changing this diagnostic",
            )
        page.close()

    def test_calendar_tabs_switch_in_real_browser(self):
        for name, path in TEMPLATES.items():
            with self.subTest(template=name):
                page = self._open(path)
                for prefix, tab in (("week-econ", "upcoming"), ("week-earnings", "upcoming")):
                    radio = page.locator(f"#{prefix}-{tab}")
                    self.assertEqual(radio.count(), 1, f"{name}: missing #{prefix}-{tab}")
                    page.locator(f'label[for="{prefix}-{tab}"]').click()
                    self.assertTrue(radio.is_checked(), f"{name}: {prefix} tab did not switch")
                page.close()

    def test_mobile_calendar_lists_fit_320px_viewport(self):
        for name, path in TEMPLATES.items():
            with self.subTest(template=name):
                page = self._open(path)
                page.set_viewport_size({"width": 320, "height": 800})
                page.wait_for_timeout(150)
                self._activate_upcoming_tabs(page)
                for selector in ("#calendar .econ-event-list", "#earnings .earnings-accordion-list"):
                    lists = page.locator(selector)
                    visible_metrics = lists.evaluate_all(
                        "(els) => els.filter(el => el.getClientRects().length).map(el => ({left: el.getBoundingClientRect().left, right: el.getBoundingClientRect().right, width: el.getBoundingClientRect().width, scrollWidth: el.scrollWidth}))"
                    )
                    for metrics in visible_metrics:
                        self.assertLessEqual(metrics["right"], 321, f"{name}: list overflows right edge: {metrics}")
                        self.assertGreaterEqual(metrics["left"], -1, f"{name}: list overflows left edge: {metrics}")
                        self.assertLessEqual(metrics["scrollWidth"], metrics["width"] + 1, f"{name}: list content overflows: {metrics}")
                page.close()


if __name__ == "__main__":
    unittest.main()
