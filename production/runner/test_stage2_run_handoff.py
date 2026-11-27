#!/usr/bin/env python3
"""Positive and negative tests for the same-Run Stage 2 handoff validator."""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
from datetime import datetime, timezone
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
    counts = {
        "global_markets": 17, "bonds": 3, "fx": 6,
        "energy": 2, "metals": 2, "risk": 3,
    }
    fixture = {
        "report_date": context["report_date"], "trading_date": context["trading_date"],
        "sectors": {}, "sector_sources": {},
    }
    expected_rows = []
    for group, count in counts.items():
        fixture[group] = {}
        for i in range(count):
            name = f"{group}-instrument-{i}"
            url = f"https://example.com/{group}/{i}"
            fixture[group][name] = {"source": {"url": url}}
            expected_rows.append((group, name, url))
    for i in range(11):
        name = f"sector-instrument-{i}"
        url = f"https://example.com/sectors/{i}"
        fixture["sectors"][name] = "待擷取"
        fixture["sector_sources"][name] = {"url": url}
        expected_rows.append(("sectors", name, url))
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
        "trading_date": context["trading_date"], "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "observations": [
            {"group": group, "name": name, "source_url": url,
             "instrument_identity": name, "target_date": context["trading_date"],
             "prior_observation_reused": False}
            for group, name, url in expected_rows
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

        # Screenshot bytes must be present under this Run and hash exactly.
        screenshots_dir = run_dir / "screenshots"
        screenshots_dir.mkdir()
        screenshot_bytes = b"same-run screenshot evidence"
        screenshot_path = screenshots_dir / "move.png"
        screenshot_path.write_bytes(screenshot_bytes)
        screenshot_sha = hashlib.sha256(screenshot_bytes).hexdigest()
        screenshot_sidecar = {
            "report_date": "2026-11-27", "trading_date": "2026-11-26",
            "observations": [],
        }
        sidecar_sha = write_json(run_dir / "market-screenshot-observations.json", screenshot_sidecar)
        with_screenshot = copy.deepcopy(bundle)
        with_screenshot.update({
            "screenshot_observations_path": "market-screenshot-observations.json",
            "screenshot_observations_sha256": sidecar_sha,
            "screenshot_evidence": [{"path": "screenshots/move.png", "sha256": screenshot_sha}],
        })
        write_json(run_dir / "stage2-chatgpt-handoff.json", with_screenshot)
        result = validator.verify(run_dir, run_dir / "stage2-chatgpt-handoff.json")
        assert result["screenshot_evidence_count"] == 1
        write_json(run_dir / "stage2-chatgpt-handoff.json", bundle)

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

        # Even if a submitter recomputes the bundle SHA, a row targeting another
        # trading date is rejected as cross-date input.
        observations["observations"][0]["target_date"] = "2026-11-25"
        obs_sha = write_json(observations_path, observations)
        bad = copy.deepcopy(bundle)
        bad["market_observations_sha256"] = obs_sha
        write_json(run_dir / "stage2-chatgpt-handoff.json", bad)
        try:
            validator.verify(run_dir, run_dir / "stage2-chatgpt-handoff.json")
        except ValueError as exc:
            assert "target_date differs" in str(exc)
        else:
            raise AssertionError("cross-date observation must fail even with recomputed SHA")

    print("PASS: same-Run handoff accepts exact inputs and rejects Run/SHA/date tampering")


if __name__ == "__main__":
    main()
