#!/usr/bin/env python3
"""Deterministic tests for report-layer repair of URL-corrupted calendar impact fields."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_review_html import apply_calendar_impact_overrides


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


if __name__ == "__main__":
    unittest.main()
