# TAC SIM-1.4 Build Trigger

report_date: 2026-11-24
trading_date: 2026-11-23
iso_week: 2026-W48
report_cutoff_taipei: 2026-11-24T05:25:00+08:00
news_window_taipei: 2026-11-23T12:00:00+08:00/2026-11-24T05:25:00+08:00
trigger_scope: simulation-only
workflow: .github/workflows/tac-simulation-lab.yml
workflow_blob_sha: c63c00b09baf5193d7ea524669632b73bb1af546
active_rules_version: SIM-1.4
active_rules_blob_sha: 7a4dc383ccf86a7c7a89b60cafc3b91f5fdb5c3b
qa_contract_version: 1.21
qa_contract_blob_sha: e4a11261fba37fbd9deee7c6b61c9dc29a1966d6
manifest_blob_sha: d47d8abece4137884bda76d6a505ba4112904e0d
monday_mother_path: simulation-lab/baseline/monday-mother-template.html
monday_mother_blob_sha: 0a7d5095aaa99c470e00e67f33567ff9f359d6ae
weekday_mother_path: simulation-lab/baseline/weekday-mother-template.html
weekday_mother_blob_sha: 3f4e65c1385532b0f0969fdc76caf2883a39e798
fixture: simulation-lab/fixtures/report-data-2026-11-24.json
fixture_blob_sha: 50c584a3a491efa6742fa37a5ba42009b78c7253
main_calendar_commit_sha: 77ab012bb027591631c704d976468cf4ea2e2046
main_calendar_current_path: data/calendar/weeks/2026-W48.json
main_calendar_current_blob_sha: 0db095ad6638d0bf75dc1ae90248571c84169f26
main_calendar_previous_path: data/calendar/weeks/2026-W47.json
main_calendar_previous_blob_sha: 727ea2be1c04688d3c4f98d36c452561bbab6821

market_history_verifier: simulation-lab/runner/browser_verify_market_history.py
market_history_verifier_blob_sha: f1599bc0068c399f5f748cbe5ea12b194668ffde
builder: simulation-lab/runner/build_review_html.py
builder_blob_sha: 2cb0a90e53b10c31aca20503f93a5b324091c0a7
market_history_web_observations: simulation-lab/input/market-history-web-observations-2026-11-24.json
market_history_web_observations_blob_sha: 5d21b9ae8682fb429ec2e339eb188cf9fd6fc977
web_observation_validator_blob_sha: 10d44f701e1bf401778081f59831e14945983e7b
market_manifest_builder_blob_sha: a9c730d0535b9f02a0b20dfe97e15e0acf1577cd
prebuild_validator_blob_sha: 30114f3967731d400d4e7dc581e94eccd8731f00
web_observation_test_blob_sha: 50faa6b9ac23612e163e8ec7049f991e27850e8e
prebuild_test_blob_sha: 6395a1cba81046385c56c2615165a8f80521b3c8
publish_to_main: false
main_delivery: disabled
run_optional_probes: false
stage2_source_pages_fetched_this_run: false
stage2_displayed_values_independently_reconciled_this_run: false
prebuild_stage_2_to_4_receipt_required: true

This is a date-scoped trigger marker only; it contains no market data.
The fixture is a 2026-11-24 report for the 2026-11-23 market session. All 44 fixed market rows are present; the 11 sector ETF closes and daily changes are pinned to 2026-11-23 Investing.com historical rows; the workflow must rebuild current-session browser observations and preserve any unresolved rows as explicitly pending.
The authoritative main W48/W47 calendar JSON files are read-only inputs. The run can only create a Simulation review artifact and QA evidence; it cannot write main preview, main index, or deploy the production homepage.
A push commit message containing [build-tac-report:2026-11-24] triggers the full report build and required artifact QA.
Fixture correction log (2026-11-23): political_scan.findings[6] and [7] were normalized from the invalid classification `reported_unverified` to the SIM-1.4 fixed enum `unverified`. Original fixture blob SHA: 8f6664356fec46c0ddb8f0a46e12eeb0e45225bc. No source, event text, transmission, scenario, or market data was changed.

Projection provenance correction (2026-11-23): calendar_main_commit_sha rebound from 09e0e5fe64a781373464858fb70c800e4ffbf098 to 0fa194ae20bb97a72420ad7104bdc4c226a8e65e after verifying the W48 calendar blob is identical (9bb842ab475fa38ca6407304990d1cd3fae42c63). No forecast values, source observations, or reporting periods changed. Original projection blob SHA: 256c86a424b76e0b9cb4a85f915ea3ddac62f4b1.

Workflow pin correction log (2026-11-23): aligned the W48 consensus projection to the current immutable main commit and its unchanged W48 calendar blob; created candidate-validation output directories before the isolated W47 overlay. No main files were modified.

Focus-news source correction (2026-11-23): replaced the Reuters item and the non-macro market-selloff item in the five-item focus block with two directly opened Cnyes macro articles (Taiwan FX/central-bank stabilization and weekly global macro outlook). All five focus items now use Cnyes or Investing.com HK, remain inside the sealed Monday news window, and are URL-distinct from the ten hot headlines.

Visual QA contract correction (2026-11-23): the published-earnings regression reads the Builder's canonical data-comparison-status attribute and checks it against the visible badge class. It no longer incorrectly requires the state to be duplicated on the outer card wrapper.

Builder approval integrity correction (2026-11-23): restored the exact SIM-1.4 §8.1 approved Builder SHA 2cb0a90e53b10c31aca20503f93a5b324091c0a7. Unapproved candidate Builder changes are not used.
Content QA scope correction (2026-11-23): non-actionable conclusion wording is checked in summary, five-layer analysis, market comments, market observation and sentiment; event-calendar impact descriptions are not treated as investment conclusions.

Report-layer overlay correction (2026-11-23): retain the exact approved Builder SHA 2cb0a90e53b10c31aca20503f93a5b324091c0a7. The approved local patcher now applies the W47 NVDA consensus and the exact-source-guarded Kevin Warsh impact wording together, with a single final HTML/receipt SHA. No main files are modified.

QA seal correction (2026-11-23): the evidence sealer now validates both nested W47 NVDA consensus and Warsh calendar-impact receipts, and binds the combined receipt to the exact final review HTML SHA. The exact approved Builder SHA remains unchanged.

Monday content Gate correction (2026-11-23): the risk observation now names the next verified catalyst, US November Flash PMI at 11/23 22:45 Taipei time with the fixture's consensus values; the operation plan states a neutral-defensive stance and explicit conditional exposure actions.
