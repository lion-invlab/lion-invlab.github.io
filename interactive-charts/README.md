# TAC 互動式圖表

此資料夾存放互動式圖表的對外索引頁與導覽入口。

## 結構原則

- `index.html`：互動式圖表選單，只負責介紹、分類與連結，不複製圖表程式。
- 各圖表的正式研究程式、資料、來源與 QA 紀錄，仍存放於各自的 `research/<project>/` 與 `data/` 專屬目錄。
- 選單項目直接連結到對應的互動 HTML，避免維護兩份圖表版本。
- 新增圖表時，先完成該圖表的資料與 QA，再在 `index.html` 增加卡片；不得以規劃中項目冒充已上架。

## 目前收錄

1. 市場恐慌與金融壓力：`../research/tac-chart3/chart3-preview.html`

## 發布原則

Chart 3 已完成驗收並正式發布於 main。正式入口為 `https://lion-invlab.github.io/interactive-charts/`，圖表本體維護於 `research/tac-chart3/chart3-preview.html`，索引頁僅連結圖表本體，不複製程式。
