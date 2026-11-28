# TAC 投資早報 R3｜MASTER WORK RULES

版本：1.7（2026-11-28｜單一 Run Stage 1–6 串接、Run-state v1.2、無 push 觸發依賴、Main Preview 隔離）
正式分支：main
規則來源：SIM-1.4 技術規範（正式生效版；來源 branch `simulation/tac-process-lab-2026-11-06`，來源 WR SHA `d60965f0a61159dd8a94c31d7a7f2b6d083e6363`）
正式生效標示：SIM-1.4（正式生效版）｜ACTIVE／正式生效
main 唯一生產規範：本文件；六份 Stage WR 與 contracts 為本文件的執行附件。Simulation 原始檔只讀，不作執行依賴。

## 1. 核心裁決
1. 使用者當次指示優先。2026-11-26 使用者明確指定：**main 母版以 Simulation SIM-1.4 baseline 雙模板為準；main 舊母版及舊流程可棄用。**
2. 新正式母版唯一來源：
   - `production/templates/monday-mother-template.html`，blob SHA `710c944205ee05a86599ef5cd869f26c4a9ebde1`
   - `production/templates/weekday-mother-template.html`，blob SHA `ff051c0cd22cf9267420c41e3952fa3178f0e45d`
   - 唯一 Manifest：`production/config/mother-template-manifest.json`
   - 唯一詳細 DOM／互動／視覺驗收：`production/contracts/MOTHER_TEMPLATE_QA.md`
   上述模板及 QA 契約已逐位元從 SIM-1.4 baseline 複製至 main。舊 `母版專區/`、根目錄 Manifest、舊 WR、舊 layout QA 不再是新 Pipeline 的規則或母版來源；可保留歷史檔案，但不得被新 Runner 引用。
3. SIM-1.4 詳細技術原文保存在 `production/reference/SIM-1.4_SOURCE_BASELINE.md`，blob SHA 來源 `d60965f0a61159dd8a94c31d7a7f2b6d083e6363`。本文件將其轉換為 main 生產責任；SIM 原文中的 Simulation-only 分支限制不適用 main，但資料品質、欄位、Stage 定義、來源政策、母版規格及 QA 原則保留。
4. main 舊生產入口及 Workflow 不得成為新系統的第二入口。完成切換前先隔離／停用衝突觸發；不刪除歷史證據，不修改 Simulation。
5. 唯一正式入口：`.github/workflows/tac-production.yml`。`capture` 負責 Stage 1–3 並產生精確 Run handoff；`build` 只接受同一 Run 的 Stage 4 編輯內容，再執行 Stage 4–6。Python Stage Runner 是 Workflow 的執行模組，不另設第二個排程入口。未完成編輯內容自動交接與真實 E2E 前不得宣稱可全自動生產。

## 2. 唯一每日流程
Stage 1 基準與母版鎖定 → Stage 2 44 項行情及獨立 FedWatch → Stage 3 行事曆與財報 → Stage 4 新聞與市場分析 → Stage 5 唯一 HTML Builder 與 QA → Stage 6 main/preview 審核版交付與驗證。
六階段是同一條流程，不是六次獨立審批。每階段保留必要輸入、輸出與交接，不重複建立等價收據或重抓已鎖定資料。Stage 1 必須先建立並提交當日 Run；Stage 2 worker 只有在讀取該 Run 的 run-context、fixture 與 Stage 1 receipt 後才可擷取。Stage 2 不得在 Stage 1 前預擷取。

## 2A. 六階段強制 WR 開工前讀取
- 六個 Stage 一律先讀取自己的完整 Stage WR，後執行本階段工作；不得只依賴 MASTER_WR 摘要、前次對話記憶、Workflow step 名稱或 Runner 註解。
- 唯一執行器為 `production/runner/stage_wr_preflight.py`；各 Stage 入口必須先呼叫對應 Stage key。Stage 1 讀取自身 WR 並留存證據；Stage 2–6 另核對 Stage 1 governance snapshot 中該 WR 的 Git blob SHA。
- Preflight 必須讀取完整 UTF-8 文件、確認非空、計算 SHA-256 並核對 Git blob。缺失、讀取失敗、未鎖定、版本漂移或收據缺少 `wr_preflight` 均 FAIL-CLOSED，不得開始或宣告完成。
- Stage 4 編輯工作者在撰寫內容前，必須先完整讀取當次 Run 鎖定的 Stage 4 WR；編輯 JSON 必須回填精確 `stage4_wr_sha256`，Runner 逐位元組驗證。不得以摘要、前次對話或 Runner 事後讀取取代編輯工作者開工前讀取。
- 每階段收據必須記錄 WR 路徑、完整讀取狀態、SHA-256、Git blob SHA、Stage 1 pinned SHA 及讀取位元組數。無證據不得 PASS。
- 下游 Stage 必須驗證所有直接上游 receipt 的 `wr_preflight` 證據：Stage 2 驗 Stage 1；Stage 3 驗 Stage 2；Stage 4 驗 Stage 2、3；Stage 5 驗 Stage 2–4；Stage 6 驗 Stage 5。路徑、Stage key、Git blob SHA、Stage 1 pinned commit 任一缺漏或不符即拒絕交接。

## 3. 唯一正式母版規則
- 正式早報製作日為台灣週二至週六；週一、週日不自動製作。
- 週二至週五：report_date=製作當日，trading_date=前一個市場交易日，使用 Weekday template。
- 週六：production_date=週六，report_date=隔週一，trading_date=週五，使用 Monday template；週六早報包含「上週」經濟與財報回顧，並投影報告週及前一週 JSON。
- 所有 Run、編輯 JSON、Preview 檔名、發布鎖均以 report_date 為唯一日期錨點；production_date 僅作實際製作時間／新聞截點紀錄。
- 母版 SHA 必須與新 Manifest 一致；不符即停止，不 fallback。
- Builder 使用真正 DOM parser，只能更新核准槽位；不得以 regex／字串切片改 HTML。
- 母版 CSS、JS、DOM、互動、響應式、字體、顏色、間距不得由 Builder 注入或重建。
- 上漲／正值紅色，下跌／負值綠色。
- 不得重新加入已刪除的「關鍵重點」膠囊。
- 五層市場深度解析槽位已存在於兩份 SIM-1.4 母版，固定順序政治地緣、政策產業、宏觀、金融市場、機構資金與策略。
- 工具欄提示泡泡在首次捲動／觸控移動時立即隱藏；呼吸燈依母版行為獨立持續。

## 4. Stage 2 行情核心規則
- 固定 44 項：全球主要市場 17（含 SOX）、11 大產業 ETF 11、公債殖利率 3、外匯 6、能源及貴金屬 4、風險情緒 3（VIX、MOVE、CNN Fear & Greed）。FedWatch 獨立，不計入 44。
- 使用者提供且能辨識商品、日期及數值的截圖優先於全部 44 項的網頁讀取，不限 MOVE。已提供欄位直接採用，不重抓、不覆蓋；缺欄才補讀。
- 未由截圖提供的欄位，直接用瀏覽器開啟指定 Investing.com 商品 Historical Data 頁，讀取實際歷史表格及目標交易日列。不得以搜尋摘要、第三方 API、Yahoo 或其他來源替代指定的 Investing.com 首選；不得繞過 Cloudflare。唯一例外為 MOVE：Investing.com 頁面不可讀或目標日期列不存在時，依 SOURCE_POLICY 與 Stage 2 WR 使用核准的 TradingView ICE:MOVE 備援；必須保留 TradingView 來源身分與當次證據，且僅限 risk.move，不適用其他 43 項。
- 同一批最多 4 個不同歷史頁面並行（concurrency=4）；每頁獨立核對標的、日期、欄位、收盤口徑及 Observation。不得藉提高並行數規避網站限制。
- 已核實值立即鎖定；下游 Stage 3–6 唯讀。不得重抓已鎖定項目。
- Stage 2 每輪先 blank-first 清除 Fixture 中所有舊行情值、舊 Observation、舊截圖證據及舊時間戳，再以當輪有效截圖／Observation 回填。不得沿用前輪 fixture 報價。
- 狀態至少區分 VERIFIED、BACKUP_VERIFIED、PENDING、MISSING、CLOSED、NOT_APPLICABLE、NOT_TESTED、TOOL_READ_FAILURE、SOURCE_NO_DATA；語意不得混淆。PENDING 不可造成整個流程崩潰，亦不可視為成功。
- 共用 trading_date 只作為 Run 日期錨點；44 項每列的 target_date／data_date 依各商品所屬市場交易日曆及截止時間，採用最近一個已完成交易時段的實際日期。不同市場允許不同 data_date；不得把美股休市日的前一交易日收盤錯標為休市日，也不得把舊值標成新日期。
- Stage 2 Observation bundle 必須帶入同一 Run 的 run_id、Stage 1 receipt SHA、run-context SHA、Stage 1 fixture SHA；Runner 只驗證，不得事後替 Stage 2 worker 補綁或修復交接身分。
- 44 項每項必須有值或明確狀態；單項缺漏不得阻止無依賴項目及其他階段繼續。未核實值不得作為確定事實。
- MOVE 的市場交易日判斷必須獨立於行情列讀取：使用 SIFMA 官方美國固定收益市場 Holiday Schedule／公告核對目標交易日。官方公告確認全天休市時，MOVE 標記 CLOSED，保留 Investing.com 當輪歷史頁讀取紀錄及 SIFMA 公告 URL、原文定位、讀取時間與 SHA；不得要求休市日存在收盤數值列。提早收市仍屬交易日，必須照常讀取該日 MOVE 收盤，不得沿用前一交易日數值或標記 CLOSED。SIFMA 公告屬市場日曆建議，僅用於相應美國固定收益市場日期判斷，不得擴張為所有資產的休市證據。
- CLOSED 行的 `display_value_reconciled` 代表休市狀態與日曆證據已核實；`display_value_matches_saved_observation` 必須為 false，因休市列沒有可比較的數值。不得把休市狀態核實誤寫成報價數值相符。
- Stage 2 只將已核實 S&P 500 現貨正式收盤追加並提交至既有 `data/tac-chart3/sp500_daily_increment.jsonl`，遵守 append／SHA／防重契約；不可另抓第二份 S&P500 報價，也不得 dispatch 或等待歷史合併。Chart 3 merge workflow 由 Main production workflow completed 事件觸發，依 workflow_run_id 對應唯一 Run，確認 Stage 2=PASS/PARTIAL、Stage 3=PASS 後接手；不要求 Stage 4–6 已成功交付，也不得由增量帳 push 直接觸發。它是非阻塞支線，失敗不得阻止早報主線。

## 5. Stage 3 行事曆／財報
- 唯一資料來源為 `data/calendar/weeks/YYYY-Www.json`；早報嚴格唯讀。
- 工作日 04:35 行事曆排程為 JSON 唯一 writer；Stage 3 不得修補、merge、upsert 或回寫。
- Stage 3 以 Stage 1 鎖定的同一 main commit 讀取 report_date 所屬週 JSON；report_date 為週一（週六製作）時另讀前一週 JSON供回顧。週二至週五不得為了產生空白回顧而讀取前一週資料。
- 財報 EPS 與 Revenue 分開選源：Yahoo Finance Average Estimate 第一順位；缺值／不可讀／期間不符依序 Investing.com、LSEG I/B/E/S、FactSet Estimates。各指標取得第一個可用平均預期後停止該指標搜尋。
- 已公布事件必須顯示實際值、共識及判讀；財報另呈現 EPS／Revenue 與預期比較及股價反應。資料不足如實標示。

## 6. Stage 4 新聞與分析
- Stage 3 後自動產生 `stage4-research-bundle.json`，彙整完整 44 項行情／來源狀態（保留每項自己的 data_date）、未核實列、FedWatch、當週行事曆與財報（僅週一另含上週）、Stage 1–3 receipts、必要輸入 SHA，以及當日截圖 sidecar／圖片證據 SHA。
- 編輯內容必須綁定同一 Run 的 `run_id`、`market_snapshot_sha256` 與 `research_bundle_sha256`；Stage 4 與 build workflow 逐一驗證，禁止跨 Run 或使用過期行情。
- 全球焦點新聞 5 則；市場熱門頭條 10 則；核對原始發布時間、時區、URL 與共同時間窗口。
- 總結小卡、五層深度解析、盤面觀察重點分層，不互相複製。
- 五層固定順序：政治與地緣政治；政策傳導與企業／產業鏈；宏觀經濟；金融市場定價／情緒／風險；機構資金動向與投資策略。
- 每日完成六領域政治掃描；無重大變化可明確寫無重大已核實變化，不硬湊。
- 策略必須有行動、觸發條件、風險、失效條件；事實、推論、情境與策略分開。
- 總結及五層文章內部來源證據完整保存，但母版指定可見區域不得顯示來源列表；新聞、行情、商品、債券、匯率、行事曆等原有來源顯示保留。
- 總結／五層文字局部修正使用 DOM 局部更新器；不重跑行情、行事曆、新聞或完整 Builder，並保留非目標 DOM 指紋。

## 7. Stage 5 Builder 與 QA
- Builder 只接受同一 Run 的 Stage 1–4 輸出、PASS 的 pre-build receipt、正式 Manifest、QA Contract 與 Stage 1 governance SHA snapshot；main Builder 必須通過 exact blob SHA owner approval。
- 目前 SIM-1.4 核准 Builder 的來源 SHA 為 `6bf6eb2f5ae29774addf696c541c5b806953c7a3`，但其路徑與執行環境仍是 Simulation 專用；main 必須先完成路徑／依賴適配、測試與使用者核准前的技術驗證，不得直接把該 SHA 宣稱為 main Runner 已可用。
- QA 四類：資料／內容、HTML 結構、視覺與互動、Run／交付整合。只跑必要且有區別的檢查，不無限加 Gate。
- 未測試標 NOT_TESTED；不把缺值變成 0 或虛構成功。必要 Gate FAIL 不得 REVIEW_READY；非核心欄位缺漏可 PARTIAL 並繼續可完成工作。

## 8. Stage 6 審核版交付與正式發布
- Main 審核版三檔：`preview/main/YYYY-MM-DD-review.html`、`.qa.json`、`.delivery.json`；Simulation 保留既有 `preview/` 根層路徑，兩者不得共用檔名或覆寫。
- 寫入前後僅允許日期化三檔；HTML bytes 不得重組；QA sidecar 綁定來源與 Builder provenance；delivery receipt 記錄 SHA、Run、attempt、commit。
- 寫入 main 後遠端回讀三檔，核對 Git blob SHA／SHA-256；使用既有 Pages workflow 部署並實際驗證公開 URL。
- 審核版交付不等於正式發布。Builder exact-blob approval、REVIEW_READY、Stage 6 DELIVERED_AND_PUBLICLY_VERIFIED receipt 均不代表首頁發布核准。正式發布必須有使用者對明確 report_date／Preview 版本的獨立核准，並更新 `production/config/homepage-publication-lock.json` 為 APPROVED_PUBLICATION、綁定 Preview／index Git blob SHA 與精確 `[publish-tac-report:YYYY-MM-DD]` commit marker；Pages 與 archive workflow 先驗證 lock，否則禁止部署或封存。未核准時 lock 必須保持 BASELINE_LOCKED。
- 舊 `archive_index.yml` 自動封存與新核准流程衝突，正式切換前必須整併／停用自動封存觸發，防止未核准封存或錯誤日期封存。

## 9. Chart 3 與資料寫入權
- 正式 Chart 3 資料路徑為 `data/tac-chart3/`，不可另建 `data/chart3/`。
- Stage 2 是 S&P 500 每日增量唯一早報寫入者；Chart 3 S&P500 merge workflow 在 Main production workflow 結束後，依唯一 workflow_run_id 與 Stage 2/3 receipt 驗證結果讀取非空增量帳並合併，與 Stage 4–6 不並行。FRED/ALFRED 更新只負責其既有宏觀序列；Chart 3 自己的資料維護鎖只序列化 Chart 3 工作，不得阻塞早報 Stage 4–6。
- Calendar updater 是週 JSON 唯一 writer；Stage 3 唯讀。
- Stage 5 是本次 HTML 唯一 writer；Stage 6 是交付 sidecar 唯一 writer。

## 10. Run、恢復與效率
- 每次唯一 Run ID 固定為 TAC-{report_date}-{workflow_run_id}，不得包含 workflow_run_attempt。綁定 report_date、Asia/Taipei、起始 main commit，以及 MASTER／六份 Stage WR／contracts／schemas／Manifest／母版／QA／Builder approval／Builder／Stage runners／依賴／Workflow 的 governance blob SHA。Retry／Resume 沿用原 Run ID；只有明確 rerun（新 workflow_run_id）才建立新 Run。Stage 5 必須比對全清單，禁止跨版本 Run。
- 同一 report_date 不可有兩個並行正式 Run。
- 每個 Stage 完成即保存輸出 SHA 與狀態；失敗只從最後有效 Stage 恢復。
- 已鎖定行情不重抓；下游只讀快照。無關項目不因單項失敗停工。
- **早報時間預算（台灣時間，冬令；週二至週六製作）**：04:45 Stage 1 啟動，05:00 Stage 2 開始正式收盤擷取；05:15 前完成 Stage 2 observation handoff 是目標，05:20 前完成 Stage 1–3 Capture 是目標，05:30 前交付審核版是整體 30 分鐘效率目標。夏令時間整體平移一小時（03:45／04:00／04:15／04:20／04:30）。這些是執行預算與告警節點，不是允許以盤中價、舊值或未核准來源補數的硬性通關條件；逾時時保留已核實資料、對未完成欄位如實標示，並立即繼續可獨立完成的下游工作。
- Stage 1→Stage 2 handoff 正常預留 15 分鐘；Stage 2 worker 05:00（夏令 04:00）喚醒時，Stage 1 應已完成。僅允許額外 5 分鐘短暫交接容錯；不得等待 70 分鐘。
- Stage 2 observation handoff 自 worker 喚醒起以 15 分鐘為目標；Main Capture 對 observation 的輪詢上限 15 分鐘。Capture job 總 timeout 35 分鐘，作為故障保護而非正常工作時間。不得讓等待耗盡整份早報時間。
- Stage 4–6 `build-and-deliver` job timeout 為 45 分鐘，僅作執行故障保護；它不是額外增加的正常製作時間，也不得把整體 05:30 審核版目標延後。
- Stage 3 僅做既有資料庫唯讀投影，目標 5 分鐘內完成；不得因單一行情狀態未核實而停止其他已具備證據的工作。
- 30 分鐘為整體效率目標，不得以犧牲正確性換取。
- 不要求使用者逐步輸入「繼續」；除必要決策／授權外自動推進。

## 11. 變更閉環
每次改規則／欄位／模板／程式／Workflow／排程，必須回頭檢查所有上下游：Stage WR、contracts、Manifest、Builder selector、Schema、測試、唯一寫入者、Workflow 觸發、Pages、archive、排程及 Chart 3。寫入後回讀 GitHub，核對 commit、blob SHA 及內容。未測試不得宣稱通過。

## 12. 全域上線定義
六階段真實 E2E、兩種母版、44 項逐市場日期行情與 FedWatch、行事曆／財報／新聞／五層分析、Chart 3 增量交接與非阻塞派送、四類 QA、main preview 遠端回讀、Pages 公開驗證、核准後正式發布／封存、排程切換及 Simulation 未受修改均有證據，方可標正式上線。

## 13. 手動補救入口（Missed Schedule Recovery）
- 正常主流程仍只由 `.github/workflows/tac-production.yml` 的 schedule 啟動 Stage 1 → Stage 2 → Stage 3；台灣週二至週六製作（對應 New York 週一至週五），週一與週日不啟動；Stage 1 排程為台灣週二至週六夏令 03:45／冬令 04:45（15:45 ET，New York 週一至週五），其職責僅為建立唯一 Run、鎖定版本與發布 handoff，**不得擷取或判定美股正式收盤行情**。Stage 2 worker 為台灣夏令 04:00／冬令 05:00（16:00 ET），此時美股才正式收盤，Stage 2 自此時點起才可擷取當日美股收盤資料。報告資料截點另固定為美東 16:25，台灣夏令 04:25／冬令 05:25；週六製作隔週一報告時，該截點對應週五美東 16:25／台灣週六 04:25（夏令）或 05:25（冬令）。此為收盤後資料截點，不是 Stage 1 或 Stage 2 排程時間。Stage 1 須先提交 Run handoff，Stage 2 worker 才接手。手動補救不是第二個每日排程，也不得由 Stage 4 直接建立 Run。
- 若當日 schedule 未產生有效 Capture，授權操作者可在 GitHub Actions 的 `tac-production.yml` 使用 `workflow_dispatch`，選擇 `mode=recover`，並明確填入台灣報告日期 `YYYY-MM-DD`。不得使用 `validate` 或一般 `build` 代替補救。
- `recover` 必須選取唯一一個具有效 run-state.json 的未完成 Run，沿用原 run_id，從最後一個有效 PASS stage 接續；不得建立新 Run、重做已 PASS 階段或重抓已鎖定資料。只有一個有效候選時才可自動接續；候選為零或多於一個時 FAIL-CLOSED，保留全部 Run，不得猜測。若同一 workflow retry，必須直接沿用由 workflow_run_id 決定的原 Run ID。
- 啟動前檢查同一 report_date 是否已有 Run。具 run-state.json 的既有 Run 會阻止未授權的新 Run；無 run-state.json 的 Legacy Run 僅記錄於新 run-context.legacy_prior_run_ids，不讀取、不複製、不覆寫。一般 `recover` 僅允許接續唯一未交付 Run；已有 Stage 5／6 或 Preview 時 fail-closed。
- **使用者明確要求同一日期重新完整 E2E 時，才可使用 `workflow_dispatch mode=rerun`。** 必須填入精確 report_date，且只能 supersede 一個明確指定的既有 Run；不得以 push marker、一般 commit 或其他自動觸發方式建立 rerun。若恰有一個具 run-state 的既有 Run，新的 Run 使用新的 workflow_run_id 並記錄 `supersedes_run_id`；若只有無 run-state 的 Legacy Runs，建立全新 Run 並記錄完整 `legacy_prior_run_ids`，不得讀取或重用其資料。具 run-state 的既有 Run 多於一個時 fail-closed；不得建立並行 Run。
- `rerun` 不刪除任何舊 Run、Observation、截圖、FedWatch、editorial JSON、receipt 或 Preview。所有新輸入都寫入新 Run 的 `production/runs/<new_run_id>/`，舊 Run 保持唯讀稽核證據，不得跨 Run 複製資料。既有 Main Preview 三檔副本保存於 `production/superseded/<report_date>/<old_run_id>/preview/`；原核准的 `preview/main/<report_date>-review.*` 必須留在原路徑，以維持 Main Preview 稽核一致。新 rerun 只能交付至獨立的 `preview/main/<report_date>-rerun-review.*`，不得覆蓋原版。Simulation 的 `preview/` 根層輸出保持不變。正式首頁 `index.html`、首頁發布鎖及正式歷史封存不變。
- `rerun` 必須建立全新 blank-first Stage 1；Stage 2 重新讀取當輪完整 WR 後，重新擷取全部 44 項與 FedWatch。不得使用 `--reuse-observations`、舊 Run Observation、舊截圖、舊新聞或舊 FedWatch；每列記錄本次讀取時間並標示 `prior_observation_reused=false`。Stage 3–6 必須只使用新 Run 的資料。
- Capture receipt 必須記錄觸發事件、dispatch mode、workflow_run_id、run_id、report_date、supersedes_run_id、market snapshot SHA 與 research bundle SHA。手動補救／重跑只接受 `event=workflow_dispatch` 且 mode 與實際執行一致的成功 Capture；不得把 push validation、一般 capture、舊 Run 或 build Run 當成新 Capture 證據。
- 同一個 Main ChatGPT automation invocation 內，Stage 2 與 Stage 4 是兩個獨立的狀態檢查點：Stage 2 提交 Observation 後，等待同一 Run 的 GitHub Stage 2 驗證及 Stage 3 PASS；再讀取 Stage 4 完整 WR 與 Research Bundle，執行 Stage 4 並提交 editorial JSON。Stage 4 提交 editorial JSON 後，同一正式 workflow run 的 build-and-deliver job 會輪詢接續。若 Stage 3 未完成，worker 必須回報 DEFERRED 並保留同一 Run；不得自行建立 Run 或跳過 Stage 3。Stage 1–3 的 workflow_dispatch recover 會依 run-state 跳過已 PASS 階段；Stage 4–6 的 job retry 依 run-state 跳過已 PASS／PARTIAL 階段，只重做尚未完成階段。所有 retry/resume 沿用原 run_id。
- 手動補救僅交付 Main Preview；不自動更新 `index.html`、不封存正式歷史、不修改 Simulation。正式首頁仍需使用者另行核准。
- 一次 DEFERRED／FAILED 不得自動停用 ChatGPT automation；既有排程必須維持啟用，讓同一 Run 可安全恢復或下一個工作日正常接續。


## 14. 2026-11-27 使用者核准的正式製作週期變更
- 生效規則：每週二至週六製作早報；週一與週日不執行正式製作。
- 週二製作：週一市場行情，report_date 週二，Weekday template。
- 週三製作：週二市場行情，report_date 週三，Weekday template。
- 週四製作：週三市場行情，report_date 週四，Weekday template。
- 週五製作：週四市場行情，report_date 週五，Weekday template。
- 週六製作：週五市場行情，report_date 為隔週一，Monday template；母版內上週經濟／財報區塊保留，行事曆投影需讀報告週與前一週。
- 週六新聞窗口：起點為週五 12:00 台灣時間；截止點是 Stage 4 research bundle 建立當下實際時間（Asia/Taipei），不可沿用舊週一時間或固定週六時間。週六／週日如發生重大新聞，只有經人工明確決定後才可置換；不得自動修改已交付 Preview。
- production_date 與 report_date 必須分開保存。週六 production_date 是週六，report_date 是隔週一；Stage 1 Run ID、所有日期化檔案與正式發布鎖均以 report_date 命名。
- Stage 2 target date 與每個商品的實際 market data_date 仍依市場交易日曆核對；本規則只定義共用交易日錨點，不可用它覆蓋各商品個別日期。


## 14. Main Run state v1.2（唯一狀態真相）

- 每個 Run 只有一個權威狀態檔：production/runs/<run_id>/run-state.json；不另建第二套 state DB、日期共用 lock DB 或重複 receipt ledger。正式切換前，既有 Automation 任務提示詞必須更新為最小 bootstrap：每次喚醒先讀取並嚴格遵循 production/CHATGPT_AUTOMATION_PROMPT_MAIN_v1.2.md，再以 Stage 1 governance pin 核對該檔 Git blob SHA；若缺檔或 SHA 不符即 DEFERRED。此分支只建立並 pin 提示詞文件，不修改線上任務或排程。
- 初始狀態由 Stage 1 與 run-context、fixture、Stage 1 receipt 同一 commit 提交：Stage 1=PASS、Stage 2=READY、Stage 3–6=NOT_STARTED。
- 每階段狀態：NOT_STARTED、READY、RUNNING、SUBMITTED、PASS、DEFERRED、PARTIAL、FAILED、SKIPPED。只有 Stage 2/4 ChatGPT submission 可用 SUBMITTED；只有 Stage 2/5 可用 PARTIAL，且 PARTIAL 是終態，不得重新開啟。整體狀態：RUNNING、PARTIAL、FAILED、REVIEW_READY、AWAITING_APPROVAL、PUBLISHED。Stage 5 PASS=REVIEW_READY；Stage 6 PASS=AWAITING_APPROVAL；DELIVERED_AND_PUBLICLY_VERIFIED 僅為 Stage 6 receipt status。
- Stage 2 worker 只能在 Stage 2=READY 時 claim RUNNING；Observation 寫入 production/runs/<run_id>/market-history-web-observations.json，提交後將狀態改為 SUBMITTED 並記錄 Observation SHA。GitHub Stage 2 Runner 驗證 exact SHA 後才可改 PASS/PARTIAL。
- Stage 3 只在 Stage 2 PASS/PARTIAL 後啟動；完成後將 Stage 3 改 PASS、Stage 4 設 READY。
- Stage 4 編輯內容唯一位置為 production/runs/<run_id>/stage4-editorial-content.json，必須綁定 run_id、report_date、market_snapshot_sha256、research_bundle_sha256、stage3_receipt_sha256 與 stage4_wr_sha256。Stage 4 worker claim RUNNING，提交完整內容後改為 SUBMITTED 並記錄 SHA；commit message 使用 [tac-stage4-submit:<run_id>] 作為稽核標籤；同一正式 workflow run 的 build-and-deliver job 會輪詢該檔案與 SUBMITTED state，不依賴 push event。GitHub Runner 驗證後改 Stage 4 PASS、Stage 5 READY。
- Stage 5 PASS 對應 QA receipt REVIEW_READY，Stage 5 PARTIAL 必須使 Stage 6=SKIPPED。Stage 2 PARTIAL 不得被 Stage 5 或 HTML Builder 覆蓋為 PASS。
- Stage 6 只接受 Stage 5 PASS；公開 Preview 驗證成功後改 Stage 6 PASS、overall_status=AWAITING_APPROVAL。這不代表已獲准更新 index.html 或正式 history。
- 每次狀態更新必須帶 expected state_version、expected previous status、input/output SHA 與 receipt path。GitHub Contents API 使用已讀取 blob SHA compare-and-swap；Actions git push 僅允許 fast-forward。遇到 stale SHA、non-fast-forward 或雙重 claim，重新讀取狀態後決定，不得 force-push 或盲目覆寫。
- RUNNING 必須記錄 lease_owner 與 lease_expires_at。未到期 lease 不可被其他 worker 接管；逾期恢復前先核對該 Run 最後一個 receipt 與實際產物。DEFERRED 不是 FAILED，不得停用 automation。
- Stage 1 是唯一正常 Run creator。Stage 1 必須先以標準函式庫建立並提交完整 handoff，再安裝重型依賴。相同 workflow retry 沿用相同 Run ID；recover 沿用既有 Run ID；只有明確 rerun 建立新 Run。
- Stage 2 與 Stage 4 的日期共用檔 production/input/market-history-web-observations-YYYY-MM-DD.json 及 production/input/report-content-YYYY-MM-DD.json 不再是正式輸入來源；任何新 Run 不得讀取或寫入這些舊路徑。
- 不依賴 GitHub connector push 喚醒第二個 Workflow；該觸發行為未獲證實。Stage 4–6 是同一正式 schedule／recover workflow run 的第二個 job，等待同一 Run 的 editorial JSON、Stage 4 SUBMITTED state 與 SHA。Marker 僅作稽核標籤。Build job 必須再次驗證 exact run_id、run-state、提交內容 SHA、Stage 3 receipt 與 Research Bundle SHA。
- Chart 3 是下游非阻塞支線。Chart 3 workflow_run 以 workflow_run_id 對應唯一 Main Run，只在同一 Run 的 Stage 2=PASS/PARTIAL 且 Stage 3=PASS 時接手；不依賴 push marker。Stage 2 增量 append 或 Chart 3 merge 失敗不得改變 Stage 2 PASS/PARTIAL，也不得阻止 Stage 4–6。
