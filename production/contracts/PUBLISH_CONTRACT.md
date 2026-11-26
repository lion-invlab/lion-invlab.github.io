# PUBLISH CONTRACT v1.1

## 審核版交付
Stage 6 僅寫入：
- `preview/YYYY-MM-DD-review.html`
- `preview/YYYY-MM-DD-review.qa.json`
- `preview/YYYY-MM-DD-review.delivery.json`

HTML bytes 從 Stage 5 原樣複製。QA sidecar／receipt 綁定來源 Run、attempt、report_date、Builder SHA、pre-build receipt SHA、HTML SHA-256、Git blob SHA、main commit 及 Pages deployment。寫入前後確認 path set 僅三檔。從遠端 main 回讀三檔並核對內容／雜湊；明確 dispatch 既有 Pages workflow，等待成功，再開啟公開預覽 URL 核對報告日期與內容。未驗證公開 URL 不得標 DELIVERED。

## 正式首頁
審核版交付不等於正式發布。只有使用者明確核准指定日期／版本後，才更新根目錄 `index.html` 並封存 history。回讀正式首頁與封存檔 SHA，並驗證公開網址。

## 舊 Workflow
新 main-native Pipeline 切換前，先阻止舊 Simulation-to-main preview workflow 與新入口競爭。整併／停用舊自動 archive workflow，避免未核准或錯誤日期的首頁被封存。歷史 artifacts 與 commits 保留。
