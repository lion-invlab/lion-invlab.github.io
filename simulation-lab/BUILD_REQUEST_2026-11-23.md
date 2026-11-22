# SIM-1.4 Build Request｜2026-11-23

- Target report: `2026-11-23` (Monday template)
- Scope: simulation branch only
- Approved Builder: `simulation-lab/runner/build_review_html.py`
- Approved Builder blob SHA: `16254bfa249814ac75e62cf8acbad2828f366fe6`
- Active SIM-1.4 rules blob SHA: `28b9d1febc106012650fe0c6085d5405742eeea6`
- Fixture blob SHA at request time: `b1db8b43e7433429a55884330a56a9743684b987`
- Expected state: 3 disclosed blockers remain; output must stay `PARTIAL`, never `REVIEW_READY`.
- Main handoff: NOT AUTHORIZED. The QA handoff gate must stop before any main fetch/write step when `sim14_blockers` is non-empty.
- Allowed output: simulation-branch preview and QA sidecar only. No main/index, mother template, Manifest, calendar JSON, historical report, or Pages deployment changes.

