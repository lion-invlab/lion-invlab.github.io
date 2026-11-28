# RUN CONTRACT v1.3

## Run identity and ownership

- report_date and production_date use Asia/Taipei. A normal scheduled production creates at most one Run for the report_date.
- Run ID is stable across workflow retries: TAC-{report_date}-{workflow_run_id}. The GitHub workflow_run_attempt is metadata, not part of Run ID. Re-running the same GitHub Actions workflow attempt must resume the same Run and must never create another Run directory.
- An explicitly authorized rerun is a new workflow_dispatch invocation and therefore a new workflow_run_id and Run ID. It records supersedes_run_id and preserves every prior Run, receipt, HTML, QA artifact and Preview unchanged.
- One Run directory is the only permanent evidence container for that Run: production/runs/<run_id>/. It contains run-context.json, stage1-fixture.json, mutable report-data.json, one run-state.json, and one receipt per completed Stage. Do not create a second state database or duplicate evidence ledger.
- One active Stage per Run at a time. Main production workflow is the sole run-state.json writer and serializes stage transitions under its workflow concurrency group. ChatGPT workers publish Run-scoped artifacts only; they never claim leases or update state. Each transition must validate expected state_version and previous status, write atomically, and persist through fast-forward-only Git pushes. If a second state writer is ever introduced, compare-and-swap against the exact previously read run-state blob SHA becomes mandatory. A stale state version or non-fast-forward push must reload and re-evaluate, never force-push or blindly replay a transition.
- Stage 1 creation is serialized by a single global Stage 1 concurrency group. Before creating a Run, it scans Main for existing Runs with the same report_date. A stateful Run blocks an unapproved second Run; same-workflow retry resumes its deterministic Run ID. Legacy Runs without run-state.json are read-only historical evidence: a fresh blank-first Run may be created, but their IDs must be recorded in run-context.legacy_prior_run_ids and no data may be read or reused. Explicit recover selects an exact existing Run with valid run-state; if more than one eligible candidate exists, fail closed rather than guessing.
- Stage 1 is the only normal Run creator. Stage 2/4 workers and Stage 3/5/6 jobs never create a Run. Stage 1 is a dedicated short GitHub job: it performs Stage 1 WR preflight before report-date/Run resolution, creates and commits the Run handoff, verifies the remote bytes, publishes its outputs, then exits. Stage 1 must not install Stage 2–6 dependencies, wait for the ChatGPT worker, or execute downstream stages. Stage 2/3 is a separate downstream job that requires the successful Stage 1 output.

## Per-Run state machine

- Exactly one authoritative file: production/runs/<run_id>/run-state.json.
- run-state includes schema_version, state_version, run_id, production_date, report_date, trading_date, main_commit_sha, workflow_run_id, created_at, updated_at, current_stage, last_passed_stage, overall_status, and a six-entry stages object.
- Each stage entry includes status, attempt, started_at, completed_at, input_sha256, output_sha256, receipt_path, error_code, lease_owner and lease_expires_at.
- Stage statuses: NOT_STARTED, READY, RUNNING, SUBMITTED, PASS, DEFERRED, PARTIAL, FAILED, SKIPPED. Only Stage 2 and Stage 4 (ChatGPT-owned submissions) may use SUBMITTED. Only Stage 2 and Stage 5 may use PARTIAL. Stage 5 PARTIAL must set Stage 6 SKIPPED.
- Overall statuses: RUNNING, PARTIAL, FAILED, REVIEW_READY, AWAITING_APPROVAL, PUBLISHED. Stage 5 PASS means REVIEW_READY; Stage 6 PASS means AWAITING_APPROVAL; it never means PUBLISHED. DELIVERED_AND_PUBLICLY_VERIFIED is the Stage 6 receipt status, not a separate overall state.
- Initial state is created atomically with Stage 1 handoff: Stage 1=PASS, Stage 2=READY, Stage 3–6=NOT_STARTED.
- Legal sequence:
  1. Stage 2 READY → RUNNING → SUBMITTED; GitHub validates the exact observation bundle and receipt, then promotes Stage 2 to PASS or PARTIAL.
  2. Stage 2 PASS/PARTIAL → Stage 3 READY → RUNNING → PASS.
  3. Stage 3 PASS → Stage 4 READY → RUNNING → SUBMITTED; GitHub validates editorial content, WR and research bundle, then promotes Stage 4 to PASS.
  4. Stage 4 PASS → Stage 5 READY → RUNNING → PASS or PARTIAL.
  5. Stage 5 PASS → Stage 6 READY → RUNNING → PASS; Stage 5 PARTIAL → Stage 6 SKIPPED.
- Every transition increments state_version and records the exact input/output SHA and receipt path. A consumer cannot start until its required upstream stage has a valid receipt and the state transition has made it READY.
- A RUNNING claim includes lease_owner and lease_expires_at. Expired leases may be reclaimed only after checking the last worker attempt and exact Run artifacts; a live lease cannot be stolen. DEFERRED means prerequisites are absent or a worker is not yet eligible; it is not a failure and must not disable the worker.
- Recovery from FAILED requires an explicit recovery transition to READY for that same Run. PARTIAL is a terminal outcome and cannot be reopened. PASS stages are immutable and are never repeated. Retry/resume preserves run_id; explicit rerun creates a new run_id.

## WR governance and receipts

- Mandatory Stage WR preflight: each Stage reads its complete own WR before work. Stage 1 records its own WR SHA evidence; Stage 2–6 compare against the Stage 1 pinned governance blob SHA. Missing, empty, unreadable, unpinned or drifted WR blocks that Stage.
- Every Stage receipt records wr_preflight. Downstream handoffs validate producer stage key, WR path, Git blob SHA, Stage 1 pinned commit and same-Run identity.
- Each Stage records status, start/end, inputs, outputs, hashes, warnings, errors, retry count and handoff. Receipts are immutable evidence; state only references their paths and hashes.
- Reuse output only if run_id, report_date, schema, input hashes and output hash validate. Never reuse old fixture quotes or mix Runs.
- Recovery resumes from the last valid stage; do not repeat already locked external reads. Retry only unresolved items or a failed stage. User-provided screenshots are valid only for the current production date and exact Run.

## Run completion and publication

- REVIEW_READY means report content and required QA passed.
- Stage 6 receipt status DELIVERED_AND_PUBLICLY_VERIFIED means Stage 6 has committed the exact three Preview files, remote bytes and Git blob SHAs were verified, Pages deployment completed for the exact payload commit, and the public Preview URL was opened and checked. The overall Run state remains AWAITING_APPROVAL.
- AWAITING_APPROVAL is the final automated state. It is not authorization to update index.html or archive formal history.
- PUBLISHED requires separate user approval for the exact report_date and Preview version, followed by formal homepage and archive completion.
