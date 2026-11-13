#!/usr/bin/env python3
"""Deterministic tests for append-only point-in-time consensus snapshots."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import jsonschema

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
            "published_at": "2026-11-09T16:00:00+00:00",
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
            self.assertEqual(snap["published_at"], "2026-11-09T16:00:00+00:00")
            self.assertEqual(snap["observed_at"], "2026-11-10T04:00:00+08:00")
            self.assertEqual(snap["raw_response_sha256"], digest)
            self.assertEqual(json.loads((Path(tmp) / ref).read_text()), self.raw)


    def test_published_at_absent_is_explicit_null(self):
        attempt = dict(self.attempt)
        attempt.pop("published_at")
        snap = self.build(attempt=attempt)
        self.assertIsNone(snap["published_at"])

    def test_invalid_published_at_is_rejected(self):
        attempt = dict(self.attempt, published_at="2026-11-09T16:00:00")
        with self.assertRaises(ValueError):
            self.build(attempt=attempt)

    def test_snapshot_matches_schema_v2(self):
        schema_path = Path(__file__).resolve().parents[2] / "schemas" / "tac-earnings-record-v2.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(schema["$defs"]["consensusSnapshot"])
        validator.validate(self.build())

    def test_same_day_date_only_is_not_proven_pre_release(self):
        attempt = dict(self.attempt, data_as_of="2026-11-10")
        snap = self.build(attempt=attempt)
        self.assertEqual(snap["snapshot_status"], "pending_cutoff_time")
        self.assertEqual(snap["reason"], "same_day_date_only_cannot_prove_pre_release")

    def test_same_day_timestamp_can_be_pre_release(self):
        attempt = dict(self.attempt, data_as_of="2026-11-10T07:00:00-05:00")
        snap = self.build(attempt=attempt)
        self.assertEqual(snap["snapshot_status"], "pre_release_eligible")

    def test_post_release_snapshot_is_rejected_for_pit(self):
        attempt = dict(self.attempt, data_as_of="2026-11-11")
        snap = self.build(attempt=attempt)
        self.assertEqual(snap["snapshot_status"], "not_pre_release")

    def test_missing_raw_response_reference_is_not_eligible(self):
        snap = self.build(ref=None)
        self.assertEqual(snap["snapshot_status"], "pending_required_fields")
        self.assertIn("raw_response_ref", snap["reason"])

    def test_missing_basis_is_preserved_but_not_eligible(self):
        attempt = dict(self.attempt, basis_code=None)
        snap = self.build(attempt=attempt)
        self.assertEqual(snap["snapshot_status"], "pending_required_fields")
        self.assertIn("basis_code", snap["reason"])

    def test_observed_at_date_only_is_rejected(self):
        attempt = dict(self.attempt, observed_at="2026-11-10")
        with self.assertRaises(ValueError):
            self.build(attempt=attempt)

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

    def test_three_daily_polls_append_distinct_immutable_snapshots(self):
        self.event["event_date"] = "2026-11-14T21:00:00+08:00"
        for day in ("09", "10", "11"):
            attempt = dict(
                self.attempt,
                observed_at=f"2026-11-{day}T04:00:00+08:00",
                data_as_of=f"2026-11-{day}",
            )
            snap = self.build(attempt=attempt)
            self.assertEqual(snap["snapshot_status"], "pre_release_eligible")
            self.assertTrue(append_consensus_snapshot(self.event, snap))
            self.assertFalse(append_consensus_snapshot(self.event, snap))
        history = self.event["eps_consensus_snapshots"]
        self.assertEqual(len(history), 3)
        self.assertEqual([x["observed_at"] for x in history], [
            "2026-11-09T04:00:00+08:00",
            "2026-11-10T04:00:00+08:00",
            "2026-11-11T04:00:00+08:00",
        ])
        self.assertEqual(len({x["snapshot_id"] for x in history}), 3)

    def test_eps_and_revenue_histories_are_separate(self):
        eps = self.build("EPS")
        rev_attempt = dict(self.attempt, unit="USD_UNIT", basis_code="US_GAAP_TOTAL_REVENUE", value=1000)
        rev = self.build("REVENUE", attempt=rev_attempt)
        append_consensus_snapshot(self.event, eps)
        append_consensus_snapshot(self.event, rev)
        self.assertEqual(len(self.event["eps_consensus_snapshots"]), 1)
        self.assertEqual(len(self.event["revenue_consensus_snapshots"]), 1)

    def test_five_day_incremental_eps_revenue_history_with_value_changes_and_pending_cutoff(self):
        self.event["event_date"] = "2026-11-15T21:00:00+08:00"
        with tempfile.TemporaryDirectory() as tmp:
            original_eps = None
            original_revenue = None
            for day, eps_value, revenue_value in (
                ("09", 1.25, 1000.0),
                ("10", 1.25, 1000.0),
                ("11", 1.30, 1000.0),
                ("12", 1.30, 1050.0),
                ("13", 1.30, 1050.0),
            ):
                poll_time = f"2026-11-{day}T04:00:00+08:00"
                eps_attempt = dict(
                    self.attempt,
                    observed_at=poll_time,
                    data_as_of=f"2026-11-{day}",
                    value=eps_value,
                )
                revenue_attempt = dict(
                    self.attempt,
                    source_level=2,
                    provider="FactSet Estimates",
                    observed_at=poll_time,
                    data_as_of=f"2026-11-{day}",
                    value=revenue_value,
                    unit="USD_MILLION",
                    basis_code="US_GAAP_TOTAL_REVENUE",
                )
                for metric, attempt, raw in (
                    ("EPS", eps_attempt, {"day": day, "eps": eps_value}),
                    ("REVENUE", revenue_attempt, {"day": day, "revenue": revenue_value}),
                ):
                    raw_ref, _ = archive_raw_response(raw, tmp, f"2026-W46/{metric.lower()}")
                    snap = self.build(metric, attempt=attempt, raw=raw, ref=raw_ref)
                    self.assertEqual(snap["snapshot_status"], "pre_release_eligible")
                    self.assertTrue(append_consensus_snapshot(self.event, snap))
                    self.assertFalse(append_consensus_snapshot(self.event, snap))
                if day == "09":
                    original_eps = dict(self.event["eps_consensus_snapshots"][0])
                    original_revenue = dict(self.event["revenue_consensus_snapshots"][0])

            # Same-day date-only evidence is retained, but cannot be labelled pre-release eligible.
            same_day_attempt = dict(
                self.attempt,
                observed_at="2026-11-15T04:00:00+08:00",
                data_as_of="2026-11-15",
            )
            pending = self.build("EPS", attempt=same_day_attempt, raw={"same_day": True})
            self.assertEqual(pending["snapshot_status"], "pending_cutoff_time")
            self.assertTrue(append_consensus_snapshot(self.event, pending))

            eps_history = self.event["eps_consensus_snapshots"]
            revenue_history = self.event["revenue_consensus_snapshots"]
            self.assertEqual(len(eps_history), 6)
            self.assertEqual(len(revenue_history), 5)
            self.assertEqual(eps_history[0], original_eps)
            self.assertEqual(revenue_history[0], original_revenue)
            self.assertEqual([x["value"] for x in eps_history[:5]], [1.25, 1.25, 1.30, 1.30, 1.30])
            self.assertEqual([x["value"] for x in revenue_history], [1000.0, 1000.0, 1000.0, 1050.0, 1050.0])
            self.assertEqual(len({x["snapshot_id"] for x in eps_history}), 6)
            self.assertEqual(len({x["snapshot_id"] for x in revenue_history}), 5)
            self.assertTrue(all(Path(tmp, x["raw_response_ref"]).is_file() for x in eps_history + revenue_history))

    def test_archive_never_overwrites_corrupted_existing_blob(self):
        with tempfile.TemporaryDirectory() as tmp:
            ref, _ = archive_raw_response(self.raw, tmp, "2026-W46")
            path = Path(tmp) / ref
            path.write_text("tampered", encoding="utf-8")
            with self.assertRaises(ValueError):
                archive_raw_response(self.raw, tmp, "2026-W46")


if __name__ == "__main__":
    unittest.main(verbosity=2)
