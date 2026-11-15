# TAC Chart 2｜資料基準 QA

執行日期：2026-11-15
分支：main

## 結果

| Gate | 結果 | 驗證 |
|---|---|---|
| Shiller 月份唯一性 | PASS | 1,870 筆，1871-01 至 2026-10，無重複月份 |
| Shiller CAPE 有效區間 | PASS | 1,750 筆，1881-01 至 2026-10 |
| Shiller 日期解析 | PASS | .01-.09 為 1-9 月；.1/.11/.12 為 10/11/12 月 |
| Treasury 日資料唯一性 | PASS | 5,971 筆，2003-01-02 至 2026-11-13，無重複日期 |
| Treasury 月資料 | PASS | 287 個月有日資料；完整 CAPE 對照月份 286 個，止於 2026-10 |
| 長期估值計算 | PASS | 286 筆；spread 逐月依 CAPE EY 減 Treasury 月平均計算 |
| Fed 2025-11 vintage | PASS | Forward P/E 442 筆；Equity Premium 409 筆 |
| Fed 2026-05 vintage | PASS | Forward P/E 436 筆；Equity Premium 415 筆 |
| Fed 修訂保留 | PASS | 兩版本獨立存檔，沒有覆寫 |
| 最新 Fed 數值限制 | PASS | 2026-11 PDF 沒有可解析 numeric accessibility table；數值最新仍標示 2026-04 |

## 長期估值基準核對

2026-10：
- Shiller CAPE：40.71
- CAPE Earnings Yield：100 / 40.71 = 2.45639892%
- Treasury 10Y TIPS Real Yield 月平均：2.78238095%（21 個交易日）
- Equity–Real Yield Spread：-0.32598203 pp

以上數字由已提交 CSV 獨立重算；頁面顯示可四捨五入為 40.71、2.46%、2.78%、-0.33 pp。

## Fed vintage 修訂比較

| 指標 | 重疊月份 | 有修訂月份 | 平均絕對修訂 | 最大絕對修訂 |
|---|---:|---:|---:|---:|
| Forward P/E | 430 | 430 | 0.269583 倍 | 1.199242 倍 |
| Equity Premium | 409 | 323 | 0.000210 pp | 0.070872 pp |

## 限制與注意事項

1. Shiller Excess CAPE Yield 不作為 CAPE Earnings Yield 或本專案 spread。
2. TR CAPE 不與傳統 CAPE 混用。
3. Treasury 2026-11 是未完成月份；不納入完整月比較。
4. Fed 2026-11 報告的資料截止日為 2026-10-28，但沒有可直接使用的數值表；不可從圖形目測反推數值。
5. Treasury 原始 XML 可由官方年度 URL 重建；本次已提交標準化日資料，未另存每份 XML 原始檔。
6. 此 QA 只代表資料基準 Gate；圖表功能、瀏覽器視覺與 GitHub Pages 上線 Gate 尚未執行。


## Chart 頁面與瀏覽器 QA（2026-11-15）

- 預覽頁：`research/tac-chart2/chart2-preview.html`
- GitHub Pages：`https://lion-invlab.github.io/research/tac-chart2/chart2-preview.html`
- Browser QA workflow：`TAC Chart 2 browser QA`
- 最終測試 commit：`d308107445f7ba7565c44b5831378c23be9fd9ef`
- Workflow run：`https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/43716584525`
- 結果：**PASS，98 項檢查全部通過**
- 視窗：桌面 1440px、手機 390px、窄螢幕 320px
- 檢查：資料載入、四項長期估值 KPI、286 筆共同歷史、1,750 筆 Shiller CAPE 長期歷史、殖利率／利差切換、Fed 兩個 vintage 切換、Forward P/E 與 Equity Premium 圖、頁面橫向溢出、SVG 寬度、來源註記。
- 互動：滑鼠滾輪縮放通過（286 個月縮至 229 個月）；水平拖曳平移通過（視窗末端由 2026-10 移至 2024-12）。
- Console errors：0；page errors：0；failed requests：0。
- QA 截圖與 report.json 已上傳為 GitHub Actions artifact，artifact SHA-256：`8e1aa827688bc12c214bbcf31cc49a60b706faf40352c956d2627ddf0c259888`。

此 Gate 代表目前 Chart 2 預覽頁在三種視窗下的瀏覽器功能與版面測試通過；尚未代表已加入互動式圖表正式索引或完成使用者視覺驗收。
