# TAC Main 早報重建計畫 v2.1（簡化版）

**更新日期：2026-11-27**  
**唯一目標：每天穩定產出當日審核版；先完成早報，不把行情擷取變成資料治理工程。**

Simulation 分支與 SIM-1.4 僅供規格參照，禁止修改。Main 可重建；正式首頁 `index.html` 與正式歷史封存仍須使用者明確核准後才可更新。

## 一、每日工作流程

`Stage 1 建立當日工作資料 → Stage 2 行情 → Stage 3 行事曆 → Stage 4 新聞與分析 → Stage 5 組版與必要 QA → Stage 6 審核版交付`

| 階段 | 執行責任 | 工作與交付 |
|---|---|---|
| 1. 建立工作資料 | Main Runner | 鎖定台灣報告日、目標交易日、週一／平日母版；建立當日空白資料與唯一 Run。 |
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
5. 只接受報告日對應的目標交易日資料。週二至週五通常以前一日為目標；週一以前一週五為目標。各市場分別判斷，不可用美股休市推定全球市場休市。
6. 不補舊行情、不推估缺失值、不把未核實值寫成已確認事實。部分項目未取得，不應阻止其他已完成資料繼續產報。
7. 當日觀察資料可先存在日期輸入檔；進入 Run 時必須核對報告日、交易日、44 個商品識別及擷取時間，再複製到該 Run。Run 內保留一份原始 observation、一份最終快照即可；不再要求多層 handoff、context hash 鏈或重複 receipt。快照可記錄單一 SHA 供回查。

## 三、資料與職責邊界

- **ChatGPT：** 讀取網頁／截圖、整理新聞、撰寫市場分析；不自行宣稱網頁讀取成功。
- **Main Runner：** 建立 Run、匯入並檢查資料日期與商品清單、回填快照、呼叫 Builder、部署 Preview。
- **行事曆 updater：** 唯一更新 `data/calendar/weeks/`；早報流程只讀。
- **Chart 3：** 保留既有 FRED／ALFRED 更新流程。S&P 500 日資料只在來源已核實且寫入規則確認後更新；不可因此阻擋早報。
- **正式首頁：** 只有使用者核准後才能更新 `index.html` 或正式封存。

## 四、資料狀態與顯示

每項行情必須有值及來源，或有清楚狀態：`VERIFIED`、`MARKET_CLOSED`、`SOURCE_NO_DATA`、`TOOL_READ_FAILURE`。不得為了湊齊 44 個數字而填入過期報價。MOVE 截圖僅當天有效；沒有當天資料就如實標示，不可改用未核准來源。

視覺規則維持既有 TAC 規格：白底紅色主標題；上漲紅色、下跌綠色；總結與市場情緒為視覺重點；中文金融術語優先。

## 五、當前執行順序（2026-11-27 狀態校正）

1. **保留 11/27 已交付成果。** `preview/2026-11-27-review.html`、QA 與 delivery 三檔均存在；QA 為 `REVIEW_READY`，四類 QA 均 PASS，Pages 公開 URL 回讀 HTTP 200 且 SHA 一致。正式首頁與歷史封存未修改。此成果已交付，不得重做、覆蓋或另建同日 Run。
2. **舊 Run 僅作歷史證據。** `TAC-2026-11-27-45937649928-1` 建立時使用舊 governance pin，缺少新制 Stage WR worker attestation；不得把新規則回填至舊 receipt，也不得再執行舊的 MOVE holiday resume job。舊 observation 與 editorial 不得作為新 Run 的合格輸入。
3. **保留受控復原機制，但只用於未交付日期。** `workflow_dispatch mode=recover` 僅可在當日恰有一個舊 Run、且沒有 Stage 5／6 receipt 或公開 Preview 三檔時建立替代 Run；新 Run 記錄 `supersedes_run_id`，舊 Run 完全保留。多個舊 Run 或已有交付成果時停止，不自動覆蓋。
4. **補齊下一個工作日的 Stage 2 輸入鏈。** 新 observation bundle 必須先由擷取工作者完整讀取本版 `STAGE_2_MARKET.md`，並在根層寫入精確 `stage2_wr_sha256`；再由 Main Capture workflow 建立 Stage 1–3。舊日期 observation 不得沿用或事後補簽。
5. **以 2026-11-30（週一）作下一次新制真實 E2E。** Stage 1 鎖定 Monday mother 與 governance；Stage 2 完成 44 項與 FedWatch；Stage 3 唯讀投影 W48／W47；Stage 4 編輯者讀取 capture receipt 的完整 Stage 4 WR 並回填 `stage4_wr_sha256`；Stage 5 Builder／必要 QA；Stage 6 交付 Preview 三檔並遠端回讀。
6. **排程整合最後驗收。** 以 America/New_York 時區統一 DST：行事曆 15:35 ET（台灣冬令 04:35／夏令 03:35）；既有 Main Stage 2–6 喚醒任務 16:00 ET（台灣冬令 05:00／夏令 04:00）先擷取 44 項及 FedWatch，再等待 Main Capture；Main Capture 16:30 ET（台灣冬令 05:30／夏令 04:30）；Chart 3 16:30 ET 獨立執行。Stage 1 cutoff 固定為 16:25 ET，台灣時間隨 DST 為 05:25／04:25。Stage 2 只提交 observation，不觸發 Run；Main Workflow schedule 是唯一 Stage 1 啟動入口。未完成真實 E2E 前，不宣稱新制已正式上線。

每完成一項，只回頭檢查：**是否讓下一個工作日審核版更接近完成？是否有新規則反而阻止產報？** 若有，移除不必要步驟，不再擴增關卡。
## 六、明確不做

- 不再建立多層 handoff receipt、重複 SHA 綁定、過度細分 Gate。
- 不因單一行情缺失而中止其他行情、新聞與組版工作。
- 不把 CI 單元測試成功當成早報 E2E 成功。
- 不修改 Simulation 分支。
- 未經使用者核准，不更新正式首頁與歷史封存。
