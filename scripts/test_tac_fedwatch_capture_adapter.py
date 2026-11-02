#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from adapt_tac_fedwatch_capture import adapt_capture, parse_rate_range

def capture():
    return {
        "provider": "Investing.com Fed Rate Monitor",
        "role": "primary",
        "status": "captured_for_review",
        "source_url": "https://www.investing.com/central-banks/fed-rate-monitor",
        "observed_at": "2026-11-02T05:00:00+08:00",
        "source_updated_at_iso": "2026-11-02T04:55:00+08:00",
        "source_age_hours": 0.08,
        "current_target_range": "3.75-4.00",
        "validation": {
            "is_monitor": True, "has_meeting_probabilities": True,
            "has_current_target_range": True, "has_source_update_time": True,
            "is_fresh": True,
        },
        "meetings": [
            {"meeting_date": "Dec 09, 2026", "probabilities": [
                {"target_rate": "3.75-4.00", "probability": 63.2},
                {"target_rate": "4.00-4.25", "probability": 36.8},
            ]},
            {"meeting_date": "Jan 27, 2027", "probabilities": [
                {"target_rate": "3.75-4.00", "probability": 50.0},
                {"target_rate": "4.00-4.25", "probability": 50.0},
            ]},
        ],
    }

class FedWatchCaptureAdapterTests(unittest.TestCase):
    def test_maps_only_current_range_and_exact_one_quarter_hike(self):
        normalized, renderer, error = adapt_capture(capture(), "2026-11-02")
        self.assertIsNone(error)
        self.assertEqual(normalized["status"], "verified")
        self.assertEqual(normalized["target_meeting"], "2026-12-09")
        self.assertEqual(renderer["probabilities"]["hold"]["probability"], 63.2)
        self.assertEqual(renderer["probabilities"]["hike_one"]["probability"], 36.8)
        self.assertEqual(renderer["target_rate_range"], "3.75-4.00%")
        self.assertEqual(sum(x["probability"] for x in normalized["probabilities"]), 100.0)

    def test_cut_or_other_outcome_is_not_mislabelled_as_hike(self):
        data = capture()
        data["meetings"][0]["probabilities"][1]["target_rate"] = "3.50-3.75"
        normalized, renderer, error = adapt_capture(data, "2026-11-02")
        self.assertIsNone(normalized)
        self.assertIsNone(renderer)
        self.assertIn("refusing to infer", error)

    def test_missing_current_target_range_remains_pending(self):
        data = capture()
        data["current_target_range"] = None
        normalized, renderer, error = adapt_capture(data, "2026-11-02")
        self.assertIsNone(normalized)
        self.assertIsNone(renderer)
        self.assertIn("rate range", error)

    def test_more_than_two_outcomes_remains_pending(self):
        data = capture()
        data["meetings"][0]["probabilities"].append({"target_rate": "4.25-4.50", "probability": 0.0})
        normalized, renderer, error = adapt_capture(data, "2026-11-02")
        self.assertIsNone(normalized)
        self.assertIsNone(renderer)
        self.assertIn("exactly two", error)

    def test_live_page_values_are_not_rejected_due_to_old_provider_updated_label(self):
        data = capture()
        data["source_age_hours"] = 2400
        data["source_updated_at_iso"] = "2026-10-01T00:00:00+00:00"
        normalized, renderer, error = adapt_capture(data, "2026-11-02")
        self.assertIsNone(error)
        self.assertEqual(normalized["updated_at"], data["observed_at"])
        self.assertIn("provider Updated label=2026-10-01", normalized["notes"])

    def test_live_page_capture_does_not_require_provider_updated_label(self):
        data = capture()
        data["source_updated_at_iso"] = None
        normalized, renderer, error = adapt_capture(data, "2026-11-02")
        self.assertIsNone(error)
        self.assertEqual(normalized["updated_at"], data["observed_at"])

    def test_wrong_role_capture_remains_pending(self):
        data = capture()
        data["role"] = "fallback"
        normalized, renderer, error = adapt_capture(data, "2026-11-02")
        self.assertIsNone(normalized)
        self.assertIn("primary", error)

    def test_invalid_range_rejected(self):
        with self.assertRaises(ValueError):
            parse_rate_range("3.75 to 4.00")

if __name__ == "__main__":
    unittest.main(verbosity=2)
