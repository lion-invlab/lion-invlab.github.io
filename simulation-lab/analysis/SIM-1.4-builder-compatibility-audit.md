# SIM-1.4｜HTML Builder 相容性稽核

> **現況讀取提示（2026-11-21 22:xx）：** 本文件前段是早期 Builder SHA `04d5976e38ab0da24e19bbe4607da8f1c20e1d35` 的歷史靜態稽核快照；不得將其舊的「尚未 build」結論當成目前狀態。最新狀態以文末「最新候選 Builder SHA 實證更新」為準：Monday 最新 Builder `fe8da8e...` 已完成 build／QA；Weekday 最新同 SHA build 尚待確認；完整 selector/write whitelist 與負向矩陣仍未完成，Builder 仍未核准為唯一入口。

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


## 2026-11-21｜Fed 官員週行程固定槽位修復（尚待 CI／Build QA）

- 使用者明確要求保留 Fed 官員行程功能；因此不刪除功能，而是修復 Builder 與母版脫節問題。
- 週一母版新增固定 `#fed .fc-fomc-weekly-events` 外層、標題、清單、事件原型及空狀態槽位；平日母版同步相同契約。事件原型固定含日期、名稱、影響說明、官方來源連結欄位。Builder 僅深複製母版原型並填入欄位，不再清空／重建外層容器或整張卡片。
- Manifest 已更新 simulation 母版 SHA：Monday `52fa9949b82b0c86974b3cc4785d734321316b02`；Weekday `c91f96e121b6fb779c6775bd845e8eb29c7cc70b`。QA Contract 已新增 Fed 行程槽位及保留結構驗收條款。
- Builder 修正 `normalize_market_label` 的 regex typo：原始 `r"\\s+"` 只會匹配反斜線與 s 字元，無法移除空白；已改為 `r"\\s+"` 的 Python 正確空白 regex（實際原始碼為單一反斜線），並補全形空白測試。
- `test_quote_type_guard.py` 已擴充：兩份母版均需驗證 Fed 行程槽位存在且唯一、已發表／預定事件能顯示、空週顯示明確空狀態、外層節點與事件原型不被破壞。該測試已在 workflow 原有 deterministic self-test step 中執行。
- Builder 修復 commit：`7e9a4fe524880a993f7a15988776627e96e4cc0a`；測試 commit：`1ca9b8da23ce9105c7cf2b04408ca50f0d008ef1`；雙母版與 Manifest／QA Contract 已分別提交。
- 仍未通過 CI 前，不宣稱測試成功；仍須跑真正 Monday／weekday HTML build、DOM 零退化、artifact validation、Playwright 桌面／手機與六 viewport 視覺 QA。SIM-1.4 維持 DRAFT，main／正式首頁未修改。


## 2026-11-21｜Builder 母版相容性修正追加

- 移除每日 Builder 的 summary heading、週一 disclosure、側欄 layout、能源報價、財報卡片及市場名稱字體 CSS 注入；保留既有母版 CSS／JS。單次突發專題 `special_focus` 為使用者 2026-11-11 明確核准的條件式例外，不作一般每日版位。
- 移除週一收折 summary 清空重建；Fed 官員行程使用雙母版固定槽位；FedWatch 維持兩卡，不再 clone 第三卡或寫死三情境。多情境資料不符合兩卡版型時 fail closed，完整情境保留在既有快照收折區。
- QA Contract 更新 SHA：`26bb1dc456185069753d1c6b9cfa038e97875913`。實際 build／DOM diff／Playwright 尚待驗收，不得標示 SIM-1.4 完成。

## 2026-11-21｜後續修正：Fed 保留、summary／Dashboard／市場評論 DOM 保護

### 修正結果
1. **Fed 官員行程保留**：週一與平日 simulation 母版均加入固定四槽位。Builder 僅 clone .fc-fomc-weekly-event-template，更新日期、活動、影響與來源；外層 wrapper、標題、list、prototype、empty-state 不重建。
2. **FedWatch**：兩卡／兩段／兩圖例固定；不 clone 第三卡。非 hold＋hike 兩情境或其他不符情況標示待核實，完整機率留在既有 snapshot disclosure。
3. **CSS 注入**：已移除每日 Builder 追加 summary、週一 disclosure、sidebar authority、energy mobile CSS。樣式由 simulation 母版擁有。
4. **Summary**：新增 populate_summary_points_preserving_dom，保留週一／平日各自原有 b／br／text 子節點序列；資料點數量與母版槽位不符即 fail closed。平日 fixture 調整為五項，以對應平日母版五個槽位。
5. **FactSet Dashboard／市場情緒**：以母版既有文字槽位更新；保留週一四卡、平日三卡、Dashboard inline style、情緒解讀 label/body wrapper。
6. **市場評論**：set_market_observation 改為更新原有粗體標題、br、文字節點；不得 clear 後重建。DOM validator 逐一比對所有 .market-reason 的子節點及 inline style。
7. **行情來源**：保留 quote_type CFD 防錯；修正正規化空白 regex，並加入現貨／provider series 不誤殺測試。

### 新增／更新測試
- test_quote_type_guard.py：CFD 拒絕、cash/provider 保留、冪等性、兩種 Fed 固定槽位、FedWatch 兩卡、多情境 fail-closed、summary 子節點保留。
- test_earnings_health_dom_preservation.py：週一／平日 Dashboard 卡片數、inline style、來源日期／連結、forward P/E、Mag7／Other 493 欄位及市場情緒 DOM 保留。
- validate_mother_dom_contract.py：style/script 完整性、全頁 ID inventory、總結段落、Fed radio／label、FedWatch 卡片／分布、FOMC 固定槽位、官員行程外層、QUICK ACCESS、週一收折區、Dashboard／情緒卡及市場評論 DOM。

### 驗收狀態
- Run 44905408554（2026-11-23 Monday，Builder SHA 45bafe4c8e346fe1c51d1eb342c114d8009fc43c）完整成功：組裝、互動、視覺六視窗、DOM validator、artifact provenance、44 項行情結構 Gate 均 PASS；QA sidecar QA_PASSED，但 review_ready=false，原因是 VIX／MOVE／CNN Fear & Greed／FedWatch 快照待截稿前刷新。
- 後續市場評論 DOM 保護又更新 Builder 至 d6f57d5d7a91526d31747abebc6a228b933402a9，DOM validator 至 52404ce2dc6881566ea998cc84e7af030dff43ba；這一組最新 SHA 尚待重新完成 Monday／weekday build。不可沿用前一 run 的 PASS 代替最新 SHA 驗收。
- SIM-1.4 仍是 DRAFT；SIM-1.3 仍有效；main／正式首頁／正式母版未修改。

## 2026-11-21｜最新 SHA 驗收更新

- 最新 Builder SHA a3186cf7c10848d0b7d37fdb3d1268dfecaba958；DOM validator SHA e202923cb0d31a8381c238884203599a2937de77；FactSet／情緒 regression SHA 07a5f8a05a0b8518223fc79fe507a4a70cfe3111；CFD／Fed／summary／市場評論 regression SHA a3569c0355c29278bddc0bc9ec551471036cf586。
- Run 44906325728 以此 Builder SHA 完成 2026-11-23 Monday 完整驗收並成功 persist；Playwright、DOM contract、provenance、44 項行情／新聞結構、六視窗全部 PASS。
- QA sidecar 3f455650a5c8b0645df54a46652b0801388e9990：QA_PASSED；review_ready=false，唯一 blocker 是 VIX／MOVE／CNN Fear & Greed／FedWatch 快照時間過舊，須在 11/23 截稿前刷新。
- 最新 SHA 的 weekday 完整回歸尚待本次 11/20 run；在其通過前，雙母版完整驗收不算結案。
- SIM-1.4 保持 DRAFT，SIM-1.3 繼續有效；main 與正式資產未修改。


## 2026-11-21｜最新 Monday 完整實證（QA Contract v1.8 DRAFT）

### Run 證據
- GitHub Actions run：`44906803821`；commit：`4cd50ba5a00fc477f1867414e59eabe85a9abc80`；conclusion：`success`。
- 報告：`preview/2026-11-23-simulation.html`；HTML Git blob SHA：`c41b645ad29c14034c73c42940a863fd9c8b2feb`；SHA-256：`1cecb801a7ce4de95a35424f27d54be171d5df917f4f6743df02b133a040f684`。
- QA sidecar：`preview/2026-11-23-simulation.qa.json`；blob SHA：`521afcf08d09616151444c1b518065f235237cc3`。
- Builder SHA：`c4c24c03625b3532f48362d7235755a8fa55850f`；DOM validator SHA：`e202923cb0d31a8381c238884203599a2937de77`；artifact validator SHA：`5490906264518c740f39779784fb6883e5b2a120`；QA Contract v1.8 DRAFT SHA：`f6848d21286f63c4eef11682eedd8825b5fd3aad`；Manifest SHA：`1496a510d144d340c41b642592675233d5bd2917`；candidate SIM-1.4 DRAFT SHA：`9d0b2fed694ffe09724f310514f3a4f759b9b956`。
- Monday mother SHA：`36f29bcb37816348756f9233b60f0429d675a76e`。Sidecar 的 provenance 四項 SHA 均已綁定 build commit；HTML 與 sidecar 已成功 persist 至 simulation branch。

### 驗收結果
- deterministic self-tests：PASS。
- HTML assemble：PASS；依 Monday 母版原有結構更新。
- Playwright navigation／tabs／accordions／source links：PASS。
- 母版 DOM／inline style contract：PASS。
- artifact／provenance 驗證：PASS。
- 日期、行事曆／財報權威資料筆數、44 項行情及新聞結構 Gate：PASS。
- 六視窗視覺 QA：PASS（1440／768／412／390／360／320 px）；Noto Sans CJK TC 字型已安裝並以 fontconfig alias 對應 Noto Sans TC，Playwright `document.fonts.check` 對母版與報告均為 true，截圖不再有中文字形方框。
- Visual evidence SHA-256：`4826bd840b96b881360b505ecf5a1830d1fe896239246f128ca93b5710b276ff`；interaction evidence SHA-256：`e240827601f4d1fa566eb97ba51b4e05df7dc99c3d6941e30309019c0e1089cc`。

### 狀態界線
- QA sidecar：`status=QA_PASSED`，但 `review_ready=false`；唯一資料 blocker 為 VIX、MOVE、CNN Fear & Greed、FedWatch 必須在 2026-11-23 05:25 截稿前刷新。不得把 QA_PASSED 誤稱為資料已可發布。
- `sim14_builder_approval=NOT_APPROVED`、`sim14_review_ready=false`；SIM-1.4 仍是 DRAFT，SIM-1.3 仍有效。
- 本 run 僅寫入 simulation branch；main、正式首頁、正式母版、正式 Manifest、正式 W47/W48 JSON 未修改。
## 2026-11-21｜Weekday 母版完整實證（與 Monday 雙母版對照）

### Run 證據
- GitHub Actions run：`44907253127`；commit：`06f09ada48f92c1092160a94422c26c15dac250f`；conclusion：`success`。
- HTML：`preview/2026-11-20-simulation.html`；Git blob SHA：`a638ee6a15a919e86b11313b404cc363f85d1763`；SHA-256：`8cfb603aae5abebfb12fb50610cce8ceab63ca68e64a8ddfc55d7f84a803159b`。
- QA sidecar：`preview/2026-11-20-simulation.qa.json`；blob SHA：`8a60cf7da0f161967fb2e124b9748400c4c449a1`。
- Builder SHA：`c4c24c03625b3532f48362d7235755a8fa55850f`；Manifest SHA：`1496a510d144d340c41b642592675233d5bd2917`；QA Contract v1.8 DRAFT SHA：`f6848d21286f63c4eef11682eedd8825b5fd3aad`；candidate SIM-1.4 rules SHA：`1b808c093bfd6186febdca58021589026ef23700`；weekday template SHA：`19e77a2f34f06a0f1a53d1eeaf875ac5e1345b96`。
- QA sidecar provenance 已綁定本次 build commit；HTML 與 sidecar 均已寫回 simulation branch 並 read-back 核對。

### 驗收結果
- deterministic self-tests：PASS。
- HTML assemble：PASS。
- Playwright navigation／tabs／accordions／source links：PASS。
- 六視窗視覺 QA：PASS（1440／768／412／390／360／320 px）。
- Noto Sans CJK TC 已安裝、fontconfig alias 已驗證；Playwright 字型檢查及視覺比較通過。
- 母版 DOM／inline style contract：PASS。
- artifact／provenance、日期、行事曆／財報權威資料筆數、44 項行情及新聞結構 Gate：PASS。
- Weekday sidecar：`status=QA_PASSED`、`review_ready=true`、`data_review_ready=true`、無 review blockers。

### Weekday 資料證據邊界（不得把 QA 通過誤寫成無保留）
- 44 項行情以 2026-11-19 為基準日；MOVE 使用使用者 11/20 06:40 提供之 Investing.com 截圖（畫面時間 11/19 16:17 EST），不是助理獨立刷新。
- CNN 官方頁本輪受 robots 限制，採 FGScore CNN Provider Index 19，並明示時間戳；Financial Context 更新晚於 05:25 截稿，未納入。
- 美債殖利率為 Investing.com 歷史序列，不是 Treasury CMT par yield；WTI／Brent／GCZ6／SIZ6 是指定月份合約平台收盤／Last，不是 CME／ICE 官方結算。
- ROST 官方實際值已採 SEC 8-K，但公告前共識缺少必要 PIT 欄位，因此不作 Beat／Miss 判斷；下一交易日價格反應待後續。
- W47 正式行事曆 JSON coverage 仍 incomplete；本報唯讀正式 JSON，未自行修補。
- 上述限制已記錄在 sidecar 的 warning／pending_items；sidecar 的 `review_ready=true` 代表依當時 SIM-1.3 截稿與來源規則，沒有阻止審核的未結案項目，不代表每項都沒有來源註記或限制。

### 雙母版實證結論
- Monday（2026-11-23）與 Weekday（2026-11-20）均已用相同 Builder SHA、Manifest SHA、QA Contract v1.8 DRAFT 及候選規則完成真實 HTML build、母版 DOM、互動、來源連結、provenance、資料結構及六視窗視覺 Gate。
- Monday：`QA_PASSED`，但 `review_ready=false`，僅因 VIX／MOVE／CNN Fear & Greed／FedWatch 尚待 11/23 05:25 截稿前最後刷新。
- Weekday：`QA_PASSED` 且 `review_ready=true`。
- 這證明候選 Builder 已具備雙母版組裝與 QA 實證；**尚不等於 SIM-1.4 已可生效**。仍須完成規則／程式／Manifest／QA Contract 的一致性審核、SIM-1.4 renderer 舊狀態分支盤點與負向測試，並取得使用者明確核准。
- SIM-1.3 仍是現行有效規則；SIM-1.4 仍為 DRAFT。main、正式首頁、正式母版、正式 Manifest、正式 W47/W48 JSON 未修改。


## 2026-11-21｜雙母版實證後的舊稽核項目重新裁定

本節以下列最新成功 build（Monday run 44906803821、Weekday run 44907253127）及 Builder SHA `c4c24c03625b3532f48362d7235755a8fa55850f` 為準。本文前段第 13、19–27、34–37、46–70、88–110、114–157 行是修正前的歷史稽核快照；凡與本節及最新 run 證據衝突者，均不得再當作現況。

### 原始 BLOCKER 的現況

| 舊稽核項目 | 最新程式／測試證據 | 現況 |
|---|---|---|
| Builder 追加每日 CSS、改 summary／收折 DOM | 最新 Builder 已移除每日 CSS 注入及週一 summary 清空重建；DOM validator 比對 style/script、ID、summary、details、tabs、radio 等母版結構；兩母版真實 build 均通過 | 已修正並通過目前 QA Contract |
| Fed 官員行程清空／重建 | `populate_fed_weekly_agenda` 僅使用母版既有 title/list/prototype/empty slots；只移除舊的動態 event instances，保留 wrapper、prototype 與 empty state；來源 URL 只填入既有 anchor | 已修正；雙母版 DOM／build Gate 通過 |
| FedWatch 重建第三卡／任意機率結構 | `populate_fedwatch_two_slots` 固定使用母版兩張機率卡、兩段 bar 與兩個 legend；不符兩情境契約即 fail closed，完整分布留在既有 snapshot disclosure | 已修正；deterministic tests、兩母版 build 通過 |
| CFD 被當成現貨收盤 | Builder 的 `reject_cfd_cash_index_quotes` 在渲染邊界拒絕 `cfd_index_reference_series`／`cfd_cash_index_proxy`；保留 rejected_reference 並顯示待核實；quote-type regression tests 通過 | 已修正；最新 11/23 fixture 17 項 global market 全部有 quote_type，沒有 CFD quote_type |
| 財報舊 incomparable／consensus_divergent renderer | Builder 只接受 beat／miss／inline／pending；已公告而實際值／共識不可比較時顯示「比較資料尚未齊備」；舊狀態不再輸出 | 已修正；四狀態 regression tests 及雙母版 build 通過 |
| Dashboard／市場情緒／市場評論文字寫入破壞子節點 | 只更新母版既有文字槽位；市場評論比較 b／br／text 子節點與 inline style；source link-only 容器保持不動 | 已修正；DOM regression tests、雙母版 DOM Gate 通過 |
| Builder／Workflow 母版檔名不一致 | Workflow 將 `weekdays` 明確映射至 `weekday-mother-template.html`，`monday` 映射至 `monday-mother-template.html` | 已修正；Weekday run 44907253127 成功 |

### 尚未裁定為完成的範圍

1. 本次通過證明候選 Builder 在兩份 simulation 母版與兩份指定 fixture 上能完成 build 及現行 QA Contract；不代表所有未來資料組合均已覆蓋。仍需補足重要 selector 缺失／重複、空行程、單一／多情境 FedWatch、所有 quote_type 邊界及資料來源缺失的負向案例矩陣。
2. 必須重新逐項對照 SIM-1.3 與 SIM-1.4 DRAFT 的規則差異、Manifest 權威 SHA、QA Contract v1.8 DRAFT 與 Builder 行為；雙母版通過不能取代規則條文審核。
3. CLI 副作用、允許寫入路徑、所有動態容器清空範圍及白名單仍需形成完整可查核的 selector/write inventory。尤其 `.week-earnings-panels`、各 accordion list 等動態資料槽位允許重建其子項，但外層 wrapper、prototype、details／summary、連結及母版控制元件必須保留；此界線要在文件中逐一明列。
4. 不得把 Monday 的 `review_ready=false` 當成 Builder 失敗：其 HTML／DOM／互動／視覺 Gate 已通過，唯一 blocker 是四項風險／情緒／FedWatch 資料需在 11/23 05:25 截稿前刷新。Weekday 11/20 sidecar 為 `review_ready=true`，但仍保留來源口徑與使用者截圖等 pending／warning 證據。
5. SIM-1.4 仍為 DRAFT；Builder 尚未取得唯一入口核准。SIM-1.3 仍是唯一現行有效規則。任何啟用或正式首頁更新均需另行明確核准。

### 目前整體判定

- **雙母版 Builder 實作與指定 fixture 實證：PASS。**
- **候選 Builder 可直接升格為 SIM-1.4 唯一入口：尚未核准。**
- **SIM-1.4 規則／Manifest／QA Contract／Builder 全面一致性審核：進行中。**
- **正式 main／首頁／正式母版：未修改。**


## 2026-11-21｜凍結本輪候選規則 SHA，重跑同版 Monday

- 本輪 SIM-1.4 DRAFT 已完成雙母版實證後的規則一致性修訂；目前候選規則 SHA：`3d5f067ff08df3ba82409620c3d3afc4265c7792`。
- Monday 既有成功 run 使用前一版 candidate rules SHA，故需以本次凍結版重新執行 2026-11-23 Monday build；Weekday 亦將在 Monday 完成後，以同一 candidate rules SHA 重跑。
- 本次只觸發 simulation branch QA；不修改 main、正式母版、正式 Manifest、正式首頁或正式行事曆 JSON。

---

## 2026-11-21 補充：同一凍結 SHA 雙母版實際 build 證據與重新裁定

本節更新前文「尚未執行新的成功 Python build、未產生新 HTML、未完成 Playwright／視覺回歸」的歷史狀態；前文保留作歷史稽核紀錄，不再代表最新 run 狀態。

### A. 同一組候選版本的兩份實際 build

| 項目 | Monday 2026-11-23 | Weekday 2026-11-20 |
|---|---|---|
| Workflow run | 44907807730 | 44907973204 |
| HTML | preview/2026-11-23-simulation.html | preview/2026-11-20-simulation.html |
| QA sidecar blob SHA | aa61f29a0808b36b15421dd139e7a1d5758b156f | 185b0f0843440307c6688f0c1325dcfac607132b |
| HTML SHA-256 | 142c60016a04b0706b263198ebd58002c0bebe75732d680c37b576f24cdf0dfa | db5321af09200ca3c0ea8a66a91bb7f211374e34572a905043ab176e6bbc0a13 |
| QA | QA_PASSED | QA_PASSED |
| review_ready | false | true |
| Builder SHA | c4c24c03625b3532f48362d7235755a8fa55850f | c4c24c03625b3532f48362d7235755a8fa55850f |
| Manifest SHA | 1496a510d144d340c41b642592675233d5bd2917 | 1496a510d144d340c41b642592675233d5bd2917 |
| QA Contract SHA | f6848d21286f63c4eef11682eedd8825b5fd3aad | f6848d21286f63c4eef11682eedd8825b5fd3aad |
| Candidate SIM-1.4 SHA | c5d992b71bb4359b22c266cab00b05d527bdfb0e | c5d992b71bb4359b22c266cab00b05d527bdfb0e |
| Active SIM-1.3 SHA | 679eae7ba7a40dbad64d15bb448fe53db7d67e09 | 679eae7ba7a40dbad64d15bb448fe53db7d67e09 |

Weekday run job 136857517375 completed successfully. Its steps show success for HTML assembly, Traditional Chinese font verification, Playwright interaction/source-link tests, comparison against the selected mother, mother-owned DOM structure validation, independent artifact/provenance validation, 44-indicator/news/calendar shape validation, evidence sealing, and simulation-branch persistence. Thus, the two templates now have successful real build and browser-QA evidence under the same frozen candidate/Builder/Manifest/QA Contract SHAs.

This does not mean the two reports have the same data readiness. Monday still has four pre-cutoff refresh blockers (VIX, MOVE, CNN Fear & Greed, FedWatch); Weekday's sidecar has review_ready=true but carries explicit data-source caveats and pending notes. It also does not approve SIM-1.4: both sidecars explicitly record sim14_builder_approval=NOT_APPROVED and sim14_review_ready=false.

### B. Builder source re-read: selector/write inventory first-pass findings

Current Builder blob SHA verified from branch: c4c24c03625b3532f48362d7235755a8fa55850f (2,567 lines). A first-pass source scan found 451 selector/find/mutation-related lines. This is a preliminary inventory, not yet a complete selector-by-selector whitelist.

**Confirmed protective changes in current source**
- set_text() refuses to clear a node that contains child elements; it is restricted to leaf-text targets.
- Fed weekly agenda checks its outer wrapper, title, list, prototype and empty-state nodes; it removes only direct rendered event instances, clones the fixed prototype, and retains the wrapper/prototype/empty-state nodes.
- FedWatch requires exactly two probability rows, two bar segments and two legend entries; it updates existing slots rather than reconstructing the cards.
- CFD reference series are explicitly rejected by the market guard and marked cfd_index_reference_rejected rather than rendered as cash-index closes.
- Summary title is updated in its existing heading slot; summary points and sentiment interpretation use dedicated preservation helpers.

**Remaining structural mutation risks found in the current source**
1. head_node.append(Comment(...)) adds calendar provenance comments; a later soup.head.append(provenance_comment) adds build provenance. These are intentional metadata additions but mean the output head is not byte-identical to the mother.
2. The optional special_focus branch constructs a new section, many new elements and inline styles, inserts it before the summary, and appends a responsive style element to head. It is conditional and absent from the ordinary 11/20 and 11/23 fixtures, but it is still a non-mother DOM/CSS mutation path requiring explicit opt-in authorization and negative tests.
3. Economic calendar assembly uses panels.clear(), then rebuilds status groups and cards from copied prototypes. Earnings assembly similarly uses ep.clear() and reconstructs groups/cards. These are broad clears of container children, not leaf-slot updates. They may be allowed only if the exact containers are explicitly designated dynamic collections by the mother/Manifest/QA Contract and all fixed wrappers, disclosures, controls, IDs and interaction structure are reconstituted and tested. Current QA_PASSED alone does not prove this is authorized by the no-structure-change rule.
4. Several source-disclosure bodies, sector-source containers, key-level disclosure bodies and core-observation callouts are cleared/repopulated. Each must be mapped to its exact mother-owned slot and tested for preservation of required anchors, details/summary, labels and controls. set_text() protection does not cover direct .clear() calls.
5. meta[name=report-date] content, approved status classes, event link href/hidden attributes, and selected labels are changed in place. These are attribute-level writes and must be separately listed in the allowlist.
6. The current browser QA's "mother-owned DOM structure unchanged" check is a stable-structure validator, not a complete byte-for-byte or all-node DOM diff. Passing it cannot be used to claim all mutations are harmless.

### C. Updated disposition

- Dual-mother real builds under one frozen SHA: PASS.
- Browser interaction and six viewport/font QA for both runs: PASS.
- Sidecar/provenance and 44-indicator structural validation for both runs: PASS.
- Monday data review readiness: NOT READY (four named freshness blockers).
- Weekday data review readiness: READY WITH EXPLICIT SOURCE CAVEATS as recorded in its sidecar.
- Builder's complete selector/write whitelist and negative mutation matrix: NOT COMPLETE.
- Builder approval as SIM-1.4 unique entry point: NOT APPROVED.
- SIM-1.4 status: DRAFT; SIM-1.3 remains active.

### D. Next required audit work

1. Enumerate every destructive operation (clear, decompose, extract, replace_with, append, insert, attrs writes) by function and exact selector; classify as fixed shell, approved dynamic collection, text leaf, attribute slot, or unauthorized/conditional extension.
2. Cross-reference each target selector against both mother-template DOMs and Manifest; record count, parent path, required child structure, and whether it is an approved dynamic slot.
3. Add negative tests proving that missing/duplicate targets, missing wrappers/prototypes, altered details/summary controls, absent source links, extra/missing FedWatch rows, missing Fed agenda slots, and unapproved special_focus/CSS injection fail closed.
4. Re-run both mother fixtures after any Builder or QA Contract change; a changed frozen SHA invalidates the current same-version dual-build evidence.


## 2026-11-21 22:xx｜最新候選 Builder SHA 實證更新（取代舊 SHA 的狀態描述）

### 最新 Monday 實證
- GitHub Actions run：`44914993653`，conclusion `success`；candidate Builder blob SHA：`fe8da8e131a314897deb68ae608fda9d7647ac16`。
- HTML：`preview/2026-11-23-simulation.html`，blob SHA `d83893d0b4be9960b6642253e51a9ef5cfe4fd9e`；QA sidecar blob SHA `e2ca2b8af44b88329b88c0e7fadec51b612f4d32`。
- 成功步驟包括 Python compile／deterministic tests、Monday HTML assembly、Playwright navigation／tabs／accordions／source links、mother comparison、mother-owned DOM structure validation、artifact/provenance、日期／calendar counts／44 indicators／news shape validation、evidence sealing 及 simulation-branch persistence。
- Monday sidecar：`QA_PASSED`，但 `review_ready=false`；VIX、MOVE、CNN Fear & Greed、FedWatch 仍須在 2026-11-23 05:25 截稿前刷新。SIM-1.4 Builder approval 仍 NOT_APPROVED。

### Weekday 證據邊界
- 最近可核對的 Weekday 完整 build 為 run `44907253127`，Builder SHA `c4c24c03625b3532f48362d7235755a8fa55850f`，QA_PASSED／review_ready=true，且有明確來源 caveats。
- 此 Weekday SHA 與最新 Monday Builder SHA `fe8da8e...` 不同。因此**不能宣稱最新 Builder SHA 已完成雙母版同版驗收**；必須用 `fe8da8e...` 再跑 Weekday fixture，才能更新為同一凍結 SHA 雙母版通過。
- 先前 run `44907253127` 的 Weekday 證據仍有效於其自身 Builder SHA，不得丟棄，也不得移植成 fe8da8e 的證據。

### 最新三項使用者回報缺陷的驗證
1. **商品連結／顯示名稱：** 最新 HTML 的 WTI／Brent／GC／SI 名稱不含合約月份；合約資訊留在來源補充說明。四個連結分別指向 Investing.com HK 商品歷史頁，已直接開啟核對頁面標題／合約：WTI Jan 2027、Brent Jan 2027 LCOF7、Gold Dec 2026 GCZ6、Silver Dec 2026 SIZ6。來源證據 URL 與商品導覽 href 分開保存。
2. **財報小卡：** 已修正四星／五星 prototype class 同步問題。最新 Monday preview 保留 EPS／Revenue 雙卡並列及下方全寬詳細區；124 個 style blocks 與 Monday mother 逐塊相同，25 個 script blocks 數量相同；母版 DOM validator 及 browser smoke 通過。
3. **行事曆分頁：** 最新 Monday preview 經濟事件 today／upcoming／published = 6／21／0，財報 = 1／10／0。已修正 status group append 造成 nth-child 順序錯位、空 group 留在原位及舊 empty-state 文案殘留；目前分頁順序 today → upcoming → published，按台灣截稿時點分類。

### 仍未完成的 Builder 相容性 Gate
- 完整 selector/write inventory 尚未完成；特別是 calendar／earnings 動態容器的 `.clear()` 子節點重建範圍、attribute writes、source disclosure containers 及 conditional `special_focus` 仍須逐 selector 對照母版、Manifest 與 QA Contract。
- 現行 mother-owned DOM validator 是穩定結構驗證，不等同全節點 byte-for-byte DOM diff；不得以 style/script 數量相同宣稱所有 DOM mutation 已獲授權。
- 必須補齊負向測試矩陣，並以最新 Builder SHA `fe8da8e...` 重跑 Weekday fixture。
- **結論：** 最新 Monday build／QA PASS；最新 Builder 的 Weekday 同 SHA 實證待補；完整 selector/write whitelist 待完成；Builder 唯一入口仍 NOT_APPROVED；SIM-1.4 DRAFT、SIM-1.3 active。


## 2026-11-21｜候選規則 SHA 與既有 build provenance 不一致（重要限制）

- 11/23 run `44914993653` 的 QA sidecar `candidate_rules_blob_sha` 是 `c5d992b71bb4359b22c266cab00b05d527bdfb0e`，不是目前 SIM-1.4 DRAFT SHA `0d390cc7de7945e1d9af247dbf004f45319d5e99`。
- 最新三項規則補正是在 run `44914993653` 之後提交，因此現有 HTML／QA PASS 只能證明舊 candidate rules SHA 下的 build；不能宣稱已按最新草案完成驗收。
- 必須用目前 DRAFT SHA `0d390cc7...` 重新執行 Monday build，並以同一最新 Builder SHA `fe8da8e...` 重新執行 Weekday build。兩次 sidecar 都必須記錄同一 candidate rules SHA、Builder SHA、Manifest SHA、QA Contract SHA，才可稱為最新版本的雙母版實證。
- 在重跑前，現有 preview 可供缺陷修復成果參考，但不是最新 SIM-1.4 草案的最終驗收件；不得把舊 PASS 移植到新 SHA。


## 2026-11-21｜最新 SIM-1.4 DRAFT SHA 與母版視覺規則補正

- 最新候選規則已更新為 blob SHA `f585c0e08e1075d760c91a5f0eab79a408ca9e45`，補回 SIM-1.3 B3.2–B3.6 的母版視覺／互動不變條款：上漲紅／下跌綠、中文名稱與英文代碼層級、行情連結範圍、五星／四星標題色彩、禁止恢復已刪除膠囊、工具泡泡與呼吸燈分別驗收。
- 11/23 build run `44914993653` 的 sidecar candidate rules SHA 仍為 `c5d992b71bb4359b22c266cab00b05d527bdfb0e`，與目前 `f585c0e...` 不同。該 build 的 PASS 只能證明舊規則 SHA，不得宣稱最新草案已完成 build QA。
- 需在最新候選規則 SHA 凍結後，重新跑 Monday 2026-11-23 與 Weekday 2026-11-20；兩者須使用同一 Builder SHA、Manifest SHA、QA Contract SHA 及 candidate rules SHA。現有 Weekday run `44907253127` 使用 Builder SHA `c4c24c03625b3532f48362d7235755a8fa55850f`，也不能代替最新 Builder `fe8da8e...` 的 weekday 實證。
- Builder 唯一入口核准仍 NOT_APPROVED；完整 selector/write inventory、動態容器白名單及負向測試矩陣仍待完成。


## 2026-11-21｜QA Contract v1.9 DRAFT 與 build provenance 邊界

- QA Contract 已更新為 1.9 DRAFT，blob SHA `28e4aa81cb795f6a82ed219375b9a2d85b822ce9`；補入 WTI／Brent／GC／SI 名稱不帶合約月份、Investing.com 頁面合約直接開啟核對、上漲紅／下跌綠、中文名稱／英文代碼層級、五星／四星色彩、禁止恢復已刪除膠囊、工具泡泡／呼吸燈分開驗收，以及已公布財報雙卡 DOM／CSS 一致性。
- 11/23 build run `44914993653` 的 QA sidecar 使用 QA Contract SHA `f6848d21286f63c4eef11682eedd8825b5fd3aad`（v1.8 DRAFT），不是目前 v1.9 SHA `28e4aa81cb795f6a82ed219375b9a2d85b822ce9`；candidate rules SHA 亦為舊版 `c5d992b71bb4359b22c266cab00b05d527bdfb0e`，不是目前 SIM-1.4 DRAFT `f585c0e08e1075d760c91a5f0eab79a408ca9e45`。
- 因此最新 HTML／QA PASS 不可宣稱符合最新 DRAFT＋QA Contract 組合。必須在兩份候選文件 SHA 凍結後，以同一 Builder SHA、Manifest SHA 分別重跑 Monday 與 Weekday；兩份 sidecar 必須同時記錄最新 candidate rules SHA 與 QA Contract SHA。
