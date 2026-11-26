# Stage 4 editorial content handoff

The main-native pipeline is a two-phase workflow. First, dispatch `tac-production.yml` with mode `capture`. It runs Stage 1–3, captures the current 44-item market snapshot, reads the pinned calendar/earnings JSON, and commits a unique Run folder under `production/runs/<run_id>/`. Its `capture-stage-receipt.json` ends in `AWAITING_EDITORIAL_INPUT`. Before the handoff, the capture workflow also creates `stage4-research-bundle.json` and its receipt from the exact Stage 1–3 Run.

The editorial producer should use `production/runs/<run_id>/stage4-research-bundle.json` as its consolidated input. The bundle contains the exact Run ID, report/trading dates, full frozen market source fields and unresolved rows, FedWatch, current/previous calendar and earnings projections, Stage 1–3 receipts, news window, editorial contract, and SHA-256 references to all source artifacts. The full source observation bundle, 44-row verification manifest and market snapshot audit are embedded in the research packet, with each unresolved market row retaining its exact Stage 2 market_data_status and reconciliation count. The Stage 2 receipt's input-file SHA references are rechecked before the bundle is produced. If screenshots were supplied, it also records the screenshot sidecar and each evidence image path/SHA-256. The original Run artifacts remain authoritative and can be opened for detail. The producer then creates:

`production/input/report-content-YYYY-MM-DD.json`

The JSON must include `run_id`, `market_snapshot_sha256`, and `research_bundle_sha256`, copied from the exact Run's context, Stage 2 summary, and `stage4-research-bundle-receipt.json`. All three are required schema bindings, not optional hints. Stage 4 and the build workflow reject missing or mismatched bindings. Never generate content against a different Run or a changed market snapshot.

The file must validate against `report-content.schema.json`. It contains exactly three summary points, 5 Global Focus News, 10 Market Hot Headlines, sentiment text, five ordered market-analysis layers with internal source evidence, six-domain political scan, core observation, market observation, key levels and market commentary.

The news cutoff is Taiwan-local report time (target 05:25). Weekday window begins the previous calendar day at 12:00; Monday window begins Friday at 12:00. Every news item must carry its original publication time, source timezone and Taiwan-converted publication time. Do not substitute page update time for original publication time.

Stage 4 verifies that cited market rows are VERIFIED or BACKUP_VERIFIED, validates the shared time window and exact counts, then merges editorial content into the current Run fixture. It computes a before/after hash of all Stage 2 market data and fails if Stage 4 changes any market value or provenance.

Do not copy prior-day report text or news into a new input. The schema is a structure contract, not a source of facts.

## Build trigger

After the date-matched editorial JSON is generated, bound to the exact Run, and committed to main with the exact marker `[build-tac-report:YYYY-MM-DD]`, the build job starts Stage 4–6 only. It does **not** rerun Stage 1–3. A manual `workflow_dispatch` with mode `build` and report_date is also supported.

A normal production code commit without the marker runs validation only. The capture phase is a separate `workflow_dispatch` mode. Main-native capture is now configured on the scheduled `tac-production.yml` entry: the DST-gated UTC cron selects Taiwan 04:05 during U.S. daylight time or 05:05 during U.S. standard time and runs Stages 1–3. The ChatGPT Main Stage 4 editorial handoff is scheduled for Taiwan 04:15 / 05:15 respectively, with the inactive DST slot designed as a no-op. These schedules have been configured but their first scheduled executions have not yet been evidenced. Do not describe the pipeline as fully autonomous or production-accepted until scheduled capture, same-Run Stage 4 handoff, exact-SHA Builder approval, real-data Stage 1–6 E2E, and public Pages verification have all passed.
