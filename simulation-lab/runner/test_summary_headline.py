#!/usr/bin/env python3
"""Regression tests for the summary card heading contract; included in every simulation build."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_review_html import validate_summary_title


class SummaryHeadlineTests(unittest.TestCase):
    def test_accepts_concise_market_takeaway(self):
        self.assertEqual(
            validate_summary_title("AI 投資轉向獲利與資本回收檢驗"),
            "AI 投資轉向獲利與資本回收檢驗",
        )

    def test_rejects_generic_section_labels(self):
        for value in ("總結", "摘要", "市場情緒", "Summary", "Market Summary"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_summary_title(value)

    def test_rejects_missing_or_overlong_headline(self):
        for value in (None, "", "市場轉弱", "這是一段過長的總結標題文字超過三十六個字所以不應該通過驗收"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_summary_title(value)

    def test_rejects_multiline_or_body_separator(self):
        for value in ("AI 投資轉向獲利檢驗\n市場觀察", "AI 投資｜資本回收"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_summary_title(value)


if __name__ == "__main__":
    unittest.main(verbosity=2)
