# TAC 設計系統架構稽核｜2026-10-26

## 基線盤點
- 分支：`tac-design-system-work-2026-10-24`（隔離測試分支，未發布正式首頁）
- `design-system.css`：41,497 字元、264 個 `!important`、190 個規則區塊。
- 重複選擇器：42 組（以空白正規化後比對）。
- 舊 CSS `legacy-cascade.css` 約 188,986 字元、1,995 個 `!important`。
- 候選建置仍把舊 CSS 與新設計系統 CSS 合併；目前是漸進遷移，不是乾淨重建。

## 重複選擇器清單
- `:root`（2 次）
- `.tac-ds-panel`（2 次）
- `.tac-ds-panel--tabbed`（2 次）
- `.tac-ds-panel > .title`（2 次）
- `.tac-ds-panel > .title small`（2 次）
- `.tac-ds-panel > .tac-section-heading h2`（2 次）
- `.tac-ds-tabs`（2 次）
- `.tac-ds-tabs__tab`（3 次）
- `.tac-tabset .tac-ds-tabs .tac-ds-tabs__tab`（4 次）
- `.tac-tabset[aria-label="產業債匯商品"] .tac-ds-tabs--industry`（2 次）
- `.tac-ds-empty`（2 次）
- `.tac-ds-panel, .tac-ds-panel--tabbed, .tac-ds-panel--calendar, .tac-ds-panel--earnings-health, .tac-ds-panel--fed, .tac-ds-panel--focus`（2 次）
- `.tac-ds-disclosure--source`（2 次）
- `.tac-ds-disclosure--source > summary`（2 次）
- `.tac-ds-panel--tabbed .tac-ds-card--news`（2 次）
- `.tac-ds-panel--tabbed .tac-ds-card--news h3`（2 次）
- `.tac-ds-panel--tabbed .tac-ds-card--news p`（2 次）
- `.tac-ds-panel--tabbed .tac-ds-card--news .newsmeta`（2 次）
- `#calendar details.tac-ds-event, #last-week-calendar details.tac-ds-event, #earnings details.tac-ds-event, #last-week-earnings details.tac-ds-event`（2 次）
- `#calendar details.tac-ds-event > summary, #last-week-calendar details.tac-ds-event > summary, #earnings details.tac-ds-event > summary, #last-week-earnings details.tac-ds-event > summary`（2 次）
- `#earnings details.tac-ds-earnings-card, #last-week-earnings details.tac-ds-earnings-card`（2 次）
- `#earnings details.tac-ds-earnings-card > summary, #last-week-earnings details.tac-ds-earnings-card > summary`（2 次）
- `#industry-bonds-fx-commodities .sector-collapse .tac-ds-data-row--sector`（2 次）
- `#industry-bonds-fx-commodities .sector-collapse .tac-ds-data-row--sector .sector-label b`（2 次）
- `#industry-bonds-fx-commodities .sector-collapse .tac-ds-data-row--sector .sector-label small`（2 次）
- `#industry-bonds-fx-commodities .sector-collapse .tac-ds-data-row--sector .r`（2 次）
- `#industry-bonds-fx-commodities .sector-collapse .sector-row.tac-ds-data-row--sector`（2 次）
- `#industry-bonds-fx-commodities .sector-collapse .sector-row.tac-ds-data-row--sector .sector-label b`（2 次）
- `#industry-bonds-fx-commodities .sector-collapse .sector-row.tac-ds-data-row--sector .r`（2 次）
- `#last-week-earnings .tac-ds-earnings-actual-card`（2 次）
- `#last-week-earnings .tac-ds-earnings-actual-card .earnings-actual-card-title`（2 次）
- `#last-week-earnings .tac-ds-earnings-actual-card .earnings-actual-line`（2 次）
- `#last-week-earnings .tac-ds-earnings-actual-card .earnings-actual-line span`（2 次）
- `#last-week-earnings .tac-ds-earnings-actual-card .earnings-actual-line strong`（2 次）
- `#last-week-earnings .tac-ds-earnings-actual-card .earnings-actual-status`（2 次）
- `#sentiment.tac-ds-panel--sentiment`（2 次）
- `html`（2 次）
- `#news-scan .tac-tabset .tac-ds-tabs .tac-ds-tabs__tab`（2 次）
- `.tac-tabset .tac-tab-nav`（2 次）
- `.tac-tabset .tac-tab-nav label`（2 次）
- `#industry-bonds-fx-commodities #bonds .row b, #industry-bonds-fx-commodities .row .instrument-name, #industry-bonds-fx-commodities .row b.instrument-name`（2 次）
- `#news-scan .newsitem`（2 次）

## 重構交付規則
1. 不直接整批刪除舊 CSS；先確認 DOM、互動腳本及響應式依賴。
2. 新元件採 tokens、layout、components、utilities 分層；同一元件只有一套正式定義，差異用明確 modifier/variant 表達。
3. 不以末尾追加單頁覆蓋規則作為常規修復；若確需例外，必須有理由與對應測試。
4. 每次遷移前後都測 1440px、390px、320px：計算樣式、互動、溢出、缺失/重複 ID、瀏覽器錯誤。
5. 只有新規則接管且回歸測試通過後，才刪除對應舊規則。
6. 任一測試 assertion error 都必須讓 workflow 失敗；不能只看 GitHub 綠色狀態。

## 遷移順序
1. Tokens、面板、標題、頁籤基礎元件。
2. 新聞卡與來源 disclosure。
3. 經濟與財報行事曆、五星標記。
4. 全球市場與產業/債匯商品資料列。
5. 情緒指標、實際財報卡、窄螢幕樣式。
6. 每組完成後刪除已被接管的 legacy 規則並跑完整回歸。

本文件是實際稽核基線；列出的遷移工作尚未宣告完成。
