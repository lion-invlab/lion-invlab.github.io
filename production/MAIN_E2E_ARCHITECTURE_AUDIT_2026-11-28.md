# TAC Main E2E Architecture — Read-only Audit (2026-11-28)

## 1. Scope and safety

- Repository: `lion-invlab/lion-invlab.github.io`
- Audited branch: `main`
- Audit/refactor branch: `refactor/tac-main-e2e-architecture-20261128` (originated from `rebuild/tac-main-e2e-architecture-20261128`)
- Simulation reference: `simulation/tac-process-lab-2026-11-06` (read-only; this audit did not read or write its runtime assets)
- This document records a read-only audit. No production code, workflow, schedule, automation prompt, Main homepage, Preview, calendar data, Chart 3 data, or Simulation file was changed.
- This audit branch is documentation-only. It is not a production branch and must not be merged as a production activation.

## 2. Executive finding

Main has substantial Stage 1–6 implementation assets, but the runtime is not yet the requested six-stage independently resumable pipeline.

The current production workflow still combines Stage 1, Stage 2 receipt waiting/validation, and Stage 3 in one long-running `capture-and-calendar` job. Stage 4–6 are entered through a separate push-marker continuation. The ChatGPT task is still a combined Stage 2 plus wait-for-Capture plus Stage 4–6 worker. This does not match the requested independent Stage 2 and Stage 4 checkpoints with state-driven resume.

A further key finding: the 2026-11-28 scheduled workflow event did occur. Run `46096657083` completed successfully at the workflow level, but its `capture-and-calendar`, `build-and-deliver`, and validation jobs were skipped. Therefore "schedule never fired" is not a valid root-cause statement for that run. The schedule-window decision and downstream job conditions must be examined.

## 3. Repository inventory

### 3.1 Workflow inventory

The Main `.github/workflows/` directory contains **24 workflow files**, not 23:

| Workflow | Current role / audit classification |
|---|---|
| `archive_index.yml` | Scheduled + manual archive writer; conflicts with approval-only publication intent because its schedule invokes the publication-lock gate. Must reconcile before activation. |
| `chart2-preview-browser-qa.yml` | Chart 2 visual QA; independent downstream QA. |
| `chart3-preview-visual-qa.yml` | Chart 3 visual QA; independent downstream QA. |
| `company_nasdaq100.yml` | Company data maintenance; inspect write paths before deciding relation to report pipeline. |
| `company_profiles.yml` | Company profile maintenance; separate from report production unless it writes shared inputs. |
| `company_profiles_nasdaq100.yml` | Company profile maintenance; separate pending write-path audit. |
| `main.yml` | Legacy volatility/watchlist data writer using yfinance; not the TAC 44-item Stage 2 and must not be treated as its fallback. |
| `mother-template-guard.yml` | Mother-template validation; preserve as protection, not a production entry point. |
| `pages.yml` | Site deployment; retain as shared deployment service, but ensure publication-lock behavior and trigger ownership are correct. |
| `simulation-workflow-lint.yml` | Simulation workflow lint; preserve its branch scope and do not edit Simulation. |
| `tac-chart3-bootstrap.yml` | Chart 3 bootstrap; independent Chart 3 maintenance. |
| `tac-chart3-incremental.yml` | Chart 3 ALFRED incremental workflow; currently listens to successful completion of TAC production with marker/event filters. |
| `tac-chart3-ingest.yml` | Chart 3 ingest; inspect exact trigger and write paths before consolidation. |
| `tac-chart3-sp500-increment-merge.yml` | Chart 3 S&P 500 compact-history merge; downstream of report workflow. |
| `tac-chart3-stress-analysis-tests.yml` | Chart 3 stress-analysis tests; independent QA. |
| `tac-five-site-browser-poc.yml` | Browser proof-of-concept; not part of formal daily report. |
| `tac-market-source-capture.yml` | Explicitly Simulation-only 44-page capture experiment; do not use as Main Stage 2. |
| `tac-production.yml` | Current Main production workflow; sole intended production report entry, but currently mixes several stage responsibilities. |
| `tac-simulation-lab.yml` | Simulation production workflow mirrored on Main; its runtime checks out Simulation and can publish only its specified Preview handoff. Must remain untouched and be prevented from competing with Main production delivery. |
| `tac-simulation-run-monitor.yml` | Simulation monitor; do not repurpose as Main Watchdog. |
| `tac-sp500-increment-qa.yml` | S&P 500 increment QA; independent downstream QA. |
| `us-mmf-chart-visual-qa.yml` | Money-market-fund chart QA; independent. |
| `us-mmf-public-data-qa.yml` | Money-market-fund public-data QA; independent. |
| `volatility-sticky-columns.yml` | Volatility page/UI QA; independent. |

Do not delete or disable workflows based only on their names. Complete event, branch, path-filter, permissions, concurrency, and write-path analysis first.

### 3.2 Production assets present on Main

- `production/MASTER_WR.md`
- Six Stage WR files under `production/stages/`
- Contracts: DATA_SCHEMA, HANDOFF_CONTRACT, HTML_BUILDER_CONTRACT, MOTHER_TEMPLATE_QA, PUBLISH_CONTRACT, QA_CONTRACT, RUN_CONTRACT, SOURCE_POLICY, STATUS_ENUM
- Config: builder approval, homepage publication lock, mother-template manifest, report-data template, schedule config
- Two production mothers: Monday and weekday
- Stage runners: `create_run_fixture.py`, `stage_wr_preflight.py`, `run_stage2.py` through `run_stage6.py`, plus validators, receipts, Research Bundle, Builder and Chart 3 handoff
- Input schemas: Observation, screenshot Observation, report content
- Existing run directories for 2026-11-27 and 2026-11-30.

### 3.3 Run-state reality

The current `production/runs/` root contains four Run directories. The inspected 2026-11-30 Run directories contain only:
- `run-context.json`
- `stage1-fixture.json`
- `report-data.json`
- `stage1-receipt.json`

No per-Run `run-state.json` exists in those inspected Run directories. The current RUN_CONTRACT v1.1 describes overall states `RUNNING`, `PARTIAL`, `FAILED`, `REVIEW_READY`, `DELIVERED`, `PUBLISHED`, but does not establish the proposed central per-Run transition ledger with current_stage / last_passed_stage / per-stage receipt references. Do not add a second state database; implement the minimum authoritative state representation only after defining its atomic update and concurrency semantics.

## 4. Current production execution path (verified from tac-production.yml)

1. Schedule events are received by `schedule-window`, which selects one DST-specific cron using the current New York DST state.
2. `capture-and-calendar` is one job with a 35-minute timeout.
3. That job installs Stage 1–3 dependencies and Chromium before creating the Run.
4. Stage 1 creates and commits the Run handoff.
5. The same job waits until 16:00 New York time, then polls Main for a date-global Stage 2 Observation for up to 15 minutes.
6. It validates Stage 1/2 Run identity and hashes, runs Stage 2 Runner to validate/freeze the 44-item snapshot, appends the S&P 500 increment if verified, runs Stage 3 and creates the Stage 4 Research Bundle.
7. It writes `capture-stage-receipt.json` with status `AWAITING_EDITORIAL_INPUT`, including full Stage 4 work instructions.
8. ChatGPT then produces date-global `production/input/report-content-YYYY-MM-DD.json` and a `[build-tac-report:YYYY-MM-DD]` commit marker.
9. The push event enters `build-and-deliver`, which validates the exact Run/content binding, runs Stage 4 validation, Stage 5 Builder/QA, and Stage 6 Preview delivery in one job.
10. Chart 3 incremental and S&P 500 merge workflows listen to successful completion of the production workflow and filter for main push + build marker.

This is a sequential two-worker handoff with a long-lived Capture job and a push-marker continuation, not a six-stage state-driven orchestration.

## 5. Verified incident evidence

### 2026-11-28 schedule run

- Workflow: `TAC main-native production pipeline`
- Run: `46096657083`
- Event: `schedule`
- Conclusion: `success`
- Jobs observed: `schedule-window` SUCCESS; `capture-and-calendar`, `build-and-deliver`, and `validate-main-production` SKIPPED.

This proves a schedule event reached Actions. It does not by itself prove the selected cron was the intended DST window; that requires reading the schedule-window job logs and comparing `github.event.schedule`, `expected_cron`, `new_york_now`, and output `should_run`.

### 2026-11-28 manual recovery Run

- Workflow Run: `46069359215`
- Run ID: `TAC-2026-11-30-46069359215-1`
- Stage 1 files were created and committed.
- Capture later failed while waiting for the current-Run Observation.
- Stage 2 and Stage 3 did not complete.

The ChatGPT task's recorded result shows it woke before the Stage 1 Run existed, reached BLOCKED, and ended. The later Stage 1 recovery did not cause a second ChatGPT Stage 2 invocation.

### PR #363

- Draft PR: https://github.com/lion-invlab/lion-invlab.github.io/pull/363
- Head SHA: `097ed608f779ffb2e1a9362b4f3c5e4c5ad4e457`
- Only changed file: `.github/workflows/tac-production.yml`
- Changes: move dependency/Chromium installation after Stage 1 handoff; validate Run ID, dates, Stage 1 file SHA-256 and pinned Stage 2 WR SHA before accepting Observation.
- Decision: do not merge as-is. Extract the valid Stage 1 fast-handoff and Run-bound Observation checks into the target design. The existing 15-minute wait remains an architectural defect and must not be carried forward as the primary handoff mechanism.

## 6. ChatGPT automation state (read from automation records)

### Main Stage 2–6 task

- Task ID: `Automation_f4da15cd95c881918c7412cdd6f35bb2`
- Current recorded state at audit time: enabled.
- Schedule: weekly Tue–Sat, 16:00 America/New_York (Taiwan winter 05:00 / summer 04:00).
- Last run: 2026-11-27 21:03:37Z to 21:05:49Z; recorded completed, content result BLOCKED.
- Current prompt still describes one combined worker: Stage 2, wait up to five minutes for Capture completion, then Stage 4–6. It is not split into independent Stage 2 and Stage 4 checkpoints.
- Its prompt also describes a 15-minute Main Capture wait, creating an unnecessary dependency on a long-running GitHub job.

### Calendar database task

- Task ID: `6af6d10c62448191819f04b976c64cf4`
- Current recorded state: enabled.
- Schedule: Tue–Sat, 15:35 America/New_York (Taiwan winter 04:35 / summer 03:35).
- Its role is the calendar JSON writer; Stage 3 must remain read-only.

### Chart 3 monitor task

- Task ID: `Automation_d59409d2de44819191030af1122bc0ec`
- Current recorded state: enabled.
- Schedule: Tue–Sat, 16:30 America/New_York (Taiwan winter 05:30 / summer 04:30).
- Prompt now says monitor/alert only; it must not initiate ALFRED or S&P 500 merge work. Keep it separate from the report's critical path.

Important: one previous automation run result reported that the Stage 2–6 task had been disabled by the failure handler. The current automation record read during this audit reports `is_enabled=true`. Treat the current record as the present setting; preserve the evidence of the prior unintended disablement as a recovery test case. No automation setting was changed during this audit.

## 7. Cross-stage responsibility matrix

| Stage | Required worker | Existing Main implementation | Current responsibility conflict |
|---|---|---|---|
| 1 | GitHub Actions | create_run_fixture.py inside capture job | Dependency install precedes Stage 1; no independently resumable Stage 1 completion |
| 2 | ChatGPT automation | ChatGPT Observation + run_stage2.py validator | GitHub job waits/polls for ChatGPT; Stage 2 not an independently terminating handoff |
| 3 | GitHub Actions | run_stage3.py + Research Bundle | Runs only after Stage 2 in same long-running job |
| 4 | ChatGPT automation | Editorial JSON + run_stage4.py | Same combined automation session as Stage 2; not a separately resumed checkpoint |
| 5 | GitHub Actions | run_stage5.py | Triggered by date marker push rather than state/receipt event contract |
| 6 | GitHub Actions | run_stage6.py | Same build job as Stage 5; should be separate logical stage but need not be separate workflow |

The target worker split remains fixed: GitHub Actions = Stages 1, 3, 5, 6; ChatGPT automation = Stages 2 and 4. Stage 2 must not be moved into GitHub Actions, and Stage 4 must not use an external LLM API.

## 8. Target architecture decisions to carry into design

1. One authoritative Run identity per report_date; no date-global file may serve as the identity of a Run.
2. Stage 1 must publish its minimal handoff and exit before heavy setup or downstream waiting.
3. Stage 2 and Stage 4 ChatGPT workers must be separate logical checkpoints. A worker that finds prerequisites absent returns a non-failure deferred result and remains enabled.
4. Stage 2 submission is not Stage 2 PASS. GitHub validates the Observation bundle, runs the Stage 2 receipt/freeze logic, then marks Stage 2 PASS and enables Stage 3.
5. Stage 3 reads the calendar DB at the pinned Main commit, and remains the sole Research Bundle producer.
6. Stage 4 consumes only the same Run's Stage 3 Research Bundle. It never re-fetches 44 market quotes or rebuilds calendar/earnings projections.
7. Stage 4 submission is not Stage 4 PASS. GitHub validates Editorial Content + WR/Research Bundle bindings before Stage 5.
8. Stage 5 and Stage 6 remain logical stages with separate receipts; they may execute as sequential Jobs in one workflow after their contracts are proven.
9. The system must not rely on a GitHub push triggering another workflow until token/connector behavior is experimentally demonstrated. GITHUB_TOKEN pushes must be treated as non-triggering unless proven otherwise.
10. Watchdog is observer/recovery coordinator only; it must not race the schedule or create a Run without atomic ownership.
11. Retry and Resume preserve run_id; explicit Rerun creates a new run_id and preserves prior artifacts.
12. Preview delivery is the terminal automated output. `main/index.html` remains protected pending explicit user approval.
13. Simulation remains read-only and is not an execution dependency for Main.

## 9. Known conflicts and P0 risks

- P0: Stage 1 is delayed by package/browser setup and is coupled to a long-running Capture job.
- P0: Stage 2/Stage 4 are combined in one ChatGPT automation; no independent second checkpoint.
- P0: Stage 2 Observation handoff depends on a date-global path and a long polling loop, even though payload validation checks Run binding later.
- P0: Current Run directories do not contain `run-state.json`; RUN_CONTRACT has no complete per-stage state transition ledger.
- P0: The Main workflow's schedule-window can report overall SUCCESS while skipping the production job; schedule event receipt is not production start.
- P0: `archive_index.yml` still has a scheduled trigger, despite publication lock requirements. Its trigger/lock semantics need to be reconciled before enabling new production.
- P1: Main `main.yml` still updates data via yfinance, unrelated to the formal 44-item Stage 2; confirm that no shared data/display path is misinterpreted as a fallback.
- P1: `tac-simulation-lab.yml` is mirrored on Main and can publish a Simulation-produced Preview; preserve Simulation but remove any ambiguity/competition in Main delivery ownership without editing Simulation.
- P1: Chart 3 workflows are separate downstream tasks and must remain outside the Stage 4–6 critical path.
- P1: Workflow-level concurrency currently serializes by ref, while run uniqueness is checked by scanning existing directories; a true atomic ownership primitive must be selected and tested before changing this.

## 10. Implementation order

### A. Finish read-only inventory
- Extract all 24 workflow trigger, branch, path, permissions, concurrency and write-path contracts.
- Inspect all six Stage runners and all direct helper calls.
- Inspect every existing Run receipt and state format.
- Inspect all automation task records and prompts.
- Read the original Gemini/Claude diagnostic files if present in Main or the conversation file library; do not infer their full contents from a summary.
- Inspect Pages, Archive and Chart 3 workflow_run event behavior.

### B. Finalize contracts before code changes
- Run identity and atomic lock semantics.
- State transition table and legal transitions.
- One Receipt per Stage; artifacts are referenced by receipt, not duplicate evidence ledgers.
- Stage 2 submit → GitHub validate/pass → Stage 3 trigger.
- Stage 3 pass → Stage 4 ChatGPT checkpoint.
- Stage 4 submit → GitHub validate/pass → Stage 5 → Stage 6.
- Deferred state and resume semantics.
- Explicit rerun policy and immutable prior-run evidence.

### C. Build on this isolated branch
- First code change only after the above contracts are approved internally against all current WR/schema/Runner consumers.
- Add tests before replacing existing workflow behavior.
- Keep Main production schedules, automation schedules, formal capture, PR merge, Preview publication and homepage untouched until separate approval.
- Do not edit Simulation.

## 11. Non-goals

- No additional permanent database.
- No additional daily schedule unless an existing checkpoint cannot satisfy the tested timing.
- No new external service or always-on poller.
- No third-party market API or Cloudflare bypass.
- No external LLM API for Stage 4.
- No second 44-item market capture.
- No duplicate calendar store.
- No Chart 3 precondition for report delivery.
- No lowering QA standards.
- No Main homepage update.

## 12. Root-cause confirmation from exact incident logs

### 12.1 Stage 1 handoff was delayed by heavy setup before Run creation

Workflow Run 46069359215, job capture-and-calendar (140742318218), completed steps in this order:

1. Checkout main.
2. Set up Python.
3. Install Stage 1–3 dependencies, including Playwright and Chromium.
4. Refresh main.
5. Resolve report date / Run ID.
6. Create Stage 1 Run.
7. Commit the four Stage 1 handoff files.
8. Wait for Stage 2 Observation.

The Stage 2 worker was scheduled at 16:00 ET (Taiwan 05:00 winter) and its prompt allows only five minutes for the Stage 1 handoff. The automation record shows it woke at 21:03:37Z and completed at 21:05:49Z with BLOCKED because the Run did not yet exist. The GitHub capture job did not reach its Stage 2 wait-window log until 2026-11-27 21:18:36Z (16:18:36 ET), then polled until 21:33:41Z and failed because no Observation was published.

**Confirmed primary root cause:** Stage 1 is not lightweight in execution. Installing Python packages and downloading/installing Chromium happens before Run creation and consumes the Stage 2 worker's five-minute handoff window. The workflow then waits for a worker that has already exited. The 15-minute poll cannot recover a one-shot worker. This is a deterministic ordering/timing defect, not a market-source issue and not evidence that the Stage 2 instructions themselves were skipped.

PR #363's move of heavy dependencies/Chromium to after Stage 1 is directionally correct and should be carried into the rebuild, but only as one part of the state-driven architecture; do not merge PR #363 as-is.

### 12.2 Duplicate Run recovery failure is a separate consequence

Workflow Run 46074632631, capture job 140766054677, was on attempt 2 and failed during the same-date recovery guard with:

Cannot supersede 2 prior Runs for 2026-11-30; manual reconciliation required.

Main contains two 2026-11-30 Run directories:
- TAC-2026-11-30-46069359215-1
- TAC-2026-11-30-46074632631-1

The latter is the earlier attempt's Run directory; retrying the workflow creates another workflow attempt, not a continuation of the previous Run. The current workflow's report-date scan treats all same-date Run directories as undifferentiated prior Runs and refuses recovery when there is more than one. It does not consult a per-Run authoritative state ledger to distinguish active, failed-before-Stage2, recoverable, superseded, or delivered Runs.

**Confirmed secondary root cause:** workflow attempt identity, Run identity, and same-date recovery selection are not represented by one authoritative state machine. A workflow retry can leave a second Stage 1 Run directory, after which the recover guard cannot safely choose the correct predecessor. Do not delete or overwrite either Run; preserve both as incident evidence.

### 12.3 Why extending the timeout is not a repair

- Stage 2 worker's five-minute wait is a prerequisite check, not an asynchronous queue.
- GitHub's 15-minute polling loop cannot wake or replay a completed ChatGPT automation.
- Increasing either timeout only prolongs a deadlock and risks stale date-global Observation consumption.
- The correct repair is to make Stage 1 complete and publish quickly, let Stage 2 run independently, and have each later Stage consume a committed handoff/state checkpoint. A deferred worker must be safely re-invokable without creating another Run.

## 13. Additional contract and runtime mismatches

1. Stage 1 WR requires Run creation and remote publication before Stage 2 starts. The implementation violates the intended timing by installing the full Stage 1–3 browser stack first.
2. RUN_CONTRACT v1.1 requires one active Run per report_date, recover from the last valid Stage, and immutable old evidence. The workflow implements this by scanning directory names and refuses all multiple-prior-Run cases; there is no durable state to determine which Run owns the date or where it stopped.
3. ChatGPT writes a date-global Stage 2 Observation file at production/input/market-history-web-observations-YYYY-MM-DD.json; Stage 2 Runner later validates that it contains the exact Run ID and Stage 1 hashes. A shared date-level path is a mutable rendezvous point and cannot safely represent retries/reruns or overlapping attempts. Target design must use a Run-scoped handoff path; any date-level alias, if retained for compatibility, must never be the source of truth.
4. Date-global Stage 4 editorial input at production/input/report-content-YYYY-MM-DD.json has the same concurrency and stale-input risk. It must be Run-scoped or carry an immutable exact Run identity and be atomically committed without replacing another Run's content.
5. production/config/schedule.json still declares Monday–Friday 05:25 for daily reports and Monday–Friday for calendar/Chart3, while the operational requirement is Tuesday–Saturday, Stage 1 at 04:45 winter / 03:45 summer, Stage 2 at 05:00 winter / 04:00 summer, calendar writer at 04:35 winter / 03:35 summer, and Chart3 monitor at 05:30 winter / 04:30 summer. README states the workflow, not the stale run_daily_report.py path, is the entry point. Treat schedule.json as stale documentation/config and reconcile it in the rebuild; do not change live schedules in this phase.
6. archive_index.yml has a daily schedule and manual dispatch with contents: write; its job runs verify_homepage_publication_lock.py --require-approved before archiving. It can mutate history/ independently of the new Stage 6 preview delivery and needs to be gated by an explicit publication/archive authorization model before production activation.
7. pages.yml deploys on preview/history/research/chart data pushes and workflow_dispatch. It has pages: write and id-token: write, but only contents: read. Stage 6's current explicit Pages dispatch and remote public-URL verification are compatible in principle; deployment event correlation must be by exact payload commit, not merely latest Pages run.
8. main.yml and company_nasdaq100.yml have scheduled/manual writers using yfinance and write data files. They are not Stage 2 fallbacks. Their output paths must be excluded from formal 44-item capture and report inputs unless an explicit contract names them.
9. tac-simulation-lab.yml is mirrored on Main but its job checks out the Simulation branch and can publish a Simulation Preview handoff to main. Preserve the Simulation branch unchanged; in the Main rebuild, document and test a non-overlapping delivery namespace/ownership boundary so the two flows cannot overwrite each other's preview artifacts.
10. Chart 3 ALFRED incremental and S&P 500 merge workflows listen to successful completion of TAC production and filter for a Main push carrying the build marker. Chart 3 is not a prerequisite for the report; the trigger must be updated to the final Stage 6 delivery event/state and remain non-blocking.

## 14. Exact target handoff design

The target flow remains six logical stages with four GitHub stages and two ChatGPT stages:

| Stage | Worker | Input | Durable output | Next action |
|---|---|---|---|---|
| 1 | GitHub Actions | report date, main commit, governance, mother, calendar pin | one Run context, blank fixture, Stage 1 receipt, state STAGE1_READY | exit immediately; Stage 2 worker may start |
| 2 | ChatGPT automation | exact Run-scoped Stage 1 handoff, full Stage 2 WR, current screenshots if supplied | Run-scoped 44-row Observation + FedWatch + provenance, state submission STAGE2_SUBMITTED | stop; no waiting for Stage 3 |
| 2 validation / 3 | GitHub Actions | exact Run-scoped Observation | frozen market snapshot, Stage 2 receipt, Stage 3 calendar/earnings projection, Research Bundle, state STAGE3_READY | exit; Stage 4 worker may start |
| 4 | ChatGPT automation | same Run's Research Bundle and Stage 4 WR | Run-scoped editorial JSON + source evidence, state submission STAGE4_SUBMITTED | stop; no build-marker race |
| 4 validation / 5 / 6 | GitHub Actions | same Run's editorial handoff | Stage 4 receipt, Stage 5 HTML/QA receipt, Stage 6 three-file preview + public URL verification | final state DELIVERED / AWAITING_APPROVAL |

Stage 2/4 submission and GitHub validation are distinct. A submission never marks a Stage PASS. Each worker can be awakened more than once; an absent prerequisite returns DEFERRED without creating a Run or permanently disabling the worker. A recovery invocation selects the exact existing Run and resumes from its last validated stage. Only an explicitly approved rerun creates a new Run.

### Minimum state record

Use one per-Run authoritative run-state.json (no separate state database), atomically updated with:
- run_id, report_date, production_date, trading_date
- main_commit_sha, workflow_run_id, workflow_run_attempt
- current_stage, last_passed_stage, overall_status
- each Stage's status, attempt, started_at, completed_at, input_sha256, output_sha256, receipt_path, error_code
- supersedes_run_id only for an explicit recovery/rerun lineage, not as a substitute for state.

Legal stage states should be small and non-overlapping: NOT_STARTED, READY, RUNNING, SUBMITTED, PASS, DEFERRED, PARTIAL, FAILED, SKIPPED. Overall states: RUNNING, PARTIAL, FAILED, REVIEW_READY, DELIVERED, AWAITING_APPROVAL, PUBLISHED. Every transition must compare the expected previous state/version and update atomically; two workers must never both acquire the same stage.

### Ownership / trigger rules

- Stage 1 is the only creator of a normal Run. It must run before heavy setup, publish the Run handoff, and exit.
- Stage 2 ChatGPT task is a scheduled/conditional worker only; it never creates a Run and never waits for the whole Capture workflow.
- GitHub's Stage 2 validator owns promotion from STAGE2_SUBMITTED to Stage 2 PASS and then Stage 3.
- Stage 3 GitHub job exits after Research Bundle and Stage 3 PASS.
- Stage 4 ChatGPT task is a separate checkpoint; it never waits for Stage 5/6.
- GitHub validates Stage 4 submission and owns Stage 4 PASS before Stage 5.
- Stage 5 and Stage 6 may remain sequential jobs within the same continuation workflow but must each write their own receipt and state transition.
- GITHUB_TOKEN push events are not assumed to trigger another workflow. Use an explicit dispatch/continuation mechanism only after testing its permissions and exact event correlation. A safe polling/watchdog may observe state but cannot create competing Runs.
- Preview is the automated terminal deliverable. Home page and archive remain separate approval-gated actions.

## 15. Updated implementation order

1. Finish contract/schema/runner call-graph audit and reconcile all path names and WR pins.
2. Define the exact atomic claim/update method using GitHub's supported primitives; test races on an isolated branch without dispatching production.
3. Add per-Run state and stage receipt validators; make same-date duplicate detection state-aware and idempotent.
4. Move all heavy Stage 1–3 dependencies after Stage 1 commit; Stage 1 must not install Chromium.
5. Replace date-global Stage 2 and Stage 4 files with Run-scoped immutable handoffs; update schema/validators/tests.
6. Split ChatGPT work into two independently resumable logical checkpoints (Stage 2 and Stage 4); keep live automation prompt/schedule unchanged until separately authorized.
7. Split GitHub workflow into short Stage 1, Stage 2/3 continuation, and Stage 4/5/6 continuation jobs/workflows, with exact run-state triggers; never use a long wait as a handoff.
8. Add recovery/resume, concurrency, stale-input, duplicate-attempt and push-token non-trigger tests.
9. Run full isolated fixture E2E and visual QA; then live-data E2E only after separate approval.
10. Request approval for live automation/schedule cutover, PR merge, formal report production, Pages/preview release, and any homepage/archive publication.


## 10. Confirmed schedule-window root cause (workflow run 46096657083)

The schedule-window job log was retrieved directly from GitHub Actions job 140829445307.

Observed values:
- Workflow event: `schedule`.
- `github.event.schedule` / `SCHEDULE_CRON`: `45 19 * * 1-5`.
- The job's New York timezone calculation selected the winter expected cron: `45 20 * * 1-5`.
- The workflow's decision is exact string equality: `should_run = actual_cron == expected_cron`.
- Therefore `should_run=false`; `capture-and-calendar` was skipped by its `needs.schedule-window.outputs.should_run == 'true'` condition. The overall workflow can still conclude SUCCESS because the skip is intentional under the job condition.

This is the direct, evidenced reason that this particular schedule event did not start Stage 1. It is not a GitHub schedule delivery failure. The workflow contains both summer and winter UTC cron entries, and the summer entry did fire on the winter date; the DST selector correctly rejected that wrong seasonal entry. The incident must not be described as "the schedule never fired."

The schedule selector currently evaluates New York DST at job execution time, not against an immutable scheduled-instant value. Queue delay and duplicate seasonal cron events therefore need explicit treatment in the target design. Do not solve this by simply removing the equality check or accepting both cron strings: that would permit early Stage 1 starts. The approved design must produce exactly one Taiwan-local 04:45 Stage 1 start and record the selected event/target local instant. Any live schedule change remains gated by owner approval and the production cutover gate.

## 11. Additional architecture findings from the isolated rebuild branch

The rebuild branch now contains a per-Run state implementation absent from the Main baseline inspected at `d401f31bdd2c016ff5497934ac5230c08763c551`:
- `production/runner/run_state.py` defines six canonical stage states, transition validation, version increments, receipt references and lease fields.
- `create_run_fixture.py` initializes `run-state.json` with Stage 1 PASS and Stage 2 READY.
- Stage 2–6 runners import and update the state machine in the rebuild branch.
- `validate_stage2_run_handoff.py` requires the Run state file and verifies Stage 2 SUBMITTED with the exact Run-scoped observation SHA.

This is a useful implementation direction, but the state module itself is storage-agnostic: its own docstring requires the caller to persist with compare-and-swap semantics. The current workflow uses git fetch/merge/rebase/push loops; these are not yet a formal atomic lease/CAS protocol for concurrent writers. The state design must not be considered race-safe until one authoritative writer/update mechanism and stale-version conflict behavior are tested.

The current Main baseline's `run_stage2.py` and the rebuild branch's `run_stage2.py` are not identical. The audit and all subsequent code changes must pin the exact branch/ref and blob SHA being inspected; do not mix Main and rebuild-branch evidence.

## 12. Cross-contract contradictions and missing integration proof

1. **Schedule manifest drift:** `production/config/schedule.json` still describes daily report production as Monday–Friday at 05:25 and Chart 3 at 05:30, while the approved cadence is Taiwan Tuesday–Saturday with Stage 1 at 04:45 winter / 03:45 summer, Stage 2 at 05:00 winter / 04:00 summer, and Preview target 05:30 winter / 04:30 summer. The file also says `NOT_CUT_OVER`. This is a configuration/documentation inconsistency, not permission to change a live schedule.
2. **Stage 2 handoff path:** the current workflow must use the exact Run-scoped `production/runs/<run_id>/market-history-web-observations.json` and verify Stage 2 SUBMITTED state plus SHA. Date-global `production/input/market-history-web-observations-<date>.json` must not be accepted as the authoritative handoff or allow another Run to consume it.
3. **Stage 2/3 ownership:** the current workflow still keeps a long-running job waiting for ChatGPT Stage 2 and then runs Stage 2 validation/freeze and Stage 3. The worker boundary is not event-driven; a missed ChatGPT wake is not automatically retried by GitHub.
4. **Stage 4 ownership:** Stage 4 requires Run-scoped editorial content, exact Stage 3 receipt SHA, research bundle SHA and Stage 4 WR attestation. The workflow must not launch Stage 4 merely because a date-global content file or generic push marker exists.
5. **Stage 5/6 readiness:** Builder exact-blob approval, four-category QA, Preview remote readback, Pages deployment and public URL verification are separate acceptance facts. A single workflow conclusion SUCCESS is insufficient evidence of delivered Preview.
6. **State semantics:** `run_state.py` currently allows `DEFERRED` as an active state and `FAILED` recovery only through an explicit transition flag. The orchestrator must define when deferred work is retried, lease expiry handling, and how a stale worker is prevented from overwriting a newer state version. No second state database is needed.
7. **Run lock:** per-report-date uniqueness is currently checked by reading committed Run directories before creating the new one. That check is not atomic across two concurrent workflows. The target needs an atomic reservation/lock before either writer can create a Run; Git push conflict/retry alone is not a sufficient lock contract.
8. **Automation wake-up:** GitHub Actions cannot directly assume it can wake a scheduled ChatGPT automation. The supported design must use the existing ChatGPT worker schedule/checkpoint plus bounded state polling/retry, or a separately approved integration. A push marker must not be treated as proof that ChatGPT executed Stage 4.
9. **Schedule manifest and actual cron:** the winter/summer cron entries must be validated against Taiwan local time and weekday mapping with deterministic tests covering both DST transitions, Saturday production, holidays and delayed workflow starts.

## 13. Immediate implementation order

1. Finish the 24-workflow trigger/permission/concurrency/write-path matrix and identify every writer that can touch Preview, index, archive, calendar, Chart 3 or production Run artifacts.
2. Finish the six Stage WR / nine contract / Manifest / Runner call-graph crosswalk. Record exact path, input, output, receipt, state transition, owner and retry behavior for each stage.
3. Define and test the minimal atomic Run reservation and state compare-and-swap protocol. Use one Run state file; do not add a second state store.
4. Define a reliable Stage 1 → Stage 2 and Stage 3 → Stage 4 worker checkpoint contract, including delayed/missed wake recovery without indefinite polling or manual "continue".
5. Refactor the single long Capture job into resumable stage jobs/checkpoints only after the contracts and deterministic tests are complete.
6. Add an isolated end-to-end test harness using synthetic fixtures; no live market capture and no schedule activation during architecture development.
7. Run Main-only deterministic tests and both mother-template test paths; preserve Main homepage, current Preview, calendar DB, Chart 3 data and Simulation.
8. Produce a draft PR and a precise acceptance report. Do not merge or activate schedules without owner approval.


## 14. Final root cause of the 2026-11-28 Stage 1 failure — confirmed from both schedule runs

The full workflow run list and both relevant job logs are now available. The earlier schedule-window finding was only the first of two events; it was not the complete incident explanation.

### Schedule event A — summer UTC cron, correctly rejected
- Workflow run: `46096657083`
- Event: `schedule`
- `github.event.schedule`: `45 19 * * 1-5`
- New York was on winter time; the selector expected `45 20 * * 1-5`.
- `schedule-window` succeeded with `should_run=false`; Capture was skipped.
- This was the wrong seasonal cron event and was correctly rejected.

### Schedule event B — winter UTC cron, reached Stage 1 but failed before creating a Run
- Workflow run: `46100523727`
- Event: `schedule`
- `schedule-window`: SUCCESS; `capture-and-calendar`: FAILURE.
- Failure step: `Resolve report date and unique Run ID`.
- Exact error: `Run already exists for 2026-11-30; use the explicitly authorized recover/rerun mode.`
- Stage 1 create and publish steps were SKIPPED. Therefore the correct winter schedule did fire; Stage 1 did not create a new Run because the resolver treated old, unstateful Run directories as authoritative conflicts.

### The two blocking legacy Run directories

Both directories were inspected from Main and have the same report_date but no `run-state.json`:
- `TAC-2026-11-30-46069359215-1`: created by `workflow_dispatch` run 46069359215, which failed.
- `TAC-2026-11-30-46074632631-1`: created by `workflow_dispatch` run 46074632631, which failed on attempt 2.

Each contains only `run-context.json`, `stage1-fixture.json`, `report-data.json`, and `stage1-receipt.json`. Neither has an authoritative six-stage state ledger, Stage 2/3 completion, or a complete recoverable Run. The ChatGPT Stage 2 automation correctly refused to treat these manual-dispatch leftovers as the scheduled Stage 1 Run.

**Actual root cause:** failed legacy manual-dispatch attempts left same-report-date Stage 1 fixture directories without `run-state.json`; the Main schedule resolver rejected any matching `run-context.json` directory instead of distinguishing legacy artifacts from authoritative stateful Runs. The correct winter schedule did run. The failure is in Run selection/legacy collision handling, not in a missing winter cron.

### Fix implemented in the isolated refactor branch

- The Stage 1 resolver now treats a Run as authoritative only when its `run-state.json` exists and validates. Legacy directories without state are never resumed, overwritten, or consumed.
- A fresh scheduled Run may be created when the only same-date matches are legacy/unstateful directories.
- `create_run_fixture.py` records those IDs in `run-context.json.legacy_prior_run_ids` for traceability; it does not mutate or delete them.
- Added deterministic `collect_legacy_prior_run_ids` helper and unit test proving that only same-date, non-current, unstateful Run directories are recorded as legacy.
- The workflow's Stage 1 resolver in the refactor branch applies the same distinction: old legacy Runs do not block a new schedule Run; a stateful Run still requires explicit recover/rerun policy.

This resolves the exact collision observed on 11/28 without reusing the failed Runs or changing the live schedule.

## 15. Additional code changes and isolated CI validation

Branch: `refactor/tac-main-e2e-architecture-20261128`

- Added `production/runner/accept_stage_submission.py`: a single GitHub-owned acceptance step for ChatGPT Stage 2 and Stage 4 artifacts. It verifies exact Run identity and upstream SHA bindings, then performs READY → RUNNING → SUBMITTED and writes `run-state.json` atomically.
- Updated the Stage 2 and Stage 4 WRs plus `HANDOFF_CONTRACT.md`: ChatGPT workers submit only their Run-scoped artifact and sidecars; the GitHub production workflow is the sole writer of `run-state.json`. This removes a second writer and avoids a state/artifact commit race.
- Split the workflow into a dedicated lightweight `stage1-create-run` job that preflights Stage 1 WR before report-date/Run resolution, commits and reads back the Run handoff, then exits. `stage2-and-stage3` is a separate downstream job; `build-and-deliver` depends on it.
- Added a workflow-structure regression test proving Stage 1 has no Stage 2 dependency installation, Stage 2/3 depends on Stage 1, and Stage 4–6 depends on Stage 2/3.
- Updated the Stage 2 and Stage 4 workflow handoff steps to call the acceptance runner and persist state before invoking Stage 2/4 validators.
- Restored the 16:00 ET gate before the Stage 2 observation polling window; otherwise the 15-minute timeout could expire before the 16:00 ET worker wake.
- Added deterministic tests for Stage 2 44-row identity, Stage 4 Research Bundle/Stage 3/WR binding, and the legacy Run classifier.
- Added the new acceptance runner and test to the governance blob pin list and PORT_MANIFEST.
- Updated the schedule manifest to the approved Tue–Sat Taiwan cadence while leaving `cutover_status=NOT_CUT_OVER`; no live schedule was changed.

### Validation result

GitHub Actions validation run `46104298636` on commit `4b5e612fa2ee3e56e05b85784a093b00e95b34b4` completed SUCCESS for the prior handoff implementation. The later Stage 1 job split and WR preflight ordering are under a new isolated validation run `46104811908`. The validation job passed: Python compile, browser QA syntax, SHA-locked mother/manifest validation, Stage 2 and pre-build deterministic tests, Builder and earnings tests, isolated candidate Builder, and mother-owned DOM checks. Subsequent branch changes were documentation-only (audit wording and removal of superseded prompt v1.2); no runtime code changed after this successful validation.

### Cutover dependency not yet applied

The currently enabled ChatGPT automation prompt is still the old Main prompt. It instructs Stage 2 to write a date-global observation file and Stage 4 to write a date-global editorial file / build marker. Before this branch can become the active production path, that prompt must be updated to:
1. write `production/runs/<run_id>/market-history-web-observations.json` for Stage 2;
2. write `production/runs/<run_id>/stage4-editorial-content.json` for Stage 4;
3. never write `run-state.json`; GitHub's acceptance runner is the only state writer;
4. treat the Stage 4 marker as an optional audit label, not a workflow trigger.

A revised prompt is prepared at `production/CHATGPT_AUTOMATION_PROMPT_MAIN_v1.3.md`; it now matches the artifact-only worker / single GitHub state-writer contract. The active automation prompt and its schedule have not been changed. Applying v1.3 remains a required cutover step after the code and CI pass; do not merge/activate the branch before it is coordinated.


## 16. 24-workflow ownership and write-path audit

All 24 workflow files in `.github/workflows/` were inventoried. The following is the operational ownership map; it distinguishes report-critical writers from independent data and QA pipelines.

| Workflow | Trigger family | Write/deploy scope | Main E2E relationship |
|---|---|---|---|
| `archive_index.yml` | weekday schedule, main `index.html` push, manual | `history/` only; requires approved homepage publication lock | Does not write homepage or preview |
| `chart2-preview-browser-qa.yml` | manual, PR, selected push paths | QA artifacts only | Non-blocking QA |
| `chart3-preview-visual-qa.yml` | manual, workflow_run, PR, selected push paths | QA artifacts only | Non-blocking QA |
| `company_nasdaq100.yml` | manual, schedule | `data/nasdaq100_volatility.json` | Independent data writer; not Stage 2 source |
| `company_profiles.yml` | manual, Saturday schedule | `data/company_profiles.json` | Independent data writer |
| `company_profiles_nasdaq100.yml` | manual, Saturday schedule | `data/company_profiles.json` | Second writer to same file; see P2 risk below |
| `main.yml` | manual, weekday schedule | legacy volatility/watchlist data under `data/` | Legacy yfinance writer; never Stage 2 fallback |
| `mother-template-guard.yml` | main push, PR, manual | read-only guard | Retain |
| `pages.yml` | selected main push, manual, Chart 3 workflow_run | GitHub Pages deployment only | Shared deploy service; serialized by `pages` concurrency |
| `simulation-workflow-lint.yml` | Simulation workflow push paths | read-only lint | Does not alter Simulation |
| `tac-chart3-bootstrap.yml` | manual | Chart 3 baseline under `data/tac-chart3/` | Manual initialization only |
| `tac-chart3-incremental.yml` | manual, workflow_run | FRED/ALFRED Chart 3 series under `data/tac-chart3/` | Downstream; shares data-maintenance concurrency with merge |
| `tac-chart3-ingest.yml` | manual | ingest artifacts; no production report handoff | Separate Chart 3 ingest |
| `tac-chart3-sp500-increment-merge.yml` | manual, workflow_run | merges verified S&P 500 increment into Chart 3 history/manifest | Downstream consumer; must not refetch S&P 500 |
| `tac-chart3-stress-analysis-tests.yml` | selected push paths | test artifacts only | Non-blocking QA |
| `tac-five-site-browser-poc.yml` | manual | browser evidence artifacts only | POC; not Main Stage 2 |
| `tac-market-source-capture.yml` | manual | isolated capture evidence artifacts | Simulation experiment; not Main Stage 2 |
| `tac-production.yml` | seasonal UTC schedule, selected code push, manual recover/rerun | Run evidence, S&P 500 increment ledger, Main preview namespace | Sole Main production owner |
| `tac-simulation-lab.yml` | Simulation branch push, manual | Simulation branch evidence and legacy `preview/` triplet; explicit Pages dispatch | Separate Simulation owner; no Main homepage write |
| `tac-simulation-run-monitor.yml` | every-5-minute schedule, Simulation push, manual | monitor/report only | No Run ownership or report writes |
| `tac-sp500-increment-qa.yml` | selected data push/workflow events | QA artifacts only | Validates Chart 3 increment; no data write |
| `us-mmf-chart-visual-qa.yml` | selected push/workflow events | QA artifacts only | Independent QA |
| `us-mmf-public-data-qa.yml` | schedule/manual | QA artifacts only | Independent QA |
| `volatility-sticky-columns.yml` | selected push/PR | QA artifacts only | Independent UI QA |

### Writer collision resolution

- **Main Preview vs Simulation Preview:** the Main Stage 6 runner uses `preview/main/<date>-review.*`; the Simulation workflow continues to use `preview/<date>-review.*`. This isolates the two writers. Pages is a shared deployment service, not a file writer, and serializes deployments.
- **S&P 500 / Chart 3:** Stage 2 is the only source writer for the daily S&P 500 increment. Chart 3 merge is a downstream consumer. Chart 3 FRED/ALFRED incremental updates and S&P 500 merge share `tac-chart3-data-maintenance` concurrency. Chart 3 failure remains non-blocking for Stage 4–6.
- **Official homepage:** TAC Main Stage 6 is restricted to the Main preview triplet. The official `index.html` remains protected by the homepage publication lock. `archive_index.yml` reads approved homepage versions and writes only `history/`.
- **Legacy data:** `main.yml` and company data workflows continue to write separate `data/` files. Main Stage 2 does not read these outputs and cannot use them as fallback.

### Remaining non-critical writer risk

`company_profiles.yml` and `company_profiles_nasdaq100.yml` both write `data/company_profiles.json` under separate workflow concurrency groups, scheduled 20 minutes apart on Taiwan Sunday morning. This is a potential lost-update race for company profile data, but it is outside the TAC Stage 1–6 critical path and does not write report Run, Preview, calendar or Chart 3 S&P 500 increment artifacts. It is recorded as P2 and is not expanded into the Main rebuild scope.

### Main preview / Pages contract

The Main preview namespace is nested at `preview/main/`; the Pages workflow's legacy `preview/*.html` push path filter does not match nested files. Stage 6 therefore explicitly dispatches `pages.yml` after committing its three-file Main preview triplet, waits for the exact Pages workflow run, then reads the public Main preview URL and verifies the report date. This is intentional and must remain explicit.
