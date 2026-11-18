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
5. S&P 500 — TAC 早報 D4 已核實的真實每日現金指數收盤價；優先沿用當日核實來源，逐筆保留實際 source_name/source_url，不得把 Yahoo 或其他備援來源改標成 Investing.com，也不得以週資料、壓縮曲線或插值替代。

## 2. 每日檢查與分層流程

每日排程執行下列工作：

1. 讀取每個來源的 checkpoint、manifest、上次成功時間與 SHA-256。
2. 分別檢查來源是否有新觀測／新 vintage；依各來源公布頻率擷取，不假設五項同日更新。
3. 將新資料寫入 staging／候選區，先完成格式、日期、數值、重複鍵、來源回應與雜湊驗證。
4. ALFRED 四序列沿用 append-only vintage/event 記錄與 current snapshot reconciliation；只取新 vintage 並保留既定 overlap。S&P 500 優先沿用 TAC 早報 D4 已核實的 OHLC，經報告資料交接器累積逐日紀錄，再轉成 Chart 3 close 歷史；不得另開重複行情擷取，也不得把不同日的實際來源混成單一來源標籤。
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


## 16. TAC 早報 D4 的既有 S&P 500 OHLC 交接（2026-11-18 修正）

核對正式 WR v5.15 的 D4 後，確認早報每日已由 ChatGPT 直接查核同一基準交易日、同一標的的 OHLC，並記錄來源與日期；這是現有資料擷取責任，不應另建一套重複行情查詢流程。

已核實的交接缺口：
- 早報 D4 的 OHLC 目前主要保存在當日報告 fixture／Session State／來源折疊區，未形成 Chart 3 可直接增量讀取的長期逐日 close 序列。
- 同一報告日期的來源可能依當日來源核實結果而異。例如 simulation fixture 2026-11-17 記錄 S&P 500 2026-11-16 OHLC（O 7,513.98、H 7,515.60、L 7,400.15、C 7,416.59），來源標示 Yahoo Finance ^SPX 現金指數，不能重新標成 Investing.com。
- 2026-11-18 fixture 目前沒有 S&P 500 OHLC override；不得把前一日值冒充當日值。

因此，後續交接以「TAC 早報 D4 已核實的現金指數 OHLC」為上游資料來源，不另開一套行情擷取。每筆必須保留原始 source_name、source_url、observation_date、retrieved_at、retrieval_method、OHLC 及 record SHA-256；來源可能逐日不同，必須逐筆保存來源，不得用單一全歷史來源標籤覆蓋不同供應商。

新增研究工具：
- `.github/scripts/import_sp500_from_tac_report.py`：從既有報告 fixture 的 `key_levels_overrides.sp500` 擷取同日 OHLC，確認報告日期／交易日期一致、OHLC 合理、來源 URL 為 HTTPS、來源註記明確為現金指數且非 CFD，並要求明確傳入帶時區的實際擷取時間。它不下載行情，也不推測擷取時間。
- 輸出採 append-only JSONL；相同日期相同內容重跑為 no-op，同日不同 close／來源資料則 fail closed，不覆蓋歷史紀錄。
- 新增五項測試，覆蓋來源與價格擷取、CFD 拒絕、日期錯配、相同資料冪等及同日衝突拒絕。

目前限制：
- 此 adapter 只是 D4 → Chart 3 staging 的第一段交接，尚未把 JSONL 轉成五序列發布器所需的完整 S&P 500 compact history，也尚未改寫同步發布器的 provenance schema 以逐筆保留不同來源。
- 因此不可宣稱 S&P 500 日線已完成自動累積，也不可宣稱五項同步發布已完成。
- 研究分支 QA workflow 已加入 adapter 測試；須待本次 push workflow 實際完成並回讀結果後，才可標記測試通過。
- Main、正式早報、正式 Chart 3、首頁及所有既有排程均未修改。


## 17. D4 daily history handoff and per-observation provenance (research branch, 2026-11-18)

The S&P 500 source of truth for this integration is the already-verified cash-index OHLC captured by TAC morning report rule D4. The adapter does not make a second market-data request. It preserves the actual provider used for each trading date; when the report uses a fallback provider, that provider remains visible on that date and is never relabeled as Investing.com.

Added:
- `.github/scripts/import_sp500_from_tac_report.py`: validates one report's S&P 500 OHLC, cash-index identity, source URL, trading date and explicit retrieval timestamp; appends an immutable daily record to `sp500_tac_report_ohlc.jsonl`. Identical retries are no-ops; conflicting same-date records fail closed.
- `.github/scripts/build_sp500_from_tac_report_history.py`: validates every JSONL record hash and source metadata, then converts the daily close observations into the Chart 3 compact encoding. Its provenance file carries a separate source_name, source_url, source_note, retrieved_at, retrieval_method and record SHA-256 for every observation date. The compact source hash is tied to the exact JSONL bytes.
- `.github/scripts/test_build_sp500_from_tac_report_history.py`: tests mixed-provider history, record tampering and CFD rejection.
- `build_tac_chart3_synchronized_release.py`: accepts either the legacy single-source Investing.com provenance schema or the new TAC D4 per-observation provenance schema. In the D4 mode, every S&P 500 chart point carries its own source metadata; all compact dates must have matching provenance.
- `run_tac_chart3_synchronized_release.py`: default input paths now point to the TAC D4-derived compact history and provenance files.

Important boundary:
- The report fixture currently contains report cutoff time, but that is not proof of the exact retrieval timestamp for each price. The importer therefore requires an explicit timezone-aware `retrieved_at`; it must not fabricate one from report cutoff.
- A report without a verified S&P 500 cash-index OHLC entry cannot add an observation. Missing days are not filled.
- This research implementation is not yet wired into the morning-report production runner or its daily artifact persistence. It does not create a daily history automatically until that handoff is integrated and tested end-to-end.
- The new QA tests have been added to the isolated research workflow; workflow execution must be observed before declaring them passed.
- No Main branch, production report, official Chart 3 page or existing schedule was modified.
