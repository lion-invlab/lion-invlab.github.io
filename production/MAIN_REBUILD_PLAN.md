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
| 4. 全面整合測試 | 44行情、calendar、earnings、news、五層分析、雙母版、DOM、視覺互動、Chart3、delivery 全鏈整合 | deterministic tests、browser QA、negative tests、integration receipts | 兩種母版都通過；狀態分類不崩潰；不重抓已鎖定行情；跨 Run 不混資料；僅三檔 preview 寫入；Pages公開預覽驗證 | IN_PROGRESS（main-only validation 14 個步驟全數通過，含 Stage 1 governance SHA、Stage 2／截圖、Stage 4 research bundle、Builder／財報 deterministic tests、候選 HTML DOM contract；真實 44 頁擷取、Stage 5/6 delivery 與雙母版完整 E2E 尚未驗收） |
| 5. 真實資料 E2E | 用當日真實資料完整執行六階段，輸出審核版；不沿用舊 fixture 價格；記錄Stage2 4頁並行實際耗時 | 完整 Run artifact、preview HTML、QA sidecar、delivery receipt、E2E report | 六階段均有真實輸入輸出與SHA；44項有值或狀態；Chart3 SP500增量同步；calendar只讀；HTML／QA／Pages驗證完成；無未揭露阻塞 | NOT_STARTED |
| 6. 排程與正式切換 | 新main-native workflow取代舊主流程；確認04:35 calendar、05:25 report、05:30 Chart3責任分流；保留使用者正式首頁核准權 | Schedule cutover evidence、old workflow disabled/retired record、monitoring | 不重複執行、不漏跑、不雙寫；自動執行與失敗恢復可驗證；正式首頁仍須使用者核准 | NOT_STARTED |

## 2026-11-26 持續修訂紀錄
- Main Stage 1–3 排程入口已加入 `.github/workflows/tac-production.yml`：GitHub Actions cron `5 21 * * 0-4` UTC，即美國冬令時間期間台灣時間週一至週五 05:05；排程事件直接執行 Main capture-and-calendar（Stage 1–3），workflow_dispatch 的 validate/capture/build 手動模式保留。這個排程不會執行 Stage 4–6，也不會修改首頁；Stage 3 後仍以同一 Run 的 `capture-stage-receipt.json` 等待編輯內容。冬令時間已修正為收盤後 05:05 啟動，避免 05:00 收盤前擷取。夏令時間切換仍待加入自動 DST 排程邏輯。
- 排程 workflow SHA 已寫入 PORT_MANIFEST。這是新增入口，尚未等到下一個排程時點實際觸發，需用首次排程 run 驗證。

- Main CI 最新結果：Workflow Run `45824747088`（commit `9c779455278d3bde84abe70324dedf5cb0db626d`）完成且 conclusion=success。逐步確認 Main-only checkout、模組編譯、雙母版 SHA、Stage 2／Pre-build 測試、Builder／earnings 測試、Candidate Builder fixture、母版 DOM contract 全部成功；capture/build job 為 skipped，故不代表真實資料 E2E。
- Stage 4→5→6 交接加固：Stage 4 receipt 新增 `trading_date`；Stage 5 驗證 Stage 4 Run／報告日／交易日、凍結市場快照前後 SHA、Research Bundle SHA 與 Stage 2 snapshot SHA 一致，並將交易日、Stage 4 receipt SHA、Research Bundle SHA、market snapshot SHA、Builder blob SHA 寫入 Stage 5 receipt。
- Stage 6 加強：核對 Stage 5 Run／雙日期、QA sidecar 日期、render manifest SHA、HTML SHA、Builder SHA；回讀 Stage 4 receipt SHA 並核對 editorial Run／snapshot／bundle 綁定後才允許交付。
- 上述 Stage 4／5／6 程式與 Stage 4 日期綁定測試已提交 Main，SHA 已同步至 PORT_MANIFEST。新增專用 `test_stage56_handoff.py`，涵蓋 Stage 4→5 的交易日／快照 SHA／Research Bundle SHA 正向與負向案例，以及 Stage 5→6 的跨 Run QA、Builder SHA、render manifest 綁定測試；已加入 Main Workflow 測試清單。這批最新 Stage 4–6 修改與新增測試尚待最新 CI 實際執行確認。

- Main Preview 清理確認：已查詢 main 完整 Git tree，`preview/2026-11-26*` 目前不存在，無需刪除；本次確認未觸及其他日期 preview、`index.html` 或 history。  
- Main Workflow 現況再次確認：capture/build 仍採手動 workflow_dispatch／內容 commit marker；Stage 4 編輯研究生產者尚未自動化，不能宣稱已具備定時全自動生產。Builder 仍為 `CANDIDATE_PENDING_OWNER_APPROVAL`，不可跳過 owner exact-SHA 核准。
- Stage 4 Bundle SHA 輸入完整性再收緊：不只逐一驗證已列出的 SHA，還強制 Stage 2 Receipt 必須完整提供 fixture、audit、manifest、observations 四種輸入引用，缺少任一項即拒絕產包。最新 Builder blob SHA：`d57346d75673b75387a6a0d0d22df7f58355d0f2`；PORT_MANIFEST 已同步。
- Stage 4 Research Bundle 完整性補強：除逐列市場狀態外，資料包現在直接嵌入完整 Observation bundle、44 列 Source Manifest 與 Market Snapshot Audit；Stage 4 編輯端不必依賴同名外部檔案才能檢視來源證據。README 同步修正，並新增內容存在與狀態統計斷言。提交：`9a63526`。

- Stage 2→Stage 4 交接強化：Stage 2 summary 傳遞 `market_status_counts`；Research Bundle 現在核對 Stage 2 Receipt、Summary、Manifest 的 44 列身份與逐列狀態一致，驗證 Receipt 內所有輸入檔 SHA，並將正式狀態帶入研究資料包；同時鎖定 Stage 2／Stage 3 的 report_date、trading_date、run_id 與 pinned main commit。Stage 4 validator 新增 Research Bundle trading_date 綁定。新增完整 44 列 handoff 測試。提交：`a88b76a`、`c323261`、`00dc7c6`、`44e4ee8`。

- Runner 移植清單同步：`PORT_MANIFEST.json` 為三支經 Main 修訂的 Stage 2 runner 記錄目前 Main blob SHA，狀態改為 `MAIN_PATCHED_STATUS_PRESERVATION`；原 Simulation source SHA 保留作來源沿革，不再誤標 Main 程式仍是原樣複製。既有 last_validation 明確標示為本輪修正前的舊驗證。提交：`2321e301fd8c9cc03442b757e029f3f52a7fa123`。

- Stage 2 Receipt 同步修正：`build_stage2_receipt.py` 將逐列 `market_data_status` 與 44 項狀態統計帶入凍結收據，並在新 Manifest 有提供時核對統計；舊測試／舊輸入可採相容推導，不提升未核實列狀態。新增 Receipt 回歸斷言。提交：`5db8f0cfe52ab4f6ae7165797854dc4e36e98082`。

- Stage 2 狀態保真修正：Source Manifest 新增逐列 `market_data_status` 與完整 `market_status_counts`，保留 `TOOL_READ_FAILURE`、`SOURCE_NO_DATA`、`SOURCE_UPDATE_PENDING`、`PENDING` 等狀態；既有 `verification_status` 維持相容，未核實資料仍不會變成 VERIFIED。Pre-build validator 現在逐列核對正式狀態及 44 項統計。新增兩種失敗狀態的回歸測試案例。相關程式提交：`08ef80fdde1ad9d0436c915faec4fe213c08ce14`、`605663a7ea933331fe39c23d797143dd5b7da6df`。

- [x] Phase 1／2 規範命名一致性：`validate_prebuild_stage_inputs.py` 模組說明由「SIM-1.4 fail-closed」修正為「Main-native」，避免把技術來源誤寫成 Main 執行期規範；僅修正說明文字，驗證邏輯未變。新 blob `648f35fb3a572d0d68435ce0d0949f647c4a2139`。
- [x] Phase 1 一致性修正：Stage 2／3 輸入規範明確改為引用 main `MASTER_WR.md` 與對應 contracts；SIM-1.4 僅保留為技術規範來源，不再列為 main Stage 執行期輸入。兩份 Stage WR 已提交並從 main 回讀驗證（Stage 2 blob `af892651b772366cb3f516c4149d9f2420c2ca70`；Stage 3 blob `992e97e980ceb05bb31001396703cbe4d7cd38cd`）。
- [x] Stage 1／2／5 WR 第一輪修訂與 GitHub 回讀。
- [x] Stage 1 建立 commit-pinned governance SHA 清單；Stage 5 逐檔比對當前 main，任何規範、Schema、Builder、Runner、依賴或 Workflow 漂移即停止。Stage 1 receipt 同時記錄 run-context SHA 與 governance 檔案數。
- [x] 修正 Stage 5 Runner 缺少 `os` import 及 Chart 3 handoff 狀態變數未定義。
- [x] Stage 5 加入 main Builder exact-SHA owner approval gate，抽成 `builder_approval.py` 並新增三種狀態測試；候選狀態不得標 REVIEW_READY。
- [x] MASTER WR、PORT_MANIFEST、Runner README 已同步 main 的 validate／capture／build 三模式流程，移除不存在的 `run_daily_report.py` 入口描述。
- [x] Stage 4 schema 已將 `run_id`、`market_snapshot_sha256`、`research_bundle_sha256` 設為必填；Stage 4 Runner 重新計算研究包 SHA，與 receipt、Run、行情快照逐一比對。
- [x] 修正 CI unittest 指令漏接續行的反斜線，並修正 SIM-1.4 相容測試 fixture 必須自行綁定合成 Run ID／snapshot SHA。
- [x] 最新 main-only 驗證 run `45819680821`：14 個 validation 步驟全數 success，包含完整治理 SHA inventory、Stage 2／截圖證據、Stage 4 research bundle 與三重 SHA 綁定、Builder approval tests、候選 Builder 及雙母版 DOM；capture/build jobs 均 skipped。

## Phase 1 已完成項目
- [x] 建立 `production/MASTER_WR.md` 並明確以 SIM-1.4 為技術來源，main 為獨立生產。
- [x] 將 SIM-1.4 Monday／Weekday 母版逐位元複製至 `production/templates/`。
- [x] 建立 `production/config/mother-template-manifest.json`，SHA 綁定兩份 SIM-1.4 模板。
- [x] 將 SIM-1.4 詳細母版 QA 契約複製至 `production/contracts/MOTHER_TEMPLATE_QA.md`。
- [x] 將 SIM-1.4 完整 WR 原文保存為 `production/reference/SIM-1.4_SOURCE_BASELINE.md`，作為可追溯技術依據。
- [x] 建立六份 Stage WR。
- [x] 第一輪 Stage WR 交叉核對：修正 Stage 1 自身規範輸入說明、Stage 2 sidecar 欄位 typo／狀態計數語意、Stage 5 Builder 核准與 REVIEW_READY 條件；六份文件均已從 main 回讀。
- [x] 建立／修訂 DATA_SCHEMA、STATUS_ENUM、SOURCE_POLICY、RUN、HANDOFF、HTML_BUILDER、QA、PUBLISH contracts。

## Phase 2 已移植項目
- [x] Stage 2 blank-first fixture bootstrap、截圖 sidecar parser、44頁 browser reader、ChatGPT Web observation validator、44-row source manifest、Stage 2 receipt、S&P 500 Chart 3 handoff。
- [x] Stage 2 browser reader default concurrency=4，且程式限制最大 concurrency=4。
- [x] Calendar source guard、earnings judgment、earnings price-reaction／consensus modules。
- [x] SIM-1.4 Builder 移植為 main candidate，路徑改為 production Manifest／雙母版／MASTER WR，輸出限制為 production/runs/<run_id>/review.html。
- [x] 主要 Stage 2、財報、母版、Builder regression tests 複製至 main；舊 Simulation 路徑已逐步清除。
- [x] 建立 main-only validation workflow；截至 run `45819680821`，14 個 validation steps 全數通過。此為 deterministic validation，不代表真實 E2E 或正式 Pipeline 已啟用。

## Stage 1–6 新增 Runner 進度（2026-11-26）
- [x] Stage 1 `create_run_fixture.py`：每次建立獨立 Run、NYSE trading date、鎖定雙母版／Manifest／規範／contracts／schema／Builder／Runner／Workflow governance SHA、calendar main commit，44 行 blank-first fixture。
- [x] Stage 2 `run_stage2.py`：4 頁並行、44-row observation／audit／manifest／receipt，S&P 500 verified 時產生 Chart 3 increment；MOVE delayed retry module 已移植。
- [x] Stage 3 `run_stage3.py`：從 Stage 1 pinned main commit 唯讀讀取本週及前一週 calendar，輸出 projection 與 receipt。
- [x] Stage 4 `run_stage4.py`：新聞／總結／五層分析／政治掃描 schema、日期窗口、來源欄位、research bundle 三重 SHA 綁定與市場快照不變檢查。
- [x] Stage 5 `run_stage5.py`：pre-build receipt、main Builder、artifact validator、母版 DOM、visual regression、interaction smoke；第一輪程式回讀另修正缺少 os import 與 Chart 3 handoff 狀態變數未定義。
- [x] Stage 5 Runner 的 `os` import、Chart 3 handoff 變數與 exact-blob approval gate 已修正，並通過 CI／fixture 驗證；正式 Builder owner approval 仍待核准。
- [x] Stage 6 `run_stage6.py`：main/preview 三檔白名單、遠端 bytes／SHA 回讀、Pages workflow dispatch 與公開 URL 驗證。
- [x] Capture 在 Stage 3 後自動產生 `stage4-research-bundle.json`：包含完整 44 項行情來源資料、未核實列、FedWatch、當週／上週行事曆與財報、Stage 1–3 receipts、瀏覽器觀察、source manifest、audit、所有輸入 SHA，以及截圖 sidecar／圖片 SHA。
- [ ] 尚未建立自動產生 `report-content-YYYY-MM-DD.json` 的 LLM 編輯研究與自動提交交接。
- [x] Stage 2 Chart 3 increment 已由 main Workflow 僅提交 `data/tac-chart3/sp500_daily_increment.jsonl`，並明確 dispatch `tac-chart3-sp500-increment-merge.yml`；等待真實 S&P 500 VERIFIED run 驗證。
- [x] Stage 5 main Builder 已加精確 SHA 核准紀錄 gate，並由獨立模組及測試執行；目前 `CANDIDATE_PENDING_OWNER_APPROVAL`，未獲核准不得產生正式 REVIEW_READY。Stage 5／6 尚未用真實當日輸入完成 E2E。

## Phase 1 未完成／需收尾
- [ ] 完成 MASTER／六份 Stage WR／contracts／Runner 全面逐欄一致性檢查；第一輪只處理已確認問題，尚未完成 SIM-1.4 全文逐條比對。
- [x] 列出 Builder 主程式精確 SHA 與來源 SHA；建立 `production/config/builder-approval.json`，預設候選待核准，Stage 5 強制檢查 exact blob SHA 與 APPROVED_MAIN 狀態。
- [ ] 完成 Builder 所有 import dependency、可寫入 selector、CLI 及路徑適配的完整清冊；SIM Builder 核准不等於 main port 已核准。
- [ ] 明確處理 SIM-1.4 的四頁並行規則與原 Workflow 中仍殘留的 concurrency=2。
- [ ] 完成新 Manifest／QA contract 的 schema 與自動檢查。
- [ ] 對照完整 SIM-1.4 原文核對全部細節；目前主文件已覆蓋核心責任，但仍需驗證所有歷史規則與 selector 契約。
- [ ] 建立 Stage 2–4 pre-build receipt 欄位與 Builder provenance 一致性規格。
- [x] Stage 5 Runner 已加入 main Builder exact blob SHA 與 `APPROVED_MAIN` owner approval 檢查；候選狀態不得產生正式 REVIEW_READY。

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

- 2026-11-26 冬令時間修正：美股 NYSE core session 16:00 ET 收盤，EST 對應台灣 05:00；Main capture cron 已由 UTC 20:45（台灣 04:45）改為 UTC 21:05（台灣 05:05）。Workflow commit `ac56284fdac80d1ae0e65c05ec922cea5f191c5e`，新 workflow blob SHA `ecad05e61de0814f66a89ffb8901124b00fcc0b3`。Manifest 已同步；首次排程實跑及 CI 尚待確認。夏令時間自動切換仍是未完成項目。

- 2026-11-26 夏令／冬令自動切換：Workflow 設置兩個 UTC schedule（20:05、21:05，週日到週四 UTC），新增 `schedule-window` preflight，依 `America/New_York` 當下 DST 狀態比對 `github.event.schedule`，只放行正確的觸發器。美國 EDT 時台灣 04:05 啟動（美股 04:00 收盤後 5 分鐘）；美國 EST 時台灣 05:05 啟動（美股 05:00 收盤後 5 分鐘）。GitHub schedule 可能延遲，因此以事件所帶 cron 字串判斷，不依賴 runner 實際啟動分鐘。Workflow blob SHA `33bb98c9757093e2aa9ea73bf4a5b8044e3c7fd5`，Workflow commit `efbc6c0c41bf07458670db3b2e1ce75b68deb6a9`；需等待 CI 與兩季實際排程觀察驗證。
