"""Regression test for the Stage 1 exit / Stage 2-3 / Stage 4-6 job boundaries."""
from pathlib import Path

workflow = Path(".github/workflows/tac-production.yml").read_text(encoding="utf-8")
assert "  stage1-create-run:" in workflow
assert "  stage2-and-stage3:" in workflow
assert "  build-and-deliver:" in workflow
stage1_start = workflow.index("  stage1-create-run:")
stage2_start = workflow.index("  stage2-and-stage3:")
build_start = workflow.index("  build-and-deliver:")
assert stage1_start < stage2_start < build_start

stage1 = workflow[stage1_start:stage2_start]
stage2 = workflow[stage2_start:build_start]
build = workflow[build_start:]

# Reservation is scoped to the report date, not the whole workflow/branch.
assert "concurrency:\n  group: tac-main-production-" not in workflow
assert "group: tac-main-stage1-${{ inputs.report_date || needs['schedule-window'].outputs.report_date || github.run_id }}" in stage1
assert "report_date: ${{ steps.dst.outputs.report_date }}" in workflow
assert 'if [ "$DISPATCH_MODE" = "rerun" ] || [ "$DISPATCH_MODE" = "recover" ]; then' in stage1
assert "Manual recovery/rerun requires an explicit Taiwan report_date" in stage1
assert "actions: read" in stage1
assert "assert_prior_workflow_inactive(prior)" in stage1
assert "Prior workflow" in stage1
assert "playwright==1.65.2" in workflow
assert "npm install --no-save --no-package-lock playwright" in workflow
assert "npx playwright install chromium" in workflow

# Stage 1 must create, publish, and exit before any Stage 2 dependency is installed.
assert "timeout-minutes: 10" in stage1
assert "Stage 1 — create or resume the exact Run" in stage1
assert "Publish Stage 1 handoff before Stage 2 starts" in stage1
assert stage1.index("Stage 1 WR preflight before report-date or Run resolution") < stage1.index("Resolve report date and unique Run ID")
assert "run_dir: ${{ steps.resolve.outputs.run_dir }}" in stage1
assert "python -m pip install" not in stage1
assert "playwright" not in stage1
assert "actions: write" not in stage1

# Stage 2/3 must use always() because schedule-window is intentionally skipped on manual dispatch.
assert "if: ${{ always() && needs['stage1-create-run'].result == 'success' }}" in stage2
assert "needs: [stage1-create-run]" in stage2
assert "needs['stage1-create-run'].outputs.run_id" in stage2 or "needs.stage1-create-run.outputs.run_id" in stage2
assert "needs['stage1-create-run'].outputs.run_dir" in stage2 or "needs.stage1-create-run.outputs.run_dir" in stage2
assert "timeout-minutes: 35" in stage2
assert "Wait for exact Run-scoped Stage 2 worker handoff" in stage2
assert "market-history-web-observations.json" in stage2
assert "accept_stage_submission.py --run-dir \"$RUN_DIR\" --stage STAGE_2" in stage2

# Stage 4-6 must also clear the skipped schedule-window ancestor after successful Stage 2/3.
assert "if: ${{ always() && needs['stage2-and-stage3'].result == 'success' }}" in build
assert "needs: [stage2-and-stage3]" in build
assert "needs['stage2-and-stage3'].outputs.run_id" in build or "needs.stage2-and-stage3.outputs.run_id" in build
assert 'pinned_wr_blob=((context.get("governance") or {}).get("blob_shas") or {}).get(wr_path.as_posix())' in stage2
assert "stage4-editorial-content.json" in build
assert "accept_stage_submission.py --run-dir \"$RUN_DIR\" --stage STAGE_4" in build

# Stage 5/6 must be a single downstream delivery chain with explicit PARTIAL isolation.
assert "Stage 5 — build exact mother and run full QA" in build
assert 'python production/runner/run_stage5.py --run-dir "$RUN_DIR"' in build
assert "Persist Stage 5 QA receipt and state" in build
assert "Stage 6 — deliver three preview files and verify Pages" in build
assert 'python production/runner/run_stage6.py --run-dir "$RUN_DIR"' in build
assert "Persist Stage 6 delivery receipt and final state" in build
assert "steps.resolve.outputs.stage5_status == 'PASS' || steps.stage5.outputs.status == 'REVIEW_READY'" in build
assert "steps.resolve.outputs.stage6_status != 'PASS'" in build
assert "steps.resolve.outputs.stage5_status == 'PARTIAL' || steps.stage5.outputs.status == 'PARTIAL'" in build
assert "Stage 5 is PARTIAL; retaining Run artifacts, skipping main/preview delivery." in build

# No stale job identity or date-global worker handoff may remain.
assert "capture-and-calendar" not in workflow
assert "production/input/market-history-web-observations-" not in workflow
assert "production/input/report-content-" not in workflow
# Stage 2 close waiting is bound to this Run's trading_date, not the current
# New York time-of-day (which caused next-day recoveries to wait another day).
assert "wait_for_trading_date_close.py \"$RUN_DIR/run-context.json\"" in stage2
assert "date +%H%M" not in stage2
assert "trading_date-bound close wait" in stage2

print("PASS: Stage 1 exits after Run handoff; Stage 2/3 and Stage 4/6 are downstream jobs.")

# Stage 4 editorial handoff must be tied to the same Run created by Stage 1,
# not a date-global file or a separately-created workflow run.
assert "timeout-minutes: 45" in build
assert "Resolve exact Run and accept Stage 4 worker submission" in build
resolve_start = build.index("      - name: Resolve exact Run and accept Stage 4 worker submission")
stage4_exec_start = build.index("      - name: Stage 4 — validate and merge current editorial research")
stage4_resolve = build[resolve_start:stage4_exec_start]
assert "CAPTURE_RUN_ID: ${{ needs['stage2-and-stage3'].outputs.run_id }}" in stage4_resolve
assert "CAPTURE_REPORT_DATE: ${{ needs['stage2-and-stage3'].outputs.report_date }}" in stage4_resolve
assert 'RUN_DIR="production/runs/$RUN_ID"' in stage4_resolve
assert 'CONTENT_FILE="$RUN_DIR/stage4-editorial-content.json"' in stage4_resolve
assert 'for attempt in $(seq 1 30); do' in stage4_resolve
assert "sleep 30" in stage4_resolve
assert "accept_stage_submission.py --run-dir \"$RUN_DIR\" --stage STAGE_4" in stage4_resolve
assert "Stage 4 worker did not publish the exact Run-scoped editorial artifact within 15 minutes." in stage4_resolve

# Stage 4 evidence checks are part of the executable validator inside the handoff step.
stage4_validator_start = stage4_resolve.index('          python - "$CONTENT_FILE" "$RUN_DIR" "$REPORT_DATE" <<\'PY\'')
stage4_validator = stage4_resolve[stage4_validator_start:]
assert 'assert context["run_id"]==run_dir.name==content["run_id"]' in stage4_validator
assert 'assert context["report_date"]==report_date==content["report_date"]' in stage4_validator
assert 'assert state["stages"]["STAGE_3"]["status"]=="PASS"' in stage4_validator
assert 'assert content["market_snapshot_sha256"]==summary["market_snapshot_sha256"]' in stage4_validator
assert 'assert content["research_bundle_sha256"]==bundle["bundle_sha256"]==capture["research_bundle_sha256"]' in stage4_validator
assert 'assert content["stage3_receipt_sha256"]==stage3_sha==capture["stage3_receipt_sha256"]' in stage4_validator
assert 'assert content["stage4_wr_sha256"]==stage4_wr_sha' in stage4_validator






