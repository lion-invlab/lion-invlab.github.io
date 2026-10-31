# TAC 動靜分離｜雙母版動態插槽盤點 v1.3

狀態：Gate A 工作底稿（候選定位彙整；未授權每日自動寫入）
分支：`tac-template-architecture`
依據：正式雙母版 manifest／SHA、`slot-map-v1.2.md`、`selector-registry-v1.json`、`summary-sentiment-map-v1.md`、`weekly-commodities-fomc-map-v1.md`、`repeat-group-policy-v1.1.md`。

## 0. 本版目的與規格優先序

本文件將既有分散盤點合併成一份雙母版欄位清冊，處理舊文件間「已定位／未定位」狀態不一致的問題。它只定義候選節點、模板差異及下一輪驗證工作，不會自行授予寫入權。

規格優先序：
1. 正式母版 manifest 與實際 HTML DOM（唯讀基準）。
2. 本文件 v1.3 的雙母版盤點狀態。
3. 各專項 map／selector registry／repeat-group policy（作為證據與測試資料）。
4. 舊版 README 的進度敘述；若與本文件不一致，須回頭更新 README，不得沿用過期狀態。

任何正式母版 SHA、manifest 或 DOM 指紋不符，立即停止。

## 1. 正式母版基準（唯讀）

| 模板 | 正式檔案 | Blob SHA |
|---|---|---|
| 週一 | `母版專區/TAC_母版_週一_2026-10-28_最終定版.html` | `776f778b895c6da781348bcf8fefc1d4719ed4ce` |
| 週二至週五 | `母版專區/TAC_母版_週二至週五_2026-10-28_最終定版.html` | `ab3286750a64aa0fc9fc01af51f819024526a4ba` |

上述檔案只供讀取與比對。本分支不得修改正式母版、manifest、首頁 `index.html`、根目錄 `TAC_WORK_RULES.md` v3.4，亦不得覆寫既有 11/02 預覽。

## 2. 欄位狀態定義

- **已定位（候選）**：DOM 中找到具體容器與子節點，且既有 selector cardinality audit 有相應記錄；仍不代表已授權寫入。
- **專項定位（候選）**：專項 map 已指出具體子節點，但尚須補 selector registry／逐欄位 DOM 驗證。
- **容器保護**：只用於限定範圍與比對，不得整段覆寫其文字或 innerHTML。
- **未定位／禁止**：不得建立 selector、不得寫入；先完成結構盤點。
- **固定結構**：不得由每日資料更新器更動，包括 wrapper、卡片骨架、tab/radio/label、details/summary、按鈕、欄位標籤、CSS、JS、aria／互動骨架等。

## 3. 雙模板共用欄位清冊

| 區塊 | 容器／候選定位 | 資料節點候選 | 筆數規則 | 目前狀態 |
|---|---|---|---|---|
| 全球焦點新聞 | `#global-focus` | `#global-focus .newsitem`；卡內 `h3`、`p`、`.newsmeta a` | 固定 5 則 | 已定位（候選）；卡片骨架固定 |
| 市場熱門頭條 | `#headlines` | `#headlines .newsitem`；卡內 `h3`、`p`、`.newsmeta a` | 固定 10 則 | 已定位（候選）；卡片骨架固定 |
| 全球主要市場－美國 | `#tac-global-panel-0` | 面板內第一個 `article.card .row`；名稱連結、行情值、漲跌狀態；`.tab-panel-meta`、`.market-reason`、`.source-details` | 5 列 | 已定位（候選） |
| 全球主要市場－亞洲 | `#tac-global-panel-1` | 同上，僅限本面板 | 6 列 | 已定位（候選） |
| 全球主要市場－歐洲 | `#tac-global-panel-2` | 同上，僅限本面板 | 3 列 | 已定位（候選） |
| 11 大產業 ETF | `#tac-assets-panel-0 #us` | `.sector-list > .sector-row`；`.rank`、`.sector-label`、`.r` 及漲跌 class | 固定 11 列；依漲跌幅排序 | 已定位（候選）；僅 ETF 漲跌幅，不得增加其他欄位 |
| 美債殖利率 | `#bonds` | `#bonds > .row`；2Y／10Y／30Y 行情值與漲跌狀態 | 固定 3 列 | 已定位（候選） |
| 外匯 | `#fx` | `#fx > .row`；DXY、USD/TWD、EUR/USD、GBP/USD、AUD/USD、USD/JPY | 固定 6 列 | 已定位（候選） |
| 本週經濟行事曆 | `#calendar` | `#calendar .econ-event`；摘要欄位及 `.econ-details .econ-field .econ-value` | 動態；依實際事件 | 已定位（候選）；Repeat Group |
| 本週財報行事曆 | `#earnings` | `#earnings .earnings-accordion`；摘要欄位及 `.earnings-detail-field .earnings-detail-value` | 動態；依實際事件 | 已定位（候選）；Repeat Group |
| FedWatch | `#fed .fed-live-watch` | `.fc-prob`、`.fc-split-head`、`.fc-split-bar`、圖例數值及 aria-label | 目前 2 個機率情境卡；依實際資料結構核對 | 已定位（候選）；比例外框固定 |
| 市場情緒 VIX／MOVE | `#sentiment` | 第 1、2 個 `.sbox` 的 `strong`、緊鄰漲跌 span、各自 `.source-details .source` | 固定 4 個 sbox 中的前 2 個 | 專項定位（候選）；只改葉節點 |
| CNN Fear & Greed | `#sentiment .cnn-fg-preview` | `.fg6-score-main`、`.fg6-status`、`.fg6-marker` 的 left／aria-label、來源文字；週一另有 `.fg6-date` | 固定 1 區 | 專項定位（候選）；日期為模板差異 |
| 市場情緒核心解讀 | `#sentiment .sent > .sbox:last-child` | 卡內解讀文字節點 | 固定 1 卡 | 容器保護；須先拆出不破壞 label／骨架的原子文字節點 |
| 總結 | `section.grid.two article.card.bluf` | `h1` 與 `p` 命中各 1 | 固定 1 卡 | 容器已定位；正文含多個語意段與標籤，整個 `p` 不得直接替換 |
| 今日觀察－市場觀點 | `#view .focus-panel.focus-market` | `.key` 內各段落／文字 | 固定 1 panel | 容器保護；須逐段／逐文字節點定位 |
| 今日觀察－關鍵價位 | `#view .focus-panel.focus-levels` | `.key` 內指數段落；來源收合區獨立保留 | 固定 1 panel | 容器保護；不得覆寫整個 `.key` |
| 今日觀察－核心觀察 | `#view .focus-panel.focus-core` | `.callout` 內評論文字 | 固定 1 panel | 容器保護；週一含 compact-disclosure，須逐節點處理 |

注意：候選 selector 的命中數是母版結構定位測試，不是每日內容筆數目標。全球行情列與產業／債匯欄位的具體子節點仍須由資料更新器以精確子 selector 寫入，禁止全頁泛用 class 查找。

## 4. 商品與 FOMC 專項欄位

| 區塊 | 模板 | 容器／候選定位 | 資料節點候選 | 狀態 |
|---|---|---|---|---|
| WTI／Brent | 雙模板 | `#tac-assets-panel-3 .energy-card` | `.energy-card > .row` 兩列；`.tab-panel-meta`、`.market-reason`、`.source-details` | 專項定位（候選）；補入 selector registry 並驗證雙模板 |
| Gold／Silver | 雙模板 | `#tac-assets-panel-4 article.card` | `article.card > .row` 兩列；日期／合約口徑、觀察、來源 | 專項定位（候選）；補入 selector registry 並驗證雙模板 |
| FOMC 會議 | 雙模板 | `#fed .fed-live-fomc .fc-fomc` | `.fc-fomc-meeting b`、`.fc-fomc-press b`、`.fc-fomc-rate b`／`small`、`.fc-fomc-observation b`、說明段落 | 專項定位（候選）；補入 selector registry 並驗證雙模板 |

商品的能源與貴金屬是不同 tab panel，不可合併或跨面板寫入。日期／合約口徑與來源文字雖屬資料內容，仍須按各自行情資料來源逐筆對應。

## 5. 週一專屬欄位

| 區塊 | 容器／候選定位 | 資料節點候選 | 筆數規則 | 狀態 |
|---|---|---|---|---|
| 上週經濟行事曆 | `#last-week-calendar` → `.last-week-calendar-collapse` → `.calendar-status-group` → `.econ-event-list` | 每張 `.econ-event` 的 `.econ-date`、`.econ-time`、`.econ-country`、`.econ-name`、`.econ-stars`；展開欄位 `.econ-details .econ-field .econ-value` | 動態；依 WR 重要性五星事件 | 專項定位（候選）；需補 registry 與逐欄位測試 |
| 上週財報行事曆 | `#last-week-earnings` → `.last-week-earnings-collapse` → `.calendar-status-group` → `.earnings-accordion-list` | 每張 `.earnings-accordion` 的日期、公司、產業、星級；結果卡 EPS／營收實際與預期、優劣狀態、分析、來源 | 動態；依 WR 篩選重要財報 | 專項定位（候選）；需補 registry 與逐欄位測試 |

上週經濟／財報外層收合、status group、列表 wrapper、卡片骨架與欄位 label 固定。不得把目前樣本 3 張／7 張寫死。這兩個區塊只存在於週一模板，平日模板沒有它們是正常模板差異，不是缺漏。

## 6. 明確禁止建立或寫入的區域

1. **獨立 KPI 區**：雙母版的 `<main id="overview">` 均由總結區開始，沒有獨立 KPI grid／卡片。不得新增 KPI 區或自行建立 KPI 插槽。
2. **整段覆寫容器**：總結正文、核心情緒解讀、今日市場觀點、關鍵價位、核心觀察等複合內容，不能以整個父容器的 `textContent`／`innerHTML` 替換。
3. **跨模板借用**：週一上週行事曆節點不得複製到平日模板；週一 CNN 日期節點不得假設平日也存在。
4. **泛用 selector**：禁止全頁 `.row`、`.r`、`.value`、`.chg` 等查找；每個 selector 必須以唯一模板容器限定。
5. **未登記區塊**：SOX、VIX、MOVE 等分散行情卡的完整行情欄位尚未全部納入本版 allowlist；不得因已有來源連結或文字就推定可寫入。

## 7. Repeat Group 與 empty-state 界線

- 動態群組：本週經濟卡、本週財報卡、週一上週經濟卡、週一上週財報卡。張數依實際事件，不設樣本數上下限。
- 固定群組：全球焦點 5、熱門頭條 10、全球市場列、11 大產業 11、美債 3、外匯 6、情緒 4 個 sbox、今日觀察 3 個 panel 等。
- 週一／平日各自以自己的正式母版作骨架，不得跨模板複製卡片原型。
- 只有同一模板、同一區塊實際存在的 empty-state HTML 原型才可進行列表／empty-state 變體切換。現有測試僅確認週一本週經濟／財報區塊具備可用原型；平日本週及週一上週區塊無同區塊原型，必須拒絕自動轉換。
- 每次增刪均須記錄事件名稱、日期、來源、增刪理由與結果；不得靜默增刪。

## 8. Gate A 尚需完成的工作

- [ ] 將商品 WTI／Brent、Gold／Silver 與 FOMC selector 納入 registry，逐模板跑命中數、父子關係及 cardinality。
- [ ] 將週一上週經濟／財報欄位納入 registry，確認每個欄位在每張卡中的唯一性及卡片骨架。
- [ ] 將總結、情緒、今日觀察的複合欄位拆成可安全更新的葉節點；對含有來源收合、計算方式、標籤的容器明確設為 protected。
- [ ] 對所有「專項定位」欄位建立正向／反向測試：允許資料葉節點變更，拒絕父容器、label、class、style、aria、details/summary、CSS／JS 變更。
- [ ] 產出週一與平日兩份欄位層級驗證報告；兩版不得合併成單一假設。
- [ ] Gate A 通過後，才進入開發母版產生；開發母版仍只存在測試分支，不能自動成為正式生產母版。

## 9. 寫入權限聲明

本文件不是每日更新器的寫入授權清單。所有狀態目前均為候選定位。只有完成 selector registry、欄位級 diff、正反向測試、雙模板瀏覽器驗證，並經專案驗收與使用者明確核准後，才可將指定葉節點升級為可寫入欄位。根目錄 WR v3.4 仍是正式早報內容與資料品質規則的唯一權威。
