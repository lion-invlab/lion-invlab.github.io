#!/usr/bin/env python3
"""Exact-blob owner approval gate for the main production HTML Builder."""
from __future__ import annotations
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
APPROVAL_PATH=ROOT/"production/config/builder-approval.json"
BUILDER_PATH="production/runner/build_review_html.py"

def current_builder_blob_sha(root:Path=ROOT)->str:
    return subprocess.check_output(
        ["git","rev-parse",f"HEAD:{BUILDER_PATH}"],cwd=root,text=True
    ).strip()

def require_approved_builder(root:Path=ROOT, approval_path:Path=APPROVAL_PATH, actual_sha:str|None=None)->dict:
    if not approval_path.is_file():
        raise ValueError("Main Builder approval record is missing")
    approval=json.loads(approval_path.read_text(encoding="utf-8"))
    actual=actual_sha or current_builder_blob_sha(root)
    if approval.get("status")!="APPROVED_MAIN" or approval.get("approved_by_owner") is not True:
        raise ValueError("Main Builder is still a candidate pending explicit owner approval")
    if approval.get("builder_path")!=BUILDER_PATH or approval.get("builder_blob_sha")!=actual:
        raise ValueError("Main Builder approval does not match the exact current Builder blob SHA")
    return {"status":"APPROVED_MAIN","builder_path":BUILDER_PATH,"builder_blob_sha":actual,
            "approved_at":approval.get("approved_at")}
