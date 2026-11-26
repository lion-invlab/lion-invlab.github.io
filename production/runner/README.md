# Main production runner port

This directory contains main-branch copies of selected SIM-1.4 modules. Source branch remains read-only. See PORT_MANIFEST.json for exact source blob SHAs and port status.

## Current scope
- Stage 2 blank-first fixture bootstrap, screenshot sidecar parser, browser history reader, observation validation, 44-row manifest, metadata audit, Stage 2 receipt and S&P 500 Chart 3 handoff have been copied.
- Browser history reader default concurrency was changed to 4 to match the 2026-11-26 SIM-1.4 amendment.
- Calendar source guard and earnings judgment modules have been copied.
- The approved Simulation Builder was copied as a main-path candidate and its output guard adapted to `production/runs/<run_id>/review.html`. This does NOT mean the main Builder is approved or E2E validated.

## Hard boundary
No production code may import from or read `simulation-lab/`. New main Workflow must checkout main only. Do not use the main legacy `scripts/`, old mother templates or old WR as fallback.

## Next work
1. Remove residual Simulation paths from copied tests and adapters.
2. Create a current-run input factory/schema without reusable old market values.
3. Complete main-native Stage 1-6 runner and Builder integration.
4. Run the copied deterministic tests and dual-mother/browser QA in a main-only Workflow.
5. Only after real-data E2E, switch schedules and retire competing legacy main workflows.
