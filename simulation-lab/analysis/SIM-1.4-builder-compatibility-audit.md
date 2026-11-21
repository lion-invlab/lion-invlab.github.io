# SIM-1.4｜HTML Builder 相容性稽核

日期：2026-11-21  
範圍：僅 simulation branch  
對象：simulation-lab/runner/build_review_html.py  
檔案 SHA：04d5976e38ab0da24e19bbe4607da8f1c20e1d35  
母版基準：Manifest 正式 SHA monday a568e594e55909041d51d8eae7e6fe5f7986c096／weekdays 3785405e331b10ec6189002e480be2a1edbe20ef；simulation baseline SHA monday 1ac39d50b138e59f4aabf55fc68560ee277ba6f8／weekdays f010ff118d7a5a2c1f6e834aa24f832766383c2b。

## 結論

**狀態：BLOCKED，不得核定為 SIM-1.4 唯一 Builder。**

本次完成全檔靜態檢查（2,703 行、176,746 字元）。已檢查 Workflow 執行定義及近期 run；尚未執行新的成功 Python build、未產生新 HTML、未完成 Playwright／視覺回歸。因此本報告不是 Builder 相容性通過證明。

## 已確認的實作行為與相容性問題

| 程式位置（約略行號） | 實際行為 | 對母版零退化契約的影響 | 判定 |
|---|---|---|---|
| 701–717 | BeautifulSoup 解析母版、移除舊 provenance comment、追加 TAC_CALENDAR_SOURCE comment；另在 head 追加 summary heading CSS | 新增 style／comment，非純內容槽位更新；若 DOM/CSS 數量需與母版完全一致即不相容 | BLOCK |
| 708–714 | 新增 style id=tac-summary-heading-size-alignment | 改動母版 CSS 節點數及 cascade | BLOCK |
| 718–826 | 對週一上週收折區追加 disclosure CSS，並改寫 summary 子節點，新增 marker／label span | 變更既有 details/summary DOM、樣式及互動呈現；違反不得重建／改造母版控制的原則 | BLOCK |
| 779–826 | 新增 tac-simulation-layout-authority-v1 CSS，並 append 至 body | 新增 CSS 到 body，直接改變母版原有樣式基線 | BLOCK |
| 828–883 | 修改 Fed 標題，清空 .fc-fomc-weekly-events，再依行事曆資料重建整個官員行程區塊 | 不是替換既有內容槽位，而是重建區塊內容；須證明目標節點及子結構為允許更新槽位，並比對原母版 | BLOCK |
| 892–931 | 新增／替換 energy mobile CSS | 修改既有 CSS cascade；即使為修復顯示，也必須先有核准的母版／技術契約授權 | BLOCK |
| 963–989 起 | 動態建立專題焦點 feature、metrics 等 DOM，並寫入 inline styles | 新增頁面元件與樣式，不屬於純內容填值；必須證明專題區塊是已核准的可選槽位 | BLOCK |
| 多處 set_text／field.clear | 先清空節點，再重新 append 子節點 | 可能刪除節點內原有 icon、class 子節點、連結或語意標籤；需逐 selector 列出允許清空範圍及保留結構測試 | BLOCK |
| 656–688 | 行情 fail-closed 只檢查 source name／URL／data_date；缺少時標待核實 | **沒有檢查 quote_type，也沒有拒絕 cfd_index_reference_series**；來源完整的 CFD 序列會被當成可渲染行情，違反 SIM-1.3 0.9 | BLOCK |

## CLI、Workflow 與實際測試狀態

- CLI 必要參數：--data、--output、--expected-master-sha；選用參數：--key-levels-live、--price-reactions、--earnings-consensus-projection。
- 程式依 simulation Manifest 選定 Monday／weekdays simulation baseline，驗證實際 Git blob SHA 同時等於 Manifest simulation_blob_sha 與 CLI expected SHA，並拒絕週末日期。
- Workflow .github/workflows/tac-simulation-lab.yml 有 build／qa-only 兩種 dispatch 模式；build 依 fixture 日期選版、擷取 earnings price reactions、呼叫本 Builder，接續執行 interaction_smoke.mjs、visual_regression.mjs、validate_review_artifact.py、44 indicators／新聞數量驗收、QA evidence 封存及 simulation branch 回讀 SHA。
- 最近一次已完成的 deterministic self-test run 44895586059 於 test_1123_fixture.py 失敗；其餘先前測試（calendar source guard、dual mothers、Fear & Greed、summary headline、earnings judgement/schema、report-layer status／calendar overrides 等）均已通過至該失敗點。失敗原因不是 Builder 本身，而是 fixture 與 test 的截稿欄位契約不一致：fixture 的 report_cutoff_taipei 與 news_cutoff_taipei 均為 2026-11-21 17:57:31，test 卻硬編碼要求兩者都等於 2026-11-23 05:25。該 fixture 的 news_window_taipei 已封口於 11/21 17:57:31，但報告日期為 11/23；應分離 report cutoff 與 news cutoff，並同步測試。
- 最新完整 deterministic self-test run：44897795972，conclusion=success；執行的 11/23 fixture contract、44 項計數、新聞 5+10、W47/W48 calendar projection、NVDA actual／price reaction、earnings schema 等測試均通過。較早 runs 曾因 cutoff、source update timestamp、Silver -7.42% stale assertion 失敗；已逐項修正。此 run 沒有執行 HTML build 或 Playwright，不能視為 Builder／視覺 QA 通過。
- QA Contract v1.5 DRAFT 已增加 320px viewport；visual_regression.mjs 與 workflow QA evidence expected_widths 已同步加入 320px。

## 已確認的正面基礎

1. 使用真正的 BeautifulSoup DOM parser，而非以固定字串 index 作為主要 DOM 定位工具。
2. 透過 calendar_source_guard 讀取 main 權威行事曆並投影資料；有 calendar SHA 與 branch scope 檢查。
3. 有 report-layer overlays，並在多處保護 main JSON 不被寫入。
4. 引入 earnings_judgment 模組；部分財報投影有事件 ID、日期、來源及狀態檢查。
5. 程式包含 fail-closed 條件，遇到來源或事件身分不符時會 raise。

## 必須補齊的驗收，才可重新評估

- [ ] CLI 全參數、預設值、必要檔案、輸入輸出路徑與副作用清單。
- [ ] 逐函式／逐 selector 的 DOM 寫入白名單：允許修改的文字、屬性、子節點，以及禁止觸碰的節點。
- [ ] 對兩份 SHA 鎖定母版分別做輸入／輸出 DOM diff；所有差異逐節點分類，CSS／JS／既有互動節點不得未經授權變更。
- [ ] 母版 CSS／JS 數量、內容 SHA、ID、錨點、tabs、radio、details/summary、收折預設狀態及卡片結構的自動化前後比對。
- [ ] 週一與平日各一份真實 fixture build；不得以 smoke test 或 Python compile 取代。
- [ ] 行事曆 source guard、財報判讀、新聞、44 項行情、11 ETF 排序、FedWatch、三區市場評論等完整 fixture contract tests。
- [ ] 負向測試：Manifest SHA 不符、母版缺失、selector 缺失／重複、事件 ID 不存在、main calendar SHA 改變、資料日期錯置、現貨／CFD 商品身分錯置、輸出路徑指向保護檔案。特別要在 Builder 或 build preflight 中拒絕任何把 cfd_index_reference_series 當現貨收盤的記錄；目前程式未做到。
- [ ] Playwright 互動及視覺回歸；至少 320／360／390／412／768／1440 px，並同步更新 Workflow／visual_regression.mjs。
- [ ] 輸出 HTML 回讀 SHA、HTML DOM diff、Pages／preview 可開啟性另行驗證。

## 建議處置

目前不修改 Builder 程式，也不將其列為唯一入口。SIM-1.4 應將它標記為「候選 Builder，尚未通過母版相容性 Gate」。若使用者希望保留現有視覺修復，必須先將那些差異列成獨立、可審核的明確授權變更；不得用「Builder 自動加 CSS」繞過母版零退化規則。

## 目前可宣告的證據狀態

- Builder 全檔靜態檢查：完成。
- Workflow Python compile／deterministic self-tests：run 44897795972 PASS。
- 11/23 fixture contract：PASS；六筆 CFD 指數已標待核實並保留 rejected_reference，未冒充現貨。
- 真正 Python HTML build：未執行；11/23 fixture 仍有 CFD／情緒資料 blocker。
- DOM 前後差異測試：未執行。
- Playwright／視覺 QA：未執行；320px 已接入程式碼與 evidence gate，但尚未實際跑瀏覽器。
- 唯一 Builder 核准：未核准。


## 2026-11-21 補充：11/23 fixture 的現貨／CFD 阻塞

對 2026-11-23 fixture 實際檢查後，global_markets 有 6 筆明確標示 cfd_index_reference_series：S&P 500、Nikkei 225、Hang Seng、FTSE 100、DAX、STOXX Europe 600。S&P 500 的 key_levels 子模組另有 Yahoo Finance ^GSPC cash_index OHLC；但 44 項 global_markets 主欄仍使用 Investing.com CFD 來源，兩者不可混作同一證據。11/23 fixture 已將這六筆列為 review blocker；尚未替換為現貨來源，不得輸出成正式收盤價。

Builder 的 market_groups 檢查僅驗 source name／URL／data_date，不驗 quote_type；所以它目前可能把有完整來源欄位的 CFD 序列照常渲染。這是 Builder 必須修正的實質阻擋項，不是只靠文字註記可解決。未通過前，Builder 不得核定為 SIM-1.4 唯一入口。


## 最新執行證據（2026-11-21）

- GitHub Actions run：44897795972（commit 87ec7dea36ed6465b4bf0386bbf2dc098055ba07），conclusion success。
- 成功測試：test_1123_fixture.py、preflight_1123_overrides.py、calendar_source_guard、dual mother validation、earnings judgment/schema、report-layer status／calendar overrides 等。
- 測試明確回報：44 項計數正確；新聞 5+10；新聞窗口 11/21 17:57:31 已封口、報告截稿 11/23 05:25；六筆 CFD index records 已被抑制成「待核實」；情緒／FedWatch刷新及 HTML QA 仍阻塞。
- 這是 deterministic self-test 通過，不是審核版產出，不是 HTML build，不是 Playwright 通過。


## 2026-11-21 補充：財報 Renderer 與新引擎不相容

- 保護中的 build_review_html.py 維持原始 SHA 04d5976e38ab0da24e19bbe4607da8f1c20e1d35，本輪未修改。
- earnings_judgment.py 已升級 1.4.0，公開狀態只有 beat／miss／inline／pending；不相容輸入會輸出 pending 並保留 comparison reason。Schema 已同步 1.4.0，visual_regression.mjs 已只接受四種狀態。
- Builder 的 earnings_status_label／earnings_commentary 仍含 incomparable／consensus_divergent 舊標籤與分支。對於數值存在但幣別／單位／期間明確不相容的紀錄，Builder 目前會把 pending 顯示成「尚未公布」，而 QA Contract v1.5 Section M 要求「比較資料尚未齊備」。
- 因交接保護限制，本輪不修改 Builder；此項列為 BLOCKER。除非 Builder 後續修正並通過 4-state renderer tests／Playwright，否則不得核准為唯一 Builder，亦不得宣稱財報卡片 QA PASS。


## 最新財報引擎回歸（2026-11-21）

- GitHub Actions run 44897795972 success；consensus snapshot store 23 tests、earnings comparison status、earnings judgment engine 1.4.0、schema audit、report-layer status、11/23 fixture contract 均通過。
- 此 run 仍未執行 HTML build／Playwright；Builder renderer 的舊狀態標籤未修正，仍為 BLOCKED。


- 最新 GitHub Actions run 44897956591（commit 384dab2fdfd498248f6911746db82f968bb8daf7）conclusion success；Python compile、Node --check（visual_regression.mjs／interaction_smoke.mjs）及 deterministic self-tests 均通過。此 run 未執行 HTML build、DOM diff 或 Playwright。

## 2026-11-21 實作修正與回歸驗證（持續中）

- Builder commit `cb2027f23c38bf0e0a415c413bb69e2538609013`：新增 `reject_cfd_cash_index_quotes`，在渲染邊界拒絕 `cfd_index_reference_series`／`cfd_cash_index_proxy`，保留 rejected_reference 證據並強制顯示「待核實」。
- Builder commit `57226d48fcf4a7c2402e36e365667b64ae056c9c`：財報 renderer 改為只接受 beat／miss／inline／pending 四種狀態；已公告但比較資料缺漏改顯示「比較資料尚未齊備」，不再輸出 incomparable／consensus_divergent 狀態 class。
- 新增 `simulation-lab/runner/test_quote_type_guard.py`，測試 CFD 數字不得渲染、有效現貨／provider 序列不受影響、重複執行冪等，以及財報 pending 標籤。已加入 workflow deterministic self-tests。
- Workflow push build run `44899645332`（commit `c8f4bc4fadb7c4daec9220752d8ca4e9eef68724`）已觸發，目的為真正執行 11/23 Monday fixture build、artifact validator、Playwright interaction smoke 及 1440/768/412/390/360/320 視覺回歸；本次記錄時狀態仍 pending，尚無測試結論。
- 本輪尚未解除原稽核列出的母版 DOM/CSS 注入、週一收折 summary 重建、Fed 區塊重建及完整雙母版 DOM diff blocker；在 run 完成並逐項修正前，Builder 不可核定為 SIM-1.4 唯一入口。
- main、正式母版、Manifest、正式首頁及正式行事曆 JSON 均未修改。
