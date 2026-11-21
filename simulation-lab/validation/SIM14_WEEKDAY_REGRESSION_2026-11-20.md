# SIM-1.4 Weekday Mother Regression｜2026-11-20

- Purpose: complete the second half of SIM-1.4 §8.1 candidate Builder validation after the 2026-11-23 Monday run passed.
- Report date: 2026-11-20 (Friday; Weekday mother).
- Fixture: `simulation-lab/fixtures/report-data-2026-11-20.json`.
- Expected fixture blob SHA at trigger: `7b2858217a0492dd84e24e56d3b93897380007e8`.
- Required locked assets: active SIM-1.4, current Manifest, QA Contract v1.16, Weekday mother, candidate Builder `simulation-lab/runner/build_review_html.py`, and independent review validator.
- Required checks: deterministic self-tests; fixture/date resolution; weekday mother SHA; browser navigation and accordions; six viewport visual regression (320/360/390/412/768/1440); mother DOM preservation; independent provenance; authoritative calendar counts; 44-indicator shape; news shape; exact HTML/QA sidecar sealing; simulation-only persistence.
- No production scope: do not modify main, formal homepage, formal mothers, formal Manifest, or authoritative calendar JSON. No Pages deployment.
- Acceptance rule: this run plus the already-passed 2026-11-23 Monday run must use identical Builder, Manifest, QA Contract, and active SIM-1.4 SHAs. Any failure blocks dual-mother candidate validation.
- Triggered by commit message marker `[build-tac-report:2026-11-20]`.
