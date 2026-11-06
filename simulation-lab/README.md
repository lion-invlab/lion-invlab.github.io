# TAC Process Simulation Lab

- Branch: `simulation/tac-process-lab-2026-11-06`
- Base main commit: `f05c889857f66c7b6d5bf9c78325932f2eb39a55`
- Main WR v5.14 blob: `80d49eeaa54e16a18dc34416239e4b46664ba44b`
- Main Manifest blob: `fade5e3d88de76a79cb5c1656cc592b98827ab55`
- Main QA contract blob: `74a7c90aaaeee497b7b2b134d9569aee615d95c0`
- Isolation: no writes to main; no Pages deployment; no PR creation/merge; no repo settings or workflow configuration changes.

## Lab layout

- `simulation-lab/TAC_WORK_RULES_SIM.md`: working simulation rules; overrides at top, complete main v5.14 preserved below.
- `simulation-lab/baseline/`: frozen copies of the source manifest and QA contract.
- `simulation-lab/analysis/`: contradictions, failure taxonomy, and repair decisions.
- `simulation-lab/fixtures/`: deterministic replay inputs and injected failures.
- `simulation-lab/runs/`: per-run step evidence, output hashes, timings, and pass/fail.
- `simulation-lab/output/`: generated HTML and test artifacts only.

## Required experiment matrix

1. Current v5.14 direct-authoring workflow.
2. Existing repository Snapshot -> validation -> HTML-binding candidate (read-only evaluation; no assumption it is production-authorized).
3. Hybrid workflow: verified source evidence and reusable data ledger, then deterministic DOM-based template population and independent QA.

Run the same fixed input set and injected failures against each candidate. Select a repair only after comparative evidence.
