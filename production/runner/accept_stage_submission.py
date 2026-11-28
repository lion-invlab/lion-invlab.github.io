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
    """Accept the completed Stage 2 artifact by Run identity only.

    Observation completeness, source provenance and field semantics are handled
    once by the Stage 2 data processor and receive their final QA in Stage 5.
    """
    artifact = run_dir / STAGE_ARTIFACTS["STAGE_2"]
    payload = read_json(artifact)
    expected = {
        "run_id": context["run_id"],
        "report_date": context["report_date"],
        "trading_date": context["trading_date"],
    }
    for key, value in expected.items():
        if not value or payload.get(key) != value:
            raise ValueError(f"Stage 2 artifact {key} does not match the active Run")
    artifact_sha = digest(artifact)
    state = _transition_to_submitted(state, "STAGE_2", context, artifact_sha, artifact, None)
    return state, {
        "stage": "STAGE_2",
        "status": "SUBMITTED",
        "artifact_path": str(artifact.relative_to(ROOT)),
        "artifact_sha256": artifact_sha,
    }


def accept_stage4(run_dir: Path, context: dict, state: dict) -> tuple[dict, dict]:
    """Accept Stage 4 editorial work by Run identity after Stage 3 completes."""
    artifact = run_dir / STAGE_ARTIFACTS["STAGE_4"]
    content = read_json(artifact)
    expected = {
        "run_id": context["run_id"],
        "report_date": context["report_date"],
        "trading_date": context["trading_date"],
    }
    for key, value in expected.items():
        if not value or content.get(key) != value:
            raise ValueError(f"Stage 4 editorial artifact {key} does not match the active Run")
    artifact_sha = digest(artifact)
    state = _transition_to_submitted(state, "STAGE_4", context, artifact_sha, artifact, None)
    return state, {
        "stage": "STAGE_4",
        "status": "SUBMITTED",
        "artifact_path": str(artifact.relative_to(ROOT)),
        "artifact_sha256": artifact_sha,
    }


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
