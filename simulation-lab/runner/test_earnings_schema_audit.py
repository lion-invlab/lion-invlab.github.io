#!/usr/bin/env python3
"""Tests for the read-only earnings migration audit output."""
import csv
from pathlib import Path
from tempfile import TemporaryDirectory

from audit_earnings_schema import write_migration_csv


def main():
    rows = [{
        "ticker": "FERG",
        "eps_legacy_status": "beat",
        "eps_v2_status": "beat",
        "eps_actual_basis_code": "NON_GAAP_ADJUSTED_DILUTED_EPS",
        "eps_estimate_basis_code": "NON_GAAP_ADJUSTED_DILUTED_EPS",
        "eps_reason": "actual_above_comparable_consensus",
        "revenue_legacy_status": "beat",
        "revenue_v2_status": "pending",
        "revenue_actual_basis_code": "US_GAAP_NET_SALES",
        "revenue_estimate_basis_code": None,
        "revenue_reason": "missing_or_unrecognized_normalized_basis_code",
    }]
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "migration.csv"
        write_migration_csv(rows, str(path))
        with path.open(encoding="utf-8-sig", newline="") as handle:
            result = list(csv.DictReader(handle))
        assert len(result) == 1
        assert result[0]["ticker"] == "FERG"
        assert result[0]["eps_v2_status"] == "beat"
        assert result[0]["revenue_v2_status"] == "pending"
    print("PASS: per-company migration CSV export")


if __name__ == "__main__":
    main()
