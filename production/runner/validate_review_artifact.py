#!/usr/bin/env python3
"""Independent fail-closed validation for the exact main production review HTML artifact."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from bs4 import BeautifulSoup, Comment

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "production" / "runner"))
from build_review_html import validate_political_scan
MANIFEST_PATH = ROOT / "production/config/mother-template-manifest.json"
BUILDER_PATH = ROOT / "production/runner/build_review_html.py"
QA_CONTRACT_PATH = ROOT / "production/contracts/MOTHER_TEMPLATE_QA.md"
ACTIVE_RULES_PATH = ROOT / "production/MASTER_WR.md"
CANDIDATE_RULES_PATH = ROOT / "production/reference/SIM-1.4_SOURCE_BASELINE.md"


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
    report_path_arg = Path(args.report)
    if (report_path_arg.name != "review.html"
            or report_path_arg.parent.parent != Path("production/runs")
            or not report_path_arg.parent.name.startswith(f"TAC-{report_date.isoformat()}-")):
        raise SystemExit("review path must be production/runs/TAC-<report-date>-<run-id>/review.html")
    report_path = ROOT / report_path_arg
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
    template_path = template["path"]
    template_bytes = (ROOT / template_path).read_bytes()
    template_sha = git_blob_sha(template_bytes)
    if template_sha != template["blob_sha"]:
        raise SystemExit("approved production mother SHA mismatch")
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
        "mode": "main-production",
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
        "manifest": ("manifest_path", "manifest_blob_sha", "production/config/mother-template-manifest.json"),
        "qa_contract": ("qa_contract_path", "qa_contract_blob_sha", "production/contracts/MOTHER_TEMPLATE_QA.md"),
        "active_rules": ("active_rules_path", "active_rules_blob_sha", "production/MASTER_WR.md"),
        "candidate_rules": ("candidate_rules_path", "candidate_rules_blob_sha", "production/reference/SIM-1.4_SOURCE_BASELINE.md"),
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
    if template["blob_sha"].encode("ascii") not in asset_bytes["qa_contract"]:
        raise SystemExit("QA Contract does not bind the selected production mother SHA")
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
    if not fixture_path.startswith("production/runs/"):
        raise SystemExit("fixture provenance path outside current production Run")
    fixture_file = ROOT / fixture_path
    if not fixture_file.is_file():
        raise SystemExit(f"current Run fixture is missing: {fixture_path}")
    fixture_bytes = fixture_file.read_bytes()
    if git_blob_sha(fixture_bytes) != provenance.get("fixture_blob_sha"):
        raise SystemExit("fixture provenance SHA does not match immutable build commit")
    fixture = json.loads(fixture_bytes)
    # Fail closed when the same CNN Fear & Greed observation is rendered
    # consistently. A pending provider response may contain a diagnostic or
    # previous-close cross-check score; that value is not an approved current
    # close and must never be promoted into the report.
    fg_record = fixture.get("risk", {}).get("fear_greed", {})
    fg_display = str(fg_record.get("display", "")).strip()
    fg_source = fg_record.get("source", {})
    fg_status = str(fg_source.get("verification_status", "")).upper()
    if not fg_display:
        raise SystemExit("CNN Fear & Greed display field missing from fixture")
    fg_card = soup.select_one("#sentiment .cnn-fg-preview .fg6-score-main")
    fg_marker = soup.select_one("#sentiment .cnn-fg-preview .fg6-marker")
    if fg_card is None or fg_card.get_text(strip=True) != fg_display:
        raise SystemExit("rendered CNN Fear & Greed numeric card differs from fixture display")
    if fg_marker is None:
        raise SystemExit("rendered CNN Fear & Greed scale marker missing")
    sentiment_section = soup.select_one("#sentiment")
    sentiment_text = sentiment_section.get_text(" ", strip=True) if sentiment_section else ""
    sentiment_cards = sentiment_section.select(".sbox") if sentiment_section else []
    if not sentiment_cards:
        raise SystemExit("rendered sentiment core-interpretation card is missing")
    core_interpretation = sentiment_cards[-1].get_text(" ", strip=True)
    market_paragraphs = fixture.get("market_analysis", {}).get("markets", {}).get("paragraphs", [])
    rendered_market_paragraphs = [
        node.get_text(" ", strip=True)
        for node in soup.select('#market-analysis [data-analysis-layer="markets"] [data-analysis-content="markets"] > p')
        if "market-analysis-sources" not in node.get("class", [])
    ]
    if fg_status == "VERIFIED":
        if fg_source.get("read_method")=="CNN_OFFICIAL_PREVIOUS_CLOSE":
            raise SystemExit("CNN previous_close must never be substituted for the current Fear & Greed dashboard score")
        if fg_source.get("quote_type")!="cnn_fear_greed_current_score" or fg_source.get("url") not in (fg_source.get("approved_primary_urls") or []):
            raise SystemExit("VERIFIED Fear & Greed must use the approved CNN current-dashboard source")
        fg_source_value = fg_source.get("source_score_value")
        if fg_source_value is None:
            raise SystemExit("CNN Fear & Greed verified source score missing from fixture")
        try:
            canonical_fg = str(int(float(fg_source_value) + 0.5))
        except (TypeError, ValueError):
            raise SystemExit("CNN Fear & Greed source score is not numeric")
        if canonical_fg != fg_display:
            raise SystemExit(f"CNN Fear & Greed fixture display {fg_display!r} differs from rounded official source score {canonical_fg!r}")
        expected_fg_phrase = f"Fear & Greed {fg_display}"
        if expected_fg_phrase not in str(fixture.get("sentiment", "")):
            raise SystemExit("fixture sentiment interpretation does not match canonical CNN Fear & Greed score")
        if not market_paragraphs or any(("Fear & Greed" in str(p) and expected_fg_phrase not in str(p)) for p in market_paragraphs):
            raise SystemExit("fixture market-analysis Fear & Greed reference differs from canonical CNN score")
        if str(fg_marker.get("data-score", "")).strip() != fg_display:
            raise SystemExit("rendered CNN Fear & Greed scale marker differs from canonical fixture score")
        if expected_fg_phrase not in sentiment_text or expected_fg_phrase not in core_interpretation:
            raise SystemExit("rendered sentiment interpretation differs from canonical CNN Fear & Greed score")
        if re.search(r"Fear\\s*&\\s*Greed\\s+(?!"+re.escape(fg_display)+r"(?:\\D|$))\\d+", core_interpretation):
            raise SystemExit("rendered sentiment core-interpretation card contains a stale CNN Fear & Greed score")
        if not rendered_market_paragraphs or any(("Fear & Greed" in p and expected_fg_phrase not in p) for p in rendered_market_paragraphs):
            raise SystemExit("rendered market-analysis Fear & Greed reference differs from canonical CNN score")
    elif fg_status == "BACKUP_VERIFIED":
        backup_value = fg_source.get("backup_source_score_value")
        if backup_value is None:
            raise SystemExit("CNN Fear & Greed backup verification requires backup_source_score_value")
        try:
            canonical_fg = str(int(float(backup_value) + 0.5))
        except (TypeError, ValueError):
            raise SystemExit("CNN Fear & Greed backup source score is not numeric")
        if canonical_fg != fg_display:
            raise SystemExit(f"CNN Fear & Greed backup display {fg_display!r} differs from backup source score {canonical_fg!r}")
        if str(fg_source.get("source_role", "")).upper() not in ("BACKUP_1", "BACKUP_2", "BACKUP", "SECONDARY"):
            raise SystemExit("CNN Fear & Greed BACKUP_VERIFIED status requires an explicit backup source role")
        if fg_source.get("source_score_value") is not None:
            raise SystemExit("CNN Fear & Greed backup status must not retain an unmapped official CNN source score")
        if fg_source.get("observation_record_status") != "VERIFIED" or fg_source.get("display_value_matches_saved_observation") is not True or not fg_source.get("verified_at_tw"):
            raise SystemExit("CNN Fear & Greed BACKUP_VERIFIED requires a verified current-run observation record, matching saved display value and verification timestamp")
        cross_check = fg_source.get("cross_check") or {}
        if cross_check.get("status") != "DATE_MAPPING_UNRESOLVED":
            raise SystemExit("CNN Fear & Greed backup status must disclose unresolved official-source date mapping")
        backup_url=str(fg_source.get("url",""))
        if "fgscore.com" in backup_url:
            backup_name="FGScore"
            expected_role="BACKUP_1"
        elif "fcontext.com" in backup_url:
            backup_name="Financial Context"
            expected_role="BACKUP_2"
        else:
            raise SystemExit("CNN Fear & Greed backup must use an approved FGScore or Financial Context provider")
        if str(fg_source.get("source_role","")).upper()!=expected_role:
            raise SystemExit("CNN Fear & Greed backup role does not match its approved provider tier")
        if backup_name not in str(fg_source.get("name","")):
            raise SystemExit("CNN Fear & Greed backup source name does not match its provider URL")
        if backup_name not in str(fixture.get("sentiment","")) or "備援" not in str(fixture.get("sentiment","")) or fg_display not in str(fixture.get("sentiment","")):
            raise SystemExit("backup CNN Fear & Greed sentiment must disclose the provider, backup status and score")
        if not market_paragraphs or not any("Fear & Greed" in str(p) and backup_name in str(p) and "備援" in str(p) and fg_display in str(p) for p in market_paragraphs):
            raise SystemExit("backup CNN Fear & Greed market analysis must disclose the provider and score")
        if str(fg_marker.get("data-score", "")).strip() != fg_display:
            raise SystemExit("rendered backup CNN Fear & Greed scale marker differs from the verified backup score")
        for label, rendered in (("sentiment", sentiment_text), ("core interpretation", core_interpretation)):
            if "Fear & Greed" not in rendered or backup_name not in rendered or "備援" not in rendered or fg_display not in rendered:
                raise SystemExit(f"rendered {label} must identify the CNN Fear & Greed backup score")
        if not rendered_market_paragraphs or not any("Fear & Greed" in p and backup_name in p and "備援" in p and fg_display in p for p in rendered_market_paragraphs):
            raise SystemExit("rendered market analysis must identify the CNN Fear & Greed backup score")
    elif fg_status in ("PENDING","TOOL_READ_FAILURE","SOURCE_NO_DATA","DATE_MISMATCH"):
        if fg_display != "待核實":
            raise SystemExit("pending CNN Fear & Greed observation must remain visibly 待核實")
        if fg_source.get("verified_at_tw") or fg_source.get("verification_status") != fg_status:
            raise SystemExit("unresolved CNN Fear & Greed source carries contradictory verification metadata")
        if fg_source.get("source_score_value") is not None or fg_source.get("backup_source_score_value") is not None:
            raise SystemExit("unresolved CNN Fear & Greed must not retain an unverified numeric score")
        if "待核實" not in str(fixture.get("sentiment", "")) or "不沿用" not in str(fixture.get("sentiment", "")):
            raise SystemExit("pending CNN Fear & Greed sentiment must explain the unverified value and reject stale carry-forward")
        if not market_paragraphs or not any("Fear & Greed" in str(p) and ("未能核實" in str(p) or "待核實" in str(p)) for p in market_paragraphs):
            raise SystemExit("pending CNN Fear & Greed market analysis must explicitly disclose the unavailable current observation")
        if str(fg_marker.get("data-score", "")).strip() or "none" not in str(fg_marker.get("style", "")).lower() or fg_marker.get("aria-hidden") != "true":
            raise SystemExit("pending CNN Fear & Greed marker must be hidden rather than positioned using an unverified score")
        if "Fear & Greed" not in sentiment_text or "待核實" not in sentiment_text:
            raise SystemExit("rendered sentiment section must disclose pending CNN Fear & Greed status")
        if "Fear & Greed" not in core_interpretation or "待核實" not in core_interpretation:
            raise SystemExit("rendered sentiment core-interpretation card must disclose pending CNN Fear & Greed status")
        if not rendered_market_paragraphs or not any("Fear & Greed" in p and ("未能核實" in p or "待核實" in p) for p in rendered_market_paragraphs):
            raise SystemExit("rendered market analysis must disclose pending CNN Fear & Greed status")
    else:
        raise SystemExit(f"unsupported CNN Fear & Greed verification status: {fg_status!r}")
    political_scan_receipt = validate_political_scan(fixture)
    expected_layers = [
        ("political", "一、政治與地緣政治局勢"),
        ("policy_industry", "二、政策傳導與企業／產業鏈影響"),
        ("macro", "三、宏觀經濟傳導"),
        ("markets", "四、金融市場定價、情緒與風險"),
        ("strategy", "五、機構資金動向與投資策略"),
    ]
    summary_card = soup.select_one("#overview > section.grid.two > article.card.bluf")
    if summary_card is None:
        raise SystemExit("summary card missing from review")
    if summary_card.select("a, details.source-details, details.market-analysis-source-details, .source, .source-list, .summary-source, .summary-sources, p.market-analysis-sources") or "資料來源" in summary_card.get_text(" ", strip=True):
        raise SystemExit("summary card exposes forbidden visible source disclosure")
    if provenance.get("summary_source_receipt") != {"visible_sources": False}:
        raise SystemExit("internal summary source-removal receipt missing or invalid")

    # The focus panel must be fully refreshed; merely appending today's summary
    # while leaving old mother-template market text is not an acceptable review.
    focus_market = soup.select_one(".focus-panel.focus-market .key")
    observation = fixture.get("observation") or {}
    observation_text = str(observation.get("text") or "").strip()
    observation_heading = str(observation.get("heading") or "盤面觀察重點").strip()
    if focus_market is None or not observation_text:
        raise SystemExit("盤面觀察重點 focus panel or current summary text missing")
    bold_slots = focus_market.find_all("b")
    point_slots = max(0, len(bold_slots) - 1)
    observation_points = observation.get("points") or []
    if point_slots and len(observation_points) != point_slots:
        raise SystemExit(f"focus panel point count {len(observation_points)} does not match mother slots {point_slots}")
    expected_focus_parts = [observation_heading + " ｜", observation_text]
    if point_slots:
        for point in observation_points:
            label = str(point.get("label") or "").strip()
            point_text = str(point.get("text") or "").strip()
            if not label or not point_text:
                raise SystemExit("focus panel observation point requires label and text")
            expected_focus_parts.extend([label + "：", point_text])
    expected_focus_text = re.sub(r"\s+", " ", " ".join(expected_focus_parts)).strip()
    actual_focus_text = re.sub(r"\s+", " ", focus_market.get_text(" ", strip=True)).strip()
    if actual_focus_text != expected_focus_text:
        raise SystemExit("rendered 盤面觀察重點 contains stale mother text or differs from the current fixture")

    # Two approved cards must display the exact two-outcome FedWatch distribution,
    # including two hikes when that is what the market snapshot contains.
    fedwatch_payload = fixture.get("fedwatch") or {}
    fedwatch_outcomes = fedwatch_payload.get("probabilities") or []
    if len(fedwatch_outcomes) == 2:
        fed_rows = soup.select("#fed .fc-prob")
        fed_bar = soup.select_one("#fed .fc-split-bar")
        if len(fed_rows) != 2 or fed_bar is None or fed_bar.has_attr("hidden"):
            raise SystemExit("valid two-outcome FedWatch snapshot is still rendered as pending")
        label_map = {
            "hold": "維持不變", "維持利率": "維持不變", "維持利率不變": "維持不變", "維持不變": "維持不變",
            "hike": "升息", "升息": "升息", "cut": "降息", "降息": "降息",
            "升息25個基點": "升息25個基點", "升息50個基點": "升息50個基點",
            "降息25個基點": "降息25個基點", "降息50個基點": "降息50個基點",
        }
        for row, outcome in zip(fed_rows, fedwatch_outcomes):
            label = label_map.get(str(outcome.get("outcome") or "").strip())
            probability = f'{float(outcome.get("probability", 0)):.1f}%'
            rate_range = str(outcome.get("rate_range") or "").strip()
            rendered = row.get_text(" ", strip=True)
            if not label or label not in rendered or probability not in rendered or rate_range not in rendered or "待核實" in rendered:
                raise SystemExit(f"FedWatch card does not render the validated outcome: {outcome}")
        aria = str(fed_bar.get("aria-label") or "")
        for outcome in fedwatch_outcomes:
            label = label_map.get(str(outcome.get("outcome") or "").strip())
            probability = f'{float(outcome.get("probability", 0)):.1f}%'
            if not label or label not in aria or probability not in aria:
                raise SystemExit("FedWatch split-bar accessible label differs from the validated distribution")
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
        if content.select("a, details.market-analysis-source-details, .source, .source-list, .market-analysis-sources") or "資料來源" in content.get_text(" ", strip=True):
            raise SystemExit(f"rendered market_analysis.{key} exposes forbidden visible source disclosure")
        receipt = provenance.get("market_analysis_slot_receipt", {})
        receipt_layers = {item.get("key"): item for item in receipt.get("layers", [])}
        layer_receipt = receipt_layers.get(key)
        if not isinstance(layer_receipt, dict):
            raise SystemExit(f"internal market_analysis.{key} evidence receipt missing")
        expected_sources = [
            {
                "label": str(src.get("label") or "").strip(),
                "url": str(src.get("url") or "").strip(),
                "status": str(src.get("status") or "").strip(),
                "published_at": str(src.get("published_at") or "").strip() or None,
                "checked_at": str(src.get("checked_at") or "").strip() or None,
            }
            for src in payload["sources"]
        ]
        if layer_receipt.get("source_count") != len(expected_sources) or layer_receipt.get("sources") != expected_sources:
            raise SystemExit(f"internal market_analysis.{key} source evidence receipt differs from fixture")
    builder_bytes = git_show(build_commit, provenance["builder_path"])
    if git_blob_sha(builder_bytes) != provenance.get("builder_blob_sha"):
        raise SystemExit("builder provenance SHA does not match immutable build commit")
    main_commit = provenance.get("calendar_main_commit_sha", "")
    if not re.fullmatch(r"[0-9a-f]{40}", main_commit):
        raise SystemExit("authoritative main calendar commit SHA missing")
    current_path = provenance.get("calendar_current_path", "")
    previous_path = provenance.get("calendar_previous_path")
    current_raw = git_show(main_commit, current_path)
    current_payload = json.loads(current_raw)
    if git_blob_sha(current_raw) != provenance.get("calendar_current_blob_sha"):
        raise SystemExit("current calendar database SHA mismatch")
    previous_blob_sha = provenance.get("calendar_previous_blob_sha")
    previous_payload = None
    if previous_path:
        if not previous_blob_sha:
            raise SystemExit("previous calendar path is present without its pinned blob SHA")
        previous_raw = git_show(main_commit, previous_path)
        previous_payload = json.loads(previous_raw)
        if git_blob_sha(previous_raw) != previous_blob_sha:
            raise SystemExit("previous calendar database SHA mismatch")
    elif provenance.get("template_key") == "monday":
        raise SystemExit("Monday template requires the previous-week calendar path and SHA")
    elif previous_blob_sha:
        raise SystemExit("previous calendar SHA is present without its path")
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
        "political_geopolitical_scan": political_scan_receipt["status"],
        "political_domains_checked": political_scan_receipt["domains_checked"],
        "political_event_status_classifications": political_scan_receipt["event_status_classifications"],
        "policy_transmission_completeness": political_scan_receipt["policy_transmission_completeness"],
        "scenario_analysis_coverage": political_scan_receipt["scenario_analysis_coverage"],
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
