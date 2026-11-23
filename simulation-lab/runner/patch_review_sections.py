#!/usr/bin/env python3
"""Patch one approved report section in an existing review HTML without rebuilding unrelated modules."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
from pathlib import Path

from bs4 import BeautifulSoup

import build_review_html as builder
from earnings_judgment import apply_judgment, audit_record, consensus_evidence_label


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


def patch_last_week_earnings_consensus(soup: BeautifulSoup, data: dict) -> dict:
    """Apply the report-layer W47 consensus evidence to its existing five-star card only."""
    if data.get("report_date") != "2026-11-23" or data.get("last_week_earnings", {}).get("week_id") != "2026-W47":
        raise ValueError("last-week consensus overlay is locked to the 2026-11-23 Monday W47 report")
    candidates = [
        copy.deepcopy(item)
        for item in data.get("last_week_earnings", {}).get("events", [])
        if item.get("ticker") == "NVDA" and item.get("id") == "current-nvda-20261118"
    ]
    if len(candidates) != 1:
        raise ValueError(f"expected exactly one W47 NVDA consensus projection; found {len(candidates)}")
    record = candidates[0]
    if record.get("status") not in ("released", "published", "completed"):
        raise ValueError("W47 NVDA event is not a published result")
    if not record.get("actual_source") or not str(record["actual_source"].get("url") or "").startswith("https://"):
        raise ValueError("W47 NVDA official actual-results source is missing")
    if record.get("actual_source_url") != record["actual_source"]["url"]:
        raise ValueError("W47 NVDA actual source URL fields disagree")

    source = record.get("consensus_source") or {}
    raw_ref = str(source.get("raw_response_ref") or "")
    capture_rel = raw_ref.split("#", 1)[0]
    if not capture_rel:
        raise ValueError("W47 NVDA consensus capture reference is missing")
    capture_path = ROOT / capture_rel
    require_within(capture_path, ROOT / "simulation-lab" / "output", "Yahoo pre-release capture")
    capture_bytes = capture_path.read_bytes()
    capture_sha = subprocess.check_output(
        ["git", "hash-object", str(capture_path)], cwd=ROOT, text=True
    ).strip()
    if capture_sha != source.get("capture_file_blob_sha"):
        raise ValueError("W47 NVDA Yahoo capture Git blob SHA mismatch")
    capture = json.loads(capture_bytes.decode("utf-8"))
    capture_entry = next((x for x in capture.get("entries", []) if x.get("ticker") == "NVDA"), None)
    if capture_entry is None or capture_entry.get("raw_response_sha256") != source.get("raw_response_sha256"):
        raise ValueError("W47 NVDA Yahoo raw response SHA mismatch")
    if capture_entry.get("eps", {}).get("estimate") != record.get("eps_estimate"):
        raise ValueError("W47 NVDA EPS estimate differs from immutable Yahoo capture")
    if abs(float(capture_entry.get("revenue", {}).get("estimate", 0)) / 1_000_000_000 - float(record.get("revenue_estimate", 0))) > 1e-9:
        raise ValueError("W47 NVDA revenue estimate differs from immutable Yahoo capture")
    if consensus_evidence_label(record, "eps") is None or consensus_evidence_label(record, "revenue") is None:
        raise ValueError("W47 NVDA TAC pre-release consensus evidence is not eligible")
    apply_judgment(record, str(data.get("report_cutoff_taipei") or "2026-11-23T05:25:00+08:00"))
    audit_issues = audit_record(record)
    if audit_issues:
        raise ValueError(f"W47 NVDA TAC 1.4 judgment audit failed: {audit_issues}")
    if record.get("eps_comparison_status") not in ("beat", "miss", "inline") or record.get("revenue_comparison_status") not in ("beat", "miss", "inline"):
        raise ValueError("W47 NVDA EPS／Revenue comparison status is incomplete")

    section = builder.unique(soup, "#last-week-earnings", "last-week earnings local patch section")
    cards = section.select("details.earnings-accordion.five-star-earnings")
    matches = [
        card for card in cards
        if "NVDA" in (card.select_one(".earnings-company-sub").get_text(" ", strip=True) if card.select_one(".earnings-company-sub") else "")
    ]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one rendered W47 NVDA five-star card; found {len(matches)}")
    card = matches[0]
    other_cards_before = [str(x) for x in cards if x is not card]

    grid = builder.unique(card, ".earnings-results-grid", "W47 NVDA results grid")
    metric_cards = grid.select(":scope > .earnings-actual-card")
    if len(metric_cards) != 2:
        raise ValueError(f"W47 NVDA results grid must have EPS and revenue cards; found {len(metric_cards)}")
    by_metric = {}
    for metric_card in metric_cards:
        title = metric_card.select_one(".earnings-actual-card-title")
        if title is None:
            raise ValueError("W47 NVDA metric card title missing")
        by_metric[title.get_text(" ", strip=True)] = metric_card
    if set(by_metric) != {"EPS", "營收"}:
        raise ValueError(f"W47 NVDA metric cards are not EPS／營收: {sorted(by_metric)}")

    def update_metric_card(metric_card, metric_key: str, display_key: str, basis_key: str) -> None:
        expected_line = next(
            (line for line in metric_card.select(".earnings-actual-line")
             if line.select_one("span") and line.select_one("span").get_text(" ", strip=True) == "預期"),
            None,
        )
        if expected_line is None:
            raise ValueError(f"W47 NVDA {metric_key} expected-value row missing")
        builder.set_text(builder.unique(expected_line, "strong", f"W47 NVDA {metric_key} estimate"), str(record[display_key]))
        status = str(record[f"{metric_key}_comparison_status"])
        status_tag = builder.unique(metric_card, ".earnings-actual-status", f"W47 NVDA {metric_key} status")
        css_status = {"beat": "beat", "miss": "miss", "inline": "beat"}[status]
        status_tag["class"] = ["earnings-actual-status", css_status]
        builder.set_text(status_tag, builder.earnings_status_label(record, metric_key, status))
        note = builder.unique(metric_card, ".earnings-actual-note", f"W47 NVDA {metric_key} basis note")
        analyst_count = record.get("eps_analyst_count") if metric_key == "eps" else record.get("revenue_analyst_count")
        observation = str(source.get("observed_at_taipei") or "2026-11-15T13:50:45+08:00")
        caveat = str(record.get(basis_key) or "")
        builder.set_text(
            note,
            f"Yahoo Finance Average Estimate｜{analyst_count}位分析師｜公告前觀測 {observation}；{caveat}；數值比較非嚴格同口徑。",
        )
        metric_card["class"] = [x for x in metric_card.get("class", []) if x != "pending"]
        metric_card["data-consensus-overlay"] = "sim14-w47-yahoo"
        metric_card["data-comparison-status"] = status

    update_metric_card(by_metric["EPS"], "eps", "eps_estimate_display", "eps_basis_display")
    update_metric_card(by_metric["營收"], "revenue", "revenue_estimate_display", "revenue_basis_display")

    judgment_field = next(
        (field for field in card.select(".earnings-detail-field")
         if field.select_one("label") and field.select_one("label").get_text(" ", strip=True) == "財報判讀"),
        None,
    )
    if judgment_field is None:
        raise ValueError("W47 NVDA financial judgment detail field missing")
    judgment_value = builder.unique(judgment_field, ".earnings-detail-value", "W47 NVDA financial judgment value")
    old_judgment = judgment_value.get_text(" ", strip=True)
    price_reaction = old_judgment.split("股價反應：", 1)[1].strip() if "股價反應：" in old_judgment else "價格反應資料未提供"
    detail_text = (
        f"EPS：{builder.earnings_status_label(record, 'eps', record['eps_comparison_status'])}，實際2.70美元對平台平均預估{record['eps_estimate']:.5f}美元，"
        f"數值差異{record['eps_surprise_pct']:+.2f}%；營收：{builder.earnings_status_label(record, 'revenue', record['revenue_comparison_status'])}，"
        f"實際1,158億美元對平台平均預估{record['revenue_estimate'] * 10:.4f}億美元，數值差異{record['revenue_surprise_pct']:+.2f}%。"
        f"Yahoo未揭露EPS GAAP／Adjusted、Basic／Diluted細項與Revenue完整定義，以上為平台數值比較，非嚴格同口徑比較。"
        f"股價反應：{price_reaction}"
    )
    builder.set_text(judgment_value, detail_text)

    source_field = next(
        (field for field in card.select(".earnings-detail-field")
         if field.select_one("label") and field.select_one("label").get_text(" ", strip=True) == "來源"),
        None,
    )
    if source_field is None:
        raise ValueError("W47 NVDA source detail field missing")
    source_value = builder.unique(source_field, ".earnings-detail-value", "W47 NVDA source value")
    source_value.clear()
    actual_link = soup.new_tag("a", href=record["actual_source"]["url"])
    actual_link["rel"] = ["noopener"]
    actual_link["target"] = "_blank"
    actual_link.string = record["actual_source"].get("name") or "NVIDIA｜FY2027 Q3 Financial Results"
    source_value.append(actual_link)
    source_value.append(" ｜ ")
    consensus_link = soup.new_tag("a", href=source["url"])
    consensus_link["rel"] = ["noopener"]
    consensus_link["target"] = "_blank"
    consensus_link.string = f"Yahoo Finance Average Estimate｜公告前觀測 {source.get('observed_at_taipei', '')}"
    source_value.append(consensus_link)

    card["data-consensus-overlay"] = "sim14-w47-yahoo"
    other_cards_after = [str(x) for x in section.select("details.earnings-accordion.five-star-earnings") if x is not card]
    if other_cards_before != other_cards_after:
        raise ValueError("non-target W47 five-star earnings cards changed during NVDA consensus overlay")

    return {
        "status": "PASS",
        "event_id": record["id"],
        "ticker": record["ticker"],
        "week_id": data["last_week_earnings"]["week_id"],
        "eps_estimate": record["eps_estimate"],
        "eps_status": record["eps_comparison_status"],
        "revenue_estimate": record["revenue_estimate"],
        "revenue_status": record["revenue_comparison_status"],
        "eps_analyst_count": record["eps_analyst_count"],
        "revenue_analyst_count": record["revenue_analyst_count"],
        "eps_evidence_label": consensus_evidence_label(record, "eps"),
        "revenue_evidence_label": consensus_evidence_label(record, "revenue"),
        "judgment_engine_version": record["judgment_engine_version"],
        "judgment_audit": "PASS",
        "actual_source_url": record["actual_source"]["url"],
        "consensus_source_url": source["url"],
        "observed_at": source.get("observed_at"),
        "observed_at_taipei": source.get("observed_at_taipei"),
        "raw_response_sha256": source.get("raw_response_sha256"),
        "capture_file_blob_sha": capture_sha,
        "price_reaction_preserved": True,
        "non_target_cards_unchanged": True,
        "visible_sources_scope": "W47 NVDA earnings card only; summary and five-layer source display remains hidden",
    }


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
    elif section == "last_week_earnings":
        target_selector = "#last-week-earnings"
    else:
        raise ValueError("section must be summary, market_analysis or last_week_earnings")

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
    elif section == "market_analysis":
        internal_receipt = builder.populate_market_analysis_preserving_dom(soup, data, manifest)
        if internal_receipt.get("visible_sources") is not False:
            raise ValueError("market analysis source visibility contract failed")
    else:
        internal_receipt = patch_last_week_earnings_consensus(soup, data)
        if internal_receipt.get("status") != "PASS":
            raise ValueError("last-week earnings consensus overlay did not PASS")

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
    parser.add_argument("--section", required=True, choices=("summary", "market_analysis", "last_week_earnings"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(patch_section(args.html, args.fixture, args.manifest,
                                   args.section, args.output, args.receipt),
                      ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
