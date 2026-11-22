# TAC SIM-1.4 Build Trigger

report_date: 2026-11-23
trigger_scope: simulation-only
workflow: .github/workflows/tac-simulation-lab.yml
active_rules_blob_sha: 9493e85b424eb1b48d4df8c328d5850d6fcef0c8
fixture: simulation-lab/fixtures/report-data-2026-11-23.json
builder: simulation-lab/runner/build_review_html.py
main_delivery: disabled
publish_to_main: false
rebuild_after_evidence_provenance_fix: true
market_manifest_sidecar_binding: enabled

This file is a date-scoped trigger marker only. It contains no market data.
A commit message containing [build-tac-report:2026-11-23] triggers the formal
Simulation Pipeline. The push-triggered workflow may build and QA a Simulation
review artifact, but must never write to main.
