#!/usr/bin/env python3
"""Deterministic tests for CNN Fear & Greed score-to-marker binding."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bs4 import BeautifulSoup
from build_review_html import parse_fear_greed_score, apply_fear_greed_marker


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
