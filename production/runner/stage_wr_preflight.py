#!/usr/bin/env python3
"""Mandatory per-stage Work Rules preflight.

Every stage runner must call stage_wr_preflight before doing stage work.
The full WR is read as UTF-8, its Git blob is checked against the Stage 1
pinned governance snapshot, and an auditable SHA-256 evidence object is returned.
"""
from __future__ import annotations
import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGE_WR_PATHS = {
    "STAGE_1": "production/stages/STAGE_1_CONTEXT.md",
    "STAGE_2": "production/stages/STAGE_2_MARKET.md",
    "STAGE_3": "production/stages/STAGE_3_CALENDAR.md",
    "STAGE_4": "production/stages/STAGE_4_NEWS_ANALYSIS.md",
    "STAGE_5": "production/stages/STAGE_5_RENDER_QA.md",
    "STAGE_6": "production/stages/STAGE_6_DELIVERY.md",
}

def _git_blob(ref: str, path: str) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", f"{ref}:{path}"], cwd=ROOT, text=True,
        stderr=subprocess.STDOUT
    ).strip()

def stage_wr_preflight(stage: str, context: dict | None = None) -> dict:
    """Read the complete stage WR and fail closed on missing, empty or drifted rules."""
    if stage not in STAGE_WR_PATHS:
        raise ValueError(f"Unknown Stage WR key: {stage}")
    path = STAGE_WR_PATHS[stage]
    file_path = ROOT / path
    if not file_path.is_file() or file_path.is_symlink():
        raise SystemExit(f"{stage} preflight blocked: required WR missing or symlinked: {path}")
    raw = file_path.read_bytes()
    if not raw:
        raise SystemExit(f"{stage} preflight blocked: WR is empty: {path}")
    try:
        full_text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SystemExit(f"{stage} preflight blocked: WR is not valid UTF-8: {path}") from exc
    if not full_text.strip():
        raise SystemExit(f"{stage} preflight blocked: WR contains no readable rules: {path}")

    current_blob = _git_blob("HEAD", path)
    pinned_commit = None
    pinned_blob = current_blob
    if context is not None:
        pinned_commit = context.get("main_commit_sha")
        governance = context.get("governance") or {}
        if not pinned_commit or governance.get("commit_sha") != pinned_commit:
            raise SystemExit(f"{stage} preflight blocked: Stage 1 governance commit binding is missing")
        pinned_map = governance.get("blob_shas")
        if not isinstance(pinned_map, dict) or path not in pinned_map:
            raise SystemExit(f"{stage} preflight blocked: Stage 1 did not pin {path}")
        pinned_blob = pinned_map[path]
        try:
            commit_blob = _git_blob(pinned_commit, path)
        except subprocess.CalledProcessError as exc:
            raise SystemExit(f"{stage} preflight blocked: WR absent from pinned Stage 1 commit: {path}") from exc
        if commit_blob != pinned_blob:
            raise SystemExit(f"{stage} preflight blocked: pinned WR SHA evidence is inconsistent: {path}")
        if current_blob != pinned_blob:
            raise SystemExit(f"{stage} preflight blocked: current WR differs from Stage 1 pinned version: {path}")

    return {
        "status": "PASS",
        "stage": stage,
        "wr_path": path,
        "wr_loaded": True,
        "wr_read_mode": "FULL_UTF8_FILE_READ",
        "wr_bytes_read": len(raw),
        "wr_sha256": hashlib.sha256(raw).hexdigest(),
        "wr_git_blob_sha": current_blob,
        "stage1_pinned_git_blob_sha": pinned_blob,
        "stage1_pinned_commit": pinned_commit,
        "rules_text_loaded": bool(full_text.strip()),
    }

def require_stage_wr_receipt(receipt: dict, expected_stage: str, context: dict) -> dict:
    """Reject a handoff unless its producer proved the exact Stage 1-pinned WR."""
    evidence = receipt.get("wr_preflight") if isinstance(receipt, dict) else None
    if not isinstance(evidence, dict):
        raise SystemExit(f"{expected_stage} handoff blocked: producer WR preflight evidence is missing")
    path = STAGE_WR_PATHS.get(expected_stage)
    governance = context.get("governance") or {}
    pinned_map = governance.get("blob_shas") or {}
    pinned_commit = context.get("main_commit_sha")
    pinned_blob = pinned_map.get(path) if path else None
    sha256_value = evidence.get("wr_sha256")
    if (evidence.get("status") != "PASS"
            or evidence.get("stage") != expected_stage
            or evidence.get("wr_loaded") is not True
            or evidence.get("rules_text_loaded") is not True
            or evidence.get("wr_path") != path
            or not isinstance(sha256_value, str) or len(sha256_value) != 64
            or evidence.get("wr_git_blob_sha") != pinned_blob
            or evidence.get("stage1_pinned_git_blob_sha") != pinned_blob
            or evidence.get("stage1_pinned_commit") != pinned_commit
            or not pinned_blob or not pinned_commit):
        raise SystemExit(f"{expected_stage} handoff blocked: producer WR evidence is incomplete or differs from Stage 1 governance pin")
    if expected_stage == "STAGE_2":
        worker = receipt.get("worker_wr_attestation") or {}
        if worker.get("status") != "PASS" or worker.get("stage2_wr_sha256") != evidence.get("wr_sha256"):
            raise SystemExit("STAGE_2 handoff blocked: ChatGPT worker WR attestation is missing or mismatched")
    if expected_stage == "STAGE_4":
        worker = receipt.get("editorial_worker_wr_attestation") or {}
        if worker.get("status") != "PASS" or worker.get("stage4_wr_sha256") != evidence.get("wr_sha256"):
            raise SystemExit("STAGE_4 handoff blocked: editorial worker WR attestation is missing or mismatched")
    return evidence
