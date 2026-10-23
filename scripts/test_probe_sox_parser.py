#!/usr/bin/env python3
"""Regression tests for the public Nasdaq SOX snapshot parser."""
import importlib.util
from pathlib import Path
import unittest
from datetime import date

MODULE_PATH = Path(__file__).with_name("probe_sox_sources.py")
spec = importlib.util.spec_from_file_location("probe_sox_sources", MODULE_PATH)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

class NasdaqSnapshotParserTests(unittest.TestCase):
    def test_parses_current_snapshot(self):
        parsed = probe.extract_nasdaq_snapshot(
            '<div>DATA AS OF 10/22/2026 10,731.98</div>'
        )
        self.assertEqual(parsed, (date(2026, 10, 22), 10731.98))

    def test_ignores_html_tags_and_whitespace(self):
        parsed = probe.extract_nasdaq_snapshot(
            '<span>DATA AS OF</span>\n<b>10/22/2026</b> <i>10,731.98</i>'
        )
        self.assertEqual(parsed, (date(2026, 10, 22), 10731.98))

    def test_unparseable_page_is_not_a_pass(self):
        self.assertIsNone(probe.extract_nasdaq_snapshot(
            '<div>Market overview - data temporarily unavailable</div>'
        ))

    def test_missing_decimal_precision_is_not_silently_rounded(self):
        self.assertIsNone(probe.extract_nasdaq_snapshot(
            '<div>DATA AS OF 10/22/2026 10731</div>'
        ))

    def test_invalid_calendar_date_fails_loudly(self):
        with self.assertRaises(ValueError):
            probe.extract_nasdaq_snapshot(
                '<div>DATA AS OF 13/40/2026 10,731.98</div>'
            )

if __name__ == "__main__":
    unittest.main(verbosity=2)
