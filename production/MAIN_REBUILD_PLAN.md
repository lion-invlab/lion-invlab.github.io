# TAC Main 早報重建計畫 v2.4（週二至週六製作週期）

**更新日期：2026-11-27**  
**唯一目標：每天穩定產出當日審核版；先完成早報，不把行情擷取變成資料治理工程。**

Simulation 分支與 SIM-1.4 僅供規格參照，禁止修改。Main 可重建；正式首頁 `index.html` 與正式歷史封存仍須使用者明確核准後才可更新。

## 一、每日工作流程

`Stage 1 建立當日工作資料 → Stage 2 行情 → Stage 3 行事曆 → Stage 4 新聞與分析 → Stage 5 組版與必要 QA → Stage 6 審核版交付`

| 階段 | 執行責任 | 工作與交付 |
|---|---|---|
| 1. 建立工作資料 | Main Runner | 鎖定台灣報告日、目標交易日、週一／週二至週五母版（週六製作週一早報）；建立當日空白資料與唯一 Run。 |
| 2. 行情擷取 | ChatGPT 讀來源；Runner 寫入 | 44 項行情。當日有效截圖優先；其餘直接讀 Investing.com Historical Data。最多四頁並行。Runner 將當日資料接入本 Run，回填行情並產生一份快照。 |
| 3. 行事曆 | Main Runner | 讀取當週／上週既有行事曆與財報資料，投影到報告；不在此階段改寫資料庫。 |
| 4. 新聞與分析 | ChatGPT | 5 則全球焦點、10 則市場熱門、三段總結、市場情緒與必要分析；只使用本 Run 行情與可追溯新聞。 |
| 5. 組版與 QA | Main Builder | 使用核准母版產生 HTML；只做會阻止錯誤交付的必要檢查：資料日期、欄位完整性、DOM／連結、版面是否破版。 |
| 6. 審核版交付 | Main Runner | 產出 `preview/YYYY-MM-DD-review.html` 及必要 QA 紀錄，確認 Preview 已部署可讀。等待使用者核准；未核准不得更新首頁或封存正式版。 |

## 一之一、六階段開工前強制讀取各自 WR

Stage 1–6 每個 Runner 入口均須先完整讀取本階段自己的 WR，再執行任何本階段工作。Stage 2–6 另核對 Stage 1 鎖定的 WR Git blob SHA；缺檔、空檔、讀取失敗、未鎖定或版本不符即停止該 Stage。每階段既有 receipt 記錄一次 `wr_preflight` 證據，不另增重複 Gate。Stage 4 的 ChatGPT 編輯工作者必須先讀取 capture receipt 中完整 `stage4_work_instructions.full_text`，並在編輯 JSON 回填精確 `stage4_wr_sha256`；Runner 驗證完整 handoff 文字與 SHA 後才可合併內容。

## 二、行情擷取的簡單規則

1. 行情共 44 項：17 全球指數、11 檔 S&P 500 產業 ETF、3 項美債殖利率、6 項匯率、4 項商品、3 項風險指標；FedWatch 另列。
2. 使用者當天提供的截圖優先採用，視為該欄位當日報價；截圖只在當天有效，絕不跨日沿用。報告不得出現「依你的截圖」等內部作業描述。
3. 沒有截圖的欄位，直接開啟對應 Investing.com Historical Data 頁面讀取目標日期資料列；最多四頁並行。不得用搜尋摘要代替歷史表格。
4. 不繞過 Cloudflare。若頁面或表格無法讀取，標示 `TOOL_READ_FAILURE`；頁面可讀但沒有目標日期資料，標示 `SOURCE_NO_DATA`。只有官方市場日曆能證明休市時才標 `MARKET_CLOSED`。
5. 只接受報告日對應的目標交易日資料。週二至週五通常以前一日為目標；週六製作的隔週一報告以前一週五為目標。各市場分別判斷，不可用美股休市推定全球市場休市。
6. 不補舊行情、不推估缺失值、不把未核實值寫成已確認事實。部分項目未取得，不應阻止其他已完成資料繼續產報。
7. 當日觀察資料可先存在日期輸入檔；進入 Run 時必須核對報告日、交易日、44 個商品識別及擷取時間，再複製到該 Run。Run 內保留一份原始 observation、一份最終快照即可；不再要求多層 handoff、context hash 鏈或重複 receipt。快照可記錄單一 SHA 供回查。

## 三、資料與職責邊界

- **ChatGPT：** 讀取網頁／截圖、整理新聞、撰寫市場分析；不自行宣稱網頁讀取成功。
- **Main Runner：** 建立 Run、匯入並檢查資料日期與商品清單、回填快照、呼叫 Builder、部署 Preview。
- **行事曆 updater：** 唯一更新 `data/calendar/weeks/`；早報流程只讀。
- **Chart 3：** ALFRED 四序列由 Chart 3 任務唯一更新；S&P 500 現金指數收盤由 Main Stage 2 唯一擷取與寫入，沿用既有 handoff／append writer 追加 `data/tac-chart3/sp500_daily_increment.jsonl`，再由 S&P 500 merge workflow 更新 compact histories。ALFRED 與 S&P 500 merge workflows 共用 `tac-chart3-data-maintenance` concurrency group；Main Stage 2 ledger／Run receipts 提交具 rebase retry，Stage 4–6 交付與 Chart 3 資料寫入共用鎖。未核實行情不寫入、不另抓第二份 S&P 500 報價，也不得阻擋其他早報工作。
- **正式首頁：** 只有使用者核准後才能更新 `index.html` 或正式封存。

## 四、資料狀態與顯示

每項行情必須有值及來源，或有清楚狀態：`VERIFIED`、`MARKET_CLOSED`、`SOURCE_NO_DATA`、`TOOL_READ_FAILURE`。不得為了湊齊 44 個數字而填入過期報價。MOVE 截圖僅當天有效；沒有當天資料就如實標示，不可改用未核准來源。

視覺規則維持既有 TAC 規格：白底紅色主標題；上漲紅色、下跌綠色；總結與市場情緒為視覺重點；中文金融術語優先。

## 五、當前執行順序（2026-11-27 狀態校正）

1. **11/27 審核版已依使用者明確核准正式發布。** 使用者於 2026-11-27 16:19（台灣時間）指示「先把審核版上傳首頁」。正式發布 commit `ed7bd1e3d51865afa789af3bb2df8787550575f0` 將 `preview/2026-11-27-review.html` 原樣複製至 `index.html`；兩者 Git blob SHA 均為 `d34fec01d0f9735e62f5b0c67bfe94a2618fb4f5`。Pages run `45966951824`、Archive run `45966951834` 均成功；前一版 11/26 首頁 blob `032090e047a363e7654e36c12adadbe859666bc2` 已由 Archive workflow 核對，未重複封存。`homepage-publication-lock.json` 現為 `APPROVED_PUBLICATION`，previous_homepage 指向 11/26。中間曾因不完整的記憶查詢產生暫時回復 commit `f7f48ddc47aaf2829a0025c4fd21c2caf6641fc3`；已由上述明確核准發布 commit 覆蓋，**目前 11/27 正式首頁正確，不得回退**。
2. **舊 Run 僅作歷史證據。** `TAC-2026-11-27-45937649928-1` 建立時使用舊 governance pin，缺少新制 Stage WR worker attestation；不得把新規則回填至舊 receipt，也不得再執行舊的 MOVE holiday resume job。舊 observation 與 editorial 不得作為新 Run 的合格輸入。
3. **11/27 新 Run 已建立，但不是完整 E2E。** `TAC-2026-11-27-45976396528-1` 的 `supersedes_run_id` 指向舊 Run `TAC-2026-11-27-45937649928-1`；但 GitHub Actions 實際事件為 `push`，不是規範要求的 `workflow_dispatch mode=rerun`，不得把它記成合規 rerun 或完整 E2E。此 Run 的 Stage 2 為 `PARTIAL`：44 項中 26 VERIFIED、17 CLOSED、1 PENDING（CNN Fear & Greed，`SOURCE_NO_DATA`）；Stage 3 為 PASS。S&P 500 現金指數目標日 2026-11-26 為美國感恩節休市，Chart 3 未追加當日資料。Stage 4 編輯內容、Stage 5、Stage 6 均未完成。Run pinned main commit 為 `f6aa1f7626699ca6054b66a97028bddcde70cd25`；後續 Stage 5／6 規範與 Runner 已變更，舊 Run 不得跨版本續跑或回填新規則。
4. **Stage 5／6 已修正兩項 Gate 矛盾。** 情境分析只有在六領域掃描完整、findings 為空且有具體 `no_material_change_note` 時可標 `NOT_APPLICABLE`；有任何 finding 則保守要求基準／風險／嚴重三情境。Stage 2 非 PASS、仍有 pending_rows 或 fixture pending_items 時，Stage 5 必須標 `PARTIAL`，Workflow 保留 Run 內證據並略過 Stage 6，不可寫入 main/preview。相關 commits：`75c4d68`、`eb488f3`、`0bc0dd3`、`f080ec1`、`ba4322d`。Main push validation Run `46001434146` 對 commit `ba4322db2cd4ff5fe4a204e56deb2eef3dbb529e` 已 SUCCESS；其中 Stage 5 情境 QA 新增測試及現有 deterministic tests 通過。這是程式驗證，不是正式行情 E2E。
5. **Builder exact-SHA 核准已完成，不再是 Stage 5 阻塞。** Main Builder 現行 blob SHA `89cedbb36ec75628c813291adf1bd025c589266e`，`production/config/builder-approval.json` 的 `APPROVED_MAIN`、`approved_by_owner=true` 及 `approved_builder_blob_sha` 均與此 SHA 一致；核准紀錄明確對應此版本。此核准不代表真實行情 E2E 或 Stage 5／6 生產驗收已通過；任何 Builder 程式變更仍須重新核准 exact blob SHA。
6. **下一個正常排程 E2E 目標為 2026-11-28（週六製作、report_date=2026-11-30，行情基準日為週五 11/27）。2026-11-30（週一）不製作早報；若週六流程未完成，下一個正常製作日為 2026-12-01（週二，report_date=12/01，行情基準日為週一 11/30）。** 04:35 台灣時間行事曆資料庫更新；04:45 Stage 1 建立唯一 Run 並鎖定 Monday mother／governance；05:00 Stage 2 worker 啟動正式收盤擷取；05:15 為 observation handoff 目標；05:20 為 Stage 1–3 Capture 目標；05:30 為完整審核版交付目標。對應 America/New_York：15:35、15:45、16:00、16:15、16:20、16:30 ET。Chart 3 監控任務 05:30 台灣時間獨立執行。三個排程均已啟用：行事曆 04:35、Main Stage 2–6 05:00、Chart 3 05:30。Main Workflow schedule 是唯一 Stage 1 啟動入口；Stage 2 只提交 observation，不另建 Run。未完成同一 Run Stage 1–6 真實 E2E 前，不宣稱新制正式上線。

每完成一項，只回頭檢查：**是否讓下一個工作日審核版更接近完成？是否有新規則反而阻止產報？** 若有，移除不必要步驟，不再擴增關卡。
## 五之一、正式首頁發布鎖（2026-11-27 已啟用）

- Builder 的 `approved_by_owner=true` 只代表 Builder exact-blob 核准，不等於報告發布核准；`REVIEW_READY` 與 Stage 6 DELIVERED 也不等於首頁發布核准。
- `production/config/homepage-publication-lock.json` 是正式首頁唯一發布狀態；目前為 `APPROVED_PUBLICATION`，綁定 11/27 report_date、Preview blob、index blob 及 11/26 previous_homepage 快照。
- Pages workflow 與 Archive workflow 均先執行 `verify_homepage_publication_lock.py`；首頁必須與獲核准 Preview 位元組完全相同。未核准的 index 變更無法部署。
- Archive 不再每日自動執行；只在明確 `[publish-tac-report:YYYY-MM-DD]` 且 lock 核准時執行，封存來源只能是 `previous_homepage` 指定的精確 blob。
- 正式首頁發布後，Stage 6 仍只交付審核版；沒有新的使用者核准，不得改動下一個報告日的首頁。

## 六、明確不做

- 不再建立多層 handoff receipt、重複 SHA 綁定、過度細分 Gate。
- 不因單一行情缺失而中止其他行情、新聞與組版工作。
- 不把 CI 單元測試成功當成早報 E2E 成功。
- 不修改 Simulation 分支。
- 未經使用者核准，不更新正式首頁與歷史封存。


## 週二至週六正式製作規則（2026-11-27 使用者核准）

| 台灣製作日 | report_date | trading_date | 母版 | 新聞窗口 |
|---|---|---|---|---|
| 週二 | 當日週二 | 週一 | Weekday | 週一 12:00 起至製作截點 |
| 週三 | 當日週三 | 週二 | Weekday | 週二 12:00 起至製作截點 |
| 週四 | 當日週四 | 週三 | Weekday | 週三 12:00 起至製作截點 |
| 週五 | 當日週五 | 週四 | Weekday | 週四 12:00 起至製作截點 |
| 週六 | 隔週一 | 週五 | Monday | 週五 12:00 起至 Stage 4 research bundle 建立當下 |

週六製作時 production_date 與 report_date 必須分離；Run、Preview、母版選擇及正式發布鎖以 report_date 為準。週六、週日的重大新聞如需置換，只能人工明確決定；自動流程不得覆寫已交付版本。排程的 New York BYDAY 為 MO–FR，台灣時區對應 Tue–Sat。


## 七、2026-11-28 Main 重建分支最新狀態（取代前述過期排程／驗收描述）

1. **Stage 2 日期綁定收盤等待已修正。** 原 Workflow 只比較當下 New York HHMM 與 16:00，沒有使用 Run 的 `trading_date`；隔日 Recover 因而可能多等至下一個交易日 16:00。重建分支已改為讀取同一 Run 的 `run-context.json`，等待該 Run 交易日 16:00 America/New_York；若目標收盤時間已過則立即進入 Observation handoff polling。新增五項單元測試及 Workflow 結構斷言。程式提交：`63466c1677c7b86f5bfd10e98ff1fccd90f9f348`。
2. **最新程式驗證已通過。** GitHub Actions Run `46120016304`（commit `63466c1`）SUCCESS；Stage 2／pre-build deterministic suite 106 tests PASS（含五項新收盤等待測試），Builder／earnings suite 52 tests PASS，isolated candidate Builder、雙母版 DOM contract 亦 PASS。這是重建分支程式驗證；push validation 中正式 Stage 1、2/3、4–6 production jobs 均 SKIPPED，不能記為真實行情 E2E。
3. **11/28 當日手動啟動 Run 尚未完成。** Main workflow_dispatch Run `46108156744` 建立 Run `TAC-2026-11-30-46108156744`，Stage 1 PASS、Stage 2 READY；Stage 2/3 job 因 15 分鐘內沒有收到該 Run 的 Observation bundle 而失敗，Stage 3–6 未執行。其前一 Run `TAC-2026-11-30-46105765414` 已被 supersede，資料不得跨 Run 沿用。
4. **真正原因是跨平台喚醒缺口，不是行情讀取失敗。** ChatGPT Stage 2–6 排程已於當日 05:00 台灣時間執行並因當時尚無 Stage 1 Run 而 DEFERRED；12:34 才手動建立新的 Stage 1 Run，GitHub Actions 不會自動再次喚醒 ChatGPT Automation。Automation 仍啟用，下一次排程為 2026-12-01 05:00 台灣時間。不得為解決此缺口擅改排程；晚到的手動 Recover 必須先明確啟動該 Automation 的單次執行，再以 `workflow_dispatch mode=recover` 沿用同一 Run。這次尚未啟動正式擷取或 Recover。
5. **未完成事項與保護範圍。** 仍需解決／驗收晚到 Recover 的 worker 喚醒操作，並完成同一 Run Stage 1–6 真實 E2E，確認 Stage 6 三檔 Preview、Pages 部署及公開 URL 驗證。重建期間未修改正式 `main`、正式首頁／封存、排程或 Simulation；未產生本次 Run 的 Stage 2 Observation，也未宣稱 11/30 審核版完成。
6. **下一個正常排程日為 2026-12-01（週二）。** 正常路徑仍是 04:35 行事曆資料庫更新、04:45 Stage 1、05:00 ChatGPT Stage 2 worker、其後 Stage 3–6 同一 Run 串接。11/28 修正目前只在重建分支，未切換至正式生產。
