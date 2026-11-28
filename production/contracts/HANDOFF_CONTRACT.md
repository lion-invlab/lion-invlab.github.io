# HANDOFF CONTRACT v1.2

Every handoff is scoped to one run_id and report_date and includes schema_version, stage, created_at with timezone, input_refs and SHA-256, output_refs and SHA-256, status_summary, unresolved_items and consumer_notes. Every producer first claims its stage in the same Run state; every consumer validates the exact Run state version, producer receipt and SHA before work.

## Canonical Run-scoped paths

- Stage 2 Observation: production/runs/<run_id>/market-history-web-observations.json
- Stage 2 screenshot sidecar: production/runs/<run_id>/market-screenshot-observations.json
- Stage 2 CNN observation: production/runs/<run_id>/cnn-fear-greed-observation.json
- Stage 4 editorial input: production/runs/<run_id>/stage4-editorial-content.json
- Stage receipts and other intermediate outputs remain under production/runs/<run_id>/.

Date-global files in production/input/ are not valid production handoff sources. A same-date file from another Run must never be attached, merged, or used as fallback.

## Stage handoffs

1. Stage 1 passes report_date, production_date, trading_date, selected mother template and exact SHA, Manifest SHA, pinned Main commit, calendar commit/weekly JSON SHAs, complete governance blob SHA map, blank-first fixture, run-state initialized with Stage 1 PASS / Stage 2 READY, and Stage 1 receipt SHA.
2. Stage 2 ChatGPT worker reads the exact Stage 1 Run handoff and full Stage 2 WR. It submits the 44-row Observation, independent FedWatch, per-field screenshot/browser provenance, source manifest inputs and WR attestation under the Run-scoped paths. The worker changes Stage 2 to SUBMITTED only after all submission files are committed and read back.
3. GitHub Stage 2 validator checks the exact Run ID, dates, Stage 1 receipt/context/fixture SHA, Stage 2 WR SHA, schema, all 44 unique rows, FedWatch, screenshot sidecars, per-field evidence and freshness. It writes the frozen market snapshot and Stage 2 receipt, then changes Stage 2 to PASS or PARTIAL. Only this validator may promote SUBMITTED to PASS/PARTIAL.
4. Stage 3 GitHub job requires Stage 2 PASS/PARTIAL, reads only the Stage 1-pinned Main calendar JSON, projects calendar/earnings, writes the Stage 3 receipt and Stage 4 Research Bundle, then marks Stage 3 PASS. Calendar source JSON remains read-only.
5. Stage 4 ChatGPT worker reads the same Run's Stage 3 Research Bundle, its receipt and the full Stage 4 WR. It submits five/ten news items, three summary points, five ordered analysis layers, six-domain political scan, evidence and concrete strategy as Run-scoped editorial content, including the exact Stage 3 receipt SHA. It changes Stage 4 to SUBMITTED only after the complete file is committed and read back.
6. GitHub Stage 4 validator verifies exact Run/date, frozen market snapshot SHA, Research Bundle SHA, Stage 4 WR attestation, schema and editorial content requirements. It writes Stage 4 receipt and promotes Stage 4 to PASS. Only then may Stage 5 start.
7. Stage 5 passes exact mother/Builder provenance, Stage 2–4 receipts, four QA categories and review HTML/QA sidecar/render manifest. It records PASS or PARTIAL. PARTIAL must skip Stage 6.
8. Stage 6 accepts only Stage 5 PASS, writes exactly the three dated Preview files, verifies remote bytes and Git blob SHAs, correlates Pages deployment to the exact payload commit, opens the public URL and writes delivery receipt. It never changes index.html or formal history.

## Submission events and worker behavior

- Stage 2 Observation uses the already-running capture job polling the Run-scoped bundle and Stage 2 SUBMITTED state; it does not depend on a push-triggered workflow.
- Stage 4 submission marker: [tac-stage4-submit:<run_id>] is an audit label in the editorial JSON commit message, not a trigger. The already-running build-and-deliver job polls for the file, Stage 4 SUBMITTED state, and matching output SHA.
- A marker is only a wake-up hint. The authoritative condition is the exact Run state and submitted artifact SHA; duplicate or delayed events must be idempotent.
- No Stage handoff depends on a GitHub connector push triggering another workflow; that behavior is not established and must not be assumed. Stage 4–6 is the second job in the same scheduled / recover workflow run and waits for the Run-scoped editorial JSON plus Stage 4 SUBMITTED state. The marker is an audit label only. Stage 6 uses explicit Pages workflow_dispatch; Chart 3 uses workflow_run after the production workflow completes.
- A worker that finds its prerequisite absent records or returns DEFERRED and exits without creating a Run, changing another Run, disabling itself, or treating the absence as a market-data failure.
- On receive, validate run_id, report_date, schema, state_version, receipt SHA and required fields. Never use a same-named artifact from a different Run.
- Downstream consumers cannot promote PENDING/MISSING/TOOL_READ_FAILURE/SOURCE_NO_DATA to VERIFIED. Preserve uncertainty.
- No stage may mutate or re-fetch locked market quotes. Stage 3 reads calendar DB only. Stage 4 does not rebuild calendar/earnings or re-fetch 44 quotes. Chart 3 remains a non-blocking downstream consumer of the Stage 2 S&P 500 increment.
