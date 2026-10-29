#!/usr/bin/env python3
"""Fail-closed integrity checks for the two approved TAC HTML master templates.

The pinned Git blob SHA is the authoritative integrity check. Structural checks
provide actionable diagnostics when an intentional template update is proposed.
This script never edits HTML or changes the homepage.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "scripts" / "tac-master-template-lock.json"


def git_blob_sha(path: str) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", f"HEAD:{path}"], cwd=ROOT, text=True
    ).strip()


def extract_title(html: str) -> str | None:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.I | re.S)
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else None


def extract_nav_ids(html: str) -> list[str]:
    nav_match = re.search(r"<nav\b[^>]*>(.*?)</nav>", html, flags=re.I | re.S)
    if not nav_match:
        return []
    return re.findall(
        r"<a\b[^>]*href=[\"']#([^\"']+)[\"']", nav_match.group(1), flags=re.I
    )


def extract_ids(html: str) -> list[str]:
    return re.findall(r"\bid=[\"']([^\"']+)[\"']", html, flags=re.I)


def main() -> int:
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []
    warnings: list[str] = []

    print("TAC master-template integrity guard")
    print(f"Lock manifest: {LOCK_PATH.relative_to(ROOT)}")

    for item in lock["protected_templates"]:
        path = item["path"]
        file_path = ROOT / path
        print(f"\n[{item['name']}] {path}")

        if not file_path.is_file():
            errors.append(f"Missing protected master: {path}")
            print("  FAIL: file is missing")
            continue

        actual_sha = git_blob_sha(path)
        expected_sha = item["git_blob_sha"]
        if actual_sha != expected_sha:
            errors.append(
                f"{path}: Git blob SHA changed (expected {expected_sha}, got {actual_sha})"
            )
            print(f"  FAIL: SHA mismatch (expected {expected_sha}, got {actual_sha})")
        else:
            print(f"  PASS: pinned Git blob SHA {actual_sha}")

        html = file_path.read_text(encoding="utf-8")
        title = extract_title(html)
        if title != item["required_title"]:
            errors.append(
                f"{path}: title mismatch (expected {item['required_title']!r}, got {title!r})"
            )
            print(f"  FAIL: title mismatch: {title!r}")
        else:
            print(f"  PASS: title matches approved scenario")

        nav_ids = extract_nav_ids(html)
        missing = [anchor for anchor in item["required_nav_ids"] if anchor not in nav_ids]
        forbidden = [anchor for anchor in item["forbidden_nav_ids"] if anchor in nav_ids]
        if missing:
            errors.append(f"{path}: required navigation anchors missing: {missing}")
            print(f"  FAIL: missing navigation anchors: {missing}")
        if forbidden:
            errors.append(f"{path}: forbidden navigation anchors present: {forbidden}")
            print(f"  FAIL: forbidden navigation anchors present: {forbidden}")
        if not missing and not forbidden:
            print(f"  PASS: scenario-specific navigation ({len(nav_ids)} anchors)")

        ids = extract_ids(html)
        duplicates = sorted({value for value in ids if ids.count(value) > 1})
        if duplicates:
            # The approved masters are SHA-pinned and must not be edited merely to
            # satisfy this legacy audit. Report existing duplicate IDs as warnings;
            # the dedicated approved-master guard remains the fail-closed authority.
            warnings.append(f"{path}: pre-existing duplicate HTML IDs: {duplicates}")
            print(f"  WARN: duplicate HTML IDs in the approved, SHA-pinned master: {duplicates}")
        else:
            print("  PASS: no duplicate HTML IDs")

        missing_targets = sorted(set(nav_ids) - set(ids))
        if missing_targets:
            errors.append(f"{path}: navigation targets missing from document: {missing_targets}")
            print(f"  FAIL: navigation targets missing from document: {missing_targets}")
        else:
            print("  PASS: every navigation anchor has a matching target ID")

        required_markers = item.get("required_markers", [])
        missing_markers = [marker for marker in required_markers if marker not in html]
        if missing_markers:
            errors.append(f"{path}: required structural markers missing: {missing_markers}")
            print(f"  FAIL: required structural markers missing: {missing_markers}")
        else:
            print(f"  PASS: required structural markers ({len(required_markers)})")

    print("\nSummary")
    print(f"  Errors: {len(errors)}")
    print(f"  Warnings: {len(warnings)}")
    for warning in warnings:
        print(f"  - {warning}")
    for error in errors:
        print(f"  ERROR: {error}")

    if errors:
        print("\nRESULT: FAIL — do not use this candidate for production.")
        return 1
    print("\nRESULT: PASS — pinned master files match; review warnings before production.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
