# TAC SIM-1.4 Build Trigger

report_date: 2026-11-23
trigger_scope: simulation-only
workflow: .github/workflows/tac-simulation-lab.yml
active_rules_blob_sha: f0beb47e588e3df8e1f41250dc5bfbb286a2601f
qa_contract_version: 1.19
qa_contract_blob_sha: d266e2074134824931561972709fc189869df98e
manifest_blob_sha: c5e3e810442cdae416a1c70039ffead895b13bb4
monday_mother_blob_sha: efcc712c627d6b26205be340102bba33c4a570d8
weekday_mother_blob_sha: 7027fedb4c5843b1a97fb77f7ef19173e1a98564
fixture: simulation-lab/fixtures/report-data-2026-11-23.json
fixture_blob_sha: d6ba74599df22a6d5c47ed02c0a5594f1b9de519
builder: simulation-lab/runner/build_review_html.py
builder_blob_sha: 16254bfa249814ac75e62cf8acbad2828f366fe6
main_delivery: disabled
publish_to_main: false
rebuild_after_evidence_provenance_fix: true
market_manifest_sidecar_binding: enabled

This file is a date-scoped trigger marker only. It contains no market data.
The version pins above are informational evidence for the exact Simulation build
and must match the corresponding repository blobs when this marker is used.
A commit message containing [build-tac-report:2026-11-23] triggers the formal
Simulation Pipeline. The push-triggered workflow may build and QA a Simulation
review artifact, but must never write to main.
