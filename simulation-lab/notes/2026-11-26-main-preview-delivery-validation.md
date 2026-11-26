# 2026-11-26 main/preview delivery architecture validation

This note exists to trigger the non-production [full-regression] workflow checks after the SIM-1.4 main-preview delivery amendment.

Expected checks:
- Main/default and Simulation copies of tac-simulation-lab.yml have identical blob SHA.
- The default branch contains both tac-simulation-lab.yml and simulation-workflow-lint.yml so GitHub can load the push-triggered workflow definitions.
- The Builder continues to produce an ephemeral Simulation-runner staging artifact; daily review HTML and QA are not committed to the Simulation branch.
- The publisher writes only the dated HTML, QA sidecar and delivery receipt under main/preview.
- main/index.html, formal mothers, Manifest, calendar JSON and history remain untouched.
- Existing Pages workflow is explicitly dispatched after the GITHUB_TOKEN push and the public review URL is checked.

This full-regression run must not trigger a real report build or publish a report.
