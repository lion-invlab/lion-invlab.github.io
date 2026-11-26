#!/usr/bin/env python3
"""Stage 5: pre-build receipt, main Builder, structural/visual QA, and immutable review artifact."""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RUNNER=Path(__file__).resolve().parent

def sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
def git_blob(path:str)->str:return subprocess.check_output(["git","rev-parse",f"HEAD:{path}"],cwd=ROOT,text=True).strip()
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
    if stage2_doc.get("status") not in ("PASS","PARTIAL") or stage2_doc.get("workflow_run_id") not in (str(context.get("workflow_run_id")),context["run_id"]):
        raise SystemExit("Stage 2 receipt status/run identity mismatch")
    if stage3_doc.get("status")!="PASS" or stage3_doc.get("run_id")!=context["run_id"] or stage3_doc.get("main_commit_sha")!=context["main_commit_sha"]:
        raise SystemExit("Stage 3 receipt status/run/pinned commit mismatch")
    if stage4_doc.get("status")!="PASS" or stage4_doc.get("run_id")!=context["run_id"] or stage4_doc.get("market_snapshot_unchanged") is not True:
        raise SystemExit("Stage 4 receipt status/run/frozen-market identity mismatch")
    fixture_doc=json.loads(fixture.read_text(encoding="utf-8"))
    sp500_item=(fixture_doc.get("global_markets") or {}).get("標普500指數") or {}
    sp500_verified=(sp500_item.get("source") or {}).get("verification_status")=="VERIFIED"
    chart3_handoff=stage2_summary_doc.get("chart3_handoff") or {}
    chart3_status=chart3_handoff.get("status","UNKNOWN")
    if sp500_verified and chart3_status not in ("APPENDED","NOOP_IDENTICAL_OBSERVATION","PASS"):
        raise SystemExit("Verified S&P 500 requires a successful Chart 3 handoff; got "+str(chart3_status))
    start=time.monotonic()
    prebuild=run_dir/"prebuild-input-receipt.json"
    execute([sys.executable,str(RUNNER/"validate_prebuild_stage_inputs.py"),
        "--report-date",report_date,"--data",str(fixture.relative_to(ROOT)),
        "--audit",str(audit.relative_to(ROOT)),"--manifest",str(manifest.relative_to(ROOT)),
        "--observations",str(observations.relative_to(ROOT)),"--output",str(prebuild.relative_to(ROOT)),
        "--run-id",str(context.get("workflow_run_id","LOCAL")),
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
    html_sha=sha(output)
    report_arg=str(output.relative_to(ROOT))
    execute([sys.executable,str(RUNNER/"validate_review_artifact.py"),
        "--report",report_arg,"--report-date",report_date],run_dir/"qa-artifact-validator.log")
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
      "schema_version":"1.0","run_id":context["run_id"],"report_date":report_date,
      "main_commit_sha":context["main_commit_sha"],"mother":context["mother"],
      "manifest_sha256":context["manifest"]["sha256"],"builder_path":"production/runner/build_review_html.py",
      "builder_blob_sha":git_blob("production/runner/build_review_html.py"),
      "mother_blob_sha":expected_master_sha,
      "master_wr_blob_sha":git_blob("production/MASTER_WR.md"),
      "qa_contract_blob_sha":git_blob("production/contracts/MOTHER_TEMPLATE_QA.md"),
      "input_sha256":{p.name:sha(p) for p in (fixture,audit,manifest,observations,stage2,stage2_summary,stage3,stage4,prebuild)},
      "output":{"path":str(output.relative_to(ROOT)),"sha256":html_sha},
      "visual_report_sha256":sha(visual_report),"interaction_report_sha256":sha(interaction_json)
    }
    render_path=run_dir/"render-manifest.json"
    render_path.write_text(json.dumps(render_manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    qa={
      "schema_version":"1.0","run_id":context["run_id"],"report_date":report_date,
      "status":"REVIEW_READY","groups":{
        "data_content":{"status":stage2_doc.get("status","PARTIAL"),"prebuild_receipt_sha256":sha(prebuild),"stage2_receipt_sha256":sha(stage2),"stage2_summary_sha256":sha(stage2_summary),"stage3_receipt_sha256":sha(stage3),"stage4_receipt_sha256":sha(stage4),"chart3_handoff_status":chart3_status,"chart3_handoff_required":sp500_verified,"unresolved_rows":stage2_doc.get("pending_rows",[])},
        "html_structure":{"status":"PASS","artifact_validator":"PASS","mother_dom_contract":"PASS"},
        "visual_interaction":{"status":"PASS","visual_report":str(visual_report.relative_to(ROOT)),"interaction_report":str(interaction_json.relative_to(ROOT)),"interaction_summary":interaction},
        "run_integration":{"status":"PASS","same_run_id":True,"html_sha256":html_sha,"render_manifest_sha256":sha(render_path)}
      },
      "html":{"path":str(output.relative_to(ROOT)),"sha256":html_sha},
      "tested_at_utc":__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    }
    qa_path=run_dir/"qa-sidecar.json"
    qa_path.write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    receipt={"status":"REVIEW_READY","run_id":context["run_id"],"report_date":report_date,
      "html_path":str(output.relative_to(ROOT)),"html_sha256":html_sha,
      "render_manifest_sha256":sha(render_path),"qa_sidecar_sha256":sha(qa_path),
      "elapsed_seconds":round(time.monotonic()-start,3)}
    receipt_path=run_dir/"stage5-render-qa-receipt.json"
    receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt,ensure_ascii=False,indent=2))

if __name__=="__main__":main()
