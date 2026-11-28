# TAC Main E2E Architecture — Read-only Audit (2026-11-28)

## 1. Scope and safety

- Repository: `lion-invlab/lion-invlab.github.io`
- Audited branch: `main`
- Audit branch: `rebuild/tac-main-e2e-architecture-20261128`
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
