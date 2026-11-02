#!/usr/bin/env python3
"""Fail-closed TAC daily preview orchestrator.

This command assembles already captured, provenance-bearing market fragments,
the weekly calendar database, and required editorial content. It renders only
a review HTML file. It never fetches quotes, edits mothers/WR, or deploys index.
"""
from __future__ import annotations
import argparse
import json
import math
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from adapt_tac_market_snapshot_for_renderer import adapt_market_snapshot
from adapt_tac_fedwatch_capture import adapt_capture as adapt_fedwatch_capture
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

def load_capture_bundle(capture_dir: Path, report_date: str, trading_date: str) -> tuple[list[Path], Path]:
    capture_dir = capture_dir.resolve()
    try:
        capture_dir.relative_to(ROOT)
    except ValueError:
        raise ValueError("capture bundle directory must remain inside the repository workspace")
    manifest_path = capture_dir / "capture_manifest.json"
    if not manifest_path.is_file():
        raise ValueError("capture bundle manifest is missing")
    manifest = load_object(manifest_path, "capture bundle manifest")
    if manifest.get("report_date") != report_date or manifest.get("trading_date") != trading_date:
        raise ValueError("capture bundle report/trading dates do not match this report")
    names = manifest.get("market_fragments")
    if not isinstance(names, list) or len(names) != 4:
        raise ValueError("capture bundle must provide exactly four market fragments")
    fragments = []
    required_groups = {"global_indices", "sectors", "bonds", "fx", "energy", "precious_metals", "risk_indicators"}
    covered = set()
    for name in names:
        path = (ROOT / name).resolve()
        try:
            path.relative_to(capture_dir)
        except ValueError:
            raise ValueError("capture bundle fragment path escapes its bundle directory")
        if not path.is_file():
            raise ValueError(f"capture bundle fragment missing: {name}")
        fragment = load_object(path, f"capture fragment {name}")
        if fragment.get("report_date") != report_date or fragment.get("trading_date") != trading_date:
            raise ValueError(f"capture fragment date mismatch: {name}")
        covered.update(key for key in required_groups if key in fragment)
        fragments.append(path)
    if covered != required_groups:
        raise ValueError(f"capture bundle market group coverage incomplete: {sorted(required_groups - covered)}")
    fedwatch_name = manifest.get("fedwatch_capture")
    if not isinstance(fedwatch_name, str):
        raise ValueError("capture bundle has no Fed Rate Monitor capture path")
    fedwatch_path = (ROOT / fedwatch_name).resolve()
    try:
        fedwatch_path.relative_to(capture_dir)
    except ValueError:
        raise ValueError("FedWatch capture path escapes capture bundle directory")
    if not fedwatch_path.is_file():
        raise ValueError("Fed Rate Monitor capture file is missing")
    return fragments, fedwatch_path


KEY_LEVELS = {
    "dow": ("道瓊工業指數", "DJI", "us-30"),
    "sp500": ("S&P 500", "SPX", "us-spx-500"),
    "nasdaq_composite": ("Nasdaq Composite", "IXIC", "nasdaq-composite"),
    "sox": ("費城半導體指數（SOX）", "SOX", "phlx-semiconductor"),
    "russell_2000": ("Russell 2000", "RUT", "smallcap-2000"),
}


def derive_key_levels(market_fragments: list[dict], report_date: str,
                      trading_date: str) -> tuple[list[str], dict]:
    bundles = [fragment["key_levels"] for fragment in market_fragments
               if isinstance(fragment.get("key_levels"), dict)]
    if len(bundles) > 1:
        raise ValueError("multiple key-level OHLC bundles supplied")
    bundle = bundles[0] if bundles else {}
    if bundle and (bundle.get("report_date") != report_date
                   or bundle.get("trading_date") != trading_date):
        raise ValueError("key-level OHLC bundle report/trading date mismatch")
    records = bundle.get("indices", {}) if isinstance(bundle, dict) else {}
    if not isinstance(records, dict):
        records = {}
    market_records = {}
    for fragment in market_fragments:
        group = fragment.get("global_indices")
        if isinstance(group, dict):
            for key, value in group.items():
                if key in market_records:
                    raise ValueError(f"duplicate global index record for key levels: {key}")
                market_records[key] = value

    segments = []
    items = []
    for key, (label, ticker, slug) in KEY_LEVELS.items():
        record = records.get(key, {})
        source = record.get("source") if isinstance(record, dict) else None
        ohlc = record.get("ohlc") if isinstance(record, dict) else None
        expected_url = f"https://hk.investing.com/indices/{slug}-historical-data"
        reason = None
        values = None
        if not isinstance(record, dict) or record.get("status") != "verified":
            reason = record.get("notes", "未取得指定交易日 OHLC") if isinstance(record, dict) else "未取得指定交易日 OHLC"
        elif not isinstance(source, dict) or source.get("name") != "Investing.com 香港站":
            reason = "來源身分未核實"
        elif source.get("data_date") != trading_date:
            reason = "OHLC 資料日期不符"
        elif source.get("url") != expected_url:
            reason = "OHLC 來源網址不符"
        elif not isinstance(source.get("instrument"), str) or ticker not in source["instrument"]:
            reason = "指數標的身分不符"
        elif not isinstance(ohlc, dict) or set(ohlc) != {"open", "high", "low", "close"}:
            reason = "OHLC 欄位不完整"
        elif not isinstance(market_records.get(key), dict) or market_records[key].get("status") != "verified":
            reason = "同一指數的收市價尚未核實"
        elif (market_records[key].get("source", {}).get("data_date") != trading_date
              or market_records[key].get("value") != ohlc.get("close")):
            reason = "OHLC 收市價與行情片段不一致"
        else:
            candidate = [ohlc.get(name) for name in ("open", "high", "low", "close")]
            if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 for v in candidate):
                reason = "OHLC 數值無效"
            else:
                open_value, high_value, low_value, close_value = candidate
                if high_value < max(open_value, close_value) or low_value > min(open_value, close_value) or high_value < low_value:
                    reason = "OHLC 區間不合理"
                else:
                    values = dict(ohlc)
        if values is None:
            segments.append(f"{label}：待核實（{reason or 'OHLC 尚未完成核對'}）")
            items.append({
                "key": key, "label": label, "status": "pending_verification",
                "ohlc": None, "pivot": None, "support1": None, "resistance1": None,
                "source_url": source.get("url") if isinstance(source, dict) else None,
                "source_instrument": source.get("instrument") if isinstance(source, dict) else None,
                "observed_at": source.get("observed_at") if isinstance(source, dict) else None,
                "notes": reason or "OHLC 尚未完成核對",
            })
            continue
        pivot = (values["high"] + values["low"] + values["close"]) / 3
        support1 = 2 * pivot - values["high"]
        resistance1 = 2 * pivot - values["low"]
        segments.append(
            f"{label}：支撐 S1：{support1:,.2f}｜中樞 P：{pivot:,.2f}｜壓力 R1：{resistance1:,.2f}"
        )
        items.append({
            "key": key, "label": label, "status": "verified",
            "ohlc": values, "pivot": round(pivot, 2),
            "support1": round(support1, 2), "resistance1": round(resistance1, 2),
            "source_url": source["url"], "source_instrument": source["instrument"],
            "observed_at": source.get("observed_at"),
            "notes": "同一基準交易日 OHLC；經典樞紐點公式",
        })
    return segments, {
        "report_date": report_date, "trading_date": trading_date,
        "method": "經典樞紐點：P=(H+L+C)/3；S1=2P−H；R1=2P−L。",
        "items": items,
    }


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
    required_editorial = {"headline", "body_segments", "market_text", "core_text"}
    if not isinstance(editorial, dict) or set(editorial) != required_editorial:
        raise ValueError("editorial fragment must provide headline, body_segments, market_text and core_text; key levels are derived from verified OHLC")
    return merged

def build_preview(report_date: str, trading_date: str, market_fragments: list[Path],
                  content_fragments: list[Path], output: Path,
                  generated_at: str | None = None,
                  fedwatch_capture_path: Path | None = None) -> Path:
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
    if fedwatch_capture_path is not None:
        capture = load_object(fedwatch_capture_path, "Investing.com Fed Rate Monitor capture")
        normalized_fedwatch, renderer_fedwatch, mapping_error = adapt_fedwatch_capture(
            capture, report_day.isoformat()
        )
        if normalized_fedwatch is not None:
            normalized_market["fedwatch"] = normalized_fedwatch
            validator.validate(normalized_market)
            print("PASS: Investing.com Fed Rate Monitor outcomes mapped to hold and one 25bp hike; normalized Snapshot revalidated")
        else:
            print(f"FedWatch remains 待核實: {mapping_error}")
    renderer_market = adapt_market_snapshot(normalized_market, renderer_fedwatch)

    template = template_path.read_text(encoding="utf-8")
    calendar = build_calendar_snapshot(current_week, previous_week,
                                       report_day.isoformat(), template, binding)
    editorial_fragments = [
        load_object(path, f"content fragment {path}") for path in content_fragments
    ]
    editorial = validate_content_fragments(editorial_fragments)
    levels_segments, levels_source = derive_key_levels(market_data, report_day.isoformat(), trading_day.isoformat())
    editorial["editorial"]["levels_segments"] = levels_segments
    editorial["editorial"]["levels_source"] = levels_source
    verified_levels = sum(item["status"] == "verified" for item in levels_source["items"])
    print(f"Key levels: {verified_levels}/5 verified from same-day OHLC; remaining items marked 待核實")
    renderer_snapshot = compose(renderer_market, calendar, [editorial])
    rendered = render_market_html(template, renderer_snapshot, binding)

    expected_title = f"TAC 投資早報｜{report_day.year}/{report_day.month:02d}/{report_day.day:02d}（{'一二三四五'[report_day.weekday()]}）審核版"
    if f"<title>{expected_title}</title>" not in rendered:
        raise ValueError("rendered report title does not match requested report date")
    report_date_meta_forms = (
        f'content="{report_day.isoformat()}" name="report-date"',
        f'name="report-date" content="{report_day.isoformat()}"',
    )
    if not any(form in rendered for form in report_date_meta_forms):
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
    ap.add_argument("--capture-dir", help="Use the four market fragments and Fed Rate Monitor capture from capture_tac_market_bundle.py")
    ap.add_argument("--market-fragment", action="append", default=[])
    ap.add_argument("--content-fragment", action="append", default=[])
    ap.add_argument("--fedwatch-capture")
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
        if args.capture_dir:
            if args.market_fragment or args.fedwatch_capture:
                raise ValueError("--capture-dir cannot be combined with --market-fragment or --fedwatch-capture")
            market_paths, fedwatch_path = load_capture_bundle(Path(args.capture_dir), args.report_date, args.trading_date)
        else:
            market_paths = [Path(x) for x in args.market_fragment]
            fedwatch_path = Path(args.fedwatch_capture) if args.fedwatch_capture else None
        build_preview(
            args.report_date, args.trading_date,
            market_paths,
            [Path(x) for x in args.content_fragment],
            output, args.generated_at, fedwatch_path
        )
        return 0
    except Exception as exc:
        print(f"TAC DAILY PIPELINE BLOCKED: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
