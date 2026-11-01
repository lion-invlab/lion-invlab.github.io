#!/usr/bin/env python3
"""Compose market and calendar snapshots into one renderer input.

The market snapshot is already schema-validated by assemble_tac_daily_snapshot.py.
The calendar snapshot is validated by assemble_tac_calendar_snapshot.py. This
step only combines non-overlapping top-level contracts and never edits inputs.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MARKET_KEYS = {
    "schema_version", "meta", "global_indices", "sectors", "bonds", "fx",
    "energy", "precious_metals", "risk_indicators", "fedwatch",
}
CALENDAR_KEYS = {"economic_calendar", "earnings_calendar"}


def load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"{label}: unable to read JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label}: JSON root must be an object")
    return value


def compose(market: dict[str, Any], calendar: dict[str, Any],
            extra_fragments: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    missing = MARKET_KEYS - set(market)
    if missing:
        raise ValueError(f"market snapshot missing required keys: {sorted(missing)}")
    if set(calendar) != CALENDAR_KEYS:
        raise ValueError(
            "calendar snapshot must contain exactly economic_calendar and earnings_calendar"
        )
    for group in sorted(CALENDAR_KEYS):
        value = calendar[group]
        if not isinstance(value, dict) or set(value) != {"panels"} or not isinstance(value["panels"], dict):
            raise ValueError(f"{group}: panels object required")
    overlap = set(market) & set(calendar)
    if overlap:
        raise ValueError(f"market/calendar key collision: {sorted(overlap)}")
    combined = dict(market)
    combined.update(calendar)
    for index, fragment in enumerate(extra_fragments or []):
        if not isinstance(fragment, dict) or not fragment:
            raise ValueError(f"extra fragment {index}: non-empty object required")
        collision = set(combined) & set(fragment)
        if collision:
            raise ValueError(f"extra fragment {index}: top-level key collision: {sorted(collision)}")
        combined.update(fragment)
    return combined


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--market-snapshot", required=True)
    ap.add_argument("--calendar-snapshot", required=True)
    ap.add_argument("--fragment", action="append", default=[])
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    try:
        market_path = (ROOT / args.market_snapshot).resolve()
        calendar_path = (ROOT / args.calendar_snapshot).resolve()
        output_path = (ROOT / args.output).resolve()
        protected = {
            (ROOT / "index.html").resolve(),
            (ROOT / "TAC_WORK_RULES.md").resolve(),
            (ROOT / "母版專區/TAC_母版_週一_2026-10-28_最終定版.html").resolve(),
            (ROOT / "母版專區/TAC_母版_週二至週五_2026-10-28_最終定版.html").resolve(),
        }
        if output_path in protected or output_path in {market_path, calendar_path}:
            raise ValueError("refusing to overwrite a protected file or input snapshot")
        market = load_object(market_path, "market snapshot")
        calendar = load_object(calendar_path, "calendar snapshot")
        fragments = [load_object((ROOT / path).resolve(), f"fragment {path}") for path in args.fragment]
        combined = compose(market, calendar, fragments)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(combined, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            "PASS: composed renderer snapshot with "
            + ", ".join(sorted(CALENDAR_KEYS))
            + f"; {len(args.fragment)} optional content fragment(s)"
        )
        return 0
    except Exception as exc:
        print(f"SNAPSHOT COMPOSITION BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
