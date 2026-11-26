# Stage 5｜唯一 HTML Builder 組裝與 QA

## 輸入
核准雙母版、production Manifest、Stage 2–4 輸出、PASS 的 pre-build receipt 與 SHA、MOTHER_TEMPLATE_QA、QA_CONTRACT、經核准的 Builder 精確版本。

## 執行
1. main Builder 必須使用 SIM-1.4 已核准 Builder 作為技術基準（來源 SHA `6bf6eb2f5ae29774addf696c541c5b806953c7a3`），但該版本含 Simulation 路徑與隔離寫入限制；需先完成 main 路徑適配、依賴遷移、完整測試及核准，未完成前只能標示 PORT_IN_PROGRESS／CANDIDATE，不得作正式生產入口。
2. Builder 只接受同一 Run 的完整輸入；核對 pre-build receipt PASS、run_id、report_date、Fixture／Manifest／calendar SHA。
3. 使用真正 DOM parser，從母版完整複製後只更新核准槽位。不得 regex 改 HTML、重建 DOM、注入 CSS／JS、改 class／ID／屬性／父子結構或破壞互動。
4. 依 MOTHER_TEMPLATE_QA 執行 DOM、ID、導航、收折、tabs、財報卡、Fed/FOMC、手機版及視覺測試。必要 viewport：360、390、412、768、1440 px。
5. 四類 QA：資料／內容、HTML 結構、視覺／互動、Run／交付整合。不得把未測試寫成 PASS；不得新增重複檢核同一事實的冗餘 Gate。
6. 只有必要 Gate 通過且 Builder 精確版本已核准，才標 REVIEW_READY。非核心行情缺漏須明確呈現，無依賴工作繼續；不可把缺值當 0。

## 輸出
當次 Run 的 review.html、render-manifest.json、QA sidecar、HTML SHA-256、四類 QA 報告、輸入 receipt 副本。

## 限制
Stage 5 不寫 preview、index.html、history、calendar JSON、母版或正式 Manifest。交給 Stage 6。
