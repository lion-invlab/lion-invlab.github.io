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
        page.goto(path.resolve().as_uri(), wait_until="domcontentloaded")
        return page

    def test_economic_and_earnings_cards_toggle_in_real_browser(self):
        for name, path in TEMPLATES.items():
            with self.subTest(template=name):
                page = self._open(path)
                for selector in (
                    "#calendar .econ-event-list details.econ-event",
                    "#earnings .earnings-accordion-list details.earnings-accordion",
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
                for selector in ("#calendar .econ-event-list", "#earnings .earnings-accordion-list"):
                    lists = page.locator(selector)
                    for index in range(lists.count()):
                        metrics = lists.nth(index).evaluate(
                            "(el) => ({left: el.getBoundingClientRect().left, right: el.getBoundingClientRect().right, width: el.getBoundingClientRect().width, scrollWidth: el.scrollWidth})"
                        )
                        self.assertLessEqual(metrics["right"], 321, f"{name}: list overflows right edge: {metrics}")
                        self.assertGreaterEqual(metrics["left"], -1, f"{name}: list overflows left edge: {metrics}")
                        self.assertLessEqual(metrics["scrollWidth"], metrics["width"] + 1, f"{name}: list content overflows: {metrics}")
                page.close()


if __name__ == "__main__":
    unittest.main()
