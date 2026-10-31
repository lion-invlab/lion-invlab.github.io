# 雙母版 DOM 節點數量盤點 v1

盤點來源為 main 分支正式母版；本文件只記錄結構數量，不代表每日資料已核實。

| 節點類型 | 週一母版 | 週二至週五母版 |
|---|---:|---:|
| 全球焦點新聞 .newsitem | 5 | 5 |
| 市場熱門頭條 .newsitem | 10 | 10 |
| 美國市場行情列 .row | 5 | 5 |
| 亞洲市場行情列 .row | 6 | 6 |
| 歐洲市場行情列 .row | 3 | 3 |
| 產業 ETF .sector-row | 11 | 11 |
| 美債行情列 #bonds > .row | 3 | 3 |
| 外匯行情列 #fx > .row | 6 | 6 |
| 本週經濟事件 .econ-event | 12 | 16 |
| 本週財報卡 .earnings-accordion | 16 | 16 |
| FedWatch 機率卡 .fc-prob | 2 | 2 |
| 上週經濟事件 .econ-event | 3 | 不適用 |
| 上週財報卡 .earnings-accordion | 7 | 不適用 |

## 驗收解讀
- 兩版新聞、全球市場列、11 檔產業 ETF、美債、外匯與 FedWatch 的結構數量一致。
- 本週經濟事件卡數量不同（週一 12、平日 16），因此不得把卡片數量寫死為跨模板共用常數；應按實際母版骨架建立空資料卡或資料插槽。
- 週一版額外有上週經濟 3 卡、上週財報 7 卡；平日版不存在這兩個區塊。
- 本週財報卡兩版均為 16 張；每日資料更新仍須依 WR 保留完整欄位及已完整驗收的小卡。

## 重複 ID 既存項目
原始碼逐字比對確認以下重複 ID 出現在正式母版中：
- 週一：tac-toolbar-bubble-preview-v1 的 style 區塊重複 2 次；tac-toolbar-bubble-preview-v1-js 的 script 區塊重複 2 次。
- 週二至週五：tac-toolbar-bubble-preview-v1-js 的 script 區塊重複 2 次；tac-toolbar-bubble-preview-v1 的 style 區塊目前只見 1 次。
- 本專案只記錄，不在此階段修正；未經使用者批准不得清除或合併。

## 工具限制與下一步
- 本次以移除 style/script 內容後的標籤結構掃描計數，並另行逐字檢查重複 ID 區塊；不是瀏覽器完整 DOM 驗收。
- 下一步需以真正 HTML parser／瀏覽器 DOM 測試驗證 selector 唯一性、父子層級、實際互動與手機版版面。
- 未完成瀏覽器測試前，所有 selector 仍為候選 allowlist，不得啟用自動寫入。