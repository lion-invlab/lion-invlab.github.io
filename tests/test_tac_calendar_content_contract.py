from __future__ import annotations

import copy
import json
import unittest

from validate_tac_daily_content import load_validator, validate_report_rules


class CalendarRatingContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator, cls.schema = load_validator()
        cls.base = {
            "schema_version": 2,
            "meta": {
                "report_date": "2026-11-02",
                "trading_date": "2026-10-30",
                "generated_at": "2026-11-01T12:00:00+08:00",
                "timezone": "Asia/Taipei",
                "wr_version": "3.10",
                "template_type": "monday",
                "news_window_start": "2026-10-30T12:00:00+08:00",
                "news_window_end": "2026-11-02T05:00:00+08:00"
            },
            "focus_news": [],
            "market_headlines": [],
            "economic_calendar": [],
            "earnings_calendar": [],
            "previous_economic_calendar": [],
            "previous_earnings_calendar": [],
            "coverage": {
                group: {"status": "incomplete", "source_refs": [], "checked_at": None}
                for group in ("focus_news", "market_headlines", "economic_calendar", "earnings_calendar",
                              "previous_economic_calendar", "previous_earnings_calendar")
            },
            "analysis": {
                "summary": {"headline": None, "text": None, "source_refs": [], "status": "pending_verification"},
                "market_observation_highlights": {
                    key: {"text": None, "source_refs": [], "status": "pending_verification"}
                    for key in ("market_view", "key_levels", "core_observations")
                },
                "market_sentiment": {"label": None, "score": None, "text": None, "source_refs": [], "status": "pending_verification"}
            }
        }

    def check(self, payload):
        schema_errors = list(self.validator.iter_errors(payload))
        rule_errors = validate_report_rules(payload)
        return schema_errors, rule_errors

    def economic_event(self, stars, event_id="econ"):
        return {
            "id": event_id,
            "event_date": "2026-11-03T21:00:00+08:00",
            "region": "US",
            "event_name": "Synthetic economic data",
            "importance_stars": stars,
            "importance_basis": "major_event_assessment",
            "importance_basis_source": "Synthetic, traceable TAC assessment",
            "previous": 1.0,
            "forecast": 1.1,
            "actual": None,
            "status": "upcoming",
            "impact_judgment": None,
            "source": {
                "name": "Synthetic source",
                "url": "https://example.com/economic",
                "published_at": None,
                "observed_at": "2026-11-01T12:00:00+08:00"
            }
        }

    def test_current_week_four_and_five_stars_are_valid(self):
        for stars in (4, 5):
            with self.subTest(stars=stars):
                data = copy.deepcopy(self.base)
                data["economic_calendar"] = [self.economic_event(stars)]
                schema_errors, rule_errors = self.check(data)
                self.assertFalse(schema_errors, [e.message for e in schema_errors])
                self.assertFalse(rule_errors, rule_errors)

    def test_current_week_three_stars_are_excluded(self):
        data = copy.deepcopy(self.base)
        data["economic_calendar"] = [self.economic_event(3)]
        _, rule_errors = self.check(data)
        self.assertTrue(any("TAC four/five-star" in e for e in rule_errors), rule_errors)

    def test_previous_week_archive_only_five_stars(self):
        data = copy.deepcopy(self.base)
        item = self.economic_event(4)
        item["id"] = "prior-four"
        item["event_date"] = "2026-10-30T21:00:00+08:00"
        item["status"] = "released"
        item["actual"] = 1.2
        data["previous_economic_calendar"] = [item]
        _, rule_errors = self.check(data)
        self.assertTrue(any("TAC five-star only" in e for e in rule_errors), rule_errors)

    def test_earnings_star_rating_must_be_traceable_tac_assessment(self):
        data = copy.deepcopy(self.base)
        item = {
            "id": "earnings-four",
            "event_date": "2026-11-03T21:00:00+08:00",
            "company": "Synthetic Corp",
            "ticker": "SYN",
            "session": "after_market",
            "importance_stars": 4,
            "importance_basis": "major_event_assessment",
            "importance_basis_source": "Synthetic assessment source",
            "importance_rating_source": None,
            "eps_estimate": None,
            "eps_actual": None,
            "revenue_estimate": None,
            "revenue_actual": None,
            "status": "upcoming",
            "stock_price_reaction": None,
            "source": {
                "name": "Synthetic source",
                "url": "https://example.com/earnings",
                "published_at": None,
                "observed_at": "2026-11-01T12:00:00+08:00"
            }
        }
        data["earnings_calendar"] = [item]
        schema_errors, rule_errors = self.check(data)
        self.assertFalse(schema_errors, [e.message for e in schema_errors])
        self.assertFalse(rule_errors, rule_errors)
        data["earnings_calendar"][0]["importance_stars"] = 3
        _, rule_errors = self.check(data)
        self.assertTrue(any("TAC four/five-star" in e for e in rule_errors), rule_errors)


if __name__ == "__main__":
    unittest.main()
