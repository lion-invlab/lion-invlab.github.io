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
5. S&P 500 — 真實每日收盤價；指定 Investing.com 歷史資料來源，保留實際交易日期，不得以週資料、壓縮曲線或插值替代。

## 2. 每日檢查與分層流程

每日排程執行下列工作：

1. 讀取每個來源的 checkpoint、manifest、上次成功時間與 SHA-256。
2. 分別檢查來源是否有新觀測／新 vintage；依各來源公布頻率擷取，不假設五項同日更新。
3. 將新資料寫入 staging／候選區，先完成格式、日期、數值、重複鍵、來源回應與雜湊驗證。
4. ALFRED 四序列沿用 append-only vintage/event 記錄與 current snapshot reconciliation；只取新 vintage 並保留既定 overlap。S&P 500 使用獨立的 Investing.com 日線增量擷取器；在該擷取器完成並驗收前，不得宣稱五項同步發布已完整自動化。
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
- S&P 500 歷史檔存在，但指定 Investing.com 來源的合規日線增量更新器尚未完成。
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
