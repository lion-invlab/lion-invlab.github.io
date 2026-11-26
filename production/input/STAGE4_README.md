# Stage 4 editorial content handoff

The scheduled TAC content-research step writes one report-date input file. It must include the exact Stage 1 `run_id` and the `market_snapshot_sha256` printed in that Run's `stage2-run-summary.json`; Stage 4 refuses content from any other Run or changed market snapshot.

`production/input/report-content-YYYY-MM-DD.json`

It must validate against `report-content.schema.json` and be committed on main before Stage 4 runs. The file contains the exact three summary paragraphs, 5 Global Focus News, 10 Market Hot Headlines, sentiment text, five ordered market-analysis layers with internal source evidence, six-domain political scan, core observation, market observation, key levels and market commentary.

The news cutoff is Taiwan-local report time (target 05:25). Weekday window begins the previous calendar day at 12:00; Monday window begins Friday at 12:00. Every news item must carry its original publication time, source timezone and Taiwan-converted publication time. Do not substitute page update time for original publication time.

Stage 4 verifies that cited market rows are VERIFIED or BACKUP_VERIFIED, validates the shared time window and exact counts, then merges editorial content into the current Run fixture. It computes a before/after hash of all Stage 2 market data and fails if Stage 4 changes any market value or provenance.

Do not copy prior-day report text or news into a new input. The schema is a structure contract, not a source of facts.
