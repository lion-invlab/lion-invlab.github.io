# PUBLISH CONTRACT v1.2

## 審核版交付
Stage 6 僅寫入：
- `preview/YYYY-MM-DD-review.html`
- `preview/YYYY-MM-DD-review.qa.json`
- `preview/YYYY-MM-DD-review.delivery.json`

HTML bytes 從 Stage 5 原樣複製。QA sidecar／receipt 綁定來源 Run、attempt、report_date、Builder SHA、pre-build receipt SHA、HTML SHA-256、Git blob SHA、main commit 及 Pages deployment。寫入前後確認 path set 僅三檔。從遠端 main 回讀三檔並核對內容／雜湊；明確 dispatch 既有 Pages workflow，等待成功，再開啟公開預覽 URL 核對報告日期與內容。未驗證公開 URL 不得標 DELIVERED。

## 正式首頁
審核版交付不等於正式發布。Builder 的 `approved_by_owner=true` 只核准 Builder exact blob，不代表報告內容或正式首頁發布核准；`REVIEW_READY`、Stage 6 DELIVERED、Preview 公開可讀也都不構成發布授權。只有使用者明確核准指定 report_date 與 Preview 版本後，才可在同一發布 commit 更新根目錄 `index.html` 及 `production/config/homepage-publication-lock.json`，並使用精確 commit marker `[publish-tac-report:YYYY-MM-DD]`。Lock 必須記錄 `APPROVED_PUBLICATION`、`approved_by_owner=true`、approved_at、approval_note、report_date、preview_path、preview_git_blob_sha 及 index_git_blob_sha；Pages 與 archive workflow 必須先通過 lock 驗證，否則 fail-closed。未有核准時 lock 維持 `BASELINE_LOCKED`，其 index_git_blob_sha 必須等於當前正式首頁 blob SHA。回讀正式首頁與封存檔 SHA，並驗證公開網址。

## 舊 Workflow
新 main-native Pipeline 切換前，先阻止舊 Simulation-to-main preview workflow 與新入口競爭。整併／停用舊自動 archive workflow，避免未核准或錯誤日期的首頁被封存。歷史 artifacts 與 commits 保留。
