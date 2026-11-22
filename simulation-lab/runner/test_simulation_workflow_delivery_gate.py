from pathlib import Path

WORKFLOW = Path(".github/workflows/tac-simulation-lab.yml").read_text(encoding="utf-8")

def section_after(text: str, marker: str) -> str:
    start = text.index(marker)
    end = text.find("\n      - name:", start + len(marker))
    return text[start:] if end < 0 else text[start:end]

inputs = section_after(WORKFLOW, "workflow_dispatch:")
assert "publish_to_main:" in inputs
publish_input = inputs.split("publish_to_main:", 1)[1].split("approved_html_sha:", 1)[0]
assert "default: false" in publish_input
assert "approved_html_sha:" in inputs

persist = section_after(WORKFLOW, "Persist QA-passed source review HTML and QA sidecar on simulation branch")
assert "github.event_name == 'push'" in persist
assert "build-tac-report" in persist

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

print("PASS: Simulation preview can be built without publishing; main delivery requires explicit publish_to_main=true and exact approved HTML SHA-256.")

# The approval token is never interpolated into shell source; it is read from an environment variable.
