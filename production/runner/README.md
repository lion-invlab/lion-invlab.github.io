# Main production runner

This directory contains main-native Stage 1–6 execution modules ported from the approved SIM-1.4 technical baseline. Simulation remains read-only; production runtime checks out main only. See `PORT_MANIFEST.json` for source provenance and current readiness.

## Current main-native workflow

The only workflow entry is `.github/workflows/tac-production.yml`:

1. `validate`: deterministic tests, dual-mother SHA and DOM checks.
2. `capture`: creates a fresh Run, captures 44 market indicators with concurrency capped at 4, performs Chart 3 S&P 500 handoff, and reads pinned calendar/earnings data (Stages 1–3). It emits a capture receipt with status `AWAITING_EDITORIAL_INPUT`.
3. `build`: accepts editorial JSON bound to the exact captured Run ID and Stage 2 snapshot SHA, then runs Stage 4–6 and delivers only the three date-scoped preview files.

There is no `run_daily_report.py` orchestrator; the GitHub Actions workflow is the single entrypoint and owns sequencing, permissions, commit boundaries and dispatches.

Stage 1 records a commit-pinned SHA inventory for the master rules, six Stage WRs, all shared contracts, both mother configuration files, schemas, Builder approval, Builder, Stage runners/dependencies and the relevant GitHub workflows. Stage 5 compares the exact inventory against current main and refuses cross-version builds.\n\nAfter Stage 3, capture creates `stage4-research-bundle.json`, consolidating the frozen 44-row market snapshot, unresolved items, FedWatch, calendar/earnings projections, source receipts and screenshot evidence SHA. Stage 4 content must bind to the bundle SHA as well as Run ID and market snapshot SHA.

## Builder status

- SIM-1.4 Builder source SHA: `6bf6eb2f5ae29774addf696c541c5b806953c7a3`.
- Main-path candidate: `production/runner/build_review_html.py`, exact blob SHA recorded in `production/config/builder-approval.json`.
- Candidate deterministic tests have passed, but this does not equal main Builder owner approval or real-data E2E.
- Stage 5 now refuses production `REVIEW_READY` until the exact current Builder blob is explicitly marked `APPROVED_MAIN` in the approval record.

## Current blockers

1. No automated editorial research/content producer yet creates `production/input/report-content-YYYY-MM-DD.json` from the exact captured Run. This remains the handoff between capture and build.
2. Main Builder approval remains `CANDIDATE_PENDING_OWNER_APPROVAL`.
3. Stage 5/6 real-data E2E and public Pages verification remain untested.
4. Daily schedule must not be cut over until those items are resolved.

## Hard boundaries

- Never import from or read `simulation-lab/` at runtime.
- Never bypass Investing.com Cloudflare or substitute unapproved market sources.
- Never reuse previous Run market values; Stage 2 is blank-first.
- Stage 3 is calendar read-only; Stage 5 writes only Run-scoped review artifacts; Stage 6 writes only the three approved preview files.
- Do not update `index.html` or archive a formal edition without explicit user approval.
