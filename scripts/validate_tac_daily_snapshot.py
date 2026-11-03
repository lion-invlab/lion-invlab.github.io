#!/usr/bin/env python3
"""Validate normalized TAC daily market snapshots against the checked-in JSON Schema."""
from __future__ import annotations
import argparse
import copy
import json
import sys
import os
import hashlib
import re
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path

from tac_wr_lock import load_local_wr_version, parse_wr_version

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "tac-daily-market-snapshot.schema.json"

def load_validator():
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError:
        raise RuntimeError("Missing dependency: install jsonschema before validating TAC snapshots")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker()), schema

def load_active_wr_lock():
    lock_path = os.environ.get("TAC_WR_LOCK_FILE")
    if lock_path:
        lock = json.loads(Path(lock_path).read_text(encoding="utf-8"))
        required = {"wr_version", "wr_commit_sha", "wr_blob_sha", "wr_content_sha256"}
        missing = sorted(required - set(lock))
        if missing:
            raise ValueError("WR lock record is missing: " + ", ".join(missing))
        return lock
    return {"wr_version": load_local_wr_version()}



def validate_snapshot_wr_provenance(data: dict, allow_historical: bool) -> None:
    """Validate the exact WR revision recorded by a formal snapshot."""
    meta = data.get("meta", {})
    required = ("wr_version", "wr_commit_sha", "wr_blob_sha", "wr_content_sha256")
    missing = [key for key in required if not meta.get(key)]
    if missing:
        raise ValueError("snapshot WR provenance is incomplete: " + ", ".join(missing))

    commit_sha = meta["wr_commit_sha"]
    blob_sha = meta["wr_blob_sha"]
    content_sha256 = meta["wr_content_sha256"]
    if not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
        raise ValueError("snapshot WR provenance has an invalid wr_commit_sha")
    if not re.fullmatch(r"[0-9a-f]{40}", blob_sha):
        raise ValueError("snapshot WR provenance has an invalid wr_blob_sha")
    if not re.fullmatch(r"[0-9a-f]{64}", content_sha256):
        raise ValueError("snapshot WR provenance has an invalid wr_content_sha256")

    active_lock = load_active_wr_lock()
    if not allow_historical:
        if meta["wr_version"] != active_lock["wr_version"]:
            raise ValueError(
                "snapshot WR version does not match the current checked-out TAC_WORK_RULES.md; "
                "use --allow-historical-wr only for intentional historical validation"
            )
        for key in ("wr_commit_sha", "wr_blob_sha", "wr_content_sha256"):
            if active_lock.get(key) and meta[key] != active_lock[key]:
                raise ValueError(f"snapshot {key} does not match the active WR lock")

    try:
        committed_content = subprocess.run(
            ["git", "show", f"{commit_sha}:TAC_WORK_RULES.md"],
            cwd=ROOT, check=True, capture_output=True, text=True,
        ).stdout
        committed_blob = subprocess.run(
            ["git", "rev-parse", f"{commit_sha}:TAC_WORK_RULES.md"],
            cwd=ROOT, check=True, capture_output=True, text=True,
        ).stdout.strip()
    except subprocess.CalledProcessError as exc:
        raise ValueError(
            "cannot resolve the snapshot's recorded WR commit; ensure repository history is available"
        ) from exc

    actual_version = parse_wr_version(committed_content)
    actual_content_sha256 = hashlib.sha256(committed_content.encode("utf-8")).hexdigest()
    if actual_version != meta["wr_version"]:
        raise ValueError(
            f"snapshot wr_version {meta['wr_version']} does not match recorded commit version {actual_version}"
        )
    if committed_blob != blob_sha:
        raise ValueError("snapshot wr_blob_sha does not match TAC_WORK_RULES.md at wr_commit_sha")
    if actual_content_sha256 != content_sha256:
        raise ValueError("snapshot wr_content_sha256 does not match TAC_WORK_RULES.md at wr_commit_sha")

    if not allow_historical and commit_sha != active_lock.get("wr_commit_sha"):
        raise ValueError("snapshot wr_commit_sha does not match the active WR lock")

def sample_snapshot(schema):
    props = schema["properties"]
    lock = load_active_wr_lock()
    snapshot = {
        "schema_version": 1,
        "meta": {
            "report_date": "2026-11-02",
            "trading_date": "2026-10-30",
            "generated_at": "2026-10-31T11:00:00+08:00",
            "timezone": "Asia/Taipei",
            "wr_version": lock["wr_version"],
        },
    }
    if "wr_commit_sha" in lock:
        snapshot["meta"].update({
            "wr_commit_sha": lock["wr_commit_sha"],
            "wr_blob_sha": lock["wr_blob_sha"],
            "wr_content_sha256": lock["wr_content_sha256"],
        })
    for group in ("global_indices", "sectors", "bonds", "fx", "energy", "precious_metals", "risk_indicators"):
        snapshot[group] = {}
        for key in props[group]["required"]:
            snapshot[group][key] = {
                "value": None, "unit": "index point", "change": None,
                "change_unit": None, "status": "pending_verification",
                "source": None, "fallback_used": False,
                "fallback_reason": None, "notes": "Awaiting source retrieval",
            }
    snapshot["fedwatch"] = {
        "target_meeting": None, "updated_at": None, "source": None,
        "probabilities": [], "status": "pending_verification",
        "notes": "Awaiting current meeting snapshot",
    }
    return snapshot

def self_test(validator, schema):
    valid = sample_snapshot(schema)
    errors = list(validator.iter_errors(valid))
    if errors:
        raise AssertionError("valid pending-data snapshot rejected: " + "; ".join(e.message for e in errors[:5]))
    print("PASS: complete pending-data snapshot accepted")

    bad_verified = copy.deepcopy(valid)
    bad_verified["global_indices"]["sp500"]["status"] = "verified"
    errors = list(validator.iter_errors(bad_verified))
    if not errors:
        raise AssertionError("verified record with null value/source unexpectedly passed")
    print("PASS: verified record without value/source rejected")

    bad_fallback = copy.deepcopy(valid)
    bad_fallback["fx"]["usd_twd"]["fallback_used"] = True
    errors = list(validator.iter_errors(bad_fallback))
    if not errors:
        raise AssertionError("fallback without reason unexpectedly passed")
    print("PASS: fallback without reason rejected")

    bad_field = copy.deepcopy(valid)
    del bad_field["global_indices"]["sox"]
    errors = list(validator.iter_errors(bad_field))
    if not errors:
        raise AssertionError("missing required market field unexpectedly passed")
    print("PASS: missing required market field rejected")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="Snapshot JSON file to validate")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--allow-historical-wr", action="store_true", help="Allow a snapshot created under a prior WR version")
    args = parser.parse_args()
    validator, schema = load_validator()
    if args.self_test:
        self_test(validator, schema)
        return 0
    if not args.file:
        parser.error("--file is required unless --self-test is used")
    path = Path(args.file)
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_snapshot_wr_provenance(data, allow_historical=args.allow_historical_wr)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    if errors:
        for error in errors:
            location = ".".join(str(x) for x in error.path) or "$"
            print("FAIL " + location + ": " + error.message, file=sys.stderr)
        print("TAC MARKET SNAPSHOT INVALID", file=sys.stderr)
        return 1
    print("PASS: TAC market snapshot conforms to schema")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
