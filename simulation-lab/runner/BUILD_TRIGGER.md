# TAC SIM-1.4 Build Trigger

report_date: 2026-11-23
trading_date: 2026-11-20
iso_week: 2026-W48
report_cutoff_taipei: 2026-11-23T05:25:00+08:00
news_window_taipei: 2026-11-20T12:00:00+08:00/2026-11-23T05:25:00+08:00
trigger_scope: simulation-only
workflow: .github/workflows/tac-simulation-lab.yml
workflow_blob_sha: 745cef00ae7de8c7d1e3a558fa18cce5b6bb337f
active_rules_version: SIM-1.4
active_rules_blob_sha: 6ab8852582b81f9da0bca7e974fbf39847067aed
qa_contract_version: 1.21
qa_contract_blob_sha: e4a11261fba37fbd9deee7c6b61c9dc29a1966d6
manifest_blob_sha: d47d8abece4137884bda76d6a505ba4112904e0d
monday_mother_path: simulation-lab/baseline/monday-mother-template.html
monday_mother_blob_sha: 0a7d5095aaa99c470e00e67f33567ff9f359d6ae
weekday_mother_path: simulation-lab/baseline/weekday-mother-template.html
weekday_mother_blob_sha: 3f4e65c1385532b0f0969fdc76caf2883a39e798
fixture: simulation-lab/fixtures/report-data-2026-11-23.json
fixture_blob_sha: d2d6fef0e69cce6991086f84559dd6c0b2b72b33
earnings_consensus_projection: simulation-lab/fixtures/earnings-consensus-projection-2026-11-23.json
earnings_consensus_projection_blob_sha: d683465166e02ef3d744fe0304ae95371d6cc292
main_calendar_commit_sha: 0fa194ae20bb97a72420ad7104bdc4c226a8e65e
main_calendar_current_path: data/calendar/weeks/2026-W48.json
main_calendar_current_blob_sha: 9bb842ab475fa38ca6407304990d1cd3fae42c63
main_calendar_previous_path: data/calendar/weeks/2026-W47.json
main_calendar_previous_blob_sha: 727ea2be1c04688d3c4f98d36c452561bbab6821
builder: simulation-lab/runner/build_review_html.py
builder_blob_sha: 2cb0a90e53b10c31aca20503f93a5b324091c0a7
publish_to_main: false
main_delivery: disabled
run_optional_probes: false
stage2_source_pages_fetched_this_run: false
stage2_displayed_values_independently_reconciled_this_run: false
prebuild_stage_2_to_4_receipt_required: true

This is a date-scoped trigger marker only; it contains no market data.
The pinned Fixture and projection were remotely read back before this marker was updated.
The authoritative main W47/W48 calendar JSON files are read-only inputs; no calendar JSON was changed.
A push commit message containing [build-tac-report:2026-11-23] triggers the formal
Simulation Pipeline. The push event can only create the Simulation branch review
artifact and its QA evidence. It cannot write main preview, main index, or deploy
the production homepage. Optional research probes remain disabled.

Fixture correction log (2026-11-23): political_scan.findings[6] and [7] were normalized from the invalid classification `reported_unverified` to the SIM-1.4 fixed enum `unverified`. Original fixture blob SHA: 8f6664356fec46c0ddb8f0a46e12eeb0e45225bc. No source, event text, transmission, scenario, or market data was changed.

Projection provenance correction (2026-11-23): calendar_main_commit_sha rebound from 09e0e5fe64a781373464858fb70c800e4ffbf098 to 0fa194ae20bb97a72420ad7104bdc4c226a8e65e after verifying the W48 calendar blob is identical (9bb842ab475fa38ca6407304990d1cd3fae42c63). No forecast values, source observations, or reporting periods changed. Original projection blob SHA: 256c86a424b76e0b9cb4a85f915ea3ddac62f4b1.

Workflow pin correction log (2026-11-23): aligned the W48 consensus projection to the current immutable main commit and its unchanged W48 calendar blob; created candidate-validation output directories before the isolated W47 overlay. No main files were modified.

Focus-news source correction (2026-11-23): replaced the Reuters item and the non-macro market-selloff item in the five-item focus block with two directly opened Cnyes macro articles (Taiwan FX/central-bank stabilization and weekly global macro outlook). All five focus items now use Cnyes or Investing.com HK, remain inside the sealed Monday news window, and are URL-distinct from the ten hot headlines.
