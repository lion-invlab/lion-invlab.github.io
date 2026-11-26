from pathlib import Path

WORKFLOW = Path(".github/workflows/tac-simulation-lab.yml").read_text(encoding="utf-8")
PAGES = Path(".github/workflows/pages.yml").read_text(encoding="utf-8")


def section_after(text: str, marker: str) -> str:
    start = text.index(marker)
    end = text.find("\n      - name:", start + len(marker))
    return text[start:] if end < 0 else text[start:end]


assert "simulation/tac-process-lab-2026-11-06" in WORKFLOW
assert "Checkout simulation branch only" in WORKFLOW
assert "Verify default-branch workflow mirror matches Simulation workflow" in WORKFLOW
assert "actions: write" in WORKFLOW and "contents: write" in WORKFLOW
assert "qa-only" not in WORKFLOW

# Builder output is an ephemeral staging file and is not committed to the Simulation branch.
assert 'echo "REPORT_OUTPUT=preview/${REPORT_DATE}-simulation.html"' in WORKFLOW
assert 'echo "REPORT_EVIDENCE=preview/${REPORT_DATE}-simulation.qa.json"' in WORKFLOW
persist = section_after(WORKFLOW, "Persist Simulation receipts and Chart 3 evidence only")
assert r'git add -f "${REPORT_OUTPUT}" "${REPORT_EVIDENCE}"' not in persist
assert "prebuild-stage-input-receipt" in persist
assert "market-source-verification-manifest" in persist
assert 'git push origin "HEAD:simulation/tac-process-lab-2026-11-06"' in persist
assert "git push --force" not in persist
assert "REMOTE_HTML_SHA" not in persist and "REMOTE_EVIDENCE_SHA" not in persist

# Only a QA-passed report can be published, and the main write set is exactly three dated preview files.
publish = section_after(WORKFLOW, "Publish REVIEW_READY report to main preview and verify GitHub Pages")
assert "if: success()" in publish
assert "publish_main_preview.py" in publish
assert "git push origin HEAD:refs/heads/main" in publish
assert "git push --force" not in publish
assert "git worktree add --detach" in publish
assert "EXPECTED_PATHS" in publish and "STAGED_PATHS" in publish and "CHANGED_PATHS" in publish
assert "preview/${REPORT_DATE}-review.html" in publish
assert "preview/${REPORT_DATE}-review.qa.json" in publish
assert "preview/${REPORT_DATE}-review.delivery.json" in publish
assert "index.html" not in publish
assert "data/calendar" not in publish
assert "mother-template" not in publish
assert "gh workflow run pages.yml" in publish
assert "curl -fsS" in publish
assert "MAIN_DELIVERY_COMMIT" in publish

# The existing Pages workflow already deploys main/preview; it is explicitly dispatched after GITHUB_TOKEN push.
assert "branches:\n      - main" in PAGES
assert '"preview/**"' in PAGES
assert "actions/deploy-pages@v4" in PAGES

# The input receipt remains Simulation-scoped and must be sealed before Builder execution.
receipt_step = section_after(WORKFLOW, "Seal pre-build Stage 2-4 input receipt")
builder_gate = section_after(WORKFLOW, "Enforce active SIM-1.4 Builder approval before production build")
assert "validate_prebuild_stage_inputs.py" in receipt_step
assert "PREBUILD_RECEIPT_SHA256" in receipt_step
assert "test -s simulation-lab/output/prebuild-stage-input-receipt.json" in builder_gate
assert "ACTUAL_RECEIPT_SHA256" in builder_gate
assert WORKFLOW.index("Seal pre-build Stage 2-4 input receipt") < WORKFLOW.index("Enforce active SIM-1.4 Builder approval before production build") < WORKFLOW.index("Assemble date-driven review")

# Run-scoped Actions artifacts remain available for independent QA, but are not branch previews.
assert "tac-build-evidence-${{ github.run_id }}-${{ github.run_attempt }}" in WORKFLOW
assert "audit_simulation_artifact_bundle.py" in WORKFLOW
assert "test_publish_main_preview.py" in WORKFLOW

print("PASS: Simulation builds remain isolated; canonical REVIEW_READY HTML/QA/receipt publish only to main/preview.")
print("PASS: main/index.html, formal mothers, Manifest and calendar JSON remain outside the publisher whitelist.")
print("PASS: existing GitHub Pages workflow is dispatched and the public preview URL is checked.")
