# TAC HTML Refactor — Migration Log

## 2026-10-24 — Baseline and CSS extraction

- Working branch: `tac-design-system-work-2026-10-24`
- Frozen baseline: `refactor-work/source-baseline-2026-10-26.html`
- Frozen source SHA: `8e905bb16e6ea1575fded3b781b86597241ffd9d`
- Candidate v1: CSS design-system scaffold linked; no component classes migrated.
- Candidate v2: all 95 style elements moved to head in order; static DOM checks passed.
- Candidate v3: all 95 style blocks extracted in original order to `legacy-cascade.css`; HTML contains no inline style tags and references legacy + design-system stylesheets.
- Candidate v4: self-contained HTML with one consolidated style block, all 10 script blocks unchanged, one DOCTYPE, no duplicate IDs, all main-panel IDs retained.
- Design tokens: original nine root variables moved to `design-system.css` with identical values; `legacy-cascade.css` now begins with a migration note instead of the old root declaration.
- Audit: no detected JavaScript references to the original style-node IDs; no stylesheet links existed in source; CSS selectors did not target the style-node IDs.

## Validation status

- Static structure and source-order checks: passed for candidate v4.
- Browser screenshots / computed-style comparison: not yet run in this environment.
- Interactive regression: not yet run.
- Visual quality upgrade: not yet verified; no claim of completion.
- Official homepage / official mother templates: untouched.

## Browser smoke-test harness

- Added `.github/workflows/tac-refactor-browser-test.yml`, restricted to pushes on this isolated refactor branch; it does not schedule or modify any existing daily automation.
- Added `visual-smoke-test.mjs` to check 12 panel IDs, navigation targets, radio tabs, native disclosures, duplicate IDs, browser errors and horizontal overflow at desktop/mobile widths.
- Workflow dispatch has not yet been observed in Actions; browser test results remain pending until a run is visible.

## Next work

1. Add a browser-capable visual regression step before applying broad appearance changes.
2. Migrate shared panel shell and heading styles with a documented selector map.
3. Migrate radio tabs and disclosures separately, preserving their checked-state selectors and mobile behavior.
4. Remove legacy overrides only after each component's visual and interaction regression passes.


## 2026-10-24 — Shared panel and tab migration passed browser smoke tests

- Candidate build used the frozen source, consolidated CSS, design-system tokens, shared panel classes, and 21 shared tab-label classes.
- Successful browser run: [GitHub Actions run 40083543167](https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40083543167), commit `91772056e4ae6acd4939a79e9a4a3cf3de99362d`.
- Viewports tested: desktop 1440×1000, mobile 390×844, narrow mobile 320×800.
- Passed: all 12 panel IDs present; no duplicate IDs; no unmatched in-page navigation links; 10 original script blocks preserved; one consolidated style block; no new browser errors; no horizontal overflow at any tested viewport.
- Passed: seven representative tab interactions across news, regional markets, assets, economic calendar, earnings calendar, Fed/FOMC, and today's focus; selected state consistently burgundy with white text.
- Passed: native previous-week economic-calendar disclosure opens.
- Visual inspection of the candidate screenshots shows more consistent panel shells, heading accents, spacing, and selected-tab states. The market-sentiment dark/glass treatment remains a distinct exception.
- The current visual difference is intentional. Desktop full-page height differs because panel padding and spacing are larger; mobile screenshots show expected styling differences. No screenshot test can alone prove aesthetic superiority, so human visual review remains part of the gate.
- This completes the **first component migration pass** (panel shell, headings, tab navigation), not the full refactor. Inner cards, data rows, disclosure components, and legacy selector cleanup remain.

