#!/usr/bin/env python3
"""Independent fail-closed validation for the exact simulation review HTML artifact."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import subprocess
from datetime import date
from pathlib import Path
from bs4 import BeautifulSoup, Comment

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "simulation-lab/baseline/mother-template-manifest.json"
BUILDER_PATH = ROOT / "simulation-lab/runner/build_review_html.py"
QA_CONTRACT_PATH = ROOT / "simulation-lab/baseline/mother-template-qa-contract.md"
ACTIVE_RULES_PATH = ROOT / "simulation-lab/TAC_WORK_RULES_SIM.md"
CANDIDATE_RULES_PATH = ROOT / "simulation-lab/TAC_WORK_RULES_SIM_1.4_DRAFT.md"


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def git_show(commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{commit}:{path}"], check=True, capture_output=True
    ).stdout


def direct_child(node, tag: str, cls: str):
    return [x for x in node.find_all(tag, recursive=False) if cls in x.get("class", [])]


def validate_card(card, context: str, toggle_class: str):
    details = direct_child(card, "div", "econ-details")
    if len(details) != 1:
        raise ValueError(f"{context}: expected one direct .econ-details, got {len(details)}")
    detail = details[0]
    children = detail.find_all("div", recursive=False)
    if len(children) != 3 or "econ-primary-grid" not in children[0].get("class", []):
        raise ValueError(f"{context}: details must contain primary-grid, impact, source as three direct children")
    grid, impact, source = children
    expected = [
        ("econ-prev", "前值"),
        ("econ-forecast", "市場預估"),
        ("econ-actual", "實際"),
    ]
    fields = direct_child(grid, "div", "econ-field")
    actual = []
    for field in fields:
        actual.append(next((c for c, _ in expected if c in field.get("class", [])), "unknown"))
    if actual != [c for c, _ in expected]:
        raise ValueError(f"{context}: comparison field order/classes invalid: {actual}")
    for field, (_, label) in zip(fields, expected):
        label_node = field.find("label", recursive=False)
        if label_node is None or label_node.get_text(strip=True) != label:
            raise ValueError(f"{context}: label mismatch for {label}")
        if len(direct_child(field, "div", "econ-value")) != 1:
            raise ValueError(f"{context}: .econ-value missing/duplicated for {label}")
    for field, cls, label in (
        (impact, "econ-impact", "市場影響"),
        (source, "econ-source", "資料來源"),
    ):
        label_node = field.find("label", recursive=False)
        if cls not in field.get("class", []) or "wide" not in field.get("class", []):
            raise ValueError(f"{context}: {label} must use .{cls}.wide")
        if label_node is None or label_node.get_text(strip=True) != label:
            raise ValueError(f"{context}: {label} label missing or out of order")
        if len(direct_child(field, "div", "econ-value")) != 1:
            raise ValueError(f"{context}: {label} .econ-value missing/duplicated")
    source_value = direct_child(source, "div", "econ-value")[0]
    if not source_value.find("a", href=re.compile(r"^https://")):
        raise ValueError(f"{context}: HTTPS source link missing")
    summary = card.find_all("summary", recursive=False)
    if len(summary) != 1:
        raise ValueError(f"{context}: summary missing")
    toggles = [x for x in summary[0].find_all("span", recursive=False) if toggle_class in x.get("class", [])]
    if len(toggles) != 1:
        raise ValueError(f"{context}: expected one direct .{toggle_class} control")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--report-date", required=True)
    args = ap.parse_args()
    report_date = date.fromisoformat(args.report_date)
    if report_date.weekday() > 4:
        raise SystemExit("weekend report date rejected")
    expected_path = f"preview/{report_date.isoformat()}-simulation.html"
    if args.report != expected_path:
        raise SystemExit(f"review path must be the canonical simulation preview: {expected_path}")
    report_path = ROOT / args.report
    if not report_path.is_file():
        raise SystemExit(f"review artifact missing: {args.report}")
    raw = report_path.read_bytes()
    soup = BeautifulSoup(raw, "html.parser")
    meta = soup.select_one('meta[name="report-date"]')
    if meta is None or meta.get("content") != report_date.isoformat():
        raise SystemExit("report-date metadata missing or mismatched")
    template_key = "monday" if report_date.weekday() == 0 else "weekdays"
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    template = manifest["templates"][template_key]
    template_path = template["simulation_path"]
    template_bytes = (ROOT / template_path).read_bytes()
    template_sha = git_blob_sha(template_bytes)
    if template_sha != template["simulation_blob_sha"]:
        raise SystemExit("approved simulation mother SHA mismatch")
    provenance_comment = next(
        (str(x) for x in soup.find_all(string=lambda x: isinstance(x, Comment) and "TAC_BUILD_PROVENANCE" in str(x))),
        None,
    )
    if not provenance_comment:
        raise SystemExit("TAC_BUILD_PROVENANCE comment missing; this artifact is not traceably assembled")
    match = re.search(r"TAC_BUILD_PROVENANCE\s+(\{.*\})", provenance_comment, re.S)
    if not match:
        raise SystemExit("TAC_BUILD_PROVENANCE JSON malformed")
    provenance = json.loads(match.group(1))
    expected_provenance = {
        "report_date": report_date.isoformat(),
        "template_key": template_key,
        "template_path": template_path,
        "template_blob_sha": template_sha,
        "builder_path": str(BUILDER_PATH.relative_to(ROOT)),
        "mode": "simulation-only",
    }
    for key, value in expected_provenance.items():
        if provenance.get(key) != value:
            raise SystemExit(f"provenance mismatch {key}: {provenance.get(key)!r} != {value!r}")
    build_commit = provenance.get("build_commit_sha", "")
    if not re.fullmatch(r"[0-9a-f]{40}", build_commit):
        raise SystemExit("immutable build commit SHA missing from provenance")
    subprocess.run(["git", "merge-base", "--is-ancestor", build_commit, "HEAD"], check=True)
    # Verify the exact rules and QA assets used by the immutable build commit.
    asset_specs = {
        "manifest": ("manifest_path", "manifest_blob_sha", "simulation-lab/baseline/mother-template-manifest.json"),
        "qa_contract": ("qa_contract_path", "qa_contract_blob_sha", "simulation-lab/baseline/mother-template-qa-contract.md"),
        "active_rules": ("active_rules_path", "active_rules_blob_sha", "simulation-lab/TAC_WORK_RULES_SIM.md"),
        "candidate_rules": ("candidate_rules_path", "candidate_rules_blob_sha", "simulation-lab/TAC_WORK_RULES_SIM_1.4_DRAFT.md"),
    }
    asset_bytes = {}
    for label, (path_key, sha_key, expected_path) in asset_specs.items():
        if provenance.get(path_key) != expected_path:
            raise SystemExit(f"{label} provenance path missing or outside the approved path: {provenance.get(path_key)!r}")
        payload = git_show(build_commit, expected_path)
        actual_sha = git_blob_sha(payload)
        if actual_sha != provenance.get(sha_key):
            raise SystemExit(f"{label} provenance SHA mismatch: {actual_sha} != {provenance.get(sha_key)!r}")
        asset_bytes[label] = payload
    if template["simulation_blob_sha"].encode("ascii") not in asset_bytes["qa_contract"]:
        raise SystemExit("QA Contract does not bind the selected simulation mother SHA")
    active_rules_text = asset_bytes["active_rules"].decode("utf-8")
    candidate_rules_text = asset_bytes["candidate_rules"].decode("utf-8")
    active_header = active_rules_text[:700]
    candidate_header = candidate_rules_text[:700]
    # SIM-1.4 is now the sole active rule. The former SIM-1.4 draft is
    # retained only as a superseded provenance artifact, not as a second
    # active candidate. Validate lifecycle identity instead of the retired
    # SIM-1.3 / DRAFT pairing.
    if "SIM-1.4" not in active_header or "正式生效版" not in active_header or "ACTIVE／正式生效" not in active_header:
        raise SystemExit("active rules must identify SIM-1.4 as the sole formally active version")
    if "SIM-1.4" not in candidate_header or "SUPERSEDED" not in candidate_header or "不得作為執行規則" not in candidate_header:
        raise SystemExit("historical SIM-1.4 draft must be explicitly superseded and non-executable")
    fixture_path = provenance.get("fixture_path", "")
    if not fixture_path.startswith("simulation-lab/fixtures/report-data-"):
        raise SystemExit("fixture provenance path outside approved simulation fixtures")
    fixture_bytes = git_show(build_commit, fixture_path)
    if git_blob_sha(fixture_bytes) != provenance.get("fixture_blob_sha"):
        raise SystemExit("fixture provenance SHA does not match immutable build commit")
    fixture = json.loads(fixture_bytes)
    expected_layers = [
        ("political", "一、政治與地緣政治局勢"),
        ("policy_industry", "二、政策傳導與企業／產業鏈影響"),
        ("macro", "三、宏觀經濟傳導"),
        ("markets", "四、金融市場定價、情緒與風險"),
        ("strategy", "五、機構資金動向與投資策略"),
    ]
    analysis_payload = fixture.get("market_analysis")
    if not isinstance(analysis_payload, dict) or set(analysis_payload) != {key for key, _ in expected_layers}:
        raise SystemExit("fixture market_analysis must contain exactly the five required layers")
    analysis_container = soup.select_one("#market-analysis")
    if analysis_container is None or analysis_container.parent is not soup.select_one("#overview"):
        raise SystemExit("five-layer market analysis container missing or misplaced")
    rendered_layers = analysis_container.select(":scope > .market-analysis-layer")
    rendered_order = [(node.get("data-analysis-layer"), node.find(["h2", "h3", "h4"], recursive=False).get_text(" ", strip=True) if node.find(["h2", "h3", "h4"], recursive=False) else "") for node in rendered_layers]
    if rendered_order != expected_layers:
        raise SystemExit(f"five-layer market analysis order mismatch: {rendered_order}")
    for key, title in expected_layers:
        payload = analysis_payload[key]
        if not isinstance(payload, dict) or not isinstance(payload.get("paragraphs"), list) or not payload["paragraphs"] or not isinstance(payload.get("sources"), list) or not payload["sources"]:
            raise SystemExit(f"fixture market_analysis.{key} lacks paragraphs or source evidence")
        section = analysis_container.select_one(f'[data-analysis-layer="{key}"]')
        content = section.select_one(f'[data-analysis-content="{key}"]') if section else None
        if content is None:
            raise SystemExit(f"rendered market_analysis.{key} content slot missing")
        actual_paragraphs = [p.get_text(" ", strip=True) for p in content.find_all("p", recursive=False) if "market-analysis-sources" not in p.get("class", [])]
        expected_paragraphs = [str(p).strip() for p in payload["paragraphs"]]
        if actual_paragraphs != expected_paragraphs:
            raise SystemExit(f"rendered market_analysis.{key} paragraphs differ from fixture")
        source_line = content.select_one("p.market-analysis-sources")
        if source_line is None:
            raise SystemExit(f"rendered market_analysis.{key} source list missing")
        actual_sources = [(a.get_text(" ", strip=True), a.get("href")) for a in source_line.select("a[href]")]
        expected_sources = [(str(src.get("label") or "").strip(), str(src.get("url") or "").strip()) for src in payload["sources"]]
        if actual_sources != expected_sources:
            raise SystemExit(f"rendered market_analysis.{key} source links differ from fixture")
    builder_bytes = git_show(build_commit, provenance["builder_path"])
    if git_blob_sha(builder_bytes) != provenance.get("builder_blob_sha"):
        raise SystemExit("builder provenance SHA does not match immutable build commit")
    main_commit = provenance.get("calendar_main_commit_sha", "")
    if not re.fullmatch(r"[0-9a-f]{40}", main_commit):
        raise SystemExit("authoritative main calendar commit SHA missing")
    current_path = provenance.get("calendar_current_path", "")
    previous_path = provenance.get("calendar_previous_path", "")
    current_payload = json.loads(git_show(main_commit, current_path))
    previous_payload = json.loads(git_show(main_commit, previous_path))
    if git_blob_sha(git_show(main_commit, current_path)) != provenance.get("calendar_current_blob_sha"):
        raise SystemExit("current calendar database SHA mismatch")
    if git_blob_sha(git_show(main_commit, previous_path)) != provenance.get("calendar_previous_blob_sha"):
        raise SystemExit("previous calendar database SHA mismatch")
    expected_econ = len(current_payload["events"]["economic"])
    expected_earnings = len(current_payload["events"]["earnings"])
    actual_econ = len(soup.select("#calendar .econ-event"))
    actual_earnings = len(soup.select("#earnings .earnings-accordion"))
    if actual_econ != expected_econ or actual_earnings != expected_earnings:
        raise SystemExit(f"calendar count mismatch: economic {actual_econ}/{expected_econ}; earnings {actual_earnings}/{expected_earnings}")
    cards = soup.select("#calendar .week-econ-panels details.econ-event")
    if not cards:
        raise SystemExit("current-week economic cards missing")
    for i, card in enumerate(cards, 1):
        validate_card(card, f"current-week card #{i}", "econ-toggle")
    previous_cards = []
    if template_key == "monday":
        if not soup.select_one("#last-week-calendar .last-week-calendar-collapse"):
            raise SystemExit("Monday previous-week economic section missing")
        previous_cards = soup.select("#last-week-calendar .last-week-calendar-collapse .econ-event-list details.econ-event")
        if not previous_cards:
            raise SystemExit("Monday previous-week economic cards missing")
        for i, card in enumerate(previous_cards, 1):
            validate_card(card, f"previous-week card #{i}", "econ-event-toggle")
        if soup.select("#last-week-calendar .last-week-calendar-collapse[open]"):
            raise SystemExit("Monday previous-week calendar must be collapsed by default")
    elif soup.select("#last-week-calendar, #last-week-earnings"):
        raise SystemExit("weekday report must not contain Monday-only sections")
    ids = [node.get("id") for node in soup.select("[id]")]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate HTML IDs detected")
    css = "\n".join(node.get_text() for node in soup.select("style"))
    normalized_css = re.sub(r"\s+", " ", css)
    if not re.search(r'grid-template-areas\s*:\s*["\']prev actual["\']\s*["\']forecast actual["\']', normalized_css):
        raise SystemExit("approved five-zone grid areas missing from report CSS")
    required = ["#overview", "#market-analysis", "#sentiment", "#news-scan", "#global-markets", "#industry-bonds-fx-commodities", "#calendar", "#earnings", "#fed", "#view"]
    missing = [selector for selector in required if not soup.select_one(selector)]
    if missing:
        raise SystemExit("required mother sections missing: " + ", ".join(missing))
    print(json.dumps({
        "status": "PASS",
        "report": args.report,
        "report_date": report_date.isoformat(),
        "template": template_key,
        "template_sha": template_sha,
        "manifest_blob_sha": provenance["manifest_blob_sha"],
        "qa_contract_blob_sha": provenance["qa_contract_blob_sha"],
        "active_rules_blob_sha": provenance["active_rules_blob_sha"],
        "candidate_rules_blob_sha": provenance["candidate_rules_blob_sha"],
        "build_commit_sha": build_commit,
        "builder_sha": provenance["builder_blob_sha"],
        "fixture_sha": provenance["fixture_blob_sha"],
        "calendar_main_commit_sha": main_commit,
        "calendar_current_blob_sha": provenance["calendar_current_blob_sha"],
        "calendar_previous_blob_sha": provenance["calendar_previous_blob_sha"],
        "economic_cards": actual_econ,
        "earnings_cards": actual_earnings,
        "previous_week_economic_cards": len(previous_cards),
        "report_git_blob_sha": git_blob_sha(raw),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
