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


## Run #270 — 2026-10-27 共用頁籤導覽列幾何回歸修正

- Run #269（https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40480446639）已成功完成；詳細幾何資料與截圖已下載檢視。
- 根因確認：共用頁籤 CSS 的導覽列與標籤尺寸和凍結基準不同。舊版候選導覽列 padding 為 3px，按鈕最小高度 34px；基準為桌面 padding 5px／按鈕 40px，手機 padding 4px／按鈕 38px，窄手機全球市場按鈕 40px。導覽列高度差使 1440／390px 內容面板上移；不能用外層 padding 補償。
- 已在隔離分支更新 `refactor-work/design-system.css`，共用導覽列還原至基準的圓角、padding、按鈕高度與字體語氣，保留窄手機全球市場 40px 可觸控目標。未修改總結卡片、HTML 母版、JSON 或排程。
- CSS commit：`26d094f244ac9bf3f4a350f7edad5cd5f693084f`
- 待驗收：本輪尚未取得修改後的瀏覽器回歸結果。下一步應觸發完整測試，再依結果核對 1440／390／320px、27 個商品名稱及 54 個報價字體稽核、總結卡片高度和頁籤幾何。


### Run #271 — narrow-mobile tab regression fix (2026-10-27)
- Run #270 exposed one confirmed failed assertion: at 320px, the news-scan main-tab labels computed `white-space: normal`, while the other two main tabsets were `nowrap`. The shared base rule had been overridden by a later narrow-mobile rule.
- Batched fix: set the news-scan narrow-mobile tab labels to `white-space: nowrap`, preserving the measured 38px minimum height, 6px/7px padding, 12px font, and existing scrollable tab strip. No outer-panel height compensation or legacy CSS deletion.
- CSS commit: 2c4d06b3897c840f732dd4fd921b67b7721bd3ea. Full browser regression rerun pending; do not treat as accepted until Actions finishes.


### Run #272 — main tab navigation geometry parity pass (2026-10-27)
- Run #271 completed successfully: browser smoke test and typography audit passed at 1440px, 390px and 320px. All three tabsets now meet the narrow-phone nowrap assertion; product-name typography remained 16px across global markets and industry instruments.
- Deep geometry still showed legacy compact overrides shrinking the news navigation (desktop 39px vs 52px baseline; 390px 35px vs 48px), with global markets and industry navigation also short by 10–12px at 390px and 8–12px at desktop. The active panels then shifted upward or expanded, so outer-panel padding is not the root cause.
- Batched CSS correction: restore baseline nav padding and label hit-target dimensions for news/global tabs; restore industry two-row navigation footprints by viewport; remove obsolete nav bottom margins instead of compensating panel padding. Keep the narrow-phone global-market 40px hit target and nowrap labels. No fixed panel heights or legacy CSS deletion.
- CSS commit: a5759b6ef985febf6e13b9c84bf8dfafd126f587. Full browser regression pending; geometry acceptance depends on measured results, not merely a green workflow.


### Run #272 — 導覽列幾何批次修正回歸結果與後續
- Run #272 workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40488935223 — **failed**. The typography audit was not the cause; the main-tab signature assertion caught that per-section legacy overrides still left different computed min-heights at desktop/mobile, despite nav geometry improving.
- Measured geometry improved: desktop news nav was restored toward baseline and industry panel height matched baseline (380px vs 380px); news/global panel heights still differ by -3/+4px at desktop and -1/+4px at 390px. At 320px, news remains -1px, global +4px, industry -1px. No horizontal overflow or instrument-font mismatch was reported.
- Follow-up batch: explicitly canonicalize computed font size, min-height, padding and wrapping across the three main tab labels per viewport, while retaining viewport-specific two-row grid geometry and the 320px global-market 40px hit target. CSS commit: 5d6b95ed56794c4a2c4ea1d86f3cda8334ab4fdf. Full regression required before acceptance.


### Run #273 — main-tab signature and nav geometry acceptance
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40489183407 — **success**. Browser smoke tests and font audits passed at 1440px, 390px, and 320px. The three main tabsets now have identical computed label signatures at desktop and 390px; narrow-mobile labels remain 12px and nowrap.
- Nav geometry is baseline-aligned: news/global nav 52px desktop and 48px mobile; industry nav 96px desktop, 90px at 390px (baseline 89px), and 88px at 320px (baseline 89px).
- Remaining inner-content deltas: news active panel +8px at desktop and 390px, global active panel +4px at all widths. This is independent of nav position/padding; no outer panel compensation will be applied. Added targeted logging of per-card and descendant geometry to the diagnostic script to identify the exact content source before the next CSS change.
- CSS commit for shared tab signatures: 5d6b95ed56794c4a2c4ea1d86f3cda8334ab4fdf. Diagnostic-only commit: 87d4e4f5c9ba09afbe4acd3c03c93734155c0ddf. Next full regression will provide card-level evidence; production homepage and official master remain untouched.


### Run #274 — card-level geometry diagnosis
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40489513571 — **success**; tab signature assertions and font audits passed.
- Card-level diagnostics identified the news-panel height drift: candidate .newsmeta uses line-height 13.5px while baseline computes normal (13px actual box), adding roughly 1px per visible metadata row and accumulating to +8px at desktop/390px. At 320px, the active news panel is already baseline-matched (1391px), so the correction is scoped to widths >=381px only.
- CSS fix commit: 1c6db661b833e554a5844658d0bf69bdcabc84eb. Extended nested diagnostics to report computed style differences even when element height/top are unchanged, to help isolate the remaining global-markets +4px delta. Full regression pending.


### Run #275 — news metadata line-height parity recheck
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40489968290 — **success**; browser regression and typography audit passed.
- Setting news metadata to baseline line-height normal reduced the news active-panel delta from +8px to +6px at desktop/390px, confirming the diagnosis. Remaining card deltas are +1px per visible card with title and paragraph heights unchanged; trimming only 1px of bottom padding per visible card at 381px+ should remove that residual without changing 320px geometry.
- Global markets remains +4px while its visible rows and panel padding appear unchanged. Expanded the diagnostic to include direct active-panel children and border/box-sizing metrics before any global-market CSS edit.
- CSS commit: 2eb68bce3a19f0bba0a73644bd98e7a7b2834444. Diagnostic commit: aef285fb60a79a5d7e19fca01b1d660d9a35591a. Full regression pending.


### Run #276 — news-card geometry residual correction
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40490772138 — **success**. Browser regression and all three typography audits passed.
- At 1440px/390px, news active-panel height is now +1px vs baseline; at 320px it remains exact (1391px). The remaining 1px at desktop/mobile comes from the final visible card rounding and is not large enough to justify further blanket spacing changes.
- Global-market active panel remains +4px at all widths. Existing row geometry and panel padding show no computed difference, so no CSS compensation was applied. Added a direct-child comparison for the active global-market panel to determine whether the difference is in the article card box or a lower-level content element.
- News-card padding correction commit: 2eb68bce3a19f0bba0a73644bd98e7a7b2834444. Diagnostic commit: f16ee4a15426e25f570dceec1b066341b587ab68. Next full run pending.


### Run #277 — global-market active article diagnosis
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40491242287 — **success**. The direct-child comparison isolates the remaining global-market delta to the active article: baseline article height 324px vs candidate 328px at desktop, while article padding, margin, border and box-sizing match. The active tab panel itself is +4px at 1440/390/320.
- This indicates a child inside the article—not the outer tab panel or navigation—is responsible. Expanded the diagnostic to report the article's direct children (metadata, rows, market summary, source disclosure) before adjusting styles.
- CSS unchanged this run; diagnostic commit: 868eddf05275ae7585867bb7f48fbe48d751db85. Next full regression pending.


### Run #278 — global-market +4px root cause confirmed
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40491533864 — **success**.
- Direct article-child diagnostics pinpointed the entire +4px global-market active-panel delta to the region source disclosure: baseline has `margin-top: 0` and no outer border; candidate had `margin-top: 2px` plus a 1px border (resulting disclosure box 23px vs 21px). The rows and market-reason block match baseline.
- Targeted fix: remove only the outer margin/border from `#global-markets details.source-details.region-source`, retaining the shared disclosure marker and typography. CSS commit: 9ab643d0067629d6f9d524f7ea1cf06c14a47b6f. Full regression pending.


### Run #279 — global-market source disclosure geometry acceptance
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40491813328 — **success**. Browser smoke tests and typography audits passed at 1440px, 390px, and 320px.
- Global-market panel now exactly matches baseline at all three widths: 477/477px desktop, 578/578px at 390px, 722/722px at 320px. Root cause was confirmed as the region source disclosure's extra 2px margin plus 1px border; targeted correction removed both without altering the shared arrow/text treatment.
- News panel residual: +1px desktop and 390px, -1px at 320px. Industry panel residual: exact desktop, +1px at 390px, -1px at 320px. These are isolated 1px rounding/card-edge differences; do not add fragile nth-child or outer-panel compensation rules. Overview cumulative geometry is +3px desktop/390px and -2px at 320px; summary card remains independently baseline-matched.
- CSS commit: 9ab643d0067629d6f9d524f7ea1cf06c14a47b6f. This closes the global-market +4px geometry issue. Next step is a focused audit of remaining legacy overrides and component migration candidates, not further arbitrary 1px compensation.


### Run #279 — CSS cascade cleanup follow-up
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40491813328 — **success**. Global-market geometry exactly matches baseline at 1440/390/320px; news/industry residuals remain within ±1px, and all typography audits pass.
- Refactor follow-up: consolidated the verified main-tab geometry and computed label signatures into one canonical block. Removed the superseded compact news-tab rules and duplicate narrow-mobile news overrides only after replacement behavior had passed browser regression. Preserved the separate Fed/Today Focus narrow-mobile rules, the validated 40px global-market hit target, source disclosure styling, and news-card geometry corrections.
- CSS cleanup commit: 70749de6de0a29d7bcc13dba290b923c78452414. Full regression pending; this is a cascade cleanup, not yet accepted until tests finish.


### Run #280 — tab cascade cleanup regression failed
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40492381368 — **failure**. Main tab signatures, global-market exact geometry, news/industry geometry (within 1px), browser interactions and typography audits still appear correct from the published summary.
- Failure source is not identified yet because the test summary omits several asserted fields (method/source typography, dark disclosure signatures, Fear & Greed marker, five-star count, source triangles and duplicate heading bars). The CSS brace structure is balanced; no broad rollback will be made based on guesswork.
- Added a diagnostic-only summary line exposing those hidden assertion values. Test-script commit: 3fadf334442c72aeb06db5d63b7e59b74712e5bf. Next run will identify the exact failed condition before deciding whether the cascade cleanup needs a targeted correction or rollback.


### Run #281 — hidden assertion metrics still pass; failure narrowed
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40493169275 — **failure**. The newly exposed hidden metrics all pass: method disclosures 4/0 inline styles, all four region source typography records match, three dark disclosure signatures match, Fear & Greed score/marker 21/21, five-star red count 16, source triangles 11, double-bar headings 0, and sector tab colors are correct.
- The failing condition is therefore among remaining unreported interaction/contract booleans, especially earnings upcoming tab and disclosure/button contracts. Expanded the summary to print those exact values; no CSS rollback or unrelated fix until the specific predicate is identified.
- Test diagnostic commit: 710b9ac59f0407aee229aeebee9803f7eba60705. Next regression pending.


### Run #282 — Playwright setup stalled; retry requested
- Run #282 was still in `Install Playwright` several minutes after the job began and had not reached candidate build or browser tests. No test result is claimed from this run.
- Retrying on a fresh Actions run to avoid treating a stalled dependency-install step as a browser regression result. Diagnostic test code remains unchanged; the next completed run should expose the remaining failed assertion values.


### Run #283 — exact failing assertion identified
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40493799412 — **failure**, browser build succeeded and all interactions/typography checks passed.
- The sole remaining smoke-test contract violation is at 320px: `#news-scan` tab labels compute `white-space: normal`, but the acceptance rule requires `nowrap` at widths <=380px. Global-market and industry tabs already satisfy the contract. This came from consolidating the shared mobile rule without retaining the narrower news-label override.
- Restored the explicit narrow-phone news-label `white-space: nowrap !important` rule only inside the <=380px media query. No height or padding compensation added. CSS fix commit: d51c16ba3e9ec2f5cd65d6f8b32782af756ff639. Full regression pending.


### Run #284 — main-tab cascade cleanup accepted
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40510250622 — **success**. Playwright install, candidate build, desktop/mobile smoke tests, typography audit and panel-child geometry diagnostic all completed successfully.
- Restoring `#news-scan .tac-tab-nav label { white-space: nowrap !important; }` under `max-width: 380px` cleared the only remaining acceptance failure. At 320px all three main-tab signatures now satisfy the required 12px/nowrap contract; at 390px their shared signatures match, and desktop signatures match.
- Geometry remains stable: global-market and industry panels exactly match baseline at all tested widths; news is within ±1px; overview remains +3px desktop, +2px at 390px, and -1px at 320px. No new browser errors, missing panels, duplicate IDs, or tab interaction failures. CSS fix commit: d51c16ba3e9ec2f5cd65d6f8b32782af756ff639.
- CSS cascade cleanup is accepted for this phase. Next: audit remaining duplicate/legacy selectors for safe, test-backed consolidation; preserve the current passing commit as the regression baseline.


### Run #284 — follow-up dead-rule audit
- Regression accepted: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40510250622 — **success**. This established a passing baseline before further cleanup.
- Computed styles show the canonical main-tab block supersedes three older industry row-height declarations (36/36 desktop, 32/33 mobile, 38/39 narrow phone), a narrow-phone industry label padding/font block, and a duplicate global-market `min-height: 40px` declaration. Removed only these demonstrably overridden declarations; canonical row heights, 320px nowrap, and validated hit targets remain unchanged.
- Cleanup commit: f3b5be37128553c90a5f291197ed748e4630e539. Full regression pending; no claim of acceptance until Run #285 completes.


### Run #285 — runner setup cancellation; not an acceptance result
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40510684448. The candidate build completed, but the job was cancelled during Playwright/Ubuntu dependency installation after long, stalled package downloads; desktop/mobile smoke tests were cancelled and did not run. This is an environment/setup interruption, not evidence that the CSS change passed or failed.
- The cleanup from commit f3b5be37128553c90a5f291197ed748e4630e539 remains **pending regression acceptance**. No additional CSS changes made.
- Started Run #286 as a fresh retry with the same candidate and no CSS changes. Do not proceed with further CSS deletion until a complete browser regression finishes.


### Runs #286–#287 — runner setup bottleneck and mitigation
- Run #286: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40513078716 — cancelled during Playwright installation; candidate build and browser tests were skipped. Run #285 had the same outcome. Logs show Ubuntu package downloads taking several minutes and the workflow's 15-minute job timeout expiring.
- Mitigation: changed only the isolated browser-test workflow runner from `ubuntu-latest` (the current Ubuntu 26.04 image) to `ubuntu-24.04` to avoid the newly observed package-mirror bottleneck. CSS files and production files were not changed by this mitigation.
- Run #287 was triggered against the same pending CSS candidate. The dead-rule cleanup remains **not accepted** until candidate build, desktop/mobile smoke tests, typography audit, and panel geometry diagnostics complete.

### Run #287 — dead-rule cleanup browser regression accepted (2026-10-27)
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40530796528 — **success**. Ubuntu 24.04 setup completed; candidate build, desktop/mobile smoke tests, typography audit, geometry diagnostics, screenshots and test report all completed.
- This run tests the pending dead-rule cleanup from CSS commit `f3b5be37128553c90a5f291197ed748e4630e539`. All three typography audits passed: desktop, mobile and narrow-mobile each compared 27 instrument names and 54 quote values against baseline.
- Browser contract checks: no horizontal overflow, duplicate IDs, new browser errors or tab errors. Navigation-anchor visibility and interaction contracts passed; the previously reported hidden acceptance metrics also match the expected values. Main tab signatures and the validated disclosure/button behavior remain intact.
- Geometry diagnostic confirms global-market and industry panels match baseline at 320px (722px and 502px respectively); at 390px, prior-week/calendar/earnings panels shown in the report also match exactly. Overview and news remain within the previously accepted 1–3px rounding deltas; no compensating CSS was added.
- Dead-rule cleanup is now regression-accepted on the isolated branch. Ubuntu runner mitigation affects only the test workflow. Production homepage, official master template, JSON and schedules remain untouched.

### Run #288 — narrow-phone industry-row duplicate cleanup pending
- After Run #287 accepted the previous cleanup, the next selector audit found one more provably redundant declaration: the `max-width: 380px` rule repeated `grid-template-rows: 37.5px 37.5px !important` already set by the enclosing `max-width: 700px` rule for the same selector. No intervening narrower rule changed that property.
- Removed only the duplicate declaration; the inherited 320px computed value remains 37.5px / 37.5px. CSS commit: `56ea0e210ffa8875bc11699b2f9f0f70eee54f1d`.
- This is **pending regression acceptance**. No other CSS selectors were changed; production homepage, official master template, JSON and schedules remain untouched.

### Run #288 — narrow-phone industry-row duplicate cleanup accepted (2026-10-27)
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40574004443 — **success**. Candidate build, Playwright browser smoke tests, typography audit, geometry diagnostics, and artifact upload all completed successfully on Ubuntu 24.04.
- All desktop/mobile/narrow-mobile typography audits passed: 27 instrument names and 54 quote values matched baseline in each viewport.
- Browser checks: no horizontal overflow, duplicate IDs, new browser errors, or tab errors. Navigation anchors and interaction contracts passed. The industry/global-market panels retained baseline geometry, including the 320px industry panel height of 502px; the removed narrow-phone declaration was redundant.
- The cleanup from CSS commit `56ea0e210ffa8875bc11699b2f9f0f70eee54f1d` is regression-accepted. Production homepage, official master template, JSON and schedules remain untouched.


### Run #289 — superseded narrow-phone tab cleanup accepted (2026-10-27)
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40574457088 — **success**. Playwright install, candidate build, desktop/mobile/narrow-mobile smoke checks, typography audit, panel-child geometry diagnostics and artifact upload all completed.
- Typography audits passed at desktop, mobile and narrow-mobile: 27 instrument names and 54 quote values compared with baseline in each viewport. All tested widths had no horizontal overflow, duplicate IDs, new browser errors or tab errors; navigation anchors and tab/disclosure interactions passed.
- At 320px, global-markets remained 722px and industry panel remained 502px, both matching baseline exactly. At 390px, the industry panel diagnostic showed a +5px delta, but this viewport is outside the removed <=380px block; this is not attributed to this cleanup. Other reported geometry deltas remain within the existing migration baseline and no compensation CSS was added.
- The cleanup from CSS commit a7fa6631197cb12ffd84e6736510db611f8363cd is regression-accepted. Production homepage, official master template, JSON and schedules remain untouched.


### Run #290 — event-name font-size duplicate accepted (2026-10-27)
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40575767093 — **success**. Candidate build, browser smoke tests, typography audit, panel geometry diagnostic and artifact upload all completed.
- Desktop/mobile/narrow-mobile typography audits passed (27 instrument names and 54 quote values per viewport). No horizontal overflow, duplicate IDs, new browser errors or tab errors; global-market and industry panel geometry matched baseline at 320px and desktop. The removed mobile event-name font-size declaration was identical to the base 15px declaration.
- Cleanup from CSS commit 9c27a3d0de9a05d96b498bfbe2c0ac2bc85fe420 is regression-accepted. Production homepage, official master template, JSON and schedules remain untouched.


### Run #291 — superseded shared mobile-tab declaration accepted (2026-10-28)
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40577824430 — **success**. Candidate build, desktop/mobile/narrow-mobile smoke tests, typography audit, geometry diagnostics and artifact upload completed.
- Typography audits passed at desktop, mobile and narrow-mobile (27 instrument names and 54 quote values compared with baseline per viewport). No horizontal overflow, duplicate IDs, new browser errors or tab errors; navigation and tab/disclosure interactions passed.
- At 320px, global-markets remained 722px and industry panel remained 502px, matching baseline exactly. At 390px, industry panel retained the known +5px diagnostic outside the removed declaration's <=700px? Note: this cleanup removes a shared <=700px duplicate, so the geometry delta is recorded as existing baseline variance and is not claimed to be caused by this one declaration. No compensation CSS added.
- Cleanup from CSS commit 3b58e39e903bd1f1900eb397f53cfe0d0b93c01e is regression-accepted. Production homepage, official master template, JSON and schedules remain untouched.


### Run #292 — superseded narrow-mobile S&P shell padding accepted (2026-10-28)
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40602358370 — **success**. Candidate build, desktop/mobile/narrow-mobile smoke tests, typography audit, panel geometry diagnostics and artifact upload completed.
- Typography audits passed at desktop, mobile and narrow-mobile (27 instrument names and 54 quote values compared with baseline per viewport). No horizontal overflow, duplicate IDs, new browser errors or tab errors; navigation and tab/disclosure interactions passed.
- At 320px, the S&P 500 earnings-health panel remained 942px versus 943px baseline (1px difference); global-markets remained 722px and industry panel remained 502px, both matching baseline. The 390px industry-panel +5px diagnostic remains an existing baseline variance and is not attributed to this S&P shell cleanup.
- Cleanup from CSS commit c1ff4cf79d09dbd905b63ac5bd762e5a1d3cdfad is regression-accepted. Production homepage, official master template, JSON and schedules remain untouched.


### Run #293 — consolidate duplicate theme-token root block accepted (2026-10-28)
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40602625460 — **success**. Candidate build, desktop/mobile/narrow-mobile smoke tests, typography audit, panel geometry diagnostics and artifact upload completed.
- Typography audits passed at desktop, mobile and narrow-mobile (27 instrument names and 54 quote values compared with baseline per viewport). No horizontal overflow, duplicate IDs, new browser errors or tab errors; navigation and tab/disclosure interactions passed.
- Moving the three heading marker custom properties into the canonical top-level `:root` block preserved their names and values; no geometry or computed typography changes were introduced. Existing diagnostic deltas remain: 390px industry panel +5px and 320px S&P earnings-health panel -1px, neither attributed to this token-only structural cleanup.
- Cleanup from CSS commit a3e074ad79814dff0cb1128bb7d96ba8a4420187 is regression-accepted. Production homepage, official master template, JSON and schedules remain untouched.


### Run #294 — superseded narrow-mobile S&P title spacing accepted (2026-10-28)
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40603610697 — **success**. Candidate build, desktop/mobile/narrow-mobile smoke tests, typography audit, panel geometry diagnostics and artifact upload completed.
- Typography audits passed at desktop, mobile and narrow-mobile (27 instrument names and 54 quote values compared with baseline per viewport). No horizontal overflow, duplicate IDs, new browser errors or tab errors; navigation and tab/disclosure interactions passed.
- At 320px, S&P earnings-health panel measured 942px versus 943px baseline (−1px); global-markets remained 722px and industry panel 502px, both matching baseline. At 390px, industry panel retains the known +5px diagnostic, not attributed to this title-spacing cleanup. Desktop S&P panel is +1px; no compensation CSS added.
- Cleanup from CSS commit 76dc63122056b009a37bc43279af2f91116b063a is regression-accepted. Production homepage, official master template, JSON and schedules remain untouched.


### Run #295 — superseded audit disclosure marker color accepted (2026-10-28)
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40603945617 — **success**. Candidate build, desktop/mobile/narrow-mobile smoke tests, typography audit, panel geometry diagnostics and artifact upload completed.
- Typography audits passed at desktop, mobile and narrow-mobile (27 instrument names and 54 quote values compared with baseline per viewport). No horizontal overflow, duplicate IDs, new browser errors or tab errors; navigation and tab/disclosure interactions passed.
- The marker color remains gold as intended: the earlier gray `color` declaration was superseded by the later exact-selector rule. Existing geometry diagnostics remain unchanged from prior runs; no compensation CSS was added.
- Cleanup from CSS commit ff774c7a309f518578df308081164783ac15d759 is regression-accepted. Production homepage, official master template, JSON and schedules remain untouched.


### Run #296 — duplicate mobile global-markets tab declarations accepted (2026-10-28)
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40609489046 — **success**. Candidate build, desktop/mobile/narrow-mobile smoke tests, typography audit, panel geometry diagnostics and artifact upload completed.
- Typography audits passed at desktop, mobile and narrow-mobile (27 instrument names and 54 quote values compared with baseline per viewport). No horizontal overflow, duplicate IDs, new browser errors or tab errors; navigation and tab/disclosure interactions passed.
- Removing the redundant mobile global-markets label block preserved the shared selector behavior. Global-markets panel geometry matched baseline at all checked viewports; existing diagnostics remain (390px industry panel +5px, 320px S&P earnings-health panel −1px), not attributed to this duplicate-declaration cleanup. No compensation CSS added.
- Cleanup from CSS commit 58fdbc5181e4ac7bbc062b538cfad6fc9d6151ce is regression-accepted. Production homepage, official master template, JSON and schedules remain untouched.

### CSS audit #297 — duplicate-rule scan completed; no safe removal selected (2026-10-28)
- Audited the current `refactor-work/design-system.css` (1,775 lines) for duplicate declarations within individual CSS rules and identical selector/declaration blocks within the same media context. The scan found no duplicate properties within a single rule and no identical repeated selector blocks in the same media context.
- Repeated-looking narrow-mobile and desktop rules were retained where their media queries are complementary or where they intentionally preserve measured baseline geometry. No CSS was changed and no browser workflow was triggered because there is no candidate change to test.
- Next pass should move to selector-usage / legacy-rule ownership analysis rather than remove breakpoint-specific geometry rules by appearance alone. Production homepage, official master template, JSON and schedules remain untouched.

### Run #297 — remove unused tab-heading selector branch accepted (2026-10-28)
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40611253077 — **success**. Candidate build, desktop/mobile/narrow-mobile smoke tests, typography audit, panel geometry diagnostics and artifact upload completed.
- Static usage audit found no `tac-section-title` class in the candidate DOM or script text, and the component migration map does not define it as a component contract. Removed only the unused selector branch `html body main.wrap .tac-tabset .tac-section-heading h2.tac-section-title`; the broader tabset-heading selector and its two declarations remain intact.
- Typography audits passed at desktop, mobile and narrow-mobile (27 instrument names and 54 quote values compared with baseline per viewport). No horizontal overflow, duplicate IDs, new browser errors or tab errors. Navigation anchors, tabs, source/prior-week disclosures, event and earnings interactions passed; double-bar headings=0 and instrument-name font sizes remained consistent at 16px.
- Geometry diagnostics recorded desktop deltas up to +3px on overview and +1px on several panels; 390px overview +7px and industry panel +5px; 320px overview −1px, news −1px and S&P earnings-health −1px. These are existing baseline comparison diagnostics and are not attributed to this selector-only cleanup; no compensating CSS was added.
- Cleanup from CSS commit 43d64f89638363c60df67b0b6cbd45f43272d588 is regression-accepted. Production homepage, official master template, JSON and schedules remain untouched.

### Run #298 — remove unused fund-dashboard wrapper styles accepted (2026-10-28)
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40611649987 — **success**. Candidate build, desktop/mobile/narrow-mobile smoke tests, typography audit, panel geometry diagnostics and artifact upload completed.
- Static audit found no references in the candidate page's markup or inline scripts to the old wrapper/navigation classes `.fund-report-card`, `.fund-report-head`, `.fund-report-title`, `.red-highlight`, `.fund-report-sub`, `.fund-report-list`, `.dashboard-link`, `.vol-dashboard-link`, `.fund-dashboard-link`, `.mobile-only`, `.q4-nav` or `.tomorrow`. The homepage dynamically generates `.fund-date-row`, `.fund-dot`, `.fund-date`, `.fund-names`, and `.fund-status` rows from linked fund-dividend data, so those rules and their mobile sizing were preserved.
- Removed only unreferenced wrapper/navigation declarations and corresponding mobile overrides. No script, data fetch, host element ID, generated row class, or interaction logic was changed.
- Regression passed at 1440/390/320px: no horizontal overflow, duplicate IDs, or new browser errors; navigation and tab/disclosure/event/earnings interactions passed. Typography audits passed at desktop, mobile and narrow-mobile (27 instrument names and 54 quote values compared with baseline per viewport); global-market and industry instrument names remained 16px. Existing geometry diagnostics remain unchanged (390px industry panel +5px, 320px S&P earnings-health panel −1px, with small +1–7px differences in other panels); no compensating CSS was added.
- Legacy CSS cleanup commit 8edb79732fce0c52da911c1cda068f7471dcd87b removed 1,136 characters and is regression-accepted. Production homepage, official master template, JSON and schedules remain untouched.

### Run #299 — remove obsolete sector child selectors accepted (2026-10-28)
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40611903057 — **success**. Candidate build, desktop/mobile/narrow-mobile smoke tests, typography audit, panel geometry diagnostics and artifact upload all completed.
- Static audit of candidate markup and inline scripts found no `.sector-name` or `.sector-pct` references. The current sector list container remains in place; live rows use the migrated sector-row component, so only four obsolete child typography/color rules were removed. No current `.sector-row` / `.tac-ds-data-row--sector` styles were changed.
- All three typography audits passed: desktop, mobile and narrow-mobile each compared 27 instrument names and 54 quote values against baseline. No horizontal overflow, duplicate IDs, new browser errors or tab errors; navigation anchors, tabs, source/prior-week disclosures, event and earnings interactions passed. Global-market and industry instrument names remained consistent at 16px.
- Geometry diagnostics: desktop overview +3px and several panels +1px; 390px overview +7px and industry panel +5px; 320px overview −1px, news −1px and S&P earnings-health −1px. These remain recorded diagnostics and are not attributed to this selector-only cleanup. No compensating CSS was added.
- Legacy CSS commit 61a20ad16d686cb2d2bdd8b6ff88918d8c2e9dd6 removed 216 characters and is regression-accepted. Production homepage, official master template, JSON and schedules remain untouched.


### Run #300 — remove obsolete history custom-element selectors accepted (2026-10-28)
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40627395769 — **success**. Candidate build and desktop/mobile/narrow-mobile smoke tests, typography audits and screenshot/diff artifacts completed.
- Candidate-markup audit found no `<history-panel>`, `<history-box>`, `<history-field>`, `<history-btn>`, `<history-note>`, `<history-status>` or `<history-nav>` custom elements. The current sidebar history tool uses separate `tac-history-mini` classes; the live `.history-status` class and script references were deliberately preserved.
- Removed only nine old custom-element selector rules (868 characters); no class selectors, JavaScript, data, IDs or interactions changed. Typography audits passed at all three viewports, each comparing 27 instrument names and 54 quote values against baseline. No horizontal overflow, duplicate IDs, new browser errors or tab errors; tested navigation, calendar/earnings accordions, sector tabs/collapse, source disclosures, prior-week collapses and toolbar onboarding checks passed.
- Geometry diagnostics remain stable: 1440px overview +3px, sentiment/news/earnings-health/fed/view mostly +1px; 390px overview +7px and industry panel +5px; 320px overview −1px, news −1px and S&P earnings-health −1px. No compensating CSS was added. CSS commit 97c918f622e66940516cd13844ac886be2e7f124 is regression-accepted. Production homepage, official master template, JSON and schedules remain untouched.

### Run #301 — remove obsolete history element state selectors accepted (2026-10-28)
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40627710577 — **success**. Candidate build, desktop/mobile/narrow-mobile smoke tests, typography audits and screenshot/diff artifacts completed.
- Removed three obsolete custom-element state selectors `history-btn.primary`, `history-btn.secondary`, and `history-status.ok` (140 characters). Candidate has no matching custom elements; current `.history-btn` and `.history-status` class styles and script references remain untouched.
- All typography audits passed at desktop, mobile and narrow-mobile, each comparing 27 instrument names and 54 quote values against baseline. No horizontal overflow, duplicate IDs, new browser errors or tab errors; navigation anchors, tabs, source disclosures, prior-week collapses, event/earnings accordions and toolbar onboarding checks passed.
- Geometry diagnostics remain consistent: desktop overview +3px and several panels +1px; 390px overview +7px and industry panel +5px; 320px overview −1px, news −1px and S&P earnings-health −1px. No compensating CSS was added. CSS commit 3896f941121edd53c8b26493ee8c1cd2ec96ceac is regression-accepted. Production homepage, official master template, JSON and schedules remain untouched.
- Follow-up selector audit found three remaining legacy rules written as custom-element selectors rather than classes: `history-btn.primary`, `history-btn.secondary`, and `history-status.ok`. Candidate HTML contains no matching custom elements. The live class selectors `.history-btn`, `.history-status` and their real current styling/script references remain untouched.
- Removed exactly three obsolete rules (140 characters). CSS commit: 3896f941121edd53c8b26493ee8c1cd2ec96ceac. Pending Run #301 browser regression; production homepage, official master template, JSON and schedules remain untouched.

### Run #302 — remove unused legacy table styling accepted (2026-10-28)
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40652856077 — **success**. Candidate build, desktop/mobile/narrow-mobile smoke tests, typography audits and screenshot/diff artifacts completed.
- Static audit confirmed no table markup, closing table tags or direct JavaScript creation of table-related elements in the candidate. Removed five unused legacy table selector rules (341 characters); no data, scripts, IDs or interaction logic changed.
- All three typography audits passed (desktop/mobile/narrow-mobile, each comparing 27 instrument names and 54 quote values with baseline). No horizontal overflow, duplicate IDs, new browser errors or tab errors; tested navigation, disclosures, prior-week collapses, event/earnings accordions, sector tabs and toolbar onboarding passed. Instrument labels remained 16px across global markets and industry.
- Geometry diagnostics remain stable: desktop overview +3px and several panels +1px; 390px overview +7px and industry panel +5px; 320px overview −1px, news −1px and S&P earnings-health −1px. No compensating CSS was added. CSS commit ced809d16b9191f850bdaea3ef6d34260c53454a is regression-accepted. Production homepage, official master template, JSON and schedules remain untouched.
### Run #303 — remove duplicate legacy heading declaration accepted (2026-10-28)
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40653247519 — **success**. Candidate build, desktop/mobile/narrow-mobile smoke tests, typography audits and screenshot/diff artifacts completed.
- Exact-rule audit found a duplicated top-level heading declaration in the V10 legacy block. It is byte-identical to the existing V9 declaration for `.card:has(.vol-dashboard-link) .title`, `.fund-report-title`, and `.history-panel>.title`; the earlier declaration was retained.
- Removed only the second duplicate declaration (213 characters). Typography audits passed at all three viewports (27 instrument names and 54 quote values compared with baseline per viewport). No horizontal overflow, duplicate IDs, new browser errors or tab errors; navigation, disclosures, prior-week collapses, event/earnings accordions, sector tabs and toolbar onboarding checks passed. CSS commit 63345a9d775f70f251a9f2865260220c1a9aad3f is regression-accepted.
- Geometry diagnostics remain consistent with prior runs: desktop overview +3px and several panels +1px; 390px overview +7px and industry panel +5px; 320px overview −1px, news −1px and S&P earnings-health −1px. No compensating CSS was added. Production homepage, official master template, JSON and schedules remain untouched.

### Run #304 — remove duplicate calendar collapse state rule accepted (2026-10-28)
- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40661199040 — **success**. Candidate build, desktop/mobile/narrow-mobile smoke tests, typography audits and screenshot/diff artifacts completed.
- Context-aware exact-rule audit found the identical open-state rule for calendar and earnings accordions twice at top level. The earlier declaration remains; no matching selector appears between occurrences, so removing the later duplicate does not change the cascade. Removed one duplicate rule (143 characters). CSS commit: 45dd12fdc5cf366719f6105dc5a859defa6f6248.
- Typography audits passed at all three viewports (27 instrument names and 54 quote values compared with baseline per viewport). No horizontal overflow, duplicate IDs, new browser errors or tab errors; navigation, disclosures, prior-week collapses, event/earnings accordions, sector tabs and toolbar onboarding checks passed.
- Geometry diagnostics remain consistent: desktop overview +3px and several panels +1px; 390px overview +7px and industry panel +5px; 320px overview −1px, news −1px and S&P earnings-health −1px. No compensating CSS was added. Production homepage, official master template, JSON and schedules remain untouched.
- Context-aware exact-rule audit found the identical open-state rule for the calendar and earnings accordions twice at top level. The earlier declaration remains; no matching selector appears between the two occurrences, so removing the later duplicate does not change the cascade.
- Removed one duplicate rule (143 characters) from `refactor-work/legacy-cascade.css`. No interaction, markup, data or scripts changed. CSS commit: 45dd12fdc5cf366719f6105dc5a859defa6f6248. Regression accepted: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40661199040 — success. Typography audits passed at desktop/mobile/narrow-mobile (27 instrument names and 54 quote values each); no horizontal overflow, duplicate IDs, new browser errors or tab errors. Existing geometry deltas unchanged; no compensating CSS. Production homepage, official master template, JSON and schedules remain untouched.

### Run #305 — remove duplicate toolbar hint strong color rule accepted (2026-10-28)
- Context-aware exact-rule audit found the same `.tac-tools-hint strong{color:#a92332!important}` rule twice within the same `@media(max-width:1099px)` context. The earlier rule is retained; no matching strong-element selector appears between occurrences.
- Removed the later duplicate declaration (47 characters) from `refactor-work/legacy-cascade.css`. No markup, script, data or interaction changes. CSS commit: cde9ba591483407d3f4e1cc4ba199ff96c06922f. Regression accepted: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40661543440 — success. Typography audits passed at desktop/mobile/narrow-mobile (27 instrument names and 54 quote values each); no horizontal overflow, duplicate IDs, new browser errors or tab errors. Existing geometry deltas unchanged; no compensating CSS. Production homepage, official master template, JSON and schedules remain untouched.

### CSS audit #306 — legacy cascade selector-usage audit; no safe removal selected (2026-10-28)
- Confirmed branch head is `6b8d10613d75530aa6f12f3b9661c89b90fb36f8`; Run #305 (`40661543440`) is `completed / success` on tested CSS commit `b4cb293956a7a5e0ba6bbc1acaa0c46596839d60`. Its artifact `12803937138` was downloaded and inspected: smoke summary confirms no horizontal overflow, missing panels, duplicate IDs, unmatched nav links or new browser errors at 1440/390/320px; instrument typography audit reports 27 names, 54 values and no failures per viewport.
- Inspected `legacy-cascade.css` for byte-identical selector/declaration blocks and cross-checked key candidates against the frozen source and regression script. A number of exact-looking blocks span different media-query contexts or old style-block boundaries (e.g. side-caption styles in separate drawer variants, toolbar arrow desktop/mobile visibility); these were not removed because the CSS context and runtime ownership do not establish safe equivalence. Repeated fragments inside nested media queries are not accepted as duplicate full rules without parsing the enclosing context.
- No CSS was changed and no browser workflow was triggered: this audit produced no candidate with sufficiently strong evidence of cascade equivalence. Existing diagnostics remain recorded, including desktop overview +3px, 390px overview +7px / industry panel +5px, and 320px overview −1px. No fixed-height or compensating CSS introduced.
- Production homepage, official mother templates, JSON data and schedules remain untouched.

### CSS audit #307 — cross-file selector/declaration collision review (2026-10-28)
- Re-read the current frozen HTML baseline, `legacy-cascade.css`, `design-system.css`, and browser smoke-test source on branch `tac-design-system-work-2026-10-24`.
- Static scan reviewed 913 legacy selector blocks and 212 design-system selector blocks. No exact selector-plus-declaration block was duplicated byte-for-byte across the two CSS files. Sixteen same-selector rule pairings do contain differing values, chiefly tab navigation sizing/spacing and the CNN Fear & Greed label grid; these are cascade/design-system overrides, not provable dead code, so they were retained.
- The baseline and smoke-test source were also checked for selector references. The broad static reference scan did not establish any safely removable legacy selector; because class fragments can be generated or referenced indirectly, absence of a simple textual match would not be sufficient evidence for deletion.
- No CSS or test code changed; no browser workflow was triggered because there was no CSS diff to validate. Next useful work is contextual audit of the remaining legacy blocks and geometry diagnostics, not broad deletion based on textual similarity.
- Known geometry deltas remain unchanged (desktop overview +3px; 390px overview +7px and industry panel +5px; 320px some panels −1px). No compensating CSS added. Production homepage, official mother templates, JSON data and schedules remain untouched.

### CSS cleanup #306 — remove duplicate Fed compact mobile declarations (2026-10-28; regression pending)
- In `legacy-cascade.css`, removed only two repeated declarations from the later `@media(max-width:560px)` block: `.fed-compact-preview .fc-probs-refined .fc-prob{padding:11px 10px}` and `.fed-compact-preview .fc-probs-refined .fc-prob strong{font-size:27px}`.
- Evidence: the same two selector/property declarations already exist in the earlier `@media(max-width:560px)` block (around lines 1188 and 1223 in the pre-edit file). Between them, the base declarations set larger values, but the earlier media-query declarations already override those values at widths <=560px; no intervening matching mobile declaration changes these two properties. The later media block still retains its unique current-rate declarations.
- CSS commit: `9e77f8d6dcf64d55ee1802ecbafa11663a0ab7d4` (136 characters removed). Browser regression trigger appended in `run-browser-tests.trigger` by commit `649833c9d6fbc36e7600b8904c082e18b75b459c`.
- **Not yet accepted:** a fresh desktop/mobile/narrow-mobile regression result has not been verified in this audit. Do not treat cleanup #306 as accepted until the workflow result and artifact are inspected. No geometry compensation added; production homepage, official mother templates, JSON data and schedules remain untouched.

### CSS audit #308 — same-file exact-rule duplicates and regression gate (2026-10-28)
- Parsed the current `legacy-cascade.css` into 1,142 selector rules and compared normalized selector + enclosing media context + declarations. Five exact duplicate rule signatures were identified:
  1. `.history-panel{padding:15px 14px!important}` in `@media(max-width:700px)` (around lines 700 and 719).
  2. `.history-panel>.title small{width:100%!important;margin-left:11px!important}` in `@media(max-width:700px)` (around lines 700 and 720).
  3. The compact FOMC grid's two-column template and 7px row/column gaps in `@media(max-width:560px)` (around lines 1301 and 1356); the later block also carries unique child-layout declarations.
  4. The 18px English sentiment-title size in `@media(max-width:390px)` (around lines 2221 and 2243).
  5. The 14px Chinese sentiment subtitle size in `@media(max-width:390px)` (around lines 1088 and 2248).
- These are **audit candidates, not approved deletions**. Before removing any declaration, re-check all intervening rules in source order and preserve unique declarations in combined media blocks. No CSS was changed in this audit.
- Run #306 remains unverified: the available GitHub connector returns no commit status checks for CSS commit `9e77f8d6dcf64d55ee1802ecbafa11663a0ab7d4` or its trigger/log commits, and the workflow-run wrapper only exposes pull-request-triggered runs. Do not infer that the browser regression started or passed from the marker-file commit alone.
- Production homepage, official mother templates, JSON data and schedules remain untouched. Existing geometry deltas remain unchanged; no fixed-height or whitespace compensation CSS was introduced.

### CSS audit #309 — contextual verification of history-panel mobile duplicates (2026-10-28)
- Rechecked the two repeated declarations from audit #308 against the full source-order context around legacy CSS lines 700–720. The first `@media(max-width:700px)` block sets `.history-panel{padding:15px 14px!important}` and `.history-panel>.title small{width:100%!important;margin-left:11px!important}`; the later mobile block repeats those exact values.
- Between the two media blocks, intervening rules do not change either property. The later block remains in place and also defines unique mobile layout/field/button styles. This supports removing only the earlier two declarations without changing the final cascade.
- **No CSS deletion made yet:** cleanup #306's regression is still unverified, so this candidate is queued rather than stacked on top of an unaccepted CSS change. Next gate remains obtaining an actual run result/artifact or a reproducible local browser regression.
- The available GitHub integration exposes specific run artifacts/jobs only when a run ID is already known; the current run-list wrapper only returns pull-request-triggered runs, and no workflow-dispatch action is exposed. This is a tooling limitation, not evidence that the run passed or failed.
- Production homepage, official mother templates, JSON data and schedules remain untouched.

### CSS audit #310 — sentiment-title duplicate candidates reviewed in cascade context (2026-10-28)
- Rechecked the narrow-mobile sentiment title rules in source order. The 18px English title declaration is repeated under `@media(max-width:390px)`, and the 14px Chinese subtitle declaration is repeated there as well. These are byte-identical declarations, but later V20 rules use more-specific `html body #sentiment...` selectors and set the Chinese subtitle to 12px (including a `max-width:700px` override); therefore the duplicate 14px rule is not the final computed value on mobile.
- This is a cascade warning: identical declarations in isolation do not prove a safe cleanup when later selectors override them. No deletion made.
- The compact FOMC grid's repeated two-column/7px-gap settings are also embedded in different specificity and layout blocks; the later block adds unique placement, padding, and rate-card rules. Keep the whole later block and do not remove a media-query segment by string matching alone.
- Workflow discovery attempt repeated against available GitHub code search and commit-run endpoints: searches for `workflow_dispatch`, `visual-smoke-test.mjs`, and `browser-results` returned no results on the searchable default branch; the known successful CSS commit and #306 CSS commit return no PR-triggered workflow runs via the available wrapper. This does not prove no workflow ran; it means the available connector cannot retrieve a run ID through these endpoints.
- Regression gate remains open for cleanup #306. No new CSS edits, no browser pass claim, and no changes to production homepage, official mother templates, JSON data or schedules.

### CSS verification #311 — inspect retained Run #305 artifact and attempt local reproduction (2026-10-28)
- Inspected the available artifact ZIP from successful Run #305 (`40661543440`, artifact `12803937138`). Its summary confirms the earlier baseline build passed the listed structural checks at 1440px, 390px, and 320px: no horizontal overflow, missing panels, duplicate IDs, unmatched navigation anchors, or browser errors. This artifact predates cleanup #306 and is **not** evidence that #306 itself passed.
- The artifact's embedded candidate CSS contains the same compact FedWatch mobile declarations in the earlier and later `@media(max-width:560px)` blocks. The later block also contains unique `.fc-current-rate` declarations, which were retained by #306. Static review continues to support the deletion as cascade-equivalent.
- Attempted a local Playwright before/after reproduction using the artifact's candidate HTML and a copy with only the two duplicate declarations removed. The browser harness blocked both `file://` and local HTTP navigation with `ERR_BLOCKED_BY_ADMINISTRATOR`, so the local browser comparison could not execute. No visual/browser pass is claimed from this attempt.
- Current conclusion: #306 has strong static equivalence evidence but remains **regression-unverified**. The available connector still cannot retrieve a non-PR workflow run ID or trigger a run. Do not stack another CSS edit until a real regression result is available.
- No CSS, production homepage, official mother templates, JSON data, or schedules changed in this verification step.

### CSS verification #312 — exact before/after diff and Run #305 log inspection (2026-10-28)
- Compared `legacy-cascade.css` at pre-cleanup SHA `b4cb293956a7a5e0ba6bbc1acaa0c46596839d60` with cleanup SHA `9e77f8d6dcf64d55ee1802ecbafa11663a0ab7d4`. The file remains 2,752 lines. The only textual difference is the `@media(max-width:560px)` rule: the two `.fc-probs-refined .fc-prob` declarations are removed while both `.fc-current-rate` declarations are preserved. No other CSS lines differ between these two revisions.
- Retrieved the actual Run #305 job (`browser-smoke-test`, job `122725511602`) and inspected its logs. The job checked out exactly SHA `b4cb293956a7a5e0ba6bbc1acaa0c46596839d60`; it completed successfully and logged typography passes for desktop, mobile and narrow-mobile (27 names and 54 quote values per viewport), alongside structural/navigation checks. This is valid evidence for the pre-cleanup baseline only, not for #306.
- The workflow is a hosted GitHub Actions Playwright job, but the available connector's run-list endpoint filters to pull-request-triggered runs; it returns no run for #306. The marker commit alone cannot establish that a job started. No authorized action is exposed here to dispatch this workflow without a known run ID.
- #306 static-diff confidence is high: exact scope is limited to the two duplicate declarations; runtime regression remains **not verified**. No CSS edits were made in this step; production homepage, official mother templates, JSON data and schedules remain untouched.

### CSS verification #313 — regression workflow trigger investigation (2026-10-28)
- Rechecked combined commit status and commit-associated workflow runs for both CSS commit `9e77f8d6dcf64d55ee1802ecbafa11663a0ab7d4` and trigger-marker commit `649833c9d6fbc36e7600b8904c082e18b75b459c`. Both status responses contain no checks, and the available workflow-run wrapper returns no runs for either SHA.
- Attempted to resolve the workflow definition by fetching plausible workflow filenames from `.github/workflows/` on the refactor branch; all guesses returned 404. The available GitHub tools do not expose repository tree/directory listing or an all-runs-by-branch endpoint, so the exact workflow file and #306 run cannot be identified through the current integration.
- This is an access/discovery limitation, not a pass/fail result. No PR was opened and no new workflow/production configuration was created merely to force a test. #306 remains regression-unverified; exact CSS diff scope and baseline Run #305 evidence remain recorded above.
- No CSS, production homepage, official mother templates, JSON data, or schedules changed.

### CSS verification #314 — normalize the #306 trigger marker format (2026-10-28)
- Found a concrete discrepancy in `refactor-work/run-browser-tests.trigger`: historical trigger entries #302–#305 include full ISO-8601 UTC timestamps, but the original #306 entry contained only the date. Replaced that entry with `2026-10-28T12:57:40.783Z` while retaining the exact target CSS commit SHA.
- Trigger-marker correction commit: `d0d605b2ab3c323b06dd1264b7bc0f497857843a`. This is a reasonable trigger-format correction, but the available commit-run endpoint still returns no run and no status checks; because that endpoint filters to PR-triggered runs, this response does not establish whether the push-triggered job has started. Do not claim the trigger succeeded until a real run ID/artifact is visible.
- CSS was not modified. #306 remains regression-unverified pending observable workflow output. Production homepage, official mother templates, JSON data and schedules remain untouched.

### CSS verification #315 — confirm test-runner prerequisites and workflow discovery (2026-10-28)
- Inspected `refactor-work/visual-smoke-test.mjs`: it expects `refactor-work/candidate-build.html` and `refactor-work/source-baseline-2026-10-26.html`, then writes reports under `refactor-work/browser-results/`.
- On branch `tac-design-system-work-2026-10-24`, `source-baseline-2026-10-26.html`, `design-system.css`, and the audit files exist, but `refactor-work/candidate-build.html` does not. This means a raw local invocation of the committed script would lack its candidate input unless an external workflow creates it first.
- Inspected discoverable workflows on the branch: `.github/workflows/pages.yml` only deploys `main`; `.github/workflows/main.yml` updates market-volatility data on schedule/manual dispatch. Neither is the CSS browser regression workflow. Guessed dedicated workflow paths and commit search did not locate a test workflow definition. No repository-tree or all-runs-by-branch endpoint is available in the current GitHub tool integration.
- Conclusion: the marker-file push cannot be treated as proof that a regression ran; both the workflow definition/run record and the generated candidate input need to be identified. #306 remains unverified. No CSS or production files changed.

### CSS verification #316 — replay the proven #305 trigger convention (2026-10-28)
- Recovered the complete successful Run #305 job log (`40661543440`, job `122725511602`) and confirmed the runner sequence: checkout pinned refactor commit → install Node 20/Playwright → `python refactor-work/build-candidate.py refactor-work/candidate-build.html` → `node refactor-work/visual-smoke-test.mjs`, `instrument-typography-audit.mjs`, `panel-child-geometry-diagnostic.mjs` → upload artifact `tac-refactor-browser-results`.
- The #305 log confirms `candidate-build.html` is intentionally generated at runtime; its absence from committed branch files is expected, not itself a defect.
- Replayed the exact known trigger commit-message convention by committing the #306 marker with message `test(refactor): run browser regression 306`; commit `a05f79d5f9ef5d66939c44460619059ca48efaac`.
- Immediate checks through the available integration still returned no associated run/status. Since `fetch_commit_workflow_runs` only exposes PR-triggered runs, that empty response cannot verify push-triggered workflow execution. Awaiting a real run ID/artifact remains the only valid acceptance gate. CSS unchanged; no production files changed.

### CSS verification #317 — narrow static cascade equivalence review (2026-10-28)
- Compared the pre-cleanup CSS at Run #305 commit `b4cb293956a7a5e0ba6bbc1acaa0c46596839d60` against the cleanup commit `9e77f8d6dcf64d55ee1802ecbafa11663a0ab7d4`. The CSS patch is limited to removing two declarations from the later `@media(max-width:560px)` rule: `.fc-probs-refined .fc-prob{padding:11px 10px}` and `.fc-probs-refined .fc-prob strong{font-size:27px}`.
- Confirmed both exact declarations already occur in an earlier `@media(max-width:560px)` rule at line 1188 and are repeated in the later rule at line 1223 before cleanup. The later rule retains its unique `.fc-current-rate` declarations. Thus static source comparison supports this as duplicate-only removal under the same media condition, but it is not a substitute for browser regression evidence.
- Rechecked the retrigger commit `a05f79d5f9ef5d66939c44460619059ca48efaac`; current integration still exposes no associated run or status checks. #306 remains unverified. No further CSS changes made; protected production files remain untouched.

### CSS verification #318 — restore mobile FedWatch overrides after cascade-order review (2026-10-28)
- Corrected a flaw in the prior static review: the two declarations removed in #306 are textually repeated in an earlier mobile media block, but that earlier block occurs before later base FedWatch styles in Original style block 36. Those later base declarations reset card padding to `14px 15px` and the probability number to `32px`; therefore the later `@media(max-width:560px)` overrides are not behaviorally redundant.
- Restored `.fc-probs-refined .fc-prob{padding:11px 10px}` and `.fc-probs-refined .fc-prob strong{font-size:27px}` to the later mobile media rule. Correction commit: `6efd715b1fb2c7844c40d16116b856f1a4b7436f`.
- This is a safety correction to return intended narrow-mobile styling while regression evidence is unavailable. It is not a claim that the restored CSS has passed browser tests. Protected homepage, official mother templates, JSON data and schedules remain untouched.

### Browser regression #318 — completed successfully (2026-10-28)
- Workflow run: `40693103038` (run #309), commit `202dd4c0f3e44c86b491b14ff248301237c9d8aa`; result `success`.
- Job `browser-smoke-test`: all steps succeeded, including self-contained candidate build, desktop/mobile smoke tests, typography audit, panel-child geometry diagnostic, and artifact upload.
- Verified at 1440px, 390px and 320px: horizontal overflow false; missing panel IDs none; duplicate IDs none; unmatched nav links 0; new browser errors 0; navigation-anchor geometry passed; global-market and industry names use matching 16px typography. Source disclosures and calendar/earnings/sector interactions passed.
- Panel height differences versus frozen baseline were small: desktop overview +3px, mobile overview +7px and industry/bonds/FX/commodities +5px, narrow-mobile overview -1px. Pixel-diff ratio was 7.64% at 390px and 10.50% at 320px; these are recorded differences, not zero-pixel parity. Desktop full-page dimensions differed by 3px vertically.
- Artifact `tac-refactor-browser-results` ID `12817544420` (7.3 MB): https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40693103038/artifacts/12817544420
- This validates the current refactor candidate's smoke checks, not pixel-perfect parity and not a separate isolated A/B assertion specifically for the two FedWatch declarations. Do not merge to production or treat visual sign-off as complete solely from this run.

### Focused FedWatch style assertion #319 — passed (2026-10-28)
- Workflow run `40694139670` completed with `success`; artifact `12818073167` was downloaded and `browser-results/results.json` inspected.
- FedWatch computed-style assertions passed at all tested widths: desktop 1440px computed card padding `14px 15px`, probability number `32px`; mobile 390px and narrow mobile 320px computed padding `11px 10px`, probability number `27px`.
- Overall smoke test returned `errors: []`; new browser errors 0; horizontal overflow false; missing/duplicate panel IDs none; unmatched nav links 0; all specified tab and disclosure interactions passed.
- Existing baseline/candidate pixel diffs remain non-zero (390px ≈7.64%; 320px ≈10.50%) and some panel heights differ by a few pixels. This successful run validates the FedWatch computed styles and listed smoke assertions; it does not certify pixel-perfect visual parity or production readiness.
- Test commit: `009af5357976cc5b505e64d8f8e1d6aae6ecc045`; run trigger commit: `5b53966e647206731eda3afaada9a450a46f2380`; workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40694139670
- Artifact: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40694139670/artifacts/12818073167


### Mobile industry-tab geometry follow-up #321–#322 — latest run passed smoke assertions (2026-10-28)
- Run #321 (40695760564) failed the shared main-tab style-signature assertion at 390px after the first label-height override; this was a real regression and was not marked complete.
- Corrected the 381–700px rule so the industry tab labels use the same 38px/8px 7px style contract as other mobile main tabs, and kept a narrow-phone first-label exception. Run #322 (40696211913) completed with conclusion success: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40696211913
- Verified in artifact 12819866378: errors=[], new browser errors 0, no horizontal overflow, no missing/duplicate panel IDs, no unmatched nav links, navigation-anchor checks pass, and tab/disclosure interactions pass at 1440px, 390px, and 320px. At 390px, main-tab style signatures are unified (12px / 38px / 8px 7px / 10px / normal). At 320px, the existing narrow-screen main-tab signature rule passes.
- Historical status at Run #322 only: nav height was 93px at 390px and 88px at 320px. This was superseded by Run #320, which restored the container to 89px at both mobile widths; Run #321 then added the box-model diagnostics and explained the selected-label rectangle difference as the frozen baseline's 1.045 transform. Do not treat the historical #322 measurements or its proposed next step as current status.
- Overall visual migration remains not pixel-perfect: desktop full-page height is +3px, and pixel-diff ratios remain about 7.64% at 390px and 10.50% at 320px. Do not merge to production or mark the full design migration visually signed off solely from these smoke runs. Official homepage and dual mother templates remain untouched.


### Mobile industry-tab geometry follow-up #320 — baseline nav height restored (2026-10-28)
- Workflow #320 (`40700480394`) completed successfully: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40700480394
- Artifact `12820953702` was downloaded and inspected. At 390px and 320px, industry tab navigation height is now 89px, matching the frozen baseline; horizontal overflow is false, browser errors are 0, navigation-anchor checks pass, and no required panel/ID/link issues were reported.
- Industry panel height now matches baseline at all measured widths: desktop 380px, 390px 448px, and 320px 502px. Shared mobile main-tab computed-style signatures pass.
- Remaining geometry nuance (clarified by run #321): at 390px the candidate label rectangles measure 38px each while the baseline's first selected label renders at 40px because of its 1.045 scale transform. Row starts are the same relative to the nav container at both 390px and 320px; the 2px absolute document-top offset at 390px is caused by the nav container being 2px lower in page flow, not a different row gap. At 320px the first selected label likewise differs only because the baseline scales it. Do not claim pixel-perfect parity or production visual sign-off.
- CSS commit: `38d5e330b779969a1aba5fafafe001e024fa5ac3`; test trigger commit: `9586e8bd0cd92eafa8cbedf90d618aa3b5488cc8`.
- Next: inspect the baseline/candidate label box-model and selected-state transform at 390px before any additional override; preserve the shared mobile style signature and avoid restoring the prior first-label min-height override that failed the shared signature.


### Mobile industry-tab box-model diagnosis #321 — difference explained (2026-10-28)
- Workflow #321 (`40701497360`) completed successfully: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40701497360; artifact `12821498384` inspected.
- `results.json` reports `errors: []`, no horizontal overflow at 1440px/390px/320px, mobile main-tab style-signature checks pass, industry panel height matches baseline (380px desktop, 448px at 390px, 502px at 320px), and the industry nav container measures 89px at both mobile widths.
- New label box diagnostics explain the apparent 40px-vs-38px discrepancy: at 390px and 320px the frozen baseline's first selected label has an untransformed layout/offset height of 38px but a rendered bounding-box height of 40px due to `transform: matrix(1.045, 0, 0, 1.045, 0, 0)`. The design-system candidate intentionally normalizes selected tabs to `transform: none`, so its rendered box remains 38px. The grid row start positions relative to the nav container match; the 2px absolute document-top difference at 390px comes from the nav container itself being 2px lower in the page flow, not a different row gap.
- Do not add a one-off transform or first-label height override just to imitate the legacy selected-state enlargement: that would reintroduce inconsistent selected-tab geometry and risks the shared style signature. Keep the shared design-system state unless a deliberate product-level decision requests legacy scale behavior.
- This closes the specific mobile label-box diagnostic. Overall visual migration remains not pixel-perfect (the existing full-page diff ratios and unrelated small panel deltas remain documented above); this is not production sign-off.


### Sentiment card geometry audit #325 — baseline/candidate selectors now aligned (2026-10-28)
- Workflow #325 (`40704305258`) completed successfully: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40704305258; artifact `12821919850` inspected.
- Corrected the geometry audit so both baseline and candidate include the `sentiment` root and the same descendant selector set. This closes the previous test-coverage gap; prior runs #322–#324 did not provide a complete baseline/candidate comparison for this panel and must not be used as evidence of sentiment geometry parity.
- Results report `errors: []`. Measured sentiment inner-grid (`.sent`) heights: desktop 487px baseline / 488px candidate (+1px); 390px 598px / 600px (+2px); 320px 676px / 678px (+2px). Sentiment panel heading remains 26px tall, with candidate left padding normalized from legacy 15px to the canonical 12px.
- Child deltas: the two top `.sbox` cards retain the same heights (147px desktop; 136px at both mobile widths). The CNN Fear & Greed card is +2px in candidate (216 vs 214px desktop; 206 vs 204px at 390px; 216 vs 214px at 320px). Source disclosure rows changed from 21px to 23px, shifting following content by about 2px. The final lower sentiment card remains 106px desktop and 240px/308px mobile.
- Overall visual diff is still not pixel-perfect: desktop full-page height 5150px vs 5147px baseline (+3px); pixel-diff ratios 7.64% at 390px and 10.50% at 320px. No horizontal overflow/error failures reported in this run. This is a focused geometry finding, not production sign-off.
- Next: inspect computed styles of the sentiment source disclosure summaries to identify whether the 2px row/card increase is an intentional canonical component change or an unintended line-height/padding delta. Do not alter CSS until that cause is established. Formal homepage and approved dual mother templates remain untouched.

## Run #326 — 2026-10-28 市場情緒 disclosure box-model audit

- Workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40721324761
- Result: **completed / success**; artifact `12830372751` downloaded and inspected locally (`summary.md`, `panel-child-geometry-diagnostic.json`, screenshots and typography audit).
- 1440px: sentiment panel 583px → 584px (+1px); sentiment grid 487px → 488px (+1px). Main panel child title uses baseline left padding 15px versus candidate 12px; title top differs by 1px. No horizontal overflow, missing panels, duplicate IDs, unmatched nav targets or new browser errors.
- 390px: sentiment panel height 685px in both versions; no overall panel-height delta.
- 320px: sentiment panel 763px in both versions; the grid height is 676px baseline vs 678px candidate (+2px), while the CNN card/source row must be compared at the individual computed-style level before attributing the difference to padding or line-height.
- Other acceptance metrics remain green: global market and industry item labels both 16px, five-star red count 16, all 11 representative tab cases pass, source disclosure and calendar/earnings disclosure interactions pass, no new browser errors.
- Interpretation: workflow success confirms test execution only. It does not close the visual audit. Do not add fixed-height compensation. Next inspect the exact computed styles and matched CSS rules for the CNN sentiment card and its source disclosure at 320px, then make only a cause-based adjustment if a non-intentional delta is proven.
- Scope protection unchanged: only isolated branch `tac-design-system-work-2026-10-24`; official homepage, approved dual mother templates, JSON data and schedules untouched.

## Run #327 — Sentiment dark disclosure summary geometry fix (2026-10-29 Taiwan time)

- CSS commit: `bdef33d043efcbd3ddd97f33c901fec8ca03ffc1`; verification workflow: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40728519887
- Root cause found by cascade inspection: the shared `.tac-ds-disclosure--source > summary` rule declares `min-height: 21px !important`, `padding: 2px 10px !important`, and `line-height: 1.35 !important`. The sentiment-specific `.tac-ds-disclosure--dark > summary` declarations had no `!important`, so their intended geometry was overridden in the cascade.
- Applied a narrowly scoped dark-sentiment override for summary `min-height: 0 !important`, `padding: 2px 0 !important`, and `line-height: normal !important`. This keeps light-surface source disclosure rows under the shared source component contract and changes only dark sentiment disclosures.
- Workflow #327 completed with **success**; artifact `12833507497` was downloaded and `browser-results/summary.md` plus `results.json` inspected. Candidate build, desktop/mobile smoke tests and artifact upload all completed successfully.
- Confirmed at 1440px, 390px and 320px: all three sentiment source summary rows now render at 19px visible summary height / 21px enclosing `details` height, with `padding: 2px 0` and `line-height: normal`; the prior 23px disclosure row is corrected. No new browser errors, no horizontal overflow, no missing panel IDs, no duplicate IDs, no unmatched nav links; navigation-anchor and source/calendar/earnings/sector interactions pass.
- Sentiment panel geometry after correction: 1440px 583px baseline → 580px candidate (-3px); 390px 685px → 681px (-4px); 320px 763px → 759px (-4px). The correction removes the unintended disclosure-row excess; remaining panel deltas must be reviewed against inner card/grid geometry rather than compensated with fixed heights.
- Other acceptance checks remain green: global-market and industry item labels both 16px, five-star red count 16, fear/greed score and marker agree, all 11 tab cases pass, and `results.json` reports `errors: []`. Mobile full-page pixel differences remain non-zero (390px 7.64%; 320px 10.50%), and desktop full-page dimensions are 5147px baseline / 5146px candidate; therefore this is not pixel-perfect parity or production sign-off.
- Artifact: https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/40728519887/artifacts/12833507497 (7-day retention).
- Run #328 completed with **success**; artifact `12833443817` was downloaded and `summary.md`, `results.json`, and `panel-child-geometry-diagnostic.json` were inspected. The explicit summary height correction worked: all three viewports report candidate `summary` height 21px with `padding: 2px 0`; this matches the frozen baseline. The regression suite reports no browser errors, no horizontal overflow, no missing/duplicate panel IDs, no unmatched nav links, and the tab/disclosure interactions pass.
- However, the same artifact revealed the enclosing dark `details` shell still measures 23px versus the baseline's 21px. CSS inspection identified the remaining cause: the generic `.tac-ds-disclosure` adds a 1px border on both edges, while the legacy sentiment source disclosure was borderless. That also leaves the CNN Fear & Greed card 2px taller than baseline (desktop 216 vs 214px; 390px 206 vs 204px; 320px 216 vs 214px). Therefore #328 is a partial pass, not full geometry parity.
- Follow-up CSS commit `01e75ff94eb0f28dbf61005751e05d48ab6b8f74` removed the inherited border only from `.tac-ds-disclosure--dark`; it preserves the 21px summary and zero horizontal padding. Run #329 completed with **success**; artifact `12834817997` was inspected. At 1440px, 390px and 320px, all three candidate dark source `details` rows and summaries now match baseline at 21px, border widths are 0px, and the CNN Fear & Greed card matches baseline at 214px, 204px and 214px respectively. Browser errors 0, horizontal overflow false, panel IDs and navigation checks pass, and the existing tab/disclosure interactions remain passing.
- Remaining panel-level geometry difference after the inner rows were corrected: sentiment panel is 580px vs 583px baseline at 1440px (-3px), 681px vs 685px at 390px (-4px), and 759px vs 763px at 320px (-4px). Detailed child geometry identified another concrete cause: the first two candidate source rows have `margin-top: 2px`, while the frozen baseline uses `5px`, shifting the CNN card and lower card upward by 3px. CSS commit `1bc8ca6189943787c456cf729e691995fa221d9c` restores the 5px margin only for dark sentiment disclosures. It was committed after Run #330 had checked out its code, so #330 validates the new assertion against the border-only CSS; a follow-up run will validate this spacing correction. No fixed-height compensation is being used.
- Run #330 completed with **success**; artifact `12834779493` was downloaded and inspected. The newly added `sentimentDisclosureGeometryPass` assertion passed at 1440px, 390px, and 320px: each of the three source disclosure rows and its summary is 21px, top/bottom border widths are 0px, and CNN card heights exactly match baseline (214px / 204px / 214px). `results.json` has `errors: []`; no browser errors, horizontal overflow, missing/duplicate panel IDs or unmatched navigation links. Run #330 tests the border correction; the follow-up 5px margin correction and margin-top assertion are reserved for Run #331.
- Added a focused regression assertion in `refactor-work/visual-smoke-test.mjs` (commit `b8052029d64bd4f966c2f227ff8c46c9bdfbfaf3`, subsequently extended in `d026a93017e3c7191b3a7b4f3b8e55de8b19a8f8`) that compares all three source `details` boxes, summaries, borders, padding and margins plus the CNN card against the frozen baseline at every viewport.
- Run #331 completed with **success**; artifact `12835147928` was downloaded and inspected. The strict geometry assertion passed at all widths. Every source row is now exactly 21px high, margin-top matches baseline (5px on the top two rows, 13px on the CNN row), border widths are 0px, and CNN card height matches baseline (214px desktop, 204px at 390px, 214px at 320px). `results.json` has `errors: []`; browser errors 0, horizontal overflow false, no missing/duplicate panel IDs or unmatched nav links, and the full tab/disclosure regression suite passes.
- Sentiment panel height is now exactly baseline at desktop (583px); residual is only -1px at 390px (684 vs 685px) and -1px at 320px (762 vs 763px). Other major panels are within ±2px: overview +2px desktop / +1px mobile / -2px narrow mobile; news scan +1px desktop/mobile / -1px narrow mobile; S&P earnings-health +1px desktop / 0px mobile / -1px narrow mobile; Fed and view are within 0–1px. These small deltas remain documented, and the overall full-page pixel diff is still non-zero; no production sign-off is implied.
- Formal homepage, approved dual mother templates, JSON data, and schedules remain untouched.


### Next geometry gate — visible news cards
- Run #331 closes the sentiment source-row issue with a strict baseline comparison. The next known residual is the news scan: visible card heights differ by at most 1px at the three viewports, while the 320px variant intentionally uses a 1px-smaller padding step to preserve its narrow text width and keep total panel geometry within 1px of baseline.
- Added a focused `newsCardGeometryPass` assertion to `refactor-work/visual-smoke-test.mjs` (commit `74d4f9689e6f4304137b35568f155969bf590d15`). It compares visible card counts and widths exactly and permits at most ±1px card-height delta against the frozen baseline, failing on larger wrapping/spacing regressions. Next run will validate this assertion without changing news content or CSS.


### Next component audit — S&P 500 narrow-mobile compact source row
- The Run #331 artifact's panel-child geometry showed the S&P 500 earnings-health panel at 320px has a 1px title-height excess (candidate 27px vs baseline 26px) and a 2px method-summary shortfall (candidate 15px vs baseline 17px). The cause is scoped responsive CSS: the narrow-mobile title did not inherit the `line-height:1.25` parity used at wider widths, and the method summary's narrow override reset `min-height` to 0.
- Applied a cause-based fix in `refactor-work/design-system.css` commit `b594c90b4df7a14872bb7a3de5fff4df07cc36c3`: set the narrow title line-height to 1.25 and restore the compact summary's 17px minimum. Added `sp500TitleSourceGeometryPass` to `visual-smoke-test.mjs` commit `d9fe66761d1d0cffcb54cac5eb2e3f858e661216`, comparing baseline/candidate title and source-summary heights at all three viewports. This fix is pending browser verification; no fixed panel height was added.


### Run #332 — news-card geometry gate exposed test-state mismatch (not a CSS verdict)
- Run #332 (`40733234585`) failed after the new news-card assertion compared different selected tabs: the interaction suite had deliberately switched the candidate to the second news tab, while the baseline page remained on its initial tab. This produced 5 baseline cards versus 10 candidate cards (and non-comparable heights), so the assertion was invalid; it does not establish a CSS regression. Artifact `12836606757` was inspected and the failure source confirmed.
- Corrected `visual-smoke-test.mjs` in commit `9bd05ffce418d1b668167a33f0dc4201446382e2` to reset both pages to `#tac-news-0` before measuring visible cards. Run #333 (`40733602397`) completed with **success**; artifact `12836581567` was inspected. The news-card assertion now passes at all widths with five comparable visible cards on each page: height deltas are `[0,0,0,0,1]` at desktop, `[0,0,0,0,1]` at 390px, and `[0,-1,-1,-1,0]` at 320px; card widths match exactly. This confirms only the documented 1px responsive differences remain.
- The S&P 500 narrow-mobile title/source-row fix also passed in Run #333: title and method-summary heights match baseline at 1440px, 390px and 320px (320px title 26px and source summary 17px). `results.json` has `errors: []`; sentiment disclosure geometry passes; browser errors 0, horizontal overflow false, no missing/duplicate panel IDs or unmatched nav links; existing tabs and disclosures pass.
- Current panel deltas: desktop sentiment 0px, news +1px, S&P earnings-health +1px, Fed +1px, View +1px, overall document +2px; 390px sentiment -1px and news +1px, all other panels 0px; 320px sentiment -1px, news -1px, other panels 0px. Full-page mobile pixel diffs remain non-zero (390px ~7.64%, 320px ~10.50%) because the migration changes card surfaces and the sentiment theme; no production sign-off is implied.


### Next audit — cross-panel source disclosure geometry inventory
- The sentiment and S&P compact source-row geometry gates are passing, and visible news cards remain within the documented ±1px tolerance. Next, `visual-smoke-test.mjs` now records the height, summary height, top margin, padding, border widths, and summary typography for every `details.source-details` across all panels in the initial baseline/candidate state. This is diagnostic-only; it does not impose parity where a component variant intentionally differs.
- Test update commit `98e556457f7e853b07cf46cc7f94f9cb72d6de18`. Run #334 completed with **success**; artifact `12835434396` was inspected at 1440px, 390px and 320px. The inventory found 11 source disclosures per viewport. The sentiment and S&P focused gates pass. The remaining concrete geometry mismatch is the asset-panel source row (candidate 23px vs baseline 21px) and nested asset source summaries inheriting 2px horizontal padding and 2px top margin; these are addressed in the pending #335 fix below. No production files or data changed.


### S&P 500 source disclosure marker follow-up (pending Run #335)
- Visual review of the 320px candidate screenshot showed the compact S&P 500 method/source row still lacked the `▸` triangle present in the frozen baseline. The scoped compact-summary CSS had been suppressing `summary::before`, despite the shared source-disclosure rule explicitly providing a triangle.
- Removed only the two S&P-specific `content:none`/`display:none` pseudo-element overrides in `design-system.css` commit `5e33eb102a32c78d334263281e938c892ae1dcae`, allowing the shared triangle to appear. Extended the S&P geometry assertion in `visual-smoke-test.mjs` commit `f8a46babe1083bd50aef6a5dacfddb587ee3a213` to verify marker content/display matches the baseline and includes `▸`. Run #334 had already checked out its source, so these changes will be validated by Run #335 after the current diagnostic run completes.


### Asset source-disclosure geometry follow-up (pending Run #335)
- Run #334's cross-panel inventory identified a second source-row mismatch outside the sentiment panel: the visible asset/bonds/FX source disclosure measured 23px in the candidate versus 21px in baseline because it inherited the generic 1px border on each edge and 2px top margin; nested sector-source disclosures also inherited `2px 10px` summary padding where baseline used `0px`.
- Added narrowly scoped corrections in `design-system.css` commit `b86e74cd290b987a2563b8e841c76a0efb0ab9e0`: borderless, zero top margin for asset-panel source rows and zero summary padding for those rows. Added `assetSourceDisclosureGeometryPass` to `visual-smoke-test.mjs` commit `b884775478b7a29a7cf549f5215716dbec4561b3`, comparing all five asset source rows to baseline for visibility, height, summary height, margin, padding and border widths. These changes await Run #335 verification; no panel fixed heights or content changes.


### Run #335 — two assertion-scope corrections required (CSS geometry findings retained)
- Run #335 (`40734545917`) failed two new gates; artifact `12835389673` was inspected. The asset-panel border/margin fix itself worked: all five asset source disclosures now have baseline-matching heights, zero borders and zero top margin. The remaining asset gate failure was caused by an over-broad summary-padding selector: the visible `.sector-source` row intentionally uses baseline `2px 0`, while the other four rows use `0px`; the candidate had forced all five to `0px`.
- Corrected the CSS selector in commit `746fcd2aa1d731201f41a3e6737eb84899b556cf` to apply zero summary padding only to asset source rows that are **not** `.sector-source`, preserving the visible sector row's `2px 0` padding.
- The S&P source marker itself is present in the candidate after removing the two `content:none` overrides, but the new test incorrectly required the pseudo-element's `display` mode to match (`block` baseline vs `inline` candidate). That display-mode difference does not remove the triangle; the gate now compares the actual marker content and requires `▸`, without coupling to an irrelevant display value (test commit `c4e38abadb5feda1f8183f105f2afc12641a4e56`).
- Run #336 completed with **success**; artifact `12835992954` was inspected. All four focused gates pass at 1440px, 390px and 320px: sentiment disclosure geometry, news-card tolerance, S&P title/source geometry including the `▸` marker, and all five asset source rows. `results.json` has `errors: []`; no new browser errors, horizontal overflow, missing/duplicate panel IDs or unmatched nav links; tabs and disclosures pass. The asset row now matches baseline at 21px with `2px 0` summary padding, while the four nested/inactive rows retain `0px` padding.
- Cross-panel source-disclosure audit now shows no remaining geometry deltas in the asset source rows; the remaining computed font-size/line-height differences (baseline 12px/16.8px vs candidate 11px/14.85px on light source labels) are the intentional canonical text-size normalization. The S&P method summary is 17px and its triangle is present at all three widths.