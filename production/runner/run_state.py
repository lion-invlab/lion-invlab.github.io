#!/usr/bin/env python3
"""Per-Run stage state machine for TAC Main production.

This module is deliberately storage-agnostic. The caller must persist the
returned state with compare-and-swap semantics (GitHub Contents API expected
blob SHA, or a fast-forward-only git push from the observed main HEAD).
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone

SCHEMA_VERSION = "1.0"
STAGES = ("STAGE_1", "STAGE_2", "STAGE_3", "STAGE_4", "STAGE_5", "STAGE_6")
STAGE_STATUS = {
    "NOT_STARTED", "READY", "RUNNING", "SUBMITTED", "PASS",
    "DEFERRED", "PARTIAL", "FAILED", "SKIPPED",
}
OVERALL_STATUS = {
    "RUNNING", "PARTIAL", "FAILED", "REVIEW_READY",
    "DELIVERED", "AWAITING_APPROVAL", "PUBLISHED",
}
TERMINAL_STAGE = {"PASS", "PARTIAL", "FAILED", "SKIPPED"}
ACTIVE_STAGE = {"READY", "RUNNING", "SUBMITTED", "DEFERRED"}

_ALLOWED = {
    "NOT_STARTED": {"READY", "SKIPPED"},
    "READY": {"RUNNING", "DEFERRED", "SKIPPED"},
    "DEFERRED": {"READY", "RUNNING", "SKIPPED"},
    "RUNNING": {"SUBMITTED", "PASS", "PARTIAL", "FAILED", "DEFERRED"},
    "SUBMITTED": {"PASS", "PARTIAL", "FAILED"},
    "FAILED": set(),
    "PARTIAL": set(),
    "PASS": set(),
    "SKIPPED": set(),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _empty_stage(status: str = "NOT_STARTED") -> dict:
    return {
        "status": status,
        "attempt": 0,
        "started_at": None,
        "completed_at": None,
        "input_sha256": None,
        "output_sha256": None,
        "receipt_path": None,
        "error_code": None,
        "lease_owner": None,
        "lease_expires_at": None,
    }


def initial_run_state(context: dict, stage1_receipt: dict, stage1_receipt_sha256: str, now: str | None = None) -> dict:
    """Create the one authoritative state file when Stage 1 commits its Run."""
    run_id = context.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise ValueError("Stage 1 context requires run_id")
    if stage1_receipt.get("run_id") != run_id:
        raise ValueError("Stage 1 receipt run_id differs from run-context")
    if stage1_receipt.get("status") != "PASS":
        raise ValueError("Stage 1 state can only be initialized from a PASS receipt")
    if not isinstance(stage1_receipt_sha256, str) or len(stage1_receipt_sha256) != 64:
        raise ValueError("Stage 1 receipt SHA-256 is required to initialize run-state")
    timestamp = now or utc_now()
    stages = {key: _empty_stage() for key in STAGES}
    stages["STAGE_1"] = {
        **_empty_stage("PASS"),
        "attempt": 1,
        "started_at": context.get("started_at") or timestamp,
        "completed_at": timestamp,
        "input_sha256": None,
        "output_sha256": stage1_receipt_sha256,
        "receipt_path": f"production/runs/{run_id}/stage1-receipt.json",
    }
    stages["STAGE_2"]["status"] = "READY"
    state = {
        "schema_version": SCHEMA_VERSION,
        "state_version": 1,
        "run_id": run_id,
        "report_date": context.get("report_date"),
        "production_date": context.get("production_date"),
        "trading_date": context.get("trading_date"),
        "main_commit_sha": context.get("main_commit_sha"),
        "workflow_run_id": str(context.get("workflow_run_id") or ""),
        "created_at": timestamp,
        "updated_at": timestamp,
        "current_stage": "STAGE_2",
        "last_passed_stage": "STAGE_1",
        "overall_status": "RUNNING",
        "stages": stages,
    }
    validate_state(state, expected_run_id=run_id)
    return state


def _derive(state: dict) -> None:
    stages = state["stages"]
    passed = [s for s in STAGES if stages[s]["status"] == "PASS"]
    state["last_passed_stage"] = passed[-1] if passed else None
    active = [s for s in STAGES if stages[s]["status"] in ACTIVE_STAGE]
    failed = [s for s in STAGES if stages[s]["status"] == "FAILED"]
    state["current_stage"] = active[0] if active else (failed[0] if failed else None)
    if stages["STAGE_6"]["status"] == "PASS":
        state["overall_status"] = "AWAITING_APPROVAL"
    elif any(stages[s]["status"] == "FAILED" for s in STAGES):
        state["overall_status"] = "FAILED"
    elif any(stages[s]["status"] == "PARTIAL" for s in STAGES):
        state["overall_status"] = "PARTIAL"
    else:
        state["overall_status"] = "RUNNING"


def _make_next_ready(state: dict, stage: str, status: str) -> None:
    next_map = {
        "STAGE_2": "STAGE_3",
        "STAGE_3": "STAGE_4",
        "STAGE_4": "STAGE_5",
        "STAGE_5": "STAGE_6",
    }
    next_stage = next_map.get(stage)
    if next_stage and status in {"PASS", "PARTIAL"}:
        if state["stages"][next_stage]["status"] == "NOT_STARTED":
            state["stages"][next_stage]["status"] = "READY"


def transition_state(
    current: dict,
    *,
    stage: str,
    expected_version: int,
    expected_status: str,
    new_status: str,
    now: str | None = None,
    input_sha256: str | None = None,
    output_sha256: str | None = None,
    receipt_path: str | None = None,
    error_code: str | None = None,
    lease_owner: str | None = None,
    lease_expires_at: str | None = None,
    recovery: bool = False,
) -> dict:
    """Return a new state if and only if version/status and transition are valid.

    Persistence must be compare-and-swap against the previously read blob SHA.
    Recovery from FAILED/PARTIAL is explicit and never rewinds a PASS stage.
    """
    validate_state(current)
    if stage not in STAGES:
        raise ValueError(f"Unknown stage: {stage}")
    if expected_version != current["state_version"]:
        raise ValueError("Stale state_version; reload state before transition")
    item = current["stages"][stage]
    if item["status"] != expected_status:
        raise ValueError(f"Expected {stage}={expected_status}, found {item['status']}")
    if new_status not in STAGE_STATUS:
        raise ValueError(f"Unknown stage status: {new_status}")
    allowed = set(_ALLOWED[expected_status])
    if recovery and expected_status in {"FAILED", "PARTIAL"}:
        allowed.add("READY")
    if new_status not in allowed:
        raise ValueError(f"Illegal stage transition: {stage} {expected_status} -> {new_status}")
    if new_status == "SUBMITTED" and stage not in {"STAGE_2", "STAGE_4"}:
        raise ValueError("Only ChatGPT-owned Stage 2 and Stage 4 may enter SUBMITTED")
    if new_status == "PARTIAL" and stage not in {"STAGE_2", "STAGE_5"}:
        raise ValueError("PARTIAL is only valid for Stage 2 market capture or Stage 5 QA")
    if new_status == "PASS" and not receipt_path and stage != "STAGE_1":
        raise ValueError(f"{stage} PASS requires a receipt_path")
    if new_status == "SUBMITTED" and not output_sha256:
        raise ValueError(f"{stage} SUBMITTED requires output_sha256")
    if new_status == "RUNNING" and not lease_owner:
        raise ValueError(f"{stage} RUNNING requires lease_owner")
    if new_status == "DEFERRED" and not error_code:
        raise ValueError(f"{stage} DEFERRED requires a concrete error_code")

    result = copy.deepcopy(current)
    target = result["stages"][stage]
    timestamp = now or utc_now()
    target["status"] = new_status
    if new_status == "RUNNING":
        target["attempt"] += 1
        target["started_at"] = timestamp
        target["completed_at"] = None
        target["lease_owner"] = lease_owner
        target["lease_expires_at"] = lease_expires_at
        target["error_code"] = None
    elif new_status in {"SUBMITTED", "PASS", "PARTIAL", "FAILED", "DEFERRED", "SKIPPED"}:
        target["completed_at"] = timestamp if new_status in TERMINAL_STAGE or new_status == "SUBMITTED" else None
        target["lease_owner"] = None
        target["lease_expires_at"] = None
        target["error_code"] = error_code
    if input_sha256 is not None:
        target["input_sha256"] = input_sha256
    if output_sha256 is not None:
        target["output_sha256"] = output_sha256
    if receipt_path is not None:
        target["receipt_path"] = receipt_path
    result["state_version"] += 1
    result["updated_at"] = timestamp
    _make_next_ready(result, stage, new_status)
    if stage == "STAGE_5" and new_status == "PARTIAL":
        result["stages"]["STAGE_6"]["status"] = "SKIPPED"
    _derive(result)
    validate_state(result, expected_run_id=current["run_id"])
    return result


def validate_state(state: dict, expected_run_id: str | None = None) -> None:
    if not isinstance(state, dict) or state.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported or missing run-state schema_version")
    if not isinstance(state.get("state_version"), int) or state["state_version"] < 1:
        raise ValueError("run-state state_version must be a positive integer")
    run_id = state.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise ValueError("run-state run_id is required")
    if expected_run_id and run_id != expected_run_id:
        raise ValueError("run-state run_id does not match expected Run")
    if state.get("overall_status") not in OVERALL_STATUS:
        raise ValueError("run-state overall_status is invalid")
    stages = state.get("stages")
    if not isinstance(stages, dict) or set(stages) != set(STAGES):
        raise ValueError("run-state must contain exactly six canonical stages")
    if stages["STAGE_1"]["status"] != "PASS":
        raise ValueError("Stage 1 must remain PASS for every initialized Run")
    partial_stages = [s for s in STAGES if stages[s]["status"] == "PARTIAL"]
    if any(s not in {"STAGE_2", "STAGE_5"} for s in partial_stages):
        raise ValueError("Only Stage 2 and Stage 5 may be PARTIAL")
    dependencies = {
        "STAGE_3": {"STAGE_2": {"PASS", "PARTIAL"}},
        "STAGE_4": {"STAGE_3": {"PASS"}},
        "STAGE_5": {"STAGE_4": {"PASS"}},
        "STAGE_6": {"STAGE_5": {"PASS"}},
    }
    for downstream, requirements in dependencies.items():
        downstream_status = stages[downstream]["status"]
        if downstream_status != "NOT_STARTED":
            for upstream, allowed_statuses in requirements.items():
                if stages[upstream]["status"] not in allowed_statuses:
                    raise ValueError(f"{downstream} cannot advance before {upstream} reaches {sorted(allowed_statuses)}")
    if stages["STAGE_5"]["status"] == "PARTIAL" and stages["STAGE_6"]["status"] != "SKIPPED":
        raise ValueError("Stage 5 PARTIAL must explicitly skip Stage 6")
    running = []
    for stage in STAGES:
        item = stages[stage]
        if not isinstance(item, dict) or item.get("status") not in STAGE_STATUS:
            raise ValueError(f"Invalid state entry for {stage}")
        if not isinstance(item.get("attempt"), int) or item["attempt"] < 0:
            raise ValueError(f"Invalid attempt count for {stage}")
        if item["status"] == "RUNNING":
            running.append(stage)
            if not item.get("lease_owner") or not item.get("lease_expires_at"):
                raise ValueError(f"{stage} RUNNING requires a lease owner and expiry")
        if item["status"] == "PASS" and stage != "STAGE_1" and not item.get("receipt_path"):
            raise ValueError(f"{stage} PASS requires a receipt path")
    if len(running) > 1:
        raise ValueError("Only one stage may be RUNNING for a Run at a time")
    if state.get("current_stage") not in set(STAGES) | {None}:
        raise ValueError("run-state current_stage is invalid")
    if state.get("last_passed_stage") not in set(STAGES) | {None}:
        raise ValueError("run-state last_passed_stage is invalid")
    expected_passed = [s for s in STAGES if stages[s]["status"] == "PASS"]
    if state.get("last_passed_stage") != (expected_passed[-1] if expected_passed else None):
        raise ValueError("run-state last_passed_stage does not match stage receipts")
