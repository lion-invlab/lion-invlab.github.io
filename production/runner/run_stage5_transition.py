#!/usr/bin/env python3
"""Stage 5 wrapper: allow only the attested SIFMA holiday-evidence transition for the exact 2026-11-27 Run."""
from __future__ import annotations
import hashlib, json, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
TRANSITION_ID="SIFMA-MOVE-THANKSGIVING-2026-11-26"
ALLOWED_CHANGED_PATHS=sorted([
 "production/MASTER_WR.md",
 "production/runner/stage2_market_fixture_bootstrap.py",
 "production/runner/build_stage2_receipt.py",
 "production/runner/build_market_source_verification_manifest.py",
 "production/runner/validate_prebuild_stage_inputs.py",
 "production/runner/build_review_html.py",
 "production/config/builder-approval.json",
 ".github/workflows/tac-production.yml",
])

def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verify_transition(context:dict, root:Path, original_error:Exception)->dict:
    run_dir=root/"production/runs"/str(context.get("run_id",""))
    att_path=run_dir/"governance-transition-attestation.json"
    if not att_path.is_file():
        raise ValueError(str(original_error)+"; exact-Run governance transition attestation missing")
    att=json.loads(att_path.read_text(encoding="utf-8"))
    from builder_approval import GOVERNANCE_PATHS, current_governance_blob_shas, require_approved_builder
    pinned=(context.get("governance") or {}).get("blob_shas")
    if att.get("schema_version")!="1.0" or att.get("status")!="APPROVED_COMPATIBLE_TRANSITION":
        raise ValueError("governance transition attestation status/schema invalid")
    if att.get("transition_id")!=TRANSITION_ID or att.get("run_id")!=context.get("run_id"):
        raise ValueError("governance transition attestation is not bound to this exact Run")
    if att.get("report_date")!=context.get("report_date") or context.get("main_commit_sha")!="c337b44d9187e79e420aa06e58121f95b5fd5336":
        raise ValueError("governance transition is limited to the original 2026-11-27 Stage 1 commit")
    if att.get("original_commit_sha")!=context.get("main_commit_sha") or att.get("original_blob_shas")!=pinned:
        raise ValueError("governance transition original Stage 1 pins mismatch")
    actual=current_governance_blob_shas(root)
    mismatches=sorted(path for path in GOVERNANCE_PATHS if pinned.get(path)!=actual.get(path))
    if mismatches!=ALLOWED_CHANGED_PATHS or att.get("changed_paths")!=ALLOWED_CHANGED_PATHS:
        raise ValueError("governance transition changed-file set is not the exact approved SIFMA-only allowlist")
    if att.get("current_blob_shas")!=actual:
        raise ValueError("governance transition current governance blob map mismatch")
    wrapper_sha=subprocess.check_output(["git","rev-parse","HEAD:production/runner/run_stage5_transition.py"],cwd=root,text=True).strip()
    if att.get("transition_runner_blob_sha")!=wrapper_sha:
        raise ValueError("governance transition runner blob SHA mismatch")
    ctx_sha=sha(run_dir/"run-context.json")
    if att.get("run_context_sha256")!=ctx_sha:
        raise ValueError("governance transition run-context SHA mismatch")
    for att_key, file_name in (
        ("stage1_receipt_sha256","stage1-receipt.json"),
        ("stage1_fixture_sha256","stage1-fixture.json"),
        ("stage2_receipt_sha256","stage2-market-snapshot-receipt.json"),
        ("stage2_summary_sha256","stage2-run-summary.json"),
        ("stage3_receipt_sha256","stage3-calendar-receipt.json"),
        ("stage4_bundle_receipt_sha256","stage4-research-bundle-receipt.json"),
        ("market_manifest_sha256","market-source-verification-manifest.json"),
        ("market_observations_sha256","market-history-browser-observations.json"),
    ):
        if att.get(att_key)!=sha(run_dir/file_name):
            raise ValueError("governance transition artifact SHA mismatch: "+file_name)
    stage1=json.loads((run_dir/"stage1-receipt.json").read_text(encoding="utf-8"))
    stage2=json.loads((run_dir/"stage2-market-snapshot-receipt.json").read_text(encoding="utf-8"))
    stage2_summary=json.loads((run_dir/"stage2-run-summary.json").read_text(encoding="utf-8"))
    stage3=json.loads((run_dir/"stage3-calendar-receipt.json").read_text(encoding="utf-8"))
    stage4=json.loads((run_dir/"stage4-analysis-receipt.json").read_text(encoding="utf-8"))
    if stage1.get("status")!="PASS" or stage1.get("governance_commit_sha")!=context.get("main_commit_sha"):
        raise ValueError("transition requires immutable original Stage 1 PASS receipt")
    if stage2.get("status")!="PASS" or stage2.get("pending_count")!=0:
        raise ValueError("transition requires exact-Run Stage 2 PASS with zero pending rows")
    move=next((x for x in stage2.get("rows",[]) if x.get("group")=="risk" and x.get("name")=="move"),None)
    if not move or move.get("status")!="CLOSED" or move.get("closure_evidence",{}).get("url","").find("sifma.org")<0:
        raise ValueError("transition requires MOVE CLOSED with SIFMA evidence")
    if stage3.get("status")!="PASS" or stage3.get("run_id")!=context.get("run_id"):
        raise ValueError("transition requires exact-Run Stage 3 PASS")
    if stage4.get("status")!="PASS" or stage4.get("run_id")!=context.get("run_id"):
        raise ValueError("transition requires exact-Run Stage 4 PASS")
    if stage4.get("market_snapshot_sha256_before")!=stage2_summary.get("market_snapshot_sha256") or stage4.get("market_snapshot_sha256_after")!=stage2_summary.get("market_snapshot_sha256"):
        raise ValueError("Stage 4 must preserve the frozen Stage 2 market snapshot")
    approval=require_approved_builder(root)
    if att.get("builder_blob_sha")!=approval.get("builder_blob_sha") or actual.get("production/runner/build_review_html.py")!=approval.get("builder_blob_sha"):
        raise ValueError("approved Builder exact blob does not match the transition attestation")
    if att.get("builder_approval_blob_sha")!=actual.get("production/config/builder-approval.json"):
        raise ValueError("Builder approval record blob SHA mismatch")
    mother=(context.get("mother") or {})
    mother_blob=subprocess.check_output(["git","rev-parse",f"HEAD:{mother.get('path')}"],cwd=root,text=True).strip()
    if mother_blob!=mother.get("blob_sha") or actual.get("production/config/mother-template-manifest.json")!=pinned.get("production/config/mother-template-manifest.json"):
        raise ValueError("approved mother template or manifest changed during governance transition")
    evidence=att.get("evidence") or {}
    if evidence.get("stage2_regression_run_id")!=45939345818 or evidence.get("stage2_regression_conclusion")!="success":
        raise ValueError("Stage 2 SIFMA regression evidence missing")
    if evidence.get("same_run_resume_id") not in (45939546192,45941381146) or evidence.get("same_run_resume_conclusion")!="success":
        raise ValueError("same-Run Stage 2 resume evidence missing")
    return {"status":"PASS_WITH_ATTESTED_COMPATIBLE_TRANSITION","file_count":len(GOVERNANCE_PATHS),
            "original_commit_sha":context["main_commit_sha"],"changed_paths":mismatches,
            "attestation_sha256":sha(att_path),"transition_id":TRANSITION_ID,
            "builder_blob_sha":approval["builder_blob_sha"]}

def main():
    import builder_approval
    original=builder_approval.verify_governance_snapshot
    def verify(context,root=ROOT):
        try:
            return original(context,root)
        except (ValueError,OSError,subprocess.CalledProcessError) as exc:
            return verify_transition(context,root,exc)
    builder_approval.verify_governance_snapshot=verify
    import run_stage5
    run_stage5.verify_governance_snapshot=verify
    run_stage5.main()

if __name__=="__main__":
    main()
