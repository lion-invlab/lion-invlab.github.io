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
- Browser screenshots / computed-style comparison: run in GitHub Actions at desktop 1440px, mobile 390px, narrow mobile 320px.
- Interactive regression: passed for seven representative tab controls and native weekly-calendar disclosure; no new browser errors or horizontal overflow.
- Shared panel shell and selected-tab state: pilot passed; full visual upgrade and inner content-component migration remain in progress.
- Official homepage / official mother templates: untouched.

## Browser smoke-test harness

- Added `.github/workflows/tac-refactor-browser-test.yml`, restricted to pushes on this isolated refactor branch; it does not schedule or modify any existing daily automation.
- Added `visual-smoke-test.mjs` to check 12 panel IDs, navigation targets, radio tabs, native disclosures, duplicate IDs, browser errors and horizontal overflow at desktop/mobile widths.
- Browser workflow has completed successfully: run `40083543167`, commit `91772056e4ae6acd4939a79e9a4a3cf3de99362d`.
- The test confirms 12 panel IDs, no duplicate IDs, no unmatched nav targets, no added horizontal overflow, no new browser errors, working disclosure, and seven tab switches with consistent burgundy/white selected state.

## Next work

1. Freeze the fixed/dynamic/conditional content contract for all 12 panels and their tabs.
2. Migrate inner data cards, source disclosures, empty/loading states and tables using the same design tokens.
3. Add the remaining interaction tests and compare full-page screenshots at desktop and mobile widths.
4. Audit JavaScript dependencies and remove legacy overrides only after each component's visual and interaction regression passes.


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



## 2026-10-24 — First panel/tab pilot passed

- Run: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40083543167 — overall conclusion `success`.
- All 12 main panel IDs remain present; no duplicate IDs, unmatched nav links, added horizontal overflow or new browser errors at 1440px, 390px and 320px widths.
- Seven representative tabs across all five tab families switch correctly and report a consistent selected style (burgundy background, white text); weekly calendar disclosure opens correctly.
- Candidate: self-contained HTML generated by `build-candidate.py`, all original 10 script blocks retained.
- Visual shell and tabs are now standardized as the first pilot. This is **not** the final master; fixed/dynamic/conditional content contract and inner components remain the next gate.
- Artifacts (screenshots, pixel diffs, test results and generated candidate): https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40083543167/artifacts/12555834260


## 2026-10-24 — Contract and dependency audit

- Created `refactor-work/DATA-CONTRACT.md`: classifies fixed, dynamic and conditional content for all 12 panels; records market-closed, not-yet-published, no-event, needs-verification, source-unavailable and stale-snapshot as distinct states.
- Created `refactor-work/CSS-JS-AUDIT.md`: static inventory of 95 extracted style blocks, approximate selector counts, repeated selector strings, `!important` use, responsive rules, script blocks, functions, event listeners and DOM selector calls.
- Current CSS audit finds approximately 1,783 selector entries, 365 repeated selector strings and 2,000 `!important` declarations; these are risk indicators, not a deletion list.
- Next gate: reconcile the draft contract with the latest project rules, then migrate inner data cards and disclosures without altering source logic, data values, JSON or schedules.


## 2026-10-24 — Prior-week disclosure component migrated and verified

- Both `last-week-calendar-collapse` and `last-week-earnings-collapse` now opt into the shared `tac-ds-disclosure` component during candidate build.
- Removed duplicated legacy appearance declarations for the two outer disclosure shells; retained the Safari visibility/clickability safeguards and content spacing.
- Shared disclosure appearance now defines shell border, radius, shadow, summary spacing, chevron state, and expanded-state divider.
- Successful browser run: [GitHub Actions run 40083854261](https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40083854261), commit `ae7dc487ef887ae80f274916c63f92e3dc5f2c1f`.
- Passed at desktop 1440×1000, mobile 390×844 and narrow mobile 320×800: both prior-week disclosures open; all seven tab checks pass; 12 panel IDs, navigation targets, script count, no duplicate IDs, no new browser errors, no horizontal overflow.
- Candidate and baseline screenshots plus the self-contained candidate HTML were uploaded as the run artifact. Artifact expires after seven days.
- Scope remains limited to the two outer prior-week disclosure components. Event-level economic/earnings accordions and other source/method disclosures remain for a later migration pass.


## 2026-10-24 — Disclosure and empty-state pilot passed

- SHA-pinned GitHub Actions run: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40084521133 — `success`.
- Verified on 1440×1000, 390×844 and 320×800: all 12 panel IDs, no duplicate IDs, no unmatched navigation, no added horizontal overflow, no new browser errors.
- Shared components present: 21 tab labels, 15 source/method disclosures (including 3 dark sentiment variants), and 4 calendar empty states.
- Source disclosure open/close works and the triangle marker is present; both prior-week calendar disclosures still open. Seven tab families keep the consistent burgundy active state with white text.
- Latest self-contained candidate generated from the reproducible builder and extracted to `/mnt/data/TAC_投資早報_設計系統_試點版.html`. It has one consolidated style block, 10 preserved script blocks and one DOCTYPE.
- This remains an isolated pilot, not the official mother template. The next stage migrates inner news/event/earnings/sector components and only then removes verified-unused legacy rules.
