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
- **尚未結案**：須以相同 Builder／QA Contract／Manifest／candidate rules SHA 完成 2026-11-20 Weekday full build；雙母版都通過後才可提交 SIM-1.4 核准審查。
