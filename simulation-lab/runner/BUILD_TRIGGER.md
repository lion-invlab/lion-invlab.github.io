# TAC SIM-1.4 Build Trigger

report_date: 2026-11-24
trading_date: 2026-11-23
iso_week: 2026-W48
report_cutoff_taipei: 2026-11-24T05:25:00+08:00
news_window_taipei: 2026-11-23T12:00:00+08:00/2026-11-24T05:25:00+08:00
trigger_scope: simulation-only
workflow: .github/workflows/tac-simulation-lab.yml
workflow_blob_sha: 0f6cd5da0ca819bbc1b75c8c834cee82b35022a4
active_rules_version: SIM-1.4
active_rules_blob_sha: b9562860f84a302888472ce86a8c0e693d13220a
qa_contract_version: 1.27
qa_contract_blob_sha: 5328fd12f919944314494107311736ff9813ad67
manifest_blob_sha: 9560308371dfa43a0d352398e5ef9abcbf8ee229
monday_mother_path: simulation-lab/baseline/monday-mother-template.html
monday_mother_blob_sha: 710c944205ee05a86599ef5cd869f26c4a9ebde1
weekday_mother_path: simulation-lab/baseline/weekday-mother-template.html
weekday_mother_blob_sha: ff051c0cd22cf9267420c41e3952fa3178f0e45d
fixture: simulation-lab/fixtures/report-data-2026-11-24.json
fixture_blob_sha: d626ec856a8bb2cb4e3b6866cc5161cb754a2ee7
main_calendar_commit_sha: 477752fa1198a0f3970671fd6d02bf5fdf50db27
main_calendar_current_path: data/calendar/weeks/2026-W48.json
main_calendar_current_blob_sha: 0db095ad6638d0bf75dc1ae90248571c84169f26
main_calendar_previous_path: data/calendar/weeks/2026-W47.json
main_calendar_previous_blob_sha: 727ea2be1c04688d3c4f98d36c452561bbab6821

market_history_verifier: simulation-lab/runner/browser_verify_market_history.py
market_history_verifier_blob_sha: f1599bc0068c399f5f748cbe5ea12b194668ffde
market_source_manifest_test_blob_sha: c5a8503f654314ae0c36b3c15ec84fa07dfbcbab
builder: simulation-lab/runner/build_review_html.py
builder_blob_sha: 102b3e3e6307fd0864bcde6618c3f089583b90ae
market_history_web_observations: simulation-lab/input/market-history-web-observations-2026-11-24.json
market_history_web_observations_blob_sha: 9d18091e0677acd27f2002f1eb650e034f926b8f
web_observation_validator_blob_sha: 5d5fe13aad1e2fcba9ce3309f34550e1353bf195
market_manifest_builder_blob_sha: e31e2e02aaf53549dab8189b209c41a59a5318ec
prebuild_validator_blob_sha: ab0f121e4b3e393f2120ddd3dde7d70d4d403953
web_observation_test_blob_sha: c484aa416dbe7512f1a3d4176cac79b813f7bed3
mother_dom_validator_blob_sha: f63c157b8cdd4895aa69d79d6245e8bf3ac6bca7

Mother DOM contract correction (2026-11-24): the weekday summary keeps its single mother-owned paragraph container while allowing the approved dynamic editorial line breaks to vary; this permits the four-paragraph weekday summary without treating text-flow breaks as a mother DOM redesign. All other wrapper attributes and stable selectors remain enforced.
prebuild_test_blob_sha: 4c40eeaa3f6232cd0be18c5cf4b7b856b2fe861a
publish_to_main: false
main_delivery: disabled
run_optional_probes: false
stage2_source_pages_fetched_this_run: true
stage2_displayed_values_independently_reconciled_this_run: false
prebuild_stage_2_to_4_receipt_required: true

This is a date-scoped trigger marker only; it contains no market data.

2026-11-24 Stage 2 recapture: 44 source pages reopened at 16:08:10 Asia/Taipei; 43 numeric observations verified and Nikkei 225 marked CLOSED using Japan Cabinet Office holiday evidence. This was a late QA recapture after the 05:25 report cutoff; it does not prove the 05:25 schedule ran successfully. Non-market fixture content remains carried forward, so this is not a full blank-input Stage 1 rebuild.
The fixture is a 2026-11-24 report for the 2026-11-23 market session. All 44 fixed market rows were reopened from current source pages; 43 numeric observations verified and one market closure recorded. The 11 sector ETF rows use 2026-11-23 historical data; XLRE uses the Investing.com Global backup page because the HK page was inaccessible. This recapture is after the 05:25 cutoff and is only a Stage 2 QA re-read, not a proof of the scheduled production run.
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

Builder approval update (2026-11-24): the user accepted the exact Builder blob SHA 102b3e3e6307fd0864bcde6618c3f089583b90ae. Active SIM-1.4 and this trigger now pin that exact version. The Workflow Builder approval step is fail-closed; this update does not run a build or authorize main delivery.

Trigger pin synchronization (2026-11-24): aligned the date-scoped trigger with the current SIM-1.4 QA Contract v1.26, simulation mother-template Manifest, and the exact Monday/weekday simulation baseline blob SHAs. This synchronizes references only; it does not approve or execute a full build, change main, or authorize homepage delivery.

Responsive earnings grid spacing correction (2026-11-24): both Simulation mothers now explicitly retain the approved <=1200px #earnings row-gap 16px / column-gap 14px; this resolves the visual regression mismatch without redesigning the section. The report's market-risk paragraph and warning note were also aligned to the freshly read MOVE 100.91 (-5.08%) and the 43-verified/1-closed observation result. Main remains untouched.

Fear & Greed raw-value mapping correction (2026-11-24): CNN official previous_close raw value 16.9658627087199 is rounded to display 17; FGScore historical-page fallback score 17 is separately pinned as backup_source_score_value. The validator distinguishes the two raw-value mappings so either source can verify without false pending status. CNN API response SHA-256 and endpoint are recorded as the primary cross-check; source URL remains the FGScore fallback page. Main unchanged.

2026-11-24 Stage 2 direct recapture (16:26 Asia/Taipei): reopened all 44 fixed source pages in the current ChatGPT web session; 43 numeric observations independently matched the fixture, and Nikkei 225 was retained as MARKET_CLOSED based on the official Cabinet Office holiday table (the Investing.com row was a CFD, not the cash index). New capture session: TAC-SIM14-RECAPTURE-20261124-1625-TW. Fixture SHA: 9e3acf4288227f8d449e84f62c0d6849c9b618ca; observation bundle SHA: 9d18091e0677acd27f2002f1eb650e034f926b8f. No prior observation records reused. This is a same-day Stage 2 recapture, not a blank-input Stage 1 rebuild or proof of the 05:25 schedule.

QA Contract v1.27 correction (2026-11-24): fixed the precise prior QA failure by syncing A2.1 simulation mother SHA bindings to the current Manifest (Monday 710c944205ee05a86599ef5cd869f26c4a9ebde1; Weekday ff051c0cd22cf9267420c41e3952fa3178f0e45d). QA Contract SHA: 5328fd12f919944314494107311736ff9813ad67; active SIM-1.4 rules SHA: b9562860f84a302888472ce86a8c0e693d13220a. This is a contract-to-mother provenance sync only; no mother DOM/CSS, main files or homepage changed.

Chart 3 handoff reliability correction (2026-11-24): S&P 500 read_method remains CHATGPT_WEB_OPEN_HISTORICAL_PAGE, while evidence_method is now the required INVESTING_COM_HISTORICAL_TABLE. Removed continue-on-error from deterministic self-tests and verified S&P 500 handoff: an unverified S&P 500 still skips cleanly, but a verified handoff or core-test failure now fails the workflow instead of being reported green. Main unchanged.

Summary slot correction (2026-11-24): consolidated the four draft summary points into the three approved SIM-1.4 summary slots. The market-catalyst explanation remains explicit; bond, FX and commodity divergences are combined in the second point; the final point retains conditional risk exposure guidance. Fixture SHA: e892d4b0a402f63e486338b7d2c1886e372e086c. No mother or main files changed.

Manifest integration correction (2026-11-24): the manifest builder now distinguishes CNN_OFFICIAL_PREVIOUS_CLOSE from the FGScore backup page even when the fixture URL is a backup URL. CNN raw previous_close compares to source_score_value; FGScore integer score compares to backup_source_score_value. The nested cross_check object carries the CNN API as PRIMARY cross-check. Added regression tests for both paths. Main unchanged.
