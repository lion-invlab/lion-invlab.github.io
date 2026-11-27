#!/usr/bin/env python3
"""Positive and negative tests for the same-Run Stage 2 handoff validator."""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
from pathlib import Path

import validate_stage2_run_handoff as validator


def write_json(path: Path, value: dict) -> str:
    raw = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def fixture_run(root: Path) -> tuple[Path, dict]:
    run_id = "TAC-2026-11-27-test-1"
    run_dir = root / "runs" / run_id
    run_dir.mkdir(parents=True)
    context = {
        "schema_version": "1.0", "run_id": run_id,
        "report_date": "2026-11-27", "trading_date": "2026-11-26",
    }
    fixture = {
        "report_date": context["report_date"], "trading_date": context["trading_date"],
    }
    context_sha = write_json(run_dir / "run-context.json", context)
    fixture_sha = write_json(run_dir / "report-data.json", fixture)
    receipt = {
        "status": "PASS", "run_id": run_id,
        "report_date": context["report_date"], "trading_date": context["trading_date"],
        "run_context_sha256": context_sha, "fixture_sha256": fixture_sha,
    }
    receipt_sha = write_json(run_dir / "stage1-receipt.json", receipt)
    observations = {
        "schema_version": "1.0", "report_date": context["report_date"],
        "trading_date": context["trading_date"], "captured_at_utc": "2026-11-27T00:00:00Z",
        "observations": [
            {"group": f"group-{i // 11}", "name": f"instrument-{i}",
             "target_date": context["trading_date"], "prior_observation_reused": False}
            for i in range(44)
        ],
    }
    obs_sha = write_json(run_dir / "market-history-web-observations.json", observations)
    bundle = {
        "schema_version": "1.0", "stage": "STAGE2_CHATGPT_INPUT",
        "run_id": run_id, "report_date": context["report_date"],
        "trading_date": context["trading_date"],
        "stage1_receipt_sha256": receipt_sha,
        "run_context_sha256": context_sha, "stage1_fixture_sha256": fixture_sha,
        "captured_at_utc": "2026-11-27T00:00:00Z",
        "market_observations_path": "market-history-web-observations.json",
        "market_observations_sha256": obs_sha,
        "screenshot_evidence": [],
    }
    bundle_path = run_dir / "stage2-chatgpt-handoff.json"
    write_json(bundle_path, bundle)
    return run_dir, bundle


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        validator.RUN_ROOT = root / "runs"
        validator.RUN_ROOT.mkdir()
        run_dir, bundle = fixture_run(root)
        result = validator.verify(run_dir, run_dir / "stage2-chatgpt-handoff.json")
        assert result["status"] == "PASS" and result["observation_count"] == 44

        bad = copy.deepcopy(bundle)
        bad["run_id"] = "TAC-2026-11-27-other-1"
        write_json(run_dir / "stage2-chatgpt-handoff.json", bad)
        try:
            validator.verify(run_dir, run_dir / "stage2-chatgpt-handoff.json")
        except ValueError as exc:
            assert "run_id mismatch" in str(exc)
        else:
            raise AssertionError("wrong Run ID must fail closed")

        bad = copy.deepcopy(bundle)
        bad["stage1_fixture_sha256"] = "0" * 64
        write_json(run_dir / "stage2-chatgpt-handoff.json", bad)
        try:
            validator.verify(run_dir, run_dir / "stage2-chatgpt-handoff.json")
        except ValueError as exc:
            assert "stage1_fixture_sha256 mismatch" in str(exc)
        else:
            raise AssertionError("wrong Stage 1 fixture SHA must fail closed")

        write_json(run_dir / "stage2-chatgpt-handoff.json", bundle)
        observations_path = run_dir / "market-history-web-observations.json"
        observations = json.loads(observations_path.read_text(encoding="utf-8"))
        observations["observations"][0]["target_date"] = "2026-11-25"
        write_json(observations_path, observations)
        try:
            validator.verify(run_dir, run_dir / "stage2-chatgpt-handoff.json")
        except ValueError as exc:
            assert "market observations SHA-256 mismatch" in str(exc)
        else:
            raise AssertionError("changed observation bytes must fail SHA validation")

    print("PASS: same-Run handoff accepts exact inputs and rejects Run/SHA/date tampering")


if __name__ == "__main__":
    main()
