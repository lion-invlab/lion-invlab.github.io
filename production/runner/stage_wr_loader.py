#!/usr/bin/env python3
"""Load the complete Stage Work Rules before executing that Stage."""
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

def load_stage_wr(stage: str, context: dict | None = None, *, include_rules_text: bool = False) -> dict:
    """Read the full local WR; optionally return the instructions to the actual executor.

    wr_loaded alone only proves file I/O; it does NOT prove rule compliance.
    Callers executing human/LLM work must request include_rules_text=True and
    supply the returned rules_text as the operative instructions.
    """
    if stage not in STAGE_WR_PATHS:
        raise ValueError(f"Unknown Stage WR key: {stage}")
    path = STAGE_WR_PATHS[stage]
    file_path = ROOT / path
    if not file_path.is_file() or file_path.is_symlink():
        raise SystemExit(f"{stage}: required Work Rules file is missing: {path}")
    raw = file_path.read_bytes()
    if not raw:
        raise SystemExit(f"{stage}: Work Rules file is empty: {path}")
    try:
        full_text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SystemExit(f"{stage}: Work Rules file is not valid UTF-8: {path}") from exc
    if not full_text.strip():
        raise SystemExit(f"{stage}: Work Rules file contains no readable instructions: {path}")

    evidence = {
        "status": "PASS",
        "stage": stage,
        "wr_path": path,
        "wr_loaded": True,
        "wr_read_mode": "FULL_UTF8_FILE_READ",
        "wr_bytes_read": len(raw),
        "rules_text_loaded": True,
        # Return the actual instructions to the caller; a PASS flag alone is not execution guidance.
        "rules_text": full_text,
    }

    if include_rules_text:
        evidence["rules_text"] = full_text

    # Stage 1-4 must read their own instructions, then get on with the work.
    # No cross-stage SHA pin, receipt chain or worker attestation is a handoff gate.
    if stage in {"STAGE_1", "STAGE_2", "STAGE_3", "STAGE_4"}:
        return evidence

    evidence["wr_sha256"] = hashlib.sha256(raw).hexdigest()
    current_blob = _git_blob("HEAD", path)
    pinned_commit = None
    pinned_blob = current_blob
    if context is not None:
        pinned_commit = context.get("main_commit_sha")
        governance = context.get("governance") or {}
        pinned_map = governance.get("blob_shas")
        if not pinned_commit or governance.get("commit_sha") != pinned_commit:
            raise SystemExit(f"{stage}: delivery governance commit binding is missing")
        if not isinstance(pinned_map, dict) or path not in pinned_map:
            raise SystemExit(f"{stage}: Stage 1 did not pin {path}")
        pinned_blob = pinned_map[path]
        try:
            commit_blob = _git_blob(pinned_commit, path)
        except subprocess.CalledProcessError as exc:
            raise SystemExit(f"{stage}: WR absent from pinned Stage 1 commit: {path}") from exc
        if commit_blob != pinned_blob or current_blob != pinned_blob:
            raise SystemExit(f"{stage}: delivery WR differs from the Stage 1 pinned version: {path}")
    evidence.update({
        "status": "PASS",
        "wr_git_blob_sha": current_blob,
        "stage1_pinned_git_blob_sha": pinned_blob,
        "stage1_pinned_commit": pinned_commit,
    })
    return evidence

