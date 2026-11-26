# TAC 投資早報 R3｜main 重建計劃表

更新：2026-11-26（Asia/Taipei）
正式目標：main 原生獨立生產；審核版直接交付 main/preview；使用者核准後才更新 index.html。
硬性邊界：Simulation branch 全程唯讀、不修改、不重寫、不停用其工作流程；main 舊母版／舊 WR／舊早報 Pipeline 可退役，不作新系統依賴。

## 總體階段表

| Phase | 工作目標 | 必要交付 | 完成判準 | 狀態 |
|---|---|---|---|---|
| 0. 資產盤點與架構定案 | 盤點 main、標出唯一資料來源／寫入者／Workflow 衝突，定案新目錄與權責 | PHASE0_INVENTORY、架構責任與風險清單 | main tree、母版、calendar、Chart 3、Pages、archive、舊 workflows 均已盤點；依賴與風險有記錄 | DONE |
| 1. 規範與契約定版 | 以 SIM-1.4 技術內容為基準，重寫 main MASTER WR、六份 Stage WR、共用 contracts、雙母版 Manifest／QA；排除舊 main 規則衝突 | MASTER_WR、STAGE_1–6、DATA_SCHEMA、STATUS_ENUM、SOURCE_POLICY、RUN、HANDOFF、BUILDER、QA、PUBLISH、母版 Manifest／QA | 每項規則有唯一權威；Stage 間輸入輸出一致；44 欄位、截圖優先、4 頁並行、Stage3唯讀、五層分析、Builder／交付責任一致；交叉引用及 SHA 經回讀 | IN_PROGRESS（主要文件已建，跨文件一致性收尾中） |
| 2. Runner 與 Builder 移植 | 將 SIM-1.4 可用模組移植／適配至 production，建立 main 唯一 Runner；不直接引用 simulation 路徑 | production/runner、Builder、Stage adapters、Stage 1–6 Runner、測試 | 不依賴 Simulation runtime 路徑；使用 production templates／Manifest；blank-first、截圖 sidecar、4 concurrency、Stage2 receipt、Chart3 append、calendar readonly、Stage 5 QA、Stage 6 delivery 均可執行 | IN_PROGRESS（Stage 1–6 Runner 已建立；Stage 5/6 尚未真實 E2E 驗證，Chart 3 寫入仍需接入主 Workflow） |
| 3. Main Workflow 與發布管線 | 建立唯一 tac-production.yml，接通 Stage 1–6、Chart 3 handoff、權限／concurrency／main preview三檔白名單／Pages dispatch；整理舊 main workflow 衝突 | .github/workflows/tac-production.yml、Workflow wiring tests、舊流程退役清單 | 新 Workflow 只 checkout main；單一正式入口；Chart 3 增量另行受控提交；Stage 6 明確 dispatch Pages；舊 Simulation-to-main preview 流程在新 E2E 通過後退役 | IN_PROGRESS（目前僅 main-only validation workflow，尚未接上六階段生產執行） |
| 4. 全面整合測試 | 44行情、calendar、earnings、news、五層分析、雙母版、DOM、視覺互動、Chart3、delivery 全鏈整合 | deterministic tests、browser QA、negative tests、integration receipts | 兩種母版都通過；狀態分類不崩潰；不重抓已鎖定行情；跨 Run 不混資料；僅三檔 preview 寫入；Pages公開預覽驗證 | IN_PROGRESS（Stage 1–4 部分單元測試已通過；Stage 5/6 與雙母版真實資料整合尚未驗收） |
| 5. 真實資料 E2E | 用當日真實資料完整執行六階段，輸出審核版；不沿用舊 fixture 價格；記錄Stage2 4頁並行實際耗時 | 完整 Run artifact、preview HTML、QA sidecar、delivery receipt、E2E report | 六階段均有真實輸入輸出與SHA；44項有值或狀態；Chart3 SP500增量同步；calendar只讀；HTML／QA／Pages驗證完成；無未揭露阻塞 | NOT_STARTED |
| 6. 排程與正式切換 | 新main-native workflow取代舊主流程；確認04:35 calendar、05:25 report、05:30 Chart3責任分流；保留使用者正式首頁核准權 | Schedule cutover evidence、old workflow disabled/retired record、monitoring | 不重複執行、不漏跑、不雙寫；自動執行與失敗恢復可驗證；正式首頁仍須使用者核准 | NOT_STARTED |

## Phase 1 已完成項目
- [x] 建立 `production/MASTER_WR.md` 並明確以 SIM-1.4 為技術來源，main 為獨立生產。
- [x] 將 SIM-1.4 Monday／Weekday 母版逐位元複製至 `production/templates/`。
- [x] 建立 `production/config/mother-template-manifest.json`，SHA 綁定兩份 SIM-1.4 模板。
- [x] 將 SIM-1.4 詳細母版 QA 契約複製至 `production/contracts/MOTHER_TEMPLATE_QA.md`。
- [x] 將 SIM-1.4 完整 WR 原文保存為 `production/reference/SIM-1.4_SOURCE_BASELINE.md`，作為可追溯技術依據。
- [x] 建立六份 Stage WR。
- [x] 建立／修訂 DATA_SCHEMA、STATUS_ENUM、SOURCE_POLICY、RUN、HANDOFF、HTML_BUILDER、QA、PUBLISH contracts。

## Phase 2 已移植項目
- [x] Stage 2 blank-first fixture bootstrap、截圖 sidecar parser、44頁 browser reader、ChatGPT Web observation validator、44-row source manifest、Stage 2 receipt、S&P 500 Chart 3 handoff。
- [x] Stage 2 browser reader default concurrency=4，且程式限制最大 concurrency=4。
- [x] Calendar source guard、earnings judgment、earnings price-reaction／consensus modules。
- [x] SIM-1.4 Builder 移植為 main candidate，路徑改為 production Manifest／雙母版／MASTER WR，輸出限制為 production/runs/<run_id>/review.html。
- [x] 主要 Stage 2、財報、母版、Builder regression tests 複製至 main；舊 Simulation 路徑已逐步清除。
- [x] 建立 main-only validation workflow（目前測試尚未全通過；不得視為正式 Pipeline）。

## Stage 1–6 新增 Runner 進度（2026-11-26）
- [x] Stage 1 `create_run_fixture.py`：每次建立獨立 Run、NYSE trading date、鎖定雙母版／Manifest SHA、calendar main commit，44 行 blank-first fixture。
- [x] Stage 2 `run_stage2.py`：4 頁並行、44-row observation／audit／manifest／receipt，S&P 500 verified 時產生 Chart 3 increment；MOVE delayed retry module 已移植。
- [x] Stage 3 `run_stage3.py`：從 Stage 1 pinned main commit 唯讀讀取本週及前一週 calendar，輸出 projection 與 receipt。
- [x] Stage 4 `run_stage4.py`：新聞／總結／五層分析／政治掃描 schema、日期窗口、來源欄位與市場快照不變檢查。
- [x] Stage 5 `run_stage5.py`：pre-build receipt、main Builder、artifact validator、母版 DOM、visual regression、interaction smoke。
- [x] Stage 6 `run_stage6.py`：main/preview 三檔白名單、遠端 bytes／SHA 回讀、Pages workflow dispatch 與公開 URL 驗證。
- [ ] Stage 4 編輯內容仍由 `production/input/report-content-YYYY-MM-DD.json` 提供；尚未建立排程可獨立執行的新聞研究／五層分析內容生成器。
- [ ] Stage 2 Chart 3 increment 目前寫入 Runner workspace；尚未由 main Workflow 以獨立白名單 commit 並 dispatch Chart 3 merge workflow。
- [ ] Stage 5／6 尚未用真實當日輸入完成 E2E；不得把 Runner 已建立視為 REVIEW_READY 或正式 Pipeline 已啟用。

## Phase 1 未完成／需收尾
- [ ] 核對所有新檔案之交叉引用、欄位名稱及狀態集合，修正與 SIM-1.4 原文的差異。
- [ ] 明確列出 Builder 主程式精確 SHA、所有 import dependency、可寫入 selector、CLI 及路徑適配方案；SIM Builder 的核准只代表來源基準，不等於 main port 已核准。
- [ ] 明確處理 SIM-1.4 的四頁並行規則與原 Workflow 中仍殘留的 concurrency=2。
- [ ] 完成新 Manifest／QA contract 的 schema 與自動檢查。\n- [ ] 對照完整 SIM-1.4 原文核對全部細節；目前主文件已覆蓋核心責任，但仍需驗證所有歷史規則與 selector 契約。
- [ ] 建立 Stage 2–4 pre-build receipt 欄位與 Builder provenance 一致性規格。

## 全域依賴與每階段回看規則
每次完成一個可交付步驟，回到本計劃表更新狀態，並檢查：
1. MASTER／Stage WR → contracts／Schema／Manifest；
2. Stage 輸入輸出 → Runner／Builder／QA；
3. 資料寫入者 → Workflow／排程／Chart 3；
4. preview 發布 → Pages／history archive／正式首頁核准；
5. 測試 → fixtures／真實資料 E2E／遠端回讀。
若變更影響任何相鄰模組，必須同步更新，不能只修單一檔案。

## 不可提前執行
- Phase 4 未通過前，不得標記新 Pipeline REVIEW_READY。
- Phase 5 真實 E2E 未完成前，不得切換每日正式排程。
- Phase 6 前不得同時啟動新舊兩套早報生產流程。
- 本計劃及所有新系統程式不得修改 Simulation branch。
