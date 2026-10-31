#!/usr/bin/env python3
"""Validate the approved TAC report market-field contract without modifying HTML."""
from __future__ import annotations
import argparse
import html
import json
import re
import sys
from pathlib import Path
from html.parser import HTMLParser

TAG_RE = re.compile(r"<[^>]+>")


def text_only(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", value))).strip()


def extract_container(source: str, container_id: str) -> str:
    marker = re.search(r'<([a-zA-Z][\w:-]*)\b(?=[^>]*\bid=["\']' + re.escape(container_id) + r'["\'])[^>]*>', source, re.I)
    if not marker:
        raise ValueError(f"container id not found: {container_id}")
    tag = marker.group(1).lower()
    token = re.compile(r"</?" + re.escape(tag) + r"\b[^>]*>", re.I)
    depth = 0
    for match in token.finditer(source, marker.start()):
        if match.group(0).startswith("</"):
            depth -= 1
            if depth == 0:
                return source[marker.start():match.end()]
        elif not match.group(0).rstrip().endswith("/>"):
            depth += 1
    raise ValueError(f"unclosed container: {container_id}")


def extract_rows(container: str, class_name: str) -> list[str]:
    class Collector(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.active = []
            self.completed = []

        def handle_starttag(self, tag, attrs):
            classes = dict(attrs).get("class", "").split()
            for item in self.active:
                if tag == item["tag"]:
                    item["depth"] += 1
            if class_name in classes:
                self.active.append({"tag": tag, "depth": 1, "parts": []})

        def handle_data(self, data):
            for item in self.active:
                item["parts"].append(data)

        def handle_endtag(self, tag):
            for item in list(self.active):
                if tag == item["tag"]:
                    item["depth"] -= 1
                    if item["depth"] == 0:
                        self.completed.append(" ".join(item["parts"]))
                        self.active.remove(item)

    parser = Collector()
    parser.feed(container)
    parser.close()
    return parser.completed


def check_section(name: str, spec: dict, source: str) -> list[str]:
    errors: list[str] = []
    try:
        container = extract_container(source, spec["container_id"])
    except ValueError as exc:
        return [f"{name}: {exc}"]
    rows = extract_rows(container, spec["row_class"])
    expected = spec["expected_count"]
    if len(rows) != expected:
        errors.append(f"{name}: expected {expected} {spec['row_class']} rows, found {len(rows)}")
    texts = [text_only(row) for row in rows]
    if "labels" in spec:
        for label in spec["labels"]:
            hits = sum(label in row for row in texts)
            if hits != 1:
                errors.append(f"{name}: label '{label}' expected exactly once, found {hits}")
    if "tickers" in spec:
        for ticker in spec["tickers"]:
            hits = sum(re.search(r"\b" + re.escape(ticker) + r"\b", row) is not None for row in texts)
            if hits != 1:
                errors.append(f"{name}: ticker {ticker} expected exactly once, found {hits}")
    if "link_targets" in spec:
        for label, url in spec["link_targets"].items():
            label_html = html.escape(label, quote=False)
            pattern = r'<a\b[^>]*href=["\']' + re.escape(url) + r'["\'][^>]*>\s*' + re.escape(label_html) + r'\s*</a>'
            if not re.search(pattern, container, re.I):
                errors.append(f"{name}: label '{label}' missing expected link {url}")

    for index, row in enumerate(rows, 1):
        visible = text_only(row)
        has_change = re.search(r"[+-]?\d[\d,.]*(?:%|bp)", visible, re.I)
        has_explicit_status = any(marker in visible for marker in ("休市", "待核實", "暫缺"))
        if not has_change and not has_explicit_status:
            errors.append(f"{name}: row {index} has neither a numeric change nor an explicit status: {visible[:100]}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", required=True, help="Report HTML to validate")
    parser.add_argument("--mapping", default=str(Path(__file__).with_name("tac_market_field_map.json")))
    args = parser.parse_args()
    source = Path(args.html).read_text(encoding="utf-8")
    mapping = json.loads(Path(args.mapping).read_text(encoding="utf-8"))
    errors: list[str] = []
    print("TAC market field contract")
    print(f"HTML: {args.html}")
    for name, spec in mapping["sections"].items():
        section_errors = check_section(name, spec, source)
        if section_errors:
            errors.extend(section_errors)
            print(f"FAIL {name}")
        else:
            print(f"PASS {name}: {spec['expected_count']} rows")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        print("MARKET FIELD CONTRACT FAILED")
        return 1
    print("MARKET FIELD CONTRACT PASSED (structure only; not quote/date/source verification)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
