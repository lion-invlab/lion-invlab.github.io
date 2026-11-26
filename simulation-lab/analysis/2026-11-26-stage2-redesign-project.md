# TAC Stage 2 行情資料擷取改造專案

**建立日期：** 2026-11-26  
**Repository：** `lion-invlab/lion-invlab.github.io`  
**工作分支：** `simulation/tac-process-lab-2026-11-06`  
**規範基準：** SIM-1.4；本專案依 2026-11-26 使用者正式指示增補 Stage 2 截圖優先與下游快照唯讀規則。  
**專案狀態：** DESIGN_LOCKED / IMPLEMENTATION_IN_PROGRESS

## 1. 專案目標

把 TAC 44 項行情資料的取得、證據、Manifest、Fixture 與快照鎖定整合成單一 Stage 2 入口。Stage 2 完成後，Stage 3、Stage 4、Builder、QA、Publisher、Pages 與 Chart 3 只消費鎖定資料，不再各自擷取或核實同一批 44 項行情。每日關鍵價位維持獨立資料流程，不納入本專案的 Stage 2 44 項行情防重抓範圍。

## 2. 正式資料取得規則

### 2.1 Investing.com 歷史數據頁

每一項尚未由截圖提供的必要欄位，使用瀏覽器直接開啟 Investing.com 對應商品的正式頁面，進入 Historical Data，讀取實際表格。至少核對商品／合約身分、資料日期、Price／Close、Open、High、Low、Change % 及該項必要欄位。

禁止以一般搜尋摘要、搜尋結果價格片段、未核准 API 或其他第三方來源替代。不得繞過 Cloudflare。頁面已載入但表格無法讀取時記錄 `TOOL_READ_FAILURE`；頁面與表格可讀但無目標資料列時記錄 `SOURCE_NO_DATA`。

### 2.2 使用者截圖優先（適用全部 44 項）

- 截圖可辨識商品、日期及數值時，直接採用截圖，不再重讀網頁核對已提供欄位。
- 不因網頁延遲而以舊值覆蓋截圖值。
- 截圖未提供的必要欄位才讀取 Investing.com Historical Data 頁補足。
- 截圖欄位與網頁補足欄位共用同一 Observation Schema，逐欄記錄來源方式與證據。
- 對外來源標示仍依商品正式來源契約；若該商品來源為 Investing.com，正文仍標示 Investing.com 歷史數據，不揭露「依使用者截圖」。
- 截圖 SHA 必須指向實際證據檔案；不一致或無法確認的雜湊不得宣稱已驗證。

## 3. Stage 2 單一輸出與凍結點

Stage 2 一次產生並封存：

1. 44 項 Observation bundle（包含每項每欄位的輸入方式與來源證據）。
2. 44 列 Manifest。
3. 當輪 Fixture。
4. 原始截圖／瀏覽器觀察證據索引。
5. Fixture、Observation bundle、Manifest、證據檔及 Receipt 的 SHA-256。
6. 批次 ID、報告日期、交易日期、資料版本及 Stage 2 receipt。

Receipt 建立即為 Stage 2 的 44 項行情快照凍結點。下游不得改寫這 44 項行情值、狀態或來源證據。只允許針對明確缺漏欄位進行單項補值；補值不得重跑其他 43 項。

## 4. 下游資料流

### Chart 3

S&P 500 收盤價使用 Stage 2 已鎖定的 44 項行情資料寫入 Chart 3 增量資料庫。Chart 3 更新不得另行擷取同一收盤報價；若 Chart 3 需要 Stage 2 未提供的其他欄位，依 Chart 3 自身資料契約處理，不得覆寫 Stage 2 快照。

### 每日關鍵價位（獨立模組，不屬於 Stage 2）

每日關鍵價位保留既有獨立 Yahoo Finance 日線 OHLC 擷取流程（`collect_key_levels_ohlc.py`），以及同交易日且具來源證據的人工／官方 OHLC override。不得將此模組改成消費 Stage 2，也不得因 Stage 2 防重抓規則而取消或限制其既有 Yahoo Finance 流程。每日關鍵價位須獨立封存交易日、來源、擷取時間與 SHA；其資料不得回寫或覆蓋 Stage 2 的 44 項行情快照。

### Stage 3–6

行事曆、新聞、分析、Builder、QA、Publisher、Pages 僅讀取 Stage 2 的 44 項行情快照；可檢查結構與 SHA，不得外部重讀已鎖定的 44 項行情。每日關鍵價位獨立模組依自身來源契約執行，不屬於此項限制。

## 5. 現況盤點（2026-11-26）

已識別的既有元件：

- `simulation-lab/runner/browser_verify_market_history.py`：Playwright 歷史頁讀取及 44 項觀察，目前主要路徑仍以瀏覽器逐項讀取為主，尚未支援完整截圖優先與欄位級合併。
- `simulation-lab/runner/build_market_source_verification_manifest.py`：由 Fixture 與 observation bundle 產生 44 列 Manifest；已有部分 screenshot 判斷邏輯，但欄位名稱、證據 SHA 與狀態尚未完全符合欄位級混合來源規格。
- `simulation-lab/runner/validate_market_snapshot.py`：驗證 44 項 Fixture 基本結構與來源中繼資料。
- `simulation-lab/runner/handoff_sp500_to_chart3.py`：S&P 500 資料交接至 Chart 3 的既有入口。
- `simulation-lab/runner/collect_key_levels_ohlc.py`：每日關鍵價位既有獨立 Yahoo Finance 日線 OHLC 流程；本專案保留，不修改其來源契約或改為消費 Stage 2。
- `.github/workflows/tac-simulation-lab.yml`：現有 Stage 2 呼叫鏈及後續資料交接須整合為單一入口。

## 6. 改造工作包與驗收

### WP1｜Observation Schema 統一

- 定義 row-level 與 field-level provenance。
- 統一 `HISTORICAL_PAGE`、`USER_PROVIDED_SCREENSHOT`、`TOOL_READ_FAILURE`、`SOURCE_NO_DATA` 等狀態。
- 截圖值優先；網頁只補未提供欄位。
- SHA-256 對標準化 Observation 與原始證據分別計算，禁止混用。

### WP2｜單一 Stage 2 擷取器

- 先載入使用者截圖觀察清單。
- 截圖已提供欄位不再開啟網頁。
- 其餘必要欄位以 Playwright 開啟 Investing.com Historical Data 表格。
- Cloudflare／工具讀取失敗如實記錄，不切換未核准來源。
- 每項只建立一份最終 Observation，保留嘗試紀錄但不重複核實已鎖定值。

### WP3｜Manifest、Fixture 與 Receipt

- Manifest 固定 44 列且每列唯一。
- 每列保存標的身分、資料日期、欄位值、逐欄輸入方式、來源 URL、證據 SHA、狀態。
- Fixture 與 Manifest 僅由 Stage 2 Observation 產生，不再由下游補寫。
- Receipt 綁定報告日、交易日、Run ID、批次 ID、Fixture SHA、Manifest SHA、Observation SHA。

### WP4｜Chart 3 與每日關鍵價位分流

- Chart 3 只使用 Stage 2 的 S&P 500 鎖定收盤價，不另行抓取同一收盤報價。
- 每日關鍵價位保留獨立 Yahoo Finance 日線 OHLC 擷取及同交易日人工／官方覆寫機制；不併入 Stage 2 44 項，也不回寫 Stage 2。
- 兩條資料流各自封存日期、來源、擷取時間與 SHA，不得互相覆蓋。

### WP5｜下游唯讀與防重抓測試

- Stage 3、4、Builder、QA、Publisher、Pages 不得對已鎖定的 Stage 2 44 項行情發出外部來源請求。
- 增加測試證明已鎖定值不會被後續 Fixture、Manifest 或 Builder 改寫。
- 增加單項補值測試，證明其餘 43 項 SHA／值不變。
- 每日關鍵價位的 Yahoo Finance OHLC 是明確排除項，必須有獨立測試證明 Stage 2 防重抓不會攔截或改寫它。

## 7. 必須完成的驗收案例

1. 截圖同時提供 Close 與 Change %：直接採用，網頁不再讀取該兩欄。
2. 截圖只提供 Close：Close 直接採用，網頁只補必要的 Open／High／Low／Change %。
3. 截圖提供多項 OHLC：已提供欄位不得由網頁覆蓋。
4. 同一商品同時有截圖與較舊網頁值：截圖優先。
5. Investing.com 頁面載入、表格不可讀：`TOOL_READ_FAILURE`。
6. 表格可讀但無目標交易日列：`SOURCE_NO_DATA`。
7. 截圖證據 SHA 不符：不得標示 VERIFIED。
8. Stage 2 Receipt 完成後，下游模擬任何 Stage 2 行情 URL 請求均應被測試攔截。
9. S&P 500 Stage 2 收盤值寫入 Chart 3，數值與 SHA 可追溯。
10. 每日關鍵價位仍可獨立取得 Yahoo Finance OHLC，且不讀取或改寫 Stage 2 快照。

## 8. 明確不在本專案授權範圍

- 不修改 `main/index.html`、正式首頁或正式母版。
- 不修改已核准 Builder 的程式或 SHA。
- 不修改 QA Contract、母版 Manifest 或正式行事曆 JSON。
- 不繞過 Cloudflare，不加入未核准資料供應商。
- 不將 PARTIAL／PENDING／TOOL_READ_FAILURE 偽裝成 VERIFIED。
- 不把每日關鍵價位既有獨立 Yahoo Finance OHLC 流程併入 Stage 2。
- 不把本專案完成等同正式早報發布授權。

## 9. 完成定義

只有 WP1–WP5 全部實作、單元測試與負向測試通過、完整 44 項 E2E 產生鎖定快照、Chart 3 消費 Stage 2 鎖定收盤價、每日關鍵價位獨立 Yahoo Finance OHLC 流程保持正常、下游防重抓測試通過，才可標記 `STAGE2_REDESIGN_ACCEPTED`。在此之前狀態保持 `IMPLEMENTATION_IN_PROGRESS` 或 `PARTIAL`，不得宣稱改造完成。

## 10. 實作紀錄

### 2026-11-26｜第一批程式改造

- `build_market_source_verification_manifest.py` 已調整為支援欄位級截圖證據：不再要求將整個商品的 `source_role` 改成截圖來源；來源契約仍保留 Investing.com。
- Manifest 會分別保存每個截圖欄位的證據路徑、SHA-256 與擷取時間；截圖欄位與歷史頁欄位可在同一筆 Observation 混合記錄。
- 截圖單獨驗證時，`source_page_fetched` 必須維持 false，不得因截圖證據存在而誤報成已讀取 Investing.com 網頁。
- 新增 `test_stage2_field_provenance.py`，涵蓋純截圖、截圖＋歷史頁混合欄位及錯誤 SHA 阻擋；並納入既有 Manifest regression test 的執行入口。
- Simulation workflow 定義暫不修改，以維持與 main/default workflow mirror 的 SHA 一致；新測試由既有 Manifest regression suite 呼叫，不另改 workflow。
- Manifest 的截圖證據 Gate 已加上實際檔案 SHA-256 比對；只檢查 64 位十六進位格式不足以通過。測試改用暫存證據檔驗證正確雜湊可通過、雜湊不符必須退回 PENDING。
- 測試以暫存圖片位元組實際計算 SHA，並測試相同檔案的錯誤 SHA 被拒絕；純截圖不得誤標為瀏覽器已讀取來源頁。
- 另加負向條件：若 Close／Change 其中一欄來自歷史頁，整筆不得標記為「純截圖」；必須明確標示混合來源，逐欄保留來源方式。
- 純截圖／混合來源狀態另須與 `source_page_fetched` 布林值一致，避免來源方法標籤與實際頁面讀取紀錄互相矛盾。
- 本批尚未完成截圖檔案自動載入、Playwright 缺欄位選擇性讀取、Fixture 自動合併、Observation bundle／Receipt 產生與完整 E2E；不得標記為完成。

### 2026-11-26｜第二批程式改造：截圖優先輸入與欄位合併

- 新增 `stage2_screenshot_inputs.py`：讀取報告日期專屬 sidecar，逐筆核對交易日、商品來源 URL、商品識別、證據檔案路徑與實際檔案 SHA-256。
- 新增 `simulation-lab/input/STAGE2_SCREENSHOT_INPUT.md`：定義 44 項共用輸入格式、圖片封存位置、欄位名稱與報價時間／截圖時間分離規則。
- `browser_verify_market_history.py` 已改成先載入截圖，再以截圖值更新當輪 Fixture 的對應值，之後才建立 44 項擷取工作清單。
- Close／Change（Fear & Greed 為 Score／Band）均由截圖提供時，該商品不會開啟歷史頁；部分截圖則只以歷史頁補齊缺少的必要欄位，已提供欄位永不被頁面值覆蓋。
- 截圖額外提供 Open／High／Low 時，亦保存欄位級來源與證據，不因主要 Close／Change 仍需補齊而丟棄。
- Fear & Greed 部分欄位可由 CNN 官方端點補足；其餘商品缺漏欄位仍使用 Playwright 直接讀取 Investing.com Historical Data，不繞過 Cloudflare。
- Manifest 已新增截圖列數、截圖欄位數、混合來源列數與純歷史頁列數；另將「值已核對」與「完全由歷史頁獨立核實」分開呈現，避免把截圖來源誤報成歷史頁重讀。
- 新增測試涵蓋真實檔案 SHA 比對、日期錯誤阻擋、Fixture 截圖值優先、純截圖跳過頁面、部分欄位混合、額外 OHLC 欄位保留。
- Workflow 無需修改即可透過預設路徑自動發現 `simulation-lab/input/market-screenshot-observations-YYYY-MM-DD.json`；截圖圖片與 sidecar 必須存在於 Simulation checkout 內。聊天附件不會自動出現在 GitHub runner，因此必須先封存實際圖片檔及 sidecar。
- 本批尚未完成 44 項實際截圖 bundle 的上線驗收、E2E 及下游防重抓測試；亦尚未取得本輪 GitHub Actions 測試通過紀錄。狀態維持 `IMPLEMENTATION_IN_PROGRESS`。

### 2026-11-26｜第三批改造：缺欄回寫、Receipt 相容與多張截圖

- 部分截圖列的歷史頁缺欄讀取完成後，新增 `apply_page_completions_to_fixture()`：只把截圖未提供的欄位回寫當輪 Fixture；截圖提供欄位不覆蓋。回寫後更新 observation 的欄位匹配狀態，避免只拿舊 Fixture 值比對而無法補值。
- 截圖可按欄位分別引用不同原始圖片；欄位層級的路徑、SHA、截圖時間及報價時間優先於列層級預設值。每張圖各自重新計算 SHA。
- Fixture 保存逐欄截圖證據索引與歷史頁補欄欄位清單；Manifest 與 Prebuild Receipt 重新核對實際圖片檔案 SHA。
- CFD 參考列只有在 Close／Change 均由有效截圖或本輪歷史頁完整補足時，才允許顯示數值；否則回到「待核實」，避免殘留舊 Fixture 價格。
- `validate_prebuild_stage_inputs.py` 已區分純截圖、混合來源與歷史頁列；允許純截圖列的 `source_page_fetched=false`，同時要求完整欄位證據及實際圖片 SHA。另將「值已具證據」與「歷史頁獨立核實」拆成兩個狀態。
- `validate_market_snapshot.py` 加入 CFD 截圖／歷史頁完整欄位證據 Gate，並新增正向／負向測試。
- GitHub Actions 在 commit `58b64deed25e5af7f3c20cde7f22d8615db230e9` 的 Simulation isolated-smoke 已回報 success；該版本涵蓋截圖載入、欄位優先、Fixture 缺欄回寫、Prebuild Receipt 與 CFD 證據 Gate 的回歸測試。之後增加的多圖片欄位測試及規格文件，仍須等待最新 commit 的 Actions 結果。
- 尚未完成實際 44 項截圖 bundle 的正式 E2E、完整 Stage 2 Receipt 產出與下游防重抓驗收；狀態仍為 `IMPLEMENTATION_IN_PROGRESS`。

### 2026-11-26｜第四批改造：Observation bundle 與 Receipt SHA 閉環

- Page-only Observation 也補上逐欄來源證據；不再只有整列的 read method，而是逐欄記錄 Investing.com Historical Data 或 CNN 官方端點來源、欄名、值與觀察時間。
- 截圖欄位與頁面補欄完成後，重新計算最終 Observation row SHA；不得沿用欄位合併前的舊雜湊。
- Prebuild Receipt 現在必須讀取 `simulation-lab/output/market-history-browser-observations.json`，核對 44 列、日期、唯一標的、每列 canonical SHA，並逐列比對 Manifest 的來源 URL、交易日及已核實數值。
- Receipt 新增 Observation bundle 路徑、SHA-256、純截圖列數、混合來源列數與純歷史頁列數，將 Fixture、Audit、Manifest、Observation bundle 一起綁定。
- 另外加上來源模式一致性檢查：純截圖列必須 `source_page_fetched=false)，混合列與純歷史頁列必須有本輪頁面／官方來源讀取紀錄。
- 目前已完成程式與回歸測試接線；最新一輪對應 commit 的 isolated-smoke 正在執行。先前 commit `b85fdb2deea5be79ed2364d6749fc033975b39a3` 的 isolated-smoke 已成功，涵蓋修正後的 Python compile 與既有測試；新增的 Receipt source-mode gate 尚待最新測試確認。
- 完整 44 項實際截圖 bundle、正式 Stage 2 Receipt 實際產出、下游防重抓 E2E 仍未完成。狀態維持 `IMPLEMENTATION_IN_PROGRESS`，不得宣稱整體改造已驗收。

### 2026-11-26｜最新回歸結果與尚未驗收項目

<badge color="success">ISOLATED-SMOKE PASS</badge>

- Commit `43cbd281bdf108b5b36f584dbc0449f576261bc5` 的 GitHub Actions `TAC isolated simulation lab` 已完成並回報 success；同 commit 的 workflow YAML lint 亦 success。
- 本輪測試涵蓋 Python compile、截圖 sidecar SHA／日期／標的識別、純截圖跳過歷史頁、部分欄位由歷史頁補足並回寫 Fixture、同商品多張圖片、CFD 證據 Gate、Prebuild Receipt 純截圖／混合來源接受，以及 Observation bundle 44 列／canonical row SHA／Manifest 交叉綁定。
- Receipt production entry 預設讀取 `simulation-lab/output/market-history-browser-observations.json`，必須核對 44 列、報告日、交易日、唯一標的、逐列 SHA、Manifest 對應值，並將 Observation bundle 檔案 SHA 納入 Receipt。
- **尚未完成實際 44 項行情 E2E。** 目前 `simulation-lab/input/` 只有輸入規格文件，沒有 2026-11-26 的 `market-screenshot-observations-2026-11-26.json` 及對應原始圖片，因此本輪程式測試沒有套用任何真實截圖值。
- 11/26 MOVE 舊 Fixture 的截圖 SHA／報價時間不一致仍未解決；不得把該舊紀錄宣稱為已驗證，也不得拿它冒充新的 Sidecar 證據。
- 正式 44 項 Stage 2 擷取、Observation bundle／Manifest／Receipt 實際產出、Chart 3 寫入與下游防重抓 E2E 尚待執行。每日關鍵價位 `collect_key_levels_ohlc.py` 維持原樣，Yahoo Finance 獨立 OHLC 流程未被修改。
- 正式首頁 `main/index.html`、`main` workflow、母版與正式資料均未修改。Simulation workflow 與 main/default workflow 的 mirror SHA 保持一致。
- **專案狀態：** `IMPLEMENTATION_IN_PROGRESS`；目前是程式回歸測試通過，不等同 44 項實際行情流程驗收或正式早報發布。

### 2026-11-26｜Stage 2 回歸套件已接入並通過

- 將 `test_market_source_verification_manifest.py`（含 `test_stage2_field_provenance.py` 與 `test_stage2_screenshot_inputs.py`）、`test_validate_market_snapshot.py`、`test_prebuild_stage_inputs.py` 接入既有 Simulation isolated-smoke 的實際測試入口；不修改 main／Simulation workflow mirror。
- Commit `4b1690e1f44a1c75ab52ae3cccbd13e065369f30` 的 GitHub Actions `TAC isolated simulation lab` 已回報 success。執行日誌明確顯示：截圖 SHA／日期阻擋、截圖優先、純截圖、混合來源、CFD 證據 Gate、44 列 Receipt、Observation bundle 交叉綁定等測試全部 PASS。
- 這是 Stage 2 程式回歸測試通過；仍不是實際 44 項市場行情擷取或當日截圖 Sidecar 的 E2E。正式資料驗收仍需有當輪 44 項輸出與真實圖片證據。


### 2026-11-26｜第五批改造：空白行情輸入與來源值回填

- 新增 simulation-lab/runner/stage2_market_fixture_bootstrap.py，提供 blank 與 apply 兩種操作：
  - blank 保留當日報告非行情內容及 44 項標的／來源中繼資料，但清除舊收盤值、漲跌值、歷史值及舊觀察證據；保存純格式規格，不把舊數值當成新一輪比對基準。
  - 若存在當日截圖 Sidecar，先驗證實際圖片 SHA、日期、商品與來源 URL，再將截圖欄位套入空白行情輸入；已提供欄位不得被頁面讀值覆蓋。
  - apply 只使用本輪 Observation bundle 回填 44 項行情 Fixture；沒有有效來源證據的欄位標示「待核實」，不沿用空白輸入前的舊價位。完整截圖、混合來源及純歷史頁分別保留逐欄證據。
  - 美債殖利率顯示的 bp 變化由本輪收盤殖利率及頁面 Change % 推導；原始日變化百分比仍保留於來源欄位。產業 ETF 顯示漲跌幅，另保存本輪 ETF 收盤價供來源核對。
- browser_verify_market_history.py 已支援空白行情基準：沒有既有數值時，不再要求和舊 Fixture 比價；仍必須確認商品身分、目標交易日、歷史表格欄位映射及可解析數值。Observation 明確標記 NOT_PERFORMED_BLANK_INPUT，不冒稱已與舊數值比對。
- validate_chatgpt_web_observations.py 同步支援空白行情輸入：直接歷史頁觀察值只依頁面列、商品身分、交易日、欄位與來源證據判定；既有 Fixture 數值缺席時，不會被錯誤判為不匹配。讀取成功但無目標日期列仍維持待核實。
- validate_market_snapshot.py 允許產業 ETF 欄位明確顯示「待核實」或「休市」，並要求對應來源狀態分別為 PENDING 或 CLOSED；不得以缺值假裝百分比。
- 新增／擴充回歸測試：空白化 44 項舊值、由 44 列 Observation 回填、單項 SOURCE_NO_DATA 不沿用舊價、殖利率 bp、ETF 顯示、Fear & Greed、日期／重複列拒絕、部分截圖在頁面讀取失敗時保留已提供欄位、空白輸入下的直接 Web Observation 驗證，以及 ETF PENDING／CLOSED 狀態。
- 專用 TAC Stage 2 live 44-row diagnostic 已改為先產生零行情值的暫存輸入，再直接開啟 Investing.com Historical Data 頁，之後才回填 Fixture、建立 Manifest 及執行 Snapshot Validator。原始已提交的 report-data-YYYY-MM-DD.json 不會被覆寫；此診斷保留非行情報告內容與來源目錄，只將 44 項市場數值清空，故驗證範圍是「零行情輸入到行情 Fixture」，不是整份報告所有內容從零建立。
- 專用診斷工作流加入序列化，避免同一批 44 頁同時被多輪診斷重複讀取；加入空白 Fixture、直接 Web Observation 與 PENDING／CLOSED 測試。
- Commit ba654f85711473075a5cdf785200c20636eac382 對應 Run 45777774344：目前可見步驟中，空白 Fixture bootstrap 測試、空白輸入的直接 Web Observation 測試、PENDING／CLOSED Snapshot 測試均已 PASS；44 項瀏覽器擷取仍在執行，尚未完成 Fixture 回填、Manifest 與 Snapshot 驗收。
- 原先 Run 45775503897 已結束，Workflow conclusion=success，但 44 項觀察結果為 TOOL_READ_FAILURE=43、OBSERVED_PENDING_FIELD_MAPPING=1、VERIFIED=0。Artifact 顯示 43 個 Investing.com 頁面回應 HTTP 403，正常瀏覽器等待後 Cloudflare challenge 仍未完成；CNN 官方端點 HTTP 200，但本輪 previous_close 的顯示對應尚未通過。此結果確認真正的外部阻塞在瀏覽器來源頁存取，而非 Fixture 日期檢查；不得把 Workflow success 當行情成功。
- 另有 2026-11-26 手動歷史頁 Observation bundle：44 列中 43 列 PAGE_CONTENT_READ_SUCCESS，MOVE 為 SOURCE_NO_DATA。這份 bundle 的 MOVE 不得沿用舊 Fixture 的 97.54；使用者曾提供的 MOVE 截圖尚未封存為本輪 Repository Sidecar，不能把缺少的截圖證據假稱已讀取。
- 正式生產 Workflow 尚未切換到 blank/apply 新流程。曾在 Simulation copy 暫試整合，但因 SIM-1.4 要求 main/default workflow mirror SHA 一致，且 main 路徑目前受唯讀邊界限制，已將 Simulation 的 .github/workflows/tac-simulation-lab.yml 還原至 main 相同 blob SHA 0698f88333e29c3b7e86ee74e557fdc14b6ce429。正式 Workflow 尚未修改，避免下一輪完整早報因 mirror Gate 失敗；待取得更新 main workflow mirror 的明確授權後，再把已驗證的 blank/apply 呼叫鏈整合進正式生產流程。
- main/index.html、正式首頁、母版、正式資料與每日關鍵價位 collect_key_levels_ohlc.py 均未修改。
- 本批狀態：BOOTSTRAP_UNIT_TESTS_PASS / LIVE_44_ROW_E2E_IN_PROGRESS / PRODUCTION_WORKFLOW_NOT_YET_INTEGRATED；整體專案仍為 IMPLEMENTATION_IN_PROGRESS，不得標記 STAGE2_REDESIGN_ACCEPTED。


### 2026-11-26｜第五批驗收結果補記

- Commit 66016cc831b35901aeeb1bff19bd20ba711f656c 對應 Run 45778257845，專用 Stage 2 diagnostic 全部步驟 success：三組回歸測試、空白行情輸入建立、當日直接歷史頁 Observation 驗證、Fixture 回填、Manifest 建立、Snapshot Validator、Artifact 上傳均完成。
- 實際結果：空白輸入 44 列；Observation 44 列，其中 VERIFIED 43、OBSERVED_PENDING_VALIDATION 1；回填 Fixture 44 列，其中 verified 43、pending 1；Manifest 為 PARTIAL（43 verified／1 pending）；Snapshot Audit 為 PASS（44 列 metadata/date 結構檢查）。這代表零行情值到 43 項有效數值回填的 E2E 已通過，不能宣稱 44 項全部核實。
- 唯一待核實列為 risk/move：當日 Investing.com 歷史頁 Observation 記錄 2026-11-25 無目標列（SOURCE_NO_DATA）；不沿用舊 Fixture 97.54，也不將舊截圖記錄冒充本輪證據。
- 驗收 Artifact：tac-stage2-diagnostic-2026-11-26，Artifact ID 15097495872；SHA-256 digest 4baf021f98bbc422884e9260c667b1bba3a02bc0c729aa4d53d156591815af7f。Artifact 中 report-data-blank.json 的 stage2_market_bootstrap.preexisting_market_values_used=false；report-data-populated.json 只有 43 項新觀察值，MOVE close_value 為 null、顯示「待核實」。
- 本輪另發現舊 Fixture 的 MOVE source metadata 還殘留 previous_close／OHLC、screenshot_sha256、user_screenshot_observation、截圖時間與來源時間等舊欄位，即使顯示值已清空仍可能造成錯誤引用。已擴充 blank 清理清單並將舊數值型 note 改成通用 Stage 2 提示；新增負向測試確認上述欄位全部移除。Run 45778257845 的空白 bootstrap 測試已 PASS；Artifact 證實 MOVE 不再殘留上述舊截圖與 OHLC metadata。
- 本輪截圖 Sidecar 偵測數為 0；因此沒有把舊 Fixture 內 SHA／時間互相不一致的 MOVE 截圖紀錄當成當日有效截圖。使用者先前提供的截圖必須以當日有效原始圖檔與 Sidecar 封存，才能作為 SHA-locked screenshot evidence。
- Run 45775503897 的 43 個 Investing.com HTTP 403 仍是 Playwright live-page path 的實際存取阻塞；本輪 43 項成功值來自當日直接歷史頁 Observation bundle（capture session manual-takeover-2026-11-26-retry-1），不是把 HTTP 403 當成功，也不是沿用前一交易日 Fixture。
- 正式生產 Workflow 仍未切換 blank/apply；Simulation workflow mirror 已還原並與 main blob SHA 一致。正式整合仍需更新 main/default workflow mirror 的明確授權。
- 狀態： ZERO_MARKET_INPUT_E2E_PARTIAL_PASS / 43_VERIFIED_1_PENDING / PRODUCTION_WORKFLOW_NOT_YET_INTEGRATED。


### 2026-11-26｜第六批改造：正式 Stage 2 入口 blank-first 整合與 Stage 2 Receipt

- 正式早報 Workflow YAML 無須修改，也沒有擴張 main 寫入白名單；透過既有 Stage 2 呼叫的 Runner 程式完成整合：
  - browser_verify_market_history.py 預設先將傳入 Fixture 的 44 項行情值、舊截圖紀錄與舊觀察證據清空，再執行截圖優先／歷史頁補值；成功後將本輪 Observation 回填至同一份工作目錄 Fixture。另提供 --no-fixture-write，供診斷工作流分離 capture 與 apply。
  - validate_chatgpt_web_observations.py 預設同樣 blank-first，依本輪直接歷史頁 Observation 回填同一份 Fixture；若當日 Screenshot Sidecar 存在，則優先委派 screenshot-first browser runner，不會讓舊 Web bundle 覆蓋截圖欄位。另提供 --no-fixture-write 給診斷工作流。
  - 因此既有 tac-simulation-lab.yml 的兩條 Stage 2 入口都已使用 blank-first/apply；後續 Metadata Audit、Manifest、Stage 2–4 Receipt、Chart 3 與 Builder 讀到的都是本輪回填後的 Fixture。正式 Workflow YAML 本身未修改，Simulation/main workflow mirror SHA 仍一致。
- 新增 simulation-lab/runner/build_stage2_receipt.py：將 populated Fixture、Metadata Audit、44-row Manifest、Observation bundle 的檔案 SHA-256 綁成獨立 Stage 2 receipt；逐列核對商品、來源 URL、交易日、Observation row SHA、Manifest record SHA、回填值及 PENDING/CLOSED 狀態。PENDING row 若沒有有效截圖欄位，不得殘留舊 close／score 或舊顯示值。
- 新增 test_build_stage2_receipt.py，涵蓋 44 列 SHA 綁定、43 verified + 1 pending、manifest record SHA 錯誤、Observation SHA 錯誤，以及 MOVE 待核實列殘留 97.54 時拒絕產生 Receipt。
- 正式入口 CLI 整合測試加入 test_validate_chatgpt_web_observations.py：直接呼叫正式 Validator main，確認它先清空原 Fixture、再驗證 44 列、回填 43 項與一筆 CLOSED，並將新 Fixture 寫回原工作目錄路徑。Run 45779383174 的測試全部 PASS。
- Run 45779383174（Commit 9d9eaf730b8b847fb9bb3c2ed117af868883bf7c）專用 Stage 2 diagnostic 全流程 success；44-row Observation=43 VERIFIED／1 OBSERVED_PENDING_VALIDATION，Manifest=PARTIAL（43／1），Snapshot Audit=PASS（44 metadata/date rows），Stage 2 Receipt=PARTIAL（44 rows、43 verified、1 pending、0 closed）。
- Stage 2 Receipt batch_id：fcb6ae5c1caf8662d37e0d78。Artifact ID：15096998765；Artifact SHA-256：0f24a8c1b3a7e786aa872c9a618a5a1dc2448373116afa29835c5a567b36c0ca。Receipt 綁定 Fixture SHA f8b566aa48cbde8a5aed0df32bf3720aff0f9cf1185648ed4d1837882c2072b8、Audit SHA 7003c76ce0ecd7c01c251205a45b6e98d40853e6b94856ec3722f619f91b907b、Manifest SHA 94be7a7974765a1bb415877037f6a17651c5cf542eff31df207dbde25d70d819、Observation SHA 9bd76c1b0b11392ccb66b4b9cc13f26d3553180cc90850134823439abc7803fc。
- Receipt 明確標記 PARTIAL；唯一待核實仍為 MOVE，原因是當日 Observation bundle 的 Investing.com 歷史頁沒有 2026-11-25 目標列（SOURCE_NO_DATA）。MOVE 顯示待核實，close_value 為 null，舊 screenshot_sha256、user_screenshot_observation、previous_close、OHLC 與舊 note 均未被帶入新 Fixture。
- 同一 Commit 的 TAC isolated simulation lab Run 45779383099：workflow mirror check PASS，compile／靜態檢查 PASS；因提交未包含 [build-tac-report:YYYY-MM-DD]，完整報告建置階段依規則 SKIPPED，未觸發 main/preview 交付。
- 目前 11/26 Sidecar 偵測仍為 0；本輪 43 個可核實值取自同日 direct Investing.com Historical Data page Observation bundle，非 HTTP 403 後猜測或前日 Fixture 值。Playwright 新開頁路徑仍會遇到 Cloudflare 403；正常等待後不完成 challenge 時保留 TOOL_READ_FAILURE，不繞過。
- 正式生產入口已透過既有 Runner 程式完成 blank-first/apply 整合；無需修改 main workflow mirror。仍需注意：本輪只有 43/44 行情 VERIFIED，故 Stage 2 receipt 為 PARTIAL，不能標示 44 項完整通過或 REVIEW_READY。
- 狀態： ZERO_MARKET_INPUT_E2E_PARTIAL_PASS / PRODUCTION_STAGE2_RUNNER_INTEGRATED / 43_VERIFIED_1_PENDING / STAGE2_RECEIPT_SHA_BOUND。


### 2026-11-26｜SIM-1.4 正式規則增補與 SHA 影響測試

- 已將空白行情值起跑、當輪 Observation 回填、正式 Runner blank-first 行為、Screenshot Sidecar 優先、Stage 2 Receipt SHA 綁定、PENDING／CLOSED 狀態及下游凍結正式寫入 SIM-1.4 第 0.5.4 節；本次新增規則明確限定「零行情值」，不要求新聞、行事曆及非行情內容從零重建。
- SIM-1.4 規則檔內容變更會使其 Git blob SHA 改變；但 Builder approval Gate 不綁定一個固定 SIM 規則檔 SHA，而是每輪從目前有效 SIM 文字擷取核准條款，再比對 Builder 精確路徑與 Builder blob SHA。修改 Stage 2 規則不會自行撤銷已核准 Builder。
- 已擴充 test_sim14_builder_approval.py：加入「SIM 規則文字增加 Stage 2 amendment、active_rules_blob_sha 改變，但相同 Builder path/blob SHA 仍為 APPROVED」測試。Run 45779855600 的此項測試 PASS；其餘 Stage 2 bootstrap、direct web blank input、PENDING／CLOSED、Receipt SHA 測試亦 PASS。
- SIM 規則 SHA 更新不等於 Stage 2 Receipt SHA 更新；每輪 Receipt 仍依當輪 Fixture、Audit、Manifest、Observation 的實際內容各自計算 SHA。正式 Builder 核准仍以第 8.1 節核准的 Builder path/blob SHA 為準。


### 2026-11-26｜第七批正式規則與回歸驗收

- SIM-1.4 第 0.5.4 節已正式加入零行情值起跑、blank-first、當輪 Observation 回填、正式入口 screenshot-first、Stage 2 Receipt、PENDING／CLOSED、SHA 凍結及診斷範圍定義。
- 最新 SIM-1.4 blob SHA：daf94617679efa74e39e576442200b90bf1423db。
- Run 45779855600（Commit 9e0bbc963371fef5f650046ab9a057a75e7f68f8）全部步驟 success；空白 Fixture、Web Observation blank-input、PENDING／CLOSED、Stage 2 Receipt SHA、SIM 規則 SHA 更新不撤銷 Builder 核准等測試均 PASS；44 列 Observation／Manifest／Audit／Receipt 與 Artifact 上傳完成。
- 最新 Stage 2 Receipt：PARTIAL；44 rows、43 VERIFIED、1 PENDING、0 CLOSED。batch_id f35f102abeb86cfce389df38；Receipt file SHA-256 f003c61727857f02be376f0e5a5c273ff316a96e3df636e5fb5409af45478924。
- 最新 Artifact：ID 15097976732；SHA-256 3509a25e7b1b291ac2d5b45a83c988a60045476a0f116008e99ef5fbe318de0c。Fixture SHA f8b566aa48cbde8a5aed0df32bf3720aff0f9cf1185648ed4d1837882c2072b8；Manifest SHA 94be7a7974765a1bb415877037f6a17651c5cf542eff31df207dbde25d70d819；Observation SHA 9bd76c1b0b11392ccb66b4b9cc13f26d3553180cc90850134823439abc7803fc；Audit SHA 7003c76ce0ecd7c01c251205a45b6e98d40853e6b94856ec3722f619f91b907b。
- 最新 Fixture 的 stage2_market_bootstrap.preexisting_market_values_used=false；MOVE close_value=null、display／change_display 均為待核實，舊截圖／OHLC metadata 均已清除。唯一 pending 原因仍是當日 MOVE 歷史頁 Observation 為 SOURCE_NO_DATA，且本輪 Sidecar 偵測為 0。
- Run 45779855507 的 TAC isolated simulation lab workflow mirror check PASS，確認 Simulation 與 main 的 tac-simulation-lab.yml blob SHA 都是 0698f88333e29c3b7e86ee74e557fdc14b6ce429；compile／靜態檢查 PASS。未帶 [build-tac-report:YYYY-MM-DD]，因此完整早報建置依規則 SKIPPED。
- 本次修改只在 Simulation branch 的 SIM、Runner、Tests、診斷 Workflow 與專案紀錄；main workflow mirror、main/index.html、正式母版、正式資料及每日關鍵價位程式均未修改。
- **目前結論：** Stage 2 blank-first／apply 已在正式 Runner 入口整合，44 列 E2E 的結構與 SHA 收據流程通過；市場數值為 43 VERIFIED／1 PENDING，故整體仍是 PARTIAL，不得標記 44/44 VERIFIED 或 REVIEW_READY。

### 2026-11-26｜MOVE 延遲發布與 TradingView 唯一備援正式整合

- 使用者確認 MOVE 來源僅保留兩層：Investing.com 歷史數據優先；TradingView ICE:MOVE 唯一備援；兩邊都沒有目標交易日歷史收盤資料時，Close／Change 保持 null，畫面顯示待核實。禁止第三來源、舊值回填、即時報價代替收盤。
- SIM-1.4 新增第 0.5.5 節，明確定義 MOVE 的 SOURCE_UPDATE_PENDING、TradingView 備援核實條件、報告不中斷、單項補查及證據保存；該 MOVE 專用來源契約優先於一般來源限制，不影響其他 43 項。
- browser_verify_market_history.py：Investing.com 目標列缺失或讀取失敗時，MOVE 才開啟 TradingView ICE:MOVE 商品頁；支援 --only risk:move --move-backup-only，供只讀單項備援，不重抓其餘 43 項。TradingView 使用獨立 read_method、TRADINGVIEW_HISTORICAL_PAGE 欄位來源類型及 BACKUP_1 角色。
- validate_chatgpt_web_observations.py：直接 Web Observation 的 MOVE 主來源若缺目標列，會自動執行 TradingView 單列備援；把原 Investing.com 嘗試與 TradingView 備援嘗試合併在同一 Observation，保留兩邊 URL、狀態、頁面標題、標的識別、時間、頁面摘錄與 SHA。Manifest 也保留 evidence_source_url、evidence_source_role、source_attempts、source_read_status、source_page_title 及 source_instrument_identity。
- 測試新增 MOVE 延遲狀態、TradingView 備援成功時 BACKUP_VERIFIED、兩來源均無目標列時空值、欄位來源類型、primary／backup attempt history 等回歸測試；Stage 2 diagnostic workflow 已納入 test_stage2_field_provenance.py。
- 實際驗收 Run 45785278030（Commit f9e68f669592a6751a7785fd4d3ada72477e9671）成功；同一 Commit 的 isolated simulation lab Run 45785278199 success、workflow YAML lint Run 45785278396 success。44-row Stage 2：43 VERIFIED、1 SOURCE_UPDATE_PENDING；Fixture、Manifest、Receipt 均維持 PARTIAL，無舊行情值回填。
- 本輪 MOVE 目標交易日為 2026-11-25。Investing.com 歷史頁可讀但尚無 11/25 目標列；TradingView ICE:MOVE 商品頁 HTTP 200，商品身分確認為 ICE:MOVE，但頁面只顯示當下延遲報價／區間摘要，沒有 11/25 歷史列。頁面顯示的即時摘要數字沒有寫入 Close／Change；MOVE 兩欄均為 null，顯示待核實。
- Stage 2 Receipt：PARTIAL，44 rows、43 verified、1 pending、0 closed；batch_id 3e874d6c2398fcbd62170a2c；Receipt SHA-256 d35561a7255b61a4b33c92c0b7fbc37f141e2515f379decbe7411a24ee2760e5。Fixture SHA df37dbd8cd816457cbb76b0a7a086b4fa6769f5e68aefb87439b47e13ea7978c；Audit SHA 7003c76ce0ecd7c01c251205a45b6e98d40853e6b94856ec3722f619f91b907b；Manifest SHA 2e822a52f663e7fc2d2d1caf2617654f539e77123eb8fab93db0c604c959abbd；Observation SHA 9e7f6d2c1bb01bcc1901b400c91de5a65bfb9d09e77296636f25b9d0d603ccba。
- Artifact ID 15100326736；Artifact ZIP SHA-256 76cd233bd6740cacc13fed4bad4456985252b5e4db7c0e455388ce12282faf99。Workflow： https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/45785278030
- 本次只修改 Simulation branch 的 SIM、Runner、Tests、Stage 2 diagnostic workflow 與專案紀錄；未改 main/index.html、正式母版、main workflow mirror、正式資料或每日關鍵價位模組。未觸發正式早報建置、main/preview 發布或首頁更新。
- 狀態： MOVE_INVESTING_PRIMARY_TRADINGVIEW_ONLY_BACKUP / MOVE_NO_DATA_STAYS_BLANK / 43_VERIFIED_1_UPDATE_PENDING / STAGE2_PARTIAL_RECEIPT_PASS。