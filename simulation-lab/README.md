# TAC Process Simulation Lab

- Branch: `simulation/tac-process-lab-2026-11-06`
- Unified simulation WR: `simulation-lab/TAC_WORK_RULES_SIM.md` (SIM-1.2)
- WR merge basis: SIM-1.1 plus the simulation-branch v5.19 rules; the root-level simulation copy `TAC_WORK_RULES.md` is retired after migration.
- The unified simulation WR is the only authority for the 05:25 simulation report workflow. Do not read the main-branch WR as a second authority for that workflow.
- Main calendar database: `data/calendar/weeks/YYYY-Www.json` is the single shared authoritative source. The independent 04:35 calendar automation is its only writer; the 05:25 simulation report is read-only.
- Main writes remain narrowly separated: the authorized dated simulation review preview, and `index.html` only after explicit user approval under the unified WR. No other main assets may be modified.
- Simulation mother templates, Manifest and QA contract are frozen read-only baselines under `simulation-lab/baseline/`.

## Lab layout

- `simulation-lab/TAC_WORK_RULES_SIM.md`: the sole unified simulation Work Rules (SIM-1.2), including SIM-1.1 isolation/data gates and the v5.19 operational rules.
- `simulation-lab/baseline/`: frozen simulation copies of the approved mother templates, Manifest and QA contract.
- `simulation-lab/analysis/`: contradictions, failure taxonomy, and repair decisions.
- `simulation-lab/fixtures/`: deterministic replay inputs and injected failures.
- `simulation-lab/runs/`: per-run step evidence, output hashes, timings, and pass/fail.
- `simulation-lab/output/`: generated HTML and test artifacts only.

## Required experiment matrix

1. Current SIM-1.2 direct-authoring workflow.
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
