# Stage 1｜開工基準與母版鎖定
版本：Main E2E v1.3（2026-11-28）
- 正式製作日為台灣週二至週六；週一、週日不自動製作。週二至週五 report_date=製作當日；週六製作時 report_date=隔週一（production_date+2 days），trading_date=週五，使用 Monday mother。週六不是 report_date，不得以週六日期命名 Preview。
- 週二至週五使用 Weekday mother；週六生產的週一早報使用 Monday mother，讀取報告週及前一週 ISO-week 行事曆資料。
- report_cutoff_taipei 代表實際生產日的收盤後資料截點。週二至週五按 report_date 前一個 New York 日期 16:25 ET 換算；週六生產的週一早報則按 report_date 前第三個 New York 日期（週五）16:25 ET 換算，對應台灣週六 05:25 冬令／04:25 夏令。

## 開工前讀取本階段 WR
- 開始本階段工作前，完整讀取本文件（UTF-8）；確認內容可讀即可。
- 這是工作指令，不是額外驗收關卡。不得要求 Stage 1–4 提交 WR SHA、Git blob SHA、Preflight receipt 或跨階段 WR 證明。
- 讀取本階段 WR 後，直接依下列工作內容執行；完成即交付下一階段。

 
Stage 1 自身必須先完整讀取本文件，完整讀取本文件後即可建立 Run。Stage 1 是輕量初始化：只允許 Python 標準函式庫與 Git 操作；建立及提交 Run handoff 前，禁止安裝 pandas、Playwright、Chromium、瀏覽器或 Stage 2–6 的任何重型依賴。Stage 1 必須在 Stage 2 喚醒前，將 run-context、Stage 1 fixture、report-data、Stage 1 receipt 與初始 run-state.json 一次提交至 main，並確認遠端可讀。Stage 2 不得在 Stage 1 之前預擷取。 Stage 1 是獨立且短時的 GitHub job：完成遠端提交及回讀後必須立即結束，不得等待 Stage 2 worker、不得安裝 Stage 2–6 依賴、不得執行 Stage 2／3。Stage 1 只需先讀取本文件，不設獨立 Preflight 關卡。

## 輸入
MASTER_WR、Stage 1 本身及 Stage 2–6 WR、共用 contracts、production/config/mother-template-manifest.json、雙母版、MOTHER_TEMPLATE_QA、報告日期及 main 行事曆 JSON。Stage 1 讀取自身規範是執行依據，不構成前置 Stage 依賴。

## 執行
1. 以 Asia/Taipei 確定 production_date 與 report_date：週二至週五 report_date=當日；週六 report_date=隔週一；週一、週日不得由正常排程啟動。依 report_date 決定最近已完成交易日。
2. 週一 report_date（由週六製作）選 Monday template，讀取報告週及前一週 ISO-week JSON；週二至週五選 Weekday template，只讀報告週 JSON。
3. 記錄 main 起始 commit、MASTER WR／六份 Stage WR／全部共用 contracts／Manifest／母版／QA blob SHA，另固定 Builder approval record、Builder、Stage Runner／依賴模組、PORT_MANIFEST 與 tac-production.yml 的 blob SHA，以及週 JSON 路徑與 SHA。以 governance.blob_shas 固定清單保存；所有版本均固定於同一個起始 main commit，不得混用執行途中更新的 HEAD。
4. 驗證模板 SHA 與 Manifest 完全一致、週別情境正確、JSON 可解析、schema/日期合理。不得 fallback 到 main 舊母版、首頁、歷史報告或前次 preview。
5. 建立唯一 Run ID 與 run-context；Run ID 固定為 TAC-{report_date}-{workflow_run_id}，不得包含 workflow_run_attempt。相同 GitHub workflow retry 必須沿用同一 Run ID；只有明確 rerun（新 workflow_run_id）才建立新 Run。記錄保護範圍及當次輸出路徑。Run context 必須包含固定 report_date、共用日期錨點 trading_date、report cutoff、mother key/path/blob SHA、Manifest SHA、calendar commit、週 JSON SHA 及 governance blob SHA 清單。trading_date 只供 Run／行事曆日期錨定，不代表 44 項商品必須採用同一個市場 data_date；Stage 1 Fixture 的 data_date 是空白建置用暫定值，Stage 2 必須逐項替換為實際 target_date。

## 輸出
run-context.json（含 legacy_prior_run_ids，只記錄無 run-state 的舊 Run ID，不讀取其資料）、Stage 1 fixture、report-data、基準 SHA 清單、calendar read receipt、Stage 1 receipt（含 run-context SHA 與 governance file count）、run-state.json（Stage 1=PASS、Stage 2=READY、Stage 3–6=NOT_STARTED），並在 Stage 2 啟動前提交遠端。

## 驗收與交接
必要路徑、SHA、日期、星期情境全部正確才 PASS。將固定日期、交易日、44 項欄位清單、母版及來源規格交給 Stage 2。Stage 1 不修改母版、Manifest 或 calendar JSON。
