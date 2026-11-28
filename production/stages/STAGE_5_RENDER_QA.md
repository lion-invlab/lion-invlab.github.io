# Stage 5｜唯一 HTML Builder 組裝與 QA
版本：Main E2E v1.2（2026-11-28）

## 開工前強制 WR Preflight
- Stage Runner 必須在任何本階段資料處理、分析、組裝或交付動作前，呼叫 `stage_wr_preflight` 完整讀取本階段 WR。
- Stage 1 以當前 main HEAD 的本階段 WR 為基準；Stage 2–6 必須同時核對 Stage 1 `governance.blob_shas`、鎖定 commit 與當前 WR Git blob SHA。
- 缺檔、空檔、無法完整 UTF-8 讀取、Run 未鎖定該 WR、SHA 不一致，均立即 FAIL-CLOSED；不得跳過、fallback 或繼續工作。
- 本階段輸出收據必須包含 `wr_preflight`，至少記錄 `wr_path`、`wr_loaded`、`wr_sha256`、`wr_git_blob_sha`、`stage1_pinned_git_blob_sha`、讀取位元組數及 PASS 狀態。沒有該證據不得宣告本階段完成。
 
Stage 5 必須先完整讀取本文件及完成 WR Preflight，才可執行 Builder、內容 QA 或任何測試。

## 輸入
核准雙母版、production Manifest、Stage 2–4 同一 Run 輸出、PASS 的 pre-build receipt 與 SHA、MOTHER_TEMPLATE_QA、QA_CONTRACT、Stage 1 governance.blob_shas 完整快照，以及 main Builder 精確版本及其核准狀態。

## 執行
1. 比對 Stage 1 governance.blob_shas 與當前 main 的所有規範、Manifest、Builder approval、Builder、Stage Runner、依賴模組及 Workflow blob SHA；任何差異均停止，避免跨版本 Run。並核對 Builder approval record 的 exact blob SHA 與 APPROVED_MAIN 狀態。
2. SIM-1.4 Builder 僅為 Main 移植的技術來源，來源 SHA `6bf6eb2f5ae29774addf696c541c5b806953c7a3`；Main 執行只能使用 `production/runner/build_review_html.py`。目前 Main Builder exact blob `5d555e40285bf4156740e418664f4833d66956ee` 已於 2026-11-27 獲 Owner 明確核准，核准紀錄為 `APPROVED_MAIN`。此核准僅對應該精確 blob，不代表真實資料 E2E 或 Stage 5／6 QA 已通過；任何 Builder 程式修改都必須重新核准 exact blob SHA。
3. Builder 只接受同一 Run 的完整輸入；核對 pre-build receipt PASS、run_id、report_date、Fixture／Manifest／calendar SHA。任何跨 Run、跨日期或 SHA 不符均停止。
4. Stage 4 內容 QA 必須在既有 Stage 5 驗收中實際執行：總結恰為三段且互不重複；市場情緒評論具實質解讀且不複製總結；五層分析及各層來源完整；政治／地緣六領域掃描、事件分類與政策傳導有證據；只有當日存在重大且具可辨識市場影響的事件時，才要求基準、風險、嚴重三種情境；當日沒有重大事件時，記錄 NOT_APPLICABLE 與原因，不得為了通過 QA 硬湊情境。 目前 Main 的操作判準：六領域掃描完成、`political_scan.findings` 為空陣列，且 `no_material_change_note` 有具體文字，才可標示 `NOT_APPLICABLE`；Builder 與 artifact validator 的情境數均須為 0。只要存在任何 finding，保守視為情境分析適用，必須完整提供基準、風險、嚴重三種情境；未來若要排除非重大 finding，須先在 schema 加入經審查且具證據的非重大市場影響分類。QA sidecar 必須記錄政治掃描、六領域、事件分類、政策傳導完整性及 scenario_analysis_coverage；適用項目缺漏、NOT_TESTED 或 PARTIAL 不得標 REVIEW_READY。
5. Main 審核版的 top-warning、側欄頁尾、資料警示及 footer 不得殘留「模擬審核版」、「Simulation 隔離區」或「內部教育訓練」標示；只更新核准 DOM 既有文字槽，不改動母版結構。
6. 使用真正 DOM parser，從核准母版完整複製後只更新核准槽位。不得 regex 改 HTML、重建 DOM、注入 CSS／JS、改 class／ID／屬性／父子結構或破壞互動。
7. 依 MOTHER_TEMPLATE_QA 執行 DOM、ID、導航、收折、tabs、財報卡、Fed/FOMC、手機版及視覺測試。必要 viewport：360、390、412、768、1440 px。詳細檢查以 MOTHER_TEMPLATE_QA 為唯一清單，不在本文件複製第二份檢查表。
8. 四類 QA：資料／內容、HTML 結構、視覺／互動、Run／交付整合。不得把未測試寫成 PASS；不得新增重複檢核同一事實的冗餘 Gate。必要 QA 只執行一次，結果由 receipt 引用。
9. 只有 main Builder 精確版本已核准、必要 Gate 全數通過、同一 Run provenance 完整時，才標 REVIEW_READY。非核心行情缺漏須明確呈現，可標 PARTIAL 並讓無依賴工作繼續；不可把缺值當 0，也不可將 PARTIAL 誤寫成 REVIEW_READY。 Stage 5 整體狀態必須由證據推導：Stage 2 非 PASS、仍有 pending_rows，或 fixture 尚有 pending_items，Stage 5 receipt 與 QA sidecar 一律標 `PARTIAL`；不得以 Builder 的 HTML review_ready 欄位覆蓋資料狀態。Workflow 必須保留 Run 產物並略過 Stage 6，不得交付 main/preview。只有 Stage 2 PASS 且無未解項目，且其餘必要 Gate 通過，才可標 `REVIEW_READY`。

## 輸出
當次 Run 的 review.html、render-manifest.json、QA sidecar、HTML SHA-256、四類 QA 報告、輸入 receipt 副本及 Stage 5 receipt。

## 限制
Stage 5 不寫 preview、index.html、history、calendar JSON、母版或正式 Manifest。交給 Stage 6。

## Main Builder approval gate
`production/config/builder-approval.json` 必須為 `APPROVED_MAIN`、`approved_by_owner: true`，且記錄的 Builder blob SHA 必須等於當前 `production/runner/build_review_html.py`。任何 Builder 程式修改均使原核准失效，必須重新核准 exact blob SHA。


## Main Run state contract v1.2
- Stage 5 必須確認同一 Run 的 Stage 4=PASS，且 Stage 5=READY；Stage 2/3/4 receipts、market snapshot、Research Bundle、editorial content、Builder approval 及母版 SHA 必須全部綁定相同 run_id。
- Stage 5 Runner 先以 compare-and-swap 將 Stage 5 改為 RUNNING，完成 QA 後寫入 stage5-render-qa-receipt.json，再將 Stage 5 狀態更新為 PASS 或 PARTIAL，記錄 receipt SHA。
- Stage 5 的 PASS 對應 QA receipt REVIEW_READY；PARTIAL 對應 QA receipt PARTIAL。若 Stage 2 為 PARTIAL，Stage 5 不得標 PASS，即使 HTML 可成功組裝也必須 PARTIAL，Stage 6 設為 SKIPPED。
- Chart 3 S&P 500 增量是非阻塞下游支線；Chart 3 append／merge／監控失敗不得單獨阻止 Stage 5 QA 或早報交付。Stage 5 必須記錄 Chart 3 handoff 狀態，但不得把它列為 Stage 6 前置 Gate。
- Stage 5 不建立 Run、不重抓行情、不讀日期共用 Stage 4 檔案、不改寫正式母版或 Manifest。
