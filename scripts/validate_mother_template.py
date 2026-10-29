#!/usr/bin/env python3
"""Fail-closed guard for the two approved TAC daily-report masters."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = Path("母版專區/mother-template-manifest.json")
RULES_PATH = Path("TAC_WORK_RULES.md")
MIRROR_RULES_PATH = Path("母版專區/TAC_WORK_RULES.md")
README_PATH = Path("母版專區/README.md")


class IdParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key.lower() == "id" and value:
                self.ids.add(value)


def git_blob_sha(path: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", f"HEAD:{path}"], cwd=ROOT, text=True,
            stderr=subprocess.STDOUT
        ).strip()
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Git 中找不到核准路徑：{path}") from exc


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="台灣報告日期 YYYY-MM-DD；未提供則使用台灣今天")
    args = parser.parse_args()

    report_date = date.fromisoformat(args.date) if args.date else datetime.now(ZoneInfo("Asia/Taipei")).date()
    if report_date.weekday() >= 5:
        fail(f"{report_date.isoformat()} 是週末；依規則不得自動製作早報。")

    manifest_file = ROOT / MANIFEST_PATH
    if not manifest_file.is_file():
        fail(f"母版 manifest 不存在：{MANIFEST_PATH.as_posix()}")
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"manifest JSON 無法解析：{exc}")

    expected_rules = ROOT / RULES_PATH
    mirror_rules = ROOT / MIRROR_RULES_PATH
    if not expected_rules.is_file() or not mirror_rules.is_file():
        fail("正式規則檔或母版區同步副本不存在。")
    if expected_rules.read_bytes() != mirror_rules.read_bytes():
        fail("根目錄 TAC_WORK_RULES.md 與母版專區同步副本不一致。")

    kind = "monday" if report_date.weekday() == 0 else "weekdays"
    template = manifest.get("templates", {}).get(kind)
    if not template:
        fail(f"manifest 缺少情境設定：{kind}")
    path = template.get("path", "")
    approved_sha = template.get("blob_sha", "")
    if not path or not approved_sha:
        fail(f"manifest 的 {kind} 路徑或 SHA 不完整。")

    source_path = ROOT / path
    if not source_path.is_file():
        fail(f"核准母版檔不存在：{path}")
    actual_sha = git_blob_sha(path)
    if actual_sha != approved_sha:
        fail(f"核准母版 SHA 不符：{path}; expected={approved_sha}; actual={actual_sha}")

    html = source_path.read_text(encoding="utf-8")
    ids = IdParser()
    ids.feed(html)
    required_common = ["calendar", "earnings"]
    missing_common = [value for value in required_common if value not in ids.ids]
    if missing_common:
        fail(f"母版缺少必要行事曆結構 ID：{', '.join(missing_common)}")

    last_week_ids = {"last-week-calendar", "last-week-earnings"}
    if kind == "monday":
        missing = sorted(last_week_ids - ids.ids)
        if missing:
            fail("週一母版缺少上週行事曆區塊：" + ", ".join(missing))
    else:
        present = sorted(last_week_ids & ids.ids)
        if present:
            fail("週二至週五母版含有禁止的上週行事曆區塊：" + ", ".join(present))

    print("PASS: TAC 母版來源驗證通過")
    print(f"report_date={report_date.isoformat()}")
    print(f"scenario={kind}")
    print(f"source_path={path}")
    print(f"source_blob_sha={actual_sha}")
    print(f"manifest_path={MANIFEST_PATH.as_posix()}")
    print("fallback=disabled")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        fail(f"日期格式錯誤，請使用 YYYY-MM-DD：{exc}")
