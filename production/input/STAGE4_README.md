# Stage 4 editorial content handoff

The main-native pipeline is a two-phase workflow. First, dispatch `tac-production.yml` with mode `capture`. It runs Stage 1–3, captures the current 44-item market snapshot, reads the pinned calendar/earnings JSON, and commits a unique Run folder under `production/runs/<run_id>/`. Its `capture-stage-receipt.json` ends in `AWAITING_EDITORIAL_INPUT`.

The editorial producer must read that exact Run's `run-context.json`, `report-data.json`, Stage 2 observation/receipt/summary, Stage 3 calendar/earnings projections and capture receipt. It then creates:

`production/input/report-content-YYYY-MM-DD.json`

The JSON must include **both** `run_id` and `market_snapshot_sha256`, copied from the exact Run's `run-context.json` and `stage2-run-summary.json`. These are required schema fields, not optional hints. Stage 4 and the build workflow reject missing or mismatched bindings. Never generate content against a different Run or a changed market snapshot.

The file must validate against `report-content.schema.json`. It contains exactly three summary points, 5 Global Focus News, 10 Market Hot Headlines, sentiment text, five ordered market-analysis layers with internal source evidence, six-domain political scan, core observation, market observation, key levels and market commentary.

The news cutoff is Taiwan-local report time (target 05:25). Weekday window begins the previous calendar day at 12:00; Monday window begins Friday at 12:00. Every news item must carry its original publication time, source timezone and Taiwan-converted publication time. Do not substitute page update time for original publication time.

Stage 4 verifies that cited market rows are VERIFIED or BACKUP_VERIFIED, validates the shared time window and exact counts, then merges editorial content into the current Run fixture. It computes a before/after hash of all Stage 2 market data and fails if Stage 4 changes any market value or provenance.

Do not copy prior-day report text or news into a new input. The schema is a structure contract, not a source of facts.

## Build trigger

After the date-matched editorial JSON is generated, bound to the exact Run, and committed to main with the exact marker `[build-tac-report:YYYY-MM-DD]`, the build job starts Stage 4–6 only. It does **not** rerun Stage 1–3. A manual `workflow_dispatch` with mode `build` and report_date is also supported.

A normal production code commit without the marker runs validation only. The capture phase is a separate `workflow_dispatch` mode. There is currently no scheduled main-native capture trigger and no automatic LLM editorial producer; do not describe the pipeline as fully scheduled or fully autonomous until those integrations and a real-data E2E have been completed.
