# Main 重建全面盤點紀錄｜2026-11-27

盤點基準：main HEAD `f840986e0976013f940ef296d152e67ceb54ad44`
本文件是盤點底稿，不是 E2E 驗收或可生產聲明。

## 一、總結

Main 重建尚未完成全面盤點與跨階段接口驗證。最嚴重的 P0 是 Stage 2 的責任與傳輸斷點：正式規範要求 ChatGPT 直接瀏覽 Investing.com Historical Data；但 Main Workflow 仍直接呼叫 `run_stage2.py`，而 Runner 在當日 ChatGPT observation bundle 不存在時會呼叫 Playwright。現有 schema 僅定義資料形狀，沒有完成 ChatGPT 將結果交回同一 Run 的傳輸、接收、確認與 PARTIAL 恢復協定。

因此不能把現有 Stage 2 Runner／tests／receipt 的存在，當成 Stage 2 已串接。

## 二、已回讀的核心檔案及實際 SHA

| 檔案 | Main blob SHA | 實際狀況 |
|---|---|---|
| `production/MAIN_REBUILD_PLAN.md` | `1129f9949e281abcc9191dfea2aaf59a28169caa` | Phase 0 標 DONE，但多處仍列 Phase 1–6 未完成。 |
| `production/PHASE0_INVENTORY.md` | `bd1c5935989eb9d931dcba7cc27615437107e69c` | 盤點基準 HEAD `7df1f84` 已落後目前 main；文件本身亦列多項待查項目。 |
| `production/MASTER_WR.md` | `25fe936b6cafff82780ff06c309e9ec822b84f01` | v1.2，定義 Main 唯一規範及 Stage 2 截圖／Investing.com／四頁並行原則。 |
| `production/stages/STAGE_2_MARKET.md` | `0c4e70c6e3e5addee7984a80b45d1553646accce` | 要求 ChatGPT 瀏覽器讀取、44 列 observation、receipt、FedWatch、Chart 3。 |
| `production/contracts/SOURCE_POLICY.md` | `b38ca5845a52ede91d0c9551a2d19da7c538aee0` | 明定 ChatGPT browser read，禁止未核准來源替代及 Cloudflare 繞過。 |
| `production/contracts/HANDOFF_CONTRACT.md` | `bcfae545634374673607d7d588789c277947d309` | 定義 Stage 2 輸出，但未完整定義 ChatGPT↔GitHub transport／ack／resume。 |
| `production/runner/README.md` | `953c067aac4009c50cb67736169f6d79d1934fdc` | 仍描述 capture workflow 自行 captures 44 indicators，與 Stage 2 ChatGPT 責任不一致。 |
| `.github/workflows/tac-production.yml` | `5ffbc27d3a84d8b2580b8edd610b13519954e291` | Stage 2 直接執行 `run_stage2.py --concurrency 4`，接著同 job 執行 Stage 3。 |
| `production/runner/run_stage2.py` | `21774db465a4e65ed9e416c6e4a84b79b5144740` | 有 web bundle、reuse、Playwright 三種分支；無 bundle 時走 Playwright。 |

## 三、Stage 2 P0 斷點

1. **執行責任錯置**：Workflow 直接執行 Runner；Runner 預設可自行開頁擷取，與規範指定 ChatGPT 讀取不一致。
2. **缺少工作包**：Stage 1 沒有完整產生可交給 ChatGPT 的 Run-scoped 44 項工作包（Run ID、report/trading date、商品身份／URL、pinned SHA、截圖欄位及缺欄清單）。
3. **缺少回傳協定**：雖有 `market-history-web-observations.schema.json`，但沒有完整定義 ChatGPT 如何把當輪結果安全交回 Main，如何綁定 Run、日期及 SHA。
4. **缺少接收確認**：沒有清楚的 bundle 接收 receipt、重複提交防護、same-Run acknowledgement 及 Stage 3 gate。
5. **缺少 PARTIAL 恢復流程**：未定義已鎖定欄位如何保留、ChatGPT 如何只補 unresolved rows，以及如何防止跨 Run 混用。
6. **Chart 3 邊界待核對**：Stage 2 Runner append、Workflow commit ledger、merge workflow dispatch 三者需明確分離 append writer／merge writer，驗證冪等與失敗恢復。

`--reuse-observations` 只重用 Run 目錄中已有觀察檔，不建立上述工作包、傳輸、接收及確認協定，不能視為架構修復。

## 四、其餘階段與舊流程盤點

| 範圍 | 已回讀事實 | 未完成驗證 |
|---|---|---|
| Stage 1 | 有 Run fixture、日期／母版／治理 SHA 鎖定規範 | Stage 1 工作包是否完整供 Stage 2 使用 |
| Stage 3 | 有 calendar projection Runner；規範唯讀同一 pinned commit | 與新 Stage 2 handoff 的真實 same-Run 串接 |
| Stage 4 | 有 research bundle、content validator、Stage 4 Runner | ChatGPT 是否能自動產出並提交完整綁定的 editorial JSON |
| Stage 5 | 有 Builder、QA Runner、deterministic tests | 當前 Builder exact SHA 核准及真實輸入 E2E |
| Stage 6 | 有三檔 preview delivery、Pages dispatch／驗證程式 | 真實交付、遠端回讀、公開 URL 驗證 |
| Calendar | Stage 3 規範唯一讀取週 JSON；04:35 updater 為 writer | updater 實際 schema／排程／writer 全盤核對 |
| Chart 3 | 有 S&P500 increment、merge workflow、FRED/ALFRED workflow | append／merge／其他舊 workflow 寫入邊界與併發 |
| Preview／History | Pages workflow 部署 preview/history；archive workflow 仍監聽 index push 並排程 | 舊 archive 是否違反核准後發布原則 |
| 舊 Pipeline | `tac-simulation-lab.yml` 仍監聽 Simulation branch 並可交付 main/preview | 新 Main E2E 完成前保留；切換時需防止同日期雙流程交付 |
| 舊行情 workflow | `tac-market-source-capture.yml` 只 checkout Simulation | 僅作 Simulation 歷史用途，不可替代 Main Stage 2 |
| 舊資料 workflow | `main.yml` 排程執行舊 update scripts 並 `git add data/` | 必須確認是否觸及早報／Chart 3 共用資料路徑 |

## 五、修復順序

### P0 — Stage 2 架構先行
- 定義 Stage 1 完成後的明確等待／handoff 狀態。
- 建立 Run-scoped Stage 2 work packet。
- ChatGPT 依截圖優先及 concurrency=4 規則直接瀏覽 Investing.com，產生 44 項 observation。
- 建立 ChatGPT→Main bundle 傳輸、SHA、schema、Run/date 綁定、接收 acknowledgement。
- GitHub 只做驗證、fixture 組裝、manifest、audit、receipt、Chart 3 append／merge handoff，不代替 ChatGPT 擷取行情頁。
- 定義 PASS／PARTIAL／FAIL 及只補 unresolved rows 的恢復流程。

### P0 — Stage 2 內部一致性
逐項核對 screenshot parser、observation schema／validator、fixture bootstrap、source manifest、audit、receipt、status enum、Chart 3 helper 及其 tests；每條規範都要對應程式、測試及收據欄位。

### P1 — 六階段接口
逐一驗證 Stage 1→2→3→4→5→6 的 input/output、Run ID、日期、SHA、PARTIAL／FAIL 語意及恢復策略。

### P1 — 全域 writer／workflow
確認行情、calendar、Chart 3、preview、history、index、Pages 的唯一寫入者；逐一核對 schedule、push、workflow_run、dispatch、branch scope、permissions、concurrency。

### P2 — 真實 E2E
先完成 Stage 2 ChatGPT bundle 正反向測試，再執行六階段真實資料 E2E。真實 E2E 通過前，不切換正式排程、不退役 Simulation 歷史流程。

## 六、保護邊界

- Simulation branch 唯讀，不修改、不停用、不重寫。
- 不繞過 Investing.com Cloudflare，不用未核准來源替代。
- 不更新正式首頁 `index.html`，不封存正式歷史報告。
- 不觸發新的正式行情 Capture 或修改正式排程。
- 後續任何程式修正必須同步更新計畫、Manifest、contracts、tests，並以實際 CI／E2E 證據驗收。
