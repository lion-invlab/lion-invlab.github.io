# TAC 投資早報 R3｜main 重建計劃表

更新：2026-11-27（Asia/Taipei）
正式目標：main 原生獨立生產；審核版直接交付 main/preview；使用者核准後才更新 index.html。
硬性邊界：Simulation branch 全程唯讀、不修改、不重寫、不停用其工作流程；main 舊母版／舊 WR／舊早報 Pipeline 可退役，不作新系統依賴。

## 總體階段表

| Phase | 工作目標 | 必要交付 | 完成判準 | 狀態 |
|---|---|---|---|---|
| 0. 資產盤點與架構定案 | 盤點 main、標出唯一資料來源／寫入者／Workflow 衝突，定案新目錄與權責 | PHASE0_INVENTORY、架構責任與風險清單 | main tree、母版、calendar、Chart 3、Pages、archive、舊 workflows 均已盤點；依賴與風險有記錄 | DONE |
| 1. 規範與契約定版 | 以 SIM-1.4 技術內容為基準，重寫 main MASTER WR、六份 Stage WR、共用 contracts、雙母版 Manifest／QA；排除舊 main 規則衝突 | MASTER_WR、STAGE_1–6、DATA_SCHEMA、STATUS_ENUM、SOURCE_POLICY、RUN、HANDOFF、BUILDER、QA、PUBLISH、母版 Manifest／QA | 每項規則有唯一權威；Stage 間輸入輸出一致；44 欄位、截圖優先、4 頁並行、Stage3唯讀、五層分析、Builder／交付責任一致；交叉引用及 SHA 經回讀 | IN_PROGRESS（六份 Stage WR 已逐份回讀並完成第一輪修訂；尚待完整 SIM-1.4 逐條對照與 Runner／Contract 自動一致性驗證） |
| 2. Runner 與 Builder 移植 | 將 SIM-1.4 可用模組移植／適配至 production，建立 main 唯一 Runner；不直接引用 simulation 路徑 | production/runner、Builder、Stage adapters、Stage 1–6 Runner、測試 | 不依賴 Simulation runtime 路徑；使用 production templates／Manifest；blank-first、截圖 sidecar、4 concurrency、Stage2 receipt、Chart3 append、calendar readonly、Stage 5 QA、Stage 6 delivery 均可執行 | IN_PROGRESS（Stage 1–6 Runner 已建立；Stage 2 Chart 3 commit／merge dispatch 已接入 Workflow；Stage 5/6 尚未真實 E2E 驗證） |
| 3. Main Workflow 與發布管線 | 建立唯一 tac-production.yml，接通 Stage 1–6、Chart 3 handoff、權限／concurrency／main preview三檔白名單／Pages dispatch；整理舊 main workflow 衝突 | .github/workflows/tac-production.yml、Workflow wiring tests、舊流程退役清單 | 新 Workflow 只 checkout main；單一正式入口；Chart 3 增量另行受控提交；Stage 6 明確 dispatch Pages；舊 Simulation-to-main preview 流程在新 E2E 通過後退役 | IN_PROGRESS（唯一 weekday schedule 由 Stage 1 啟動 Stage 1–3；ChatGPT continuation automation 已配置為同 Run Stage 3 後接手 Stage 4–6；但 schedule Capture 首次真實觸發、當日 editorial JSON、Builder exact-SHA 核准及 Stage 4–6 E2E 尚未全部驗收） |
| 4. 全面整合測試 | 44行情、calendar、earnings、news、五層分析、雙母版、DOM、視覺互動、Chart3、delivery 全鏈整合 | deterministic tests、browser QA、negative tests、integration receipts | 兩種母版都通過；狀態分類不崩潰；不重抓已鎖定行情；跨 Run 不混資料；僅三檔 preview 寫入；Pages公開預覽驗證 | IN_PROGRESS（main-only validation 14 個步驟全數通過，含 Stage 1 governance SHA、Stage 2／截圖、Stage 4 research bundle、Builder／財報 deterministic tests、候選 HTML DOM contract；真實 44 頁擷取、Stage 5/6 delivery 與雙母版完整 E2E 尚未驗收） |
| 5. 真實資料 E2E | 用當日真實資料完整執行六階段，輸出審核版；不沿用舊 fixture 價格；記錄Stage2 4頁並行實際耗時 | 完整 Run artifact、preview HTML、QA sidecar、delivery receipt、E2E report | 六階段均有真實輸入輸出與SHA；44項有值或狀態；Chart3 SP500增量同步；calendar只讀；HTML／QA／Pages驗證完成；無未揭露阻塞 | NOT_STARTED |
| 6. 排程與正式切換 | Main Stage 1–3 capture EDT 04:05／EST 05:05；ChatGPT Stage 4–6 continuation EDT 04:15／EST 05:15；04:35 calendar、05:30 Chart3 各司其職；保留使用者正式首頁核准權 | 首次 scheduled capture evidence、同 Run Stage 4 handoff、Builder 當前 exact-SHA 核准、真實 E2E、舊流程退役證據 | 主排程與接續任務已設定；首次 schedule Capture 真實觸發、同 Run 自動交接、Builder 當前 exact-SHA 核准、真實 E2E、正式切換與舊流程退役仍未完成 | IN_PROGRESS |

## 2026-11-26 持續修訂紀錄
- Main Stage 1–3 排程入口已加入 `.github/workflows/tac-production.yml`：GitHub Actions cron `5 21 * * 0-4` UTC，即美國冬令時間期間台灣時間週一至週五 05:05；排程事件直接執行 Main capture-and-calendar（Stage 1–3），workflow_dispatch 的 validate/capture/build 手動模式保留。這個排程不會執行 Stage 4–6，也不會修改首頁；Stage 3 後仍以同一 Run 的 `capture-stage-receipt.json` 等待編輯內容。冬令時間已修正為收盤後 05:05 啟動，避免 05:00 收盤前擷取。夏令時間切換仍待加入自動 DST 排程邏輯。
- 排程 workflow 使用雙 UTC cron：EDT 20:05 UTC、EST 21:05 UTC，對應台灣次日 04:05／05:05；schedule-window 依 New York DST 選取唯一正確觸發。此設定已由 2026-11-27 回讀確認，但 11/27 未找到 schedule Capture Run，仍須以後續真實 schedule run 驗證。

- Main CI 最新結果：Workflow Run `45824747088`（commit `9c779455278d3bde84abe70324dedf5cb0db626d`）完成且 conclusion=success。逐步確認 Main-only checkout、模組編譯、雙母版 SHA、Stage 2／Pre-build 測試、Builder／earnings 測試、Candidate Builder fixture、母版 DOM contract 全部成功；capture/build job 為 skipped，故不代表真實資料 E2E。
- Stage 4→5→6 交接加固：Stage 4 receipt 新增 `trading_date`；Stage 5 驗證 Stage 4 Run／報告日／交易日、凍結市場快照前後 SHA、Research Bundle SHA 與 Stage 2 snapshot SHA 一致，並將交易日、Stage 4 receipt SHA、Research Bundle SHA、market snapshot SHA、Builder blob SHA 寫入 Stage 5 receipt。
- Stage 6 加強：核對 Stage 5 Run／雙日期、QA sidecar 日期、render manifest SHA、HTML SHA、Builder SHA；回讀 Stage 4 receipt SHA 並核對 editorial Run／snapshot／bundle 綁定後才允許交付。
- 上述 Stage 4／5／6 程式與 Stage 4 日期綁定測試已提交 Main，SHA 已同步至 PORT_MANIFEST。新增專用 `test_stage56_handoff.py`，涵蓋 Stage 4→5 的交易日／快照 SHA／Research Bundle SHA 正向與負向案例，以及 Stage 5→6 的跨 Run QA、Builder SHA、render manifest 綁定測試；已加入 Main Workflow 測試清單。這批最新 Stage 4–6 修改與新增測試尚待最新 CI 實際執行確認。

- Main Preview 清理確認：已查詢 main 完整 Git tree，`preview/2026-11-26*` 目前不存在，無需刪除；本次確認未觸及其他日期 preview、`index.html` 或 history。  
- Main Workflow 現況：weekday schedule 是唯一 Stage 1 主啟動入口，負責 Stage 1–3；ChatGPT continuation automation 只負責 Stage 3 完成後的 Stage 4–6，不呼叫外部 LLM API。自動化已設定但未完成真實 schedule Capture 與全鏈 E2E。Builder 當前 blob 與歷史核准 SHA 不一致，必須取得當前 exact-SHA 核准，不可跳過。
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

- 2026-11-26 夏令／冬令自動切換：Workflow 設置兩個 UTC schedule（20:05、21:05，週日到週四 UTC），新增 `schedule-window` preflight，依 `America/New_York` 當下 DST 狀態比對 `github.event.schedule`，只放行正確的觸發器。美國 EDT 時台灣 04:05 啟動（美股 04:00 收盤後 5 分鐘）；美國 EST 時台灣 05:05 啟動（美股 05:00 收盤後 5 分鐘）。GitHub schedule 可能延遲，因此以事件所帶 cron 字串判斷，不依賴 runner 實際啟動分鐘。Workflow blob SHA `c2d97b2e77a84f28719b60c5f60c6654d1fac1fa`，Workflow commit `f31b449872147cb5be7be18541d6f8657cf0502f`；需等待 CI 與兩季實際排程觀察驗證。


## 2026-11-26 排程與交接狀態校正（最新回讀）
- Main Stage 1–3 capture 已設定於唯一入口 `.github/workflows/tac-production.yml` 的 DST-gated schedule：EDT 台灣 04:05、EST 台灣 05:05；兩個 UTC cron 由 `schedule-window` 依 `America/New_York` DST 只放行一個。這是「已設定、尚待首次 scheduled run 驗證」，不可記為未設定，也不可記為已實際成功。
- Main Stage 4 ChatGPT Automation 已由原早報任務 ID 改寫為 Main-only，設定 EDT 台灣 04:15／EST 台灣 05:15；inactive slot no-op。已回讀確認 enabled、prompt 的 Main-only 邊界及確切 Stage 4 WR／schema 路徑。Chart 3 05:30 任務已回讀確認監控 Main Stage 4；行事曆 04:35 任務保持不變。
- Stage 4 handoff 說明已更新為符合上述排程，Commit `9b7698465488d0361a11413eeb3488ff24c201fc`；CI Run `45828484006` completed/success。該 run 是 push validation，capture/build jobs 並未執行。
- **目前排程首次實跑尚未發生／尚未取得證據**：下一個工作日的正確 DST 時段需確認 schedule event、唯一 Capture Run、Stage 1–3 receipts、Research Bundle SHA 與 Stage 4 Automation 接手紀錄。
- Builder 仍是 `CANDIDATE_PENDING_OWNER_APPROVAL`，exact Main Builder SHA `20eefe57d6f3b389157c01b8532cae3a69128a02`，`approved_by_owner=false`。未經使用者明確核准，不可觸發 build marker 或宣稱 REVIEW_READY。
- Phase 6 由 NOT_STARTED 更正為 IN_PROGRESS（排程已設定；首次排程實跑、同 Run 自動交接、Builder 核准及真實 E2E 尚未完成）。整體 Pipeline 仍未達正式上線／驗收標準。

## 2026-11-27｜全面回讀後的重建計畫校正（先規劃，未修改 Runner）

本節優先於本文件 2026-11-26 的舊狀態敘述。原因：11/27 回讀發現計畫表、Phase 0 inventory、README、Builder approval record 與實際程式／Workflow 已出現狀態漂移。此輪先完成計畫校正，不以單點程式修改代替通盤重建。

### A. 本輪實際基準與當日早報狀態

- 回讀時間：2026-11-27（Asia/Taipei；本次檢查約 06:00）。
- Main HEAD：`73be77f835a6bfa8883f64b8c6c281a7a968303f`；最新提交更新 W48 ECB meeting account actual。
- Main 唯一生產 Workflow：`.github/workflows/tac-production.yml`，blob SHA `c2d97b2e77a84f28719b60c5f60c6654d1fac1fa`。
- 05:05 台灣時間冬令 capture cron 已存在（UTC 21:05）；但截至本次 GitHub Actions 最新 run 清單回讀，尚未找到 2026-11-27 當日 `tac-production.yml` 的 schedule/capture run。不得將 cron 存在視為今日已啟動或成功。
- Main Stage 4 Automation 已啟用，冬令時段為 05:15；本次 peek 顯示 11/27 05:15 run 為 `in_progress`，依其規則等待當日唯一 Capture 最多 70 分鐘。若 Capture 未成功，不得使用舊 Run／舊 Fixture 代替。
- 因尚未取得當日 Capture Run 與 Stage 1–3 receipts，11/27 審核版目前沒有可用的正式 Run 輸入；本計畫不宣稱今日早報已產出。
- 11/27 當日資料日期不可用單一 NYSE 日期套用全部 44 項。美股 11/26 感恩節休市，但亞洲等市場須按各自交易所日曆判斷 11/26 是否有交易。

### B. 已確認的跨文件／跨模組差異

| ID | 實際發現 | 影響範圍 | 必須同步處理 |
|---|---|---|---|
| AUD-01 | `MAIN_REBUILD_PLAN.md`、`PHASE0_INVENTORY.md` 仍含 11/26 以前的基準與過時資產描述；Phase 0 DONE 不代表新 production 架構已完成重新盤點 | 全域架構、Workflow、資料寫入者 | 重新盤點 main tree、workflow、calendar、Chart 3、preview/history、排程與權限；更新唯一現況基準 |
| AUD-02 | Builder approval JSON 已是 `APPROVED_MAIN`、`approved_by_owner=true`，且當前 Builder blob SHA 為 `20eefe57d6f3b389157c01b8532cae3a69128a02`；但 README、計畫表仍寫候選未核准，approval JSON 的 validation limitation 又錯寫 no owner approval | Stage 5、README、計畫表、Stage 1 governance SHA | 統一狀態文字；保留真實限制：已核准 Builder exact SHA，但真實資料 E2E 尚未完成 |
| AUD-03 | `create_run_fixture.py` 以 `last_nyse_session()` 決定單一 `trading_date`，再把該日期寫入所有 44 項 source.data_date；Stage 2 reader 也只接收單一 target date | Stage 1、Stage 2、Schema、Manifest、Receipt、Stage 4 分析 | 改為逐商品／市場資料日期；保留報告日與主要美股交易日概念，但不得將 NYSE 日期套用全市場 |
| AUD-04 | SIM-1.4 §3.3 明定依各標的所屬交易所／主管機關官方交易日曆核對；Main Stage 2 WR／SOURCE_POLICY 尚未完整納入「查無目標列先查官方假期」流程 | Stage 2 規範、狀態分類 | 正式承接 SIM-1.4：先查資料列；查無資料時查官方市場日曆；官方確認休市才 CLOSED，並記錄假期名稱 |
| AUD-05 | Main browser reader 對可讀頁面找不到目標日期，回傳 `TARGET_DATE_NOT_FOUND`；bootstrap 最後只保留 PENDING／原 read_status，未正規化成契約要求的 `SOURCE_NO_DATA`，也未先接市場假期核對 | Reader、Bootstrap、Manifest、Receipt、STATUS_ENUM、QA | 統一觀察狀態轉換；保留 MOVE 特例 `SOURCE_UPDATE_PENDING`，不得將一般開市但查無資料混為更新延遲 |
| AUD-06 | Main CLOSED bootstrap 目前把行情點位與漲跌欄都顯示「休市」；既有使用者規則為點位顯示 `-`、漲跌欄顯示當地假期名稱（如「感恩節」） | Bootstrap、Schema、Builder、QA | CLOSED 必須帶 `holiday_name`、官方日曆證據與市場識別；點位 `-`、漲跌欄假期名稱 |
| AUD-07 | Main 有 CLOSED 狀態及舊 `MARKET_CLOSED` alias，但缺少可證明各市場休市的日曆判斷來源／映射；不能因頁面無資料或 Cloudflare 阻擋就推定休市 | 市場日曆、來源政策、Runner | 建立 44 項 instrument-to-calendar mapping；對非交易所／跨時段商品定義適用日曆與未知狀態，不得猜測假期 |
| AUD-08 | Main Runner README 說沒有自動編輯研究／交接；實際存在 Main-only Stage 4 ChatGPT Automation，但同 Run 自動交接與今日實際執行仍未證明 | Stage 4、Workflow、Automation、Handoff | 改寫為「Automation 已設定、實際 Capture→Stage 4→build E2E 未驗證」；用同一 Run ID／snapshot SHA／bundle SHA 驗收 |
| AUD-09 | Main CI push validation 成功的 run（例如 45829664051）只有 validate job；capture/build jobs skipped。這不是真實行情擷取或完整早報 E2E | Phase 4/5、Runner、QA | 嚴格區分 deterministic validation、capture run、build run、完整真實 E2E |
| AUD-10 | Chart 3、S&P 500 append handoff、calendar writer、舊 workflow/archive、Pages 的寫入責任需按目前 Main 實際程式與排程重新確認；不可只沿用 Phase 0 舊盤點 | Chart 3、Calendar、Stage 6、Pages、History | 逐項確認唯一 writer、commit path、workflow trigger、SHA／防重與公開部署責任 |

### C. 修訂後的分階段執行順序

| 子階段 | 工作範圍 | 必須交付／完成判準 | 目前狀態 |
|---|---|---|---|
| R0｜現況重新盤點 | 更新 Main HEAD、production tree、全部 workflow／排程、資料庫、Chart 3、preview/history、Builder 與權限基準 | 新版 PHASE0 inventory；唯一 writer／觸發器／分支邊界矩陣；所有現存與退役 workflow 清單 | IN_PROGRESS |
| R1｜SIM-1.4 全文差異矩陣 | 對照 SIM-1.4 source baseline、MASTER WR、六份 Stage WR、全部 contracts、Schema、Manifest、QA、Runner、tests | 每條規則標記 MATCH／MISSING／CONFLICT／NOT_APPLICABLE；每項缺口有唯一修正位置及下游依賴 | NOT_STARTED |
| R2｜契約與資料模型定版 | 先統一 report_date、per-instrument data_date、market calendar、holiday evidence、狀態 enum、Observation、Manifest、Receipt、handoff SHA | Schema／Stage WR／SOURCE_POLICY／STATUS_ENUM／Receipt／QA 完全一致；通過跨檔自動一致性檢查 | NOT_STARTED |
| R3｜Stage 1–3 Capture 修正 | 修正 per-market 日期與假期判斷；44 項 blank-first、截圖優先、4 頁並行、來源分類、FedWatch、Calendar readonly | 每個市場日期可獨立判斷；假期正確 CLOSED；開市缺資料不冒充 CLOSED；所有 44 項有值或正確狀態；Stage 3 唯讀 | NOT_STARTED |
| R4｜Stage 4 研究與同 Run 交接 | 讀取同一 Capture 的 Research Bundle；產生完整新聞 5+10、三段總結、情緒、五層分析、六領域政治掃描及策略；生成綁定 JSON | Run ID、market snapshot SHA、research bundle SHA 完全相符；自動交付 build marker；無舊資料 fallback | NOT_STARTED（Automation 已設定，E2E 未驗證） |
| R5｜Stage 5 Builder／QA | 核對 Builder exact SHA approval、DOM slot、資料／內容／結構／視覺互動／整合 QA；同步修正 README、approval evidence 文字 | Builder exact SHA = APPROVED_MAIN；真實資料 Build 成功；四類 QA 收據完整；不將 PARTIAL 偽稱 REVIEW_READY | NOT_STARTED（Builder 已核准；真實 E2E 未測） |
| R6｜Stage 6 Main Preview | 僅寫三個日期化 preview 檔；遠端 bytes／SHA 回讀；Pages workflow success；公開 URL 實際讀回日期、Run ID、HTML SHA | HTML、QA、delivery 三檔完整；Pages 公開 URL 驗證通過；index.html 與正式 history 未被未授權修改 | NOT_STARTED |
| R7｜排程／正式切換驗收 | 05:05 capture、05:15 Stage 4、04:35 calendar、05:30 Chart 3 互相銜接；確認唯一生產入口與舊流程隔離 | 至少一輪 scheduled 真實資料完整 E2E；無重複 Run／重複 writer；Pages verified；保留使用者首頁核准權 | NOT_STARTED |

### D. Stage 2 市場日期／假期處理的正式設計要求（納入 R2/R3，不單獨打補丁）

1. 44 項各自保留 instrument identity、交易所／主管機構、適用交易日曆、當地時區、資料日期及來源頁 URL；不可再用單一 NYSE session date 覆蓋全部 44 項。
2. 對每項先讀取指定日期的 Historical Data。若頁面／表格不可讀，標 `TOOL_READ_FAILURE`，不得推定休市。
3. 若表格可讀但找不到指定日期，先查該標的所屬官方交易所／主管機關行事曆；官方確認休市時，標 `CLOSED` 並保存假期名稱、日期、日曆來源 URL 與查核時間。
4. 若官方日曆確認當日有交易，則按來源契約判斷：一般項目查無目標列標 `SOURCE_NO_DATA`；只有明確規定允許延遲觀察的項目（例如 MOVE）才可使用 `SOURCE_UPDATE_PENDING`。不得無限重試。
5. 若日曆資料不可取得、日曆映射不明或商品不適用單一交易所日曆，標示待核實／相應錯誤，不得猜假期名稱，也不得標 CLOSED。
6. CLOSED 顯示：價格／點位欄為 `-`；漲跌幅／漲跌點欄為官方確認的當地假期名稱（例如「感恩節」）；來源說明保留正式來源與假期日曆證據。不得將兩欄都顯示「休市」。
7. 單項 CLOSED、SOURCE_NO_DATA、SOURCE_UPDATE_PENDING 或 TOOL_READ_FAILURE 不得造成 44 項流程 crash；其餘項目及無依賴 Stage 繼續，未核實值不得進入分析作為事實。
8. 任何日期／狀態／顯示規則變更，必須同步 Fixture、Observation schema、Manifest、Receipt、Stage 4 bundle、Builder、四類 QA 與測試，不可只修改 Stage 2 一個檔案。

### E. 執行與保護規則

- 先完成 R0/R1/R2 並回讀本計畫，再開始 R3；未完成跨檔差異矩陣前不修改 Runner。
- R3 每個可交付改動都要回頭核對 MASTER／六份 Stage WR／Schema／Manifest／Receipt／Builder／QA／Workflow，並更新本計畫。
- 只允許 Main-native 修改；Simulation branch、SIM-1.4 runtime、Simulation workflows 全程唯讀。
- 不使用外部 LLM API；Stage 4 研究與撰稿由本次 ChatGPT 執行，依既有 Automation／Workflow handoff。
- 不繞過 Cloudflare、不以未核准來源取代 Investing.com、不用舊 Fixture／舊 Run 補值、不將單項缺值升格為全流程停工。
- 審核版只能交付 main/preview 三檔；正式首頁 index.html 與正式 history 只在使用者明確核准後更新。
- deterministic CI success 不等於真實資料 E2E；排程存在不等於 schedule 已觸發；Builder approval 不等於 Stage 5/6 已完成。

### F. 本次實際變更範圍

- 本次只校正本重建計畫表，記錄回讀證據、差異與後續分拆；沒有修改 Runner、Builder、Schema、Manifest、Workflow、排程、calendar JSON、preview、index.html 或 Simulation。
- 下一個執行動作固定為完成 R0/R1 全面盤點與差異矩陣；不得跳過規劃直接進入 Stage 2 單點修改。

### G. R0 追加盤點｜Workflow、排程、契約與執行清單（2026-11-27）

#### G1. Main 現有 Workflow inventory

本次重新讀取 `.github/workflows/`，目前共 23 份 Workflow。以下按 TAC 早報生產相依性分組：

| Workflow | 目前責任／觸發 | R0 判定 |
|---|---|---|
| `tac-production.yml` | Main 唯一新生產入口；雙 UTC cron、DST gate、push validation、workflow_dispatch capture/build | 保留為唯一 Main Stage 1–6 入口；須補首次 scheduled capture 實跑證據 |
| `tac-simulation-lab.yml` | Simulation branch push／手動觸發；checkout Simulation，QA 後可寫 main/preview 三檔 | 仍是潛在跨分支 preview writer；Main 正式切換前必須定義隔離／停用策略，但不得修改 Simulation branch |
| `tac-market-source-capture.yml` | 手動觸發、checkout Simulation，僅 Simulation 行情診斷 | Simulation 專用，Main 不可引用；保留唯讀 |
| `archive_index.yml` | index.html push 與每日 UTC 17:10 schedule，自動建立 history archive／index | 與正式首頁核准及歷史封存責任需整併；避免未核准封存 |
| `pages.yml` | preview/history/index push、手動 dispatch、指定 Chart 3 workflow_run 成功後部署 | 沿用唯一 Pages 部署器；Stage 6 需核對實際 dispatch、公開 URL 與 SHA |
| `tac-chart3-incremental.yml` | Chart 3 FRED／ALFRED 增量資料更新 | 保留風險指標序列更新；不得競爭 S&P 500 writer |
| `tac-chart3-sp500-increment-merge.yml` | 手動 dispatch／指定程式路徑 push；合併已驗證 S&P 500 增量 | Stage 2 handoff 的下游 merge writer；須驗證防重、日期衝突、唯一資料表及成功 receipt |
| `tac-chart3-bootstrap.yml`, `tac-chart3-ingest.yml`, `tac-chart3-stress-analysis-tests.yml`, `chart3-preview-visual-qa.yml`, `tac-sp500-increment-qa.yml` | Chart 3 bootstrap／ingest／QA／視覺測試 | 盤點各自寫入路徑與觸發關係，禁止重複寫入同一資料 |
| 其餘 12 份非早報核心 Workflow | 公司資料、其他圖表、母版保護、Simulation workflow lint、MMF、volatility 等 | 保留；只在證實會修改早報受保護資產時才納入改造 |

#### G2. 排程資料存在明確漂移

- `production/config/schedule.json` 目前 daily_report.local_time 仍寫 05:25。
- 實際 Main Workflow 冬令 capture cron 是台灣 05:05；Main Stage 4 Automation 冬令時段是台灣 05:15；Chart 3 Automation 是台灣 05:30；Calendar updater 是台灣 04:35。
- 因此 schedule.json 不能再當成目前排程真相；R2 必須統一 schedule.json、MASTER WR、Workflow cron、Automation prompt、handoff 文件及驗收紀錄。
- 本次確認 05:05 cron 已寫入，但 11/27 當日尚未在 Actions run 清單看到對應 schedule run；不得以排程設定代替實際觸發證據。

#### G3. 執行與歷史狀態證據

- Main commit `620c0f22...` 的 Builder approval push validation run `45829664051`：`validate-main-production` success；`schedule-window`、`capture-and-calendar`、`build-and-deliver` 均 skipped。這只證明 deterministic validation 成功，不是當日行情擷取或報告 E2E。
- 本次計畫文件提交後，Main run `45897439038` 正在執行 `validate-main-production`；capture/build jobs skipped。此 run 也不能視為早報生產成功。
- Simulation branch 的舊 workflow `tac-simulation-lab.yml` 仍存在 push／workflow_dispatch 觸發；最新回讀的相關歷史 run `45798889894`（2026-11-26 push）結論 failure。此為 Simulation workflow 證據，不得拿來當 Main 生產結果。
- Calendar Automation 11/27 04:36 已完成 W48 更新並回讀；Main 最新 HEAD 因而更新到 `73be77f...`。Stage 3 仍只能唯讀此週 JSON。
- Main Stage 4 Automation 11/27 05:15 run 在本次查核時仍為 `in_progress`，等待當日唯一 Capture；不得重複 run_now 或拿舊 Run 替代。

#### G4. Main 文件與資料契約的追加差異

| ID | 文件／契約 | 目前差異 | 修正安排 |
|---|---|---|---|
| AUD-11 | `production/config/schedule.json` | daily_report 仍寫 05:25，與實際 05:05 capture／05:15 Stage 4 不一致 | R2 統一排程單一真相，保留 04:35 calendar 與 05:30 Chart 3 |
| AUD-12 | `production/runner/PORT_MANIFEST.json` | builder_approval 仍寫 CANDIDATE_PENDING_OWNER_APPROVAL；但 approval record 與 Builder exact SHA 已是 APPROVED_MAIN | R2 同步實際 Builder 核准狀態、當前 SHA、CI evidence 與「真實 E2E 尚未完成」限制 |
| AUD-13 | `production/contracts/MOTHER_TEMPLATE_QA.md` | Main contract 仍要求讀取 Simulation branch 的 `simulation-lab/TAC_WORK_RULES_SIM.md`，與 Main-only runtime／權威文件邊界不夠清楚 | R1/R2 改為引用 Main 已封存的 `production/reference/SIM-1.4_SOURCE_BASELINE.md` 與 Main MASTER WR；不得在 Main runtime checkout／讀取 Simulation |
| AUD-14 | `tac-simulation-lab.yml`／`archive_index.yml`／`pages.yml` | 舊 Simulation workflow 仍可向 main/preview 寫入；archive workflow 仍有獨立自動封存排程；Pages 同時承接多種來源 | R0 完成觸發／寫入者／部署圖；R7 才執行安全切換，不能在真實 E2E 前任意停用或同時放行兩套生產 |
| AUD-15 | `production/contracts/DATA_SCHEMA.md` 與 Runner | Schema 每列可保存交易日期，但 Stage 1／Stage 2 實際仍以單一 NYSE `trading_date` 當 44 項 target date | R2 定義全域主要交易日與逐項 market_data_date／data_date 的關係；R3 實作並測試跨市場日期 |
| AUD-16 | `production/runner/README.md`／`PORT_MANIFEST.json`／`MAIN_REBUILD_PLAN.md` | 自動編輯研究能力、Builder approval、schedule cutover 狀態各自描述不一致 | R2 統一文件狀態；只記錄實際存在的 Automation 與已驗證的執行結果，不誇大自動化完成度 |

#### G5. 本輪新增盤點數量

- Main workflows：23。
- Stage WR：6。
- Shared contracts：9（含 STATUS_ENUM）。
- Main runner：本次目錄回讀含 Runner、Builder、validators 與 tests；需以 PORT_MANIFEST 完成逐檔 SHA／來源／依賴矩陣。
- Config：4 個主要檔案（Builder approval、雙母版 Manifest、report data template、schedule）。
- Input：7 個主要 schema／README 檔案。
- Main 已存在 SIM-1.4 pinned source baseline；此為 Main repo 內的規則參考快照，不等於 Main 可讀寫 Simulation runtime。

#### G6. R0/R1 尚未完成的工作

1. 將 23 份 Workflow 的完整觸發、寫入路徑、權限、分支及 concurrency 逐項盤成 machine-readable matrix。
2. 讀取 PORT_MANIFEST 全部 253 行，逐檔核對當前 Main blob SHA、source SHA、copy/adaptation status、測試覆蓋與未完成依賴。
3. 完成六份 Stage WR、九份 contracts、Schema、兩份 screenshot/web observation schema、44 項 Manifest、兩份母版、Builder approval、Builder、六階段 Runner 與 tests 的逐條 SIM-1.4 規則對照。
4. 完成唯一 writer matrix：Calendar JSON、44 行情 Fixture／snapshot、Chart 3 ALFRED、S&P 500 daily increment、review HTML、QA sidecar、delivery receipt、Pages、history archive、index。
5. 完成後才把 R0 標記 DONE、R1 標記 PASS，並凍結 R2 資料模型；目前 R0 仍 IN_PROGRESS。


### H. R0 實際回讀校正｜2026-11-27（追加）

#### H1. Main Git tree 與 Workflow 數量校正
本次以 GitHub main recursive tree API 回讀，不沿用前版盤點數字：
- Main recursive tree 回傳 `truncated=false`。
- `.github/workflows/` 實際為 **24 份**，不是 G1/G5 所記的 23 份；原盤點漏列 `tac-simulation-run-monitor.yml`。
- `production/` 實際 107 個 tree entries（含目錄）；Runner、六份 Stage WR、九份 contracts、四份主要 config、四種 input schema／README、雙母版均已列入目錄盤點。
- `preview/` 有 39 個 entries；其中可見多種歷史／Simulation preview 命名，需在 R0 writer matrix 中按 workflow 觸發來源區分，不能將整個 preview 目錄視為 Main 新流程獨占。
- Chart 3 的 `data/tac-chart3/` 有 33 個 entries；包括 FRED/ALFRED 系列、歷史 S&P 500 compact data 及 `sp500_daily_increment.jsonl`。

#### H2. 24 份 Workflow 觸發器清冊（main 回讀）
| Workflow | 已讀到的觸發器 | R0 初步分類 |
|---|---|---|
| archive_index.yml | push、workflow_dispatch、schedule（17:10 UTC，週日–週四） | History/index writer，須確認 push paths 與核准邊界 |
| chart2-preview-browser-qa.yml | workflow_dispatch、pull_request、push | Chart 2 QA |
| chart3-preview-visual-qa.yml | workflow_dispatch、workflow_run、pull_request、push | Chart 3 QA／部署相依 |
| company_nasdaq100.yml | workflow_dispatch、schedule（21:20 UTC，週日–週四） | 公司／市場資料更新 |
| company_profiles.yml | workflow_dispatch、schedule（週六 21:40 UTC） | 公司資料 |
| company_profiles_nasdaq100.yml | workflow_dispatch、schedule（週六 22:00 UTC） | 公司資料 |
| main.yml | workflow_dispatch、schedule（21:10 UTC，週日–週四） | S&P 500 波動資料 |
| mother-template-guard.yml | push、workflow_dispatch、pull_request | 母版保護／QA |
| pages.yml | push、workflow_dispatch、workflow_run | GitHub Pages 部署器 |
| simulation-workflow-lint.yml | push | Simulation YAML lint |
| tac-chart3-bootstrap.yml | workflow_dispatch | Chart 3 bootstrap |
| tac-chart3-incremental.yml | push | Chart 3 FRED／ALFRED 增量 |
| tac-chart3-ingest.yml | workflow_dispatch | Chart 3 歷史匯入 |
| tac-chart3-sp500-increment-merge.yml | workflow_dispatch、push | S&P 500 increment merge writer |
| tac-chart3-stress-analysis-tests.yml | push | Chart 3 stress QA |
| tac-five-site-browser-poc.yml | workflow_dispatch | Browser PoC |
| tac-market-source-capture.yml | workflow_dispatch | Simulation-only 行情診斷 |
| tac-production.yml | schedule（20:05／21:05 UTC，週日–週四）、push、workflow_dispatch | Main 新生產入口；validate／capture／build 分流 |
| tac-simulation-lab.yml | push、workflow_dispatch | Simulation 生產／preview writer 潛在交叉 |
| tac-simulation-run-monitor.yml | push、schedule（每 5 分鐘）、workflow_dispatch | Simulation run monitor |
| tac-sp500-increment-qa.yml | push、pull_request | S&P 500 increment QA |
| us-mmf-chart-visual-qa.yml | workflow_dispatch、push | MMF 視覺 QA |
| us-mmf-public-data-qa.yml | push、workflow_dispatch | MMF 公開資料 QA |
| volatility-sticky-columns.yml | push、pull_request | Volatility UI QA |

本表只記錄已回讀的觸發類型與已知 cron；各 workflow 的完整 branches／paths filter、permissions、實際寫入路徑、concurrency 與跨 workflow_run 關係，仍須在 R0 writer matrix 逐項展開，不能僅由觸發器名稱推定。

#### H3. 直接讀取確認的排程與自動化現況
- `tac-production.yml` main blob SHA：`c2d97b2e77a84f28719b60c5f60c6654d1fac1fa`。排程有兩個 UTC cron：20:05、21:05，並由 `schedule-window` 按 New York DST 只放行一個；冬令對應台灣 05:05，夏令對應台灣 04:05。workflow_dispatch 的 `mode` 預設仍為 `validate`，選 `capture` 才會跑 Stage 1–3；選 `build` 才會跑 Stage 4–6。
- 手動 Run `45899538718` 已 completed：`validate-main-production` success（14 個步驟），`schedule-window`、`capture-and-calendar`、`build-and-deliver` skipped。這是 validate，不是 Capture。
- Main Stage 4 Automation `Automation_f4da15cd95c881918c7412cdd6f35bb2` 最新回讀 `is_enabled=false`；不得引用先前文件所稱「已啟用」作現況。其 prompt 雖定義 EDT 04:15／EST 05:15 接手，但目前停用，無法自動接手 Capture。
- `production/config/schedule.json` blob SHA `3f42774d58a865fa46a6a321f8366a181b05767b` 仍寫 daily_report 05:25、entrypoint `production/runner/run_daily_report.py`；該檔在 main 不存在。此為已確認的設定文件漂移，不代表應直接改 cron 或切換排程。
- Builder approval JSON blob SHA `1da061e7eb9149ceaee3b0b83cd5b1ad40b37932`：`APPROVED_MAIN`、`approved_by_owner=true`，核准 Builder SHA `20eefe57d6f3b389157c01b8532cae3a69128a02`。但其 validation_evidence.limitation 仍寫 no owner approval，與同一檔案的核准欄位矛盾；需修正文案，不能推翻已存在的核准記錄。
- `production/runner/README.md` 仍寫 Builder 尚未 owner approval，與 approval JSON 不一致。
- `production/stages/STAGE_5_RENDER_QA.md` 的條件式 gate 正確要求 exact SHA + APPROVED_MAIN；不需因核准已成立而移除 gate，只需確保現況說明一致。
- Stage 4 Automation 停用、真實 Stage 1–6 E2E 未完成、排程尚未 cut over，三者是不同狀態，必須分別追蹤。

#### H4. R0/R1 狀態修正
- R0：仍 IN_PROGRESS。Workflow 數量修正為 24；尚欠每份 Workflow 的 branches／paths／permissions／concurrency／write-set matrix，以及各資料資產唯一 writer 與觸發依賴圖。
- R1：仍 NOT_STARTED。六份 Stage WR 與九份 contracts 的第一輪內容已回讀；但尚未完成 SIM-1.4 source baseline 逐條對照、schema／manifest／runner／tests 的完整規則矩陣，不能標記 PASS。
- 本次只追加現況證據至重建計畫；沒有修改任何 Workflow、Automation、排程、Runner、Builder、Schema、Manifest、calendar、preview、index.html 或 Simulation。


#### H5. 核心跨流程寫入者與權限實證（追加回讀）
以下不是只依 workflow 名稱推定，而是檢視 YAML 中實際 permissions、checkout、git add／commit／push 與 dispatch 命令：

| 資產 | 已確認寫入者／觸發 | 實際風險與處理界線 |
|---|---|---|
| `production/runs/<RUN_ID>/`、Stage 1–3 收據 | `tac-production.yml` 的 capture job，contents/actions write；只提交當次 RUN_DIR | Main 新流程的 capture writer；應保留 |
| `data/tac-chart3/sp500_daily_increment.jsonl` | `tac-production.yml` capture job；只 stage 此 ledger 後 push main，再 dispatch merge workflow | Stage 2 是 increment ledger writer；必須保留既有 SHA／防重流程 |
| Chart 3 compact S&P500 data／manifest | `tac-chart3-sp500-increment-merge.yml`，contents write；checkout main，僅 stage兩份 compact JSON 與 manifest | 下游 merge writer；需在 R0/R1 核對日期排序／防重／衝突驗收 |
| Chart 3 FRED／ALFRED data | `tac-chart3-incremental.yml`，contents write；push trigger、checkout main，提交 `data/tac-chart3` | 與 S&P500 ledger 是不同資料路徑；仍須核對是否可能把 S&P500 ledger 也納入 stage |
| `preview/YYYY-MM-DD-review.*` | `tac-simulation-lab.yml` 有 actions/contents write，Simulation branch checkout；流程明確設定 Main preview 三檔路徑、dispatch Pages 並驗證公開 URL | **這是 Main preview 的第二個實際 writer**，不是單純 Simulation-only。它可從 Simulation 流程寫 Main preview，與 Main 新流程的唯一入口原則衝突。依使用者要求保留 Simulation 不動；R7 切換時必須在 Main 側設置安全隔離／權限或流程防護，不能直接改 Simulation workflow |
| `history/` 與 `history/index.json` | `archive_index.yml` 有 contents write；index.html push 或每日 17:10 UTC schedule；生成 archive 並 push | 獨立歷史封存 writer；須核對自動排程是否會在首頁未核准時封存舊首頁 |
| GitHub Pages | `pages.yml` 接受 preview/history/index push、workflow_dispatch、workflow_run；contents read，使用 Pages artifact/deploy actions | Pages 是部署器，不是內容 writer；多個來源可觸發部署，需以 main commit／URL 驗證來源 |
| 正式首頁 `index.html` | 本次讀取的 `archive_index.yml` 會檢查 index.html 且不修改；`pages.yml` 只部署；Main Stage 6 明文禁止改 index | 本次未證實上述三者會寫 index；仍需盤點其他舊 workflow／人工流程與保護規則，不能宣稱已證明唯一 writer |

**R0 新增關鍵裁決：** `tac-simulation-lab.yml` 的 Main preview 寫入能力是切換前必須處理的雙 writer 風險。不得以「Simulation branch 唯讀」誤認其無法影響 Main；本次不修改該 workflow，保留 Simulation 原狀。

#### H6. 盤點狀態更新
- 已完成：24 份 Workflow 的觸發類型清冊；Main capture、Chart 3 increment/merge、Simulation-to-main preview、archive、Pages 等主要寫入流程的第一輪實際命令與權限核對。
- 尚未完成：全部 24 份 workflow 的完整 permissions／branch filters／path filters／concurrency／write-set 機器可讀矩陣；Chart 3 writer 的檔案白名單與相互觸發圖；所有舊 workflow 對 preview/index/history 的潛在寫入掃描。
- R0 維持 IN_PROGRESS；R1 維持 NOT_STARTED。未開始 R2/R3 Runner 修改，未更改任何排程或 Automation。


#### H7. Chart 3 FRED workflow 觸發範圍精確校正
進一步回讀 `.github/workflows/tac-chart3-incremental.yml` 全文後，修正 H5 的風險描述：
- 觸發器不是對 `data/tac-chart3/**` 的一般 push，而是 main 上 `.github/scripts/tac_chart3_incremental_trigger.py` 路徑變更。
- Workflow checkout main 後，執行 FRED／ALFRED 系列增量程式，再以 `git add data/tac-chart3` 提交變更。
- 因此，Main Stage 2 提交 S&P 500 ledger 的一般資料 push **不會單憑該資料路徑觸發**這支 FRED workflow；先前將它描述成會由 ledger push 直接觸發，並無 YAML 證據，予以撤回。
- 仍保留一項較窄的檢查：該 workflow 的 stage 範圍是整個 `data/tac-chart3`，R0/R1 需確認乾淨 checkout 下只有 FRED/ALFRED 程式修改其系列檔，並核對與 S&P500 merge writer 的 branch push 競爭控制；目前沒有證據顯示它會主動改寫 S&P500 ledger。



### I. Main-native 修正與驗證進度｜2026-11-27

#### I1. Builder 核准狀態文件一致化
- `production/config/builder-approval.json` 已保留既有 Owner 核准事實：`APPROVED_MAIN`、exact Builder blob `20eefe57d6f3b389157c01b8532cae3a69128a02`、核准時間 2026-11-26 21:29:30 +08:00；只修正 validation limitation 的矛盾文字，明確指出 capture/build 未執行，故不構成真實 E2E。
- `production/runner/PORT_MANIFEST.json` 與 `production/runner/README.md` 已同步為 `APPROVED_MAIN`。核准只涵蓋精確 Builder blob，不代表 Stage 5/6 或真實資料 E2E 通過。
- `production/stages/STAGE_5_RENDER_QA.md` 已更新 exact Main Builder 核准說明，保留任何 Builder blob 變更必須重新核准的 gate。
- Main-only validation Runs `45900415778`、`45900427665` 均 success；兩次的 capture/build jobs 均 skipped，故只證明 validate scope 通過。

#### I2. 母版 QA 契約切離 Simulation runtime
- `production/contracts/MOTHER_TEMPLATE_QA.md` 升為 v1.29：執行期依賴改為 Main `MASTER_WR`、Main mother Manifest、`production/templates/`；SIM-1.4 pinned source baseline 僅供技術沿革／比對，不再要求每日讀取 Simulation branch。
- A2.1 兩份模板路徑與 SHA 改為 Main 執行路徑及 Main Manifest SHA；明文禁止每日 QA checkout、讀取或修改 Simulation branch。
- Simulation branch 與 Simulation workflow 未修改。

#### I3. Stage 2 休市證據與呈現修正
- `stage2_market_fixture_bootstrap.py` 現在只有在 `read_status=MARKET_CLOSED` 且同時具備日期吻合的官方交易日曆證據（OFFICIAL、HTTPS URL、指定 trading date、非空 evidence）時才輸出 CLOSED。
- 只回傳 MARKET_CLOSED 字串、或歷史表格缺少該日資料，不能直接推定休市；未達證據條件者保留 PENDING。
- 確認休市時，非 sector 行情的數值欄輸出 `-`、變動欄輸出 `休市`，不再兩欄都寫休市；sector 單一變動欄保留休市狀態。
- Observation schema 已加入官方日曆證據欄位；Stage 2 WR 與 Runner README 已同步規定。
- 新增正向／負向測試：沒有官方日曆證據不得標 CLOSED；有正式證據時檢查顯示欄位。此批修改的最新完整 CI 尚待回報；不可先標 PASS。

#### I4. 仍需處理的 Stage 2 日期模型缺陷
- `create_run_fixture.py` 目前以 `last_nyse_session(report_date)` 得出單一 trading_date，並將該日期寫入全球 17 指數、11 個產業 ETF、債券、FX、能源、金屬及風險指標所有列。
- 這會把 NYSE 交易日曆錯誤套用到東京、首爾、台灣、澳洲、歐洲及其他不同交易日曆的市場；遇到當地假日／時差或非同步收盤時，資料日期會錯配。
- 尚未修改。下一步需從 44 項 Manifest 的商品／交易所欄位建立逐列 calendar mapping；每列獨立解析該市場最近已完成交易日，並在 Stage 2 Observation、Fixture、receipt、Builder 中保留 row-level trading_date。不能只把日期計算函式換成另一個單一市場日曆。
- 只有官方交易日曆能證明 CLOSED；缺少目標日期資料而無正式假日證據時，必須保留 SOURCE_NO_DATA／PENDING，不能用「前一筆日期」推斷休市。

#### I5. 驗證及安全邊界
- 最新 Stage 2 closure patch 觸發 Main CI Run `45900637416`（截至本紀錄仍 in_progress）；之後的 manifest／README commits 亦觸發後續 validation runs，需以最新 HEAD 對應 run 的完整步驟結果作為判定。
- Main Workflow 的 validate 不執行 capture/build；所有本輪驗證成功均不可等同真實 44 項擷取、Stage 4–6、Pages 預覽交付或 E2E。
- 未改動 tac-production cron、Stage 4 automation、Simulation branch/workflows、正式首頁 `index.html`、preview 交付檔、calendar DB 或 Chart 3 歷史資料。


## 2026-11-27 Stage 2 休市證據修正（Main）
- 針對前一版休市判斷只檢查 HTTPS 與非空文字的漏洞，Stage 2 fixture bootstrap 現在要求休市行事曆 URL 的 hostname 必須屬於明確列出的交易所／官方市場營運機構網域；一般網站、內容平台與任意 HTTPS 網址不再足以構成官方休市證據。
- Source Verification Manifest 同步套用相同官方網域檢查，避免上游 Manifest 將非官方連結標成 CLOSED，但下游 Fixture 又採用不同標準。
- 新增負向測試：example.com 即使有 OFFICIAL 標籤、休市日期與證據文字，也必須維持 PENDING；正向測試改用 NYSE 官方行事曆網域。日本官方假日來源 cao.go.jp 保留在允許清單，與既有日經休市測試一致。
- Main 變更檔案：
  - production/runner/stage2_market_fixture_bootstrap.py blob e94eeffd7931e6cd12189f09bd5c5b3717d41d63
  - production/runner/build_market_source_verification_manifest.py blob b2ed6b66adda87f97c8144807d36105fa208f504
  - production/runner/test_stage2_market_fixture_bootstrap.py blob c7a4358498c61b35eedd65fa592aa19f2c52264a
  - production/runner/PORT_MANIFEST.json blob cea1d6e64e212f9ddc962f786debd9b725df3ba6
- 此修正只收緊休市證據網域，不代表 44 項逐列交易日模型已完成；create_run_fixture.py 目前仍將 NYSE 日期套用全部 44 項，這個阻塞仍列為 Stage 2 未結案。最新 CI 結果待本次 Main push 觸發後回讀；在測試通過前不得將休市驗證標示為完成。


## 2026-11-27 Stage 2 逐列日期模型依賴盤查
- 已逐檔追查全域交易日的硬編碼依賴，確認不能只改 Stage 1 fixture 產生器。以下模組目前仍強制 44 列共用同一日期：
  1. `create_run_fixture.py`：以 `last_nyse_session(report_date)` 設定全域 `trading_date`，並寫入全部 44 列 `source.data_date`。
  2. `stage2_market_fixture_bootstrap.py`：要求每列 source.data_date、Observation target_date 均等於 fixture.trading_date；輸出時再次覆寫 source.data_date。
  3. `validate_chatgpt_web_observations.py`：bundle 僅接受一個 trading_date，且每筆 target_date 必須等於 source.data_date；需改為逐列比對。
  4. `validate_market_snapshot.py`：`_validate_source`、截圖欄位完整性及最後 `common_data_dates == [trading_date]` 均要求單一日期。
  5. `build_market_source_verification_manifest.py`：逐列 target/data date 已由 source.data_date讀取，但 Manifest top-level仍綁單一 trading_date；需分離 report benchmark date 與 row data date。
  6. `build_stage2_receipt.py`：Observation target_date、Manifest row trading_date、browser record data_date、row receipt date 都被強制等於全域 trading_date。
  7. `validate_prebuild_stage_inputs.py`：Manifest與Observation逐列日期檢核仍綁全域 trading_date。
  8. `prepare_stage4_research_bundle.py`：目前檢核並傳遞全域 trading_date，但研究資料列已有 data_date 欄位可供逐列呈現；需確保 snapshot／receipt SHA 綁定不丟失 row dates。
- 日期語意定義：全域 `trading_date` 只保留為報告的美股基準日期／相容欄位；每一個行情列必須有獨立 `target_date`（Observation）與 `source.data_date`（Fixture），以該商品所屬交易所或報價市場的正式交易日曆及報告截止時間計算。不可用「全部減一天」或「全部套 NYSE」替代。
- 日期來源策略：先為 44 列建立明確 `calendar_id`／市場時區／session cutoff 對照；可由已核准日曆套件確定計算的市場才自動計算。日曆不支援、商品日期語意不明（例如外匯供應商日線、MOVE 顯示值、CNN Fear & Greed）者不得猜日期，須由明確的來源日期／時間戳或官方交易日證據決定；無法確定時 fail closed，不產生假 VERIFIED。
- 尚未提交逐列日期程式碼：目前尚未確認 Runner 使用的日曆套件對全部指定交易所的實際支援清單，且 8 個下游模組尚未完成共同契約改造。先列出依賴與契約，避免只改一段造成生產流程中途失敗。


## 2026-11-27 Stage 2 行情基準日規則更正（取代 I4 與逐列日期模型盤查結論）

### 正式規則
- 早報日期 2026-11-27 的 44 項行情，統一以 2026-11-26 作為目標／交易基準日；不得因市場所在地、時區或交易日曆不同，預先將個別列改成 2026-11-25 或其他最近有資料的日期。
- Stage 1 fixture 的全域 `trading_date` 為 2026-11-26；44 列每筆 Observation 的 `target_date` 及對應 source 的 `data_date`，正常情況均應為 2026-11-26。
- Stage 2 必須逐項查詢 2026-11-26 的歷史數據。查到該日數據即採用；查不到時才啟動休市判定。
- 缺少 2026-11-26 資料本身不構成休市證據。只有取得日期吻合、來源為該市場官方交易所／官方營運機構的休市證據，才能標記 CLOSED，並依既定格式呈現數值欄 `-`、變動欄 `休市`。
- 若無法證實休市，必須保留實際狀態（例如 SOURCE_NO_DATA、TOOL_READ_FAILURE 或 PENDING），並記錄原因；不得以 11/25 或其他日期的最近一筆數據冒充 11/26 收盤。
- 不同市場的交易日曆只用於解釋「為何 11/26 沒有數據」及驗證官方休市證據，不用來替換早報統一行情基準日。

### 對先前盤查的更正
- 撤回 I4 及「Stage 2 逐列日期模型依賴盤查」中提出的逐列獨立計算最近交易日、將全域 trading_date 改為各市場日期的設計方向；該方向不符合早報統一基準日要求。
- 原盤查所指出的 8 個模組仍需檢查，但目的改為確保它們一致保留共同目標日期 2026-11-26，並能逐列記錄「當日有數據／官方休市／無法判定」的證據與狀態；不得引入 row-specific fallback trading date。
- 既有官方休市證據欄位、官方網域白名單及負向測試方向保留；需再確認實際 browser observation 能產生並傳遞這些欄位，且上游 Manifest、Fixture、Receipt、Pre-build 與 Stage 4 Bundle 使用同一套證據契約。
- 本更正只修正日期模型規則與盤查結論，不代表 44 項真實擷取、休市查核或 E2E 已完成。


## 2026-11-27 Stage 2 休市證據契約實際修復（Main）
- 依使用者確認，11/27 早報 44 項行情統一查詢 11/26；不採用逐市場最近交易日替代基準日。原 I4 提出的 row-specific fallback date 設計已撤回。
- 實際回讀發現 Stage 2 bootstrap 原先要求 `market_calendar_*` 欄位，但 Observation validator 與 Source Verification Manifest 使用的是 `closure_evidence_*`、reader ref／line range 及 current-run provenance。這是上下游欄位契約不一致，會使有效的瀏覽器休市證據無法通過 bootstrap。
- 已修正 `stage2_market_fixture_bootstrap.py`：改用與 Source Verification Manifest 相同的當次瀏覽器休市證據欄位、官方網域檢查、目標日期、來源頁讀取、商品身分／欄位映射、非重用觀察與完成時間；並補回日本官方假日網域 `cao.go.jp`。有效證據摘要寫入 Fixture。
- 已更新 Observation schema，明列 `closure_evidence_url/text/reader_ref/line_start/line_end`、provenance、prior_observation_reused、source_page_fetched、instrument_identity_status、field_mapping_status。
- 已更新 Stage 2 WR 與 Runner README，明訂全體 44 列共用 run-level target/trading date；缺少目標日資料先記 SOURCE_NO_DATA，只有具備官方行事曆及當次瀏覽器證據才標 CLOSED。
- 已更新 bootstrap 測試：無證據不准 CLOSED、非官方網域不准 CLOSED、完整官方證據可呈現數值 `-`／變動 `休市`。
- Main blobs：bootstrap `de41464be161bfc719663ee08555ccc4bf5a4cf0`；測試 `6f0ef2b5abca24d82b8cd30d92e49be3362e7e6e`；Observation schema `b9392611aa773df6eed939e4c875a8fb6baaa573`；PORT_MANIFEST 已更新 bootstrap SHA。
- 相關 commits：`10810f5`（bootstrap）、`f8e2e5f`（tests）、`ef7de8e`（schema）、`ac62619`（PORT_MANIFEST）、`4845fc4`（Stage 2 WR）、`105e40e`（README）。
- **尚未完成**：最新 Main CI 尚未取得結果；Source Manifest 的完整官方休市驗證、Receipt／Pre-build／Stage 4 傳遞與 44 項真實瀏覽器擷取仍需同一 Run 實測。此修復不代表真實早報已產出。


## 2026-11-27 Stage 2 → Stage 4 休市狀態傳遞修復（續）
- 回讀實際程式後，確認舊 Builder 將 CLOSED 限定為「日經 225」，且把「休市」放在數值欄、破折號放在變動欄，與 44 項共同基準日及正式顯示規則衝突。
- 已修正 Main Builder 的 CLOSED 分支：44 項任何一列均可在具備上游官方休市證據時標記 CLOSED；非產業 ETF 數值欄輸出 `-`、變動欄輸出 `休市`；產業 ETF 的百分比欄輸出 `-`，其來源 change_display 設為 `休市`。Builder 同時檢查 Manifest 中的官方休市證據記錄及當次瀏覽器欄位。
- Stage 2 bootstrap 的產業 ETF CLOSED 數值也由「休市」改為 `-`，原因欄維持 `休市`。
- Receipt 現在要求 CLOSED Observation 與 Manifest 同時為 CLOSED，且 Manifest record 必須綁定同一來源 URL、11/26 等 run-level target date、官方網域、reader ref／line range、current-run provenance、非重用觀察與當次讀取完成時間；Receipt 另封存官方證據引用。
- Pre-build Gate 現在檢查同一套官方網域及瀏覽器證據欄位，不再只接受一個寬鬆的 `evidence_status=MARKET_CLOSED` 字串。
- Stage 4 Bundle 會核對 Receipt 與 Manifest 的休市證據引用完全一致，並將官方證據引用帶入各列的 `closure_evidence` 欄位。
- 測試同步修正為數值欄 `-`、變動欄 `休市`，並補強 Pre-build CLOSED 證據案例。
- Main 相關程式 blobs：bootstrap `02e42000d6d304f2a02c9f96056a614e652e9b18`；receipt `06c743efd6ee136a0de6bbbcb271729e0514712e`；pre-build `7ef4e3c8b4d8cc62650a3b2ae06bf91587733283`；Builder `3e5a971d6d0a3ad3d41881b542580308276021f9`；Stage 4 bundle `2c07c18f3885f82dbec2aab0dba8b17566ae93ef`。
- **Builder 精確 SHA 已改變**，原先核准只涵蓋舊 blob `20eefe57d6f3b389157c01b8532cae3a69128a02`；PORT_MANIFEST 已標記新 Builder 為 `CANDIDATE_PENDING_NEW_EXACT_BLOB_APPROVAL`。不得沿用舊核准或聲稱新版本已獲核准。
- **尚待驗收**：Main CI 尚未回讀；Receipt／Pre-build／Stage 4 的新增 CLOSED 分支尚未在同一實際 Run 完成整合測試；Builder 新 SHA 尚待精確版本核准。真實 44 項瀏覽器擷取及完整 E2E 仍未完成。


### 續查發現與修正（11/27）
- Receipt 原先把所有 Manifest browser record 都當成一般行情記錄，只接受 `data_date`；官方 CLOSED record 使用 `target_date`，會被錯誤拒絕。已修正為一般行情使用 `data_date`、休市證據使用 `target_date`，兩者都必須等於本 Run 的共同 `trading_date`。
- 產業 ETF 的 CLOSED 分支亦需將 `history_close` 明確設為 `-`，否則 Manifest 建構時拿到 null，與 Observation 的預期顯示值不一致；已補正並新增 sector closure 測試。
- 新增 Pre-build 對官方休市證據的完整檢查：官方網域、目標日期、當次來源頁讀取、商品與欄位身分、reader ref／line range、provenance、非重用觀察。
- Stage 4 現在核對 Manifest 與 Receipt 的 closure URL／reader ref／line range 完全一致，並將 target date 與 provenance 帶入 research bundle。
- 測試的休市顯示慣例同步為數值欄 `-`、變動欄 `休市`。
- 最新程式 blobs：bootstrap `4557c95c5ee8041231116ce937f784786d6f1076`；Receipt `239f9e6aa028a159791b5f63d50b2b8b02afd03a`；Pre-build `7ef4e3c8b4d8cc62650a3b2ae06bf91587733283`；Builder `3e5a971d6d0a3ad3d41881b542580308276021f9`；Stage 4 `2c07c18f3885f82dbec2aab0dba8b17566ae93ef`；PORT_MANIFEST 最新同步 commit `63faddc`。
- 最新測試 blobs：bootstrap `32c1515ad6d005404091eb055a130dfe0066190f`；Manifest `a67265b5940c06c73020b6668afce259c095b46f`；Pre-build `8752971e73129a8042d80ca1046a3a11ec65a6cb`。
- 尚未取得這批最新 commits 的 CI 結果；尚未完成真實 browser run。Builder 新 blob 仍待精確 SHA 核准，不得沿用舊 blob 核准。


## 2026-11-27 續修：Stage 4 逐列休市證據與截圖優先權
- 回讀 Stage 4 實際程式發現 CLOSED row handoff 使用了前一段統計迴圈殘留的 `manifest_row`、`receipt_row`，而非當前 row key；已修正為以 `manifest_rows[key]`、`receipt_rows[key]` 精確綁定，避免證據錯列。
- Stage 2 bootstrap 新增截圖優先權保護：當 observation 由使用者截圖提供，或欄位證據含 USER_PROVIDED_SCREENSHOT 時，不得進入 CLOSED 分支覆蓋截圖行情。
- Main blobs：`prepare_stage4_research_bundle.py` `f051f79fcdf1f49f98fdaf5f8de8589f79f37969`；`stage2_market_fixture_bootstrap.py` `870ed3bbaf84bb04c095a4ec7942723f76bfa05f`；PORT_MANIFEST `2fca6cdbdbd7d42d12e5e8ffc44ce91f253c7754`。
- CI：Stage 4 修正 commit 的 Run `45903290060` 啟動時仍在安裝依賴；後續 bootstrap／Manifest commits 會觸發更新的 Main validation。尚未取得涵蓋最新 HEAD 的完成結果，不標記 PASS。
- 尚待：為 Stage 4 增加 CLOSED row 正反向整合測試；為 Stage 2 增加截圖不被 CLOSED 覆蓋的回歸測試；回讀最新 Main CI；確認 Builder 新 blob 的 exact approval gate 維持 fail-closed。未修改 Simulation、排程、正式首頁或真實行情資料。


## 2026-11-27 續修：CLOSED 證據內容必填與 CI 根因
- 回讀 Run `45903158288` 的 job log，確認唯一阻塞在 `test_market_closed_requires_official_calendar_evidence`：測試案例只有官方 URL／reader ref／行號，沒有實際證據文字，但 bootstrap 仍接受 CLOSED。這是程式驗證缺口，不是單純測試格式問題。
- 已修正 bootstrap：官方休市 URL 之外，必須有非空 `closure_evidence_text` 才能 CLOSED；截圖優先權保護仍保留。
- 正向測試（ASX／NYSE）加入實際證據文字；無證據文字的 NYSE 案例保留負向測試，必須呈現 PENDING／待核實。
- 最新 blobs：bootstrap `c71d1fd5cf3226907c09243a7a75c14af8db4e24`；測試 `3320a75d67e0f4ea61641194fa066b06cebbfe47`；Stage 4 per-row binding `f051f79fcdf1f49f98fdaf5f8de8589f79f37969`；PORT_MANIFEST `70b5bc04aebdf1ab9aa88fce9bd1a86009407a38`。
- 先前 CI Run `45903158288`：compile、dual mother SHA、Manifest validation 通過；Stage 2 測試 24 項中 1 項失敗，其餘通過；Builder／earnings 測試因前置失敗而 skipped。最新修正後 CI 尚待執行及回讀。
- 尚未完成：新增 Stage 4 CLOSED row 整合測試及截圖＋CLOSED 衝突回歸測試；最新 Main CI；真實 44 項資料擷取與 E2E。Builder 新 blob仍維持 exact approval pending。未修改 Simulation、排程、正式首頁。


## 2026-11-27 Main validation result and screenshot regression
- Main CI Run `45903428235`（HEAD `6e2213a0a5a55214e7c213b79de74d4867cd716a`）已完成 SUCCESS：Python compile、browser QA syntax、雙母版 SHA／Manifest、Stage 2 + pre-build deterministic tests、Builder／earnings tests、candidate Builder fixtures、mother-owned DOM contract 全部通過。Capture、build、schedule 均 skipped；這不是實際行情 E2E，也不是正式早報交付。
- 另新增回歸測試：當 MOVE 已有截圖值 97.54／-1.32%，同一 observation 又帶入 MARKET_CLOSED 證據時，截圖行情必須原值保留，不得被「-／休市」覆蓋。測試檔 blob `84f866960b35c8c37ad84bc7f59f008844676352`，提交 `1850e12463de9b0d15c9d5e5cd474f6ab63f212d`；該新測試尚待下一輪 CI 驗證。
- PORT_MANIFEST 已記錄成功 Run 與 bootstrap SHA，最新 blob `953464b5bfb767cc61dcfc979245b243ba75ffa0`。Stage 4 CLOSED row 的獨立正反向整合測試仍待補。
- 下一階段：先驗證新增截圖衝突測試，再補 Stage 4 CLOSED 證據跨 Manifest／Receipt／Bundle 的正向與錯列負向測試；其後再處理 Builder exact-blob 核准、內容生產器、真實 Stage 1-6 E2E。未修改 Simulation、正式排程或首頁。


## 2026-11-27 Main 截圖當日有效期修正
- 使用者明確規定：提供的行情截圖僅限當天有效，不得跨日沿用。
- 回讀 `stage2_screenshot_inputs.py` 確認原程式僅檢查 sidecar 的 report_date／trading_date、row data_date，對 captured_at 只檢查非空；舊圖若被複製到新 sidecar 並改寫日期欄位，仍可能通過。
- Main 已修改載入器：解析每個欄位實際使用的 ISO-8601 captured_at，要求明確時區，轉換為 Asia/Taipei 日期後必須等於本次 report_date。逐欄位檢查，避免列級時間戳掩蓋舊圖；data_date 仍獨立要求等於共同 trading_date。
- 新增負向測試：舊日期截圖即使 sidecar 日期欄位改成當天仍拒絕；個別欄位舊時間戳不得被列級新時間戳掩蓋；無時區時間戳拒絕。
- Main commits：載入器 `8d698825`（blob `8d254826569b65c901dbff32eb14a2ebc4c49dda`）；測試 `96693240`（blob `f21f7004792c691ebdfd3e4cc19e3af335934fc0`）。PORT_MANIFEST 已同步載入器 SHA。
- CI Runs `45903973586` 與 `45903977272` 涵蓋此次變更，狀態待完成；尚未宣告通過。未執行真實行情擷取、早報建置、排程修改或正式首頁更新。


## 2026-11-27 截圖優先回歸測試修正
- 回讀 CI Run `45903973586` 日誌，失敗點不是載入器跨日檢查，而是先前新增的「截圖不可被 CLOSED 覆蓋」測試 Fixture 只標記 close 欄位為截圖來源，卻要求 change 欄位也保留截圖值。依逐欄位證據規則，程式正確將未標記的 change 欄位設為待核實；測試 Fixture 不完整。
- 已修正測試：同時明確提供 close=97.54 與 change=-1.32 的 USER_PROVIDED_SCREENSHOT field_evidence，讓測試真正驗證兩欄都不得被 CLOSED 覆蓋。Main commit `81a17584`，blob `6fe74dbb8e8fd23f3dc7567d89e06b31041f3f0e`。
- 這是測試資料修正，不放寬程式規則；截圖只保護實際有截圖證據的欄位。
- 同日有效期變更 CI 仍未完成；不得標示 PASS。


## 2026-11-27 截圖當日有效期與截圖優先權 CI 驗收
- Main CI Run `45904128098`（commit `81a17584001d321915a0a6c3e6b59910804e9bc1`）SUCCESS；截圖與 CLOSED 衝突回歸測試通過。
- Main CI Run `45904153569`（HEAD `da3ac8e7478570a94b2973c53929c3abba69f357`）SUCCESS；涵蓋同日有效期載入器、舊日期截圖拒絕、欄位級 captured_at 檢查、無時區時間戳拒絕，以及修正後的截圖／CLOSED 衝突測試。
- 驗收範圍僅為 Main deterministic validation；capture-and-calendar、build-and-deliver、schedule-window 均 skipped。未執行真實 44 項行情擷取、早報 E2E、排程切換或正式首頁更新。
- PORT_MANIFEST 已記錄最新成功 Run 與精確 HEAD SHA。截圖規則可標記為程式與 CI 測試通過，但真實 Run 尚未實測。


## 2026-11-27 Main 重建續查：最新 CI、Stage 4 生產邊界與 Builder 核准差異

### 最新 Main validation
- Run `45904766962`，HEAD `057fa669a7647d8b7adddb64644667cb675a867b`，已完成 `SUCCESS`。
- `validate-main-production` 成功；`capture-and-calendar`、`build-and-deliver`、`schedule-window` 均為 `SKIPPED`。
- 成功範圍包括 Python／Browser QA 語法檢查、雙母版 SHA 與 Manifest、Stage 2／Pre-build deterministic tests、Builder／earnings deterministic tests、隔離 fixture 候選 Builder 建置及母版 DOM contract。
- CI log 明確標示候選 fixture 為 synthetic，且 `production_preview_written=false`、`review_ready=false`。因此本 Run 不代表真實行情擷取、Stage 4 編輯內容產生、Stage 5/6 真實交付或完整 E2E 通過。

### Stage 4 編輯內容生產器盤點
- 已逐條回讀 SIM-1.4 Stage 4 規格及 Main `production/stages/STAGE_4_NEWS_ANALYSIS.md`。
- Main 現有 `prepare_stage4_research_bundle.py` 負責把同一 Run 的凍結 44 項行情、未核實項目、FedWatch、行事曆／財報、來源觀察、Manifest、Receipt、截圖證據及新聞時間窗整理成研究包；它不是新聞研究或編輯內容生成器。
- Main `run_stage4.py` 負責驗證既有 `report-content-YYYY-MM-DD.json` 的 Schema、Run／日期／行情 SHA／研究包 SHA、新聞時間窗、來源及分析結構，再把內容合併至同一 Run Fixture；它不會自行搜尋原始報導或撰寫內容。
- Main Workflow 的 capture handoff 明確停在 `AWAITING_EDITORIAL_INPUT`，build job 則要求先存在日期化 report-content JSON。Workflow 目前沒有模型研究／生成步驟；因此 P0-1 尚未完成。
- 真正自動化需補上可核准的研究／生成執行介面、模型供應商與憑證管理、成本／重試／逾時政策、原文抓取與時間戳證據封存，以及輸出後的既有 Stage 4 fail-closed 驗證。不得用空白、測試 fixture、搜尋摘要或假新聞填補。未取得模型服務授權前，不得假設 API secret 已存在或自行發起付費模型呼叫。
- Stage 4 輸出仍必須由同一 Run 的 `run_id`、`market_snapshot_sha256`、`research_bundle_sha256` 三者綁定；Stage 2 快照保持唯讀。

### Stage 5 Builder exact-blob 核准差異
- Main 現行 `production/runner/build_review_html.py` blob SHA 為 `3e5a971d6d0a3ad3d41881b542580308276021f9`。
- `production/config/builder-approval.json` 的歷史核准只涵蓋 `20eefe57d6f3b389157c01b8532cae3a69128a02`。
- 目前 Builder 在 2026-11-26 的 `dd1f5c87d23ee0d4a0594508f104198584ef76d4` 變更後，已不是原核准 blob。Stage 5 的 exact-blob gate 會拒絕此差異；不得把舊核准延伸到新版，也不得由助理代替使用者核准。
- Main validation Run 45904766962 沒有執行 Stage 5 runtime gate，故未驗證新版 Builder 可正式執行。

### 下一步（不改排程、不啟動正式擷取、不發布首頁）
1. 定義並實作 Stage 4 研究／生成 adapter，但先確認模型供應商與憑證／成本授權邊界；沒有授權時只完成可測試的介面與 fail-closed contract，不偽稱內容已自動生成。
2. 補強 Stage 4 producer／validator 的正反向測試：跨 Run、跨日期、行情 SHA 不符、研究包 SHA 不符、新聞超出時間窗、來源缺失、政治六領域未完成及五層分析缺來源均須拒絕。
3. 對目前 Builder 新 blob 維持 `REAPPROVAL_REQUIRED`；完成程式修訂與測試後，提交 exact SHA 供使用者核准，不自動改寫核准紀錄。
4. 完成後再執行 Main validation；Stage 5/6 真實 E2E 仍須等編輯內容與 Builder 核准條件俱備，且另行遵守正式擷取與發布權限。
5. 本次續查未修改 Simulation、Workflow 排程、正式行情資料、Main preview 或 `index.html`。

## 2026-11-27 Stage 4 驗證加固（CI 待完成）

- Stage 4 政治掃描 finding 的來源 URL 原先接受 HTTP 或 HTTPS，與 Stage 4 證據品質要求不一致；已收緊為僅接受 HTTPS。
- 新增負向測試：政治 finding 使用 HTTP 必須拒絕；政治 finding 使用六領域以外的 domain 必須拒絕；研究包 receipt 跨 Run 必須拒絕；研究包內 market snapshot SHA 與當次 Run 不一致必須拒絕。
- 修改：
  - `production/runner/run_stage4.py` blob `0e30c83ad54876f5450866fe2bd11eaf218494b4`
  - `production/runner/test_stage4_content_validation.py` blob `85df5222d97fea88acaf02517ae0cd7f17357a71`
- 對應 Main CI Run `45905791303`（HEAD `6d6b3927437d0292680b95ebc0e748d309c4c721`）目前 GitHub 回報 `pending`，尚無 jobs 可讀；不可宣稱測試通過。
- 此次變更只加固 Stage 4 驗證器及測試，沒有生成報告內容、沒有真實研究呼叫、沒有讀取或改動任何 Simulation 檔案，沒有觸發正式擷取或發布。
- 自動研究／編輯內容生產器仍受模型供應商、模型版本、API 憑證及付費使用授權限制。尚未獲得指定供應商與 API 使用授權前，不可啟用付費模型呼叫或宣稱 Stage 4 自動生成已完成。

## 2026-11-27 Stage 4 驗證加固 CI 結果

- Run `45905788264`，HEAD `4ca8bf89ed55664a493dcad96022a44061cb077d`：`SUCCESS`。
- 通過 Main compile、雙母版 SHA／Manifest、Stage 2／Pre-build deterministic tests、Stage 4 content validation tests、Builder／earnings deterministic tests、isolated candidate Builder 與 mother DOM contract。
- 本次新增 Stage 4 測試（HTTP 政治來源拒絕、六領域外 domain 拒絕、跨 Run research bundle receipt 拒絕、bundle snapshot SHA mismatch 拒絕）已包含於成功的 Stage 2／Pre-build deterministic tests job。
- `build-and-deliver`、`capture-and-calendar`、`schedule-window` 均 SKIPPED；成功範圍仍不包含真實行情擷取、AI 編輯生成、Stage 5／6 真實交付或 E2E。


## 2026-11-27｜早報主排程由 Stage 1 啟動（正式架構修正）

- **唯一早報主啟動入口**：`.github/workflows/tac-production.yml` 的 weekday `schedule` event。該 workflow 的 `capture-and-calendar` job 必須由 Stage 1 建立全新 Run，依序執行 Stage 1 → Stage 2 → Stage 3；不得以 Stage 4 automation 作為早報主啟動排程。
- **Stage 1 時間**：美國 EDT 期間台灣 04:05；美國 EST 期間台灣 05:05。現行 workflow 以雙 UTC cron 搭配 `schedule-window` 的 New York DST gate 選出唯一正確觸發。Workflow SHA 維持既有 `c2d97b2e77a84f28719b60c5f60c6654d1fac1fa`，本次不變更已正確設定的 Stage 1–3 cron。
- **Stage 4–6 接續任務**：ChatGPT automation 僅作為 Stage 3 完成後的 continuation worker；EDT 台灣 04:15、EST 台灣 05:15 喚醒，等待並核對當日唯一 schedule Capture 的 receipts 後，才進行 Stage 4 研究撰稿、Stage 5 Builder/QA、Stage 6 Main Preview 交付。它不是另一個早報起點，也不得在 Capture 缺席時自行以舊資料啟動。
- **阻塞行為**：若當日 schedule Capture 未啟動或失敗，接續任務回報 BLOCKED，保留任務啟用狀態，不得自動停用接續任務、不得改用 Stage 4 排程取代 Stage 1。
- **保留的獨立任務**：04:35 行事曆資料庫更新與 05:30 Chart 3 更新仍維持各自職責，不得與早報主流程混成第二個早報入口。
- **當前驗收限制**：雖已確認 workflow 內 Stage 1–3 的順序及雙 UTC cron 定義正確，但 2026-11-27 當日未找到 schedule Capture run；因此不能宣稱排程觸發已驗收。下一個工作日必須以真實 `event=schedule` run 驗證 Stage 1 起始、Stage 1–3 receipts、Stage 4–6 接續及 Main Preview。正式首頁仍須另行核准。


## 2026-11-27 補充｜Stage 4 由 ChatGPT 接續執行，不使用外部模型 API

- Stage 4 編輯內容的執行者已定為 ChatGPT 的 Main continuation automation「TAC Main 早報接續｜Stage 4–6」。它在當日 Stage 1–3 Capture 成功後讀取同 Run receipts／research bundle，直接產出綁定 Run ID、market snapshot SHA、research bundle SHA 的 editorial JSON；不呼叫外部 LLM API、不需要另行配置模型供應商 API key。
- 因此，舊版計畫中「Stage 4 producer 尚待模型供應商／憑證授權」的描述不再適用於此執行架構。真正尚未驗證的是：在真實 schedule Capture 成功後，continuation automation 是否能完成當日研究、JSON 寫入、Stage 4–6 build 與 Main Preview E2E。
- production/runner/PORT_MANIFEST.json 已同步記錄此 ChatGPT continuation worker；但這不代表 E2E 已通過，也不改變 Stage 5 Builder exact-blob approval gate。
- **現存正式阻塞**：Main Builder 當前 blob 3e5a971d6d0a3ad3d41881b542580308276021f9 與歷史核准 blob 20eefe57d6f3b389157c01b8532cae3a69128a02 不一致，仍須對當前 exact blob 取得使用者核准；未核准前不得觸發 Stage 5/6 build。
- **下一驗收順序**：先在下一個工作日取得真實 event=schedule Stage 1–3 Capture；再驗證 ChatGPT continuation 研究與 JSON；同時先完成 Builder 當前 blob 的核准流程，最後才可執行 Stage 4–6 E2E。不得為了趕進度跳過任一條件。


## 2026-11-27 首次排程窗口根因判定

- 以 GitHub Actions 實際 run metadata 核對：最新 schedule/workflow 變更提交 `67c79b4fb6c98e78f03867dfa8695233fcf27d9c` 建立於 `2026-11-26T22:46:32Z`；11/27 台灣 05:05 的冬令啟動窗口等於 `2026-11-26T21:05:00Z`。因此該 workflow 在預定窗口後約 1 小時 41 分才更新到 main，11/27 沒有 schedule Capture 屬於錯過首次排程窗口，不能據此判定 cron 表達式失效。
- 11/27 可見的 Main pipeline runs `45897439038`、`45897601608` 是 `event=push`，其 `capture-and-calendar` 與 `schedule-window` 均 skipped；最新文件驗證 run `45906904274` 同樣是 `event=push`，`validate-main-production` 執行中，Capture／Build／schedule-window 均 skipped。這些都不是早報排程執行。
- 現行 cron `5 21 * * 0-4` 在美國冬令時間對應台灣週一至週五 05:05；下一個預期 schedule event 為 `2026-11-29T21:05:00Z`（台灣 `2026-11-30T05:05:00+08:00`）。夏令時間對應 `5 20 * * 0-4`（台灣 04:05）。
- 已將此時間根因、實際 Run event 類型及下一個預期窗口同步寫入 PORT_MANIFEST。未手動 dispatch capture，未啟動真實行情擷取，避免把測試當成排程驗收。
