# RUN CONTRACT v1.0

## Run identity
- `run_id`: TAC-YYYY-MM-DD-<UTC timestamp>-<unique suffix>；同一 report_date 僅一個 active run。
- `report_date`: Asia/Taipei YYYY-MM-DD。
- `market_data_date`: 最近一個已完成美股交易日；其他市場可有各自交易日期。
- `timezone`: Asia/Taipei。
- `workflow_run_id`、`git_sha`、`master_wr_sha`、`stage_wr_shas`、`contract_shas` 必須記錄。

## Run directory
每次執行使用 `production/runs/<run_id>/` 作暫存與證據目錄；此目錄不是新的行情／新聞／行事曆持久資料庫。至少包含 run-context.json、stage-status.json、各 Stage 輸出、sha256sums.txt、run-summary.json。

## Stage record
每個 Stage 記錄 stage、status、started_at、completed_at、input_refs、output_refs、input_sha256、output_sha256、warnings、errors、retry_count、handoff_summary。

## Idempotency and recovery
- 同一 Run 的同一 Stage 輸出若存在且 SHA、schema、Run ID 均有效，可重用。
- 不可只依檔案存在判定有效；必須檢查 Run ID、輸入 SHA、Schema 及輸出 SHA。
- 來源重新擷取僅限未結項目；已 VERIFIED 並鎖定的欄位不重抓，除非有具體更正證據。
- Stage 失敗時保留有效上游輸出；只重試該 Stage 的失敗項目或恢復點。
- 不可跨 Run 混用舊輸出；如需引用歷史正式資料，必須明確標記 historical_reference 並符合來源政策。

## Concurrency
以 report_date 建立互斥鎖；活動中的同日期 Run 不得被新觸發取消或覆蓋。新觸發可排隊或拒絕並回報既有 Run ID。不同日期是否並行由正式設定決定，預設不並行。

## Completion
Run 狀態只可為 RUNNING、PARTIAL、FAILED、REVIEW_READY、DELIVERED、PUBLISHED。REVIEW_READY 代表完整審核版通過必要檢查；DELIVERED 代表 main/preview 遠端回讀及公開預覽已驗證；PUBLISHED 僅代表使用者核准後正式首頁及歷史封存均完成。
