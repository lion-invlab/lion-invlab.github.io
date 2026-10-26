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


## 2026-10-24 — News-card pilot passed

- SHA-pinned browser run: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40084737163 — `success`.
- Exactly 15 news items now use `tac-ds-card--news`; their backgrounds are uniformly white, border radii are 12px on desktop and 10px on mobile, with no overflow or new browser errors.
- Content, timestamps, source URLs, news selection and deduplication logic were not changed.
- Next inner-component pilot: economic event cards, preserving details/summary expansion and field layout.


## 2026-10-24 — Economic event-card pilot passed

- SHA-pinned browser run: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40084950673 — `success`.
- 12 economic event cards use `tac-ds-event`; desktop radius 12px, mobile/narrow-mobile radius 10px; event details expand/collapse successfully.
- Existing weekly economics/earnings disclosures, 21 shared tab labels, 15 news cards, 15 source/method disclosures and 4 empty states continue to pass regression.
- Event fields and content were not changed. Next pilot: the 22 earnings accordion cards.


## 2026-10-24 — Earnings accordion pilot passed

- SHA-pinned browser run: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40085163426 — `success`.
- All 22 earnings accordions use `tac-ds-earnings-card`; desktop radius 12px, mobile/narrow-mobile radius 10px; upcoming earnings tab and accordion open/close passed.
- No changes to earnings content, EPS consensus, event times, source URLs or data selection. Next pilot: sector ETF rows and prior-week actual earnings result cards.


## 2026-10-24 — Sector ETF row pilot passed

- GitHub Actions: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40111101979 — `success`.
- 11 個產業 ETF 列已使用共用資料列變體；桌機圓角 12px、手機／窄手機 10px，白色卡面一致。
- 三種 viewport 均通過產業頁籤切換、收折開啟與關閉循環；瀏覽器新增錯誤為 0，沒有橫向溢出、重複 ID 或未匹配導覽連結。
- 產業排序、ETF 報酬百分比、漲跌顏色、資料來源及資料內容未更動；不顯示價格的規則保留。
- 下一批：上週已公布財報的 EPS／營收結果卡，需保留 beat/miss 狀態色及雙欄排列，並先處理既有多組高特異性 CSS 的覆蓋風險。


## 2026-10-24 — Prior-week actual earnings result-card pilot passed

- GitHub Actions run: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40112871889 — `success`; tested commit `8e4dd02e789a896bde68516dee90c019681776b7`.
- Exactly 14 `.earnings-actual-card` result cards were found and styled within `#last-week-earnings`; desktop radius 14px, mobile/narrow-mobile radius 12px, white backgrounds.
- Browser smoke-test detected 6 beat and 2 miss statuses; all 14 cards remain present. Three viewport checks completed at 1440×1000, 390×844 and 320×800.
- No added browser errors, horizontal overflow, duplicate IDs, unmatched navigation links or missing panel IDs. Prior-week economics and earnings disclosures still open correctly; seven representative tab checks remain passing.
- EPS/revenue values, actuals, status logic and existing data-selection logic were not changed by the visual pilot.
- Mobile pixel diffs were recorded (390px: ~10.0%; 320px: ~12.7%) and remain subject to screenshot review; automated success is not a claim that all visual differences have been manually approved.
- Screenshots, pixel diffs, report and candidate HTML artifact: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40112871889/artifacts/12567511267 (7-day retention).
- Next gate: inspect the candidate/baseline/diff screenshots, then proceed to source/method disclosure or calendar status-group refinement based on risk. Do not bulk-delete legacy CSS; no production homepage or JSON/schedule was changed.


## 2026-10-25 — Special background theme isolation added (awaiting browser verification)

- Added Design System v1.9 scoped background contract for `#sentiment.tac-ds-panel--sentiment`: panel-local color tokens, layered gradients, concentric orbital rings, gold top accent, isolated stacking context and mobile-specific background.
- Added browser smoke assertions for the sentiment theme class, layered gradient background and both pseudo-element orbit/shadow layers at desktop 1440px, mobile 390px and narrow mobile 320px.
- Intent: future background customization of another main panel should not overwrite the sentiment theme; new themed panels should receive their own scoped variant instead of global background overrides.
- Current status: code committed to isolated refactor branch; GitHub Actions browser run pending. Do not treat as passed until all three viewport assertions pass and screenshots are reviewed.
- No production homepage, JSON data or scheduled automation changed.


## 2026-10-26 — 商品名稱共用字體與報價保留驗收通過

- GitHub Actions Run #218: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40296309253 — `success`；測試分支 `tac-design-system-work-2026-10-24`，觸發 commit `d471b63c357c61a9a2610ea0404f30b02a067a97`。
- 新增獨立 `instrument-typography-audit.mjs`，在 1440px、390px、320px 三種寬度逐項核對商品名稱及報價字體。
- 27 個商品名稱（全球股市 14 個、產業債匯商品 13 個）均符合共用規則：16px 字體、21.6px 行高、700 字重；每個 viewport 僅有 1 條 canonical name rule。
- 54 個報價值／每個 viewport，逐項與唯讀基準在同一寬度比較；全部符合基準字體簽章，未要求不同商品報價採用同一字級。
- 三種寬度均無水平溢出、缺失主版面、重複 ID、未匹配導覽連結或新增瀏覽器錯誤；各主版面高度差：桌機 overview +18px，其餘主要面板在 ±2px 內；手機 overview -1px，窄手機另以報告為準。這些數據代表自動化回歸，不等於所有像素差異已人工核准。
- Run #217 的失敗已定位為錯誤的報價字體測試假設；Run #218 改為基準逐項比較後通過，沒有為了讓測試變綠而修改報價 CSS。
- 正式首頁、正式母版、JSON 與排程均未修改。
- 下一步：延續 Gate 4，逐一檢視尚未完成的主版面／內層元件及 legacy CSS 覆蓋；不得把本次字體子任務通過視為整體重構完成。
