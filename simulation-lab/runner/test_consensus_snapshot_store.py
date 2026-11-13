#!/usr/bin/env python3
"""Deterministic tests for append-only point-in-time consensus snapshots."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from consensus_snapshot_store import (
    append_consensus_snapshot,
    archive_raw_response,
    build_consensus_snapshot,
)


class ConsensusSnapshotStoreTests(unittest.TestCase):
    def setUp(self):
        self.event = {
            "id": "earnings-ABC-2026Q3",
            "ticker": "ABC",
            "event_date": "2026-11-10T21:00:00+08:00",
            "reporting_period": "2026 Q3",
        }
        self.attempt = {
            "source_level": 1,
            "provider": "LSEG I/B/E/S",
            "url": "https://provider.example/consensus/ABC",
            "observed_at": "2026-11-10T04:00:00+08:00",
            "data_as_of": "2026-11-09",
            "period": "2026 Q3",
            "period_end_date": "2026-09-30",
            "value": 1.25,
            "currency": "USD",
            "unit": None,
            "basis_code": "US_GAAP_DILUTED_EPS",
            "statistic": "mean",
            "analyst_count": 18,
        }
        self.raw = {"request": {"ticker": "ABC"}, "data": [{"epsConsensusMean": 1.25}]}

    def build(self, metric="EPS", attempt=None, raw=None, ref="raw/abc.json"):
        return build_consensus_snapshot(
            self.event, metric, attempt or self.attempt, self.raw if raw is None else raw, ref
        )

    def test_valid_pre_release_snapshot_and_raw_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            ref, digest = archive_raw_response(self.raw, tmp, "2026-W46")
            snap = self.build(ref=f"{ref}")
            self.assertEqual(snap["snapshot_status"], "pre_release_eligible")
            self.assertEqual(snap["data_as_of"], "2026-11-09")
            self.assertEqual(snap["observed_at"], "2026-11-10T04:00:00+08:00")
            self.assertEqual(snap["raw_response_sha256"], digest)
            self.assertEqual(json.loads((Path(tmp) / ref).read_text()), self.raw)

    def test_same_day_date_only_is_not_proven_pre_release(self):
        attempt = dict(self.attempt, data_as_of="2026-11-10")
        snap = self.build(attempt=attempt)
        self.assertEqual(snap["snapshot_status"], "pending_cutoff_time")
        self.assertEqual(snap["reason"], "same_day_date_only_cannot_prove_pre_release")

    def test_same_day_timestamp_can_be_pre_release(self):
        attempt = dict(self.attempt, data_as_of="2026-11-10T08:00:00-05:00")
        snap = self.build(attempt=attempt)
        self.assertEqual(snap["snapshot_status"], "pre_release_eligible")

    def test_post_release_snapshot_is_rejected_for_pit(self):
        attempt = dict(self.attempt, data_as_of="2026-11-11")
        snap = self.build(attempt=attempt)
        self.assertEqual(snap["snapshot_status"], "not_pre_release")

    def test_missing_basis_is_preserved_but_not_eligible(self):
        attempt = dict(self.attempt, basis_code=None)
        snap = self.build(attempt=attempt)
        self.assertEqual(snap["snapshot_status"], "pending_required_fields")
        self.assertIn("basis_code", snap["reason"])

    def test_provider_must_match_source_level(self):
        attempt = dict(self.attempt, source_level=3, provider="LSEG I/B/E/S")
        with self.assertRaises(ValueError):
            self.build(attempt=attempt)

    def test_observed_at_requires_timezone(self):
        attempt = dict(self.attempt, observed_at="2026-11-10T04:00:00")
        with self.assertRaises(ValueError):
            self.build(attempt=attempt)

    def test_append_is_immutable_and_idempotent(self):
        first = self.build()
        self.assertTrue(append_consensus_snapshot(self.event, first))
        saved = dict(self.event["eps_consensus_snapshots"][0])
        self.assertFalse(append_consensus_snapshot(self.event, first))
        second_attempt = dict(self.attempt, data_as_of="2026-11-08", value=1.20)
        second = self.build(attempt=second_attempt, raw={"different": True})
        self.assertTrue(append_consensus_snapshot(self.event, second))
        self.assertEqual(len(self.event["eps_consensus_snapshots"]), 2)
        self.assertEqual(self.event["eps_consensus_snapshots"][0], saved)

    def test_eps_and_revenue_histories_are_separate(self):
        eps = self.build("EPS")
        rev_attempt = dict(self.attempt, unit="USD_UNIT", basis_code="US_GAAP_TOTAL_REVENUE", value=1000)
        rev = self.build("REVENUE", attempt=rev_attempt)
        append_consensus_snapshot(self.event, eps)
        append_consensus_snapshot(self.event, rev)
        self.assertEqual(len(self.event["eps_consensus_snapshots"]), 1)
        self.assertEqual(len(self.event["revenue_consensus_snapshots"]), 1)

    def test_archive_never_overwrites_corrupted_existing_blob(self):
        with tempfile.TemporaryDirectory() as tmp:
            ref, _ = archive_raw_response(self.raw, tmp, "2026-W46")
            path = Path(tmp) / ref
            path.write_text("tampered", encoding="utf-8")
            with self.assertRaises(ValueError):
                archive_raw_response(self.raw, tmp, "2026-W46")


if __name__ == "__main__":
    unittest.main(verbosity=2)
