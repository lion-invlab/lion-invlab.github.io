# TAC Main 重建總計畫 v2.0

**更新日期：2026-11-27**  
**目標：交付 2026-11-27 早報審核版，並建立可重複、可追溯、無需使用者逐步催促的 Main 生產流程。**

本文件取代本檔先前互相矛盾的階段紀錄與日期模型。舊版提交仍保留於 Git 歷史；後續以本版作為 Main 重建主軸。Simulation 分支只作 SIM-1.4 規範參照，禁止修改。

---

## 1. 最終交付定義

每個台灣工作日只允許一個正式 Run，完成以下流程：

`Stage 1 → Stage 2 → Stage 3 → Stage 4 → Stage 5 → Stage 6`

- Stage 1–3：建立 Run、取得並凍結 44 項行情、讀取行事曆與財報。
- Stage 4：ChatGPT 讀取同一 Run 的研究資料包，產生新聞與市場分析。
- Stage 5：Main Builder 產生 HTML 並完成結構、內容、視覺 QA。
- Stage 6：只交付 `preview/YYYY-MM-DD-review.html`、QA sidecar、delivery receipt，並驗證公開 Preview。
- 正式首頁 `index.html`、正式歷史封存及任何對外正式版，均不在自動交付範圍；只有使用者明確核准後才可處理。

審核版必須完整呈現 44 項各自的 VERIFIED、BACKUP_VERIFIED、MARKET_CLOSED、SOURCE_NO_DATA 或 TOOL_READ_FAILURE 等正式狀態。未核實值不得進入分析當成事實；不能為了版面完整而補舊行情。

## 2. 職責分配（不可越權）

| 工作 | 唯一主要執行者 | 輸出／責任 | 明確禁止 |
|---|---|---|---|
| Stage 1：日期、Run、母版、Manifest、治理 SHA、calendar SHA 鎖定 | GitHub Actions + Main Runner | run-context、blank-first fixture、Stage 1 receipt、Stage 2 work packet | 不以 NYSE 最近交易日覆蓋全球所有市場；不抓行情 |
| Stage 2：讀取截圖、Investing.com Historical Data、FedWatch | ChatGPT | 同 Run 44-row observation bundle、來源頁證據、FedWatch 證據 | 不使用搜尋摘要、Yahoo、未核准 API；不繞過 Cloudflare；不重用前次行情或截圖 |
| Stage 2：資料驗證、狀態分類、fixture 回填、快照凍結、Chart 3 增量 | GitHub Actions + Main Runner | snapshot、manifest、audit、receipt、S&P500 increment | 不自行以 Playwright 取代 ChatGPT 的來源讀取；不把缺資料改成 CLOSED |
| Stage 3：行事曆／財報投影 | GitHub Actions + Main Runner | pinned calendar projection、receipt | 不修改週資料庫；不重新抓日曆 |
| Stage 4：新聞、總結、情緒、五層分析、政治掃描 | ChatGPT | Run-scoped editorial JSON、來源與研究證據 | 不改行情快照；不使用外部 LLM API；不跨 Run |
| Stage 5：HTML Builder、QA | GitHub Actions + Main Runner | HTML、render manifest、QA sidecar、prebuild receipt | 不改行情、不代寫新聞、不自動放寬 QA |
| Stage 6：Main Preview 交付 | GitHub Actions + Main Runner | 三檔 Preview、Pages run、遠端 SHA／URL 驗證 | 不碰 index.html、不自行封存正式版 |
| 行事曆資料庫更新 | 04:35 專用 updater | `data/calendar/weeks/YYYY-Www.json` | Stage 3 不可寫入；其他工作流不得成為第二寫入者 |
| Chart 3 FRED／ALFRED 更新 | 既有 Chart 3 updater | VIX/NFCI/NFCICREDIT/STLFSI4 等既有序列 | 不寫入 S&P500 daily increment |
| S&P500 Chart 3 增量 | Stage 2 唯一 writer | 已核實 S&P500 現貨 close、SHA、防重及日期序 | 不另抓第二份報價；不與 FRED updater 共用寫入責任 |
| 正式首頁決策 | 使用者 | 核准或不核准正式首頁更新 | 自動流程不得代替使用者核准 |

**使用者操作原則：** 使用者不負責逐步輸入「繼續」。只在需要提供當日截圖、處理真正無法取得的必要輸入或核准正式首頁時介入。ChatGPT／Runner 必須自行完成可完成的步驟，並回報阻塞原因與證據。

## 3. 日期模型：報告日與市場狀態分開

- 台灣報告日為 `report_date`。
- 週二至週五報告，目標資料日為前一個日曆日；週一報告，目標資料日為前一個週五。
- 例：2026-11-27 早報的目標資料日為 **2026-11-26**。美國感恩節休市的商品必須標記 CLOSED；亞洲、歐洲及外匯市場則讀取 11/26 實際資料。不得把 11/25 的美股收盤值冒充 11/26 行情。
- Stage 1 只鎖定報告規則產生的共同目標日；Stage 2 逐項依該商品所屬市場的官方日曆與 Investing.com 歷史表格判斷該目標日是否有資料。
- 頁面可讀但缺少目標日列：SOURCE_NO_DATA；工具無法讀取頁面／表格：TOOL_READ_FAILURE；只有可回查的官方市場日曆明確證明休市，才可標 MARKET_CLOSED。
- 不得用 NYSE 單一交易日曆決定亞洲、歐洲、外匯及商品的資料日期。不得把「表格沒有該日期」直接推定為休市。
- Stage 1 已將預設日期解析由 NYSE-only 改為上述報告日規則；回歸測試正在執行，未通過 CI 前不宣稱完成。

## 4. 唯一 Run 與 ChatGPT ↔ GitHub 交接

### 4.1 Run-scoped 原則

所有可變的當日資料都必須放在：

`production/runs/<run_id>/`

包括：
- `run-context.json`
- `report-data.json`
- `stage1-receipt.json`
- `market-history-web-observations.json`
- `stage2-market-snapshot-receipt.json`
- Stage 2 audit／manifest／summary
- `stage3-calendar-projection.json`、Stage 3 receipt
- `stage4-research-bundle.json`
- `report-content.json`
- Stage 4–6 receipts、HTML、QA、render manifest、delivery receipt

禁止用同一個日期檔案覆寫另一個 Run 的內容。所有 handoff 必須包含 run_id、report_date、trading_date、schema_version、created_at、input/output refs、SHA-256、狀態、未解項目及警告。

### 4.2 兩段式交接

現行單一 Capture job 把 Stage 1–3 一次跑完，沒有讓 ChatGPT 在 Stage 1 後讀取當輪 Run 的正式交接點；Stage 2 Runner 在缺少 ChatGPT observation bundle 時還會啟動 Playwright。這與規範要求的 ChatGPT 直接開啟 Investing.com 歷史頁不一致，是目前最優先的架構缺陷。

目標交接必須改為：

1. **Stage 1 Prepare：** 唯一 weekday schedule 啟動；Runner 建立 Run、鎖定日期／母版／治理 SHA／calendar SHA，產生 blank-first fixture 與 Stage 2 work packet，提交 Run-scoped 證據後停止，狀態為 `AWAITING_CHATGPT_STAGE2`。
2. **ChatGPT Stage 2：** 讀取該 Run work packet；先採用當日有效截圖，缺欄才開 Investing.com Historical Data；最多同時讀取 4 個不同頁面；完成 44 列 observation 與 FedWatch，寫入同一 Run 的 bundle。Bundle 必須明確綁定 run_id、兩個日期及 Stage 1 fixture/context SHA。
3. **Stage 2 Complete：** ChatGPT 將 observation bundle 寫入 Main；以明確的同 Run handoff marker 觸發唯一 Main workflow。Runner 只驗證 bundle、回填 fixture、凍結 snapshot、產生 receipts；禁止在沒有 ChatGPT bundle 時 fallback 到 Playwright。
4. **Stage 3：** 同一 workflow 讀取 Stage 1 pinned commit 的 calendar JSON，唯讀產生 projection；產出 research bundle 與 `AWAITING_CHATGPT_STAGE4` receipt。
5. **ChatGPT Stage 4：** 讀取同 Run research bundle，生成完整 editorial JSON，綁定 run_id、market_snapshot_sha256、research_bundle_sha256；寫回同 Run。
6. **Stage 4–6 Build：** 以同 Run build marker 觸發 Runner；Runner 驗證 JSON、執行 Stage 4、Stage 5 Builder／QA、Stage 6 Preview delivery。
7. **完成條件：** 遠端 Preview HTML bytes、Git blob SHA、QA sidecar、Pages workflow 與公開 URL 全部核對一致；回寫同 Run 最終 receipt。

不得以外部模型 API 或額外付費模型作為必要依賴。ChatGPT 是瀏覽器研究與編輯執行者；GitHub Actions 是確定性驗證、編排、渲染、QA 與交付執行者。

## 5. Stage 1–6 工作規格

| Stage | 必要輸入 | 必要輸出 | 失敗／重試原則 |
|---|---|---|---|
| 1 | report_date、日期規則、Main MASTER WR、六份 Stage WR、contracts、schema、兩種母版 Manifest、calendar JSON | Run context、blank fixture、Stage 1 receipt、Stage 2 work packet | 任何 SHA／母版／calendar pin 不符即停止；不可建立第二個同日有效 Run |
| 2 | 同 Run work packet、當日 screenshot sidecar／原圖（若有）、Investing.com 頁面 | 44-row observations、FedWatch、snapshot、manifest、audit、receipt、Chart3 handoff | 每列有值或明確狀態；只刷新 unresolved；已 VERIFIED 不重抓；Cloudflare 不繞過 |
| 3 | Stage 1 pinned main commit、calendar read receipts、Stage 2 frozen snapshot | 本週／上週 calendar & earnings projection、receipt、research bundle | 來源 JSON 缺漏或 SHA 不符即停止；不改 DB |
| 4 | Stage 2 snapshot、Stage 3 projection、research bundle、新聞來源 | 5 則 Global Focus、10 則 Market Headlines、三段總結、Market Sentiment、五層分析、六領域政治掃描、editorial JSON | 新聞需在規定時間窗；每項主張有來源；未核實行情不得寫成事實 |
| 5 | 同 Run Stage 1–4、exact Builder approval、prebuild receipt | HTML、render manifest、QA sidecar、Stage 5 receipt | Builder blob／治理 SHA／資料 schema／DOM／視覺任一失敗即停止；不放寬門檻 |
| 6 | Stage 5 REVIEW_READY artifacts | 三檔 dated Preview、Pages deploy evidence、遠端 SHA／URL 驗證 | 僅允許 Preview 三檔；不覆寫已存在 Preview；不得碰正式首頁 |

## 6. 資料寫入權責矩陣

| 資料／路徑 | 唯一寫入者 | 其他角色 |
|---|---|---|
| `production/runs/<run_id>/*` | 對應 Stage Runner／ChatGPT handoff，各自只寫所屬 stage artifacts | 下游唯讀；同 Run SHA 驗證 |
| `data/calendar/weeks/*` | TAC 行事曆資料庫 updater | Stage 1/3 只讀、pin SHA |
| `data/tac-chart3/sp500_daily_increment.jsonl` | Stage 2 已驗證 S&P500 handoff | merge workflow 只做 append ledger 合併／整理 |
| Chart 3 FRED/ALFRED series | 既有 FRED updater | 不碰 S&P500 increment |
| `preview/YYYY-MM-DD-review.*` | Stage 6 | 其他工作流不得建立或覆寫 |
| `index.html` | 使用者明確核准後的正式發布流程 | TAC Main pipeline 禁止寫入 |
| `history/*`、`history/index.json` | 正式版核准後的封存流程 | 未核准不得自動封存 |
| `production/input/*` | 僅限版本化設定／截圖原始輸入；當日觀察 bundle 應改為 Run-scoped | 不得用日期全域檔案跨 Run 覆寫 |

## 7. Workflow 與 Automation 佈局

- `.github/workflows/tac-production.yml` 是 Main 唯一早報生產入口，負責 schedule、Run 建立、Stage Runner、同 Run handoff marker、Build、權限與提交邊界。
- Main weekday schedule 只負責啟動 Stage 1，不可在沒有 ChatGPT observation bundle 時自行執行 Stage 2。
- ChatGPT Stage 2 worker 在 Stage 1 work packet 可讀後接手；ChatGPT Stage 4 worker 在 Stage 3 research bundle 可讀後接手。可由同一 Main continuation automation 分段完成，但每段都必須有 Run ID／SHA gate，不能用「等待」冒充完成。
- 04:35 Calendar updater 是獨立唯一寫入者；05:30 Chart 3 任務須在確認與 Stage 2 S&P500 writer 不重複後才決定是否保留；不得另建重複早報主排程。
- 已逐一讀取 Main 上 24 份 GitHub Actions workflow（本輪 HEAD `b42476f2077f8b9b8a4eb67048e7c5aaecfaacb3`）。觸發／寫入衝突初步結果：
  - `tac-production.yml`：schedule 直接串 Stage 1→2→3；push 只做 validation 或 build marker，沒有 Stage 2 bundle handoff marker。
  - `tac-simulation-lab.yml`：只由 Simulation branch push／dispatch 啟動；它會將 QA 通過的三檔審核版寫入 Main `preview/`，因此是 Main Preview 的第二個 writer，切換前必須建立停用／封存方案，但不得修改 Simulation branch。
  - `pages.yml`：會因 Preview、Chart 3、index 等路徑及 Chart 3 workflow_run 部署整站；部署本身不寫早報資料，但需核對 Stage 6 遠端驗證與並行部署。
  - `archive_index.yml`：除 index push 外另有每日排程，會自動封存正式首頁；與「正式封存須經使用者核准」存在政策衝突，正式切換前必須處理。
  - `main.yml`：更新兩個波動率／watchlist 腳本後使用廣泛的 `git add data/`，可能把同一工作目錄中其他資料變更一併提交；需縮小到腳本實際輸出檔案並加寫入隔離。
  - `tac-chart3-incremental.yml`：只由專用 trigger marker 啟動，寫 Chart 3 FRED／ALFRED 資料；未直接監聽 S&P500 ledger。
  - `tac-chart3-sp500-increment-merge.yml`：ledger push／dispatch 均可啟動，負責合併 compact S&P500 歷史。
  - 其他公司資料、視覺 QA、測試及 Simulation 專用 workflow 已列入 24 份清單；目前未發現它們直接成為 Main 早報 Stage 1–6 的第二入口。
- Stage 2 不只 Runner 有 Playwright fallback：`validate_chatgpt_web_observations.py` 在日期截圖 sidecar 存在時也會轉交 `browser_verify_market_history.py`；Stage 1 bootstrap 與 Runner／validator 仍讀取日期級 sidecar／bundle 路徑。R2 必須同時移除兩處自動瀏覽替代路徑並改為同 Run handoff。
- GitHub Actions connector 支援 Git Blob 的 base64 建立及 tree／commit／ref 更新，因此二進位截圖證據可透過 Git Data API 寫入 Run 專屬路徑；這解決了「只能用文字 Contents API」的初步疑慮，但實作仍須加上路徑白名單、SHA 回讀及檔案大小限制。
- Main Stage 4 continuation automation 本輪回讀為 `is_enabled=true`，下次預定 2026-11-30 05:15 Asia/Taipei；先前結果只證明 11/27 Capture 未啟動，不能誤記為目前停用。
- GitHub push validation、workflow_dispatch validate、CI PASS 均不得冒充 schedule Capture 或 Stage 1–6 E2E。
- 所有自動化須明確報告實際 event、workflow_run_id、run_id、日期、receipt SHA 與最終狀態；沒有證據就標示未驗證。

## 8. 目前 Main 已知狀態與缺口

### 已確認
- Main 主規範為 `production/MASTER_WR.md` v1.2；Simulation SIM-1.4 僅作規範基準。
- Monday／weekday 兩份母版與 Manifest 已建立。
- Stage 1–6 Runner、contracts、schemas、Builder、QA 與 Main Workflow 已存在。
- Stage 2 的 blank-first、截圖優先、44 項、4 頁並行、官方休市證據、Chart 3 handoff 等規則已有部分 deterministic tests。
- 11/27 失敗 Run `TAC-2026-11-27-45912371719-1` 的 Stage 2 使用 Playwright；42/44 項因 403 無法讀取，MOVE 未完成，WTI 合約標籤缺失。該 Run 的交易日為 11/25，不可拿來作 11/27 最終報告。
- 11/27 的最新 push validation 成功只代表 deterministic tests；當日沒有成功的 schedule Capture，也沒有 Stage 1–6 E2E。

### 必須完成
1. 完成 Stage 1 → ChatGPT Stage 2 → Runner Stage 2/3 的 Run-scoped 兩段式 handoff；移除 Stage 2 的 Playwright fallback。
2. Stage 2 bundle schema、validator、Runner、workflow、handoff contract 全部改為同 Run 路徑與 run_id/context SHA 綁定。
3. 日期規則及跨市場休市測試完整化；11/27 目標資料日固定為 11/26，美股休市不可回退至 11/25。
4. Stage 4 editorial JSON 改為 Run-scoped，避免日期檔案跨 Run 混用；Stage 4 continuation 必須讀取精確 Run 的 bundle。
5. 統一 Builder approval、README、PORT_MANIFEST、MASTER WR、Stage WR 的 exact blob 與狀態說明。
6. 驗證 Chart 3 S&P500 increment 唯一寫入、merge 防重、FRED updater 無重複寫入。
7. 盤點並處理 archive_index、pages、main、舊 Simulation-to-Main preview workflow 的觸發與寫入衝突。
8. 完成真實 44 項 capture、Stage 3、Stage 4、Builder、QA、Pages Preview 的端到端驗收。

## 9. 實施順序與每階段回頭檢查

| 順序 | 工作 | 完成條件 | 主軸檢查 |
|---|---|---|---|
| R0 | 全面現況盤點與責任矩陣 | 每個 workflow、資料路徑、writer、automation、stage 有唯一責任人 | 是否直接支持 11/27 早報與未來每日生產 |
| R1 | Stage 1 日期／Run 基準 | 11/27 → 11/26；週一 → 前週五；Run／SHA／母版鎖定 | 是否不再將 NYSE 日期套用全市場 |
| R2 | Stage 2 ChatGPT ↔ GitHub handoff | 同 Run bundle、schema、SHA、狀態完整；移除 Playwright fallback | ChatGPT 讀來源、Runner 驗證，職責沒有混淆 |
| R3 | Stage 2–3 真實資料 | 44 項逐列完成；Chart3 append 正確；calendar readonly | 未核實值沒有混入分析 |
| R4 | Stage 4 編輯 handoff | 5+10 新聞、三段總結、情緒、五層分析，綁定同一 snapshot/bundle | 分析完全依據本 Run 的資料 |
| R5 | Stage 5 Builder／QA | exact Builder SHA、DOM、內容、視覺 QA PASS | 不改母版、不補造資料 |
| R6 | Stage 6 Preview | 三檔 Preview、Pages、遠端 SHA 與 URL 驗證 | 沒有寫入 index.html 或正式封存 |
| R7 | 排程與衝突切換 | 真實 schedule Run、ChatGPT handoff、全鏈 E2E、writer/trigger 唯一 | 使用者不需逐步催促，流程可獨立完成 |

每完成一個 R 階段，都必須先回頭核對本節目標、寫入權責矩陣、未完成阻塞與 11/27 早報狀態；若發現新工作不能直接解除阻塞或降低生產風險，不得擅自擴大範圍。

## 10. 2026-11-27 當日早報處理原則

- 目標 report_date：2026-11-27；目標資料日：2026-11-26。
- 已有失敗 Run 使用 2026-11-25，且 Stage 2 多數頁面讀取失敗；不得沿用其行情或將其改標為成功。
- 必須以 11/26 目標日重新建立正確的單一 Run，44 項逐列讀取或以官方證據標示 CLOSED；11/26 目標日缺列但無官方休市證據者，保留 SOURCE_NO_DATA，不得回填 11/25。
- 先完成 Stage 2 observation bundle 與驗證，再進 Stage 3、Stage 4、Stage 5、Stage 6。不可跳過 Stage 2 或直接用舊審核版改日期。
- 只交付 11/27 Main Preview；正式首頁仍待使用者另行核准。

---

**目前狀態（2026-11-27 08:40 Asia/Taipei）：**
- R0 全面現況盤點：已完成 24 份 workflow 的逐一讀取與初步 trigger／writer 矩陣；發現 Preview 雙 writer、archive 自動封存政策衝突、main.yml 廣泛 data staging，以及 Stage2 雙 Playwright fallback。R0 的盤點已完成，衝突處理列為 R7 切換 Gate，不在 E2E 前任意停用舊流程。
- R1 日期基準：`create_run_fixture.py` 已採台灣報告日規則；2026-11-27 → 2026-11-26。CI #395（GitHub Run `45916213111`）與更新本計畫的 CI #396（GitHub Run `45918547203`）均已 success；兩者都是 deterministic validation，不是當日 Capture 或 E2E。
- 11/26 休市證據：Nasdaq／Cboe 官方交易日曆確認美國股票與選擇權市場 11/26 休市；SIFMA 確認美國固定收益市場 11/26 full close。不得將 11/25 價格回填為 11/26。
- R2 尚未完成：現行 `tac-production.yml` 仍在同一 Capture job 直接呼叫 Stage 2 Runner；Runner 在缺少 ChatGPT bundle 時仍有 Playwright fallback，且 observation bundle／editorial input 仍使用日期級全域路徑，尚未完成 Run-scoped handoff。
- 11/27 當日尚無成功的 11/26 Stage 2 snapshot、Stage 3 receipt、Stage 4 editorial JSON、Stage 5 QA 或 Stage 6 Preview。舊失敗 Run `TAC-2026-11-27-45912371719-1` 的 trading_date=11/25，不得重用。
- 下一個唯一工程主軸：完成 R2 的兩段式 Run-scoped handoff（Stage 1 commit → ChatGPT Stage 2 bundle → Runner Stage 2/3 → ChatGPT Stage 4 JSON → Runner Stage 4–6），同步更新 schema、validator、Runner、Workflow、contracts、tests、README、PORT_MANIFEST；移除 Stage 2 Playwright fallback。未完成前不得宣稱 11/27 早報已產出.
