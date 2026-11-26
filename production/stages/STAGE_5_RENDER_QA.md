# Stage 5｜唯一 HTML Builder 組裝與 QA

## 輸入
核准雙母版、production Manifest、Stage 2–4 同一 Run 輸出、PASS 的 pre-build receipt 與 SHA、MOTHER_TEMPLATE_QA、QA_CONTRACT、Stage 1 governance.blob_shas 完整快照，以及 main Builder 精確版本及其核准狀態。

## 執行
1. 比對 Stage 1 governance.blob_shas 與當前 main 的所有規範、Manifest、Builder approval、Builder、Stage Runner、依賴模組及 Workflow blob SHA；任何差異均停止，避免跨版本 Run。並核對 Builder approval record 的 exact blob SHA 與 APPROVED_MAIN 狀態。
2. SIM-1.4 核准 Builder 是 main 移植的技術基準，來源 SHA `6bf6eb2f5ae29774addf696c541c5b806953c7a3`。此來源版本含 Simulation 路徑與隔離寫入限制，不得直接視為 main 已核准版本。main port 必須完成路徑／依賴適配、完整測試、精確版本與 provenance 登記；在正式核准狀態成立前只能標示 PORT_IN_PROGRESS／CANDIDATE，不能產生正式 REVIEW_READY。
3. Builder 只接受同一 Run 的完整輸入；核對 pre-build receipt PASS、run_id、report_date、Fixture／Manifest／calendar SHA。任何跨 Run、跨日期或 SHA 不符均停止。
4. 使用真正 DOM parser，從核准母版完整複製後只更新核准槽位。不得 regex 改 HTML、重建 DOM、注入 CSS／JS、改 class／ID／屬性／父子結構或破壞互動。
5. 依 MOTHER_TEMPLATE_QA 執行 DOM、ID、導航、收折、tabs、財報卡、Fed/FOMC、手機版及視覺測試。必要 viewport：360、390、412、768、1440 px。詳細檢查以 MOTHER_TEMPLATE_QA 為唯一清單，不在本文件複製第二份檢查表。
6. 四類 QA：資料／內容、HTML 結構、視覺／互動、Run／交付整合。不得把未測試寫成 PASS；不得新增重複檢核同一事實的冗餘 Gate。必要 QA 只執行一次，結果由 receipt 引用。
7. 只有 main Builder 精確版本已核准、必要 Gate 全數通過、同一 Run provenance 完整時，才標 REVIEW_READY。非核心行情缺漏須明確呈現，可標 PARTIAL 並讓無依賴工作繼續；不可把缺值當 0，也不可將 PARTIAL 誤寫成 REVIEW_READY。

## 輸出
當次 Run 的 review.html、render-manifest.json、QA sidecar、HTML SHA-256、四類 QA 報告、輸入 receipt 副本及 Stage 5 receipt。

## 限制
Stage 5 不寫 preview、index.html、history、calendar JSON、母版或正式 Manifest。交給 Stage 6。

## Main Builder approval gate
`production/config/builder-approval.json` 必須為 `APPROVED_MAIN`、`approved_by_owner: true`，且記錄的 Builder blob SHA 必須等於當前 `production/runner/build_review_html.py`。任何 Builder 程式修改均使原核准失效，必須重新核准 exact blob SHA。
