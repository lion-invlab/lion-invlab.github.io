#!/usr/bin/env python3
"""Stage 5: pre-build receipt, main Builder, structural/visual QA, and immutable review artifact."""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RUNNER=Path(__file__).resolve().parent
from builder_approval import require_approved_builder, verify_governance_snapshot
from stage_wr_preflight import stage_wr_preflight, require_stage_wr_receipt
from run_state import transition_state, validate_state

def sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
def git_blob(path:str)->str:return subprocess.check_output(["git","rev-parse",f"HEAD:{path}"],cwd=ROOT,text=True).strip()
def determine_stage5_status(stage2_doc:dict, fixture_doc:dict)->str:
    """Never promote unresolved market/editorial inputs to REVIEW_READY."""
    pending_rows=stage2_doc.get("pending_rows") or []
    pending_items=fixture_doc.get("pending_items") or []
    if stage2_doc.get("status")!="PASS" or pending_rows or pending_items:
        return "PARTIAL"
    return "REVIEW_READY"


def evaluate_scenario_qa(fixture_doc:dict, strategy_paragraphs:list, builder_scan_receipt:dict, artifact_validation:dict)->dict:
    """Require three scenarios when political findings exist; allow evidenced N/A on a no-material-change scan."""
    scan=fixture_doc.get("political_scan") or {}
    findings=scan.get("findings")
    if not isinstance(findings,list):
        raise ValueError("Political scan findings must be a list before scenario applicability can be assessed")
    no_material_change=not findings and bool(str(scan.get("no_material_change_note") or "").strip())
    required=("基準情境","風險情境","嚴重情境")
    coverage=sum(1 for label in required if any(label in str(p) for p in strategy_paragraphs))
    builder_coverage=builder_scan_receipt.get("scenario_analysis_coverage")
    artifact_coverage=artifact_validation.get("scenario_analysis_coverage")
    if no_material_change:
        if coverage!=0 or builder_coverage!=0 or artifact_coverage!=0:
            raise ValueError("NOT_APPLICABLE scenario QA must consistently report zero scenario coverage")
        if builder_scan_receipt.get("scenario_analysis_status") not in ("NOT_TESTED","PARTIAL"):
            raise ValueError("NOT_APPLICABLE scenario QA has an unexpected Builder scenario status")
        return {"coverage":0,"status":"NOT_APPLICABLE","reason":str(scan["no_material_change_note"]).strip()}
    if coverage!=3 or builder_coverage!=coverage or artifact_coverage!=coverage:
        raise ValueError("Scenario analysis applies when political findings exist and must cover base, risk, and severe scenarios")
    if builder_scan_receipt.get("scenario_analysis_status")!="PASS":
        raise ValueError("Builder scenario-analysis receipt did not PASS for an applicable scenario analysis")
    return {"coverage":coverage,"status":"PASS","reason":"Political findings are present; all three required scenarios were verified."}


def validate_stage4_handoff(stage4_doc:dict, stage2_summary_doc:dict, context:dict)->dict:
    if (stage4_doc.get("status")!="PASS" or stage4_doc.get("run_id")!=context.get("run_id")
            or stage4_doc.get("report_date")!=context.get("report_date")
            or stage4_doc.get("trading_date")!=context.get("trading_date")
            or stage4_doc.get("market_snapshot_unchanged") is not True):
        raise ValueError("Stage 4 receipt status/run/date/frozen-market identity mismatch")
    binding=stage4_doc.get("editorial_run_binding") or {}
    bundle=stage4_doc.get("research_bundle") or {}
    if (binding.get("run_id")!=context.get("run_id")
            or binding.get("market_snapshot_sha256")!=stage4_doc.get("market_snapshot_sha256_before")
            or stage4_doc.get("market_snapshot_sha256_before")!=stage4_doc.get("market_snapshot_sha256_after")
            or not binding.get("research_bundle_sha256")
            or binding.get("research_bundle_sha256")!=bundle.get("sha256")):
        raise ValueError("Stage 4 editorial Run/snapshot/research-bundle binding is incomplete or inconsistent")
    if stage2_summary_doc.get("market_snapshot_sha256")!=binding.get("market_snapshot_sha256"):
        raise ValueError("Stage 4 market snapshot SHA differs from the Stage 2 frozen snapshot")
    return binding

def execute(cmd:list[str],log_path:Path)->str:
    p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    log_path.write_text("$ "+" ".join(cmd)+"\n\nSTDOUT:\n"+p.stdout+"\nSTDERR:\n"+p.stderr,encoding="utf-8")
    if p.returncode:
        raise RuntimeError(f"Stage 5 command failed ({p.returncode}): {' '.join(cmd)}; see {log_path.relative_to(ROOT)}")
    return p.stdout

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--run-dir",required=True)
    args=ap.parse_args()
    run_dir=Path(args.run_dir)
    if not run_dir.is_absolute():run_dir=ROOT/run_dir
    runs=ROOT/"production/runs"
    if runs.is_symlink() or runs.resolve()!=runs.absolute() or run_dir.is_symlink():
        raise SystemExit("Stage 5 run directory must be a direct non-symlink child of production/runs")
    run_dir=run_dir.resolve()
    if run_dir.parent!=runs.resolve():
        raise SystemExit("Stage 5 run directory must be a direct non-symlink child of production/runs")
    context=json.loads((run_dir/"run-context.json").read_text(encoding="utf-8"))
    wr_preflight=stage_wr_preflight("STAGE_5",context)
    state_path=run_dir/"run-state.json"
    state=json.loads(state_path.read_text(encoding="utf-8"))
    validate_state(state,expected_run_id=context["run_id"])
    if state["stages"]["STAGE_4"]["status"]!="PASS":
        raise SystemExit("Stage 5 requires Stage 4 PASS in the authoritative Run state")
    if state["stages"]["STAGE_5"]["status"]=="FAILED":
        state=transition_state(state,stage="STAGE_5",expected_version=state["state_version"],expected_status="FAILED",new_status="READY",recovery=True)
    elif state["stages"]["STAGE_5"]["status"]=="DEFERRED":
        state=transition_state(state,stage="STAGE_5",expected_version=state["state_version"],expected_status="DEFERRED",new_status="READY")
    if state["stages"]["STAGE_5"]["status"]!="READY":
        raise SystemExit("Stage 5 is not READY in the authoritative Run state")
    state=transition_state(state,stage="STAGE_5",expected_version=state["state_version"],expected_status="READY",new_status="RUNNING",
        now=datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),lease_owner="github-actions-stage5",
        lease_expires_at=(datetime.now(timezone.utc)+timedelta(minutes=30)).isoformat().replace("+00:00","Z"),
        input_sha256=hashlib.sha256((run_dir/"stage4-analysis-receipt.json").read_bytes()).hexdigest())
    state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")
    try:
        governance_snapshot=verify_governance_snapshot(context,ROOT)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(str(exc))
    try:
        builder_approval=require_approved_builder(ROOT)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc))
    report_date=context["report_date"]
    if not run_dir.name.startswith(f"TAC-{report_date}-"):raise SystemExit("Stage 5 run ID/date mismatch")
    fixture=run_dir/"report-data.json"
    audit=run_dir/"market-snapshot-audit.json"
    manifest=run_dir/"market-source-verification-manifest.json"
    observations=run_dir/"market-history-browser-observations.json"
    stage2=run_dir/"stage2-market-snapshot-receipt.json"
    stage2_summary=run_dir/"stage2-run-summary.json"
    stage3=run_dir/"stage3-calendar-receipt.json"
    stage4=run_dir/"stage4-analysis-receipt.json"
    for p in (fixture,audit,manifest,observations,stage2,stage2_summary,stage3,stage4):
        if not p.is_file():raise SystemExit(f"Stage 5 missing required input: {p.relative_to(ROOT)}")
    stage2_doc=json.loads(stage2.read_text(encoding="utf-8"))
    stage2_summary_doc=json.loads(stage2_summary.read_text(encoding="utf-8"))
    stage3_doc=json.loads(stage3.read_text(encoding="utf-8"))
    stage4_doc=json.loads(stage4.read_text(encoding="utf-8"))
    require_stage_wr_receipt(stage2_doc,"STAGE_2",context)
    require_stage_wr_receipt(stage3_doc,"STAGE_3",context)
    require_stage_wr_receipt(stage4_doc,"STAGE_4",context)
    if stage2_doc.get("run_id")!=context["run_id"] or stage2_doc.get("status") not in ("PASS","PARTIAL") or stage2_doc.get("workflow_run_id")!=str(context.get("workflow_run_id")):
        raise SystemExit("Stage 2 receipt status/run identity mismatch")
    if stage3_doc.get("status")!="PASS" or stage3_doc.get("run_id")!=context["run_id"] or stage3_doc.get("main_commit_sha")!=context["main_commit_sha"]:
        raise SystemExit("Stage 3 receipt status/run/pinned commit mismatch")
    try:
        editorial_binding=validate_stage4_handoff(stage4_doc,stage2_summary_doc,context)
    except ValueError as exc:
        raise SystemExit(str(exc))
    fixture_doc=json.loads(fixture.read_text(encoding="utf-8"))
    summary_points=fixture_doc.get("summary_points") or []
    if len(summary_points)!=3:
        raise SystemExit("Stage 5 editorial QA requires exactly three summary paragraphs")
    summary_texts=[str(item.get("text") or "").strip() for item in summary_points]
    if any(not item for item in summary_texts) or len(set(summary_texts))!=3:
        raise SystemExit("Stage 5 editorial QA found empty or duplicated summary paragraphs")
    sentiment_text=str(fixture_doc.get("sentiment") or "").strip()
    if len(sentiment_text)<80 or sentiment_text in summary_texts:
        raise SystemExit("Stage 5 editorial QA requires a substantive, distinct market-sentiment interpretation")
    analysis_payload=fixture_doc.get("market_analysis") or {}
    expected_layer_keys={"political","policy_industry","macro","markets","strategy"}
    if set(analysis_payload)!=expected_layer_keys:
        raise SystemExit("Stage 5 editorial QA requires all five distinct analysis layers")
    source_count_by_layer={key:len((analysis_payload.get(key) or {}).get("sources") or []) for key in expected_layer_keys}
    if any(count<1 for count in source_count_by_layer.values()):
        raise SystemExit("Stage 5 editorial QA requires traceable sources in all five analysis layers")
    strategy_paragraphs=(analysis_payload.get("strategy") or {}).get("paragraphs") or []
    sp500_item=(fixture_doc.get("global_markets") or {}).get("標普500指數") or {}
    sp500_verified=(sp500_item.get("source") or {}).get("verification_status")=="VERIFIED"
    chart3_handoff=stage2_summary_doc.get("chart3_handoff") or {}
    chart3_status=chart3_handoff.get("status","UNKNOWN")
    start=time.monotonic()
    prebuild=run_dir/"prebuild-input-receipt.json"
    execute([sys.executable,str(RUNNER/"validate_prebuild_stage_inputs.py"),
        "--report-date",report_date,"--data",str(fixture.relative_to(ROOT)),
        "--audit",str(audit.relative_to(ROOT)),"--manifest",str(manifest.relative_to(ROOT)),
        "--observations",str(observations.relative_to(ROOT)),"--output",str(prebuild.relative_to(ROOT)),
        "--run-id",str(context["run_id"]),
        "--run-attempt",str(context.get("workflow_run_attempt","1"))],run_dir/"qa-prebuild.log")
    prebuild_doc=json.loads(prebuild.read_text(encoding="utf-8"))
    if prebuild_doc.get("status")!="PASS":raise SystemExit("Pre-build input receipt did not PASS")
    template_key=context["mother"]["key"]
    output=run_dir/"review.html"
    expected_master_sha=context["mother"]["blob_sha"]
    builder_cmd=[sys.executable,str(RUNNER/"build_review_html.py"),
        "--data",str(fixture.relative_to(ROOT)),
        "--market-source-manifest",str(manifest.relative_to(ROOT)),
        "--output",str(output.relative_to(ROOT)),
        "--expected-master-sha",expected_master_sha]
    optional={
      "--key-levels-live":run_dir/"key-levels-live.json",
      "--price-reactions":run_dir/"earnings-price-reactions.json",
      "--earnings-consensus-projection":run_dir/"earnings-consensus-projection.json"
    }
    for flag,path in optional.items():
        if path.is_file():builder_cmd.extend([flag,str(path.relative_to(ROOT))])
    execute(builder_cmd,run_dir/"qa-builder.log")
    if not output.is_file():raise SystemExit("Builder did not create review.html")
    from bs4 import BeautifulSoup,Comment
    import re
    soup=BeautifulSoup(output.read_text(encoding="utf-8"),"html.parser")
    provenance_comment=next((str(x) for x in soup.find_all(string=lambda x:isinstance(x,Comment) and "TAC_BUILD_PROVENANCE" in str(x))),"")
    match=re.search(r"TAC_BUILD_PROVENANCE\s+(\{.*\})",provenance_comment,re.S)
    if not match:raise SystemExit("Builder provenance is missing or malformed")
    provenance=json.loads(match.group(1))
    if provenance.get("review_ready") is not True:
        raise SystemExit("Builder has not approved REVIEW_READY: "+json.dumps(provenance.get("review_ready_blockers",[]),ensure_ascii=False))
    builder_analysis_receipt=provenance.get("market_analysis_slot_receipt") or {}
    builder_scan_receipt=builder_analysis_receipt.get("political_scan") or {}
    builder_scenario_coverage=builder_scan_receipt.get("scenario_analysis_coverage")
    builder_scenario_status=builder_scan_receipt.get("scenario_analysis_status")
    forbidden_branding=("模擬審核版","Simulation隔離區","資料僅供內部教育訓練使用","僅供內部教育訓練使用")
    main_branding={}
    for selector in (".top-warning",".tac-side-foot",".data-sync-warning","footer.footer"):
        nodes=soup.select(selector)
        if not nodes:
            raise SystemExit("Main review branding slot missing: "+selector)
        rendered=" ".join(node.get_text(" ",strip=True) for node in nodes)
        if any(token in rendered for token in forbidden_branding):
            raise SystemExit("Main review HTML contains Simulation/internal-training branding: "+selector)
        main_branding[selector]=rendered
    if "Main 審核版" not in main_branding[".top-warning"]:
        raise SystemExit("Main review top-warning label missing")
    html_sha=sha(output)
    report_arg=str(output.relative_to(ROOT))
    artifact_validation_text=execute([sys.executable,str(RUNNER/"validate_review_artifact.py"),
        "--report",report_arg,"--report-date",report_date],run_dir/"qa-artifact-validator.log")
    try:
        artifact_validation=json.loads(artifact_validation_text)
    except json.JSONDecodeError as exc:
        raise SystemExit("Stage 5 artifact validator did not return a machine-readable QA receipt") from exc
    if artifact_validation.get("status")!="PASS":
        raise SystemExit("Stage 5 artifact validator did not PASS")
    political_domains=artifact_validation.get("political_domains_checked") or []
    political_classes=artifact_validation.get("political_event_status_classifications") or []
    political_findings=(fixture_doc.get("political_scan") or {}).get("findings") or []
    if artifact_validation.get("political_geopolitical_scan")!="PASS" or len(political_domains)!=6:
        raise SystemExit("Stage 5 political/geopolitical scan QA is incomplete")
    if len(political_classes)!=len(political_findings) or artifact_validation.get("policy_transmission_completeness")!=len(political_findings):
        raise SystemExit("Stage 5 policy-transmission QA does not cover all classified findings")
    try:
        scenario_qa=evaluate_scenario_qa(fixture_doc,strategy_paragraphs,builder_scan_receipt,artifact_validation)
    except ValueError as exc:
        raise SystemExit(str(exc))
    execute([sys.executable,str(RUNNER/"validate_mother_dom_contract.py"),
        "--mother",str((ROOT/context["mother"]["path"]).relative_to(ROOT)),
        "--report",report_arg,"--template",template_key],run_dir/"qa-dom-contract.log")
    visual_dir=run_dir/"visual"
    execute(["node",str(RUNNER/"visual_regression.mjs"),report_arg,template_key,report_date,
        str(visual_dir.relative_to(ROOT))],run_dir/"qa-visual.log")
    interaction_json=run_dir/"interaction-smoke.json"
    os.environ["TEMPLATE_KEY"]="monday" if template_key=="monday" else "weekday"
    execute(["node",str(RUNNER/"interaction_smoke.mjs"),report_arg,
        str(interaction_json.relative_to(ROOT))],run_dir/"qa-interaction.log")
    if sha(output)!=html_sha:raise SystemExit("Review HTML bytes changed during QA")
    visual_report=visual_dir/"visual-regression.json"
    if not visual_report.is_file():raise SystemExit("Visual regression report missing")
    interaction=json.loads(interaction_json.read_text(encoding="utf-8"))
    render_manifest={
      "schema_version":"1.0","run_id":context["run_id"],"report_date":report_date,"trading_date":context["trading_date"],
      "main_commit_sha":context["main_commit_sha"],"mother":context["mother"],
      "manifest_sha256":context["manifest"]["sha256"],"builder_path":"production/runner/build_review_html.py",
      "builder_blob_sha":git_blob("production/runner/build_review_html.py"),
      "builder_approval":builder_approval,
      "governance_snapshot":governance_snapshot,
      "wr_preflight":wr_preflight,
      "mother_blob_sha":expected_master_sha,
      "master_wr_blob_sha":git_blob("production/MASTER_WR.md"),
      "qa_contract_blob_sha":git_blob("production/contracts/MOTHER_TEMPLATE_QA.md"),
      "input_sha256":{p.name:sha(p) for p in (fixture,audit,manifest,observations,stage2,stage2_summary,stage3,stage4,prebuild)},
      "output":{"path":str(output.relative_to(ROOT)),"sha256":html_sha},
      "visual_report_sha256":sha(visual_report),"interaction_report_sha256":sha(interaction_json)
    }
    render_path=run_dir/"render-manifest.json"
    render_path.write_text(json.dumps(render_manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    stage5_status=determine_stage5_status(stage2_doc,fixture_doc)
    qa={
      "schema_version":"1.0","run_id":context["run_id"],"report_date":report_date,"trading_date":context["trading_date"],
      "status":stage5_status,"groups":{
        "data_content":{"status":stage2_doc.get("status","PARTIAL"),"prebuild_receipt_sha256":sha(prebuild),"stage2_receipt_sha256":sha(stage2),"stage2_summary_sha256":sha(stage2_summary),"stage3_receipt_sha256":sha(stage3),"wr_preflight":wr_preflight,"stage4_receipt_sha256":sha(stage4),"chart3_handoff_status":chart3_status,"chart3_handoff_required":False,"chart3_handoff_non_blocking":True,"unresolved_rows":stage2_doc.get("pending_rows",[]),"pending_items":fixture_doc.get("pending_items",[]),"editorial_content_status":"PASS","summary_points_count":len(summary_points),"sentiment_char_count":len(sentiment_text),"market_analysis_layer_count":len(analysis_payload),"market_analysis_source_count_by_layer":source_count_by_layer,"political_geopolitical_scan":artifact_validation["political_geopolitical_scan"],"political_domains_checked":political_domains,"political_event_status_classifications":political_classes,"policy_transmission_completeness":artifact_validation["policy_transmission_completeness"],"scenario_analysis_coverage":scenario_qa["coverage"],"scenario_analysis_status":scenario_qa["status"],"scenario_analysis_reason":scenario_qa["reason"]},
        "html_structure":{"status":"PASS","artifact_validator":"PASS","mother_dom_contract":"PASS","main_branding_status":"PASS","main_review_labels":main_branding},
        "visual_interaction":{"status":"PASS","visual_report":str(visual_report.relative_to(ROOT)),"interaction_report":str(interaction_json.relative_to(ROOT)),"interaction_summary":interaction},
        "run_integration":{"status":"PASS","same_run_id":True,"html_sha256":html_sha,"render_manifest_sha256":sha(render_path)}
      },
      "html":{"path":str(output.relative_to(ROOT)),"sha256":html_sha},
      "tested_at_utc":__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    }
    qa_path=run_dir/"qa-sidecar.json"
    qa_path.write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    receipt={"status":stage5_status,"run_id":context["run_id"],"report_date":report_date,"trading_date":context["trading_date"],
      "wr_preflight":wr_preflight,
      "stage4_receipt_sha256":sha(stage4),"builder_blob_sha":git_blob("production/runner/build_review_html.py"),"research_bundle_sha256":editorial_binding["research_bundle_sha256"],
      "market_snapshot_sha256":editorial_binding["market_snapshot_sha256"],"html_path":str(output.relative_to(ROOT)),"html_sha256":html_sha,
      "render_manifest_sha256":sha(render_path),"qa_sidecar_sha256":sha(qa_path),
      "scenario_analysis_coverage":scenario_qa["coverage"],"scenario_analysis_status":scenario_qa["status"],"scenario_analysis_reason":scenario_qa["reason"],"political_geopolitical_scan":artifact_validation["political_geopolitical_scan"],"editorial_content_status":"PASS",
      "elapsed_seconds":round(time.monotonic()-start,3)}
    receipt_path=run_dir/"stage5-render-qa-receipt.json"
    receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    state=json.loads(state_path.read_text(encoding="utf-8"))
    state_status="PASS" if stage5_status=="REVIEW_READY" else "PARTIAL"
    state=transition_state(state,stage="STAGE_5",expected_version=state["state_version"],expected_status="RUNNING",new_status=state_status,
        now=datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
        input_sha256=hashlib.sha256((sha(stage4)+sha(stage2)+sha(fixture)).encode()).hexdigest(),
        output_sha256=sha(receipt_path),receipt_path=str(receipt_path.relative_to(ROOT)))
    state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,ensure_ascii=False,indent=2))

if __name__=="__main__":main()
