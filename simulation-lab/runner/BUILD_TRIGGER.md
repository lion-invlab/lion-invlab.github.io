# TAC SIM-1.4 Build Trigger

report_date: 2026-11-24
trading_date: 2026-11-23
iso_week: 2026-W48
report_cutoff_taipei: 2026-11-24T05:25:00+08:00
news_window_taipei: 2026-11-23T12:00:00+08:00/2026-11-24T05:25:00+08:00
trigger_scope: simulation-only
workflow: .github/workflows/tac-simulation-lab.yml
workflow_blob_sha: 12d72b4162d8f8f2c80d174d55a1dc2bd74766eb
active_rules_version: SIM-1.4
active_rules_blob_sha: 91083f5d18e960fa9e1e9dbb5bedca1029232d81
qa_contract_version: 1.21
qa_contract_blob_sha: 1bf22ea17356eaf4cdfba2c1ecc17ca402302578
manifest_blob_sha: 81e01655fd8a2dfeaa72b5c63d1695db13370562
monday_mother_path: simulation-lab/baseline/monday-mother-template.html
monday_mother_blob_sha: 0a7d5095aaa99c470e00e67f33567ff9f359d6ae
weekday_mother_path: simulation-lab/baseline/weekday-mother-template.html
weekday_mother_blob_sha: 33a5790c8132c1e24cebb5e30059f2b3348aca5c
fixture: simulation-lab/fixtures/report-data-2026-11-24.json
fixture_blob_sha: 6eafa708f8da49c9b0bf8240f8b00f8ff555b960
main_calendar_commit_sha: 477752fa1198a0f3970671fd6d02bf5fdf50db27
main_calendar_current_path: data/calendar/weeks/2026-W48.json
main_calendar_current_blob_sha: 0db095ad6638d0bf75dc1ae90248571c84169f26
main_calendar_previous_path: data/calendar/weeks/2026-W47.json
main_calendar_previous_blob_sha: 727ea2be1c04688d3c4f98d36c452561bbab6821

market_history_verifier: simulation-lab/runner/browser_verify_market_history.py
market_history_verifier_blob_sha: f1599bc0068c399f5f748cbe5ea12b194668ffde
market_source_manifest_test_blob_sha: 2e90721eb30faea80ec282d4aea695efc24d9421
builder: simulation-lab/runner/build_review_html.py
builder_blob_sha: 92605353973bb2c8200c5785917a95060681790a
market_history_web_observations: simulation-lab/input/market-history-web-observations-2026-11-24.json
market_history_web_observations_blob_sha: 17b21de7e406a67fc09490fc3cf347cf8521e5cc
web_observation_validator_blob_sha: 8264ad968f5f5c7ec3527345db6d1ec5167076f9
market_manifest_builder_blob_sha: f127126d6a932069d3e8f5f9c52a11bbcd5f6ed2
prebuild_validator_blob_sha: ab0f121e4b3e393f2120ddd3dde7d70d4d403953
web_observation_test_blob_sha: f46339e631898f1bd7e1080649ebf9ba3ae20903
mother_dom_validator_blob_sha: f63c157b8cdd4895aa69d79d6245e8bf3ac6bca7

Mother DOM contract correction (2026-11-24): the weekday summary keeps its single mother-owned paragraph container while allowing the approved dynamic editorial line breaks to vary; this permits the four-paragraph weekday summary without treating text-flow breaks as a mother DOM redesign. All other wrapper attributes and stable selectors remain enforced.
prebuild_test_blob_sha: 4c40eeaa3f6232cd0be18c5cf4b7b856b2fe861a
publish_to_main: false
main_delivery: disabled
run_optional_probes: false
stage2_source_pages_fetched_this_run: false
stage2_displayed_values_independently_reconciled_this_run: false
prebuild_stage_2_to_4_receipt_required: true

This is a date-scoped trigger marker only; it contains no market data.
The fixture is a 2026-11-24 report for the 2026-11-23 market session. All 44 fixed market rows are present; the 11 sector ETF closes and daily changes are pinned to 2026-11-23 Investing.com historical rows; the workflow must rebuild current-session browser observations and preserve any unresolved rows as explicitly pending.
The authoritative main W48/W47 calendar JSON files are read-only inputs. The build workflow creates the Simulation artifact and QA evidence. Once Stage 5 is REVIEW_READY, Stage 6 must immediately copy the exact artifact and QA sidecar to main/preview with a delivery receipt using a main-capable GitHub file update action; this is a review-only delivery and must never modify main/index.html or deploy the production homepage. User review corrections are made directly to that same main/preview HTML without rerunning QA.
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
