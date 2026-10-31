#!/usr/bin/env python3
"""Validate the approved TAC report market-field contract without modifying HTML."""
from __future__ import annotations
import argparse
import html
import json
import re
import sys
from pathlib import Path

TAG_RE = re.compile(r"<[^>]+>")
ROW_RE = re.compile(r'<(?:div|tr)\\b[^>]*class=["\'][^"\']*\\b{class_name}\\b[^"\']*["\'][^>]*>(.*?)</(?:div|tr)>', re.I | re.S)


def text_only(value: str) -> str:
    return re.sub(r"\\s+", " ", html.unescape(TAG_RE.sub(" ", value))).strip()


def extract_container(source: str, container_id: str) -> str:
    marker = re.search(r'<([a-zA-Z][\\w:-]*)\\b(?=[^>]*\\bid=["\']' + re.escape(container_id) + r'["\'])[^>]*>', source, re.I)
    if not marker:
        raise ValueError(f"container id not found: {container_id}")
    tag = marker.group(1).lower()
    token = re.compile(r"</?" + re.escape(tag) + r"\\b[^>]*>", re.I)
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
    pattern = re.compile(
        r'<([a-zA-Z][\\w:-]*)\\b[^>]*class=["\'][^"\']*\\b' + re.escape(class_name) +
        r'\\b[^"\']*["\'][^>]*>(.*?)</\\1>',
        re.I | re.S,
    )
    return [m.group(2) for m in pattern.finditer(container)]


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
            hits = sum(re.search(r"\\b" + re.escape(ticker) + r"\\b", row) is not None for row in texts)
            if hits != 1:
                errors.append(f"{name}: ticker {ticker} expected exactly once, found {hits}")
    for index, row in enumerate(rows, 1):
        visible = text_only(row)
        if not re.search(r"[+-]?\\d[\\d,.]*(?:%|bp)", visible, re.I):
            errors.append(f"{name}: row {index} has no recognizable numeric change: {visible[:100]}")
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
        print("\\n".join(errors), file=sys.stderr)
        print("MARKET FIELD CONTRACT FAILED")
        return 1
    print("MARKET FIELD CONTRACT PASSED (structure only; not quote/date/source verification)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
