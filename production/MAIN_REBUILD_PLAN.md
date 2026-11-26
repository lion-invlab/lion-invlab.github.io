# TAC 投資早報 R3｜main 重建計劃表

更新：2026-11-26（Asia/Taipei）
正式目標：main 原生獨立生產；審核版直接交付 main/preview；使用者核准後才更新 index.html。
硬性邊界：Simulation branch 全程唯讀、不修改、不重寫、不停用其工作流程；main 舊母版／舊 WR／舊早報 Pipeline 可退役，不作新系統依賴。

## 總體階段表

| Phase | 工作目標 | 必要交付 | 完成判準 | 狀態 |
|---|---|---|---|---|
| 0. 資產盤點與架構定案 | 盤點 main、標出唯一資料來源／寫入者／Workflow 衝突，定案新目錄與權責 | PHASE0_INVENTORY、架構責任與風險清單 | main tree、母版、calendar、Chart 3、Pages、archive、舊 workflows 均已盤點；依賴與風險有記錄 | DONE |
| 1. 規範與契約定版 | 以 SIM-1.4 技術內容為基準，重寫 main MASTER WR、六份 Stage WR、共用 contracts、雙母版 Manifest／QA；排除舊 main 規則衝突 | MASTER_WR、STAGE_1–6、DATA_SCHEMA、STATUS_ENUM、SOURCE_POLICY、RUN、HANDOFF、BUILDER、QA、PUBLISH、母版 Manifest／QA | 每項規則有唯一權威；Stage 間輸入輸出一致；44 欄位、截圖優先、4 頁並行、Stage3唯讀、五層分析、Builder／交付責任一致；交叉引用及 SHA 經回讀 | IN_PROGRESS（六份 Stage WR 已逐份回讀並完成第一輪修訂；尚待完整 SIM-1.4 逐條對照與 Runner／Contract 自動一致性驗證） |
| 2. Runner 與 Builder 移植 | 將 SIM-1.4 可用模組移植／適配至 production，建立 main 唯一 Runner；不直接引用 simulation 路徑 | production/runner、Builder、Stage adapters、Stage 1–6 Runner、測試 | 不依賴 Simulation runtime 路徑；使用 production templates／Manifest；blank-first、截圖 sidecar、4 concurrency、Stage2 receipt、Chart3 append、calendar readonly、Stage 5 QA、Stage 6 delivery 均可執行 | IN_PROGRESS（Stage 1–6 Runner 已建立；Stage 2 Chart 3 commit／merge dispatch 已接入 Workflow；Stage 5/6 尚未真實 E2E 驗證） |
| 3. Main Workflow 與發布管線 | 建立唯一 tac-production.yml，接通 Stage 1–6、Chart 3 handoff、權限／concurrency／main preview三檔白名單／Pages dispatch；整理舊 main workflow 衝突 | .github/workflows/tac-production.yml、Workflow wiring tests、舊流程退役清單 | 新 Workflow 只 checkout main；單一正式入口；Chart 3 增量另行受控提交；Stage 6 明確 dispatch Pages；舊 Simulation-to-main preview 流程在新 E2E 通過後退役 | IN_PROGRESS（main Workflow 已拆為 validate／capture／build：capture 完成 Stage 1–3 並交付 AWAITING_EDITORIAL_INPUT handoff；build 僅接受綁定同一 Run 的編輯內容再執行 Stage 4–6。Chart 3 merge 與 Pages dispatch 已接通；尚未完成自動編輯內容交接及真實 E2E） |
| 4. 全面整合測試 | 44行情、calendar、earnings、news、五層分析、雙母版、DOM、視覺互動、Chart3、delivery 全鏈整合 | deterministic tests、browser QA、negative tests、integration receipts | 兩種母版都通過；狀態分類不崩潰；不重抓已鎖定行情；跨 Run 不混資料；僅三檔 preview 寫入；Pages公開預覽驗證 | IN_PROGRESS（main-only validation 的 Stage 1–4、Builder／財報 deterministic tests、候選 HTML DOM contract 已通過；真實 44 頁擷取、Stage 5/6 delivery 與雙母版完整 E2E 尚未驗收） |
| 5. 真實資料 E2E | 用當日真實資料完整執行六階段，輸出審核版；不沿用舊 fixture 價格；記錄Stage2 4頁並行實際耗時 | 完整 Run artifact、preview HTML、QA sidecar、delivery receipt、E2E report | 六階段均有真實輸入輸出與SHA；44項有值或狀態；Chart3 SP500增量同步；calendar只讀；HTML／QA／Pages驗證完成；無未揭露阻塞 | NOT_STARTED |
| 6. 排程與正式切換 | 新main-native workflow取代舊主流程；確認04:35 calendar、05:25 report、05:30 Chart3責任分流；保留使用者正式首頁核准權 | Schedule cutover evidence、old workflow disabled/retired record、monitoring | 不重複執行、不漏跑、不雙寫；自動執行與失敗恢復可驗證；正式首頁仍須使用者核准 | NOT_STARTED |

## 2026-11-26 持續修訂紀錄\n- [x] Stage 1／2／5 WR 第一輪修訂與 GitHub 回讀。\n- [x] 修正 Stage 5 Runner 缺少 `os` import 及 Chart 3 handoff 狀態變數未定義。\n- [x] Stage 5 加入 main Builder exact-SHA owner approval gate；候選狀態不得標 REVIEW_READY。\n- [x] MASTER WR、PORT_MANIFEST、Runner README 已同步 main 的 validate／capture／build 三模式流程，移除不存在的 `run_daily_report.py` 入口描述。\n- [x] 最新已完成驗證 run `45813748282`：validate job success；build job skipped（該 run 為 validation only）。Stage 5 新 gate 尚待新 CI 執行。\n\n## Phase 1 已完成項目
- [x] 建立 `production/MASTER_WR.md` 並明確以 SIM-1.4 為技術來源，main 為獨立生產。
- [x] 將 SIM-1.4 Monday／Weekday 母版逐位元複製至 `production/templates/`。
- [x] 建立 `production/config/mother-template-manifest.json`，SHA 綁定兩份 SIM-1.4 模板。
- [x] 將 SIM-1.4 詳細母版 QA 契約複製至 `production/contracts/MOTHER_TEMPLATE_QA.md`。
- [x] 將 SIM-1.4 完整 WR 原文保存為 `production/reference/SIM-1.4_SOURCE_BASELINE.md`，作為可追溯技術依據。
- [x] 建立六份 Stage WR。\n- [x] 第一輪 Stage WR 交叉核對：修正 Stage 1 自身規範輸入說明、Stage 2 sidecar 欄位 typo／狀態計數語意、Stage 5 Builder 核准與 REVIEW_READY 條件；六份文件均已從 main 回讀。
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
- [x] Stage 5 `run_stage5.py`：pre-build receipt、main Builder、artifact validator、母版 DOM、visual regression、interaction smoke；第一輪程式回讀另修正缺少 os import 與 Chart 3 handoff 狀態變數未定義。\n- [ ] Stage 5 Runner 修正後仍須 CI／fixture 執行驗證；Builder 核准狀態 gate 尚未完成。
- [x] Stage 6 `run_stage6.py`：main/preview 三檔白名單、遠端 bytes／SHA 回讀、Pages workflow dispatch 與公開 URL 驗證。
- [ ] Stage 4 編輯內容仍由 `production/input/report-content-YYYY-MM-DD.json` 提供；capture receipt 已指向 exact Run 的輸入位置，但尚未建立可獨立執行的新聞研究／五層分析內容生成器及自動提交交接。
- [x] Stage 2 Chart 3 increment 已由 main Workflow 僅提交 `data/tac-chart3/sp500_daily_increment.jsonl`，並明確 dispatch `tac-chart3-sp500-increment-merge.yml`；等待真實 S&P 500 VERIFIED run 驗證。
- [ ] Stage 5 main Builder 已加精確 SHA 核准紀錄 gate；目前 `CANDIDATE_PENDING_OWNER_APPROVAL`，未獲核准不得產生正式 REVIEW_READY。Stage 5／6 尚未用真實當日輸入完成 E2E。
- [ ] 尚無自動產生 `production/input/report-content-YYYY-MM-DD.json` 的編輯研究步驟；capture 已改為明確交付 Run-bound handoff，build 再以 `workflow_dispatch` 或 `[build-tac-report:YYYY-MM-DD]` marker 啟動。

## Phase 1 未完成／需收尾
- [ ] 完成 MASTER／六份 Stage WR／contracts／Runner 全面逐欄一致性檢查；第一輪只處理已確認問題，尚未完成 SIM-1.4 全文逐條比對。
- [x] 列出 Builder 主程式精確 SHA 與來源 SHA；建立 `production/config/builder-approval.json`，預設候選待核准，Stage 5 強制檢查 exact blob SHA 與 APPROVED_MAIN 狀態。\n- [ ] 完成 Builder 所有 import dependency、可寫入 selector、CLI 及路徑適配的完整清冊；SIM Builder 核准不等於 main port 已核准。
- [ ] 明確處理 SIM-1.4 的四頁並行規則與原 Workflow 中仍殘留的 concurrency=2。
- [ ] 完成新 Manifest／QA contract 的 schema 與自動檢查。\n- [ ] 對照完整 SIM-1.4 原文核對全部細節；目前主文件已覆蓋核心責任，但仍需驗證所有歷史規則與 selector 契約。
- [ ] 建立 Stage 2–4 pre-build receipt 欄位與 Builder provenance 一致性規格。\n- [ ] Stage 5 Runner 尚須加入 main Builder 精確版本核准狀態檢查；目前僅檢查 Builder provenance 的 review_ready，不足以單獨證明 main port 已核准。

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
