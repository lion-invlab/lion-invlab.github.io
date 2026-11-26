# Main production runner

This directory contains main-native Stage 1–6 execution modules ported from the approved SIM-1.4 technical baseline. Simulation remains read-only; production runtime checks out main only. See `PORT_MANIFEST.json` for source provenance and current readiness.

## Current main-native workflow

The only workflow entry is `.github/workflows/tac-production.yml`:

1. `validate`: deterministic tests, dual-mother SHA and DOM checks.
2. `capture`: creates a fresh Run, captures 44 market indicators with concurrency capped at 4, performs Chart 3 S&P 500 handoff, and reads pinned calendar/earnings data (Stages 1–3). It emits a capture receipt with status `AWAITING_EDITORIAL_INPUT`.
3. `build`: accepts editorial JSON bound to the exact captured Run ID and Stage 2 snapshot SHA, then runs Stage 4–6 and delivers only the three date-scoped preview files.

There is no `run_daily_report.py` orchestrator; the GitHub Actions workflow is the single entrypoint and owns sequencing, permissions, commit boundaries and dispatches.

Stage 1 records a commit-pinned SHA inventory for the master rules, six Stage WRs, all shared contracts, both mother configuration files, schemas, Builder approval, Builder, Stage runners/dependencies and the relevant GitHub workflows. Stage 5 compares the exact inventory against current main and refuses cross-version builds.\n\nAfter Stage 3, capture creates `stage4-research-bundle.json`, consolidating the frozen 44-row market snapshot, unresolved items, FedWatch, calendar/earnings projections, Stage receipts, browser observations, source manifest, audit and screenshot evidence SHA. Stage 4 content must bind to the bundle SHA as well as Run ID and market snapshot SHA.

## Builder status

- SIM-1.4 Builder source SHA: `6bf6eb2f5ae29774addf696c541c5b806953c7a3`.
- Main-path candidate: `production/runner/build_review_html.py`, exact blob SHA recorded in `production/config/builder-approval.json`.
- The exact Main Builder blob `20eefe57d6f3b389157c01b8532cae3a69128a02` is explicitly owner-approved in `production/config/builder-approval.json` (`APPROVED_MAIN`, approved 2026-11-26 21:29 Asia/Taipei). This approval covers that exact Builder blob only; it does not substitute for real-data Stage 1–6 E2E or any Stage 5/6 QA Gate.

## Current blockers

1. No automated editorial research/content producer yet creates `production/input/report-content-YYYY-MM-DD.json` from the exact captured Run. This remains the handoff between capture and build.
2. Main Builder exact-blob approval is complete (`APPROVED_MAIN`); real-data Stage 1–6 E2E and Stage 5/6 delivery QA remain outstanding.
3. Stage 5/6 real-data E2E and public Pages verification remain untested.
4. Daily schedule must not be cut over until those items are resolved.

## Hard boundaries

- Never import from or read `simulation-lab/` at runtime.
- Never bypass Investing.com Cloudflare or substitute unapproved market sources.
- Never reuse previous Run market values; Stage 2 is blank-first.
- Stage 3 is calendar read-only; Stage 5 writes only Run-scoped review artifacts; Stage 6 writes only the three approved preview files. Stage 2 marks a row CLOSED only with date-matched official calendar evidence; a missing historical row alone remains SOURCE_NO_DATA / pending, and a confirmed holiday renders value as `-` and change as `休市`.
- Do not update `index.html` or archive a formal edition without explicit user approval.


### Stage 2 official market-closure evidence
All 44 rows retain the single run-level `trading_date` as their target date. A missing row for that date is not proof of a holiday. Both the fixture bootstrap and source-verification manifest consume the same current-run browser evidence fields: `closure_evidence_url`, reader reference and line range, exact target date, source-page-fetched flag, verified instrument/field mapping, current web-open provenance, non-reused observation and finish timestamp. The URL must be on the explicit official-calendar host allowlist. The observation schema now declares these fields. This contract supersedes the earlier bootstrap-only `market_calendar_*` requirement.
