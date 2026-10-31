#!/usr/bin/env python3
"""Fail-closed authorization check for TAC market-data sources.

This tool checks permission declarations only. It does not fetch market data,
interpret legal terms, or grant permission. A source is usable for a requested
operation only when its registry record explicitly allows that operation and
has a documented evidence reference.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REQUIRED_PERMISSIONS = {
    "ingestion": ("automated_access", "numeric_quote_extraction"),
    "storage": ("storage",),
    "internal_display": ("internal_display",),
    "public_display": ("public_display", "redistribution"),
}


def load_registry(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read valid registry: {exc}") from exc
    if data.get("default_policy") != "deny" or not isinstance(data.get("sources"), list):
        raise ValueError("Registry must define default_policy=deny and a sources array.")
    return data


def authorize(registry: dict, source_id: str, operation: str) -> tuple[bool, list[str]]:
    source = next((s for s in registry["sources"] if s.get("source_id") == source_id), None)
    if source is None:
        return False, ["source is absent from registry (default deny)"]
    reasons = []
    if source.get("status") not in {"authorized", "limited_scope_authorized"}:
        reasons.append(f"source status is {source.get('status', 'missing')}")
    if not source.get("evidence_reference"):
        reasons.append("written authorization evidence reference is missing")
    for permission in REQUIRED_PERMISSIONS[operation]:
        if source.get("permissions", {}).get(permission) is not True:
            reasons.append(f"permission {permission}=true is not documented")
    return not reasons, reasons


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", default="data-sources/authorization-registry.json")
    parser.add_argument("--source", required=True, help="Registry source_id")
    parser.add_argument("--operation", choices=sorted(REQUIRED_PERMISSIONS), required=True)
    args = parser.parse_args()

    try:
        registry = load_registry(Path(args.registry))
    except ValueError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2

    allowed, reasons = authorize(registry, args.source, args.operation)
    if allowed:
        print(f"AUTHORIZED: {args.source} permits {args.operation} (registry declaration only).")
        return 0
    print(f"BLOCKED: {args.source} is not authorized for {args.operation}.")
    for reason in reasons:
        print(f"- {reason}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
