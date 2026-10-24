# TAC Design System｜元件移轉對照表

狀態：依凍結基準的實際 DOM 與 CSS 選擇器建立；尚未代表每個元件已移轉或通過視覺驗收。

## 1. 主版面外殼

| 主版面 | 現況 DOM | 新元件目標 | 注意事項 |
|---|---|---|---|
| 總結（BLUF） | `article.card.bluf`，標題 `.title` | `.tac-ds-panel.tac-ds-panel--bluf`、`.tac-ds-panel__heading` | 保留酒紅左側識別、摘要階層與評論文字；不可讓 BLUF 被當成一般數據卡 |
| 市場情緒 | `article#sentiment.card` | `.tac-ds-panel.tac-ds-panel--sentiment` | 特殊深色面板、同心圓、玻璃反光與白色標題是專屬變體，不可被白色通用面板覆蓋 |
| 重點新聞掃瞄 | `section#news-scan.tac-tabset` | `.tac-ds-panel.tac-ds-panel--tabbed` | 標題區、活頁導航與內容卡片層級須避免雙重外框 |
| 全球主要股市 | `section#global-markets.tac-tabset` | `.tac-ds-panel.tac-ds-panel--tabbed` | 美洲／亞洲／歐洲共用頁籤；行情列需保留數字右對齊與紅漲綠跌 |
| 產業債匯商品 | `section#industry-bonds-fx-commodities.tac-tabset` | `.tac-ds-panel.tac-ds-panel--tabbed` | 五個活頁的資料結構不同，統一外殼但不可強迫所有資料列相同欄數 |
| 上週經濟行事曆 | `section#last-week-calendar` | `.tac-ds-panel.tac-ds-panel--calendar` | 週一版專屬；保留 details 原生收折 |
| 上週財報行事曆 | `section#last-week-earnings` | `.tac-ds-panel.tac-ds-panel--calendar` | 週一版專屬；EPS／營收卡片的並列與星等需保留 |
| 本週經濟行事曆 | `section#calendar` | `.tac-ds-panel.tac-ds-panel--calendar` | 今日／即將／已公布三狀態；空資料、待核與未公布需區分 |
| 本週財報行事曆 | `section#earnings` | `.tac-ds-panel.tac-ds-panel--calendar` | 與經濟行事曆共用狀態頁籤，但公司資訊卡不可被簡化成經濟事件列 |
| S&P 500 財報健康度 | `section#sp500-earnings-health` | `.tac-ds-panel.tac-ds-panel--earnings-health` | FactSet 快照、核心判讀及指標卡需維持明確層級 |
| Fed 限時動態 | `section#fed.fed-live` | `.tac-ds-panel.tac-ds-panel--fed` | FedWatch 與 FOMC 共用主外殼，兩個子視圖仍保留各自資訊結構 |
| 今日觀察重點 | `section#view.today-focus` | `.tac-ds-panel.tac-ds-panel--focus` | 市場觀點、關鍵價位、核心觀察三頁籤；關鍵價位須保留可掃讀的數值格式 |

## 2. 現有頁籤系統與新共用元件

| 現有結構 | 目前切換機制 | 移轉策略 |
|---|---|---|
| `.tac-tabset / .tac-tab-radio / .tac-tab-nav` | radio checked + label[for]，以 ID 選擇器切換 panel | 先統一視覺層，保留 input ID、name、checked、label for 與 panel 顯示選擇器 |
| `.week-econ-tabs / .week-econ-tab-labels` | radio checked + 三個 status group 的 nth-child | 與財報頁籤共用外觀 tokens；不要改變三組狀態順序 |
| `.week-earnings-tabs / .week-earnings-tab-labels` | radio checked + 三個 status group 的 nth-child | 共用按鈕尺寸與選取狀態，但保留財報卡片的內部欄位 |
| `.fed-live-tabs / .fed-live-tab-labels` | radio checked + watch/FOMC panel selector | 保留雙欄分段控制及窄螢幕字級 |
| `.focus-tabs / .focus-tab-labels` | radio checked + market/levels/core panel selector | 保留三欄切換與手機版窄寬處理 |

## 3. 共用元件 class 契約

- `.tac-ds-panel`：主版面外殼；不應直接套到所有內層卡片。
- `.tac-ds-panel__heading`：主版面標題；紅色標記只能有一個來源，避免重複 pseudo-element。
- `.tac-ds-tabs` / `.tac-ds-tabs__tab`：頁籤導航視覺層；radio 仍為原生可操作控制。
- `.tac-ds-card`：主版面內的內容卡，不取代整個主版面。
- `.tac-ds-disclosure`：收折區，需保留原生 `details/summary`。
- `.tac-ds-data-row`：可共用的行情列；需容許不同欄位模板。
- `.tac-ds-source`：來源與方法說明。
- `.tac-ds-empty`：無資料／尚未公布狀態，不得與「已公布但實際值缺失」混為一談。

## 4. 移轉順序

1. 主版面標題與外殼（先選一般白色面板，避開市場情緒特殊面板）。
2. 一般 radio 頁籤（先 `#global-markets`，再新聞與產業活頁）。
3. 經濟／財報狀態頁籤與收折元件。
4. FedWatch／FOMC 特殊雙頁籤。
5. 今日觀察重點。
6. BLUF 與市場情緒兩個特殊視覺變體。
7. 最後才移除已被替代的 legacy CSS，逐次檢查未使用選擇器。

每一階段先記錄基準畫面、修改差異與互動測試；沒有瀏覽器回歸結果時，只能標示為靜態驗證。
