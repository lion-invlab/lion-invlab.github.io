#!/usr/bin/env python3
"""Validate and extract an authenticated TAC snapshot handoff from issue #319."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

BEGIN = "<!-- TAC_MARKET_SNAPSHOT_V1_BEGIN -->"
END = "<!-- TAC_MARKET_SNAPSHOT_V1_END -->"
OWNER_ID = 335424146
ISSUE_NUMBER = 319
LOCK_FIELDS = ("wr_version", "wr_commit_sha", "wr_blob_sha", "wr_content_sha256")
DATA_GROUPS = {
    "global_indices", "sectors", "bonds", "fx", "energy",
    "precious_metals", "risk_indicators", "fedwatch",
}
FRAGMENT_FIELDS = {"report_date", "trading_date", "fetched_at", "dataset"} | DATA_GROUPS


def fail(message: str) -> None:
    raise ValueError(message)


def iso_date(value: object, field: str) -> str:
    if not isinstance(value, str):
        fail(f"{field} must be an ISO date string")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date string") from exc
    if parsed.isoformat() != value:
        fail(f"{field} must use YYYY-MM-DD")
    return value


def extract_payload(body: str) -> dict:
    if body.count(BEGIN) != 1 or body.count(END) != 1:
        fail("handoff must contain exactly one begin and end marker")
    start = body.index(BEGIN) + len(BEGIN)
    end = body.index(END)
    if end <= start:
        fail("handoff markers are out of order")
    raw = body[start:end].strip()
    if not raw:
        fail("handoff JSON is empty")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"handoff JSON is invalid: {exc}") from exc
    if not isinstance(payload, dict):
        fail("handoff payload must be a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", required=True)
    parser.add_argument("--lock", required=True)
    parser.add_argument("--fragment-out", required=True)
    parser.add_argument("--metadata-out", required=True)
    args = parser.parse_args()

    event = json.loads(Path(args.event).read_text(encoding="utf-8"))
    lock = json.loads(Path(args.lock).read_text(encoding="utf-8"))

    issue = event.get("issue") or {}
    comment = event.get("comment") or {}
    actor = comment.get("user") or {}
    if issue.get("number") != ISSUE_NUMBER or issue.get("pull_request"):
        fail("only ordinary issue #319 is an accepted handoff target")
    if actor.get("id") != OWNER_ID or actor.get("login") != "lion-invlab":
        fail("comment author is not the pinned repository owner identity")

    payload = extract_payload(comment.get("body") or "")
    required = {"schema_version", "report_date", "trading_date", "wr_lock", "fragment"}
    if set(payload) != required:
        fail("handoff payload must contain exactly: " + ", ".join(sorted(required)))
    if payload["schema_version"] != 1:
        fail("unsupported handoff schema_version")

    report_date = iso_date(payload["report_date"], "report_date")
    trading_date = iso_date(payload["trading_date"], "trading_date")
    if report_date != str(lock.get("locked_at_taipei", ""))[:10]:
        fail("report_date does not match the active WR lock's Taipei date")

    supplied_lock = payload["wr_lock"]
    if not isinstance(supplied_lock, dict) or set(supplied_lock) != set(LOCK_FIELDS):
        fail("wr_lock must contain exactly the four authoritative WR identity fields")
    active_lock = {key: lock.get(key) for key in LOCK_FIELDS}
    if supplied_lock != active_lock:
        fail("handoff WR identity does not match the active main-branch WR lock")

    fragment = payload["fragment"]
    if not isinstance(fragment, dict):
        fail("fragment must be a JSON object")
    unexpected = set(fragment) - FRAGMENT_FIELDS
    if unexpected:
        fail("fragment contains unsupported fields: " + ", ".join(sorted(unexpected)))
    if fragment.get("report_date") != report_date:
        fail("fragment report_date does not match handoff report_date")
    if fragment.get("trading_date") != trading_date:
        fail("fragment trading_date does not match handoff trading_date")
    if not (set(fragment) & DATA_GROUPS):
        fail("fragment contains no recognized TAC data group")

    for group in set(fragment) & DATA_GROUPS:
        if not isinstance(fragment[group], dict):
            fail(f"fragment group {group} must be an object")

    Path(args.fragment_out).write_text(
        json.dumps(fragment, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    Path(args.metadata_out).write_text(
        json.dumps({"report_date": report_date, "trading_date": trading_date},
                   ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Authenticated handoff: report_date={report_date}, trading_date={trading_date}")
    print("WR lock identity: PASS")
    print("Fragment envelope: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("REJECTED: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
