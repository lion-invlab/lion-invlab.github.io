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

1. **保留舊 Run，不得原地修補。** 既有 `TAC-2026-11-27-45937649928-1` 的 Stage 1 governance pin 是舊版提交 `c337b44`，早於六階段 WR preflight 強制規則；其 Stage 1–4 receipts 沒有新制要求的 WR 證據，因此不能接續新規則下的 Stage 2–6。舊 Run 與舊 observation／editorial 全部保留作歷史證據，不回填或偽造 worker attestation。
2. **建立受控替代 Run。** 只有 `workflow_dispatch mode=recover` 可在確認當日僅有一個未交付舊 Run、且沒有 Stage 5／6 或公開 Preview 成果時，建立新 Run；新 Run 明確記錄 `supersedes_run_id`，舊 Run 不刪除、不覆寫。若已有多個 Run 或任何已交付成果，停止並人工釐清。
3. **重新執行 Stage 2。** 既有 11/27 observation 缺少 `stage2_wr_sha256`，不能沿用或事後補簽。Stage 2 擷取工作者必須先完整讀取本版 `STAGE_2_MARKET.md`，重新讀取當日有效截圖／Investing.com Historical Data，並在 44 列 observation bundle 根層寫入精確 `stage2_wr_sha256`。當日截圖僅當天有效；沒有有效截圖就重新讀取來源，不得沿用舊截圖。
4. **Stage 3–4 重新綁定同一 Run。** Stage 3 讀取該新 Run 的行事曆；Stage 4 必須先讀 capture receipt 內完整 Stage 4 WR，再根據新 research bundle 重寫 editorial，寫入精確 `stage4_wr_sha256`。舊 `report-content-2026-11-27.json` 不得直接送入新 Run。
5. **完成 Stage 5–6。** 使用核准 Builder 產生 11/27 Preview，通過必要 QA，部署後遠端回讀 HTML／QA／delivery 三檔並驗證公開 URL。這只交付審核版，不更新正式首頁或歷史封存。
6. **最後才驗收排程。** 確認 Stage 2 observation 先於 Capture workflow 到位，Stage 4 editorial 先於 Stage 4–6 continuation 到位；以同一 Run 串接，不另造第二條生產入口。

每完成一項，只回頭檢查：**是否讓當日審核版更接近完成？是否有新規則反而阻止產報？** 若有，移除不必要步驟，不再擴增關卡。

每完成一項，只回頭檢查：**是否讓當日審核版更接近完成？是否有新規則反而阻止產報？** 若有，移除不必要步驟，不再擴增關卡。

## 六、明確不做

- 不再建立多層 handoff receipt、重複 SHA 綁定、過度細分 Gate。
- 不因單一行情缺失而中止其他行情、新聞與組版工作。
- 不把 CI 單元測試成功當成早報 E2E 成功。
- 不修改 Simulation 分支。
- 未經使用者核准，不更新正式首頁與歷史封存。
