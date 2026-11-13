# W46 財報資料欄位與來源完整性盤點｜2026-11-13 最新回讀

## 最新正式資料基準

- Repository：`lion-invlab/lion-invlab.github.io`
- Production branch：`main`
- Main HEAD：`68223e3aa384ae4d75311a243eb029da3c55b32c`
- Main WR：v5.15；blob SHA：`23b52f27b7afad083bbe28ed86021e04759f198d`
- W46：`data/calendar/weeks/2026-W46.json`
- W46 blob SHA：`ec246b8a765c64b798e348ce8df2760ea89cc5e1`
- W46 updated_at：`2026-11-13T18:59:36+08:00`
- schema_version：1
- Events：16 economic / 48 earnings / 129 audit
- Released earnings：45

> 本文件取代同日較早、以 42 筆 released earnings 與舊 W46 blob SHA 為基準的盤點。所有數字均由本次重新讀取 main JSON 計算；不得把舊報告的數字沿用為最新結果。

## 已公布財報欄位覆蓋（45 筆）

| 欄位 | 有值筆數 |
|---|---:|
| EPS actual | 38/45 |
| EPS estimate | 36/45 |
| EPS actual basis code | 18/45 |
| EPS estimate basis code | 15/45 |
| EPS actual currency | 19/45 |
| EPS estimate currency | 19/45 |
| EPS actual period | 45/45 |
| EPS estimate period | 0/45 |
| Revenue actual | 44/45 |
| Revenue estimate | 36/45 |
| Revenue actual basis code | 5/45 |
| Revenue estimate basis code | 2/45 |
| Revenue actual currency | 4/45 |
| Revenue estimate currency | 4/45 |
| Revenue actual period | 45/45 |
| Revenue estimate period | 0/45 |
| Revenue actual unit | 3/45 |
| Revenue estimate unit | 3/45 |
| judgment_engine_version | 0/45 |

### 數值缺漏名單

- EPS actual 缺值：PBR、CBRS、HIVE、SKYD、VG、ASTS、KSPI。
- EPS estimate 缺值：PBR、CBRS、VOD、GIB、KSPI、RBA、CNH、BAP、ALC。
- Revenue actual 缺值：BAP。
- Revenue estimate 缺值：PBR、CBRS、VOD、GIB、KSPI、RBA、CNH、BAP、ALC。

## 共識來源查核紀錄（45 筆）

| 指標 | Attempt 總數 | unavailable | not_pre_release | missing_required_fields | adopted |
|---|---:|---:|---:|---:|---:|
| EPS | 135 | 123 | 6 | 6 | 0 |
| Revenue | 135 | 123 | 6 | 6 | 0 |

- 每家公司每指標均留下 3 級來源查核紀錄；這代表「查核流程有紀錄」，不代表「共識值已取得」。
- LSEG I/B/E/S 與 FactSet Estimates 本輪均因執行環境沒有登入／API 權限而 unavailable。
- Investing.com 結果中，EPS 與 Revenue 各有 6 筆 not_pre_release、6 筆 missing_required_fields，其餘 33 筆 unavailable；沒有任何一筆符合完整採用條件。
- EPS 與 Revenue 的 selected consensus source object 各為 0/45。
- 舊來源物件仍各有 37/45 筆保存在 legacy 欄位；這些是歷史證據，不等於本輪來源階梯已採用，也不能自動視為符合 v2 的期間／口徑要求。
- 不得把 attempt 數量、legacy source 數量或舊數值覆蓋率當成有效共識取得率。

## 目前已存比較狀態（均為 legacy／未經 v2 引擎驗證）

| 狀態 | EPS | Revenue |
|---|---:|---:|
| Beat | 17 | 19 |
| Miss | 3 | 8 |
| Null | 25 | 18 |

45 筆 released records 全部沒有 `judgment_engine_version`。上述 Beat／Miss 只能視為歷史欄位值，不能宣稱已由統一 v2 規則驗證。

## Schema 漂移與期間欄位風險

- W45 與 W46 都標示 schema_version=1，但欄位集合不同；同一 schema_version 已出現 schema drift。
- W46 所有 45 筆 released records 的 EPS／Revenue estimate_period 均為空；actual period 45/45。
- `reporting_period` 只可作為 actual period 的來源；不可複製到 estimate_period。Estimate period 必須由共識來源明確提供。
- 2026-11-13 在 simulation branch 發現舊遷移函式 `migrate_legacy_record()` 曾把 `reporting_period` 複製到 actual 與 estimate 兩側，會錯誤製造「期間相符」證據。
- 已在隔離分支修正：只允許 reporting_period 填 actual_period；estimate_period 沒有明確來源證據時保持 null，判讀結果必須 pending。
- 修正程式 commit：`d0d8a1af6b137964364ed842823f4864e7aa619b`。
- 新增回歸測試 commit：`b95192767a2f11e35178fb99fa0127bb4ab934b8`。
- 後續測試案例修正 commit：`5142f4255bb8d95dc4be3e4b6b4ee8c353b69b95`，為合成 FERG 測試明確加入 `eps_estimate_period=Q3 2026`；沒有來源期間的案例仍必須維持 Pending。
- GitHub Actions run `43415581638`（2026-11-13 11:15 UTC）整體 `success`；`Run deterministic self-tests` 與 `Audit authoritative main earnings schema (read-only)` 均 `success`。這只證明隔離測試及唯讀稽核通過，不代表正式 main 已部署。
- 此次為一般 `push` smoke run，早報組裝、瀏覽器互動、視覺回歸等需 `workflow_dispatch`／`[build-tac-report]` 的步驟均 `skipped`；不得將本次 run 說成早報端到端驗收。

## 排程與寫入權責現況

- 目前啟用的唯一資料庫更新 automation：`TAC 行事曆資料庫更新`，ID `6af6d10c62448191819f04b976c64cf4`，每日 04:30 Asia/Taipei。
- 該 automation prompt 已補入公告前／公告後資料擷取欄位及 coverage matrix，並已修正其 W46 基準敘述；目前仍啟用，下一次排程為 2026-11-14 04:30。
- 另一個 Schema v2 automation：`TAC 行事曆資料庫｜每日 04:35 預更新`，ID `6ae6dff2200c81919ba2cee4db78f8a5`，目前 disabled；不得與 04:30 任務同時啟用成雙 writer。
- Main WR v5.15 的文字仍記載 04:35；目前啟用 automation 實際為 04:30，兩者存在設定／文件時間不一致。尚未修改 WR 或排程，不得默默把其中一方當成已同步。
- Main 正式 Schema v2、判讀引擎與 strict validator 尚未部署；正式 JSON 仍是 schema_version=1。不可提前把 main JSON 升成 v2。

## 結論與下一步

1. W46 已完成一次回填與來源查核紀錄，但 EPS／Revenue 有效共識採用數仍為 0；資料庫尚未完整。
2. 先完成 estimate period 不可推定的遷移修正測試，再重新產生 45 筆 in-memory migration preview。
3. 重新評估現有 legacy source 及其他可追溯來源能否提供公告前快照、期間、basis、幣別與單位；未能證明的值維持 pending，不得猜填。
4. 完成 Schema v2、engine、validator、W45/W46 migration 與 assembler integration 的隔離測試後，才可評估正式 main 部署。
5. 正式資料庫寫入權限仍由唯一 updater automation 持有；不得新增第二個週 JSON writer。


## 額外來源可行性初查（候選，未納入正式來源階梯）

目前 SIM-1.2 的核准來源順序仍是 LSEG I/B/E/S → FactSet Estimates → Investing.com。以下僅是來源可行性研究，不代表已授權採用、已取得帳號、已測試 API 或已寫入資料庫。

1. **OHLC Analyst Estimates API**
   - 文件描述支援 EPS／Revenue mean、low、high、analyst_count、issuer fiscal period、currency，以及 `effective_date`／`as_of` 歷史快照；最早公開快照日期為 2026-09-23，理論上涵蓋 W46 公告前日期。
   - API 需 `estimates.read` 權限；Free／Developer 不含 estimates，Pro 有 estimates 但僅 internal use；若要將資料顯示於公開 TAC 產品，文件列出的 Commercial plan 才含 commercial display／redistribution rights（定價頁列 USD 899/月）。
   - 文件未證明每筆 EPS consensus 的 GAAP／Adjusted、Basic／Diluted basis code，因此即使取得數值，也不能自動視為可 Beat／Miss 比較；必須先取得明確 basis 定義。
   - 文件： https://ohlc.io/docs/analyst-estimates ；方案與授權：https://ohlc.io/pricing

2. **Earnings Whispers Data API**
   - 文件提供每家公司最近 20 次財報歷史，含 reported EPS、consensus EPS、Revenue actual／estimate 及公告時段；EPS actual 與 consensus 明確為 option-expense-adjusted basis，Revenue 以 millions 表示。
   - 需建立 API key 並依訂閱層級取得資料；Investor 歷史僅限 watchlist，Trader 才可查詢全市場。文件明示資料供使用者自身使用，重新發布／再散布需另行授權。
   - 適合評估美股 EPS／Revenue 歷史回溯，但仍須逐筆核對 fiscal period、幣別、Revenue 定義、資料截點及 45 家公司的覆蓋；不可把 API 回傳時間當成公告前 data_as_of。
   - 文件：https://www.earningswhispers.com/data-api

3. **Ortex Consensus Estimates API（S&P Capital IQ sourced）**
   - 文件列有 point-in-time consensus date、fiscal period、currency、EPS／Revenue mean／median／high／low 及 analyst count；可使用 trial key `TEST`，但試用資料可能受日期與地區限制，完整存取需 API 方案。
   - 尚需驗證 EPS basis／Revenue definition、各 ticker 覆蓋、試用資料可用範圍及公開顯示授權；未完成前不得納入正式來源順序。
   - 文件：https://docs.ortex.com/reference/stock_estimates_consensus_retrieve

**來源研究裁決：** 三者都比單純公告後新聞摘要更值得做技術驗證，但目前沒有一個能在不補充授權與欄位定義的情況下直接成為 v2 比較來源。不得自行把它們插入 SIM-1.2 的固定來源順位；先取得使用者／資料供應商授權，再做 API 實測與 basis／period／currency／unit 驗收。


## Legacy consensus 逐筆時點稽核補充（2026-11-13 最新 main 回讀）

本次進一步檢查舊有 `legacy_consensus_source`／`legacy_revenue_consensus_source`，發現不能把「舊來源物件存在」直接視為公告前資料：

| 指標 | Legacy source object | estimate value | observed_at 晚於／等於公告時間 | observed_at 早於公告時間 |
|---|---:|---:|---:|---:|
| EPS | 37/45 | 36/45 | 4 筆 | 33 筆 |
| Revenue | 37/45 | 36/45 | 3 筆 | 34 筆 |

- EPS 公告後來源：CSCO、CBRS、AMAT、MRCY。
- Revenue 公告後來源：CSCO、CBRS、AMAT。
- 上述公告後來源的 `observed_at` 分別為 11/12 或 11/13，而事件已在更早的美東／台灣時間公布；不得拿來當公告前共識。即使頁面列有 forecast，也不能證明是公告前凍結快照。
- EPS 及 Revenue 各有 9 筆 estimate value 缺漏；缺值名單：PBR、CBRS、VOD、GIB、KSPI、RBA、CNH、BAP、ALC。
- EPS 37 筆 source notes 中只有 12 筆文字含可辨識季度／財年期間線索；Revenue 僅 2 筆。這些文字線索不是標準化的來源 period 欄位，也不自動等於已驗證。
- 因此 33／34 筆 observed_at 早於公告時間，只能證明來源物件記錄時間較早；不能單獨證明該時間就是共識值的資料截點，也不能證明估值 period、basis、currency、unit 全部吻合。
- 這批 legacy estimate 可留作研究線索與原始歷史紀錄，但 v2 判讀須逐項完成 source cutoff、fiscal period、basis、currency、unit 驗證；未完成前保持 Pending／Incomparable。不得因舊欄位已有數字就回填 estimate_period。

## 外部候選資料來源文件核對更新

以下內容依 2026-11-13 可取得的供應商 API 文件重新核對；候選來源尚未接入、尚未取得帳號／授權、尚未完成 45 ticker 覆蓋測試。

### OHLC Analyst Estimates API

- `effective_date` 可取得該日期或之前最近的共識快照，並回傳實際 `observed_on`；`as_of` 可限制只使用當時已知的修訂。來源最早快照日期為 2026-09-23；對已在供應商開始觀測前公布的期間，不會補發 frozen consensus。
- 可提供 EPS／Revenue mean、low、high、analyst_count、幣別及來源命名的 fiscal period；文件明示 `period_start`、`fiscal_year` 為 null，`fiscal_quarter` 才是供應商提供的季度欄位。
- 文件未明確給出 EPS 是 GAAP、Adjusted、Basic 或 Diluted basis。故 EPS 數值不得直接與公司任意 EPS actual 比較；Revenue 也需逐筆核對單位與 metric definition。
- Estimates 不包含 Free／Developer；Pro 可用但限 internal use；Commercial／Scale 才含 commercial display／redistribution rights。OHLC 公開頁目前列 Commercial USD 899/月，Scale USD 1,499/月；此成本未經使用者核准，不得註冊付費。
- 文件：https://ohlc.io/docs/analyst-estimates；https://ohlc.io/pricing；https://ohlc.io/terms

### Earnings Whispers Data API

- `GET /earnings` 可提供 upcoming earnings 的 EPS／Revenue estimates；若在公告前定期擷取並於事件公布時鎖定，可以建立本系統自己的 prospective point-in-time snapshot。
- `GET /history/{ticker}` 提供最近 20 次財報的 reported EPS、consensus EPS、Revenue actual／estimate；文件明確表示 EPS actual 與 consensus 都是 option-expense-adjusted basis，Revenue 以 millions 表示。
- 但歷史 endpoint 文件沒有為每筆歷史 consensus 提供精確的 pre-release `data_as_of`／凍結時間；不能僅憑歷史值回填 W46 公告前 PIT 快照。未來若採用，必須由排程在公告前留存 raw response、抓取時間、事件時間與 SHA-256。
- Investor／Trader 訂閱可用不同範圍；Trader 可查約 4,500 家有分析師覆蓋公司。API 文件明示資料供自身使用，重新發布／再散布需另行授權；TAC 公開頁不能直接沿用個人 API 權限。
- 文件：https://www.earningswhispers.com/data-api

### Ortex Consensus Estimates API

- 可按 `date` 取指定日期共識快照，欄位含 fiscal year／quarter、period end date、currency、EPS／Revenue mean／median／high／low、analyst count，資料來源說明為 S&P Capital IQ 並每日擷取；適合做 point-in-time 可行性測試。
- 文件將 EPS 稱為 normalized EPS，但未在目前欄位說明中明確定義 GAAP／Adjusted、Basic／Diluted 的正規化規則；未補得 basis 文件前，不得直接做 Beat／Miss。
- 公開文件提供 TEST 試用 key，但可能受日期與地區限制；尚未實際呼叫 API、驗證 W46 日期與 45 家覆蓋，也未確認 TAC 公開顯示授權。
- 文件：https://docs.ortex.com/reference/stock_estimates_consensus_retrieve

### 來源裁決

1. **最值得先做無付費／低成本技術驗證：Ortex TEST**，先測 2026-11-05 至 11-13 的 W46 公告前 snapshot 是否能回傳、ticker 覆蓋及 EPS basis metadata；TEST 若受限，不能將其視為可用。
2. **最適合建立未來公告前快照的候選：Earnings Whispers upcoming endpoint**，但要先確認訂閱範圍、API 權限及 TAC 公開再發布授權；歷史 endpoint 不足以回填 W46 PIT。
3. **OHLC 可作商業授權候選**，但 Commercial 起價 USD 899/月，且 EPS basis 未定義；沒有使用者授權前不付費、不接入正式排程。
4. 以上皆為候選，不改動 SIM-1.2 既有來源優先順序。正式納入前需完成授權、API 實測、45 ticker 覆蓋、欄位 schema、point-in-time、basis／period／currency／unit 及重複性驗收。


## Schema v2 隔離遷移預覽與 CI 補充（2026-11-13）

- 最新 main W46（45 筆 released）已由 workflow 的唯讀稽核步驟重新產生 `earnings-migration-preview.csv` 與 `earnings-schema-audit.json`；輸出為 `IN_MEMORY_READ_ONLY`，沒有寫入 main JSON。
- 遷移預覽 45/45 筆：EPS `pending=41`、`incomparable=4`、方向性 Beat/Miss/Inline `0`；Revenue `pending=44`、`incomparable=1`、方向性 `0`。
- EPS 不可比較：TDG、WIX、MRCY（basis code mismatch），ONON（currency mismatch）。Revenue 不可比較：ONON（currency mismatch）。其餘未達完整證據條件者維持 Pending。
- 預覽原因分布：EPS missing consensus period 12、missing/unrecognized basis 16、basis mismatch 3、missing/invalid actual or consensus 13、currency mismatch 1；Revenue missing/unrecognized basis 33、missing consensus period 2、missing/invalid actual or consensus 9、currency mismatch 1。
- 再讀 main W46 的兩組 legacy source object：EPS 37/37、Revenue 37/37 均只有 `name/url/publisher/observed_at/notes/secondary_refs` 等欄位；`data_as_of`、`published_at`、`analyst_count`、標準化 `fiscal_period/period` 均為 0/37。這直接證明目前舊來源物件無法提供公告前快照截點與估值期間欄位；`observed_at` 不能替代 `data_as_of`。
- Workflow run `43415581638` 的 artifact 內雖有 `TAC_投資早報_2026-11-13_審核版.html`，但 `runner-metadata.txt` 記載 `report_date=self-test-only`，且本次 report build 步驟為 skipped；該 HTML 是分支既有檔案，不可宣稱由本次 run 新製作或通過 QA。CSV／audit JSON 則由本次唯讀稽核步驟產生。
- 正式 main 仍為 schema_version=1；本次沒有改動 main。

## ORTEX TEST consensus API 實際連線驗證（2026-11-13）

- Simulation workflow run：`43416557107`，最終 `success`；專用步驟 `Probe ORTEX TEST consensus API (read-only, simulation only)` 成功。
- Probe 程式：`simulation-lab/runner/probe_ortex_test.py`；執行時僅使用官方文件公開的 `Ortex-Api-Key: TEST`，不使用付費憑證、不寫入 main、不修改 W46 JSON。
- 實際 HTTP 回應：NASDAQ/AAPL、NASDAQ/MSFT、NYSE/AMC 均為 HTTP 200，各回傳 10 筆資料列；TEST key note 明確出現在三份回應中，credits used=0。
- 三組 raw response SHA-256：AAPL `b02807951837eeb05ec6011dd6395391b154937dc2f51cbf20fca2b91484e399`；MSFT `2eca693a092731a458ac60587b7d1fbf34eba584bce292a9a3979ae7dc8bf130`；AMC `232f390acd601f15100769b0856415713a7ea7d6e2966517a531e950facc234b`。
- Probe JSON SHA-256：`4d226633647fc072bf90364fe13b3b8cf2ee80e4d8718b398c2a64aa20c2c01c`；原始 JSON 已由 run artifact `tac-simulation-43416557107-1` 暫存。後續 workflow 已加上將 probe JSON 歸檔至 simulation `runs/` 的步驟；該歸檔步驟須由後續 run 實際驗證。

### 實際欄位能力

API 實際回傳欄位包含 `date`、`estimateAsOf`、`periodType`、`periodEndDate`、`fiscalYear`、`fiscalQuarter`、`currency`、`epsConsensusMean/Median/High/Low`、`epsNumEstimates`、`revenueConsensusMean/Median/High/Low`、`revenueNumEstimates`。這證明 TEST endpoint 的實際 JSON schema 含 EPS／Revenue 數值、財報期間、幣別及 analyst count。

### 關鍵限制與 Schema 欄位映射

- 雖請求 `from_date=2026-11-05` 至 `to_date=2026-11-13`，TEST key 明確限制日期範圍；response 的 `request` 未回顯這兩個日期，`resolved` 實際為 `2026-05-17` 至 `2026-10-14`，第一筆資料日期為 `2026-05-18`。故本次**不能驗證 W46 歷史快照、不能回填 W46，也不能證明 W46 ticker 覆蓋率**。
- API 文件定義 `date` 為 consensus as-of date，故可映射至候選 `data_as_of`；`estimateAsOf` 是 vendor last recalculated date，必須獨立保存，不可當成 `published_at`。本次取得時間另記為 `observed_at`；`event_date` 仍取財報事件正式公布時間。API 未提供可直接映射的 `published_at`。
- API 文件只稱 EPS 為 normalized EPS，未說明 GAAP／Adjusted、Basic／Diluted 的精確規則；basis code 仍無法由本次資料證明。EPS 不得直接進入 Beat/Miss。
- Revenue 文件定義為 row currency 的 absolute value；實際回應未提供獨立 revenue unit 欄位。若未另有來源定義，必須保存原始 absolute amount 與 currency，不可自行縮放或假設為百萬／十億。
- 技術連線成功不等於正式存取方案或公開展示／再散布授權成立；目前未購買方案、未取得正式 key、未核准採用。

### 裁決

ORTEX TEST 的技術連線與基本欄位可用性已實測成功；但 TEST 的日期／區域限制、W46 PIT 覆蓋、EPS basis 及公開再散布權利仍未解決。它仍只是 SIM-1.2 之外的候選研究來源，不得插入 LSEG I/B/E/S → FactSet Estimates → Investing.com 的正式來源階梯，不得作為 W46 歷史共識補值來源。下一步應先取得可查詢 W46 日期的正式授權試用／正式方案（未經使用者同意不得付費），再逐筆驗證 45 家 ticker 的指定日期、期間、basis、currency、unit 及授權條款。


### Raw probe evidence durable archive confirmation

- Follow-up simulation workflow run `43416810131` completed `success`; the ORTEX probe, deterministic self-tests, and main read-only earnings schema audit all succeeded. All report assembly / browser / visual QA steps were skipped because this was a push smoke run.
- Raw probe JSON archived in the simulation branch at `simulation-lab/runs/ortex-test-probe-43416810131.json`; blob SHA `b082a2ca778521fcdb2b383935d8f4f4c599fd03`; 49,835 bytes; read-back confirmed the raw response bodies are included.
- Archive commit advanced simulation HEAD to `d47ee45a4a73f269305836a004e7206b45150929`.
- After the simulation changes, main HEAD remained `68223e3aa384ae4d75311a243eb029da3c55b32c` and W46 JSON blob remained `ec246b8a765c64b798e348ce8df2760ea89cc5e1`; no production data was modified.


### ORTEX 公開展示與再散布授權核查（官方條款）

- ORTEX Standard Consumer Terms（last updated 2026-07-06）將非專業用戶服務限於個人／直系家庭投資用途；條款 4.4 禁止向第三方分發服務或其摘錄／衍生內容，條款 5.4(e) 禁止商業利用或向第三方提供服務，條款 6.4(b) 禁止將 API／Data Services 資料再散布、轉售、再授權或提供第三方。
- 因 TAC 是公開展示的產品，不能假設一般個人 API 訂閱或 TEST key 可授權 TAC 網站展示。須由 ORTEX 確認 Professional／Institutional data licence 或平台／OEM redistribution 條款，並以書面確認可展示 EPS／Revenue estimates、歷史 PIT 快照、保存期限及公開頁面展示範圍。
- ORTEX 官方機構頁面將資料授權按 dataset／coverage／delivery 定價，並列出 redistribution／OEM 與 trials；因此下一步若要商業評估，應走機構資料授權／平台整合洽詢，而非使用個人訂閱或 TEST key 上線。
- 官方依據：
  - https://public.ortex.com/terms-and-conditions
  - https://public.ortex.com/
  - https://docs.ortex.com/reference/stock_estimates_consensus_retrieve
- 裁決：目前授權狀態為 **未確認／未獲准**；禁止將 TEST 回應或任何個人 API 訂閱資料接入 TAC 公開頁、長期資料庫或向讀者再散布。技術可用性與授權可用性必須分開驗收。
