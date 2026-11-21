#!/usr/bin/env python3
"""Deterministic tests for report-layer repair of URL-corrupted calendar impact fields."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_review_html import apply_calendar_impact_overrides, apply_last_week_economic_overrides, apply_last_week_earnings_actuals


class CalendarImpactOverrideTests(unittest.TestCase):
    def test_replaces_only_url_corrupted_impact_and_preserves_source(self):
        data = {
            "calendar": {"events": [
                {"id": "bad-1", "impact": "https://example.com/source", "source_url": "https://example.com/source"},
                {"id": "good-1", "impact": "Valid market impact text that must remain unchanged."},
            ]},
            "calendar_impact_overrides": [{
                "event_id": "bad-1",
                "impact": "若初領失業金維持低檔，代表勞動市場仍具韌性，可能延後市場對降息的預期。",
            }],
        }
        applied = apply_calendar_impact_overrides(data)
        self.assertEqual(applied, 1)
        self.assertIn("可能延後市場對降息的預期", data["calendar"]["events"][0]["impact"])
        self.assertEqual(data["calendar"]["events"][0]["source_url"], "https://example.com/source")
        self.assertEqual(data["calendar"]["events"][1]["impact"], "Valid market impact text that must remain unchanged.")

    def test_promotes_corrupted_impact_url_to_source_url_when_missing(self):
        original_url = "https://www.newyorkfed.org/newsevents/mediaadvisory/2026/1113-2026"
        data = {
            "calendar": {"events": [{
                "id": "w48-fed-williams",
                "source": "New York Fed｜Media Advisory",
                "impact": original_url,
            }]},
            "calendar_impact_overrides": [{
                "event_id": "w48-fed-williams",
                "impact": "若Williams重申通膨黏性，將推升利率預期並壓抑高估值資產；若偏向等待數據，則可能緩和短端利率壓力。",
            }],
        }
        self.assertEqual(apply_calendar_impact_overrides(data), 1)
        event = data["calendar"]["events"][0]
        self.assertEqual(event["impact"], data["calendar_impact_overrides"][0]["impact"])
        self.assertEqual(event["source_url"], original_url)
        self.assertEqual(event["source_name"], "New York Fed｜Media Advisory")

    def test_refuses_to_overwrite_valid_impact_text(self):
        data = {
            "calendar": {"events": [{"id": "good-1", "impact": "Already valid market impact text."}]},
            "calendar_impact_overrides": [{"event_id": "good-1", "impact": "Replacement text that should not be applied."}],
        }
        with self.assertRaisesRegex(ValueError, "source field is not a URL"):
            apply_calendar_impact_overrides(data)

    def test_refuses_url_as_replacement(self):
        data = {
            "calendar": {"events": [{"id": "bad-1", "impact": "https://example.com/wrong"}]},
            "calendar_impact_overrides": [{"event_id": "bad-1", "impact": "https://example.com/another"}],
        }
        with self.assertRaisesRegex(ValueError, "not a URL"):
            apply_calendar_impact_overrides(data)

    def test_missing_event_fails_closed(self):
        data = {
            "calendar": {"events": []},
            "calendar_impact_overrides": [{"event_id": "missing", "impact": "This is a valid replacement impact statement."}],
        }
        with self.assertRaisesRegex(ValueError, "event not found"):
            apply_calendar_impact_overrides(data)


class LastWeekEconomicOverrideTests(unittest.TestCase):
    def test_publishes_late_reported_actual_without_mutating_authoritative_source(self):
        data = {
            "report_cutoff_taipei": "2026-11-23 05:25",
            "last_week_calendar": {"events": [{
                "id": "current-japan-cpi-202610",
                "date": "2026-11-20T07:30:00+08:00",
                "status": "upcoming",
                "actual": None,
                "source_url": "https://example.com/schedule",
            }]},
            "last_week_economic_overrides": [{
                "event_id": "current-japan-cpi-202610",
                "actual": "總合CPI年增2.3%；核心CPI年增2.2%。",
                "source_name": "Statistics Bureau of Japan",
                "source_url": "https://www.stat.go.jp/data/cpi/sokuhou/tsuki/index-z.html",
            }],
        }
        applied = apply_last_week_economic_overrides(data)
        event = data["last_week_calendar"]["events"][0]
        self.assertEqual(applied, 1)
        self.assertEqual(event["status"], "released")
        self.assertIn("2.3%", event["actual"])
        self.assertEqual(event["source_url"], "https://www.stat.go.jp/data/cpi/sokuhou/tsuki/index-z.html")
        self.assertTrue(event["report_layer_only"])

    def test_missing_event_fails_closed(self):
        data = {
            "report_cutoff_taipei": "2026-11-23 05:25",
            "last_week_calendar": {"events": []},
            "last_week_economic_overrides": [{
                "event_id": "missing",
                "actual": "Verified actual value.",
                "source_url": "https://example.com/source",
            }],
        }
        with self.assertRaisesRegex(ValueError, "event not found"):
            apply_last_week_economic_overrides(data)

    def test_refuses_to_overwrite_existing_actual(self):
        data = {
            "report_cutoff_taipei": "2026-11-23 05:25",
            "last_week_calendar": {"events": [{
                "id": "released",
                "date": "2026-11-20T07:30:00+08:00",
                "status": "released",
                "actual": "Already published actual.",
            }]},
            "last_week_economic_overrides": [{
                "event_id": "released",
                "actual": "Replacement actual.",
                "source_url": "https://example.com/source",
            }],
        }
        with self.assertRaisesRegex(ValueError, "not an unreleased empty record"):
            apply_last_week_economic_overrides(data)

    def test_refuses_future_event(self):
        data = {
            "report_cutoff_taipei": "2026-11-23 05:25",
            "last_week_calendar": {"events": [{
                "id": "future",
                "date": "2026-11-24T07:30:00+08:00",
                "status": "upcoming",
                "actual": None,
            }]},
            "last_week_economic_overrides": [{
                "event_id": "future",
                "actual": "Not yet released.",
                "source_url": "https://example.com/source",
            }],
        }
        with self.assertRaisesRegex(ValueError, "later than report cutoff"):
            apply_last_week_economic_overrides(data)


class LastWeekEarningsActualOverrideTests(unittest.TestCase):
    def test_applies_verified_actuals_and_keeps_comparison_pending(self):
        data = {
            "report_cutoff_taipei": "2026-11-23 05:25",
            "last_week_earnings": {"events": [{
                "id": "current-rost-20261120",
                "event_date": "2026-11-20T05:00:00+08:00",
                "ticker": "ROST",
                "status": "upcoming",
                "eps_actual": None,
                "revenue_actual": None,
                "eps_estimate": 1.86,
                "revenue_estimate": 6.23,
            }]},
            "last_week_earnings_actuals": [{
                "event_id": "current-rost-20261120",
                "event_date": "2026-11-20T05:00:00+08:00",
                "ticker": "ROST",
                "eps_actual": 1.91,
                "eps_actual_display": "GAAP diluted EPS US$1.91",
                "eps_actual_basis": "GAAP diluted EPS",
                "eps_actual_basis_code": "GAAP_DILUTED_EPS",
                "eps_actual_currency": "USD",
                "eps_actual_period": "Q3 FY2026",
                "revenue_actual": 6.255954,
                "revenue_actual_display": "US$6.256B",
                "revenue_actual_basis": "Total sales (USD billions)",
                "revenue_actual_basis_code": "US_GAAP_TOTAL_REVENUE",
                "revenue_actual_currency": "USD",
                "revenue_actual_unit": "B",
                "revenue_actual_period": "Q3 FY2026",
                "judgment": "實際值已由公司公告核實；公告前共識缺乏有效PIT與口徑證據，不判定Beat/Miss。",
                "actual_source": {"name": "Ross Stores official results", "url": "https://example.com/issuer-results"},
            }],
        }
        applied = apply_last_week_earnings_actuals(data)
        event = data["last_week_earnings"]["events"][0]
        self.assertEqual(applied, 1)
        self.assertEqual(event["status"], "released")
        self.assertEqual(event["eps_actual"], 1.91)
        self.assertEqual(event["revenue_actual"], 6.255954)
        self.assertEqual(event["eps_estimate"], 1.86)
        self.assertTrue(event["report_layer_only"])

    def test_refuses_to_overwrite_authoritative_actuals(self):
        data = {
            "report_cutoff_taipei": "2026-11-23 05:25",
            "last_week_earnings": {"events": [{
                "id": "released", "event_date": "2026-11-20T05:00:00+08:00",
                "ticker": "ROST", "status": "released", "eps_actual": 1.91,
            }]},
            "last_week_earnings_actuals": [{
                "event_id": "released", "event_date": "2026-11-20T05:00:00+08:00",
                "ticker": "ROST", "eps_actual": 1.92,
                "actual_source": {"url": "https://example.com/issuer-results"},
            }],
        }
        with self.assertRaisesRegex(ValueError, "refusing to overwrite authoritative"):
            apply_last_week_earnings_actuals(data)


if __name__ == "__main__":
    unittest.main()
