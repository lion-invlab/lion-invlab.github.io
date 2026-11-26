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
| 6. 排程與正式切換 | Main capture EDT 04:05／EST 05:05；Main Stage 4 EDT 04:15／EST 05:15；04:35 calendar、05:30 Chart3責任分流；保留使用者正式首頁核准權 | 首次 scheduled capture evidence、同 Run Stage 4 handoff、Builder 核准、真實 E2E、舊流程退役證據 | 排程已設定但首次實跑待驗證；同 Run 自動交接、Builder exact-SHA 核准、真實 E2E、正式切換與舊流程退役均未完成 | IN_PROGRESS |

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

