Run browser regression for sector ETF row migration
Date: 2026-10-24
Scope: verify 11 sector rows use the unified grid/card style and responsive radii; preserve rank, Chinese sector name, ETF code and percentage-only values; check all prior panel, tab, disclosure, news, event and earnings interactions.

Retry sector row radius assertion after correcting expected desktop/mobile values.

Rerun sector disclosure toggle test with state-independent assertion.
rerun-sector-disclosure-after-scroll-stabilization-2026-10-25T0017+0800
rerun-sector-disclosure-close-state-2026-10-25
actual-earnings-card-pilot-2026-10-25
regex-guard-fix-rerun-2026-10-25
special-background-isolation-regression-2026-10-25
nav-anchor-hand-indicator-regression-2026-10-25
fix-hand-color-contract-regression-2026-10-25

nav-anchor-real-click-geometry-regression-2026-10-25

nav-anchor-geometry-debug-2026-10-25
anchor-root-scroll-padding-112px-rerun-2026-10-25
anchor-cascade-override-removed-rerun-2026-10-25

anchor-scroll-padding-in-design-system-rerun-2026-10-25
measure-panel-geometry-height-regression-2026-10-25
inspect-expanded-section-card-geometry-2026-10-25
compare-legacy-and-shared-card-geometry-2026-10-25

compact-tabbed-panel-and-news-card-geometry-trial-2026-10-25

restore-news-text-rhythm-and-panel-geometry-2026-10-25

reduce-tab-navigation-vertical-footprint-2026-10-25

restore-prior-week-disclosure-geometry-2026-10-25

restore-prior-week-event-stack-rhythm-2026-10-25

fix-prior-week-summary-selector-scope-2026-10-25

remove-doubled-prior-week-disclosure-padding-2026-10-25

preserve-prior-week-wrapper-and-disclosure-legacy-geometry-2026-10-25

compact-tabs-and-source-summary-geometry-parity-2026-10-25

final-news-scan-spacing-pass-2026-10-25

mobile-toolbar-comic-bubble-v1-2026-10-25

retry-coach-test-syntax-fix-2026-10-25

coach-inline-style-and-legacy-hand-cleanup-rerun-2026-10-25

fix-coach-bubble-width-and-wrap-2026-10-25
fix-coach-bubble-wrap-geometry-2026-10-25
remove-legacy-toolbar-hint-2026-10-25
remove-obsolete-toolbar-capsule-code-2026-10-25

coach-text-inner-boundary-regression-2026-10-25

progress-check-2026-10-25T12:54:21.319Z

fix-nav-selector-2026-10-25
progress-check-2026-10-25T21:55+08:00
review-fixes-batch-2026-10-25
scroll-toolbar-gauge-and-style-regression-2026-10-25
correct-selected-tab-only-state-2026-10-25
scroll-position-toolbar-regression-2026-10-25
instrument-font-and-tab-signature-regression-2026-10-25

report-font-and-toolbar-diagnostics-2026-10-25

fix-diagnostic-summary-newlines-rerun-2026-10-25

rerun-after-multiline-diagnostic-fix-2026-10-25

panel-geometry-report-trigger-2026-10-26T0052+0800
restore-prior-week-disclosure-padding-regression-2026-10-26T0525+0800
fix-prior-week-legacy-selector-scope-2026-10-26T0530+0800
restore-prior-week-disclosure-legacy-shell-parity-2026-10-26T0613+0800
restore-prior-week-disclosure-labels-and-arrows-2026-10-26T0620+0800
capture-full-page-mobile-visual-regression-2026-10-26T0625+0800

refine-320px-industry-tabs-and-earnings-card-2026-10-26T0700+0800
refine-320px-tabs-test-contract-2026-10-26Tcontinued
news-scan-320px-padding-review-2026-10-26Tcontinued-branch

news-scan-320px-padding-review-selector-fix-2026-10-26
news-scan-320px-padding-review-selector-fix-rerun-2026-10-26
news-scan-320px-article-card-selector-2026-10-26
news-scan-320px-item-spacing-regression-2026-10-26
news-scan-320px-item-padding-6px-2026-10-26
news-scan-320px-remove-card-gaps-2026-10-26
news-scan-all-widths-legacy-gap-parity-2026-10-26

fix-exact-five-star-economic-and-earnings-markers-2026-10-26

architecture-audit-five-star-parser-fix-2026-10-26

computed-five-star-color-assertion-2026-10-26

Strict assertions enabled: fail on all recorded errors; require 16 red five-star glyphs and exactly 8 five-star earnings cards. Trigger 2026-10-26T01:40Z

Architecture step 1: consolidate duplicate .tac-ds-empty rule; verify 320/390/1440 regression. 2026-10-26T02:00Z

Architecture step 2: consolidate source-disclosure sizing into the canonical component rule; rerun strict browser regression. 2026-10-26T02:10Z

Architecture step 3: remove duplicate tabbed-panel padding and redundant mobile news typography overrides; verify browser regression. 2026-10-26T02:20Z

Architecture step 4: fold shared tab-container spacing into canonical rule; run strict regression. 2026-10-26T02:30Z

sector-label-mobile-duplicate-cleanup da3dc74f1ecec4abdd370e4ce5d670abedbff999

news-card-legacy-rules-removed 582a02eebf484ca2d0be9aae1df5c4ee3415d91f 97ae9c8c42b98c202d76d99516f9406cf55b8345

sector-row-legacy-rules-removed 8904b7d91be62648211b19377ec4de196c068253

Architecture step 5: remove superseded generic sector-row rules; validate canonical sector component at 320/390/1440. 2026-10-26T09:00+0800
Sentiment source disclosure legacy styling handoff 2026-10-26T09:00:00+08:00
Source-details legacy marker override removal 2026-10-26T09:10:00+08:00
Method disclosure component ownership migration 2026-10-26T09:20:00+08:00

Calendar source disclosure component ownership migration 2026-10-26T09:35:00+08:00

Dead calendar-source selector cleanup; verify no matching candidate DOM element and rerun regression 2026-10-26T09:45:00+08:00
Method disclosure inline-style migration: normalize 4 elements, remove legacy selector, assert ownership 2026-10-26T11:20:00+08:00
Fix disclosure block normalization and preserve summary typography; rerun browser regression 2026-10-26T11:30:00+08:00
Region/sector source disclosure typography migration; assert four summary signatures 2026-10-26T11:45:00+08:00
Retry after stale Playwright install; verify region/sector and sentiment dark disclosure CSS ownership 2026-10-26T12:05:00+08:00
Retry after normalizing computed CSS padding serialization in source disclosure assertion 2026-10-26T12:20:00+08:00

Layout-drift diagnosis: expand detailed DOM geometry capture for overview, news, industry and S&P earnings panels at 320/390/1440. 2026-10-26T11:25+0800

Compare baseline and candidate internal DOM geometry at all three viewports before layout changes. 2026-10-26T11:30+0800

Restore baseline two-row industry tab geometry and verify all viewports 2026-10-26

Retry after repairing industry tab CSS cascade and row sizing 2026-10-26

2026-10-26 industry-tabs-grid-retest after 1a2b6af83bdf8103dd59de1a89075ff1ec7981d7

2026-10-26 sector-row-height-retest after 0cb933eaaf6cc9ba713942aaca9c4c5896a4de8e
industry-tab-baseline-geometry-run-136-2026-10-26T1223+0800
revert-industry-tab-override-run-137-2026-10-26T1230+0800

Run 138: capture exact nav label geometry to diagnose industry panel height mismatch after reverting the failed tab styling trial.

Run 139: verify industry tab row-height correction against baseline geometry and shared style parity.

Run 140: verify S&P 500 earnings-health shell, title, and method-summary geometry at desktop and standard mobile widths.

Run 141: capture detailed child geometry for Fed, View, Calendar and Earnings panels before next parity fixes.

Run 142: pair baseline and candidate child geometry for Fed, View, Calendar and Earnings.

Run 143: verify Fed and View geometry restoration at desktop and standard mobile widths.

Run 144: measure paired calendar/earnings tab-row and content-region geometry at all three viewport sizes.

Run 145: compare calendar event-group and empty-state heights between baseline and candidate.

Run 146: verify calendar empty-state and tab-row geometry restoration at desktop, mobile and narrow mobile.

Run 147: verify calendar empty-state typography using baseline font size and normal line-height.

Run 148: verify small news-scan/global-market panel-height deltas after scoped nav sizing.

Run 149: verify economic-event shell migration after removing duplicate legacy outer-shell selectors.

Run 150: verify economic-event summary metadata migration and five-star red styling across all viewports.

Run 151: verify economic-event detail-field grid and responsive styles after legacy selector removal.

Run 152: verify event summary ownership and removal of unused econ-toggle CSS selectors.

Run 153: verify economic event-list wrapper migration and card layout across all viewports.

Run 154: verify earnings accordion shell migration across all 22 cards and open/close states.

Run 155: verify earnings accordion-list wrapper migration and all accordion interactions.

Run 156: capture final computed styles for earnings accordion shell, summary and toggle at desktop/mobile widths.

Run 157: verify earnings accordion summary-row migration and confirm no visible layout regressions.

Run 158: verify earnings company/date/subtitle/star typography migration and red-star contract.

Run 159: verify earnings accordion detail-field base styles while preserving last-week results-grid overrides.

Run 160: verify removal of redundant generic earnings-results and actual-card styles.

Run 161: verify prior-week actual-card styles moved to design system and no result-card visual regressions.

Run 162: verify prior-week earnings result-grid ownership after removing legacy !important chains.

Run 163: verify prior-week wide detail-field variant migration.

Run 164: verify removal of redundant earnings summary visibility override.

Run 165: verify prior-week earnings accordion closed-detail visibility after moving the Safari/mobile collapse safeguard into the design system.

Run 166: capture computed main-heading styles and matching CSS cascade rules across desktop, mobile, and narrow mobile to guide safe legacy cleanup.

Run 167: verify corrected main-heading cascade diagnostics and confirm heading computed styles plus matching CSS rules across all viewports.

Run 168: verify CSSOM heading-rule inventory includes matching legacy and design-system selectors while preserving all viewport smoke checks.

Run 169: verify removal of redundant low-specificity sentiment title color rule; compare all main heading computed styles and viewport regression checks with Run 168.

Run 170: verify removal of lower-specificity sentiment title color override while retaining white title color and all responsive regressions.

Run 171: verify removal of the early main.wrap sentiment-title white-color declaration; later stronger white exception must remain effective on all viewports.

Run 172: validate removal of block 93 low-specificity sentiment title white override; block 94 higher-specificity white exception must preserve the computed title color.

Run 173: validate removal of redundant body main.wrap sentiment title white rule; the later main.wrap #sentiment .title:first-child exception must retain white text across all viewports.

Run 174: verify removal of obsolete red sentiment-title color override; preserve sentiment up/down/warn colors and white title styling across desktop, mobile, and narrow mobile.

Run 175: verify removing only the redundant white-color declaration from the sentiment title rule; preserve its font size/weight and all responsive styles.

Run 176: verify removing block 47 instrument-row declarations that are superseded by later block 48; retain metadata font rules and check all product tabs at desktop/mobile/narrow-mobile.

Run 177: capture computed typography for representative bond, FX, energy, and precious-metal rows across all viewport widths before changing block 48/91.

Run 172: verify removal of the five-selector block 95 heading color escalation; block 94 must continue styling all five target headings identically across desktop, mobile, and narrow mobile.

Run 179: verify removal of block 91 bonds-name typography selectors now covered by design-system.css; compare computed style for bonds, FX, energy, and precious-metal rows on desktop/mobile/narrow mobile.

Run 180: verify removal of block 91 FX name selectors now covered by design-system.css .instrument-name rules; energy and precious-metal bare-bold selectors remain unchanged.

Run 181: verify restored block 91 FX-name specificity override after Run 180 showed legacy block 48 wins at mobile; retain only FX override, with bonds selector still migrated to design-system.css.

Run 182: verify energy instrument names are 16px on desktop, mobile, and narrow mobile, while energy values retain their existing compact 15px mobile typography and all panels/interactions remain stable.

Run 183: verify energy name typography remains 16px/1.35 on desktop/mobile/narrow mobile after removing its legacy block 91 selectors; keep precious-metal selectors intact.

Run 184: verify removing only block 48 mobile generic row-b 15px selector preserves 16px names in bonds/FX/energy/metals while keeping compact 15px numeric values and .name/.label variants.

Run 185: verify design-system ownership of precious-metal name typography at 16px/1.35 on desktop/mobile/narrow mobile before removing legacy block 91 selectors.

Run 185: inspect block 48 desktop row-name typography overlap against design-system.css; no CSS deletion until selector coverage and computed styles are proven. 2026-10-26T15:30+0800

Run 187: verify precious-metal name typography stays 16px/1.35 after removing block 91 legacy selectors; keep FX selector and validate all four product groups across desktop/mobile/narrow mobile.


Run 188: rerun after fixing dangling commas in retained legacy FX typography selectors; verify CSS parses and FX/bonds/energy/metals computed styles plus all viewport smoke checks. 2026-10-26

Run 189: verify removing block 48 .row .name/.label selectors unused by the baseline DOM; preserve bold names, compact numeric values, and all desktop/mobile/narrow-mobile checks.

Run 190: verify repaired block 48 .row b selector after removing unused .name/.label selectors; inspect artifact and all viewport styles. 2026-10-26

Run 190: verify removing block 47 .tab-panel .title small selector with zero DOM matches while preserving .tab-panel-meta typography and all viewport regressions.

Run 192: remove only redundant block 48 .row .up selector (all 7 hits are also .r); verify 1440/390/320 computed styles and interactions. 2026-10-26

Run 193: remove only redundant block 48 .row span.r selector (all 26 hits are already .row .r); verify computed styles and all viewport interactions. 2026-10-26

Run 194: remove only redundant block 48 span[style*=font-weight] selector (all 3 hits are also .r); verify styles and viewport regressions. 2026-10-26

Run 195: remove only redundant block 48 .row .down selector (all 6 hits are also .r); verify computed styles and all viewport regressions. 2026-10-26

Run 196: retry Run 195 after Install Playwright stalled before candidate build/tests; validate the same isolated CSS change, do not treat Run 195 as a pass. 2026-10-26

Run 197: test removal of block 48 generic row b rule only; all 13 names are covered by specific bond/FX/energy/metal name selectors, inspect computed typography and all viewport regressions. 2026-10-26

Run 198: remove only the redundant font-size declaration from block 48 generic row b rule; preserve line-height, weight, and letter-spacing after Run 197 exposed an energy letter-spacing shift. 2026-10-26

Run 198: inventory direct children and computed styles under all 13 instrument rows before considering block 48 generic .row rule; do not remove rule without proving no unique styling dependency. 2026-10-26

Run 200: remove only font-size:16px!important from block 48 generic row rule; preserve alignment and line-height after DOM inventory found all direct children have dedicated typography. Verify computed styles and all viewports. 2026-10-26

Run 201: remove only generic block 48 .row line-height:1.5 declaration; retain align-items and explicit child typography; verify computed line heights, row/panel geometry, and all viewport interactions. 2026-10-26

Run 202: remove the remaining block 48 align-items:center!important declaration; base .row already defines centered alignment and instrument-specific rules do not override it. Verify row geometry and all viewport interactions. 2026-10-26

Run 203: remove only block 48 generic row b line-height:1.5!important; keep font-weight and letter-spacing, as specific bond/FX/energy/metal name rules already provide 21.6px line-height. Verify all typography and viewport geometry. 2026-10-26
