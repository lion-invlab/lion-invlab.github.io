# TAC SIM-1.4 Build Trigger

report_date: 2026-11-23
trading_date: 2026-11-20
iso_week: 2026-W48
report_cutoff_taipei: 2026-11-23T05:25:00+08:00
news_window_taipei: 2026-11-20T12:00:00+08:00/2026-11-23T05:25:00+08:00
trigger_scope: simulation-only
workflow: .github/workflows/tac-simulation-lab.yml
workflow_blob_sha: dd03a0abb3c5a8b280191ade3b80802987c46a48
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
fixture_blob_sha: 8f6664356fec46c0ddb8f0a46e12eeb0e45225bc
earnings_consensus_projection: simulation-lab/fixtures/earnings-consensus-projection-2026-11-23.json
earnings_consensus_projection_blob_sha: 256c86a424b76e0b9cb4a85f915ea3ddac62f4b1
main_calendar_commit_sha: 09e0e5fe64a781373464858fb70c800e4ffbf098
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
