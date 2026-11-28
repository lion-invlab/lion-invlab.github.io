# TAC Main ChatGPT Automation Cutover Contract

Status: PREPARED — NOT ACTIVE  
Applies to: Main Stage 2 and Stage 4 ChatGPT worker task  
Current task: `Automation_f4da15cd95c881918c7412cdd6f35bb2`  
Current schedule is not changed by this document.

## 1. Why the prompt must change

The currently enabled automation prompt still uses the old date-global Stage 2 and Stage 4 paths and the old build marker. The Main refactor workflow now accepts only exact Run-scoped artifacts. Leaving the prompt unchanged would make a successful worker output invisible to the active workflow.

The active task must not be edited until the Main code branch is approved for cutover. This document is the exact change specification for that cutover.

## 2. Stage 2 worker instructions

Before any capture:
1. Read the complete `production/stages/STAGE_2_MARKET.md` from the current Main ref.
2. Find the single Run for the target `report_date` that has a valid `run-state.json`. A directory with only `run-context.json` / Stage 1 fixture files and no `run-state.json` is a legacy artifact and is never a valid Run.
3. Read and SHA-256 bind `run-context.json`, `stage1-fixture.json`, `stage1-receipt.json`, and the exact Stage 2 WR pinned by Stage 1.
4. Capture the 44 market rows and independent FedWatch strictly under the Stage 2 WR. Preserve the existing Investing.com Historical Data rules, maximum four parallel page reads, screenshot priority/freshness, no Cloudflare bypass, no unapproved source substitution, and no cross-day screenshot reuse.

The only formal Observation path is:

`production/runs/<run_id>/market-history-web-observations.json`

All screenshots, CNN observation sidecars, source manifests and other Stage 2 evidence must be stored under that same Run directory and use the exact names/schema in Stage 2 WR.

Required root bindings include:
- `schema_version`
- `run_id`
- `report_date`
- `trading_date`
- `stage1_receipt_sha256`
- `run_context_sha256`
- `stage1_fixture_sha256`
- `stage2_wr_sha256`
- `captured_at_utc`
- exactly 44 unique `observations`
- independent `fedwatch` with matching Stage 2 WR attestation

The worker must:
- Commit the Run-scoped artifact and required sidecars.
- Read the committed files back from Main and verify their SHA-256 values.
- Report the exact Run ID, artifact paths, SHA values, and capture result.

The worker must NOT:
- Write or update `run-state.json`.
- Write or read `production/input/market-history-web-observations-YYYY-MM-DD.json`.
- Reuse another Run's observation, screenshot, FedWatch or evidence.
- Create a new Run, alter schedules, or modify the Main homepage.
- Use a push marker as a workflow trigger.

The GitHub production workflow is the sole state writer. It calls `accept_stage_submission.py --stage STAGE_2`, validates the exact Stage 1/WR/44-row/FedWatch bindings, and advances Stage 2 READY → RUNNING → SUBMITTED. The Stage 2 Runner then validates and freezes the market snapshot, advancing to PASS or PARTIAL.

## 3. Stage 4 worker instructions

After the exact same Run has Stage 3 PASS:
1. Read the complete `production/stages/STAGE_4_NEWS_ANALYSIS.md`.
2. Read the Run-scoped Stage 3 receipt, Research Bundle and Stage 2 market snapshot summary.
3. Verify all upstream SHA values before producing editorial content.
4. Follow the complete editorial requirements: five Global Focus News, ten Market Hot Headlines, three summary points, sentiment, five ordered analysis layers, six-domain political scan, evidence, concrete strategy, and all existing content/wording rules.

The only formal editorial path is:

`production/runs/<run_id>/stage4-editorial-content.json`

Required bindings include:
- `run_id`
- `report_date`
- `trading_date`
- `market_snapshot_sha256`
- `research_bundle_sha256`
- `stage3_receipt_sha256`
- `stage4_wr_sha256`

The worker must:
- Commit the complete Run-scoped editorial JSON.
- Read the committed file back and verify its SHA-256.
- Report the exact Run ID, artifact path, SHA, WR SHA and upstream receipt/bundle bindings.

The worker must NOT:
- Write or update `run-state.json`.
- Write or read `production/input/report-content-YYYY-MM-DD.json`.
- Create a `[build-tac-report:YYYY-MM-DD]` marker or assume a push will trigger another workflow.
- Start Stage 5/6 itself. The already-running GitHub workflow performs Stage 4 validation, Stage 5 Builder/QA and Stage 6 Preview delivery.

An optional commit-message audit label `[tac-stage4-submit:<run_id>]` is allowed, but it is not a trigger.

The GitHub production workflow calls `accept_stage_submission.py --stage STAGE_4`, validates Stage 3 PASS, exact Run/date/market snapshot/Research Bundle/Stage 3 receipt/Stage 4 WR SHA, and advances Stage 4 READY → RUNNING → SUBMITTED. The Stage 4 Runner then advances to PASS.

## 4. One task, sequential Stage 2 then Stage 4

Keep one Main worker task responsible for Stage 2 and Stage 4, sequentially:
1. Resolve the exact stateful Run.
2. Complete Stage 2 or safely skip it if the same Run is already PASS/PARTIAL.
3. Wait for the same Run's Stage 2/3 workflow completion; do not create another Run.
4. When Stage 3 is PASS, produce Stage 4 editorial content.
5. Stop after the Stage 4 artifact is committed and SHA-verified; GitHub continues Stage 4–6.

Retry/Resume always uses the same Run ID. A new Run ID is only for an explicitly authorized rerun.

## 5. Activation gates

Do not apply this prompt until:
- The Main refactor PR is approved and merged.
- Main workflow validation passes on the merged commit.
- The current Main Stage 2 and Stage 4 worker paths have been verified against the merged WR/contracts.
- The owner explicitly approves the formal production cutover.

Separate unresolved reliability decision:
- GitHub scheduled workflow run 46100523727 was created more than six hours after its intended 20:45 UTC cron. This is an observed schedule-delivery delay, not a Stage 1 code failure.
- The Stage 2 task currently wakes at 05:00 Taiwan and has only a short Stage 1 handoff tolerance. A late Stage 1 schedule event can therefore occur after the worker has exited.
- A bounded late-handoff recovery trigger (for example, an additional worker checkpoint or approved watchdog dispatch) would require an explicit scheduling/automation authorization. Do not silently add a new schedule or change the existing automation cadence.

