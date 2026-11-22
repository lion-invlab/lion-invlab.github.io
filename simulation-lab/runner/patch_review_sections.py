#!/usr/bin/env python3
"""Patch only the summary or five-layer analysis slots in an existing review HTML."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

from bs4 import BeautifulSoup

import build_review_html as builder


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def outside_target_dom(soup: BeautifulSoup, selector: str) -> str:
    clone = copy.deepcopy(soup)
    targets = clone.select(selector)
    if len(targets) != 1:
        raise ValueError(f"expected exactly one target {selector!r}; found {len(targets)}")
    targets[0].decompose()
    return str(clone)


ROOT = Path(__file__).resolve().parents[2]


def require_within(path: Path, root: Path, label: str) -> None:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} must remain inside {root}") from exc


def patch_section(html_path: Path, fixture_path: Path, manifest_path: Path,
                  section: str, output_path: Path, receipt_path: Path,
                  test_only: bool = False) -> dict:
    if not test_only:
        output_root = ROOT / "simulation-lab" / "output"
        require_within(html_path, output_root, "input review HTML")
        require_within(output_path, output_root, "output review HTML")
        require_within(receipt_path, output_root, "local patch receipt")
        require_within(fixture_path, ROOT / "simulation-lab" / "fixtures", "Fixture")
        require_within(manifest_path, ROOT / "simulation-lab" / "baseline", "Manifest")
        resolved_paths = [html_path.resolve(), output_path.resolve(), receipt_path.resolve()]
        if len(set(resolved_paths)) != 3:
            raise ValueError("input HTML, output HTML and patch receipt must use three distinct paths")
    source_bytes = html_path.read_bytes()
    fixture_bytes = fixture_path.read_bytes()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    data = json.loads(fixture_bytes.decode("utf-8"))
    soup = BeautifulSoup(source_bytes, "lxml")

    if section == "summary":
        target_selector = "#overview > section.grid.two > article.card.bluf"
    elif section == "market_analysis":
        target_selector = "#market-analysis"
    else:
        raise ValueError("section must be summary or market_analysis")

    before_outside = outside_target_dom(soup, target_selector)
    if section == "summary":
        card = builder.unique(soup, target_selector, "summary local patch target")
        content = builder.unique(card, ".key, .bluf-content, p", "summary local patch content")
        title = builder.validate_summary_title(data.get("summary_title"))
        builder.set_text(builder.unique(card, "h1", "summary local patch headline"), title)
        count = builder.populate_summary_points_preserving_dom(content, data.get("summary_points"))
        summary_source_receipt = builder.remove_visible_sources_from_summary(card)
        internal_receipt = {
            "section": "summary",
            "summary_title": title,
            "summary_point_count": count,
            "summary_source_receipt": summary_source_receipt,
            "fixture_source_fields_retained": True,
        }
    else:
        internal_receipt = builder.populate_market_analysis_preserving_dom(soup, data, manifest)
        if internal_receipt.get("visible_sources") is not False:
            raise ValueError("market analysis source visibility contract failed")

    after_outside = outside_target_dom(soup, target_selector)
    if before_outside != after_outside:
        raise ValueError("non-target DOM changed during local section patch")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_bytes = str(soup).encode("utf-8")
    output_path.write_bytes(output_bytes)
    result = {
        "status": "PASS",
        "mode": "local_dom_patch",
        "section": section,
        "target_selector": target_selector,
        "input_html_path": str(html_path),
        "input_html_sha256": sha256_bytes(source_bytes),
        "output_html_path": str(output_path),
        "output_html_sha256": sha256_bytes(output_bytes),
        "fixture_path": str(fixture_path),
        "fixture_sha256": sha256_bytes(fixture_bytes),
        "manifest_path": str(manifest_path),
        "non_target_dom_unchanged": True,
        "full_report_rebuild": False,
        "market_data_refresh": False,
        "news_refresh": False,
        "calendar_refresh": False,
        "internal_receipt": internal_receipt,
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", required=True, type=Path)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--section", required=True, choices=("summary", "market_analysis"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(patch_section(args.html, args.fixture, args.manifest,
                                   args.section, args.output, args.receipt),
                      ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
