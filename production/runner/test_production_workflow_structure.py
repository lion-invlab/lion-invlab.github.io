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

# Stage 1 must create, publish, and exit before any Stage 2 dependency is installed.
assert "timeout-minutes: 10" in stage1
assert "Stage 1 — create or resume the exact Run" in stage1
assert "Publish Stage 1 handoff before Stage 2 starts" in stage1
assert stage1.index("Stage 1 WR preflight before report-date or Run resolution") < stage1.index("Resolve report date and unique Run ID")
assert "run_dir: ${{ steps.resolve.outputs.run_dir }}" in stage1
assert "python -m pip install" not in stage1
assert "playwright" not in stage1
assert "actions: write" not in stage1

# Stage 2/3 consumes only the successful Stage 1 outputs and owns the bounded wait.
assert "needs: [stage1-create-run]" in stage2
assert "needs['stage1-create-run'].outputs.run_id" in stage2 or "needs.stage1-create-run.outputs.run_id" in stage2
assert "needs['stage1-create-run'].outputs.run_dir" in stage2 or "needs.stage1-create-run.outputs.run_dir" in stage2
assert "timeout-minutes: 45" in stage2
assert "Wait for exact Run-scoped Stage 2 worker handoff" in stage2
assert "market-history-web-observations.json" in stage2
assert "accept_stage_submission.py --run-dir \"$RUN_DIR\" --stage STAGE_2" in stage2

# Stage 4-6 cannot begin unless Stage 2/3 completed in the same workflow Run.
assert "needs: [stage2-and-stage3]" in build
assert "needs['stage2-and-stage3'].outputs.run_id" in build or "needs.stage2-and-stage3.outputs.run_id" in build
assert "stage4-editorial-content.json" in build
assert "accept_stage_submission.py --run-dir \"$RUN_DIR\" --stage STAGE_4" in build

# No stale job identity or date-global worker handoff may remain.
assert "capture-and-calendar" not in workflow
assert "production/input/market-history-web-observations-" not in workflow
assert "production/input/report-content-" not in workflow
print("PASS: Stage 1 exits after Run handoff; Stage 2/3 and Stage 4/6 are downstream jobs.")
