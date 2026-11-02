#!/usr/bin/env python3
"""Resolve and record the exact TAC Work Rules revision used by one pipeline run."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_RE = re.compile(r"^版本：([0-9]+\.[0-9]+)", re.MULTILINE)


def parse_wr_version(content: str) -> str:
    match = VERSION_RE.search(content)
    if not match:
        raise ValueError("TAC_WORK_RULES.md has no valid leading version declaration")
    return match.group(1)


def resolve_git_lock(ref: str) -> dict:
    commit = subprocess.run(
        ["git", "rev-parse", "--verify", f"{ref}^{{commit}}"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout.strip()
    content = subprocess.run(
        ["git", "show", f"{ref}:TAC_WORK_RULES.md"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout
    blob = subprocess.run(
        ["git", "rev-parse", f"{ref}:TAC_WORK_RULES.md"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout.strip()
    return {
        "schema_version": 1,
        "wr_version": parse_wr_version(content),
        "wr_commit_sha": commit,
        "wr_blob_sha": blob,
        "wr_content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "source_ref": ref,
        "locked_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def self_test() -> None:
    sample = "# TAC\n\n版本：4.3（2026-11-02｜測試）\n"
    assert parse_wr_version(sample) == "4.3"
    try:
        parse_wr_version("# no version")
    except ValueError:
        pass
    else:
        raise AssertionError("missing WR version must fail closed")
    print("PASS: WR version parser and fail-closed behavior")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref", default="HEAD", help="Git ref containing the authoritative WR")
    parser.add_argument("--output", help="Optional JSON lock-record output path")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    try:
        lock = resolve_git_lock(args.ref)
        if args.output:
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WR_VERSION={lock['wr_version']}")
        print(f"WR_COMMIT_SHA={lock['wr_commit_sha']}")
        print(f"WR_BLOB_SHA={lock['wr_blob_sha']}")
        print(f"WR_CONTENT_SHA256={lock['wr_content_sha256']}")
        print(f"WR_SOURCE_REF={lock['source_ref']}")
        return 0
    except Exception as exc:
        print(f"FAIL: cannot resolve authoritative TAC_WORK_RULES.md: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
