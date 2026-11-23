from pathlib import Path

WORKFLOW = Path(".github/workflows/tac-simulation-lab.yml").read_text(encoding="utf-8")

def section_after(text: str, marker: str) -> str:
    start = text.index(marker)
    end = text.find("\n      - name:", start + len(marker))
    return text[start:] if end < 0 else text[start:end]

transfer_evidence_step = section_after(WORKFLOW, "Materialize SHA-locked simulation Monday and weekday mothers")
assert "indent=2)+'\\\\n'" not in transfer_evidence_step
assert "indent=2)+'\\n'" in transfer_evidence_step
assert "json.loads" in transfer_evidence_step

inputs = section_after(WORKFLOW, "workflow_dispatch:")
assert "publish_to_main:" in inputs
publish_input = inputs.split("publish_to_main:", 1)[1].split("approved_html_sha:", 1)[0]
assert "default: false" in publish_input
assert "approved_html_sha:" in inputs

persist = section_after(WORKFLOW, "Persist QA-passed source review HTML and QA sidecar on simulation branch")
assert "github.event_name == 'push'" in persist
assert "build-tac-report" in persist
assert "PUSHED=false" in persist and "PUSHED=true" in persist
assert "for attempt in 1 2 3" in persist
assert "git -c rebase.autoStash=true rebase origin/simulation/tac-process-lab-2026-11-06" in persist
assert persist.index("git fetch origin simulation/tac-process-lab-2026-11-06") < persist.index("git -c rebase.autoStash=true rebase") < persist.index('if git push origin "HEAD:simulation/tac-process-lab-2026-11-06"')
assert "git push --force" not in persist
assert "\\n          git -c rebase.autoStash=true rebase" not in persist
assert "Simulation branch push failed after 3 safe attempts" in persist

delivery = section_after(WORKFLOW, "Deliver the exact QA-passed artifact to main preview only after explicit user approval")
condition = delivery.split("shell:", 1)[0]
assert "github.event_name == 'workflow_dispatch'" in condition
assert "inputs.mode == 'build'" in condition
assert "inputs.publish_to_main == true" in condition
assert "github.event_name == 'push'" not in condition

assert "approved_html_sha" in delivery
assert "APPROVED_HTML_SHA: ${{ inputs.approved_html_sha }}" in delivery
assert 'os.environ.get("APPROVED_HTML_SHA", "")' in delivery
assert 're.fullmatch(r"[0-9a-f]{64}", approved_html_sha)' in delivery
assert "approved_html_sha != actual_html_sha256" in delivery
assert delivery.index("approved_html_sha != actual_html_sha256") < delivery.index("git fetch origin main")

# Stage 2-4 input receipt is mandatory before Builder execution and remains bound through QA and handoff.
receipt_step = section_after(WORKFLOW, "Seal pre-build Stage 2-4 input receipt")
market_step = section_after(WORKFLOW, "Validate 44 market-row metadata/date/identity only")
capture_step = section_after(WORKFLOW, "Capture 44 raw market source pages")
builder_gate = section_after(WORKFLOW, "Enforce active SIM-1.4 Builder approval before production build")
overlay_step = section_after(WORKFLOW, "Apply local W47 NVDA consensus overlay")
assert 'mkdir -p "$(dirname "${BUILDER_OUTPUT}")"' in overlay_step
assert overlay_step.index("mkdir -p") < overlay_step.index('cp "${REPORT_OUTPUT}"')
seal_step = section_after(WORKFLOW, "Seal QA evidence to the exact review HTML blob")
seal = Path("simulation-lab/runner/seal_qa_evidence.py").read_text(encoding="utf-8")
assert "seal_qa_evidence.py" in seal_step
assert "GITHUB_RUN_ID" in seal and "GITHUB_RUN_ATTEMPT" in seal and "${{" not in seal
assert "analysis_text_parts" in seal and "visible_report_text" not in seal
assert "market_analysis" in seal and "market_comments" in seal
persist = section_after(WORKFLOW, "Persist QA-passed source review HTML and QA sidecar on simulation branch")
assert WORKFLOW.index("Validate 44 market-row metadata/date/identity only") < WORKFLOW.index("Seal pre-build Stage 2-4 input receipt") < WORKFLOW.index("Capture 44 raw market source pages") < WORKFLOW.index("Enforce active SIM-1.4 Builder approval before production build") < WORKFLOW.index("Assemble date-driven review")
assert "validate_prebuild_stage_inputs.py" in receipt_step
assert "market-snapshot-audit.json" in receipt_step and "market-source-verification-manifest.json" in receipt_step
assert "PREBUILD_RECEIPT_SHA256" in receipt_step
assert "test -s simulation-lab/output/prebuild-stage-input-receipt.json" in builder_gate
assert "ACTUAL_RECEIPT_SHA256" in builder_gate
assert "prebuild_input_receipt_sha256" in seal and "calendar_main_commit_sha" in seal
receipt_recheck = section_after(WORKFLOW, "Recheck pre-build receipt SHA after Builder")
assert WORKFLOW.index("Recheck pre-build receipt SHA after Builder") < WORKFLOW.index("Seal QA evidence to the exact review HTML blob")
assert "ACTUAL_PREBUILD_RECEIPT_SHA256" in receipt_recheck
assert 'if [[ "${ACTUAL_PREBUILD_RECEIPT_SHA256}" != "${PREBUILD_RECEIPT_SHA256}" ]]; then' in receipt_recheck
assert 'if [[ ! -s simulation-lab/output/prebuild-stage-input-receipt.json ]]; then' in receipt_recheck
assert "Pre-build receipt SHA changed after Builder execution" in receipt_recheck
assert all(module in seal for module in ("hashlib", "json", "os", "re", "subprocess", "sys"))
assert "PREBUILD_RECEIPT_ARCHIVE" in persist and "REMOTE_PREBUILD_SHA" in persist
assert "prebuild_receipt.get(\"status\") != \"PASS\"" in delivery
assert "prebuild_input_receipt_sha256" in delivery
assert "PRE_BUILD_STAGE_2_TO_4_INPUT_RECEIPT" in Path("simulation-lab/runner/validate_prebuild_stage_inputs.py").read_text(encoding="utf-8")

capture = section_after(WORKFLOW, "Capture simulation checkout provenance")
metadata = section_after(WORKFLOW, "Record isolated run metadata")
artifact_audit = section_after(WORKFLOW, "Verify downloaded simulation evidence bundle")
assert "SIM_CHECKOUT_COMMIT=$(git rev-parse HEAD)" in capture
assert 'echo "SIM_TRIGGER_COMMIT=$GITHUB_SHA"' in capture
assert 'echo "commit=$(git rev-parse HEAD)"' in metadata
assert 'echo "build_commit=${SIM_CHECKOUT_COMMIT:-unavailable}"' in metadata
assert 'echo "checkout_commit=${SIM_CHECKOUT_COMMIT:-unavailable}"' in metadata
assert 'echo "trigger_commit=$GITHUB_SHA"' in metadata
assert 'echo "commit=$GITHUB_SHA"' not in metadata
assert '--expected-trigger-commit "${GITHUB_SHA}"' in artifact_audit
assert "expected_trigger_commit" in Path("simulation-lab/runner/audit_simulation_artifact_bundle.py").read_text(encoding="utf-8")

print("PASS: Simulation preview requires a sealed Stage 2-4 receipt before Builder; receipt is SHA-bound to QA, archived, read back, and required for explicit main handoff.")
print("PASS: main delivery requires explicit publish_to_main=true and exact approved HTML SHA-256.")

# The approval token is never interpolated into shell source; it is read from an environment variable.

# Trigger the 2026-11-23 simulation-only Builder and QA run; main publication remains disabled on push.
