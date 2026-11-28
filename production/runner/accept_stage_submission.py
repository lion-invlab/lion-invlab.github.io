#!/usr/bin/env python3
"""Accept ChatGPT-owned Stage 2/4 artifacts and advance the authoritative Run state.

ChatGPT workers publish only their Run-scoped artifact. The single GitHub
production workflow validates the artifact and owns the state transition,
avoiding concurrent writes to run-state.json by independent workers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from run_state import transition_state, validate_state
from stage_wr_preflight import stage_wr_preflight

ROOT = Path(__file__).resolve().parents[2]
STAGE_ARTIFACTS = {
    "STAGE_2": "market-history-web-observations.json",
    "STAGE_4": "stage4-editorial-content.json",
}


def read_json(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Required artifact missing or symlinked: {path.name}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_state_atomic(path: Path, state: dict) -> None:
    if path.is_symlink():
        raise ValueError("run-state.json must not be a symlink")
    raw = (json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    temp = path.with_name(".run-state.json.tmp")
    if temp.exists() or temp.is_symlink():
        temp.unlink()
    with temp.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)
    try:
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass


def _transition_to_submitted(state: dict, stage: str, context: dict,
                             artifact_sha: str, artifact_path: Path,
                             input_sha: str) -> dict:
    current = state["stages"][stage]["status"]
    if current == "SUBMITTED":
        if state["stages"][stage].get("output_sha256") == artifact_sha:
            return state
        # A Stage 2 worker may submit a corrected Run-bound observation packet
        # only when the previous submission failed before a snapshot receipt
        # or summary was persisted. The serialized GitHub Runner owns this reset.
        if (stage == "STAGE_2"
                and not (artifact_path.parent / "stage2-market-snapshot-receipt.json").exists()
                and not (artifact_path.parent / "stage2-run-summary.json").exists()):
            state = transition_state(state, stage=stage,
                expected_version=state["state_version"], expected_status="SUBMITTED",
                new_status="READY", recovery=True)
            current = "READY"
        else:
            raise ValueError(f"{stage} already SUBMITTED with a different artifact SHA and is not safely recoverable")
    if current in {"PASS", "PARTIAL"}:
        # Runners replace output_sha256 with their receipt SHA on completion;
        # input_sha256 remains the accepted ChatGPT artifact SHA.
        if state["stages"][stage].get("input_sha256") == artifact_sha:
            return state
        raise ValueError(f"{stage} is already complete with a different artifact")
    if current == "DEFERRED":
        state = transition_state(state, stage=stage,
            expected_version=state["state_version"], expected_status="DEFERRED",
            new_status="READY")
        current = "READY"
    if current != "READY":
        raise ValueError(f"{stage} must be READY before accepting a worker artifact; found {current}")
    now = datetime.now(timezone.utc)
    state = transition_state(state, stage=stage,
        expected_version=state["state_version"], expected_status="READY",
        new_status="RUNNING", now=now.isoformat().replace("+00:00", "Z"),
        input_sha256=input_sha, lease_owner=f"github-handoff-{stage.lower()}",
        lease_expires_at=(now + timedelta(minutes=10)).isoformat().replace("+00:00", "Z"))
    state = transition_state(state, stage=stage,
        expected_version=state["state_version"], expected_status="RUNNING",
        new_status="SUBMITTED", now=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        output_sha256=artifact_sha, receipt_path=str(artifact_path.relative_to(ROOT)))
    validate_state(state, expected_run_id=context["run_id"])
    return state


def accept_stage2(run_dir: Path, context: dict, state: dict) -> tuple[dict, dict]:
    artifact = run_dir / STAGE_ARTIFACTS["STAGE_2"]
    payload = read_json(artifact)
    stage1_receipt = read_json(run_dir / "stage1-receipt.json")
    if stage1_receipt.get("status") != "PASS" or stage1_receipt.get("run_id") != context["run_id"]:
        raise ValueError("Stage 2 requires the exact Run's PASS Stage 1 receipt")
    stage1_fixture = run_dir / "stage1-fixture.json"
    context_path = run_dir / "run-context.json"
    if not stage1_fixture.is_file() or stage1_fixture.is_symlink():
        raise ValueError("Stage 1 immutable fixture is missing")
    expected = {
        "run_id": context["run_id"],
        "report_date": context["report_date"],
        "trading_date": context["trading_date"],
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise ValueError(f"Stage 2 artifact {key} does not match the exact Stage 1 Run")
    if payload.get("schema_version") != "1.1":
        raise ValueError("Stage 2 observation schema_version must be 1.1")
    if not payload.get("captured_at_utc"):
        raise ValueError("Stage 2 captured_at_utc is required")
    wr = stage_wr_preflight("STAGE_2", context)
    observations = payload.get("observations")
    if not isinstance(observations, list) or len(observations) != 44:
        raise ValueError("Stage 2 artifact must contain exactly 44 observations")
    keys = [(x.get("group"), x.get("name")) for x in observations if isinstance(x, dict)]
    if len(keys) != 44 or len(set(keys)) != 44:
        raise ValueError("Stage 2 observations must contain 44 unique group/name identities")
    fixture = read_json(run_dir / "stage1-fixture.json")
    expected_keys = set()
    for group in ("global_markets", "bonds", "fx", "energy", "metals", "risk"):
        expected_keys.update((group, name) for name in (fixture.get(group) or {}))
    expected_keys.update(("sectors", name) for name in (fixture.get("sectors") or {}))
    if set(keys) != expected_keys:
        raise ValueError("Stage 2 observation identities differ from the exact 44-row Stage 1 fixture")
    if not isinstance(payload.get("fedwatch"), dict):
        raise ValueError("Independent FedWatch observation object is required")
    artifact_sha = digest(artifact)
    state = _transition_to_submitted(state, "STAGE_2", context, artifact_sha, artifact,
                                     None)
    return state, {"stage": "STAGE_2", "status": "SUBMITTED",
                   "artifact_path": str(artifact.relative_to(ROOT)),
                   "artifact_sha256": artifact_sha, "wr_sha256": wr["wr_sha256"]}


def accept_stage4(run_dir: Path, context: dict, state: dict) -> tuple[dict, dict]:
    artifact = run_dir / STAGE_ARTIFACTS["STAGE_4"]
    content = read_json(artifact)
    stage3_receipt_path = run_dir / "stage3-calendar-receipt.json"
    capture_path = run_dir / "capture-stage-receipt.json"
    bundle_receipt_path = run_dir / "stage4-research-bundle-receipt.json"
    summary_path = run_dir / "stage2-run-summary.json"
    for path in (stage3_receipt_path, capture_path, bundle_receipt_path, summary_path):
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Stage 4 upstream handoff missing or symlinked: {path.name}")
    stage3 = read_json(stage3_receipt_path)
    capture = read_json(capture_path)
    bundle_receipt = read_json(bundle_receipt_path)
    summary = read_json(summary_path)
    if stage3.get("status") != "PASS" or stage3.get("run_id") != context["run_id"]:
        raise ValueError("Stage 4 requires the exact Run's PASS Stage 3 receipt")
    if state["stages"]["STAGE_3"]["status"] != "PASS":
        raise ValueError("Stage 4 cannot be accepted before Stage 3 state is PASS")
    instructions = capture.get("stage4_work_instructions") or {}
    wr = stage_wr_preflight("STAGE_4", context)
    full_wr_text = instructions.get("full_text")
    full_wr_sha = hashlib.sha256(full_wr_text.encode("utf-8")).hexdigest() if isinstance(full_wr_text, str) else None
    if (capture.get("status") != "AWAITING_EDITORIAL_INPUT"
            or capture.get("run_id") != context["run_id"]
            or capture.get("report_date") != context["report_date"]
            or instructions.get("path") != "production/stages/STAGE_4_NEWS_ANALYSIS.md"
            or not isinstance(full_wr_text, str) or not full_wr_text.strip()):
        raise ValueError("Stage 4 capture handoff does not match the pinned full Stage 4 WR")
    expected = {
        "run_id": context["run_id"],
        "report_date": context["report_date"],
        "trading_date": context["trading_date"],
        "market_snapshot_sha256": summary.get("market_snapshot_sha256"),
        "research_bundle_sha256": bundle_receipt.get("bundle_sha256"),
    }
    for key, value in expected.items():
        if not value or content.get(key) != value:
            raise ValueError(f"Stage 4 editorial artifact {key} does not match the exact Run handoff")
    artifact_sha = digest(artifact)
    state = _transition_to_submitted(state, "STAGE_4", context, artifact_sha, artifact,
                                     digest(stage3_receipt_path))
    return state, {"stage": "STAGE_4", "status": "SUBMITTED",
                   "artifact_path": str(artifact.relative_to(ROOT)),
                   "artifact_sha256": artifact_sha, "wr_sha256": wr["wr_sha256"]}


def accept_stage_submission(run_dir: str | Path, stage: str) -> dict:
    if stage not in STAGE_ARTIFACTS:
        raise ValueError("Only ChatGPT-owned STAGE_2 and STAGE_4 submissions are accepted")
    supplied = Path(run_dir)
    if not supplied.is_absolute():
        supplied = ROOT / supplied
    runs = ROOT / "production" / "runs"
    if runs.is_symlink() or runs.resolve() != runs.absolute() or supplied.is_symlink():
        raise ValueError("Run path must be canonical and non-symlinked")
    run = supplied.resolve()
    if run.parent != runs.resolve():
        raise ValueError("Run must be a direct child of production/runs")
    context = read_json(run / "run-context.json")
    if context.get("run_id") != run.name:
        raise ValueError("Run directory and run-context identity mismatch")
    state_path = run / "run-state.json"
    state = read_json(state_path)
    validate_state(state, expected_run_id=run.name)
    if stage == "STAGE_2":
        state, result = accept_stage2(run, context, state)
    else:
        state, result = accept_stage4(run, context, state)
    write_state_atomic(state_path, state)
    return {**result, "run_id": run.name, "report_date": context["report_date"],
            "state_version": state["state_version"], "overall_status": state["overall_status"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--stage", required=True, choices=tuple(STAGE_ARTIFACTS))
    args = parser.parse_args()
    print(json.dumps(accept_stage_submission(args.run_dir, args.stage),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
