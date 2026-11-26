# TAC 投資早報 R3｜MASTER WORK RULES

版本：1.1（2026-11-26）
正式分支：main
規則來源：SIM-1.4 技術規範（來源 branch `simulation/tac-process-lab-2026-11-06`，來源 WR SHA `d60965f0a61159dd8a94c31d7a7f2b6d083e6363`）
main 唯一生產規範：本文件；六份 Stage WR 與 contracts 為本文件的執行附件。Simulation 原始檔只讀，不作執行依賴。

## 1. 核心裁決
1. 使用者當次指示優先。2026-11-26 使用者明確指定：**main 母版以 Simulation SIM-1.4 baseline 雙模板為準；main 舊母版及舊流程可棄用。**
2. 新正式母版唯一來源：
   - `production/templates/monday-mother-template.html`，blob SHA `710c944205ee05a86599ef5cd869f26c4a9ebde1`
   - `production/templates/weekday-mother-template.html`，blob SHA `ff051c0cd22cf9267420c41e3952fa3178f0e45d`
   - 唯一 Manifest：`production/config/mother-template-manifest.json`
   - 唯一詳細 DOM／互動／視覺驗收：`production/contracts/MOTHER_TEMPLATE_QA.md`
   上述模板及 QA 契約已逐位元從 SIM-1.4 baseline 複製至 main。舊 `母版專區/`、根目錄 Manifest、舊 WR、舊 layout QA 不再是新 Pipeline 的規則或母版來源；可保留歷史檔案，但不得被新 Runner 引用。
3. SIM-1.4 詳細技術原文保存在 `production/reference/SIM-1.4_SOURCE_BASELINE.md`，blob SHA 來源 `d60965f0a61159dd8a94c31d7a7f2b6d083e6363`。本文件將其轉換為 main 生產責任；SIM 原文中的 Simulation-only 分支限制不適用 main，但資料品質、欄位、Stage 定義、來源政策、母版規格及 QA 原則保留。
4. main 舊生產入口及 Workflow 不得成為新系統的第二入口。完成切換前先隔離／停用衝突觸發；不刪除歷史證據，不修改 Simulation。
5. 唯一正式入口：`.github/workflows/tac-production.yml`。`capture` 負責 Stage 1–3 並產生精確 Run handoff；`build` 只接受同一 Run 的 Stage 4 編輯內容，再執行 Stage 4–6。Python Stage Runner 是 Workflow 的執行模組，不另設第二個排程入口。未完成編輯內容自動交接與真實 E2E 前不得宣稱可全自動生產。

## 2. 唯一每日流程
Stage 1 基準與母版鎖定 → Stage 2 44 項行情及獨立 FedWatch → Stage 3 行事曆與財報 → Stage 4 新聞與市場分析 → Stage 5 唯一 HTML Builder 與 QA → Stage 6 main/preview 審核版交付與驗證。
六階段是同一條流程，不是六次獨立審批。每階段保留必要輸入、輸出與交接，不重複建立等價收據或重抓已鎖定資料。

## 3. 唯一正式母版規則
- 週一使用 Monday template；週二至週五使用 Weekday template；週末不自動製作。
- 母版 SHA 必須與新 Manifest 一致；不符即停止，不 fallback。
- Builder 使用真正 DOM parser，只能更新核准槽位；不得以 regex／字串切片改 HTML。
- 母版 CSS、JS、DOM、互動、響應式、字體、顏色、間距不得由 Builder 注入或重建。
- 上漲／正值紅色，下跌／負值綠色。
- 不得重新加入已刪除的「關鍵重點」膠囊。
- 五層市場深度解析槽位已存在於兩份 SIM-1.4 母版，固定順序政治地緣、政策產業、宏觀、金融市場、機構資金與策略。
- 工具欄提示泡泡在首次捲動／觸控移動時立即隱藏；呼吸燈依母版行為獨立持續。

## 4. Stage 2 行情核心規則
- 固定 44 項：全球主要市場 17（含 SOX）、11 大產業 ETF 11、公債殖利率 3、外匯 6、能源及貴金屬 4、風險情緒 3（VIX、MOVE、CNN Fear & Greed）。FedWatch 獨立，不計入 44。
- 使用者提供且能辨識商品、日期及數值的截圖優先於全部 44 項的網頁讀取，不限 MOVE。已提供欄位直接採用，不重抓、不覆蓋；缺欄才補讀。
- 未由截圖提供的欄位，直接用瀏覽器開啟指定 Investing.com 商品 Historical Data 頁，讀取實際歷史表格及目標交易日列。不得以搜尋摘要、第三方 API、Yahoo 或其他來源替代指定的 Investing.com 首選；不得繞過 Cloudflare。
- 同一批最多 4 個不同歷史頁面並行（concurrency=4）；每頁獨立核對標的、日期、欄位、收盤口徑及 Observation。不得藉提高並行數規避網站限制。
- 已核實值立即鎖定；下游 Stage 3–6 唯讀。不得重抓已鎖定項目。
- Stage 2 每輪先 blank-first 清除 Fixture 中所有舊行情值、舊 Observation、舊截圖證據及舊時間戳，再以當輪有效截圖／Observation 回填。不得沿用前輪 fixture 報價。
- 狀態至少區分 VERIFIED、BACKUP_VERIFIED、PENDING、MISSING、CLOSED、NOT_APPLICABLE、NOT_TESTED、TOOL_READ_FAILURE、SOURCE_NO_DATA；語意不得混淆。PENDING 不可造成整個流程崩潰，亦不可視為成功。
- 44 項每項必須有值或明確狀態；單項缺漏不得阻止無依賴項目及其他階段繼續。未核實值不得作為確定事實。
- Stage 2 同步將已核實 S&P 500 現貨正式收盤寫入既有 `data/tac-chart3/sp500_daily_increment.jsonl`，遵守現有 append／SHA／防重契約；不可另抓第二份 S&P500 報價。

## 5. Stage 3 行事曆／財報
- 唯一資料來源為 `data/calendar/weeks/YYYY-Www.json`；早報嚴格唯讀。
- 工作日 04:35 行事曆排程為 JSON 唯一 writer；Stage 3 不得修補、merge、upsert 或回寫。
- Stage 3 以 Stage 1 鎖定的同一 main commit 讀取本週及前一週 JSON，以完成跨週來源收據；只有週一將上週事件投影至可見回顧區塊，週二至週五不呈現上週回顧。
- 財報 EPS 與 Revenue 分開選源：Yahoo Finance Average Estimate 第一順位；缺值／不可讀／期間不符依序 Investing.com、LSEG I/B/E/S、FactSet Estimates。各指標取得第一個可用平均預期後停止該指標搜尋。
- 已公布事件必須顯示實際值、共識及判讀；財報另呈現 EPS／Revenue 與預期比較及股價反應。資料不足如實標示。

## 6. Stage 4 新聞與分析
- Capture 的 Stage 3 後自動產生 `stage4-research-bundle.json`，彙整完整 44 項行情／來源狀態、未核實列、FedWatch、當週／上週行事曆與財報、Stage 1–3 receipts、所有輸入 SHA，以及使用者截圖 sidecar／圖片證據 SHA。
- 編輯內容必須綁定同一 Run 的 `run_id`、`market_snapshot_sha256` 與 `research_bundle_sha256`；Stage 4 與 build workflow 逐一驗證，禁止跨 Run 或使用過期行情。
- 全球焦點新聞 5 則；市場熱門頭條 10 則；核對原始發布時間、時區、URL 與共同時間窗口。
- 總結小卡、五層深度解析、盤面觀察重點分層，不互相複製。
- 五層固定順序：政治與地緣政治；政策傳導與企業／產業鏈；宏觀經濟；金融市場定價／情緒／風險；機構資金動向與投資策略。
- 每日完成六領域政治掃描；無重大變化可明確寫無重大已核實變化，不硬湊。
- 策略必須有行動、觸發條件、風險、失效條件；事實、推論、情境與策略分開。
- 總結及五層文章內部來源證據完整保存，但母版指定可見區域不得顯示來源列表；新聞、行情、商品、債券、匯率、行事曆等原有來源顯示保留。
- 總結／五層文字局部修正使用 DOM 局部更新器；不重跑行情、行事曆、新聞或完整 Builder，並保留非目標 DOM 指紋。

## 7. Stage 5 Builder 與 QA
- Builder 只接受同一 Run 的 Stage 1–4 輸出、PASS 的 pre-build receipt、正式 Manifest、QA Contract 與 Stage 1 governance SHA snapshot；main Builder 必須通過 exact blob SHA owner approval。
- 目前 SIM-1.4 核准 Builder 的來源 SHA 為 `6bf6eb2f5ae29774addf696c541c5b806953c7a3`，但其路徑與執行環境仍是 Simulation 專用；main 必須先完成路徑／依賴適配、測試與使用者核准前的技術驗證，不得直接把該 SHA 宣稱為 main Runner 已可用。
- QA 四類：資料／內容、HTML 結構、視覺與互動、Run／交付整合。只跑必要且有區別的檢查，不無限加 Gate。
- 未測試標 NOT_TESTED；不把缺值變成 0 或虛構成功。必要 Gate FAIL 不得 REVIEW_READY；非核心欄位缺漏可 PARTIAL 並繼續可完成工作。

## 8. Stage 6 審核版交付與正式發布
- 審核版三檔：`preview/YYYY-MM-DD-review.html`、`.qa.json`、`.delivery.json`。
- 寫入前後僅允許日期化三檔；HTML bytes 不得重組；QA sidecar 綁定來源與 Builder provenance；delivery receipt 記錄 SHA、Run、attempt、commit。
- 寫入 main 後遠端回讀三檔，核對 Git blob SHA／SHA-256；使用既有 Pages workflow 部署並實際驗證公開 URL。
- 審核版交付不等於正式發布。只有使用者另行核准明確日期／版本後才更新 `index.html` 並封存 history。
- 舊 `archive_index.yml` 自動封存與新核准流程衝突，正式切換前必須整併／停用自動封存觸發，防止未核准封存或錯誤日期封存。

## 9. Chart 3 與資料寫入權
- 正式 Chart 3 資料路徑為 `data/tac-chart3/`，不可另建 `data/chart3/`。
- Stage 2 是 S&P 500 每日增量唯一早報寫入者；Chart 3 FRED/ALFRED 既有更新與 S&P500 merge workflow 必須避免重複寫入同一資料，需先明確拆分責任。
- Calendar updater 是週 JSON 唯一 writer；Stage 3 唯讀。
- Stage 5 是本次 HTML 唯一 writer；Stage 6 是交付 sidecar 唯一 writer。

## 10. Run、恢復與效率
- 每次唯一 Run ID，綁定 report_date、Asia/Taipei、git SHA、規則／Manifest／母版／QA SHA。
- 同一 report_date 不可有兩個並行正式 Run。
- 每個 Stage 完成即保存輸出 SHA 與狀態；失敗只從最後有效 Stage 恢復。
- 已鎖定行情不重抓；下游只讀快照。無關項目不因單項失敗停工。
- 30 分鐘為效率目標，不得以犧牲正確性換取。
- 不要求使用者逐步輸入「繼續」；除必要決策／授權外自動推進。

## 11. 變更閉環
每次改規則／欄位／模板／程式／Workflow／排程，必須回頭檢查所有上下游：Stage WR、contracts、Manifest、Builder selector、Schema、測試、唯一寫入者、Workflow 觸發、Pages、archive、排程及 Chart 3。寫入後回讀 GitHub，核對 commit、blob SHA 及內容。未測試不得宣稱通過。

## 12. 全域上線定義
六階段真實 E2E、兩種母版、44 項行情與 FedWatch、行事曆／財報／新聞／五層分析、Chart 3 同步、四類 QA、main preview 遠端回讀、Pages 公開驗證、核准後正式發布／封存、排程切換及 Simulation 未受修改均有證據，方可標正式上線。
