# TAC Chart 3｜五項資料同步發布規範

版本：1.0  
建立日期：2026-11-18  
適用範圍：Chart 3「市場恐慌 × 金融壓力」資料擷取、整合、快照發布與圖表顯示。

## 1. 核心原則

五項序列可以依各自來源頻率獨立擷取、驗證與暫存，但不得各自直接更新正式圖表。正式圖表只讀取一份通過同步門檻的整批快照（atomic release）。

同步的意思是「同一批次發布、採用共同資料截止日」，不是把不同來源的觀測日期改寫成相同日期，也不是要求每個序列每天都有新數字。

五項序列：
1. VIXCLS — CBOE VIX（FRED/ALFRED）
2. NFCI — Chicago Fed National Financial Conditions Index（FRED/ALFRED）
3. NFCICREDIT — Chicago Fed NFCI Credit Subindex（FRED/ALFRED）
4. STLFSI4 — St. Louis Fed Financial Stress Index（FRED/ALFRED）
5. S&P 500 — 僅接受已核實且符合本規格來源 Gate 的真實每日現金指數收盤價。可沿用 TAC 早報 D4 已核實資料，但該筆來源必須符合 Investing.com 來源與使用權限要求；Yahoo 或其他備援來源不得未經使用者明確核准就匯入本同步發布序列，也不得改標成 Investing.com。不得以週資料、壓縮曲線或插值替代。

## 2. 每日檢查與分層流程

每日排程執行下列工作：

1. 讀取每個來源的 checkpoint、manifest、上次成功時間與 SHA-256。
2. 分別檢查來源是否有新觀測／新 vintage；依各來源公布頻率擷取，不假設五項同日更新。
3. 將新資料寫入 staging／候選區，先完成格式、日期、數值、重複鍵、來源回應與雜湊驗證。
4. ALFRED 四序列沿用 append-only vintage/event 記錄與 current snapshot reconciliation；只取新 vintage 並保留既定 overlap。S&P 500 可沿用 TAC 早報 D4 已核實 OHLC，但只有來源符合 Investing.com 來源與使用權限 Gate 的紀錄才可進入本發布流程；不符合者保留於早報原始紀錄，不得匯入或改標。若 D4 無符合條件的資料，使用已驗證的 Investing.com CSV 匯入流程，不得另用未核准供應商補值。
5. 所有五項檢查完成後，執行共同觀測日期計算與發布 Gate。
6. 通過 Gate 才建立單一整批快照、更新發布 manifest，並讓圖表讀取新版本；未通過則正式版本完全不變。

## 3. 共同觀測日期（common_observation_date）

共同觀測日期必須是五個序列都具有「來源實際觀測值」的同一個日期：

- 對每個序列取有效、非缺值的 observation date 集合。
- 計算五個集合的交集。
- 共同基準日取交集中不晚於所有來源已驗證資料範圍的最新日期。
- 不得用前值填補（forward-fill）、插值、重採樣、週轉日或最近日期配對，製造不存在的共同觀測值。
- 若最新週頻觀測日不是 S&P 500 交易日（例如市場假日），不得把前一交易日收盤價偽裝成該日收盤價；應等待來源出現真正共同日期，或維持舊版快照。
- 若交集沒有比目前正式快照更新的日期，視為「尚無可發布的新共同基準日」，不是錯誤，也不得為了更新而降低標準。

注意：五項資料的 latest_observation_date 可以不同。共同基準日是五者皆有實際觀測值的最新交集日期；它不是五個 latest date 的最小值，也不是把不同日期資料標成同一天。

## 4. 原始日期與版本欄位

每一筆原始觀測都必須保留：
- series_id
- observation_date（來源原始觀測日期）
- value（原始數值；來源缺值維持缺值）
- source / source_url / retrieval_method
- retrieved_at（UTC）
- vintage_date / realtime_start / realtime_end（來源有提供時）
- source_release_date（來源有提供時；未提供時明確標示未提供，不得推算成觀測日期）
- source_missing / QA flags
- source artifact SHA-256

每份整批發布快照必須另記：
- snapshot_id
- published_at（UTC）
- common_observation_date
- 每個序列各自的 latest_observation_date
- 每個序列採用的 vintage/as-of 資訊（適用時）
- 每個來源的 retrieval time、URL/method、SHA-256
- 五項資料各自通過的 QA 結果
- previous_snapshot_id
- release_status

不得用 published_at、retrieved_at 或 vintage_date 取代 observation_date。

## 5. 發布 Gate（五項全數通過）

以下條件必須全部成立，才可發布新快照：

1. 五項來源本輪均已完成檢查；來源暫時失敗、逾時或回應不完整，該輪不得發布。
2. 五項資料均有有效數值，且存在比上一版更新的共同觀測日期。
3. common_observation_date 當日五項序列都有來源原生觀測值。
4. 每筆資料的日期、數值型別、重複鍵、排序、缺值語意及來源範圍驗證通過。
5. ALFRED point-in-time 重建符合 vintage 規則：不得使用 as-of 日期之後的 vintage 或 observation；保留來源缺值，不 forward-fill。
6. S&P 500 必須是指定來源的真實日收盤資料，日期完整且可追溯；不可用近似、週頻或壓縮資料。
7. 五項來源資料與整批輸出均完成 SHA-256 驗證。
8. 候選快照建置及圖表資料 schema 驗證成功。

任何一項不通過：不更新正式快照、不覆蓋 last-good、不發布部分序列。保留 staging 供診斷，記錄阻塞原因並在下一輪重試。

## 6. 圖表資料呈現

- 圖表的正式資料截止日標示為 common_observation_date。
- 同時揭露五個序列各自的 latest_observation_date，避免把共同截止日誤解為所有來源的實際最新日期。
- 正式比較視圖的五個序列均截至 common_observation_date；各序列只畫出自己原生存在的觀測點。
- 歷史起點不同時保留真實缺口；不可補值。Chart 3 預設共同展示起點仍依既有規格為 1993-12-31，並保留更早可用歷史供使用者向左探索。
- 顯示資料更新時間與資料截止日，兩者不可混為一談。
- 若本輪未達 Gate，畫面仍顯示上一版完整快照，並保留上一版的資料截止日；不得只更新部分線條。

## 7. 與現有管線的整合界線

現有 GitHub Actions 工作流 `.github/workflows/tac-chart3-incremental.yml` 已負責四項 FRED/ALFRED 序列的增量擷取、驗證、視覺化資料建置及 point-in-time snapshot QA。此工作流目前不是五項資料同步發布 Gate；現況不得誤稱已經完成五項同步發布。

整合時應採以下架構：
- 保留四項 ALFRED 增量歷史與既有 SHA-256／PIT 規則。
- 將四項新資料及 S&P 500 新日線先寫入候選區。
- 新增單一同步發布器，計算五序列共同觀測日期並執行第 5 節 Gate。
- 只有同步發布器成功後，才原子式更新正式 chart-ready snapshot 與 release manifest。
- 視覺 QA 必須針對「新發布的同一 snapshot_id」執行；資料 Gate 失敗時不得觸發新版本視覺發布。
- 任一模組失敗都保留 last-good；整體流程須可重跑、冪等，不可因重跑產生重複事件或 timestamp-only commit。

## 8. 目前已知缺口（2026-11-18）

- 四項 FRED/ALFRED 序列已有增量更新流程。
- S&P 500 早報 D4 → append-only OHLC JSONL → compact close history 的研究版工具已建立；尚未接入每日早報產製的自動輸出，因此目前仍需人工提供／觸發報告資料交接。
- 現有工作流尚未實作五項共同觀測日期計算與原子式發布 Gate。
- 因此目前只能說「四項序列自動更新已運作」，不能說「五項同步更新已完成」。

## 9. 驗收測試

至少涵蓋：
1. 五項都有同一個新觀測日期：產生一份新快照。
2. 任一週頻序列尚未更新：不發布，正式快照 hash 不變。
3. 五項最新日期不同但存在較新的共同日期：以共同日期發布，並保留各自 latest date。
4. 五項沒有新的共同日期：不發布、不降低標準。
5. 某週共同日期遇到 S&P 500 市場假日：不以最近交易日冒充當日值。
6. 任一來源失敗、缺值、重複日期、錯誤 hash 或 schema 錯誤：不發布。
7. 重跑相同來源資料：結果冪等，不產生無意義 commit。
8. 快照發布後，圖表五條線均讀取相同 snapshot_id，且顯示共同截止日與各自實際最新日期。
9. 回溯歷史時保留各來源原始日期、ALFRED vintage 與缺口，不得 forward-fill 或插值。
10. 桌機、手機視覺 QA 對新 snapshot 通過後，才標記該版本可供正式圖表使用。


## 10. Implementation progress (research branch, 2026-11-18)

Research branch: `research/chart3-synchronized-release-20261118`.

Implemented:
- `.github/scripts/build_tac_chart3_synchronized_release.py`: validates four FRED/ALFRED series plus S&P 500 compact data; decodes and validates compact daily observations; requires an HTTPS Investing.com source URL, ISO-8601 retrieval timestamp, retrieval method and source hash matching the compact dataset provenance; calculates the exact five-way intersection of non-missing native observation dates; selects the latest common date; builds a single five-series snapshot; writes atomically; refuses to replace an existing release when the common date is not newer.
- Provenance validation does not require an authorization-reference field. Personal research use is not treated as a missing technical credential; source identity, retrieval method, timestamp and content hash remain mandatory.
- `.github/scripts/prepare_sp500_research_import.py` provides an explicit CSV import path for a user-supplied Investing.com historical export. It validates the HTTPS source URL, timestamp, required Date/Price columns, positive closes and unique dates; sorts the observations, builds the compact payload and writes matching SHA-256 provenance. This is a manual import utility, not an unattended downloader.
- `.github/scripts/test_tac_chart3_synchronized_release.py`: tests successful common-date publication, no-common-date rejection, non-Investing.com source rejection and same/older-date no-op behavior.
- `.github/workflows/chart3-synchronized-release-qa.yml`: isolated research-branch test workflow.

QA run: [44298889579](https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/44298889579) — completed successfully.

Not yet implemented:
- Investing.com S&P 500 unattended daily incremental downloader; current CSV importer requires a user-supplied export.
- End-to-end integration with the existing four-series updater, chart-ready builder, release manifest and browser QA.
- Production scheduling and any Main deployment.

Safety: this work remains isolated on the research branch. The existing Main data workflow, chart page, homepage and schedules have not been changed. The current S&P 500 compact dataset identifies a non-Investing.com historical source, so the new release builder intentionally rejects it; no new five-series release has been published.


## 11. Personal research data handling

The project is being developed for the user's personal research workflow. Do not repeatedly block engineering progress by demanding an authorization-reference field as a technical prerequisite.

The data pipeline must still:
- Preserve the actual source URL, retrieval timestamp, retrieval method, raw artifact/content SHA-256 and observation dates.
- Prefer the requested Investing.com historical-data source for S&P 500 and never silently relabel another provider's data as Investing.com.
- Avoid reverse-engineering private endpoints, bypassing access controls, or misrepresenting a third-party feed as an official Investing.com API.
- Support a transparent, validated import path when a reliable direct source interface is unavailable. A manually supplied export must be labeled as such and must not be described as unattended automatic retrieval.
- Keep source-specific technical and contractual limitations documented, without adding a fabricated authorization credential to the data schema.
- Never substitute FJA, Yahoo Finance, Stooq or another provider for the required Investing.com source without the user's explicit approval.


## 12. Fail-closed orchestration implementation (research branch, 2026-11-18)

Added `.github/scripts/run_tac_chart3_synchronized_release.py` as an isolated orchestration entry point. It reads the existing four-series chart-ready dataset and the separately imported Investing.com S&P 500 compact/provenance pair. Missing files produce `BLOCKED_MISSING_INPUT`; invalid source, schema, hash or common-date checks produce `BLOCKED_VALIDATION_FAILURE`. Both paths leave the active release manifest and last-good snapshot unchanged.

Successful candidates are written as immutable files under `data/tac-chart3/synchronized/snapshots/`. The single `active_manifest.json` pointer is replaced atomically only after the snapshot file is complete. The runner verifies the previous snapshot SHA-256 before advancing it and does nothing when no newer common date exists. A status report records the result. The runner is not yet called by the Main workflow and no schedule has been added.

Added runner tests for missing S&P 500 input, successful snapshot/manifest creation, failed common-date validation preserving the previous manifest, and same-date no-op. Research QA workflow now includes these tests.


## 13. Investing.com public interface findings (2026-11-18)

- Investing.com Support states that Investing.com does not offer public API access because of its data-provider agreements: https://www.investing-support.com/hc/en-us/articles/115005473825-Do-You-Offer-API-Access-at-Investing-com
- The public S&P 500 historical-data page describes daily historical OHLC/change data and provides a download option: https://www.investing.com/indices/us-spx-500-historical-data
- Investing.com Support describes long-term daily/weekly/monthly chart history (up to 30 years): https://www.investing-support.com/hc/en-us/articles/115003946765-Exploring-Historical-Data-on-Investing-com-Charts

Engineering consequence: do not implement or depend on an undocumented/private Investing.com API endpoint. The next compliant automation experiment is to evaluate the public website's documented historical-data download control through ordinary browser UI interaction, without bypassing access controls. Until that is demonstrated in the research workflow with a real downloaded CSV, the manual CSV importer remains the only validated Investing.com ingestion path. Do not claim unattended daily S&P 500 ingestion is complete.


## 14. Download and data-rights gate (2026-11-18)

Further official-source review:

- The public S&P 500 historical-data page exposes a download option in its page description, but a page-rendered option is not proof that an unauthenticated or free account can download a full CSV: https://www.investing.com/indices/us-spx-500-historical-data
- Investing.com's own chart-upgrade announcement says one-click chart price-data CSV download is available with InvestingPro: https://www.investing.com/blog/meet-the-new-investingcom-chart-10-upgrades-built-for-how-traders-really-trade-345
- The historical-data page's rights notice states that the data may not be stored, reproduced, displayed, modified, transmitted or distributed without prior explicit written permission from Fusion Media and/or the data provider. The intended scope and any permitted personal/research use must therefore be checked against the applicable terms/permission before persistent ingestion or republication.

Accordingly, the research branch must not assume that the visible download label means free, anonymous, unattended access. No headless scraping, private endpoint reverse-engineering, cookie/session circumvention or automated export is to be added. The manual CSV importer remains a technical adapter only; it does not grant data-use rights. Before using it with real production data, confirm that the downloaded file was obtained through an authorized account/feature and that the intended retention and display are permitted. Until then, S&P 500 ingestion remains a blocked dependency and no five-series release is published.

## 15. Additional runner integrity gates (2026-11-18)

The fail-closed runner now validates that the active manifest references exactly `snapshots/{snapshot_id}.json`, rejects absolute or parent-traversal paths, verifies the referenced snapshot SHA-256 and embedded snapshot identity/date, and rejects an existing immutable snapshot file if its content differs from the candidate. Tests cover a tampered last-good snapshot and an unsafe manifest path. The active manifest is not advanced on either failure.


## 16. TAC 早報 D4 與 S&P 500 來源 Gate（2026-11-18 修正）

TAC 早報 D4 是既有的每日 OHLC 查核位置，可避免重複查價；但「D4 已核實」不代表該來源自動符合 Chart 3 的資料留存與發布條件。Chart 3 五序列同步發布目前要求 S&P 500 採 Investing.com 歷史資料，並遵守其頁面所載資料使用限制。

已核實的交接缺口：
- 早報 D4 的 OHLC 目前主要保存在當日報告 fixture／Session State／來源折疊區，尚未形成可直接增量讀取的長期逐日 close 序列。
- simulation fixture 2026-11-17 記錄的 2026-11-16 S&P 500 OHLC 來源是 Yahoo Finance ^SPX 現金指數。該筆可以保留作為早報 D4 的來源證據，但依本研究分支現行來源 Gate，不可直接匯入 Chart 3 Investing.com 同步發布資料集，也不可重新標記為 Investing.com。
- 2026-11-18 fixture 沒有 S&P 500 OHLC override；不得把前一日值冒充當日值。
- D4 既有 fixture 未提供精確行情擷取時間；report cutoff 不可代替 retrieved_at。

資料進入 Chart 3 的條件：
- 若 D4 當日來源本身是 Investing.com，且取得方式、留存與預計顯示用途符合適用權限，才可沿用該筆資料；須逐筆保留 source_name、source_url、observation_date、retrieved_at、retrieval_method、OHLC 及 record SHA-256。
- 若 D4 使用 Yahoo 或其他未經明確核准的備援來源，該筆不得進入本同步發布序列。不得混入歷史後再以單一 Investing.com 標籤包裝。
- 若 D4 沒有符合來源 Gate 的資料，現階段唯一已驗證的技術匯入方式是使用者提供的 Investing.com CSV；匯入工具不會自行下載資料，也不代表資料使用權限已取得。
- 沒有精確、帶時區的 retrieved_at 時不得自行推算；不得以 report_cutoff_taipei 代替。

D4 JSONL adapter 與 converter 仍保留在研究分支作為獨立實驗工具，但不得作為預設五序列發布輸入，除非後續來源 Gate 明確允許該筆資料。Main、早報正式流程及正式 Chart 3 均未因本研究變更。

## 17. Investing.com S&P 500 import and synchronized runner defaults (research branch, 2026-11-18)

The only currently validated S&P 500 ingestion path for the five-series research release is an explicit, user-supplied Investing.com historical CSV export. This is a manual import, not an unattended downloader, and it does not itself establish permission to retain or republish the data.

- `.github/scripts/prepare_sp500_research_import.py` validates the Investing.com HTTPS source URL, required Date/Price columns, positive closes, unique dates and timezone-aware retrieval timestamp. It records the raw CSV SHA-256 and writes:
  - `data/tac-chart3/sp500_investing_daily.compact.json`
  - `data/tac-chart3/sp500_investing_daily.provenance.json`
- `.github/scripts/run_tac_chart3_synchronized_release.py` now defaults to those exact two paths, so the importer output and release runner input are aligned. Both paths remain overridable through CLI arguments.
- Unit tests assert that the importer output defaults exactly match the runner input defaults.
- The release builder independently validates the Investing.com host, retrieval metadata, source hash and exact five-way native observation-date intersection before it can create a candidate snapshot.
- The D4 JSONL importer/converter remain research-only utilities. A D4 row sourced from Yahoo or another unapproved provider is not eligible for this Investing.com-only synchronized release and must not be silently substituted or relabeled.

Operational boundary:
- The CSV must be obtained through an authorized account/feature and its intended retention/display use must be permitted under applicable terms. The importer is a technical adapter only.
- No private endpoint, headless scraping, session circumvention or unattended download is implemented.
- No real S&P 500 CSV has yet been imported into the research dataset; no five-series synchronized snapshot has been published.
- Main, the official Chart 3 page, the homepage and existing schedules remain unchanged.



## 18. TAC D4 daily incremental handoff — Yahoo Finance research experiment (2026-11-18)

The user explicitly approved trying Yahoo Finance for the S&P 500 research data path. This approval applies to this isolated Chart 3 research experiment; it does not authorize changes to Main, the official Chart 3 page, the TAC report production workflow, or any schedule.

Verified existing TAC D4 collector contract in the simulation branch:
- `simulation-lab/runner/collect_key_levels_ohlc.py` already retrieves the five US cash-index OHLC bars, including Yahoo Finance `^SPX` for S&P 500 when no same-session source override is supplied.
- Its output contains `report_date`, `trading_date`, `captured_at_taipei`, and `key_levels.items[]`; the S&P 500 item identifies `key=sp500`, `symbol=^SPX`, `quote_type=cash_index`, source name, source URL and an OHLC string containing the close.
- The capture timestamp is the D4 collector batch timestamp. It is not represented as a per-request timestamp; this limitation must remain explicit in the imported provenance.
- Existing report fixture `report-data-2026-11-17.json` also demonstrates a Yahoo Finance `^SPX` cash-index observation for 2026-11-16 (close 7416.59), while the next day's fixture does not contain a new Yahoo S&P 500 OHLC override. Never carry that value forward to a later trading date.

New research-branch adapter:
- `.github/scripts/import_sp500_from_d4_capture.py` reads the existing D4 collector output; it does not fetch or download market data.
- It validates the capture timestamp, report/trading dates, exact S&P 500 item, `^SPX`/`^GSPC` symbol, explicit `cash_index` identity, HTTPS source and source-name/host consistency.
- It extracts the true close from the structured close field or D4's rendered `ohlc` string, then appends one close-only observation to `data/tac-chart3/sp500_tac_d4_close.jsonl`.
- Each record stores its own source name/URL, source symbol, observation date, D4 batch capture timestamp, retrieval method, timestamp semantics and SHA-256. Same-date identical observations are idempotent; conflicting same-date values/sources fail closed.
- The existing `.github/scripts/build_sp500_from_tac_report_history.py` converter validates close-only records as well as OHLC records and can produce compact close history plus per-observation provenance from the append-only JSONL.
- Added `.github/scripts/test_import_sp500_from_d4_capture.py` and included it in the isolated research QA workflow.

Important remaining integration work:
1. The D4 collector output must be made available as a file to the Chart 3 research job. No direct scheduled handoff has yet been connected.
2. The new incremental compact data must be merged with the existing 1927–2026 S&P 500 history without overwriting or altering historical observations. Historical source metadata must be retained by date/range; do not fabricate per-row original-source retrieval timestamps.
3. The five-series builder must accept the explicitly user-approved Yahoo D4 source in per-observation provenance for this research experiment while retaining the actual Yahoo source identity. Never relabel it as Investing.com.
4. End-to-end tests must prove a new D4 capture appends exactly one date, a repeated run is a no-op, a conflict is blocked, and the synchronized release uses the latest exact common date.
5. This adapter and experiment do not establish third-party licensing or public redistribution rights. Keep the dataset isolated and do not publish to the official chart until the intended use is verified and the user approves deployment.

Current status: adapter and unit tests are committed to the research branch; automated handoff, historical merge, full five-series release and deployment remain incomplete.


## 19. Daily TAC report source handoff clarification (2026-11-18)

A read-only review of simulation report fixtures for 2026-11-11 through 2026-11-18 found that the S&P 500 close is already present in the daily report data, but its source varies by report date:
- 2026-11-10 close: Associated Press
- 2026-11-11 close: Associated Press
- 2026-11-12 close: Associated Press
- 2026-11-13 close: MarketWatch/FactSet OHLC override, with AP cash-close reference
- 2026-11-16 close: Yahoo Finance `^SPX` cash-index OHLC
- 2026-11-17 close: Associated Press

The importer must preserve each day's actual source name and URL. It must not require Yahoo for every date, nor rewrite AP/MarketWatch/Yahoo as a single provider. The user's explicit request to test Yahoo authorizes Yahoo as a research source; the daily report's already verified per-day source record remains the source of truth for each observation.

The adapter `.github/scripts/import_sp500_from_d4_capture.py` now supports two machine-readable inputs:
1. D4 collector output (`captured_at_taipei` + `key_levels.items[]`).
2. TAC report-data JSON (`key_levels_overrides.sp500` preferred; otherwise `global_markets["標普500指數"]`).

For report-data input, it requires an explicit timezone-aware `retrieved_at` in the source record or an explicit `market_data_captured_at` on the report. It will not substitute report date, report cutoff, or trading date for the actual retrieval timestamp. It validates source URL, date match and cash-index identity, then appends only the close value with per-date source provenance. The converter supports this close-only append-only record format.

Operational correction:
- `.github/workflows/tac-key-levels-live.yml` exists only on the simulation branch. Its `schedule` trigger does not run from a non-default branch: GitHub documents that scheduled workflows only run on the default branch. The repository's simulation-branch run history contains no runs named `TAC live key-level OHLC capture (simulation only)`; therefore this workflow must not be described as a live daily scheduled feed. It can only be manually dispatched unless separately enabled on the default branch.
- The official Main TAC report process remains ChatGPT-led and its report data currently lacks a dedicated exact retrieval timestamp field for S&P 500 source records. The existing fixtures demonstrate source URL/date/close but do not supply `retrieved_at` or `market_data_captured_at`.
- Consequently, the new adapter and tests establish the research-side ingestion contract, not an automated daily handoff. The remaining production integration is to record the exact timestamp at the moment the daily report source is checked and pass that structured report record to the Chart 3 append-only importer. Do not change Main or the official report process without explicit approval.
