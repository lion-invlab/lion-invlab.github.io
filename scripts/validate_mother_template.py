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
README_PATH = Path("母版專區/README.md")

# These values are deliberately duplicated outside the manifest. If both the
# manifest and validator could be changed silently, the manifest would not be
# an effective guard. Updating these values requires an explicitly approved
# mother-template change.
APPROVED = {
    "monday": {
        "path": "母版專區/TAC_母版_週一_2026-10-28_最終定版.html",
        "blob_sha": "776f778b895c6da781348bcf8fefc1d4719ed4ce",
        "required_ids": {"sentiment", "bonds", "fx", "calendar", "earnings",
                         "last-week-calendar", "last-week-earnings"},
        "required_nav_targets": {"last-week-calendar", "last-week-earnings"},
        "forbidden_ids": set(),
    },
    "weekdays": {
        "path": "母版專區/TAC_母版_週二至週五_2026-10-28_最終定版.html",
        "blob_sha": "ab3286750a64aa0fc9fc01af51f819024526a4ba",
        "required_ids": {"sentiment", "bonds", "fx", "calendar", "earnings"},
        "required_nav_targets": set(),
        "forbidden_ids": {"last-week-calendar", "last-week-earnings"},
    },
}


class IdParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.nav_targets: set[str] = set()

    def handle_starttag(self, tag, attrs):
        attr_map = dict(attrs)
        element_id = attr_map.get("id")
        if element_id:
            self.ids.add(element_id)
        href = attr_map.get("href", "")
        if tag.lower() == "a" and href.startswith("#"):
            self.nav_targets.add(href[1:])


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

    # The repository-root TAC_WORK_RULES.md is the sole authoritative rules file.
    # Historical copies under 母版專區 are non-authoritative and must not gate validation.
    expected_rules = ROOT / RULES_PATH
    if not expected_rules.is_file():
        fail("唯一正式規則檔不存在：TAC_WORK_RULES.md")

    kind = "monday" if report_date.weekday() == 0 else "weekdays"
    template = manifest.get("templates", {}).get(kind)
    if not template:
        fail(f"manifest 缺少情境設定：{kind}")
    policy = APPROVED[kind]
    path = template.get("path", "")
    approved_sha = template.get("blob_sha", "")
    if path != policy["path"]:
        fail(f"manifest 的 {kind} 路徑不符合硬編碼核准路徑：{path}")
    if approved_sha != policy["blob_sha"]:
        fail(f"manifest 的 {kind} SHA 不符合硬編碼核准 SHA：{approved_sha}")
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
    missing = sorted(policy["required_ids"] - ids.ids)
    if missing:
        fail(f"{kind} 母版缺少必要結構 ID：{', '.join(missing)}")

    forbidden = sorted(policy["forbidden_ids"] & ids.ids)
    if forbidden:
        fail(f"{kind} 母版含有禁止的結構 ID：{', '.join(forbidden)}")

    missing_nav = sorted(policy["required_nav_targets"] - ids.nav_targets)
    if missing_nav:
        fail(f"{kind} 母版缺少對應導航錨點：{', '.join(missing_nav)}")

    for target in policy["forbidden_ids"]:
        if target in ids.nav_targets:
            fail(f"{kind} 母版導航仍指向禁止的區塊：{target}")

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
