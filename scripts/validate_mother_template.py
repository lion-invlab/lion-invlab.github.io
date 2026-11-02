#!/usr/bin/env python3
"""Single fail-closed guard for TAC's two approved daily-report masters."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = Path("母版專區/mother-template-manifest.json")
RULES_PATH = Path("TAC_WORK_RULES.md")

# Independent trust anchor: the Manifest remains the sole registry, while these
# pinned values prevent a silent simultaneous edit of the Manifest and masters.
APPROVED = {
    "monday": {
        "path": "母版專區/TAC_母版_週一_2026-10-28_最終定版.html",
        "blob_sha": "0ea4775c5d15899a1e0b0a97c78744d90b8fff22",
        "title": "TAC 投資早報｜2026/10/26（一）審核版",
        "required_ids": {
            "overview", "sentiment", "news-scan", "global-markets",
            "industry-bonds-fx-commodities", "bonds", "fx", "calendar",
            "earnings", "last-week-calendar", "last-week-earnings",
            "sp500-earnings-health", "fed", "view",
        },
        "required_nav_ids": {
            "overview", "sentiment", "news-scan", "global-markets",
            "industry-bonds-fx-commodities", "last-week-calendar",
            "last-week-earnings", "calendar", "earnings",
            "sp500-earnings-health", "fed", "view",
        },
        "forbidden_ids": set(),
        "forbidden_nav_ids": set(),
    },
    "weekdays": {
        "path": "母版專區/TAC_母版_週二至週五_2026-10-28_最終定版.html",
        "blob_sha": "e5976190efd4c7fcc92cd623bfa94926997cc672",
        "title": "TAC 投資早報｜2026/10/28（三）審核版",
        "required_ids": {
            "overview", "sentiment", "news-scan", "global-markets",
            "industry-bonds-fx-commodities", "bonds", "fx", "calendar",
            "earnings", "sp500-earnings-health", "fed", "view",
        },
        "required_nav_ids": {
            "overview", "sentiment", "news-scan", "global-markets",
            "industry-bonds-fx-commodities", "calendar", "earnings",
            "sp500-earnings-health", "fed", "view",
        },
        "forbidden_ids": {"last-week-calendar", "last-week-earnings"},
        "forbidden_nav_ids": {"last-week-calendar", "last-week-earnings"},
    },
}
REQUIRED_MARKERS = ("今日關鍵價位", "今日核心觀察")


class StructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.nav_targets: set[str] = set()
        self.in_nav = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        element_id = attrs.get("id")
        if element_id:
            self.ids.append(element_id)
        if tag.lower() == "nav":
            self.in_nav += 1
        href = attrs.get("href", "")
        if self.in_nav and tag.lower() == "a" and href.startswith("#"):
            self.nav_targets.add(href[1:])

    def handle_endtag(self, tag):
        if tag.lower() == "nav" and self.in_nav:
            self.in_nav -= 1


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

    if not (ROOT / RULES_PATH).is_file():
        fail("唯一正式規則檔不存在：TAC_WORK_RULES.md")

    kind = "monday" if report_date.weekday() == 0 else "weekdays"
    template = manifest.get("templates", {}).get(kind)
    if not template:
        fail(f"manifest 缺少情境設定：{kind}")
    policy = APPROVED[kind]
    path = template.get("path", "")
    approved_sha = template.get("blob_sha", "")
    if path != policy["path"]:
        fail(f"manifest 的 {kind} 路徑不符合核准路徑：{path}")
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
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.I | re.S)
    actual_title = re.sub(r"\\s+", " ", title_match.group(1)).strip() if title_match else None
    if actual_title != policy["title"]:
        fail(f"{kind} 母版 title 不符：expected={policy['title']!r}; actual={actual_title!r}")

    structure = StructureParser()
    structure.feed(html)
    id_set = set(structure.ids)
    missing = sorted(policy["required_ids"] - id_set)
    if missing:
        fail(f"{kind} 母版缺少必要結構 ID：{', '.join(missing)}")
    forbidden = sorted(policy["forbidden_ids"] & id_set)
    if forbidden:
        fail(f"{kind} 母版含有禁止的結構 ID：{', '.join(forbidden)}")

    missing_nav = sorted(policy["required_nav_ids"] - structure.nav_targets)
    if missing_nav:
        fail(f"{kind} 母版缺少必要導航錨點：{', '.join(missing_nav)}")
    forbidden_nav = sorted(policy["forbidden_nav_ids"] & structure.nav_targets)
    if forbidden_nav:
        fail(f"{kind} 母版導航仍指向禁止的區塊：{', '.join(forbidden_nav)}")
    missing_targets = sorted(structure.nav_targets - id_set)
    if missing_targets:
        fail(f"{kind} 母版存在失效導航目標：{', '.join(missing_targets)}")

    duplicates = sorted(value for value, count in Counter(structure.ids).items() if count > 1)
    if duplicates:
        print(f"WARN: 核准母版既有重複 ID（SHA 已鎖定，不擅自改版）：{', '.join(duplicates)}")

    missing_markers = [marker for marker in REQUIRED_MARKERS if marker not in html]
    if missing_markers:
        fail(f"{kind} 母版缺少必要內容標記：{', '.join(missing_markers)}")

    print("PASS: TAC 母版來源與結構驗證通過")
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
