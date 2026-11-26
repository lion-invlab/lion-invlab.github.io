# TAC 投資早報 R3｜MASTER WORK RULES

版本：1.0-draft（2026-11-26）
適用分支：main
權威層級：本檔為 main 新正式生產環境最高規範；使用者最新明確指示優先。
Simulation：唯讀保留，不屬於 main Pipeline 的執行依賴。

## 1. 唯一目標
每日自 main 獨立啟動並完成 TAC 投資早報，產出可公開讀取的 main/preview 審核版。使用者核准後，才更新正式首頁並封存歷史報告。所有設計均服務資料正確、連續產出、可恢復及成品品質；不以文件、Gate 或測試數量作為成果。

## 2. 系統組成
- 本 MASTER WR：定義權責、順序、輸入輸出、寫入權、狀態、恢復及發布邊界。
- 六份 Stage WR：定義各階段具體工作。
- 共用 contracts：定義資料格式、狀態、來源、Run、交接、Builder、QA、發布的共同介面。
- 唯一入口：production/runner/run_daily_report.py。
- 唯一正式 Workflow：.github/workflows/tac-production.yml。
- 唯一核准母版來源：母版專區/mother-template-manifest.json。
- 正式資料庫沿用 data/calendar/weeks/ 與 data/tac-chart3/；不得另建平行資料庫。

## 3. 唯一每日流程
Stage 1 Context → Stage 2 Market → Stage 3 Calendar → Stage 4 News & Analysis → Stage 5 Render & QA → Stage 6 Delivery。
每個 Stage 僅負責其 WR 定義的輸入、輸出與副作用。Runner 只負責排序、Run 狀態、交接、重試及總結，不重做 Stage 業務邏輯。

## 4. 權責與唯一寫入者
| 資產 | 唯一正式寫入者 | 其他階段 |
|---|---|---|
| data/calendar/weeks/YYYY-Www.json | 既有行事曆更新排程 | Stage 3 唯讀 |
| 當次 44 項行情資料集與 FedWatch | Stage 2 | 下游唯讀 |
| data/tac-chart3/sp500_daily_increment.jsonl | Stage 2（只追加已核實現貨收盤） | Chart 3 驗證／呈現端唯讀該增量 |
| 當次新聞與分析資料 | Stage 4 | 下游唯讀 |
| 當次審核版 HTML | Stage 5 | Stage 6 不重寫內容 |
| 當次 QA sidecar、delivery receipt | Stage 6 | 其他階段不覆寫 |
| index.html 與 history 封存 | 使用者核准後的 Stage 6 發布子流程 | 排程不得自行發布 |

任何新程式不得成為上述資產的第二寫入者。既有 Chart 3 merge／ingest workflow 在切換前須先完成責任重整，不能與 Stage 2 同時追加／合併同一日期。

## 5. Stage 輸入輸出
| Stage | 必要輸入 | 必要輸出 |
|---|---|---|
| 1 | MASTER、Stage WR、contracts、報告日期、Manifest、母版、週 JSON | run-context.json |
| 2 | run-context、44 欄位規格、來源政策、使用者已提供的截圖證據（如有） | market-data.json |
| 3 | run-context、週 JSON（唯讀） | calendar-data.json |
| 4 | Stage 2／3 輸出、新聞來源 | analysis-data.json |
| 5 | 同一 Run 的 Stage 1–4 輸出、核准母版 | preview HTML、render manifest |
| 6 | Stage 5 HTML、QA 結果、同一 Run ID | main/preview HTML、QA sidecar、delivery receipt；核准後正式發布與封存 |

每一個 Stage 輸出都必須攜帶 run_id、report_date、schema_version、created_at、status_summary、input_refs、output_refs。不得從其他 Run 取代當次輸入。

## 6. 執行原則
1. 每次建立唯一 Run ID；相同 report_date 不可有兩個並行正式 Run。
2. 每個 Stage 完成即保存輸出、SHA-256、狀態及交接資訊。
3. 只從最後一個有效且可驗證的 Stage 輸出恢復；不重抓已鎖定行情、不重做已完成內容。
4. 單項資料缺漏不得阻止無關項目及下游階段完成；不確定性必須一路保留。
5. 狀態依 STATUS_ENUM 契約；PENDING 不得被當成已完成，也不得因其存在而讓整批 Pipeline 直接崩潰。
6. 不繞過 Investing.com Cloudflare 或其他網站存取限制；頁面不可讀時如實標記。
7. 不要求使用者逐步輸入「繼續」。只在缺少必要授權／決策或有安全風險時暫停相應操作，其餘可獨立工作繼續。
8. 使用者提供的行情截圖若明確對應標的與收盤資料，優先作為該項採用證據；來源仍記錄為 Investing.com 對應標的，內部保留證據型態與收到時間。報告正文不得寫「依使用者截圖」，亦不得為已採用截圖數值再做不必要的重複核驗。

## 7. 日期、母版與時區
所有報告日期與排程以 Asia/Taipei 為準。週一使用 Manifest 登記的週一母版，週二至週五使用 weekdays 母版。週一保留上週經濟／財報回顧；其他工作日不得出現。母版 SHA 必須與 Manifest 一致；不一致時停止 Stage 5，不得 fallback 或自行改 SHA。

## 8. 審核版與正式發布邊界
Stage 6 先將 HTML、QA sidecar、delivery receipt 寫入 main/preview，回讀並核對 SHA，再驗證 GitHub Pages 公開 URL。這只代表審核版交付，不代表正式首頁發布。未收到使用者對明確日期／版本的核准，不得更新 index.html 或封存該份報告。使用者核准後，Stage 6 才執行首頁更新、歷史封存、Pages 驗證及發布紀錄。

## 9. 舊系統退場
新系統通過 Phase 5 E2E 並完成 Phase 6 排程切換前，保留舊 Workflow 作為現況／歷史資產，但不得同時啟動兩套正式生產流程。切換時停用舊 Simulation 跨分支交付觸發，整併 archive_index.yml 的責任；不刪除有歷史價值的舊程式與紀錄。Simulation 分支不修改。

## 10. 版本與變更管理
修改任何規則或契約，必須同步檢查相依 Stage WR、Schema、Runner、Workflow、測試、Manifest、資料寫入者與排程。先更新介面契約，再更新實作，再更新測試；不允許只改單點。每次改動完成後回讀 GitHub 遠端內容並記錄 commit／blob SHA。未執行的檢查標示未測試，不得宣稱通過。

## 11. 全域完成定義
新系統只有在六階段有實際輸入輸出、兩種母版均可產出、44 項行情與 FedWatch 可處理、行事曆／財報／新聞分析整合、Chart 3 資料同步、四類 QA、main/preview 遠端回讀、Pages 公開驗證、核准後正式發布與封存、排程切換及 Simulation 未受修改全部有證據時，才可標記正式上線。
