#!/usr/bin/env python3
"""Fail-closed validation for a ChatGPT Stage 2 input bundle bound to one Main Run."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

RUN_ROOT = Path("production/runs")
EXPECTED_OBSERVATIONS = "market-history-web-observations.json"
EXPECTED_CNN = "cnn-fear-greed-observation.json"
EXPECTED_SCREENSHOTS = "market-screenshot-observations.json"
SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value, hashlib.sha256(raw).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def run_file(run_dir: Path, name: str) -> Path:
    require(isinstance(name, str) and name and Path(name).name == name,
            f"Run artifact must be a direct child filename: {name!r}")
    path = run_dir / name
    require(not path.is_symlink(), f"Symlink is not allowed: {name}")
    require(path.is_file(), f"Required Run artifact is missing: {name}")
    require(path.resolve().parent == run_dir.resolve(),
            f"Run artifact escaped its Run directory: {name}")
    return path


def verify(run_dir: Path, bundle_path: Path) -> dict:
    runs_root = RUN_ROOT.resolve()
    require(not RUN_ROOT.is_symlink(), "production/runs must not be a symlink")
    require(not run_dir.is_symlink(), "Run directory must not be a symlink")
    run_dir = run_dir.resolve()
    require(run_dir.parent == runs_root, "Run directory must be a direct child of production/runs")
    require(bundle_path.resolve().parent == run_dir, "Handoff bundle must be inside this exact Run")
    require(not bundle_path.is_symlink() and bundle_path.is_file(), "Handoff bundle is missing or symlinked")

    context_path = run_file(run_dir, "run-context.json")
    fixture_path = run_file(run_dir, "report-data.json")
    receipt_path = run_file(run_dir, "stage1-receipt.json")
    context, context_sha = load_json(context_path)
    fixture, fixture_sha = load_json(fixture_path)
    receipt, receipt_sha = load_json(receipt_path)
    bundle, _ = load_json(bundle_path)

    run_id = run_dir.name
    report_date = context.get("report_date")
    trading_date = context.get("trading_date")
    require(context.get("run_id") == run_id, "run-context run_id does not match Run directory")
    require(fixture.get("report_date") == report_date and fixture.get("trading_date") == trading_date,
            "Stage 1 fixture dates do not match run-context")
    require(receipt.get("status") == "PASS", "Stage 1 receipt is not PASS")
    require(receipt.get("run_id") == run_id, "Stage 1 receipt run_id mismatch")
    require(receipt.get("report_date") == report_date and receipt.get("trading_date") == trading_date,
            "Stage 1 receipt dates mismatch")
    require(receipt.get("run_context_sha256") == context_sha, "Stage 1 receipt run-context SHA mismatch")
    require(receipt.get("fixture_sha256") == fixture_sha, "Stage 1 receipt fixture SHA mismatch")

    required = {
        "schema_version": "1.0",
        "stage": "STAGE2_CHATGPT_INPUT",
        "run_id": run_id,
        "report_date": report_date,
        "trading_date": trading_date,
        "stage1_receipt_sha256": receipt_sha,
        "run_context_sha256": context_sha,
        "stage1_fixture_sha256": fixture_sha,
    }
    for key, expected in required.items():
        require(bundle.get(key) == expected, f"Stage 2 handoff {key} mismatch")
    captured = bundle.get("captured_at_utc")
    require(isinstance(captured, str), "captured_at_utc is required")
    parsed = datetime.fromisoformat(captured.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None, "captured_at_utc must be timezone-aware")
    age = datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)
    require(age.total_seconds() >= -300, "Stage 2 handoff timestamp is in the future")
    require(age.total_seconds() <= 24 * 3600, "Stage 2 handoff timestamp is stale")

    observations_path = run_file(run_dir, EXPECTED_OBSERVATIONS)
    require(bundle.get("market_observations_path") == EXPECTED_OBSERVATIONS,
            "market observations path must be the fixed Run-local filename")
    observations, observations_sha = load_json(observations_path)
    require(bundle.get("market_observations_sha256") == observations_sha,
            "market observations SHA-256 mismatch")
    require(observations.get("schema_version") == "1.0", "market observations schema_version mismatch")
    require(observations.get("report_date") == report_date and observations.get("trading_date") == trading_date,
            "market observations dates do not match this Run")
    rows = observations.get("observations")
    require(isinstance(rows, list) and len(rows) == 44, "market observations must contain exactly 44 rows")
    keys = [(x.get("group"), x.get("name")) for x in rows]
    require(len(set(keys)) == 44 and all(g and n for g, n in keys),
            "market observations contain duplicate or unnamed rows")
    require(all(x.get("target_date") == trading_date for x in rows),
            "market observation target_date differs from this Run trading_date")
    require(all(x.get("prior_observation_reused") is not True for x in rows),
            "cross-Run or prior observation reuse is forbidden")

    cnn_name = bundle.get("cnn_observation_path")
    cnn_hash = bundle.get("cnn_observation_sha256")
    require((cnn_name is None) == (cnn_hash is None), "CNN path and SHA must be supplied together")
    if cnn_name is not None:
        require(cnn_name == EXPECTED_CNN, "CNN observation path must be the fixed Run-local filename")
        cnn_path = run_file(run_dir, EXPECTED_CNN)
        cnn, actual = load_json(cnn_path)
        require(actual == cnn_hash, "CNN observation SHA-256 mismatch")
        for row in cnn.get("observations", []):
            require(row.get("target_date") == trading_date, "CNN target_date differs from this Run")
            require(row.get("observed_date") == report_date, "CNN observed_date differs from report_date")

    screenshot_name = bundle.get("screenshot_observations_path")
    screenshot_hash = bundle.get("screenshot_observations_sha256")
    require((screenshot_name is None) == (screenshot_hash is None),
            "screenshot sidecar path and SHA must be supplied together")
    screenshot_count = 0
    if screenshot_name is not None:
        require(screenshot_name == EXPECTED_SCREENSHOTS,
                "screenshot sidecar path must be the fixed Run-local filename")
        screenshot_path = run_file(run_dir, EXPECTED_SCREENSHOTS)
        screenshots, actual = load_json(screenshot_path)
        require(actual == screenshot_hash, "screenshot sidecar SHA-256 mismatch")
        require(screenshots.get("report_date") == report_date
                and screenshots.get("trading_date") == trading_date,
                "screenshot sidecar dates do not match this Run")
        evidence = bundle.get("screenshot_evidence")
        require(isinstance(evidence, list), "screenshot_evidence must be an array")
        for item in evidence:
            name, expected_sha = item.get("path"), item.get("sha256")
            require(isinstance(expected_sha, str) and SHA_RE.fullmatch(expected_sha),
                    "screenshot evidence SHA-256 is malformed")
            path = run_file(run_dir, name)
            require(sha256(path) == expected_sha, f"screenshot evidence SHA-256 mismatch: {name}")
            screenshot_count += 1
    else:
        require(bundle.get("screenshot_evidence", []) == [],
                "screenshot bytes cannot be supplied without a Run-local screenshot sidecar")

    return {
        "status": "PASS",
        "stage": "STAGE2_CHATGPT_INPUT",
        "run_id": run_id,
        "report_date": report_date,
        "trading_date": trading_date,
        "stage1_receipt_sha256": receipt_sha,
        "run_context_sha256": context_sha,
        "stage1_fixture_sha256": fixture_sha,
        "market_observations_sha256": observations_sha,
        "observation_count": len(rows),
        "cnn_observation_sha256": cnn_hash,
        "screenshot_evidence_count": screenshot_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--bundle", default="stage2-chatgpt-handoff.json")
    parser.add_argument("--output")
    args = parser.parse_args()
    root = Path(args.run_dir)
    if not root.is_absolute():
        root = Path.cwd() / root
    bundle = Path(args.bundle)
    if not bundle.is_absolute():
        bundle = root / bundle
    result = verify(root, bundle)
    raw = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = Path(args.output)
        if not output.is_absolute():
            output = Path.cwd() / output
        output.write_text(raw, encoding="utf-8")
    print(raw, end="")


if __name__ == "__main__":
    main()
