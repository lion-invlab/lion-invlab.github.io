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

    def test_parses_exact_date_in_investing_historical_table(self):
        html = (
            '<tr><td>Oct 21, 2026</td><td>11,505.6</td><td>11,494.4</td>'
            '<td>11,562.2</td><td>11,355.3</td></tr>'
        )
        parsed = probe.extract_investing_row(html, date(2026, 10, 21))
        self.assertEqual(parsed, {
            "Open": 11494.4, "High": 11562.2, "Low": 11355.3, "Close": 11505.6
        })

    def test_investing_parser_does_not_accept_other_dates(self):
        html = (
            '<tr><td>Oct 22, 2026</td><td>10,731.9</td><td>11,049.0</td>'
            '<td>11,140.0</td><td>10,666.4</td></tr>'
        )
        self.assertIsNone(probe.extract_investing_row(html, date(2026, 10, 21)))

    def test_parses_exact_date_in_ycharts_historical_table(self):
        html = (
            '<tr><td>Oct 21, 2026</td><td>11494.43</td><td>11562.24</td>'
            '<td>11355.29</td><td>11505.56</td></tr>'
        )
        parsed = probe.extract_ycharts_row(html, date(2026, 10, 21))
        self.assertEqual(parsed, {
            "Open": 11494.43, "High": 11562.24, "Low": 11355.29, "Close": 11505.56
        })

    def test_ycharts_parser_does_not_accept_other_dates(self):
        html = (
            '<tr><td>Oct 22, 2026</td><td>11049.07</td><td>11140.33</td>'
            '<td>10666.41</td><td>10731.98</td></tr>'
        )
        self.assertIsNone(probe.extract_ycharts_row(html, date(2026, 10, 21)))

    def test_parses_exact_date_in_closelook_historical_table(self):
        html = (
            '<tr><td>2026-10-21</td><td>11494.43</td><td>11562.25</td>'
            '<td>11355.29</td><td>11505.56</td><td>+1.97%</td></tr>'
        )
        parsed = probe.extract_closelook_row(html, date(2026, 10, 21))
        self.assertEqual(parsed, {
            "Open": 11494.43, "High": 11562.25, "Low": 11355.29, "Close": 11505.56
        })

    def test_closelook_parser_does_not_accept_other_dates(self):
        html = (
            '<tr><td>2026-10-22</td><td>11049.07</td><td>11140.33</td>'
            '<td>10666.41</td><td>10731.98</td><td>-6.72%</td></tr>'
        )
        self.assertIsNone(probe.extract_closelook_row(html, date(2026, 10, 21)))

    def test_invalid_calendar_date_fails_loudly(self):
        with self.assertRaises(ValueError):
            probe.extract_nasdaq_snapshot(
                '<div>DATA AS OF 13/40/2026 10,731.98</div>'
            )

if __name__ == "__main__":
    unittest.main(verbosity=2)
