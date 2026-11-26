# Stage 6｜main/preview 審核版交付與驗證

## 輸入
Stage 5 REVIEW_READY HTML bytes、HTML SHA-256、Git blob SHA、QA sidecar、pre-build receipt、Builder／母版 provenance。

## 執行
1. 從 main 最新 HEAD 建立獨立 worktree；只寫三個日期化路徑：`preview/YYYY-MM-DD-review.html`、`.qa.json`、`.delivery.json`。
2. HTML 原始 bytes 不得重組或改寫。QA sidecar 作交付副本，保留建置來源 branch／Run／attempt，新增 delivery_branch=main、main report path、delivery commit 等欄位。
3. Delivery receipt 記錄 report_date、來源分支／路徑、三個 main 目標路徑、HTML／QA SHA-256 與 Git blob SHA、workflow_run_id／attempt、trigger commit、Builder SHA、pre-build receipt SHA，以及首頁／calendar／母版／Manifest 未修改聲明。
4. 寫入前後檢查 staged／committed path set 僅三檔；禁止 force-push。遇 main HEAD 競爭可安全 rebase 後重驗白名單與 SHA；衝突或權限拒絕停止。
5. 從遠端 main 重新讀取三檔，核對 bytes、blob SHA、HTML SHA-256、QA provenance、Run／attempt／trigger commit。
6. 明確 dispatch 既有 `.github/workflows/pages.yml`；等待該 main commit 對應 Pages Run success，再開啟公開 preview URL 核對報告日期與內容。未完成部署或 URL 驗證時標 MAIN_PREVIEW_DEPLOY_PENDING／UNVERIFIED，不得稱已交付。
7. Stage 6 審核版交付不更新 `index.html`、正式母版、Manifest、calendar JSON 或正式 history。只有使用者另行明確核准指定日期／版本後，才由正式發布子流程更新首頁及封存歷史。

## 輸出
main/preview 三檔、遠端回讀 SHA、Pages workflow run、公開 URL 驗證證據、delivery receipt。
