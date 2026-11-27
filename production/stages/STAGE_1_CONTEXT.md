# Stage 1｜開工基準與母版鎖定
- Stage 1 必須依 report_date 前一個 New York 交易日的 16:25 ET 截止點設定 report_cutoff_taipei；換算台灣時間為美國冬令 05:25、夏令 04:25。必須依 report_date 前一日的 America/New_York DST 狀態計算，不得全年硬編碼 05:25。

## 開工前強制 WR Preflight
- Stage Runner 必須在任何本階段資料處理、分析、組裝或交付動作前，呼叫 `stage_wr_preflight` 完整讀取本階段 WR。
- Stage 1 以當前 main HEAD 的本階段 WR 為基準；Stage 2–6 必須同時核對 Stage 1 `governance.blob_shas`、鎖定 commit 與當前 WR Git blob SHA。
- 缺檔、空檔、無法完整 UTF-8 讀取、Run 未鎖定該 WR、SHA 不一致，均立即 FAIL-CLOSED；不得跳過、fallback 或繼續工作。
- 本階段輸出收據必須包含 `wr_preflight`，至少記錄 `wr_path`、`wr_loaded`、`wr_sha256`、`wr_git_blob_sha`、`stage1_pinned_git_blob_sha`、讀取位元組數及 PASS 狀態。沒有該證據不得宣告本階段完成。
 
Stage 1 自身必須先完整讀取本文件，完成 WR Preflight 後才可建立 Run。Stage 1 建立 Run 後，必須先將 run-context、Stage 1 fixture、report-data 與 Stage 1 receipt 提交至 main，確認遠端可讀；只有這份交付存在，Stage 2 worker 才可開始。Stage 2 不得在 Stage 1 之前預擷取。

## 輸入
MASTER_WR、Stage 1 本身及 Stage 2–6 WR、共用 contracts、production/config/mother-template-manifest.json、雙母版、MOTHER_TEMPLATE_QA、報告日期及 main 行事曆 JSON。Stage 1 讀取自身規範是執行依據，不構成前置 Stage 依賴。

## 執行
1. 以 Asia/Taipei 確定 report_date、星期及最近已完成交易日；週末不自動製作。
2. 週一選 Monday template，讀取本週及上週 ISO-week JSON；週二至週五選 Weekday template，只讀本週 JSON。
3. 記錄 main 起始 commit、MASTER WR／六份 Stage WR／全部共用 contracts／Manifest／母版／QA blob SHA，另固定 Builder approval record、Builder、Stage Runner／依賴模組、PORT_MANIFEST 與 tac-production.yml 的 blob SHA，以及週 JSON 路徑與 SHA。以 governance.blob_shas 固定清單保存；所有版本均固定於同一個起始 main commit，不得混用執行途中更新的 HEAD。
4. 驗證模板 SHA 與 Manifest 完全一致、週別情境正確、JSON 可解析、schema/日期合理。不得 fallback 到 main 舊母版、首頁、歷史報告或前次 preview。
5. 建立唯一 Run ID 與 run-context；記錄保護範圍及當次輸出路徑。Run context 必須包含後續 Stage 可直接使用的固定 report_date、trading_date、mother key/path/blob SHA、Manifest SHA、calendar commit、週 JSON SHA 及 governance blob SHA 清單。

## 輸出
run-context.json、Stage 1 fixture、report-data、基準 SHA 清單、calendar read receipt、Stage 1 receipt（含 run-context SHA 與 governance file count），並在 Stage 2 啟動前提交遠端。

## 驗收與交接
必要路徑、SHA、日期、星期情境全部正確才 PASS。將固定日期、交易日、44 項欄位清單、母版及來源規格交給 Stage 2。Stage 1 不修改母版、Manifest 或 calendar JSON。
