#!/usr/bin/env python3
"""Deterministic tests for CNN Fear & Greed score-to-marker binding."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bs4 import BeautifulSoup
from build_review_html import parse_fear_greed_score, apply_fear_greed_marker, fear_greed_band, apply_fear_greed_status


class FearGreedMarkerTests(unittest.TestCase):
    def test_numeric_scores_map_to_the_same_percentage(self):
        for value in (20, 40, 75, "20", "40", "75", "40/100"):
            with self.subTest(value=value):
                score = parse_fear_greed_score(value)
                self.assertIsNotNone(score)
                marker = BeautifulSoup('<div class="fg6-marker" style="left:23%!important"></div>', "html.parser").div
                self.assertEqual(apply_fear_greed_marker(marker, value), score)
                self.assertEqual(marker.get("data-score"), f"{score:g}")
                self.assertEqual(marker["style"], f"left: {score:g}% !important;")
                self.assertNotIn("aria-hidden", marker.attrs)

    def test_boundaries_are_valid(self):
        self.assertEqual(parse_fear_greed_score(0), 0)
        self.assertEqual(parse_fear_greed_score(100), 100)

    def test_invalid_or_missing_score_hides_stale_marker(self):
        for value in ("待核實", "N/A", None, -1, 101, True, ""):
            with self.subTest(value=value):
                marker = BeautifulSoup('<div class="fg6-marker" style="left:23%!important"></div>', "html.parser").div
                self.assertIsNone(apply_fear_greed_marker(marker, value))
                self.assertEqual(marker["style"], "display: none !important;")
                self.assertEqual(marker.get("aria-hidden"), "true")
                self.assertNotIn("data-score", marker.attrs)


    def test_score_bands_follow_cnn_fear_and_greed_ranges(self):
        cases = [
            (0, ("Extreme Fear", "極度恐懼")),
            (24, ("Extreme Fear", "極度恐懼")),
            (25, ("Fear", "恐懼")),
            (44, ("Fear", "恐懼")),
            (45, ("Neutral", "中性")),
            (55, ("Neutral", "中性")),
            (56, ("Greed", "貪婪")),
            (74, ("Greed", "貪婪")),
            (75, ("Extreme Greed", "極度貪婪")),
            (100, ("Extreme Greed", "極度貪婪")),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(fear_greed_band(value), expected)

    def test_visible_status_updates_both_languages_from_score(self):
        node = BeautifulSoup(
            '<div class="fg6-status"><span>Fear</span><i></i><b>恐懼</b></div>',
            "html.parser"
        ).div
        self.assertEqual(apply_fear_greed_status(node, 19), ("Extreme Fear", "極度恐懼"))
        self.assertEqual(node.select_one("span").get_text(strip=True), "Extreme Fear")
        self.assertEqual(node.select_one("b").get_text(strip=True), "極度恐懼")
        self.assertEqual(node.get("aria-label"), "Extreme Fear / 極度恐懼")

    def test_invalid_score_sets_status_to_pending(self):
        node = BeautifulSoup(
            '<div class="fg6-status"><span>Fear</span><i></i><b>恐懼</b></div>',
            "html.parser"
        ).div
        self.assertEqual(apply_fear_greed_status(node, "待核實"), ("Unavailable", "待核實"))
        self.assertEqual(node.select_one("span").get_text(strip=True), "Unavailable")
        self.assertEqual(node.select_one("b").get_text(strip=True), "待核實")

if __name__ == "__main__":
    unittest.main(verbosity=2)
