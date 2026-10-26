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
