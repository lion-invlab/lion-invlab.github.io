# TAC Main Orchestrator Architecture Decision

**Date:** 2026-11-28  
**Repository:** `lion-invlab/lion-invlab.github.io`  
**Target:** `main`  
**Build branch:** `rebuild/tac-main-autonomous-e2e-20261128`  
**Simulation:** `simulation/tac-process-lab-2026-11-06` — read-only

## 1. Purpose

Implement the existing Main rebuild plan as one autonomous Stage 1–6 production pipeline. This document is an architecture decision record, not evidence that implementation or E2E acceptance has passed.

## 2. Source recommendations being integrated

### Claude
- Make Stage 1 a lightweight, early Run creation and handoff.
- Downstream workers identify work only by exact `run_id`, report date and SHA-bound artifacts.
- Stage 2 and Stage 3 continue as independent handoffs; do not depend on date-global files.
- Recover from the last valid stage using Retry/Resume; do not repeat completed work.

### Gemini
- Use one central GitHub Actions Orchestrator.
- Enforce one Active Run for a report date.
- Use one authoritative `run-state.json` state machine.
- Require WR and Receipt preflight before each stage.
- Include a Watchdog for stalled or interrupted work.

### Existing user-approved Main constraints
- GitHub Actions owns Stage 1, 3, 5 and 6.
- ChatGPT owns Stage 2 and 4.
- Stage 4 must not use an external LLM API.
- Simulation is reference-only and must not be modified.
- The Main homepage and formal archive remain approval-gated.
- No schedule cutover or new recurring schedule without separate approval.

## 3. Decisions

1. **One entry point:** `.github/workflows/tac-production.yml` is the only Main production entry. Legacy workflows are inventoried and classified; no workflow is deleted solely by filename.
2. **One Orchestrator:** the production workflow coordinates the entire Run and owns every state transition. Python Stage runners perform stage work but do not create a competing pipeline.
3. **One Run identity:** `TAC-{report_date}-{workflow_run_id}`. Retries/resumes retain the Run ID; an explicitly authorized rerun receives a new workflow_run_id and preserves the previous Run.
4. **One state truth:** `production/runs/<run_id>/run-state.json`. No second state database, date-global handoff or duplicate receipt ledger.
5. **Single Active Run:** enforce a repository-wide Stage 1 concurrency reservation and verify the exact report-date candidate before creating a Run. The lock must be held only for reservation/creation, not for the entire report build. Existing Run state and leases govern downstream ownership.
6. **State persistence:** GitHub Actions is the sole state writer. Each transition checks expected state_version and previous status, writes atomically, then persists fast-forward-only. A stale version or non-fast-forward requires reload/re-evaluation; never force-push or blind replay.
7. **Stage 1 fast handoff:** run Stage 1 WR preflight before date/Run resolution; use standard-library/Git operations only; commit and remotely read back context, blank-first fixture, receipt and initial state; exit before heavy dependency installation or waiting.
8. **Worker artifacts are submissions, not PASS:** ChatGPT Stage 2/4 writes only its own Run-scoped artifact and verifies its bytes SHA. GitHub validates the artifact, upstream receipt, WR attestation and exact Run binding before advancing the state.
9. **Stage sequence:** Stage 1 PASS → Stage 2 submission/validation → Stage 3 projection → Stage 4 submission/validation → Stage 5 Builder/QA → Stage 6 Preview delivery.
10. **Watchdog without a second scheduler:** implement stall detection and safe recovery inside the existing Orchestrator/recovery path. It observes state, receipts, leases and workflow status; it never creates a competing Run or steals an unexpired lease.
11. **Wake-up constraint:** retain the existing ChatGPT task and schedule during the build. Its execution must handle the Stage 2 and Stage 4 checkpoints against the same Run, with Stage 4 eligible only after Stage 3 PASS. A worker that exits DEFERRED cannot be assumed to wake itself later. The integration test must prove the actual worker can bridge the Stage 2→Stage 3→Stage 4 handoff without manual user input. If that cannot be proven with the existing task, record the exact platform limitation and seek approval before adding a second wake mechanism or schedule.
12. **No scope expansion:** Chart 3 remains a non-blocking downstream branch; calendar JSON remains single-writer/read-only to Stage 3; no Cloudflare bypass, third-party market API, external LLM API, new database, duplicate market capture or extra permanent QA gates.

## 4. Stage ownership and artifacts

| Stage | Owner | Required input | Canonical output / acceptance |
|---|---|---|---|
| 1 — Context | GitHub | Main governance, template Manifest, calendar snapshot | Run context, blank-first fixture, Stage 1 receipt, initial run-state |
| 2 — Market | ChatGPT; GitHub validates | Exact Stage 1 handoff and Stage 2 WR | Run-scoped 44-row Observation, FedWatch and evidence sidecars; GitHub promotes to PASS/PARTIAL |
| 3 — Calendar | GitHub | Stage 2 PASS/PARTIAL and Stage 1-pinned calendar JSON | Calendar/earnings projection, Research Bundle and receipt; Stage 3 PASS |
| 4 — News/Analysis | ChatGPT; GitHub validates | Same Run Research Bundle, frozen market snapshot, Stage 4 WR | Run-scoped editorial content; GitHub promotes to PASS |
| 5 — Render/QA | GitHub | Stage 2–4 artifacts, approved Builder and both mother-template contracts | Review HTML, QA sidecar, render manifest and Stage 5 receipt |
| 6 — Delivery | GitHub | Stage 5 PASS | Main Preview HTML, QA and delivery sidecars, remote SHA and public URL verification |

## 5. Acceptance sequence

- A: finish asset, workflow, runner, automation and write-path inventory.
- B: reconcile this design with MASTER_WR, six Stage WRs, schemas, contracts and runner consumers.
- C: implement the orchestrator/state/handoff changes on this isolated build branch.
- D: prove autonomous handoff and recovery using synthetic fixtures only.
- E: pass full synthetic Stage 1–6 E2E for both Monday and weekday templates, including deferred worker, stale artifact, duplicate trigger, interruption and resume cases.
- F: only after approval, run a fresh real-data E2E for the requested report date and deliver Main Preview.

## 6. Explicit non-actions

This branch does not change production schedules, active Automation prompts, formal market capture, `index.html`, archive history, Simulation, or the formal production flow. It is not merged into `main` until acceptance and separate cutover approval.
