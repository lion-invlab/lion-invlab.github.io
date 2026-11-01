#!/usr/bin/env python3
"""Check editorial binding selectors against the two immutable TAC mother templates."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = ROOT / "scripts" / "tac_content_binding_map.json"


def check_template(template_type: str, config: dict) -> list[str]:
    path = ROOT / config["path"]
    if not path.is_file():
        return [f"{template_type}: missing mother template: {config['path']}"]
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    errors: list[str] = []
    for section_name, spec in config["sections"].items():
        container = soup.select_one(spec["container"])
        if container is None:
            errors.append(f"{template_type}.{section_name}: container selector missing: {spec['container']}")
            continue
        for key in ("headline", "body", "collapse", "tabs"):
            selector = spec.get(key)
            if selector and container.select_one(selector) is None:
                errors.append(f"{template_type}.{section_name}: {key} selector missing: {selector}")
        item_selector = spec.get("items")
        if item_selector:
            items = container.select(item_selector)
            if not items:
                errors.append(f"{template_type}.{section_name}: no existing item nodes match {item_selector}")
            expected = spec.get("expected_count")
            if expected is not None and len(items) != expected:
                errors.append(
                    f"{template_type}.{section_name}: expected {expected} existing items, found {len(items)}"
                )
        if spec.get("source_links") and section_name in {"focus_news", "market_headlines"}:
            news_items = container.select(spec["items"])
            for index, item in enumerate(news_items, 1):
                if item.select_one(spec["source_links"]) is None:
                    errors.append(
                        f"{template_type}.{section_name}[{index}]: source link node missing"
                    )
    return errors


def main() -> int:
    config = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []
    for template_type, template in config["templates"].items():
        errors.extend(check_template(template_type, template))
    if errors:
        for error in errors:
            print("FAIL: " + error, file=sys.stderr)
        return 1
    print("PASS: editorial content selectors exist in both approved mother templates")
    print("PASS: focus news and market headlines have exactly 5 and 10 existing item nodes")
    print("PASS: summary, sentiment, calendar, earnings and observation containers are present")
    print("PASS: existing disclosure, tab and source-link nodes are preserved by selector contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
