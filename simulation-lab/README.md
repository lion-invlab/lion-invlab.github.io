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

## Key-levels ownership and data contract (simulation)

**Responsibility boundary**
1. Market-data acquisition is the upstream owner: it must provide OHLC for the five US cash indices, with exact symbol, trading date, quote type, source name and HTTPS source URL. It must not substitute CFD or futures when the cash index is closed.
2. `simulation-lab/runner/key_levels_builder.py` owns validation and pivot calculations only. It does not scrape or invent quotes. It rejects missing/duplicate indices, mismatched dates/names, invalid OHLC, missing source attribution, and non-cash quote types.
3. The producer writes the single downstream contract to `key_levels.items` in the report JSON. `build_review_html.py` consumes only this contract and renders it; it does not retrieve prices or calculate pivots.

**Input contract**: `simulation-lab/fixtures/key-levels-ohlc-2026-11-09.json` is a normalized replay fixture. Each item requires `key`, `name`, `symbol`, `trading_date`, `high`, `low`, `close`, `quote_type=cash_index`, `source_name`, and `source_url`. The five required keys are `dow`, `sp500`, `nasdaq`, `sox`, and `russell2000`.

**Calculation**: `P=(H+L+C)/3`; `S1=2P-H`; `R1=2P-L`, rounded to two decimals using decimal arithmetic. The module preserves the input H/L/C, date, symbol and source link in the generated output.

**Important scope**: this fixture is deterministic test input, not live market data. The live acquisition module must populate the same normalized input contract from verified current OHLC before this producer is used in a live report. Until that connection exists, the workflow proves calculation and assembly only, not live retrieval.

Workflow order: normalized OHLC input → `key_levels_builder.py` → `report-data-*.json:key_levels` → `build_review_html.py`.