#!/usr/bin/env python3
"""Fail-closed TAC daily preview orchestrator.

This command assembles already captured, provenance-bearing market fragments,
the weekly calendar database, and required editorial content. It renders only
a review HTML file. It never fetches quotes, edits mothers/WR, or deploys index.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from adapt_tac_market_snapshot_for_renderer import adapt_market_snapshot
from assemble_tac_calendar_snapshot import build_calendar_snapshot
from assemble_tac_daily_snapshot import assemble
from compose_tac_daily_snapshot import compose, load_object
from render_tac_market_safe import render_market_html
from validate_tac_daily_snapshot import load_validator

MANIFEST_PATH = ROOT / "母版專區/mother-template-manifest.json"
BINDING_PATH = ROOT / "scripts/tac_html_binding_map.json"
SCHEMA_PATH = ROOT / "schemas/tac-daily-market-snapshot.schema.json"

def iso_week_path(day: date) -> Path:
    year, week, _ = day.isocalendar()
    return ROOT / "data/calendar/weeks" / f"{year}-W{week:02d}.json"

def scenario_for(day: date) -> str:
    if day.weekday() == 0:
        return "monday"
    if 1 <= day.weekday() <= 4:
        return "weekdays"
    raise ValueError("TAC daily report is allowed only Monday through Friday")

def run_guard(script: str) -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script)],
        cwd=ROOT, text=True, capture_output=True
    )
    if result.returncode:
        raise ValueError(f"{script} failed:\n{result.stdout}\n{result.stderr}")
    if result.stdout.strip():
        print(result.stdout.strip())

def select_approved_template(report_day: date, manifest: dict, binding: dict) -> tuple[str, Path]:
    scenario = scenario_for(report_day)
    item = manifest.get("templates", {}).get(scenario)
    if not isinstance(item, dict) or not item.get("path") or not item.get("blob_sha"):
        raise ValueError(f"Manifest has no approved {scenario} template")
    path = ROOT / item["path"]
    if not path.is_file():
        raise ValueError(f"approved {scenario} template is missing: {item['path']}")
    expected_binding = binding.get("templates", {}).get(scenario)
    if expected_binding != item["path"]:
        raise ValueError(f"Binding Map {scenario} template differs from Manifest")
    actual_sha = subprocess.check_output(
        ["git", "rev-parse", f"HEAD:{item['path']}"], cwd=ROOT, text=True
    ).strip()
    if actual_sha != item["blob_sha"]:
        raise ValueError(f"Manifest SHA mismatch for {scenario}: expected {item['blob_sha']}, got {actual_sha}")
    return scenario, path

def validate_content_fragments(fragments: list[dict]) -> dict:
    merged = {}
    for index, fragment in enumerate(fragments):
        if not isinstance(fragment, dict) or not fragment:
            raise ValueError(f"content fragment {index} must be a non-empty object")
        collision = set(merged) & set(fragment)
        if collision:
            raise ValueError(f"content fragment key collision: {sorted(collision)}")
        merged.update(fragment)
    if set(merged) != {"news", "editorial"}:
        raise ValueError("content fragments must provide exactly news and editorial; stale mother-template copy is not allowed")
    news = merged["news"]
    if not isinstance(news, dict) or set(news) != {"global_focus", "market_headlines"}:
        raise ValueError("news must contain exactly global_focus and market_headlines")
    for key, expected_count in (("global_focus", 5), ("market_headlines", 10)):
        panel = news[key]
        if not isinstance(panel, dict) or not isinstance(panel.get("items"), list):
            raise ValueError(f"news.{key}: items array missing")
        if len(panel["items"]) != expected_count:
            raise ValueError(f"news.{key}: WR requires exactly {expected_count} items, got {len(panel['items'])}")
    editorial = merged["editorial"]
    required_editorial = {"headline", "body_segments", "market_text", "levels_segments", "core_text"}
    if not isinstance(editorial, dict) or set(editorial) != required_editorial:
        raise ValueError("editorial fragment does not match the five required renderer fields")
    return merged

def build_preview(report_date: str, trading_date: str, market_fragments: list[Path],
                  content_fragments: list[Path], output: Path,
                  generated_at: str | None = None,
                  fedwatch_renderer_path: Path | None = None) -> Path:
    report_day = date.fromisoformat(report_date)
    trading_day = date.fromisoformat(trading_date)
    scenario = scenario_for(report_day)
    if not market_fragments:
        raise ValueError("at least one validated market fragment is required")
    if not content_fragments:
        raise ValueError("news and editorial fragments are required; refusing to reuse stale mother content")

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    binding = json.loads(BINDING_PATH.read_text(encoding="utf-8"))
    _scenario, template_path = select_approved_template(report_day, manifest, binding)
    run_guard("verify_tac_master_templates.py")
    run_guard("validate_tac_html_binding.py")

    current_path = iso_week_path(report_day)
    if not current_path.is_file():
        raise ValueError(f"current ISO-week calendar database missing: {current_path.relative_to(ROOT)}")
    current_week = load_object(current_path, "current week calendar")
    previous_week = None
    if scenario == "monday":
        previous_path = iso_week_path(report_day - timedelta(days=7))
        if not previous_path.is_file():
            raise ValueError(f"previous ISO-week calendar database missing: {previous_path.relative_to(ROOT)}")
        previous_week = load_object(previous_path, "previous week calendar")

    validator, schema = load_validator()
    market_data = [load_object(path, f"market fragment {path}") for path in market_fragments]
    generated_at = generated_at or datetime.now(ZoneInfo("Asia/Taipei")).isoformat()
    normalized_market = assemble(report_day.isoformat(), trading_day.isoformat(),
                                 generated_at, market_data, validator, schema)

    renderer_fedwatch = None
    if fedwatch_renderer_path is not None:
        raw = load_object(fedwatch_renderer_path, "renderer FedWatch fragment")
        renderer_fedwatch = raw.get("fedwatch", raw)
    renderer_market = adapt_market_snapshot(normalized_market, renderer_fedwatch)

    template = template_path.read_text(encoding="utf-8")
    calendar = build_calendar_snapshot(current_week, previous_week,
                                       report_day.isoformat(), template, binding)
    editorial_fragments = [
        load_object(path, f"content fragment {path}") for path in content_fragments
    ]
    editorial = validate_content_fragments(editorial_fragments)
    renderer_snapshot = compose(renderer_market, calendar, [editorial])
    rendered = render_market_html(template, renderer_snapshot, binding)

    expected_title = f"TAC 投資早報｜{report_day.year}/{report_day.month:02d}/{report_day.day:02d}（{'一二三四五'[report_day.weekday()]}）審核版"
    if f"<title>{expected_title}</title>" not in rendered:
        raise ValueError("rendered report title does not match requested report date")
    if f'name="report-date" content="{report_day.isoformat()}"' not in rendered:
        raise ValueError("rendered report-date meta tag does not match requested date")

    output = output.resolve()
    review_root = (ROOT / "review").resolve()
    if output.parent != review_root or output.name != f"{report_day.isoformat()}-review.html":
        raise ValueError("output must be review/YYYY-MM-DD-review.html")
    if output.exists():
        raise ValueError(f"review output already exists; refusing to overwrite: {output.relative_to(ROOT)}")
    review_root.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(f"PASS: assembled {scenario} report from {len(market_data)} market fragment(s)")
    print(f"PASS: calendar database {current_path.relative_to(ROOT)}" +
          (f" + {iso_week_path(report_day - timedelta(days=7)).relative_to(ROOT)}" if previous_week else ""))
    print(f"PASS: required editorial content (5 global focus + 10 headlines)")
    print(f"PASS: report metadata updated to {report_day.isoformat()}; trading date {trading_day.isoformat()}")
    print(f"REVIEW ONLY: {output.relative_to(ROOT)}")
    print("NOT DEPLOYED: index.html, WR and approved mother templates were not modified.")
    return output

def self_test() -> None:
    assert scenario_for(date(2026, 11, 2)) == "monday"
    assert scenario_for(date(2026, 11, 3)) == "weekdays"
    for value in ("2026-11-07", "2026-11-08"):
        try:
            scenario_for(date.fromisoformat(value))
        except ValueError:
            pass
        else:
            raise AssertionError("weekend report date must be rejected")
    print("PASS: Monday and Tuesday-Friday template selection")
    print("PASS: weekend report dates rejected")

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report-date")
    ap.add_argument("--trading-date")
    ap.add_argument("--market-fragment", action="append", default=[])
    ap.add_argument("--content-fragment", action="append", default=[])
    ap.add_argument("--fedwatch-renderer")
    ap.add_argument("--output")
    ap.add_argument("--generated-at")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not all((args.report_date, args.trading_date)):
        ap.error("--report-date and --trading-date are required")
    output = Path(args.output) if args.output else ROOT / "review" / f"{args.report_date}-review.html"
    try:
        build_preview(
            args.report_date, args.trading_date,
            [Path(x) for x in args.market_fragment],
            [Path(x) for x in args.content_fragment],
            output, args.generated_at,
            Path(args.fedwatch_renderer) if args.fedwatch_renderer else None
        )
        return 0
    except Exception as exc:
        print(f"TAC DAILY PIPELINE BLOCKED: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
