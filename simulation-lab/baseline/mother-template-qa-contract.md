# TAC 投資早報｜雙母版結構驗收清單

版本：1.13 DRAFT（2026-11-21｜鎖定商品歷史收市價、來源連結與合約一致性；尚未生效）
定位：SIM-1.4 DRAFT 的候選唯一詳細 QA 附件；只有 SIM-1.4 經使用者明確核准生效後，本契約才作為其執行附件。此檔不獨立生效、不取代主規則。
適用：每一份每日審核版與正式發布版；依報告日期選擇週一或週二至週五母版。
最高原則：每日報告必須從核准母版完整複製，只更新獲授權的日期內容、行情、新聞、行事曆與分析。不得以重寫、簡化或重新排版取代母版既有元件。

## A. 開工前來源鎖定（未通過即停止）

- [ ] 已先讀取 `simulation-lab/TAC_WORK_RULES_SIM_1.4_DRAFT.md`；此草案尚未生效，正式啟用前須由使用者核准。
- [ ] 已讀取 `simulation-lab/baseline/mother-template-manifest.json`，並依 `simulation_path` 讀取本目錄的唯讀母版副本。
- [ ] 已依台灣報告日期選定正確情境：週一／週二至週五。
- [ ] 母版精確路徑與 manifest 登記一致。
- [ ] 實際 Git blob SHA 與 manifest 核准 SHA 完全一致；不一致即停止，不得自行更新 manifest 或 fallback。
- [ ] 已記錄母版 SHA、每日輸出路徑及禁止修改檔案。
- [ ] 每日審核版由核准母版完整複製建立；不是由舊 preview、首頁、歷史早報或手動重建頁面產生。

## A2. 固定母版結構定位契約（依核准 SHA 快取，不每日重析）

### A2.1 結構基準與有效範圍

本節是兩份模擬母版的固定結構定位契約。官方母版 SHA 是 main Manifest 的唯讀正式基準；本次依使用者授權，僅更新 simulation branch 的隔離基準副本，故兩者 SHA 可不同。每日模擬只使用下列 simulation blob SHA；不得把模擬副本 SHA 冒充 main 正式母版 SHA。

| 情境 | 正式母版路徑 | main 正式 blob SHA（唯讀） | simulation baseline 路徑 | simulation blob SHA（實際執行） | 基準結構統計 |
|---|---|---|---|
| 週一 | `母版專區/TAC_母版_週一_2026-10-28_最終定版.html` | `a568e594e55909041d51d8eae7e6fe5f7986c096` | `simulation-lab/baseline/monday-mother-template.html` | `36f29bcb37816348756f9233b60f0429d675a76e` | DOCTYPE 1、html/head/body 各 1、style 124、script 25、ID 183；ID 無重複 |
| 週二至週五 | `母版專區/TAC_母版_週二至週五_2026-10-28_最終定版.html` | `3785405e331b10ec6189002e480be2a1edbe20ef` | `simulation-lab/baseline/weekday-mother-template.html` | `19e77a2f34f06a0f1a53d1eeaf875ac5e1345b96` | DOCTYPE 1、html/head/body 各 1、style 120、script 24、ID 174；ID 無重複 |

以上統計是原始正式母版的結構基準，不是要求每日重新逐項分析的工作。模擬執行時必須以 Manifest 的 simulation_blob_sha 鎖定隔離副本；副本 SHA 未變時，直接使用本節定位契約。main 正式母版仍唯讀，除非另有符合 SIM-1.4 正式生效版寫入權限的明確授權。

### A2.2 共用主要區塊錨點

所有 selector 均以核准母版內唯一 ID 為入口；下列 ID 在兩份母版各出現一次：

| 區塊 | 固定入口／結構 |
|---|---|
| 主內容根節點 | `main#overview.wrap` |
| 總結 | `main#overview > section.grid.two > article.card.bluf` |
| 市場情緒 | `#overview > section.tac-main-panel > article#sentiment` |
| 新聞掃瞄 | `section#news-scan.tac-tabset`；分頁輸入 `#tac-news-0`、`#tac-news-1`；面板 `#tac-news-panel-0`、`#tac-news-panel-1` |
| 全球焦點新聞 | `#tac-news-panel-0 > article#global-focus` |
| 市場熱門頭條 | `#tac-news-panel-1 > article#headlines` |
| 全球主要股市 | `section#global-markets.tac-tabset`；3 個 radio：`#tac-global-0..2`；面板：`#tac-global-panel-0..2` |
| 產業／債匯商品 | `section#industry-bonds-fx-commodities.tac-tabset`；5 個 radio：`#tac-assets-0..4`；面板：`#tac-assets-panel-0..4` |
| 本週經濟行事曆 | `section#calendar` |
| 本週財報行事曆 | `section#earnings` |
| S&P 500 盈餘健康度 | `section#sp500-earnings-health` |
| Fed 限時動態 | `section#fed`；radio：`#fed-live-tab-watch`、`#fed-live-tab-fomc`；面板由 `.fed-live-panel.fed-live-watch` 與 `.fed-live-panel.fed-live-fomc` 承載 |
| 今日觀察／盤面觀察 | `section#view` |

### A2.2a 全球主要股市三區評論綁定

- `#global-markets #tac-global-panel-0`：美國面板，唯一評論節點標題必須為「📌 美股觀察」。
- `#global-markets #tac-global-panel-1`：亞洲面板，唯一評論節點標題必須為「📌 亞股觀察」。
- `#global-markets #tac-global-panel-2`：歐洲面板，唯一評論節點標題必須為「📌 歐股觀察」。
- 每個面板必須恰有一個直接隸屬於該面板 article 的 `.market-reason`；不可將評論節點移至其他面板、跨面板共用或以來源備註取代。
- `.market-reason` 必須保留母版原有直接子節點順序：`b` 標題、`br`、評論文字節點；Builder 只可更新既有標題／文字內容，不得 `clear()` 後重建節點或改寫其屬性／樣式。
- QA 逐一讀取每個面板的標題、評論文字與該面板指數名稱；標題／區域不一致、評論提及其他區域專屬指數或數據、空白評論、只有資料來源備註均 FAIL。
- QA sidecar 必須保存三區各自的評論摘錄、面板 ID、評論標題、引用指數及 pass/fail。不得只以標題存在、全頁文字搜尋或 tabs 可切換作為通過證據。
- 任一區失敗，整體 review_ready=false；修正後三區全部重驗。無真正 DOM parser 時標示未測試，不得以字串替換宣稱 DOM 修復完成。

### A2.2b CNN Fear & Greed 分數與可見分級一致性

- 顯示分數必須即時計算對應區間，不得沿用母版靜態的 Fear／恐懼標籤。
- 分級區間固定：0–24 Extreme Fear／極度恐懼；25–44 Fear／恐懼；45–55 Neutral／中性；56–74 Greed／貪婪；75–100 Extreme Greed／極度貪婪。
- 英文標籤、中文標籤、刻度指針及 aria-label 必須由同一個有效分數更新；來源文字中的分級不得覆蓋計算結果。
- 分數無效或缺漏時，狀態顯示 Unavailable／待核實並隱藏舊指針，不得保留母版舊分級。
- 回歸測試必須涵蓋 0、24、25、44、45、55、56、74、75、100 邊界；19 必須顯示 Extreme Fear／極度恐懼。

### A2.3 行事曆卡片的固定巢狀結構

**經濟行事曆：**
- 入口：`#calendar`；三個 radio 為 `#week-econ-today`、`#week-econ-upcoming`、`#week-econ-published`，由 `.week-econ-tab-labels` 與 `.week-econ-panels` 對應。
- 狀態容器：`.calendar-status-group`；事件清單：`.econ-event-list`；事件節點：`details.econ-event`。
- 卡片標頭：`details.econ-event > summary > .econ-meta`，內含 `.econ-date`、`.econ-time`、`.econ-country`、`.econ-name`、`.econ-stars`。
- 卡片內容：`details.econ-event > .econ-details`。五區結構固定為：`.econ-primary-grid`（僅含 `.econ-prev`、`.econ-forecast`、`.econ-actual` 三欄），其後同層依序為 `.econ-field.econ-impact.wide`（市場影響）及 `.econ-field.econ-source.wide`（資料來源）；五區各自保留 `.econ-value`，來源連結必須位於資料來源欄位內。
- **母版差異不可抹平：** 週一與週二至週五的本週經濟卡均使用 `.econ-toggle`；週一上週經濟卡使用 `.econ-event-toggle`。不得把上週卡片 selector 套用到本週卡片，也不得為統一 selector 改寫其他結構。
- 展開控制定位：`#calendar details.econ-event > summary > span.econ-toggle`；週一正式母版已逐張補齊 12 張本週事件卡，週二至週五母版原有 16 張控制。

**財報行事曆：**
- 入口：`#earnings`；三個 radio 為 `#week-earnings-today`、`#week-earnings-upcoming`、`#week-earnings-published`，由 `.week-earnings-tab-labels` 與 `.week-earnings-panels` 對應。
- 狀態容器：`.calendar-status-group`；卡片清單：`.earnings-accordion-list`；事件節點：`details.earnings-accordion`。
- 卡片標頭：`summary.earnings-accordion-summary > .earnings-summary-main`，內含 `.earnings-summary-dates`、`.earnings-us-date`、`.earnings-tw-date`、`.earnings-company-name`、`.earnings-company-sub`、`.earnings-stars`；展開控制為 `.earnings-accordion-toggle`。
- 卡片內容：`.earnings-accordion-details`；一般欄位為 `.earnings-detail-field`／`.earnings-detail-value`。
- 已公布財報的 EPS／營收雙卡結構必須保留：`.earnings-results-grid` 內有兩張 `.earnings-actual-card`，並保留實際、預期、狀態與說明；不得改成單一文字欄或一般 callout。

### A2.4 週一專用結構

週一母版額外且唯一具有：
- `section#last-week-calendar`，內含 `details.last-week-calendar-collapse`，其下保留 `.calendar-status-group > .econ-event-list > details.econ-event`。
- `section#last-week-earnings`，內含 `details.last-week-earnings-collapse`，其下保留 `.calendar-status-group > .earnings-accordion-list > details.earnings-accordion`。
- 兩個上週區塊預設收折；不得在 `details` 加上 `open`。
- 週二至週五母版不存在 `#last-week-calendar` 與 `#last-week-earnings`，也不得新增。

### A2.5 每日沿用規則與重新解析觸發條件

1. 每日先讀 `simulation-lab/baseline/mother-template-manifest.json`，取得本次情境的 `simulation_path` 及核准 SHA，再 fetch 該模擬母版副本核對實際 blob SHA。
2. **實際 SHA 與本節對應 SHA 相同：** 直接沿用本節 selector／巢狀結構契約；只做錨點存在且唯一、必要星期專屬區塊存在／禁止存在、基礎文件節點及 ID 唯一性檢查。不得重新分析整份母版 DOM。
3. **實際 SHA 與 Manifest 或本節 SHA 任一不符：** 停止組裝，不得 fallback、不得猜測 selector。只有在使用者已核准母版變更且 Manifest 已同步後，才對新 SHA 做一次完整結構解析、更新本節契約及版本統計。
4. **定位契約中的 selector 缺失、重複或父子關係不符：** 視為結構失效，停止該區塊寫入並回報；不得退回標題文字、HTML 註解、字串 index、正規表示式或固定字元範圍尋找替換邊界。
5. 每日組裝必須使用 DOM parser 定位節點；只更新已授權目標節點的文字、屬性或子節點。重複事件卡應以該情境母版的原始卡片節點 clone，再填入資料；保留原有外層容器、details/summary、class、ID 規則、tabs、CSS、JavaScript 及互動。
6. 每日輸出仍須解析 preview DOM，依本節錨點及本清單其餘 QA 驗收輸出；這是輸出驗證，不是重新分析母版。若無法使用真正 DOM parser，不得以字串替換冒充 DOM 更新，應標示未完成並停止不安全寫入。
7. 母版結構解析是「每個核准 SHA 一次」；每日例行工作是「SHA 核對＋定位契約快速檢查＋輸出驗證」。只有核准 SHA 改變才重新解析母版。

---

### A2.6 QUICK ACCESS 工具欄固定連結（兩份母版均適用）

- [ ] 工具欄 `aside#tac-side-tools` 存在且唯一。
- [ ] 連結順序固定為「美股個股波動率」→「Q4 精選基金」→「專題報導」→「互動式圖表」→「歷史早報」。
- [ ] 「互動式圖表」唯一連結指向 `https://lion-invlab.github.io/interactive-charts/`。
- [ ] 每日審核版必須從母版繼承此入口；不得由每日資料更新流程刪除或覆蓋。

## B. 共用結構完整性（兩份母版均適用）

- [ ] 頁首、報告日期、狀態列、導航、所有區塊錨點完整。
- [ ] 總結、Market Sentiment、焦點新聞、熱門頭條、全球市場、產業／債匯商品、行事曆、今日觀察、資料來源及頁尾均保留。
- [ ] 原始 CSS、JavaScript、字體、版面容器及響應式規則完整；不得只複製 HTML 內容而漏掉相依樣式／腳本。
- [ ] 一般每日組裝前後的 style 節點數、style ID／內容、script 節點數、script ID／內容與母版一致；唯一條件式例外為使用者已核准的單次突發專題 `special_focus`，只在該筆專題輸入存在時允許該專題節點及其專屬樣式，且不得寫回母版。
- [ ] Builder 不得追加 summary 樣式、週一收折樣式、側欄權威樣式、能源手機版樣式、財報卡片樣式或市場名稱字體樣式；如需視覺修正，須先經核准更新 simulation 母版與 Manifest／QA Contract，再由 Builder 沿用。

- [ ] 所有原有 tabs、radio inputs、labels、details/summary、展開／收折控制及其關聯 ID 均保留。
- [ ] 無重複 ID、新增錯誤巢狀、未閉合標籤、失效錨點或無效 href。
- [ ] 與母版相比的差異僅為當日資料更新及明確授權的內容變動；不得出現元件刪除、簡化、換成純文字或結構重建。
- [ ] `#sentiment .sent > .sbox:last-child` 保留母版 label 與 body div 兩個子節點及其 inline style；只更新 body 文字，不得清空重建卡片。
- [ ] `#sp500-earnings-health` 保留母版完整子樹、指標卡數量、inline style、排列與欄數；只更新既有文字槽位及既有來源連結 href，不得清空或重建整個 Dashboard。

## C. 經濟行事曆卡片（兩份母版均適用）

逐張檢查「今日公布／即將公布／已公布」中的事件卡：

- [ ] 每張事件卡保留母版原有獨立展開／收折結構。
- [ ] 每張卡片標頭右側均有母版規格的紅色圓形「＋」控制；展開後圖示／狀態依母版互動規則切換。
- [ ] 日期、台灣時間、國家／地區、事件名稱、重要性星等及展開內容欄位完整。
- [ ] 展開後前值、預估、實際、影響判讀與來源欄位依事件狀態正確呈現；未公布事件不得偽造實際值。

**模擬區雙母版經濟事件卡固定五區排列（週一、週二至週五及週一上週回顧均適用）：**
- [ ] 第一區「前值」位於左上；第二區「市場預估」位於左下。
- [ ] 第三區「實際」位於右側，垂直跨越前值與市場預估兩格的總高度（含兩格間距）。
- [ ] 第四區「市場影響」位於下方，獨立全寬顯示。
- [ ] 第五區「資料來源」位於市場影響下方，獨立全寬顯示。
- [ ] 手機與桌面均維持左側上下、右側跨兩列的雙欄比較結構；不得在手機改為單欄堆疊。
- [ ] DOM 必須為 `.econ-details > .econ-primary-grid`（僅含前值、預估、實際三欄），其後同層依序為市場影響、資料來源；兩個全寬欄位不得包在 primary-grid 內。
- [ ] 三個比較欄位 class 固定為 `.econ-prev`、`.econ-forecast`、`.econ-actual`；主網格 areas 固定為 `"prev actual" "forecast actual"`。
- [ ] 市場影響與資料來源分別使用 `.econ-impact.wide`、`.econ-source.wide`，標籤文字固定為「市場影響」「資料來源」。
- [ ] 週一上週經濟卡與本週經濟卡皆為五欄；週一原「觀察重點」內容映射至「市場影響」，原「來源」映射至「資料來源」。缺少影響文字的母版示範卡使用明確待填佔位，不得虛構事件分析。
- [ ] 組裝器只填入五區內容，不得再以輸出後 CSS 重新拼裝母版經濟卡。
- [ ] 三分頁狀態分類、日期／時間排序、卡片數量及事件搬移正確。
- [ ] 以手機寬度及桌面寬度檢查按鈕位置、觸控區、文字換行與水平溢位；手機不得把比較區改成單欄，實際欄仍須跨越左側兩格。

注意：不同母版可能使用不同的卡片 class／實作；驗收應以各自核准母版的實際結構與視覺為準，不可為了統一 selector 而重寫母版。

## D. 財報行事曆卡片

### D1. 所有財報卡

- [ ] 公司日期、盤前／盤後、台灣時間、公司名稱、代碼、產業、星等及右側展開控制完整。
- [ ] 卡片保留母版原有獨立展開／收折結構與視覺。
- [ ] 三分頁分類及日期／時間排序正確。

### D2. 已公布財報專用版型（必須逐卡檢查）

- [ ] EPS 與營收兩張實績卡並列；手機版仍為兩欄，不可任意堆疊。
- [ ] EPS 卡顯示實際、預期、幣別、GAAP／調整後口徑及狀態標籤。
- [ ] 營收卡顯示實際、預期、幣別／單位及狀態標籤。
- [ ] EPS 與營收各自獨立判斷高於／符合／低於預期；無可比共識須明確標示。
- [ ] 兩張實績卡下方保留母版的全寬詳細資訊區：公布時段、EPS 比較、營收比較、財報判讀與股價反應、資料來源。
- [ ] 上方實績卡與下方詳細資訊數字、口徑、方向及日期一致。
- [ ] 不可把 EPS／營收雙卡改成一般文字、單一 callout 或普通事件卡。
- [ ] 完整且已驗收的卡片應保留；只補缺漏欄位，不無故重製整張卡。
- [ ] 已公布 EPS／Revenue 雙卡的 DOM 層級、class、子節點順序及 CSS 必須與對應母版原型一致；不得自行追加／覆蓋 CSS 或改變桌面／手機欄數。

## E. 週一專用：上週行事曆

僅週一母版適用：

- [ ] 上週經濟行事曆區塊及導航存在。
- [ ] 上週財報行事曆區塊及導航存在。
- [ ] 兩個上週區塊初始狀態均為收折；不得在 details 上加 `open`。
- [ ] 使用者點擊後才展開；再次操作可收折。
- [ ] 週二至週五母版不得出現這兩個上週區塊及其導航。

## F. S&P 500 盈餘健康度 Dashboard

- [ ] 保留母版完整 Dashboard，而非改成純文字段落或單一 callout。
- [ ] 保留「TAC 核心判讀」獨立區。
- [ ] 保留母版原有指標卡數量、欄數、排列、底色、邊框、數字層級與說明文字。
- [ ] 依母版顯示混合盈餘年增率、EPS 優於預期比例、EPS 平均超預期幅度、混合營收年增率等核心指標；若母版另有營收超預期比率、估值等欄位亦須保留。
- [ ] 保留「如何解讀／收入面與解讀」、「接下來看三件事」及收折式資料來源／統計口徑。
- [ ] 指標值、FactSet 快照日期、公布進度及文字判讀一致；不得把舊快照標示為即時數據。
- [ ] 週一與週二至週五的卡片欄數可依各自核准母版不同；不得把其中一份母版的排列強行套到另一份。
- [ ] Builder 必須保留週一 4 張指標卡及平日 3 張指標卡；不得將兩份母版統一改成同一組卡片數量。

## G. Fed 限時動態兩個活頁

- [ ] 保留「CME FedWatch」及「FOMC 會議」兩個活頁標籤與 radio/tab 結構。
- [ ] 兩個活頁均可切換，沒有重複 ID、錯誤 label for 或失效互動。
- [ ] CME FedWatch 活頁保留母版原有維持／升息（及母版實際列出的其他情境）機率卡、百分比、目標利率區間、機率分布長條、圖例、資料時間／快照口徑及來源。
- [ ] FedWatch 機率卡、分布長條及圖例數量必須維持各自母版原始數量；本次兩份母版均為 2 卡／2 段／2 圖例，不得由 Builder clone 第三張卡或追加 CSS。
- [ ] 只有恰為「維持＋升息」兩種情境且合計 100%（允許 0.2 個百分點誤差）時，才更新兩卡與兩段；其他情境數量／類型不符時，兩卡標示待核實、隱藏不完整分布，並在既有資料時間／快照收折區列出完整情境，不得靜默丟棄。

- [ ] 機率卡與分布長條百分比相加一致；來源與快照時間明確，歷史快照不得標示為即時。
- [ ] FOMC 活頁保留母版原有會議日期、政策聲明時間、記者會時間、目前目標利率、核心觀察及官方來源。
- [ ] FOMC 活頁保留「本週聯準會官員行程」固定區塊；母版需有唯一的 `#fed .fc-fomc-weekly-events`，內含 title、list、event prototype、empty-state 四個固定槽位。
- [ ] Builder 只可 clone `.fc-fomc-weekly-event-template` 原型並填入日期、官員行程、影響說明與官方來源；不得清空／重建外層容器、標題或清單 wrapper。
- [ ] 有已核實行程時逐筆顯示已發表／預定狀態、台灣時間、官員／活動名稱、影響說明及官方來源；無已核實行程時顯示固定空狀態，不得因此捏造行程或使整份早報無條件失敗。
- [ ] 週一與平日母版均須存在同一固定槽位契約；組裝前後外層節點與原型結構保持一致。
- [ ] 不得把任一活頁改成純文字、單一 callout 或只剩會議日期的簡化卡。
- [ ] 兩活頁內容及時間均按報告當日更新；未核實資訊明確標示，不得沿用過期會議資訊。

## H. 行情超連結

- [ ] 指數／商品／外匯／殖利率／ETF 名稱連結與標的完全一致；數值及評論不被錯誤包進連結。
- [ ] WTI／Brent／GC／SI 可見名稱不得附加合約月份或完整月份合約代碼（CLF27／LCOF7／GCZ6／SIZ6）；母版短名稱中的商品根代碼 GC／SI 可保留。完整合約代碼、月份、交易所及報價口徑只放在收折資料來源說明，不得出現在行情摘要列、區塊 meta 或市場觀察文字。
- [ ] WTI／Brent／GC／SI 名稱連結必須直接開啟 Investing.com 對應商品歷史頁，核對頁面標題、商品、交易所及當次選定合約月份；只檢查網址網域或沿用舊 cid 不算通過。
- [ ] 四項商品的收折資料來源說明必須列出對應完整合約代碼／月份；相同字串不得出現在商品名稱列、tab-panel-meta 或 market-reason。
- [ ] 四項商品的 `display` 與 `change_display` 必須逐字對應同一 Investing.com HK 歷史數據頁、同一合約、同一資料日期的收市價與日升跌幅；不得以即時 Last、盤後 Last、即時 CFD 報價或不同月份合約替代。
- [ ] `source.quote_type` 必須為 `investing_historical_close`；`source.url` 必須等於 `instrument_url`，且為 Investing.com HK 歷史數據頁。
- [ ] `source.history_close`／`source.history_change` 必須分別等於顯示價格／漲跌幅；收折來源說明須呈現資料日期、完整合約月份、來源連結及口徑備註。
- [ ] 事件時間先轉 Asia/Taipei；報告日事件即使預定時刻晚於早報截稿仍列「今日公布」，未來台灣日期列「即將公布」。
- [ ] 已過預定時間但無發布證據者維持待核實，不得自動改為 released／published 或填造 actual；若有發布狀態來源但官方實際值未核實，卡片明確標示「公告已發布；實際值待核實」。
- [ ] 日期／時間未知的報告日事件不得假設午夜已過；延期、取消須明確標示；經濟及財報「已公布／待核實」分頁標題與卡片狀態不得互相矛盾。
- [ ] `pending_verification` 事件若預定日期／時間尚未到截稿點，仍依台灣日期列在「今日公布」或「即將公布」，卡片顯示「公布狀態待核實」；`status_source` 或 `report_layer_status_only` 不得強制提前列入「已公布」。
- [ ] 只有事件時點不晚於台灣截稿、且有可核實發布狀態來源時，才可顯示「公告已發布；實際值待核實」；沒有發布證據時維持「公布狀態待核實」。
- [ ] `time_known=false` 或缺少 `time_known` 時，不以 ISO 日期的午夜時間推斷事件已過；跨時區時間先轉 Asia/Taipei 再計算報告日。
- [ ] 依 WR 標準行情超連結清單核對 href、target、rel。
- [ ] 全球主要股市每個指數均連至對應標的頁，重複指數目的網址一致。
- [ ] 新加坡海峽時報指數（STI）使用：`https://hk.investing.com/indices/singapore-straits-time`。
- [ ] CNN Fear & Greed 依 WR 規定同頁開啟；其他一般行情連結依規定另開分頁。
- [ ] 每日更新行情內容後，重新檢查所有受影響的連結沒有遺失、錯置或連到相似但不同標的。

## I. 技術與視覺回歸

- [ ] HTML 標籤巢狀與閉合檢查通過。
- [ ] 所有 ID 唯一；所有 label for、錨點及 tabs 對應有效。
- [ ] 所有內部／外部連結均有合理目的地；可用工具實際開啟的連結已抽測。
- [ ] 依標準視窗尺寸檢查：手機 320px、360px、390px、412px；平板 768px；桌面 1440px。320px 納入例行與發布必要測試。
- [ ] CI 視覺測試環境必須安裝 Noto CJK 繁中字型，且 `fc-match "Noto Sans TC"` 確認解析至 Noto Sans CJK 字型；不可讓中文字型回退成缺字方框。
- [ ] Playwright 必須等待 `document.fonts.ready`，並以 `document.fonts.check` 確認「繁體中文」字形可用；字型未載入或字形缺失即視覺 QA 失敗，不得只因版面尺寸比較通過就宣稱視覺通過。
- [ ] 行事曆紅色圓形＋、財報雙卡、健康度 Dashboard、Fed 兩活頁均完成視覺比對。
- [ ] 漲跌色彩固定為上漲／正值紅色、下跌／負值綠色；同類數字字級、粗細、行高與對齊一致。
- [ ] 行情中文名稱在上、英文代碼小字在下且不加括號；連結只包名稱／代碼，不包點位、漲跌幅或評論。
- [ ] 行事曆五星事件標題使用 TAC 紅色；四星沿用母版原有樣式。
- [ ] 總結區下方未重新出現已刪除的「關鍵重點」膠囊或同義替代元件。
- [ ] 若母版含 QUICK ACCESS 工具欄說明泡泡，首次捲動／觸控移動後泡泡立即隱藏；呼吸燈／高亮提示依母版原定時間獨立持續，兩者分開實測。
- [ ] 收折／展開、tabs、radio、導航、回頂端及其他母版互動完成實際測試。
- [ ] 如未能執行真實瀏覽器或裝置測試，必須標示「未測試」，不可宣稱視覺與互動通過。
- [ ] GitHub Pages 預覽已實際開啟或以可用方式確認部署；若無法確認，明確標示尚未驗證。

## J. 交付前差異稽核與保護

- [ ] 將每日審核版與所選母版比較，逐項檢查結構差異；不可只做關鍵字存在檢查。
- [ ] 上述 C–H 各項全部通過；任何一項失敗即不得標示為「可審核完成」。
- [ ] 正式首頁 `index.html`、雙母版、manifest、設計系統及其他受保護檔案均未被擅自修改。
- [ ] 使用者未授權發布前，不得更新正式首頁。
- [ ] 寫入後重新 fetch 回讀每日審核版，確認 SHA、內容及差異。
- [ ] 回報逐項列出「通過／未通過／未測試／待核實」，並提供實際證據；不得以 commit 成功取代驗收。

## K. 發現不符合時的處理

1. 立即停止在不符合版面上繼續填資料，不得用補 CSS 或臨時覆蓋樣式掩蓋結構缺失。
2. 保留原有行情／新聞／行事曆內容，不得為了修版型而任意刪除、改寫或重抓已核實內容。
3. 回到核准母版，找出缺失元件，優先以母版原有完整結構及樣式修復；不得自行重設計。
4. 修復後重新執行本清單全部相關項目及完整差異稽核。
5. 母版本身若有疑義或 manifest SHA 不符，停止並回報；未經使用者明確核准不得改母版或 manifest。


## L. SIM-1.4 候選規則補充（2026-11-21）

- 本文件版本 1.5 為 SIM-1.4 DRAFT 的候選 QA 附件，尚未生效；在 SIM-1.4 主規則獲使用者明確核准前，不得把本契約標示為已啟用的新規範。
- 母版結構差異檢查不得由 Builder 以追加 CSS、重建既有 Fed 區塊、清空並重組母版 summary 子節點等方式自行「修復」；除非使用者另行核准明確的母版／技術契約變更。
- 320px viewport 加入必要測試，保留 360／390／412／768／1440px。
- 每一個執行結果需明確區分 PASS、FAIL、NOT_TESTED；無實際瀏覽器證據不得填 PASS。


## M. SIM-1.4 候選財報狀態與共識來源驗收（2026-11-21）

- 財報公開狀態只有四種：beat、miss、inline、pending，對應「優於預期／低於預期／符合預期／尚未公布或資料尚未齊備」。不得輸出 incomparable、consensus_divergent 或其他第五種狀態。
- EPS 與 Revenue 分開比較。Yahoo Finance Average Estimate 為第一順位、Investing.com 為第二順位；LSEG I/B/E/S、FactSet 僅作後順位備援，不能覆蓋已取得的較高順位來源。來源衝突保留 conflict flag／說明，但不得以「共識來源分歧」取代數值比較結果。
- PIT 快照是來源證據層，不是一般數值比較的必要條件。只要實際值與所選共識值可按同一期間、幣別及單位比較，且沒有明確相反的發行公司口徑聲明，就應進行數值比較；GAAP／Adjusted 細節未揭露本身不得阻止比較。
- 若幣別、單位、期間明確不相容，或發行公司明確聲明不可比較，公開狀態仍只能使用 pending，並在財報判讀文字標示「比較資料尚未齊備」及原因；不得建立 incomparable 第五狀態，也不得偽造 Beat／Miss。
- SIM-1.4 財報判讀引擎版本候選為 1.4.0；schema 的 judgment_engine_version、引擎 VALID_STATUSES、render_status、render_summary、Builder renderer、visual regression 與所有測試必須一致。
- visual regression 必須拒絕 incomparable／consensus_divergent class；若明確不可比較的財報仍顯示「尚未公布」或方向性結果，亦應 FAIL。數值存在但口徑不相容時應顯示「比較資料尚未齊備」。
- 目前 Builder 的 earnings_status_label／earnings_commentary 仍含 legacy incomparable／consensus_divergent 顯示分支，且無法為「數值存在但不可比」顯示「比較資料尚未齊備」；此為已知 BLOCKER，Builder 未修正前本契約不得判定財報 renderer Gate PASS。


## 2026-11-21｜版本 1.6 基準同步紀錄

- 依 simulation Manifest SHA `1496a510d144d340c41b642592675233d5bd2917`，更新 A2.1 中週一與平日 simulation baseline SHA：Monday `36f29bcb37816348756f9233b60f0429d675a76e`；Weekday `19e77a2f34f06a0f1a53d1eeaf875ac5e1345b96`。
- 本次只同步已由 Manifest 登記的實際母版 SHA，不修改正式母版路徑／SHA，也不改動 DOM selector 或視覺規格。
- 本契約仍為 DRAFT；SIM-1.4 未經使用者核准前不生效。


## N. 母版固定 DOM 零退化比對（SIM-1.4 候選 Gate）

- 每次完整 build 後，必須執行 `simulation-lab/runner/validate_mother_dom_contract.py`，以 Manifest 選定且 SHA 鎖定的母版副本，對照實際審核版 HTML。
- 必須逐項比對：全部 `style`／`script` 節點與內容、全頁 ID 清單、總結段落原始子節點順序、FedWatch 兩張機率卡及分布長條／圖例、Fed 活頁 radio 與 label 對應、FOMC 固定欄位、Fed 官員行程外層四個固定槽位、QUICK ACCESS 工具欄，以及週一兩個收折區的 summary DOM。
- 動態資料列只允許出現在明確的資料槽位內；Fed 官員行程可複製母版事件原型，但不得改寫外層容器、標題、清單 wrapper、原型或空狀態節點。
- 週一／平日母版的總結段落子節點數量與順序必須保持各自原始結構；資料項目數量不符時停止組裝，不得清空段落後自行建立另一種標籤／換行結構。
- 比對失敗即為 FAIL；不得以 Playwright 視覺測試通過、元素仍可見或人工判斷「看起來一樣」取代結構比對。
- 本 Gate 不代表資料內容已達 REVIEW_READY；行情刷新、新聞、行事曆及來源證據仍須分別通過各自 Gate。


## 2026-11-21｜版本 1.7 DOM 保護補充

- 明確固定三區市場評論的 `b／br／text` 直接子節點結構。
- 明確固定市場情緒核心解讀卡與 S&P 500 盈餘健康度 Dashboard 的子樹／inline style；資料更新僅限既有文字槽位與既有來源連結 href。
- 本次為 simulation QA Contract DRAFT 修訂，不修改正式母版及 main QA 清單；SIM-1.4 未經使用者核准前不生效。


## 2026-11-21｜版本 1.8 繁中字型視覺驗收補充

- CI 需安裝 Noto CJK 字型並驗證 Noto Sans TC 的 fontconfig 解析結果。
- Playwright 需確認繁體中文字型可用後才截圖；方框缺字截圖不得列為有效視覺驗收證據。
- 本版本仍為 simulation QA Contract DRAFT；SIM-1.4 未經使用者核准前不生效。
