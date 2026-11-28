#!/usr/bin/env python3
"""Exact-blob owner approval gate for the main production HTML Builder."""
from __future__ import annotations
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
APPROVAL_PATH=ROOT/"production/config/builder-approval.json"
BUILDER_PATH="production/runner/build_review_html.py"
GOVERNANCE_PATHS=(
 "production/MASTER_WR.md",
 "production/CHATGPT_AUTOMATION_PROMPT_MAIN_v1.3.md",
 "production/stages/STAGE_1_CONTEXT.md",
 "production/stages/STAGE_2_MARKET.md",
 "production/stages/STAGE_3_CALENDAR.md",
 "production/stages/STAGE_4_NEWS_ANALYSIS.md",
 "production/stages/STAGE_5_RENDER_QA.md",
 "production/stages/STAGE_6_DELIVERY.md",
 "production/contracts/DATA_SCHEMA.md",
 "production/contracts/HANDOFF_CONTRACT.md",
 "production/contracts/HTML_BUILDER_CONTRACT.md",
 "production/contracts/MOTHER_TEMPLATE_QA.md",
 "production/contracts/PUBLISH_CONTRACT.md",
 "production/contracts/QA_CONTRACT.md",
 "production/contracts/RUN_CONTRACT.md",
 "production/contracts/SOURCE_POLICY.md",
 "production/contracts/STATUS_ENUM.json",
 "production/config/mother-template-manifest.json",
 "production/config/report-data-template.json",
 "production/input/market-screenshot-observations.schema.json",
 "production/config/builder-approval.json",
 "production/runner/PORT_MANIFEST.json",
 "production/runner/stage_wr_loader.py",
 "production/runner/run_state.py",
 "production/runner/accept_stage_submission.py",
 "production/runner/test_accept_stage_submission.py",
 "production/runner/test_production_workflow_structure.py",
 "production/runner/test_run_state.py",
 "production/runner/test_stage2_fedwatch.py",
 "production/runner/test_stage2_field_provenance.py",
 "production/runner/verify_homepage_publication_lock.py",
 "production/runner/test_homepage_publication_lock.py",
 "production/config/homepage-publication-lock.json",
 ".github/workflows/archive_index.yml",
 "production/input/market-history-web-observations.schema.json",
 "production/runner/create_run_fixture.py",
 "production/runner/run_stage2.py",
 "production/runner/browser_verify_market_history.py",
 "production/runner/stage2_screenshot_inputs.py",
 "production/runner/stage2_market_fixture_bootstrap.py",
 "production/runner/validate_chatgpt_web_observations.py",
 "production/runner/build_stage2_receipt.py",
 "production/runner/test_create_run_fixture.py",
 "production/runner/build_market_source_verification_manifest.py",
 "production/runner/validate_market_snapshot.py",
 "production/runner/stage2_move_retry.py",
 "production/runner/handoff_sp500_to_chart3.py",
 "production/runner/run_stage3.py",
 "production/runner/calendar_source_guard.py",
 "production/runner/earnings_judgment.py",
 "production/runner/audit_earnings_schema.py",
 "production/runner/validate_earnings_v2.py",
 "production/runner/collect_earnings_price_reactions.py",
 "production/runner/consensus_snapshot_store.py",
 "production/runner/run_stage4.py",
 "production/runner/prepare_stage4_research_bundle.py",
 "production/runner/run_stage5.py",
 "production/runner/run_stage6.py",
 "production/runner/validate_mother_dom_contract.py",
 "production/runner/validate_review_artifact.py",
 "production/runner/visual_regression.mjs",
 "production/runner/interaction_smoke.mjs",
 "production/runner/build_review_html.py",
 "production/runner/builder_approval.py",
 ".github/workflows/tac-production.yml",
 ".github/workflows/tac-chart3-sp500-increment-merge.yml",
 ".github/workflows/tac-chart3-incremental.yml",
 ".github/workflows/pages.yml",
)

def current_builder_blob_sha(root:Path=ROOT)->str:
    return subprocess.check_output(
        ["git","rev-parse",f"HEAD:{BUILDER_PATH}"],cwd=root,text=True
    ).strip()

def current_governance_blob_shas(root:Path=ROOT, commit_sha:str="HEAD")->dict:
    return {
        path:subprocess.check_output(["git","rev-parse",f"{commit_sha}:{path}"],cwd=root,text=True).strip()
        for path in GOVERNANCE_PATHS
    }

def verify_governance_snapshot(context:dict, root:Path=ROOT, actual_blobs:dict|None=None)->dict:
    governance=context.get("governance") or {}
    if governance.get("commit_sha")!=context.get("main_commit_sha"):
        raise ValueError("Run governance snapshot commit does not match Stage 1 main_commit_sha")
    pinned=governance.get("blob_shas")
    if not isinstance(pinned,dict):
        raise ValueError("Run context is missing the Stage 1 governance SHA snapshot")
    missing=sorted(set(GOVERNANCE_PATHS)-set(pinned))
    if missing:
        raise ValueError("Run context governance snapshot is incomplete: "+", ".join(missing))
    actual=actual_blobs if actual_blobs is not None else current_governance_blob_shas(root)
    mismatches=[path for path in GOVERNANCE_PATHS if pinned.get(path)!=actual.get(path)]
    if mismatches:
        raise ValueError("Governance files changed after Stage 1; refusing cross-version build: "+", ".join(mismatches))
    return {"status":"PASS","file_count":len(GOVERNANCE_PATHS),"blob_shas":pinned}

def require_approved_builder(root:Path=ROOT, approval_path:Path=APPROVAL_PATH, actual_sha:str|None=None)->dict:
    if not approval_path.is_file():
        raise ValueError("Main Builder approval record is missing")
    approval=json.loads(approval_path.read_text(encoding="utf-8"))
    actual=actual_sha or current_builder_blob_sha(root)
    if approval.get("status")!="APPROVED_MAIN" or approval.get("approved_by_owner") is not True:
        raise ValueError("Main Builder is still a candidate pending explicit owner approval")
    if approval.get("builder_path")!=BUILDER_PATH or approval.get("builder_blob_sha")!=actual:
        raise ValueError("Main Builder approval does not match the exact current Builder blob SHA")
    return {"status":"APPROVED_MAIN","builder_path":BUILDER_PATH,"builder_blob_sha":actual,
            "approved_at":approval.get("approved_at")}
