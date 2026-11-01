#!/usr/bin/env python3
"""Fail-safe TAC daily report orchestrator prototype.

The calendar-only mode is a real integration trial. Full mode deliberately
refuses to claim completion until verified market, news, analysis and full-page
rendering inputs are supplied. This script never writes index.html or a master.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
TZ = ZoneInfo("Asia/Taipei")
WR_PATH = ROOT / "TAC_WORK_RULES.md"
MANIFEST_PATH = ROOT / "母版專區" / "mother-template-manifest.json"
DB_SCRIPT = ROOT / "scripts" / "tac_weekly_calendar_db.py"
CALENDAR_RENDERER = ROOT / "scripts" / "tac_calendar_html_renderer.py"
WEB_OBSERVATION_CONVERTER = ROOT / "scripts" / "convert_tac_web_observations.py"
MARKET_SNAPSHOT_VALIDATOR = ROOT / "scripts" / "validate_tac_daily_snapshot.py"
MARKET_RENDERER = ROOT / "scripts" / "render_tac_market_snapshot.py"
CONTENT_VALIDATOR = ROOT / "scripts" / "validate_tac_daily_content.py"
FULL_PAGE_RENDERER = ROOT / "scripts" / "render_tac_full_report.py"
LAYOUT_VALIDATOR = ROOT / "scripts" / "validate_tac_layout_contract.py"
BROWSER_QA = ROOT / "scripts" / "tac_browser_layout_regression.mjs"
MODE_BY_WEEKDAY = {0: "monday", 1: "weekday", 2: "weekday", 3: "weekday", 4: "weekday"}


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def iso_week_id(day: date) -> str:
    year, week, _ = day.isocalendar()
    return f"{year}-W{week:02d}"


def previous_iso_week_id(day: date) -> str:
    return iso_week_id(day - timedelta(days=7))


def read_wr_version() -> str:
    text = WR_PATH.read_text(encoding="utf-8")
    match = re.search(r"^版本：([0-9.]+)", text, re.MULTILINE)
    if not match:
        raise ValueError("正式 WR 版本欄位不存在")
    return match.group(1)


def verify_master(report_date: date) -> tuple[str, Path, str]:
    if report_date.weekday() not in MODE_BY_WEEKDAY:
        raise ValueError("週末不自動製作早報")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    mode = MODE_BY_WEEKDAY[report_date.weekday()]
    entry = manifest["templates"][mode]
    template = ROOT / entry["path"]
    if not template.is_file():
        raise ValueError(f"核准母版不存在：{entry['path']}")
    actual_sha = git_blob_sha(template)
    expected_sha = entry["blob_sha"]
    if actual_sha != expected_sha:
        raise ValueError(
            f"母版 SHA 不符，停止製作：{entry['path']} expected={expected_sha} actual={actual_sha}"
        )
    return mode, template, actual_sha


def run(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=ROOT, check=True, text=True, capture_output=True)


def calendar_trial(report_date: date, output_dir: Path) -> dict:
    week_id = iso_week_id(report_date)
    previous_week_id = previous_iso_week_id(report_date)
    week_file = ROOT / "data" / "calendar" / "weeks" / f"{week_id}.json"
    previous_file = ROOT / "data" / "calendar" / "weeks" / f"{previous_week_id}.json"
    if not week_file.is_file():
        raise ValueError(f"當週行事曆資料庫不存在：{week_file.relative_to(ROOT)}")
    if not previous_file.is_file():
        raise ValueError(f"上週封存資料庫不存在：{previous_file.relative_to(ROOT)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot = output_dir / f"{report_date.isoformat()}-calendar-snapshot.json"
    quality = output_dir / f"{report_date.isoformat()}-calendar-quality.json"
    preview = output_dir / f"{report_date.isoformat()}-calendar-only-review.html"

    run([
        sys.executable, str(DB_SCRIPT), "snapshot",
        "--file", str(week_file),
        "--previous-week-file", str(previous_file),
        "--report-date", report_date.isoformat(),
        "--output", str(snapshot),
    ])
    run([
        sys.executable, str(DB_SCRIPT), "quality-report",
        "--file", str(week_file),
        "--output", str(quality),
    ])
    mode, template, _ = verify_master(report_date)
    run([
        sys.executable, str(CALENDAR_RENDERER),
        "--template", str(template),
        "--snapshot", str(snapshot),
        "--output", str(preview),
        "--mode", mode,
    ])

    html = preview.read_text(encoding="utf-8")
    required = ('<html', '</html>', 'id="calendar"', 'id="earnings"')
    missing = [marker for marker in required if marker not in html.lower()]
    if missing:
        raise ValueError("行事曆預覽 HTML 驗證失敗：" + ", ".join(missing))
    if mode == "monday":
        for marker in ('id="last-week-calendar"', 'id="last-week-earnings"'):
            if marker not in html:
                raise ValueError("週一母版缺少上週區塊：" + marker)
    else:
        for marker in ('id="last-week-calendar"', 'id="last-week-earnings"'):
            if marker in html:
                raise ValueError("平日母版不應出現上週區塊：" + marker)

    return {
        "calendar_snapshot": str(snapshot),
        "calendar_quality_report": str(quality),
        "calendar_only_preview": str(preview),
        "template_mode": mode,
        "template_path": str(template.relative_to(ROOT)),
        "template_blob_sha": git_blob_sha(template),
        "html_smoke_test": "PASS",
    }



def calendar_snapshot_trial(report_date: date, output_dir: Path,
                            current_file: str | None = None,
                            previous_file: str | None = None) -> dict:
    """Read the canonical weekly DB and create the report-date calendar snapshot."""
    week_id = iso_week_id(report_date)
    previous_week_id = previous_iso_week_id(report_date)
    week_file = Path(current_file) if current_file else ROOT / "data" / "calendar" / "weeks" / f"{week_id}.json"
    previous_path = Path(previous_file) if previous_file else ROOT / "data" / "calendar" / "weeks" / f"{previous_week_id}.json"
    if not week_file.is_file():
        raise ValueError(f"當週正式行事曆資料庫不存在：{week_file}")
    if report_date.weekday() == 0 and not previous_path.is_file():
        raise ValueError(f"週一必要的上週封存資料庫不存在：{previous_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot = output_dir / f"{report_date.isoformat()}-calendar-snapshot.json"
    quality = output_dir / f"{report_date.isoformat()}-calendar-quality.json"
    command = [
        sys.executable, str(DB_SCRIPT), "snapshot",
        "--file", str(week_file),
        "--report-date", report_date.isoformat(),
        "--output", str(snapshot),
    ]
    if report_date.weekday() == 0:
        command.extend(["--previous-week-file", str(previous_path)])
    run(command)
    run([
        sys.executable, str(DB_SCRIPT), "quality-report",
        "--file", str(week_file),
        "--output", str(quality),
    ])
    return {
        "week_id": week_id,
        "previous_week_id": previous_week_id if report_date.weekday() == 0 else None,
        "database_path": str(week_file.relative_to(ROOT)),
        "previous_database_path": str(previous_path.relative_to(ROOT)) if report_date.weekday() == 0 else None,
        "calendar_snapshot": str(snapshot),
        "calendar_quality_report": str(quality),
        "snapshot_created": snapshot.is_file(),
        "quality_report_created": quality.is_file(),
    }


def full_mode_blockers(args: argparse.Namespace) -> list[str]:
    blockers = []
    for label, value in (
        ("已驗證市場快照", args.market_snapshot),
        ("已核實新聞與 AI 分析內容包", args.content_json),
    ):
        if not value:
            blockers.append(f"尚未接入：{label}")
        elif not Path(value).is_file():
            blockers.append(f"指定檔案不存在：{label} ({value})")
    if args.content_json and Path(args.content_json).is_file():
        content = json.loads(Path(args.content_json).read_text(encoding="utf-8"))
        if len(content.get("focus_news", [])) != 5:
            blockers.append("全球焦點新聞必須恰好 5 則")
        if len(content.get("market_headlines", [])) != 10:
            blockers.append("市場熱門頭條必須恰好 10 則")
    return blockers


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-date", required=True, help="Taipei report date YYYY-MM-DD")
    parser.add_argument("--output-dir", default="artifacts/tac-daily-report-trial")
    parser.add_argument("--mode", choices=("calendar-only", "full"), default="calendar-only")
    parser.add_argument("--market-snapshot")
    parser.add_argument("--web-observations", help="ChatGPT direct webpage-read observation JSON")
    parser.add_argument("--content-json", help="Validated editorial content v2 JSON")
    parser.add_argument("--calendar-week-file", help="Override current ISO-week database file")
    parser.add_argument("--previous-week-file", help="Override previous ISO-week database file (Monday only)")
    args = parser.parse_args()

    report_date = date.fromisoformat(args.report_date)
    if report_date.weekday() not in MODE_BY_WEEKDAY:
        raise ValueError("週末不自動製作早報")
    wr_version = read_wr_version()
    if wr_version != "3.10":
        raise ValueError(f"目前正式 WR 為 {wr_version}，本原型要求先同步確認 WR 版本")

    mode, template, template_sha = verify_master(report_date)
    output_dir = Path(args.output_dir)
    result = {
        "report_date": report_date.isoformat(),
        "timezone": "Asia/Taipei",
        "wr_version": wr_version,
        "status": "calendar_trial_only",
        "template_mode": mode,
        "template_path": str(template.relative_to(ROOT)),
        "template_blob_sha": template_sha,
        "publish_allowed": False,
        "protected_paths": ["index.html", "TAC_WORK_RULES.md", str(template.relative_to(ROOT)), "母版專區/mother-template-manifest.json"],
    }


    if args.mode == "full":
        if args.market_snapshot and args.web_observations:
            raise ValueError("請只提供 --market-snapshot 或 --web-observations，不可同時提供")
        output_dir.mkdir(parents=True, exist_ok=True)

        # The canonical weekly DB is now part of the same full-report run.
        calendar_result = calendar_snapshot_trial(
            report_date, output_dir, args.calendar_week_file, args.previous_week_file
        )
        result["calendar"] = calendar_result

        if args.web_observations:
            observation_path = Path(args.web_observations)
            if not observation_path.is_file():
                raise ValueError("直接網頁觀察資料不存在：" + str(observation_path))
            market_path = output_dir / (report_date.isoformat() + "-market-snapshot.json")
            run([
                sys.executable, str(WEB_OBSERVATION_CONVERTER),
                "--input", str(observation_path),
                "--output", str(market_path),
                "--expected-report-date", report_date.isoformat(),
            ])
            run([
                sys.executable, str(MARKET_SNAPSHOT_VALIDATOR),
                "--file", str(market_path),
            ])
            args.market_snapshot = str(market_path)
        elif args.market_snapshot:
            market_path = Path(args.market_snapshot)
            if not market_path.is_file():
                raise ValueError("行情快照不存在：" + str(market_path))
            run([
                sys.executable, str(MARKET_SNAPSHOT_VALIDATOR),
                "--file", str(market_path),
            ])

        market_preview = None
        if args.market_snapshot:
            market_preview_path = output_dir / (report_date.isoformat() + "-market-only-review.html")
            run([
                sys.executable, str(MARKET_RENDERER),
                "--template", str(template),
                "--snapshot", str(args.market_snapshot),
                "--output", str(market_preview_path),
                "--mode", mode,
            ])
            market_preview = str(market_preview_path)
        result["market_only_preview"] = market_preview

        # Calendar DB events replace only the four calendar arrays in the
        # editorial package. News and analysis remain sourced editorial input.
        if args.content_json and Path(args.content_json).is_file():
            content_path = Path(args.content_json)
            content_data = json.loads(content_path.read_text(encoding="utf-8"))
            if content_data.get("meta", {}).get("report_date") != report_date.isoformat():
                raise ValueError("content report_date mismatch")
            if args.market_snapshot:
                market_data = json.loads(Path(args.market_snapshot).read_text(encoding="utf-8"))
                if content_data.get("meta", {}).get("trading_date") != market_data.get("meta", {}).get("trading_date"):
                    raise ValueError("content and market snapshot trading_date mismatch")
            merged_content = output_dir / f"{report_date.isoformat()}-content-with-calendar.json"
            run([
                sys.executable, str(DB_SCRIPT), "apply-snapshot",
                "--content", str(content_path),
                "--snapshot", calendar_result["calendar_snapshot"],
                "--output", str(merged_content),
            ])
            args.content_json = str(merged_content)

        blockers = full_mode_blockers(args)
        if not blockers and args.market_snapshot and args.content_json:
            content_path = Path(args.content_json)
            run([
                sys.executable, str(CONTENT_VALIDATOR),
                "--file", str(content_path),
            ])
            staged_preview = output_dir / f"{report_date.isoformat()}-review-staged.html"
            render_run = run([
                sys.executable, str(FULL_PAGE_RENDERER),
                "--snapshot", str(args.market_snapshot),
                "--content", str(content_path),
                "--output", str(staged_preview),
            ])
            if not staged_preview.is_file():
                raise ValueError("Full Report Renderer did not create its HTML output")

            # Gate 2: compare the rendered DOM/layout contract with the exact
            # SHA-verified mother selected for this report date.
            run([
                sys.executable, str(LAYOUT_VALIDATOR),
                "--master", str(template),
                "--report", str(staged_preview),
            ])

            # Gate 3 and Gate 4: real Chromium viewports, screenshots,
            # geometry, overflow, tabs and disclosure interaction checks.
            if not BROWSER_QA.is_file():
                raise ValueError("Browser QA script missing; visual/interaction gates cannot run")
            run([
                "node", str(BROWSER_QA),
                "--report", str(staged_preview),
                "--output", str(output_dir / "layout-regression"),
            ])

            # Gate 1 has passed schema/rule validation for market and editorial
            # data. Pending values remain explicitly visible; they are not
            # silently converted into verified observations.
            market_data = json.loads(Path(args.market_snapshot).read_text(encoding="utf-8"))
            pending_market = sum(
                row.get("status") not in {"verified", "market_closed"}
                for group in ("global_indices", "sectors", "bonds", "fx", "energy", "precious_metals", "risk_indicators")
                for row in market_data.get(group, {}).values()
            )
            calendar_data = json.loads(Path(calendar_result["calendar_snapshot"]).read_text(encoding="utf-8"))
            pending_calendar = sum(
                item.get("status") == "pending_verification"
                for group in ("economic_calendar", "earnings_calendar", "previous_economic_calendar", "previous_earnings_calendar")
                for item in calendar_data.get(group, [])
            )
            final_preview = ROOT / "preview" / f"{report_date.isoformat()}.html"
            final_preview.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(staged_preview, final_preview)

            result["full_page_preview"] = str(final_preview.relative_to(ROOT))
            result["staged_preview"] = str(staged_preview)
            result["gates"] = {
                "data_quality": "PASS",
                "html_structure": "PASS",
                "visual_regression": "PASS",
                "interaction": "PASS",
            }
            result["pending_items"] = {
                "market_records": pending_market,
                "calendar_events": pending_calendar,
            }
            result["status"] = (
                "ready_for_human_review_with_pending_items"
                if pending_market or pending_calendar
                else "ready_for_human_review"
            )
            result["publish_allowed"] = False
            result["blockers"] = []
            result["preview_written_only_after_all_gates"] = True
            report = output_dir / f"{report_date.isoformat()}-orchestrator-status.json"
            report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        else:
            result["status"] = "blocked"
            result["blockers"] = blockers
            result["publish_allowed"] = False
            report = output_dir / f"{report_date.isoformat()}-orchestrator-status.json"
            report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 2


    result["calendar"] = calendar_trial(report_date, output_dir)
    result["status"] = "calendar_trial_passed_full_report_not_ready"
    report = output_dir / f"{report_date.isoformat()}-orchestrator-status.json"
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("ORCHESTRATOR FAIL-SAFE: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
