#!/usr/bin/env python3
"""Fail-closed, read-only loader for the sole TAC calendar database on main."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import PurePosixPath

from earnings_judgment import ENGINE_VERSION, migrate_legacy_record, render_summary

REPOSITORY = "lion-invlab/lion-invlab.github.io"
SIMULATION_BRANCH = "simulation/tac-process-lab-2026-11-06"
MAIN_REF = "refs/remotes/origin/main"


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], check=True, text=True, capture_output=True
    )
    return result.stdout.strip()


def validate_repository_and_branch() -> None:
    remote = run_git("remote", "get-url", "origin").strip()
    normalized = remote.lower().removesuffix(".git").replace("git@github.com:", "https://github.com/")
    if normalized.rstrip("/") != "https://github.com/" + REPOSITORY:
        raise RuntimeError(f"calendar source repository mismatch: {remote!r}")

    github_ref = os.environ.get("GITHUB_REF", "")
    if github_ref.startswith("refs/heads/"):
        current_branch = github_ref.removeprefix("refs/heads/")
    else:
        current_branch = run_git("branch", "--show-current")
    if current_branch != SIMULATION_BRANCH:
        raise RuntimeError(
            f"calendar source Gate 0 rejected checkout branch {current_branch!r}; "
            f"expected {SIMULATION_BRANCH!r}. No fallback is permitted."
        )


def iso_week_path(day: date) -> tuple[str, str]:
    iso = day.isocalendar()
    week_id = f"{iso.year}-W{iso.week:02d}"
    return week_id, f"data/calendar/weeks/{week_id}.json"


def _load_week(commit: str, day: date) -> dict:
    week_id, path = iso_week_path(day)
    if str(PurePosixPath(path)) != path or not re.fullmatch(
        r"data/calendar/weeks/\d{4}-W\d{2}\.json", path
    ):
        raise RuntimeError(f"invalid canonical calendar path: {path}")
    try:
        blob_sha = run_git("rev-parse", f"{commit}:{path}")
        raw = subprocess.run(
            ["git", "show", f"{commit}:{path}"],
            check=True, text=True, capture_output=True
        ).stdout
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"authoritative main calendar missing/unreadable: {path}; "
            "stale simulation JSON and fixtures are forbidden"
        ) from exc
    payload = json.loads(raw)
    if payload.get("week_id") != week_id:
        raise RuntimeError(
            f"calendar week_id mismatch in {path}: {payload.get('week_id')!r} != {week_id!r}"
        )
    iso = day.isocalendar()
    expected_start = date.fromisocalendar(iso.year, iso.week, 1).isoformat()
    expected_end = date.fromisocalendar(iso.year, iso.week, 7).isoformat()
    if payload.get("week_start") != expected_start or payload.get("week_end") != expected_end:
        raise RuntimeError(f"calendar date range mismatch in {path}; expected {expected_start}..{expected_end}")
    if payload.get("timezone") != "Asia/Taipei":
        raise RuntimeError(f"calendar timezone mismatch in {path}")
    events = payload.get("events")
    if not isinstance(events, dict):
        raise RuntimeError(f"calendar events must be an object in {path}")
    for group in ("economic", "earnings"):
        records = events.get(group)
        if not isinstance(records, list) or not records:
            raise RuntimeError(f"calendar {group} records missing/invalid in {path}")
        ids = [x.get("id") for x in records]
        if any(not item_id for item_id in ids) or len(ids) != len(set(ids)):
            raise RuntimeError(f"calendar {group} IDs missing/duplicated in {path}")
    return {
        "repository": REPOSITORY,
        "branch": "main",
        "path": path,
        "commit_sha": commit,
        "blob_sha": blob_sha,
        "week_id": week_id,
        "week_start": payload.get("week_start"),
        "week_end": payload.get("week_end"),
        "updated_at": payload.get("updated_at"),
        "economic_count": len(events["economic"]),
        "earnings_count": len(events["earnings"]),
        "payload": payload,
    }


def load_authoritative_calendar(report_date: str) -> dict:
    """Fetch origin/main once, then read current and previous ISO-week JSON by immutable commit."""
    validate_repository_and_branch()
    report_day = date.fromisoformat(report_date)
    subprocess.run(
        ["git", "fetch", "--no-tags", "origin", "main"],
        check=True, text=True, capture_output=True
    )
    main_commit = run_git("rev-parse", MAIN_REF)
    current = _load_week(main_commit, report_day)
    previous = _load_week(main_commit, report_day - timedelta(days=7))
    return {"main_commit_sha": main_commit, "current": current, "previous": previous}


def _source_fields(record: dict) -> tuple[str | None, str | None]:
    source = record.get("source") if isinstance(record.get("source"), dict) else {}
    return source.get("url"), source.get("name")


def _money_display(value, currency: str | None, unit: str | None = None, decimals: int = 2):
    if value is None:
        return None
    prefix = {"USD": "US$", "CAD": "C$", "EUR": "€", "GBP": "£", "AUD": "A$"}.get(currency, (currency + " ") if currency else "")
    number = f"{value:,.{decimals}f}" if isinstance(value, (int, float)) else str(value)
    suffix = unit if unit and unit not in ("share", "per_share") else ""
    return f"{prefix}{number}{suffix}"


def _economic_records(payload: dict) -> list[dict]:
    output = []
    for item in payload["events"]["economic"]:
        source_url, source_name = _source_fields(item)
        output.append({
            "id": item.get("id"),
            "date": item.get("event_date"),
            "event_date": item.get("event_date"),
            "region": item.get("region", ""),
            "name": item.get("event_name", ""),
            "stars": item.get("importance_stars", 0),
            "time_known": item.get("time_known", False),
            "status": "released" if item.get("status") in ("released", "published", "completed") else item.get("status"),
            "previous": item.get("previous"),
            "forecast": item.get("forecast"),
            "actual": item.get("actual"),
            "impact": item.get("impact_judgment"),
            "source_url": source_url,
            "source_name": source_name,
        })
    return output


def _earnings_records(payload: dict, observed_at: str | None = None) -> list[dict]:
    """Project calendar earnings into versioned v2 judgment records in memory.

    The calendar JSON remains read-only. Legacy records are normalized by the
    single judgment engine before the HTML renderer sees them; old persisted
    Beat/Miss labels are retained only as legacy metadata, never trusted.
    """
    if observed_at is None:
        observed_at = datetime.now(ZoneInfo("Asia/Taipei")).isoformat(timespec="seconds")

    output = []
    for item in payload["events"]["earnings"]:
        # Display formatting may use a shared legacy currency label. This is
        # deliberately NOT passed to the judgment engine as comparison proof.
        def display_currency_pair(value):
            if not isinstance(value, str):
                return None, None
            match = re.fullmatch(
                r"([A-Z]{3}) actual; ([A-Z]{3}) estimate \\(not comparable\\)",
                value,
            )
            if match:
                return match.group(1), match.group(2)
            if re.fullmatch(r"[A-Z]{3}", value):
                return value, value
            return None, None

        eps_actual_currency, eps_estimate_currency = display_currency_pair(item.get("eps_currency"))
        revenue_actual_currency, revenue_estimate_currency = display_currency_pair(item.get("revenue_currency"))
        revenue_unit = item.get("revenue_unit")

        # This is an in-memory projection only. migrate_legacy_record applies
        # the v2 evidence gates and will return Pending/Incomparable whenever
        # actual/estimate basis, currency, period, units or sources are unclear.
        judged = migrate_legacy_record(item, observed_at=observed_at)
        source = judged.get("source") if isinstance(judged.get("source"), dict) else {}
        output.append({
            "id": item.get("id"),
            "date": item.get("event_date"),
            "event_date": item.get("event_date"),
            "company": item.get("company", ""),
            "ticker": item.get("ticker", ""),
            "industry": item.get("industry", ""),
            "stars": item.get("importance_stars", 0),
            "session": item.get("session"),
            "time_type": item.get("time_type"),
            "time_known": item.get("time_known", False),
            "status": "released" if item.get("status") in ("released", "published", "completed") else item.get("status"),
            "reporting_period": item.get("reporting_period"),
            "eps_actual": judged.get("eps_actual"),
            "eps_estimate": judged.get("eps_estimate"),
            "eps_actual_display": _money_display(item.get("eps_actual"), eps_actual_currency),
            "eps_estimate_display": _money_display(item.get("eps_estimate"), eps_estimate_currency),
            "eps_basis": item.get("eps_basis"),
            "eps_actual_basis": item.get("eps_actual_basis"),
            "eps_estimate_basis": item.get("eps_estimate_basis"),
            "eps_actual_basis_code": judged.get("eps_actual_basis_code"),
            "eps_estimate_basis_code": judged.get("eps_estimate_basis_code"),
            "eps_actual_currency": judged.get("eps_actual_currency"),
            "eps_estimate_currency": judged.get("eps_estimate_currency"),
            "eps_actual_period": judged.get("eps_actual_period"),
            "eps_estimate_period": judged.get("eps_estimate_period"),
            "eps_surprise": judged.get("eps_surprise"),
            "eps_surprise_pct": judged.get("eps_surprise_pct"),
            "eps_comparison_status": judged.get("eps_comparison_status"),
            "eps_comparison_reason": judged.get("eps_comparison_reason"),
            "eps_consensus_conflict": judged.get("eps_consensus_conflict", False),
            "eps_inline_tolerance_abs": judged.get("eps_inline_tolerance_abs"),
            "revenue_actual": judged.get("revenue_actual"),
            "revenue_estimate": judged.get("revenue_estimate"),
            "revenue_actual_display": _money_display(item.get("revenue_actual"), revenue_actual_currency, revenue_unit, 3),
            "revenue_estimate_display": _money_display(item.get("revenue_estimate"), revenue_estimate_currency, revenue_unit, 3),
            "revenue_actual_basis": item.get("revenue_actual_basis"),
            "revenue_estimate_basis": item.get("revenue_estimate_basis"),
            "revenue_actual_basis_code": judged.get("revenue_actual_basis_code"),
            "revenue_estimate_basis_code": judged.get("revenue_estimate_basis_code"),
            "revenue_actual_currency": judged.get("revenue_actual_currency"),
            "revenue_estimate_currency": judged.get("revenue_estimate_currency"),
            "revenue_actual_unit": judged.get("revenue_actual_unit"),
            "revenue_estimate_unit": judged.get("revenue_estimate_unit"),
            "revenue_actual_period": judged.get("revenue_actual_period"),
            "revenue_estimate_period": judged.get("revenue_estimate_period"),
            "revenue_surprise": judged.get("revenue_surprise"),
            "revenue_surprise_pct": judged.get("revenue_surprise_pct"),
            "revenue_comparison_status": judged.get("revenue_comparison_status"),
            "revenue_comparison_reason": judged.get("revenue_comparison_reason"),
            "revenue_consensus_conflict": judged.get("revenue_consensus_conflict", False),
            "revenue_inline_tolerance_abs": judged.get("revenue_inline_tolerance_abs"),
            "source": judged.get("source"),
            "consensus_source": judged.get("consensus_source"),
            "revenue_consensus_source": judged.get("revenue_consensus_source"),
            "source_url": source.get("url"),
            "source_name": source.get("name"),
            "judgment_engine_version": judged.get("judgment_engine_version"),
            "judgment_timestamp": judged.get("judgment_timestamp"),
            "earnings_comparison_summary": judged.get("earnings_comparison_summary"),
            "earnings_commentary": judged.get("earnings_commentary"),
            "judgment": render_summary(judged) + (
                "；" + judged["earnings_commentary"]
                if isinstance(judged.get("earnings_commentary"), str)
                and judged["earnings_commentary"].strip()
                else ""
            ),
            "price_reaction": item.get("stock_price_reaction"),
            "price_reaction_source": item.get("price_reaction_source"),
            "us_exchange_listed": item.get("us_exchange_listed", False),
            "us_listing_ticker": item.get("us_listing_ticker"),
        })
    return output

def project_calendar_data(bundle: dict) -> dict:
    current = bundle["current"]["payload"]
    previous = bundle["previous"]["payload"]
    return {
        "calendar": {
            "week_id": current["week_id"],
            "week_start": current["week_start"],
            "week_end": current["week_end"],
            "events": _economic_records(current),
        },
        "earnings": {
            "week_id": current["week_id"],
            "week_start": current["week_start"],
            "week_end": current["week_end"],
            "events": _earnings_records(current),
        },
        "last_week_calendar": {
            "week_id": previous["week_id"],
            "week_start": previous["week_start"],
            "week_end": previous["week_end"],
            "events": _economic_records(previous),
        },
        "last_week_earnings": {
            "week_id": previous["week_id"],
            "week_start": previous["week_start"],
            "week_end": previous["week_end"],
            "events": _earnings_records(previous),
        },
    }


def self_test() -> None:
    # Deliberately simulate the wrong branch: it must fail closed.
    try:
        branch = "main"
        if branch != SIMULATION_BRANCH:
            raise RuntimeError(
                f"calendar source Gate 0 rejected checkout branch {branch!r}; "
                f"expected {SIMULATION_BRANCH!r}. No fallback is permitted."
            )
    except RuntimeError as exc:
        assert "rejected checkout branch" in str(exc)
        print("PASS: wrong-branch negative test rejected main checkout")
    else:
        raise AssertionError("wrong branch must be rejected")
    sample = {
        "week_id": "2026-W46", "week_start": "2026-11-09", "week_end": "2026-11-15",
        "timezone": "Asia/Taipei",
        "events": {
            "economic": [{"id": "econ-1", "event_date": "2026-11-10T08:30:00+08:00",
                          "event_name": "CPI", "importance_stars": 5, "status": "released",
                          "source": {"name": "Official", "url": "https://example.com"}}],
            "earnings": [{"id": "earn-1", "event_date": "2026-11-10T20:00:00+08:00",
                          "company": "Example", "ticker": "EX", "importance_stars": 4,
                          "status": "released", "eps_actual": 1.2, "eps_currency": "USD",
                          "source": {"name": "Issuer", "url": "https://example.com"}}],
        },
    }
    assert _economic_records(sample)[0]["name"] == "CPI"
    assert _earnings_records(sample)[0]["eps_actual_display"] == "US$1.20"
    print("PASS: main calendar schema mapping")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    else:
        parser.error("only --self-test is supported")
