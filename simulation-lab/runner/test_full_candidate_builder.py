#!/usr/bin/env python3
"""Exercise the complete candidate Builder with clearly synthetic five-layer content and output-only paths."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
from bs4 import BeautifulSoup, Comment

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "simulation-lab" / "runner"
OUT = ROOT / "simulation-lab" / "output" / "candidate-validation"
FIXTURES = OUT / "fixtures"
FIXTURES.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(RUNNER))
import build_review_html as builder

manifest = json.loads((ROOT / "simulation-lab/baseline/mother-template-manifest.json").read_text(encoding="utf-8"))
domains = ["us_policy", "us_china", "geopolitics", "trade_sanctions", "major_economies", "energy_resources"]
layers = [
    ("political", "一、政治與地緣政治局勢"),
    ("policy_industry", "二、政策傳導與企業／產業鏈影響"),
    ("macro", "三、宏觀經濟傳導"),
    ("markets", "四、金融市場定價、情緒與風險"),
    ("strategy", "五、機構資金動向與投資策略"),
]
cases = [
    ("2026-11-23", "monday", "report-data-2026-11-23.json"),
    ("2026-11-20", "weekdays", "report-data-2026-11-20.json"),
]
outputs = []
for report_date, template_key, source_name in cases:
    source = ROOT / "simulation-lab" / "fixtures" / source_name
    data = json.loads(source.read_text(encoding="utf-8"))
    data["review_ready_blockers"] = list(data.get("review_ready_blockers", [])) + ["CANDIDATE_TEST_ONLY_SYNTHETIC_ANALYSIS"]
    data["market_analysis"] = {
        key: {
            "paragraphs": [
                f"{title}｜合成 Builder 整合測試內容，僅用於驗證既有母版槽位、段落生成、來源連結與響應式排版，不代表真實市場評論。",
                f"{title}｜測試內容包含長中文文字、條件與風險敘述，驗證桌機與手機版換行，不得作為正式早報資料。",
            ],
            "sources": [{
                "label": "合成測試來源（非正式資料）",
                "url": f"https://example.com/candidate-test/{key}",
                "published_at": "2026-11-22T08:00:00+08:00",
                "checked_at": "2026-11-22T08:10:00+08:00",
                "status": "TEST_ONLY",
            }],
        }
        for key, title in layers
    }
    data["political_scan"] = {
        "checked_at": "2026-11-22T08:10:00+08:00",
        "domains_checked": domains,
        "findings": [],
        "no_material_change_note": "合成測試：六領域掃描欄位完整；此文字不代表真實政治／地緣政治研究結論。",
    }
    fixture_path = FIXTURES / f"report-data-{report_date}-candidate.json"
    fixture_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output_path = OUT / f"{report_date}-candidate.html"
    expected_sha = manifest["templates"][template_key]["simulation_blob_sha"]
    command = [
        sys.executable,
        str(RUNNER / "build_review_html.py"),
        "--data", str(fixture_path.relative_to(ROOT)),
        "--output", str(output_path.relative_to(ROOT)),
        "--expected-master-sha", expected_sha,
        "--candidate-test-output",
    ]
    print("RUN:", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)
    if not output_path.exists():
        raise SystemExit(f"candidate Builder did not create {output_path}")
    soup = BeautifulSoup(output_path.read_text(encoding="utf-8"), "html.parser")
    article = soup.select_one("#market-analysis")
    if article is None:
        raise SystemExit(f"{template_key}: candidate Builder output missing #market-analysis")
    actual = [
        (node.get("data-analysis-layer"), node.find(["h2", "h3", "h4"], recursive=False).get_text(" ", strip=True))
        for node in article.select(":scope > .market-analysis-layer")
    ]
    expected = [(key, title) for key, title in layers]
    if actual != expected:
        raise SystemExit(f"{template_key}: candidate Builder output layer order mismatch: {actual}")
    for key, _ in layers:
        content = article.select_one(f'[data-analysis-content="{key}"]')
        if content is None or content.select("a, details.market-analysis-source-details, .source, .source-list, .market-analysis-sources") or "資料來源" in content.get_text(" ", strip=True):
            raise SystemExit(f"{template_key}: analysis layer {key} exposes forbidden visible source disclosure")
    summary = soup.select_one("#overview > section.grid.two > article.card.bluf")
    if summary is None or summary.select("a, details.source-details, details.market-analysis-source-details") or "資料來源" in summary.get_text(" ", strip=True):
        raise SystemExit(f"{template_key}: summary exposes forbidden visible source disclosure")
    provenance_comment = next(
        (str(x) for x in soup.find_all(string=lambda x: isinstance(x, Comment) and "TAC_BUILD_PROVENANCE" in str(x))),
        None,
    )
    if not provenance_comment:
        raise SystemExit(f"{template_key}: candidate Builder provenance comment missing")
    import re
    match = re.search(r"TAC_BUILD_PROVENANCE\s+(\{.*\})", provenance_comment, re.S)
    if not match:
        raise SystemExit(f"{template_key}: candidate Builder provenance JSON malformed")
    provenance = json.loads(match.group(1))
    if provenance.get("summary_source_receipt") != {"visible_sources": False}:
        raise SystemExit(f"{template_key}: summary source-removal receipt missing")
    analysis_receipt = provenance.get("market_analysis_slot_receipt", {})
    receipt_layers = {item.get("key"): item for item in analysis_receipt.get("layers", [])}
    for key, _ in layers:
        layer = receipt_layers.get(key)
        if not isinstance(layer, dict) or layer.get("source_count", 0) < 1 or not layer.get("sources"):
            raise SystemExit(f"{template_key}: internal source evidence missing for {key}")
    if "candidate-validation-only" not in output_path.read_text(encoding="utf-8"):
        # Provenance is JSON-escaped in the embedded HTML; still require the mode marker.
        raise SystemExit(f"{template_key}: output lacks candidate-validation-only provenance marker")
    if "CANDIDATE_TEST_ONLY_SYNTHETIC_ANALYSIS" not in output_path.read_text(encoding="utf-8"):
        raise SystemExit(f"{template_key}: synthetic-only blocker missing; candidate output could be mistaken for production")
    mother_path = ROOT / "simulation-lab" / "baseline" / (
        "monday-mother-template.html" if template_key == "monday" else "weekday-mother-template.html"
    )
    subprocess.run([
        sys.executable, str(RUNNER / "validate_mother_dom_contract.py"),
        "--mother", str(mother_path.relative_to(ROOT)),
        "--report", str(output_path.relative_to(ROOT)),
        "--template", template_key,
    ], cwd=ROOT, check=True)
    outputs.append(str(output_path.relative_to(ROOT)))

print(json.dumps({
    "status": "PASS",
    "mode": "candidate-validation-only",
    "production_preview_written": False,
    "review_ready": False,
    "outputs": outputs,
    "fixtures_are_synthetic": True,
}, ensure_ascii=False, indent=2))
