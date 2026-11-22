#!/usr/bin/env python3
"""Resolve SIM-1.4 Builder approval from the active rule and verify the exact bytes."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path


APPROVAL_RE = re.compile(
    r"本版唯一正式 Builder 已核准：\*\*\s*`([^`]+)`，blob SHA `([0-9a-f]{40})`"
)


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def resolve_builder_approval(
    active_rules_text: str,
    active_rules_bytes: bytes,
    builder_path: str,
    builder_bytes: bytes,
) -> dict:
    """Return NOT_APPROVED only when no approval clause exists; mismatches fail closed."""
    match = APPROVAL_RE.search(active_rules_text)
    actual_builder_sha = git_blob_sha(builder_bytes)
    rules_sha = git_blob_sha(active_rules_bytes)
    if not match:
        return {
            "decision": "NOT_APPROVED",
            "approved_builder_path": None,
            "approved_builder_blob_sha": None,
            "actual_builder_path": builder_path,
            "actual_builder_blob_sha": actual_builder_sha,
            "active_rules_blob_sha": rules_sha,
            "approval_basis": None,
        }

    approved_path, approved_sha = match.groups()
    if builder_path != approved_path:
        raise ValueError(
            f"Builder path differs from active SIM-1.4 approval: {builder_path!r} != {approved_path!r}"
        )
    if actual_builder_sha != approved_sha:
        raise ValueError(
            f"Builder bytes differ from active SIM-1.4 approval: {actual_builder_sha} != {approved_sha}"
        )
    return {
        "decision": "APPROVED",
        "approved_builder_path": approved_path,
        "approved_builder_blob_sha": approved_sha,
        "actual_builder_path": builder_path,
        "actual_builder_blob_sha": actual_builder_sha,
        "active_rules_blob_sha": rules_sha,
        "approval_basis": "Exact path and Git blob SHA matched the active SIM-1.4 §8.1 approval clause",
    }


def resolve_from_files(active_rules_path: str, builder_path: str) -> dict:
    rules_bytes = Path(active_rules_path).read_bytes()
    builder_bytes = Path(builder_path).read_bytes()
    return resolve_builder_approval(
        rules_bytes.decode("utf-8"), rules_bytes, builder_path, builder_bytes
    )
