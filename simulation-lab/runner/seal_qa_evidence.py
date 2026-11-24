#!/usr/bin/env python3
"""Seal QA evidence to the exact final review HTML blob for this workflow run."""
import os
import hashlib, json, os, re, subprocess, sys
from datetime import date
from pathlib import Path
from bs4 import BeautifulSoup, Comment
sys.path.insert(0, 'simulation-lab/runner')
from sim14_builder_approval import resolve_from_files
from build_review_html import validate_political_scan
report_path, report_date, evidence_path, patch_receipt_path, patched_output_path = sys.argv[1:]
from datetime import date
is_monday = date.fromisoformat(report_date).weekday() == 0
raw = Path(report_path).read_bytes()
patch_receipt_file = Path(patch_receipt_path)
patched_output_file = Path(patched_output_path)
overlay_receipt_archive_path = f"simulation-lab/runs/last-week-consensus-overlay-{report_date}-{os.environ['GITHUB_RUN_ID']}.json"
report_sha256 = hashlib.sha256(raw).hexdigest()
overlay = {}
calendar_overlay = {}
patch_receipt_bytes = b""
patch_receipt = {}
if is_monday:
    if not patch_receipt_file.is_file() or not patched_output_file.is_file():
        raise SystemExit("Monday W47 overlay receipt or patched output is missing")
    patch_receipt_bytes = patch_receipt_file.read_bytes()
    patch_receipt = json.loads(patch_receipt_bytes.decode("utf-8"))
    patched_output_bytes = patched_output_file.read_bytes()
    patched_output_sha256 = hashlib.sha256(patched_output_bytes).hexdigest()
    if patch_receipt.get("status") != "PASS" or patch_receipt.get("section") != "last_week_earnings_and_calendar_impact":
        raise SystemExit("Monday W47 NVDA and calendar impact overlay receipt did not PASS")
    if patch_receipt.get("output_html_sha256") != patched_output_sha256 or patched_output_sha256 != report_sha256:
        raise SystemExit("Monday W47 overlay receipt is not bound to the exact final review HTML")
    internal_receipt = patch_receipt.get("internal_receipt", {})
    overlay = internal_receipt.get("last_week_earnings", {})
    calendar_overlay = internal_receipt.get("last_week_calendar_impact", {})
    if overlay.get("status") != "PASS" or overlay.get("event_id") != "current-nvda-20261118" or overlay.get("judgment_audit") != "PASS":
        raise SystemExit("Monday W47 NVDA consensus overlay evidence or TAC 1.4 judgment audit is incomplete")
    if calendar_overlay.get("status") != "PASS" or calendar_overlay.get("event_id") != "current-fed-warsh-productivity-jobs-20261117":
        raise SystemExit("Monday W47 Warsh calendar impact overlay evidence is incomplete")
    if calendar_overlay.get("expected_impact_matched_exactly") is not True or calendar_overlay.get("authoritative_main_calendar_modified") is not False:
        raise SystemExit("Monday W47 Warsh calendar impact overlay did not preserve exact-source/read-only guarantees")
    if overlay.get("raw_response_sha256") != "5a20857e65c628b2ce0236b48a1414e8b361eef6e90c446a875b8ed1e3773a2a":
        raise SystemExit("Monday W47 NVDA consensus overlay raw response SHA mismatch")
    if overlay.get("eps_estimate") != 2.47121 or overlay.get("revenue_estimate") != 108.7319039:
        raise SystemExit("Monday W47 NVDA consensus overlay estimates differ from approved pre-release snapshot")
    if overlay.get("eps_status") != "beat" or overlay.get("revenue_status") != "beat":
        raise SystemExit("Monday W47 NVDA consensus overlay comparison statuses are not complete")
else:
    if not patch_receipt_file.is_file() or not patched_output_file.is_file():
        raise SystemExit("Weekday no-overlay receipt or unchanged output copy is missing")
    patch_receipt_bytes = patch_receipt_file.read_bytes()
    patch_receipt = json.loads(patch_receipt_bytes.decode("utf-8"))
    patched_output_bytes = patched_output_file.read_bytes()
    if patch_receipt.get("status") != "NOT_APPLICABLE" or patch_receipt.get("section") != "weekday_no_last_week_overlay":
        raise SystemExit("Weekday report must carry an explicit NOT_APPLICABLE no-overlay receipt")
    if patch_receipt.get("output_html_sha256") != report_sha256 or patched_output_bytes != raw:
        raise SystemExit("Weekday no-overlay receipt must bind to the unchanged report HTML")
soup = BeautifulSoup(raw, "html.parser")
is_monday = date.fromisoformat(report_date).weekday() == 0
patch_receipt_file = Path(patch_receipt_path)
patched_output_file = Path(patched_output_path)
overlay_receipt_archive_path = None
patch_receipt_bytes = b""
patch_receipt = {"status": "NOT_APPLICABLE_WEEKDAY"}
overlay = {}
calendar_overlay = {}
patched_output_sha256 = None
report_sha256 = hashlib.sha256(raw).hexdigest()
if is_monday:
    overlay_receipt_archive_path = f"simulation-lab/runs/last-week-consensus-overlay-{report_date}-{os.environ['GITHUB_RUN_ID']}.json"
    if not patch_receipt_file.is_file() or not patched_output_file.is_file():
        raise SystemExit("Monday W47 NVDA consensus overlay receipt or patched output is missing")
    patch_receipt_bytes = patch_receipt_file.read_bytes()
    patch_receipt = json.loads(patch_receipt_bytes.decode("utf-8"))
    patched_output_bytes = patched_output_file.read_bytes()
    patched_output_sha256 = hashlib.sha256(patched_output_bytes).hexdigest()
    if patch_receipt.get("status") != "PASS" or patch_receipt.get("section") != "last_week_earnings_and_calendar_impact":
        raise SystemExit("W47 NVDA and calendar impact overlay receipt did not PASS")
    if patch_receipt.get("output_html_sha256") != patched_output_sha256 or patched_output_sha256 != report_sha256:
        raise SystemExit("combined W47 overlay receipt is not bound to the exact final review HTML")
    internal_receipt = patch_receipt.get("internal_receipt", {})
    overlay = internal_receipt.get("last_week_earnings", {})
    calendar_overlay = internal_receipt.get("last_week_calendar_impact", {})
    if overlay.get("status") != "PASS" or overlay.get("event_id") != "current-nvda-20261118" or overlay.get("judgment_audit") != "PASS":
        raise SystemExit("W47 NVDA consensus overlay evidence or TAC 1.4 judgment audit is incomplete")
    if calendar_overlay.get("status") != "PASS" or calendar_overlay.get("event_id") != "current-fed-warsh-productivity-jobs-20261117":
        raise SystemExit("W47 Warsh calendar impact overlay evidence is incomplete")
    if calendar_overlay.get("expected_impact_matched_exactly") is not True or calendar_overlay.get("authoritative_main_calendar_modified") is not False:
        raise SystemExit("W47 Warsh calendar impact overlay did not preserve exact-source/read-only guarantees")
    if overlay.get("raw_response_sha256") != "5a20857e65c628b2ce0236b48a1414e8b361eef6e90c446a875b8ed1e3773a2a":
        raise SystemExit("W47 NVDA consensus overlay raw response SHA mismatch")
    if overlay.get("eps_estimate") != 2.47121 or overlay.get("revenue_estimate") != 108.7319039:
        raise SystemExit("W47 NVDA consensus overlay estimates differ from approved pre-release snapshot")
    if overlay.get("eps_status") != "beat" or overlay.get("revenue_status") != "beat":
        raise SystemExit("W47 NVDA consensus overlay comparison statuses are not complete")
comment = next((str(x) for x in soup.find_all(string=lambda x: isinstance(x, Comment) and "TAC_BUILD_PROVENANCE" in str(x))), None)
if not comment: raise SystemExit("missing TAC_BUILD_PROVENANCE")
match = re.search(r"TAC_BUILD_PROVENANCE\s+(\{.*\})", comment, re.S)
if not match: raise SystemExit("malformed TAC_BUILD_PROVENANCE")
provenance = json.loads(match.group(1))
# SIM-1.3 G1: Monday has three fixed summary sections; weekdays use a concise daily market judgment.
fixture_path = Path(f"simulation-lab/fixtures/report-data-{report_date}.json")
fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
bluf = soup.select_one("#overview > section.grid.two > article.card.bluf")
if bluf is None:
    raise SystemExit("content analysis gate: summary card missing")
title_node = bluf.select_one("h1")
summary_body = bluf.select_one(".key, .bluf-content, p")
if title_node is None or title_node.get_text(" ", strip=True) != fixture.get("summary_title"):
    raise SystemExit("content analysis gate: summary headline mismatch")
if summary_body is None:
    raise SystemExit("content analysis gate: summary body missing")
summary_text = summary_body.get_text(" ", strip=True)
summary_points = fixture.get("summary_points", [])
if not isinstance(summary_points, list) or not summary_points:
    raise SystemExit("content analysis gate: summary points missing")
if is_monday:
    required_labels = ["上週主軸", "風險觀察", "操作建議"]
    if [x.get("label") for x in summary_points] != required_labels:
        raise SystemExit(
            f"content analysis gate: Monday summary labels must be {required_labels}; "
            f"got {[x.get('label') for x in summary_points]}"
        )
for point in summary_points:
    if not point.get("text") or point["text"] not in summary_text:
        raise SystemExit(f"content analysis gate: summary point not rendered: {point.get('label')}")
if is_monday:
    risk_text = summary_points[1]["text"]
    if not re.search(r"11/\d{1,2}", risk_text) or not re.search(r"\d{1,2}:\d{2}", risk_text):
        raise SystemExit("content analysis gate: Monday risk observation must include a dated and timed upcoming catalyst")
    action = summary_points[2]["text"]
    if not any(token in action for token in ("偏多", "偏空", "中性", "防禦")):
        raise SystemExit("content analysis gate: Monday operation plan must state an investment stance")
    if not any(token in action for token in ("加碼", "提高風險承擔", "降低曝險", "減碼")):
        raise SystemExit("content analysis gate: Monday operation plan must state an executable portfolio action")
    if not any(token in action for token in ("若", "只有", "當")):
        raise SystemExit("content analysis gate: Monday operation plan must include conditional triggers")
market_comments = fixture.get("market_comments", {})
def normalize_analysis_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()
def comment_body(value):
    text = str(value or "")
    return text.split("｜", 1)[1].strip() if "｜" in text else text.strip()
region_rows = [
    ("#tac-global-panel-0", 0, "美股"),
    ("#tac-global-panel-1", 1, "亞股"),
    ("#tac-global-panel-2", 3, "歐股"),
]
for selector, index, label in region_rows:
    panel = soup.select_one(selector)
    note = panel.select_one(".market-reason") if panel else None
    expected = market_comments.get("global_markets", [])[index]
    if note is None or normalize_analysis_text(comment_body(expected)) not in normalize_analysis_text(note.get_text(" ", strip=True)):
        raise SystemExit(f"content analysis gate: {label} commentary not rendered in its correct panel")
# Legacy region slots must not retain cross-region commentary.
for selector, index, label in (("#asia", 1, "亞洲舊槽位"), ("#tac-region-panel-2", 3, "歐洲舊槽位")):
    panel = soup.select_one(selector)
    note = panel.select_one(".market-reason") if panel else None
    expected = market_comments.get("global_markets", [])[index]
    if note is not None and comment_body(expected) not in note.get_text(" ", strip=True):
        raise SystemExit(f"content analysis gate: {label} contains stale or mismapped commentary")
asset_rows = [
    ("#tac-assets-panel-0", "sectors", "產業"),
    ("#bonds", "bonds", "債券"),
    ("#fx", "fx", "匯率"),
    ("#tac-assets-panel-3", "energy", "原油"),
    ("#tac-assets-panel-4", "metals", "貴金屬"),
]
for selector, key, label in asset_rows:
    panel = soup.select_one(selector)
    note = panel.select_one(".market-reason") if panel else None
    expected = market_comments.get(key, "")
    if not expected or note is None or normalize_analysis_text(comment_body(expected)) not in normalize_analysis_text(note.get_text(" ", strip=True)):
        raise SystemExit(f"content analysis gate: {label} commentary missing or not rendered")
    action_cues = ("操作", "投資含意", "投資應對", "策略", "配置", "避免", "防守", "觀察", "追蹤", "評估")
    if not any(token in expected for token in action_cues):
        raise SystemExit(f"content analysis gate: {label} commentary lacks an investment response")
    if re.search(r"\d+(?:\.\d+)?%", expected):
        raise SystemExit(f"content analysis gate: {label} commentary repeats a percentage quote")
observation = fixture.get("observation", {})
observation_text = observation.get("text", "") if isinstance(observation, dict) else str(observation)
market_panel = soup.select_one(".focus-panel.focus-market")
if not observation_text or market_panel is None or observation_text not in market_panel.get_text(" ", strip=True):
    raise SystemExit("content analysis gate: market observation missing from rendered focus panel")
if not any(token in observation_text for token in ("投資決策", "操作", "配置")) or not any(token in observation_text for token in ("若", "如果")):
    raise SystemExit("content analysis gate: market observation lacks decision implication or invalidation condition")
sentiment = fixture.get("sentiment", "")
sentiment_panel = soup.select_one("#sentiment")
if not sentiment or sentiment_panel is None or sentiment not in sentiment_panel.get_text(" ", strip=True):
    raise SystemExit("content analysis gate: market sentiment interpretation missing")
expected_analysis_layers = [
    ("political", "一、政治與地緣政治局勢"),
    ("policy_industry", "二、政策傳導與企業／產業鏈影響"),
    ("macro", "三、宏觀經濟傳導"),
    ("markets", "四、金融市場定價、情緒與風險"),
    ("strategy", "五、機構資金動向與投資策略"),
]
analysis_payload = fixture.get("market_analysis", {})
def flatten_analysis_text(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [part for item in value.values() for part in flatten_analysis_text(item)]
    if isinstance(value, list):
        return [part for item in value for part in flatten_analysis_text(item)]
    return []
analysis_text_parts = [summary_text]
analysis_text_parts.extend(flatten_analysis_text(market_comments))
analysis_text_parts.extend(flatten_analysis_text(observation_text))
analysis_text_parts.extend(flatten_analysis_text(sentiment))
analysis_text_parts.extend(flatten_analysis_text(analysis_payload))
for forbidden_phrase in ("後續觀察", "值得持續關注", "市場仍需觀察", "審慎觀望"):
    if any(forbidden_phrase in part for part in analysis_text_parts):
        raise SystemExit(
            f"content analysis gate: generic non-actionable conclusion remains in summary/deep-analysis sections: {forbidden_phrase}"
        )
analysis_container = soup.select_one("#market-analysis")
if is_monday:
    nvda_card_matches = [
        card for card in soup.select("#last-week-earnings details.earnings-accordion.five-star-earnings")
        if "NVDA" in (card.select_one(".earnings-company-sub").get_text(" ", strip=True) if card.select_one(".earnings-company-sub") else "")
    ]
    if len(nvda_card_matches) != 1:
        raise SystemExit(f"W47 NVDA five-star card missing or duplicated: {len(nvda_card_matches)}")
    nvda_card = nvda_card_matches[0]
    if nvda_card.get("data-consensus-overlay") != "sim14-w47-yahoo":
        raise SystemExit("W47 NVDA consensus overlay marker missing from rendered HTML")
    metric_cards = {
        card.select_one(".earnings-actual-card-title").get_text(" ", strip=True): card
        for card in nvda_card.select(".earnings-actual-card")
        if card.select_one(".earnings-actual-card-title")
    }
    if set(metric_cards) != {"EPS", "營收"}:
        raise SystemExit("W47 NVDA EPS／營收 metric cards are incomplete")
    for key, expected in (("EPS", "US$2.47"), ("營收", "US$108.73B")):
        metric_card = metric_cards[key]
        if expected not in metric_card.get_text(" ", strip=True):
            raise SystemExit(f"W47 NVDA {key} estimate was not rendered")
        status_node = metric_card.select_one(".earnings-actual-status")
        if status_node is None or "優於預期" not in status_node.get_text(" ", strip=True):
            raise SystemExit(f"W47 NVDA {key} comparison status was not rendered")
        if "非嚴格同口徑" not in metric_card.get_text(" ", strip=True):
            raise SystemExit(f"W47 NVDA {key} basis caveat is missing")
    nvda_judgment = next(
        (field.select_one(".earnings-detail-value") for field in nvda_card.select(".earnings-detail-field")
         if field.select_one("label") and field.select_one("label").get_text(" ", strip=True) == "財報判讀"),
        None,
    )
    if nvda_judgment is None or not all(term in nvda_judgment.get_text(" ", strip=True) for term in ("9.26%", "6.50%", "非嚴格同口徑比較", "-2.89%")):
        raise SystemExit("W47 NVDA judgment, basis caveat or first-session price reaction is incomplete")
    nvda_sources = next(
        (field.select_one(".earnings-detail-value") for field in nvda_card.select(".earnings-detail-field")
         if field.select_one("label") and field.select_one("label").get_text(" ", strip=True) == "來源"),
        None,
    )
    if nvda_sources is None or not nvda_sources.select_one('a[href="https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Announces-Financial-Results-for-Third-Quarter-Fiscal-2027/"]') or not nvda_sources.select_one('a[href="https://finance.yahoo.com/quote/NVDA/analysis/"]'):
        raise SystemExit("W47 NVDA official actual or Yahoo consensus source link missing")
    
if analysis_container is None or analysis_container.parent is not soup.select_one("#overview"):
    raise SystemExit("content analysis gate: five-layer article container missing or misplaced")
rendered_layers = analysis_container.select(":scope > .market-analysis-layer")
actual_layers = [(node.get("data-analysis-layer"), node.find(["h2", "h3", "h4"], recursive=False).get_text(" ", strip=True) if node.find(["h2", "h3", "h4"], recursive=False) else "") for node in rendered_layers]
if actual_layers != expected_analysis_layers:
    raise SystemExit(f"content analysis gate: five-layer order mismatch: {actual_layers}")
for key, heading in expected_analysis_layers:
    payload = analysis_payload.get(key)
    if not isinstance(payload, dict) or not payload.get("paragraphs") or not payload.get("sources"):
        raise SystemExit(f"content analysis gate: market_analysis.{key} lacks paragraphs or sources")
    section = analysis_container.select_one(f'[data-analysis-layer="{key}"]')
    content = section.select_one(f'[data-analysis-content="{key}"]') if section else None
    if content is None:
        raise SystemExit(f"content analysis gate: market_analysis.{key} content slot missing")
    rendered_paragraphs = [p.get_text(" ", strip=True) for p in content.find_all("p", recursive=False) if "market-analysis-sources" not in p.get("class", [])]
    if rendered_paragraphs != [str(p).strip() for p in payload["paragraphs"]]:
        raise SystemExit(f"content analysis gate: market_analysis.{key} text differs from fixture")
    if content.select("a[href], details, .source, .source-list, .market-analysis-sources") or "資料來源" in content.get_text(" ", strip=True):
        raise SystemExit(f"content analysis gate: market_analysis.{key} exposes forbidden visible source disclosure")
    expected_sources = [(str(src.get("label") or "").strip(), str(src.get("url") or "").strip()) for src in payload["sources"]]
    if not expected_sources or any(not label or not url.startswith("https://") for label, url in expected_sources):
        raise SystemExit(f"content analysis gate: market_analysis.{key} internal source evidence is incomplete")
political_scan_receipt = validate_political_scan(fixture)
for i, comment in enumerate(market_comments.get("global_markets", [])):
    if i in (0, 1, 3) and re.search(r"\d+(?:\.\d+)?%", comment):
        raise SystemExit(f"content analysis gate: regional commentary {i} repeats a percentage quote")
    action_cues = ("投資含意", "操作", "投資應對", "策略", "配置", "避免", "防守", "觀察", "追蹤", "評估")
    if i in (0, 1, 3) and not any(token in comment for token in action_cues):
        raise SystemExit(f"content analysis gate: regional commentary {i} lacks an investment response")
analysis_sections_checked = ["summary", "political_geopolitical", "policy_industry", "macro_transmission", "financial_market_pricing", "institutional_flows_strategy", "market_sentiment", "market_observation", "US", "Asia", "Europe", "sectors", "bonds", "FX", "energy", "metals"]
unsupported_causal_claims = []
duplicate_quote_restatements = []
actionability_findings = []
interaction_path = Path("simulation-lab/output/interaction-smoke.json")
visual_path = Path("simulation-lab/output/visual/visual-regression.json")
interaction = json.loads(interaction_path.read_text(encoding="utf-8"))
visual = json.loads(visual_path.read_text(encoding="utf-8"))
if interaction.get("status") != "PASS" or interaction.get("page_errors"):
    raise SystemExit("interaction evidence is not PASS")
if visual.get("failures") or visual.get("report_date") != report_date:
    raise SystemExit("visual evidence is not PASS or report date mismatch")
expected_widths = [1440, 768, 412, 390, 360, 320]
actual_widths = [v.get("width") for v in visual.get("viewports", [])]
if actual_widths != expected_widths:
    raise SystemExit(f"visual viewport evidence mismatch: {actual_widths}")
blockers = provenance.get("review_ready_blockers", [])
data_review_ready = bool(provenance.get("review_ready", not blockers)) and (not is_monday or patch_receipt.get("status") == "PASS")
approval = resolve_from_files("simulation-lab/TAC_WORK_RULES_SIM.md", provenance["builder_path"])
if approval["active_rules_blob_sha"] != provenance["active_rules_blob_sha"]:
    raise SystemExit("active SIM-1.4 approval resolver SHA differs from build provenance")
if approval["actual_builder_blob_sha"] != provenance["builder_blob_sha"]:
    raise SystemExit("Builder SHA differs between approval resolver and build provenance")
sim14_blockers = list(blockers)
if approval["decision"] != "APPROVED":
    sim14_blockers.append("Builder path/SHA has no explicit approval in active SIM-1.4 §8.1")
sim14_review_ready = approval["decision"] == "APPROVED" and data_review_ready and not blockers and (not is_monday or overlay.get("status") == "PASS")
data_audit = provenance.get("data_audit", {})
market_snapshot_audit_path = Path("simulation-lab/output/market-snapshot-audit.json")
if not market_snapshot_audit_path.is_file():
    raise SystemExit("44-row market metadata/date audit receipt missing")
market_snapshot_audit = json.loads(market_snapshot_audit_path.read_text(encoding="utf-8"))
if market_snapshot_audit.get("status") != "PASS":
    raise SystemExit("44-row market metadata/date audit did not PASS")
if market_snapshot_audit.get("source_pages_fetched") is not False or market_snapshot_audit.get("displayed_values_independently_reconciled") is not False:
    raise SystemExit("metadata/date-only audit must not claim live source fetching or independent numeric reconciliation")
market_snapshot_audit_sha256 = hashlib.sha256(market_snapshot_audit_path.read_bytes()).hexdigest()
market_source_manifest_path = Path("simulation-lab/output/market-source-verification-manifest.json")
if not market_source_manifest_path.is_file():
    raise SystemExit("44-row prior-observation verification manifest missing")
market_source_manifest = json.loads(market_source_manifest_path.read_text(encoding="utf-8"))
market_source_rows = market_source_manifest.get("rows", [])
verified_rows = [row for row in market_source_rows if row.get("verification_status") in {"VERIFIED", "BACKUP_VERIFIED"}]
closed_rows = [row for row in market_source_rows if row.get("verification_status") == "CLOSED"]
pending_rows = [row for row in market_source_rows if row.get("verification_status") == "PENDING_CURRENT_RUN_BROWSER_OBSERVATION"]
expected_manifest_status = "PASS" if len(verified_rows) == 44 else "PARTIAL" if verified_rows else "PENDING"
if (
    len(market_source_rows) != 44
    or market_source_manifest.get("row_count") != 44
    or market_source_manifest.get("verified_count") != len(verified_rows)
    or market_source_manifest.get("closed_count") != len(closed_rows)
    or market_source_manifest.get("pending_count") != len(pending_rows)
    or len(verified_rows) + len(closed_rows) + len(pending_rows) != 44
    or market_source_manifest.get("status") != expected_manifest_status
):
    raise SystemExit("44-row source-observation manifest status/counts do not reconcile")
if market_source_manifest.get("observation_record_hash_missing_count") != 0:
    raise SystemExit("verified market observations have missing record hashes")
allowed_source_provenance = {"CURRENT_RUN_BROWSER_OBSERVATION", "CURRENT_CHATGPT_WEB_OPEN_OBSERVATION", "CURRENT_CNN_OFFICIAL_API_OBSERVATION"}
if any(
    not row.get("observation_record_sha256")
    or row.get("source_page_fetched") is not True
    or row.get("display_value_reconciled") is not True
    or row.get("observation_provenance") not in allowed_source_provenance
    for row in verified_rows
):
    raise SystemExit("verified market rows lack current-session source evidence or hashes")
if any(row.get("display_value_reconciled") is True for row in pending_rows):
    raise SystemExit("pending/closed market rows must not claim numeric reconciliation")
market_source_manifest_sha256 = hashlib.sha256(market_source_manifest_path.read_bytes()).hexdigest()
prebuild_receipt_path = Path("simulation-lab/output/prebuild-stage-input-receipt.json")
if not prebuild_receipt_path.is_file():
    raise SystemExit("pre-build Stage 2-4 input receipt missing")
prebuild_receipt = json.loads(prebuild_receipt_path.read_text(encoding="utf-8"))
prebuild_receipt_sha256 = hashlib.sha256(prebuild_receipt_path.read_bytes()).hexdigest()
if prebuild_receipt.get("status") != "PASS" or prebuild_receipt.get("gate") != "PRE_BUILD_STAGE_2_TO_4_INPUT_RECEIPT":
    raise SystemExit("pre-build Stage 2-4 input receipt did not PASS")
if prebuild_receipt.get("report_date") != report_date or prebuild_receipt.get("branch") != "simulation/tac-process-lab-2026-11-06":
    raise SystemExit("pre-build receipt report date or branch mismatch")
if prebuild_receipt.get("workflow_run_id") != os.environ.get("GITHUB_RUN_ID") or prebuild_receipt.get("workflow_run_attempt") != os.environ.get("GITHUB_RUN_ATTEMPT"):
    raise SystemExit("pre-build receipt belongs to a different workflow run/attempt")
if prebuild_receipt.get("fixture", {}).get("sha256") != hashlib.sha256(fixture_path.read_bytes()).hexdigest():
    raise SystemExit("pre-build receipt fixture SHA differs from Builder input")
if prebuild_receipt.get("stage_2_market", {}).get("audit_sha256") != market_snapshot_audit_sha256:
    raise SystemExit("pre-build receipt market audit SHA differs from QA input")
if prebuild_receipt.get("stage_2_market", {}).get("manifest_sha256") != market_source_manifest_sha256:
    raise SystemExit("pre-build receipt source manifest SHA differs from QA input")
calendar_receipt = prebuild_receipt.get("stage_3_calendar", {})
if calendar_receipt.get("main_commit_sha") != provenance.get("calendar_main_commit_sha"):
    raise SystemExit("pre-build receipt main calendar commit differs from Builder provenance")
if calendar_receipt.get("current", {}).get("blob_sha") != provenance.get("calendar_current_blob_sha") or calendar_receipt.get("previous", {}).get("blob_sha") != provenance.get("calendar_previous_blob_sha"):
    raise SystemExit("pre-build receipt calendar blob SHA differs from Builder provenance")
market_source_summary = {
    "status": market_source_manifest.get("status"),
    "row_count": market_source_manifest.get("row_count"),
    "verified_count": market_source_manifest.get("verified_count"),
    "pending_count": market_source_manifest.get("pending_count"),
    "closed_count": market_source_manifest.get("closed_count"),
    "prior_observation_reused_count": market_source_manifest.get("prior_observation_reused_count"),
    "observation_record_hash_missing_count": market_source_manifest.get("observation_record_hash_missing_count"),
    "raw_response_sha256_saved_count": market_source_manifest.get("raw_response_sha256_saved_count"),
    "source_pages_fetched": market_source_manifest.get("source_pages_fetched"),
    "displayed_values_independently_reconciled": market_source_manifest.get("displayed_values_independently_reconciled"),
    "verification_scope": market_source_manifest.get("verification_scope"),
}
evidence = {
    "status": "QA_PASSED",
    "review_ready": data_review_ready and sim14_review_ready,
    "review_ready_blockers": blockers,
    "last_week_earnings_overlay_receipt_path": str(patch_receipt_file) if is_monday else None,
    "last_week_earnings_overlay_receipt_archive_path": overlay_receipt_archive_path,
    "last_week_earnings_overlay_receipt_sha256": hashlib.sha256(patch_receipt_bytes).hexdigest() if is_monday else None,
    "last_week_earnings_overlay_receipt_git_blob_sha": subprocess.check_output(["git", "hash-object", str(patch_receipt_file)], text=True).strip() if is_monday else None,
    "last_week_earnings_overlay": {"status": "NOT_APPLICABLE_WEEKDAY"} if not is_monday else {
        "status": overlay.get("status"),
        "event_id": overlay.get("event_id"),
        "ticker": overlay.get("ticker"),
        "eps_estimate": overlay.get("eps_estimate"),
        "eps_status": overlay.get("eps_status"),
        "revenue_estimate": overlay.get("revenue_estimate"),
        "revenue_status": overlay.get("revenue_status"),
        "judgment_engine_version": overlay.get("judgment_engine_version"),
        "judgment_audit": overlay.get("judgment_audit"),
        "raw_response_sha256": overlay.get("raw_response_sha256"),
        "capture_file_blob_sha": overlay.get("capture_file_blob_sha"),
        "non_target_cards_unchanged": overlay.get("non_target_cards_unchanged")
    },
    "last_week_calendar_impact_overlay": {"status": "NOT_APPLICABLE_WEEKDAY"} if not is_monday else {
        "status": calendar_overlay.get("status"),
        "event_id": calendar_overlay.get("event_id"),
        "expected_impact_matched_exactly": calendar_overlay.get("expected_impact_matched_exactly"),
        "source_url": calendar_overlay.get("source_url"),
        "report_layer_only": calendar_overlay.get("report_layer_only"),
        "authoritative_main_calendar_modified": calendar_overlay.get("authoritative_main_calendar_modified")
    },
    "data_audit": data_audit,
    "market_snapshot_audit_path": str(market_snapshot_audit_path),
    "market_snapshot_audit_scope": market_snapshot_audit.get("verification_scope"),
    "market_snapshot_audit_sha256": market_snapshot_audit_sha256,
    "market_source_verification_manifest_path": str(market_source_manifest_path),
    "market_source_verification_manifest_sha256": market_source_manifest_sha256,
    "market_source_verification_summary": market_source_summary,
    "prebuild_input_receipt_path": str(prebuild_receipt_path),
    "prebuild_input_receipt_sha256": prebuild_receipt_sha256,
    "prebuild_input_receipt": prebuild_receipt,
    "branch": "simulation/tac-process-lab-2026-11-06",
    "report_path": report_path,
    "report_date": report_date,
    "report_git_blob_sha": subprocess.check_output(["git", "hash-object", report_path], text=True).strip(),
    "report_sha256": hashlib.sha256(raw).hexdigest(),
    "build_commit_sha": provenance["build_commit_sha"],
    "builder_blob_sha": provenance["builder_blob_sha"],
    "fixture_blob_sha": provenance["fixture_blob_sha"],
    "template_blob_sha": provenance["template_blob_sha"],
    "manifest_blob_sha": provenance["manifest_blob_sha"],
    "qa_contract_blob_sha": provenance["qa_contract_blob_sha"],
    "active_rules_blob_sha": provenance["active_rules_blob_sha"],
    "candidate_rules_blob_sha": provenance["candidate_rules_blob_sha"],
    "candidate_builder_path": provenance["builder_path"],
    "candidate_builder_blob_sha": provenance["builder_blob_sha"],
    "data_review_ready": data_review_ready,
    "content_analysis_gate": "PASS",
    "analysis_sections_checked": analysis_sections_checked,
    "political_geopolitical_scan": political_scan_receipt["status"],
    "political_domains_checked": political_scan_receipt["domains_checked"],
    "political_event_status_classifications": political_scan_receipt["event_status_classifications"],
    "policy_transmission_completeness": political_scan_receipt["policy_transmission_completeness"],
    "scenario_analysis_coverage": political_scan_receipt["scenario_analysis_coverage"],
    "political_scan_no_material_change_note": political_scan_receipt["no_material_change_note"],
    "unsupported_causal_claims": unsupported_causal_claims,
    "duplicate_quote_restatements": duplicate_quote_restatements,
    "actionability_findings": actionability_findings,
    "sim14_builder_approval": approval["decision"],
    "sim14_review_ready": sim14_review_ready,
    "sim14_blockers": sim14_blockers,
    "builder_approval_record": approval,
    "calendar_main_commit_sha": provenance["calendar_main_commit_sha"],
    "calendar_current_blob_sha": provenance["calendar_current_blob_sha"],
    "calendar_previous_blob_sha": provenance["calendar_previous_blob_sha"],
    "interaction_evidence_sha256": hashlib.sha256(interaction_path.read_bytes()).hexdigest(),
    "visual_evidence_sha256": hashlib.sha256(visual_path.read_bytes()).hexdigest(),
    "viewports": actual_widths,
    "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
    "workflow_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT")
}
Path(evidence_path).write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(evidence, ensure_ascii=False, indent=2))
