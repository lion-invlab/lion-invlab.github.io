# Stage 6｜main/preview 審核版交付與驗證
版本：Main E2E v1.2（2026-11-28）

## 開工前強制 WR Preflight
- Stage Runner 必須在任何本階段資料處理、分析、組裝或交付動作前，呼叫 `stage_wr_preflight` 完整讀取本階段 WR。
- Stage 1 以當前 main HEAD 的本階段 WR 為基準；Stage 2–6 必須同時核對 Stage 1 `governance.blob_shas`、鎖定 commit 與當前 WR Git blob SHA。
- 缺檔、空檔、無法完整 UTF-8 讀取、Run 未鎖定該 WR、SHA 不一致，均立即 FAIL-CLOSED；不得跳過、fallback 或繼續工作。
- 本階段輸出收據必須包含 `wr_preflight`，至少記錄 `wr_path`、`wr_loaded`、`wr_sha256`、`wr_git_blob_sha`、`stage1_pinned_git_blob_sha`、讀取位元組數及 PASS 狀態。沒有該證據不得宣告本階段完成。
 
Stage 6 必須先完整讀取本文件及完成 WR Preflight，才可建立 worktree、寫入 preview 或啟動 Pages 驗證。

## 輸入
Stage 5 REVIEW_READY HTML bytes、HTML SHA-256、Git blob SHA、QA sidecar、pre-build receipt、Builder／母版 provenance。 若 Stage 5 receipt／QA sidecar 為 `PARTIAL`，只保留 Run 內 HTML 與 QA 證據供內部檢視，不建立 main/preview 三檔、不啟動 Pages；Workflow 應明確略過 Stage 6。Stage 6 只接受 `REVIEW_READY`。

## 執行
1. 從 main 最新 HEAD 建立獨立 worktree；Main 一般 Run 只寫 `preview/main/YYYY-MM-DD-review.html`、`.qa.json`、`.delivery.json`，與 Simulation 的 `preview/` 根層輸出完全隔離。若 Run context 含 `supersedes_run_id`（使用者明確核准的同日期 rerun），改寫入獨立的 `preview/main/YYYY-MM-DD-rerun-review.html`、`.qa.json`、`.delivery.json`；不得覆蓋原已核准 Preview，確保首頁發布鎖仍可核對原版。
2. HTML 原始 bytes 不得重組或改寫。QA sidecar 作交付副本，保留建置來源 branch／Run／attempt，新增 delivery_branch=main、main report path、delivery commit 等欄位。
3. Delivery receipt 記錄 report_date、來源分支／路徑、三個 main 目標路徑、HTML／QA SHA-256 與 Git blob SHA、workflow_run_id／attempt、trigger commit、Builder SHA、pre-build receipt SHA，以及首頁／calendar／母版／Manifest 未修改聲明。
4. 寫入前後檢查 staged／committed path set 僅三檔；禁止 force-push。遇 main HEAD 競爭可安全 rebase 後重驗白名單與 SHA；衝突或權限拒絕停止。
5. 從遠端 main 重新讀取三檔，核對 bytes、blob SHA、HTML SHA-256、QA provenance、Run／attempt／trigger commit。
6. 明確 dispatch 既有 `.github/workflows/pages.yml`；等待該 main commit 對應 Pages Run success，再開啟公開 preview URL 核對報告日期與內容。未完成部署或 URL 驗證時標 MAIN_PREVIEW_DEPLOY_PENDING／UNVERIFIED，不得稱已交付。
7. Stage 6 審核版交付不更新 `index.html`、正式母版、Manifest、calendar JSON 或正式 history。只有使用者另行明確核准指定日期／版本後，才由正式發布子流程更新首頁及封存歷史。

## 輸出
main/preview 三檔、遠端回讀 SHA、Pages workflow run、公開 URL 驗證證據、delivery receipt。


## Main Run state contract v1.2
- Stage 6 必須確認同一 Run 的 Stage 5=PASS、QA receipt=REVIEW_READY，且 Stage 6=READY。Stage 5 PARTIAL 時 Stage 6 必須 SKIPPED，不得建立 Preview 三檔或啟動 Pages。
- Stage 6 Runner 以 compare-and-swap 將 Stage 6 改為 RUNNING；只有在三檔 Preview bytes／Git blob SHA、Pages deployment 對應 commit 及公開 URL 全部核實後，才寫入 stage6-delivery-receipt.json 並將 Stage 6 改為 PASS。
- Stage 6 PASS 的 Run overall_status 固定為 AWAITING_APPROVAL；不得自動改為 PUBLISHED。Stage 6 完成後，必須把 Stage 4–6 receipts、delivery receipt 及最終 run-state.json 提交回同一 Run 目錄，確保遠端可讀。
- Retry／Resume 必須沿用原 run_id 並從最後有效 PASS stage 接續；不得覆寫已完成 Stage receipt 或既有 Preview。只有明確核准 rerun 才可建立新 Run 與獨立 rerun Preview 路徑。
