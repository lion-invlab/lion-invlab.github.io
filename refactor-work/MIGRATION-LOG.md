## Run #266 — 2026-10-27 窄版活頁籤間距批次修正

- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40469033755
- Result: **success**; desktop/mobile/narrow-mobile typography audit passed (27 names and 54 quote values at each viewport).
- 修正已確認有效：320px 全球主要股市活動面板的上方間距由 +8px 回到 0px；產業債匯商品面板也由 +8px 回到 0px。此差異源自導覽列底部留白，不是面板的 margin-top。
- 320px 幾何差異大幅收斂：總覽由 +21px 降至 +5px；全球主要股市由 +12px 降至 +4px；產業債匯商品由 +10px 降至 +2px。新聞掃瞄為 -1px。
- 320px 剩餘差異：全球主要股市活動面板內部高度 +4px；產業債匯商品導覽列高度 +2px。保留目前觸控區尺寸，後續集中處理這兩項及桌面/一般手機標題面板約 -2px 的差異，不使用固定高度補償。
- 本次 CSS 僅變更隔離分支 `tac-design-system-work-2026-10-24`；正式首頁、正式母版、JSON 與排程未動。

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


## 2026-10-26 — Run #219 行事曆狀態頁籤回歸通過

- GitHub Actions Run #219: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40297130118 — `success`；commit `426bc3562d1d4b3e4c903d0bf71d33a124136dcf`。
- 三種寬度 1440／390／320 均驗證經濟行事曆與財報行事曆的「今日／即將／已公布」六個狀態：頁籤可選、對應面板可見、每次僅 1 個狀態群組可見。
- 三種寬度均無水平溢出、缺失主版面、重複 ID、未匹配導覽連結或新增瀏覽器錯誤；16 個五星標記顏色檢查通過；既有互動與主要元件檢查通過。
- 幾何差異待後續人工視覺核對：1440px overview 高度 +18px；390px overview -1px、S&P 500 財報健康 -2px；320px overview -62px、新聞掃描 -25px、S&P 500 財報健康 -34px、Fed -5px、觀察版面 +4px。這些變化未觸發現有回歸斷言，但不能視為已完成人工視覺驗收。
- 320px 下產業頁籤文字仍為 11px，新聞與全球市場頁籤為 12px；目前測試只要求窄螢幕不換行，這項尺寸差異列為待統一項目。
- 桌機全頁截圖高度 baseline 5147px、candidate 5165px，尺寸不同所以未計算全頁 pixel diff；不得把此結果描述成像素級完全一致。
- 本次僅變更隔離重構分支的測試程式、觸發檔與工作紀錄；正式首頁、正式母版、JSON 與排程未修改。
- 下一步：統一 320px 三組主頁籤字體尺寸並加入嚴格斷言；之後重新跑三尺寸回歸，再繼續 Gate 4 尚未完成的內層元件遷移與 legacy 規則清理。


## 2026-10-26 — Run #220 窄螢幕頁籤字級統一回歸通過

- GitHub Actions Run #220: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40297490428 — `success`；commit `38c2686b41d119cd18e735a4c199dfebdb179398`。
- 1440／390／320px 三種 viewport 的完整瀏覽器回歸通過；320px 版主頁籤字級斷言已納入測試。
- 320px 下新聞、全球市場、產業債匯商品三組主頁籤均為 12px、white-space nowrap；產業頁籤使用 6px 水平 padding，其餘兩組 7px，均無換行或水平溢出。
- 390px 下三組主頁籤均為 12px；1440px 下均為 13px，保留原本響應式字級規則。
- 主要互動、六個行事曆狀態頁籤、15 個來源／方法 disclosure、兩個上週 disclosure、新聞／經濟事件／財報／產業 ETF／上週實際財報卡等檢查均通過；新增瀏覽器錯誤 0，缺失面板／重複 ID／未匹配導覽／水平溢出均為 0。
- 幾何差異仍未視為完成驗收：320px overview 高度差 -62px、新聞掃描 -25px、S&P 500 財報健康 -34px、Fed -5px、觀察版面 +4px；390px overview -1px、S&P 500 財報健康 -2px；桌機 overview +18px。這些值需後續逐區塊對照 baseline/candidate，不能只因自動化通過就判定視覺已完全一致。
- 商品名稱共用字體仍通過：27 個名稱在三種寬度均為 16px／21.6px／700；每種寬度僅一條 canonical rule；54 個報價值逐項對照唯讀基準，未改動報價字體。
- 本次所有變更仍限於 `tac-design-system-work-2026-10-24` 隔離分支；正式首頁、正式母版、JSON 與排程未修改。
- 下一步：優先定位 320px overview -62px、新聞 -25px 與 S&P 500 財報健康 -34px 的實際來源，區分有意的共享元件間距變更與非預期的內容／換行差異；一次只調整可證明原因的 CSS，並重跑三尺寸回歸。


## 2026-10-26 — Run #221 窄螢幕幾何診斷完成

- GitHub Actions Run #221: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40297955653 — `success`；commit `472529af017e1e95b1789d4a5bf7e13d13a10016`。
- 已將總結區標題、內文、chips 與 BLUF 元件加入幾何報告；三種 viewport 的瀏覽器回歸、既有互動、無水平溢出／新增瀏覽器錯誤等檢查均通過。
- 重要解讀修正：`#overview` 的 7393px → 7331px（Δ -62px）是整個長頁面容器的累積高度，不是首頁總結卡自身縮短 62px。窄手機下第一張 BLUF 摘要卡實際是 692px → 689px（Δ -3px）；標題與正文高度基本相同。不得把整頁累積差異誤判成摘要卡本身的幾何錯誤。
- 新聞掃描在 320px 為 1503px → 1478px（Δ -25px）。細項顯示：頁籤列 48px → 32px（-16px）；新聞卡片依文字行數縮短約 8–10px／張（卡片內距由 11px 垂直縮至 6px），同時標題高度增加 2px。這與現有窄螢幕緊湊化 CSS 一致，但仍需確認縮短的卡片內距符合設計目標、文字沒有擁擠。
- S&P 500 財報健康區在 320px 為 943px → 909px（Δ -34px）。外層標題與摘要區高度差很小；主要差異來自內部 grid 由 266px → 235px（-31px），而後續卡片高度保持一致。現有窄螢幕 CSS 將卡片 padding 設為 9px、資料列 gap 設為 5px、padding 設為 7px；下一步需針對 grid 內部子列與文字換行作更細的對照，再決定是否回調，不先盲目加高外層。
- 320px Fed 高度差 -5px、觀察版面 +4px；其他主要面板高度一致。390px overview -1px、S&P 區 -2px；桌機 overview +18px，尚未做像素級人工核准。
- 本次只擴充隔離分支中的幾何診斷測試與記錄；正式首頁、正式母版、JSON 與排程未修改。
- 下一步：把 S&P grid 內部子列（含實際文字節點、行數、clientHeight/scrollHeight）加入診斷，並以新聞卡片實際文字換行作第二個判斷點。先拿到可比對的子節點數據，再做最小 CSS 修正與三尺寸回歸。


## 2026-10-26 — Run #222 S&P 500 子元素幾何深度診斷（artifact 已取回，診斷流程中止）
- GitHub Actions Run #222： https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40298318877；結論 `cancelled`，不是測試失敗。commit `26fb8e78184f63ac31bf17d53f236cdd4a34fd33`，分支 `tac-design-system-work-2026-10-24`。
- 實際 job steps 顯示：Checkout、Node setup、Playwright install、候選版本建置皆成功；「Run desktop and mobile smoke tests」步驟被取消；artifact 上傳成功。已下載 artifact `tac-refactor-browser-results.zip`（artifact ID `12639144652`，約 7.2 MB），內含 `browser-results/results.json`、`summary.md`、三個 viewport 截圖及候選 HTML。
- `results.json` 已含 `sp500DeepGeometry`。320px 下父 grid 量測為 266px（唯讀基準）→ 235px（候選），差 -31px；四張 metric 卡各自高度：基準 121/121/106/106px，候選 121/121/106/106px，並非四張卡一起縮短。候選 grid 容器縮短的主要可見原因，是第二列卡片起始位置相較基準提前約 14px（基準 top 6093、候選 top 6079）且 grid 的列／gap／padding 窄版規則需再以 DOM parent-child 對照確認；現有資料不能直接把 -31px 歸因於外層加高或特定單一宣告。
- 在 320px，首張核心判讀卡基準 219px、候選 219px；「如何解讀」卡均為 232px；提醒區均為 101px；來源 disclosure 內文均為 104px。故已排除上述子區塊單體高度是 -31px 的來源。390px 與桌面主面板整體差距分別只有約 -2px／-1px。
- Run #222 的瀏覽器 smoke tests 未完成，因此不能把 artifact 當成本次回歸通過；沒有修改任何 CSS。正式首頁、母版、JSON、排程均未修改。
- 下一步：在隔離分支檢查 `sp500DeepGeometry` 的 parent/child 關係和候選 HTML 中對應窄版 CSS，定位第二列 top 偏移與 grid track sizing 的確切來源。若診斷測試可在取消前完成，調整 workflow 的步驟／timeout 或拆分 diagnostic job；確認原因後才改 CSS，最後重跑 1440／390／320px 回歸。


## 2026-10-26 — Run #222 子元素對照補充：已定位 -31px 的具體組成，待重新回歸
- 對照 Run #222 artifact 中同一 320px viewport 的 `baseline.sp500DeepGeometry` 與候選 `sp500DeepGeometry` 後，確定 grid 由 266px 降至 235px（Δ -31px）不是整列 gap 單獨造成，而是第三、第四張指標卡由基準 137px 降至候選 106px（各 -31px）；第一、第二張卡維持 121px。
- 根因是窄版規則 `#sp500-earnings-health .tac-ds-card, #sp500-earnings-health .tac-ds-earnings-actual-card { padding: 9px !important; }` 沒有命中這四張內嵌指標卡，因其 HTML 尚未加入相應的 Design System 卡片 class。真正造成第三、第四張卡高度差的則是候選版文字節點可用寬度增加：基準卡內容寬 99px，候選卡內容寬 105px。因為候選版外層容器／內卡幾何不同，兩個比較長的輔助文字列由 48px 降成 32px（EPS 平均超預期幅度卡）及由 48px 降成 32px（混合營收年增率卡），每張卡少 31px。
- 此外，第三、第四張卡對應的輔助字串在基準寬度 99px 時都換成三行（48px），候選寬度 105px 時為兩行（32px）；這是可驗證的內容換行差異，而不是 grid 任意少高。這也表示 -31px 是兩張卡各自的高度少量，grid 的整體 track size 取兩列中較高的卡片後縮短 31px。
- 尚不立即回退所有 9px 規則：需先比較 320px 寬度預算與卡片左右 padding 的實際影響，採用最小且可維持可讀性的修正，並確認資料列與其他卡片元件的樣式邊界。Run #222 的 smoke-test step 被取消，需將幾何診斷獨立為短工作或修正 workflow 的 cancellation/timeout 觸發條件後，重新完成 1440／390／320px 全回歸。
- 未變更正式首頁、正式母版、JSON 或排程。


## 2026-10-26 — Run #222 說明更正：已確認窄版 -31px 的機制
- 更精確的基準／候選 DOM 同序列比較顯示：基準 320px 下第三、第四張 metric card 高度均為 137px，候選均為 106px；它們的內文提示各少一行（48px → 32px），因而每張少約 31px，grid 高度取列中最大高度後由 266px 變 235px。
- 但目前尚不能把根因定為「卡片 padding 規則未命中」；這四張內嵌卡在兩版量測的 padding 都是 11px 12px，真正待查的差異是基準內容寬 99px、候選內容寬 105px，導致同一段 11px 提示文字的斷行數不同。需檢查 320px 下外層面板 padding 16px → 10px、標題與卡片寬度的連帶影響，以及窄版 CSS 對 grid 子項的實際盒模型。
- 因此不依目前數據直接回退或增加卡片 padding；先以獨立診斷 job 比較可用內容寬度、grid column/row gap 和 computed styles，再決定最小修正。


## 2026-10-26 — Run #222 深度診斷結果已完整對照，進入最小修正前檢查
- Run #222 artifact 中的 `baseline.sp500DeepGeometry` 與候選 `sp500DeepGeometry` 都有 35 筆 320px 子元素，現已逐筆對照。
- 已確認：320px 下外層 S&P 面板 padding 16px → 10px，導致其內容寬度 258px → 270px；四張 inline-styled 指標卡的內容寬度因此 99px → 105px。第三、第四張卡各有一段 11px 輔助文字從 3 行（48px）變成 2 行（32px），卡高各由 137px 降至 106px，grid 整高由 266px 降至 235px。這是外層窄版 padding 引起的換行／高度變更，不是缺少卡片 padding 規則、也不是 gap 自行縮短。
- 目前已能證明造成 -31px 的幾何鏈條；但不能單憑「高度接近基準」決定是否應修，還需確認窄螢幕設計目的。基準較窄內容會換更多行但減少水平空間；候選卡內容較寬、少一行且更緊湊。下一步先比較整區內外 padding 與視覺可讀性，修正應限於 S&P 這個 panel 的 mobile outer padding／內部 grid，不更動文字或資料。
- Run #222 smoke-test step 已於長時間導覽回歸過程中被取消，artifact 數據可供診斷但不是驗收成功；因此任何 CSS 變更後仍必須重跑 1440／390／320px。


## 2026-10-26 — Run #223 三尺寸瀏覽器回歸通過；修正效果已驗證
- Run #223: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40305505809 — `success`，commit `bb93ce79a30804fea1d197a3b55a26cca8318a65`，分支 `tac-design-system-work-2026-10-24`。
- Playwright 安裝、候選 HTML 建置、desktop/mobile smoke tests、artifact upload 均成功。artifact ID `12642425979`（7.25 MB）；已下載並分析 `browser-results/results.json`、`instrument-typography-audit.json` 與截圖。
- S&P 500 panel 內層 grid 在 320px 已從 Run #222 的錯誤候選 235px 恢復至唯讀基準 266px；四張 metric cards 的高度對齊基準：121/121/137/137px。外層 panel 在 320px 為 943px，對比唯讀基準 943px，已修正原 -34px 差異。
- 1440／390／320px 均完成瀏覽器 regression：新增瀏覽器錯誤 0、水平溢出 false、缺失主要面板 0、重複 ID 0、未匹配導覽連結 0；導航錨點、頁籤與來源 disclosure 等既有互動通過；16 個五星紅色標示通過。商品名稱 audit：27 個商品（14 全球市場＋13 產業債匯商品）均為 16px／21.6px／700；每個 viewport 1 條 canonical rule；54 個報價值逐項對基準，均通過。
- 幾何剩餘事項：320px 新聞掃描仍比基準少 25px（符合已記錄的窄版頁籤／新聞卡 padding 緊湊化，仍待人工可讀性審核）；320px overview 長頁容器差異仍約 -62px，但首張 BLUF 卡只差 3px，不能誤讀為卡本身短 62px。標準手機 S&P panel 約 -2px，桌面約 -1px；整體全頁 desktop 高度 5147px vs 5165px，尚未宣稱像素級完全一致。
- 本次 CSS 改動只在隔離分支的 `refactor-work/design-system.css`：在 `max-width:380px` 下還原 `#sp500-earnings-health` 的 padding 至 16px；不改動任何資料、文字、報價或互動邏輯。正式首頁、正式母版、JSON、排程均未修改。
- 下一步：人工檢視本次 Run #223 的 candidate/baseline/diff 截圖，特別確認 320px 新聞卡內距的可讀性；再繼續下一個已量測的幾何差異與 Design System 元件／legacy CSS 遷移。不把單一回歸成功視為整體 CSS 重構完成。


## 2026-10-27 — Latest verified status: Run #248 heading-marker regression passed; geometry follow-up remains open

- Latest completed workflow verified from GitHub Actions: [Run #248](https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40351391304), conclusion `success`, commit `0357066235eeb5d9dd8aa96a9586d18d6ddd8629`.
- The preceding Run #247 failed at the browser smoke-test step. The subsequent isolated fix commit `c2f06198b082bca4a421f1d555a5d443b988c275` removes the duplicate border marker inside tabset headings while retaining the existing pseudo-element marker. Run #248 then passed.
- Run #248 artifact: [browser results, screenshots and candidate](https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40351391304/artifacts/12665041881), artifact ID `12665041881`, approximately 7.27 MB, retention until 2026-11-02 15:50 UTC.
- Geometry diagnostics in the successful run still show unresolved 320px differences: `#news-scan` candidate height 1493px versus baseline 1503px (−10px); its heading is +2px and first news tab panel is −12px. The three main tabset heading heights are 51px versus 49px baseline; global-market tab navigation is 34px versus 48px baseline (−14px), and industry tab navigation is 79px versus 89px baseline (−10px). These are not failures of the existing smoke assertions, but they are not pixel/geometry parity and need deliberate visual review before acceptance.
- Other 320px panels in this report are close to baseline: S&P 500 panel 942px versus 943px (−1px), and Today Focus 368px versus 368px. The panel child geometry report records cumulative vertical offsets of approximately −12/−13px after the changed heading/tabset regions; do not misattribute these downstream offsets to each later panel's own height.
- Important recordkeeping gap: the migration log had not been updated after Run #223 despite subsequent commits and runs. This entry restores a traceable pointer to the latest verified run.
- Next: inspect Run #248 candidate/baseline/diff screenshots and the detailed geometry artifact; resolve the narrow news panel and tab-navigation height differences one component at a time; rerun all 1440/390/320px checks. Continue the inner-component migration and legacy CSS audit only after the relevant visual and interaction gates pass. Do not bulk-delete legacy CSS.
- Safety boundary unchanged: no production homepage, official mother template, JSON or scheduled automation is modified by this work.


## Run #249 — 2026-10-27 窄手機頁籤幾何回歸

- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40431016478
- Result: **success**; browser smoke tests completed at 1440px, 390px, and 320px.
- CSS fix commit: `ed225650e1db34eaf17211cc35eb3374d4bcae9a` (narrow-mobile tab touch target geometry).
- Trigger commit: `131316dbeb39eb42db930d59ffc0090d6eae3225`.
- Artifact: `tac-refactor-browser-results`, ID `12702845076`.
- Regression checks: no horizontal overflow, missing panel IDs, duplicate IDs, unmatched nav links, or new browser errors. Tab controls, source disclosures, prior-week economics/earnings disclosures, and unified 16px instrument-name typography passed.
- At 320px, candidate panel geometry changed from Run #248 baseline comparison as follows: global markets 722px → 738px (+16px); industry/bonds/FX/commodities 502px → 514px (+12px). The increase is consistent with restoring narrow-screen tab touch target height and two-row layout.
- Remaining known geometry difference: `#news-scan` is 1493px vs baseline 1503px (-10px) at 320px. Do not treat the full layout as parity-complete; inspect the news panel and heading geometry separately before further migration.
- The CSS fix is currently an end-appended, scoped exception in `design-system.css`. After validation, consolidate it into the existing narrow-mobile tab rules rather than allowing one-off overrides to accumulate. Keep all work on the isolated branch; production homepage and official template remain untouched.


## Run #250 — 2026-10-27 CSS 規則整併回歸

- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40432544155
- Result: **success** after consolidating the narrow-mobile global-market and industry tab rules into their existing component sections and removing the end-appended override.
- Consolidation commit: `69d8cf9e4a4cf36b9db3a960702efb1d0f87d44a`; run trigger commit: `fc2b7fe8725b5d8fb61f394db8ea65274472149c`.
- Artifact: `tac-refactor-browser-results`, ID `12703260099`.
- 1440px: no horizontal overflow; panel geometry is at baseline for news/global/industry; no new browser errors.
- 390px: no horizontal overflow; all tracked panel heights match baseline except overview +1px; no new browser errors.
- 320px: no horizontal overflow; global markets panel 722px → 738px (+16px), industry/bonds/FX/commodities 502px → 514px (+12px), confirming the narrow-mobile touch-target correction remains after consolidation. No new browser errors.
- Known residual: `#news-scan` at 320px remains 1503px baseline vs 1493px candidate (-10px). Do not add a fixed-height compensation; inspect child-level geometry to locate the exact source. Overall pixel differences (390px ~11.29%, 320px ~13.82%) still need visual review as part of the ongoing migration.


## Run #252 — 2026-10-27 新聞卡片內距實驗回退後驗收

- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40439674930
- Result: **success** after reverting the oversized 11px vertical news-card padding experiment.
- Revert commit: `7135822fc338dcdbfb0e0c63e8ea8d7874c65836`; trigger commit: `fc4bc6cecc5af023318dee3a97598619252a90e6`.
- Artifact: `tac-refactor-browser-results`, ID `12706038036`.
- At 320px, `#news-scan` returned to 1493px candidate vs 1503px baseline (-10px); global markets 738px vs 722px (+16px); industry/bonds/FX/commodities 514px vs 502px (+12px). No horizontal overflow; existing panels/IDs/navigation links and interactions passed.
- At 390px, tracked panel geometry matches baseline except overview +1px. At 1440px, news/global/industry panel heights match baseline; overview is +20px, requiring separate later investigation and not part of this news-card experiment.
- News panel diagnosis: at 320px, heading is 51px candidate vs 49px baseline; nav is 48px both; content panel is 1379px vs 1391px (-12px). Attempting to set card padding to 11px 9px made the news panel 1542px (+39px), so it was reverted. Do not retry broad padding changes or force panel height. Next inspect per-card computed heights, text line counts/line-height, and margins against baseline, then make a narrowly scoped adjustment.


## Run #252 follow-up — 2026-10-27 差異定位補充

The artifact's narrow-mobile child-geometry diagnostic confirms the remaining discrepancy is isolated to two direct children inside `#news-scan`: heading 49px baseline vs 51px candidate (+2px), and active tab panel 1391px baseline vs 1379px candidate (-12px); tab nav is 48px in both. The panel's total is therefore 1503px vs 1493px (-10px). Desktop news panel is 807px in both and 390px is 1360px in both. This narrows the remaining fix to narrow-mobile heading and active panel internals, not the shared tab bar or global card padding. Next step: inspect actual nested news-card measurements/line counts from the built DOM before changing per-card spacing; existing smoke artifact currently reports only direct panel children, so do not infer which specific cards account for the 12px.


## Run #256 — 2026-10-27 窄手機新聞卡片 10px 內距驗收

- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40450641309
- Result: **success**; browser smoke tests, typography audit, and panel-child geometry diagnostics completed at 1440px, 390px, and 320px.
- CSS change: commit `8baf51212c94873c47ffdbfb3d4fbc6520aa7922`; narrow-mobile `#news-scan .newsitem` vertical padding adjusted from 11px to 10px, with horizontal padding 8px retained to account for shared-card border width and preserve text wrapping.
- At 320px, `#news-scan` is 1504px candidate vs 1503px baseline (+1px); active content panel is 1391px in both; first news card is 289px in both. The heading remains 51px candidate vs 49px baseline, while the outer panel total differs by only 1px because internal geometry offsets.
- At 390px, `#news-scan` is 1360px in both; at 1440px, 807px in both. No horizontal overflow or browser-smoke regression was reported.
- Conclusion: retain the 10px narrow-mobile card padding; do not add fixed heights or further blanket padding changes. Residual 2px heading-height difference at 320px can be reviewed separately only if visual comparison shows a meaningful mismatch. Production homepage and official mother template remain untouched.

## Run #259 — 2026-10-27 總結卡片幾何診斷

- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40454073387
- Result: **success**; exact nested geometry was captured for `article.card.bluf` and its title, headline, and summary paragraph at 1440px, 390px, and 320px.
- At 1440px, the summary card is 383px vs 364px baseline (+19px). Root causes: card padding 22px vs 16px (+12px total), title vertical padding (+2px), and title bottom margin 16px vs 11px (+5px). Downstream sections consequently shift about +19–20px.
- At 390px, card height is 608px vs 607px (+1px); at 320px, 689px vs 692px (-3px). The title's added vertical padding and margin are shared contributors.
- Corrective change committed as `aa18461afd3c5a63b2f9afdc806b81f5ba8be03b`: set the actual `.tac-ds-panel--bluf` card padding to 16px at all widths and restore title vertical padding to 0 and bottom margin to 11px while preserving the shared left marker. Follow-up browser regression: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40454306652 (pending at log update).
- Scope remains the isolated refactor branch; production homepage, official mother template, JSON, and scheduled automations are untouched.

## Run #260 — 2026-10-27 總結卡片修正後回歸驗收

- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40454306652
- Result: **success**; browser smoke tests and geometry/typography audits completed at 1440px, 390px, and 320px.
- Summary-card geometry is now an exact height match to baseline at all three widths: 1440px 364px vs 364px; 390px 607px vs 607px; 320px 692px vs 692px. Padding is 16px at each width; title height and bottom margin match baseline. The shared left marker remains, causing only a 1px content-width difference.
- Overall `#overview`: 1440px 4993px vs 4994px (+1px); 390px 6639px in both; 320px 7393px vs 7422px (+29px). The 320px overall delta is not from the summary card: narrow-mobile global markets remains +16px and industry/bonds/FX/commodities +12px, with the accumulated downstream offset about +30px. These are existing tab/nav geometry differences and remain a separate follow-up.
- Other tracked panel geometry is baseline-matched at 1440px and 390px except expected 1px rounding differences. At 320px, news remains +1px, global markets +16px, and industry/bonds/FX/commodities +12px. No horizontal overflow or smoke-test failure reported.
- Conclusion: **summary-card fix accepted**; do not further adjust its padding or heading spacing. Continue separately with narrow-mobile tab heading/nav geometry; do not use fixed-height compensation. Production homepage and official mother template remain untouched.

## Run #261 — 2026-10-27 共用標題垂直幾何回歸

- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40457469848
- Result: **success**; typography audit passed for desktop/mobile/narrow-mobile (27 names and 54 quote values per viewport).
- Canonical section-heading top/bottom padding is now 0px, matching baseline heading height. This removes the prior +2px heading difference, but also reduces the three tabset panel heights by 2px at 1440px and 390px; this needs a small spacing rebalance before final acceptance.
- At 1440px: overview 4993px baseline vs 4988px candidate (-5px); news/global/industry panels each -2px. At 390px: overview -6px; news -2px, global -2px, industry -2px. No browser smoke-test failures.
- At 320px: news 1502px vs 1503px baseline (-1px); global markets 736px vs 722px (+14px); industry/bonds/FX/commodities 512px vs 502px (+10px). Diagnostics identify two narrow-mobile factors: tab nav height +2px in global/industry and an 8px gap before the active tab panel (baseline 0px). Keep validated touch-target minimums; investigate the source of the 8px gap and remove only the unintended gap instead of reducing button hit areas or setting fixed panel heights.
- Summary card remains exact baseline height at all three widths. Production homepage and official mother template remain untouched.

## Run #267 — 2026-10-27 頁籤深層幾何診斷擴充

- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40470903788
- Result: **success**; desktop/mobile/narrow-mobile typography audit all passed (27 names and 54 quote values per viewport).
- Added nested geometry measurements to `refactor-work/panel-child-geometry-diagnostic.mjs`, including active tab panels, row labels/values, heading and navigation elements; logs now compare relative position, height, padding, margin and line-height.
- Verified 1440px/390px tabset deltas remain: news, global markets and industry panels each -2px. Their active panel top offsets shift upward (news -11px and global -6px) while content heights grow (+8px news, +4px global), indicating that these deltas are not explained by a simple outer padding change. Do not compensate with fixed heights.
- At 320px, global markets remains +4px and industry section +2px. The tab panel top positions and padding are stable; the remaining difference is inside the narrow-screen panel/nav geometry and needs a targeted next pass. Preserve the validated 40px global tab touch target and two-row industry tab target.
- This run was diagnostic-only; no CSS behavior changed. Next step is to inspect the detailed nested geometry report and apply only evidence-backed spacing corrections, then run the full regression again.
- All work remains on `tac-design-system-work-2026-10-24`; production homepage, official mother template, JSON and schedules are untouched.

## Run #268 — 2026-10-27 深層幾何完整輸出驗證

- Workflow： https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40471452892
- 結果：瀏覽器回歸成功；1440、390、320 三種寬度的字體稽核均通過（每種視窗 27 個名稱、54 個報價值）。
- 深層診斷確認：1440/390 下新聞掃描內層面板相對位置上移 11px、面板高度增加 8px；全球市場內層面板上移 6px、高度增加 4px；產業債匯商品內層面板上移 2px、高度不變。這些變化不能單純以外層 padding 解釋，因此本輪不做補償式 padding 修改。
- 320px：全球市場內層面板高度仍比基準多 4px；產業債匯商品內層面板位置下移 2px、內層高度不變。整體面板差異維持：overview +5px、news-scan -1px、global-markets +4px、industry +2px。
- 本輪僅確認診斷輸出與回歸結果，尚未修改 CSS。正式首頁、正式母版、JSON 與排程未動。
