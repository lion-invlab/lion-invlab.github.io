# TAC Chart 2｜股債相對估值｜設計與資料規格

- 專案：TAC 互動式圖表
- 正式工作分支：`main`
- 本文件狀態：設計規格基準（尚非已發布圖表）
- 建立日期：2026-11-15
- 目標路徑：`research/tac-chart2/`
- 對外入口：既有 `interactive-charts/index.html`；只有完成資料與 QA 後才新增上架卡片
- 保護範圍：不修改 `index.html`、既有 Chart 3、工具欄入口、其他研究頁或排程

## 1. 設計目標與已確認版型

主題：**股債相對估值**。目的在於比較股票盈餘殖利率與美國公債實質殖利率，呈現相對估值環境，不把單一利差包裝成買賣訊號。

採用已確認的 **方案 C：上方投資吸引力儀表板，下方歷史走勢圖**。頁面使用 TAC 現有互動圖表的字體、留白、卡片、標題層級及工具欄導覽慣例；不複製 Chart 3 程式碼，也不修改 Chart 3。

頁面分成兩個口徑獨立的檢視模式：
1. **長期估值（主視圖）**：Shiller CAPE Earnings Yield 對比 10 年期 TIPS 實質殖利率。
2. **Forward 估值（獨立視圖）**：Fed 公布的 S&P 500 Forward P/E 與 Equity Premium。

不得把兩種模式的數值合併成同一條利差或同一個「總估值分數」。

## 2. 長期估值模組（主視圖）

### 指標與公式

| 欄位 | 定義／公式 | 單位 | 頻率 |
|---|---|---:|---|
| CAPE | Robert Shiller 傳統 Shiller P/E | 倍 | 月 |
| CAPE Earnings Yield | 100 ÷ CAPE | % | 月 |
| 10Y TIPS Real Yield | 美國財政部 10 年期實質殖利率 | % | 日轉月 |
| Equity–Real Yield Spread | CAPE Earnings Yield − 10Y TIPS Real Yield | 百分點（pp） | 月 |

### 日期與頻率規則

- Shiller CAPE 使用官方 XLS 月資料，保留原始月份，不插值。
- Treasury 10Y Real Yield 使用官方 Daily Treasury Real Yield XML。月資料以該月所有可取得交易日觀測值的算術平均計算。
- 只在 CAPE 與 Treasury 月平均均存在的月份計算 spread。
- 完整月份才列入正式歷史比較；尚未結束月份標示「未完成」，不混入完整月份趨勢。
- 兩組來源月份日期需正規化為 YYYY-MM；禁止以資料列位置而非日期進行配對。
- Shiller 2026-10 CAPE = 40.71；CAPE EY = 2.4564%（顯示 2.46%）。
- Treasury 2026-10 10Y TIPS 月平均 = 2.7824%（顯示 2.78%）。
- 2026-10 spread = -0.3260 pp（顯示 -0.33 pp）。此值只作為來源與計算核對基準；正式顯示前仍須由本專案資料管線重算並留存驗證紀錄。

### 歷史覆蓋

- Shiller 原始月資料：1871-01 至 2026-10；CAPE 有效值：1881-01 至 2026-10。
- Treasury 10Y TIPS Real Yield：官方歷史序列約自 2003 年起。
- CAPE 與 CAPE EY 長期走勢可展示 Shiller 有效歷史；CAPE EY 與 TIPS spread 僅從兩來源共同有效的月份開始。
- 圖表必須明確標示共同歷史起點，不得將較早的 CAPE 歷史誤畫成已有 TIPS 對照值。

### 不可混用欄位

- 主線只用傳統 CAPE；TR CAPE 可作輔助資料，不得與傳統 CAPE 混算。
- Shiller XLS 的 Excess CAPE Yield 欄位定義尚未完成獨立核實，不得當作 CAPE Earnings Yield 或本模組 spread。
- DGS10 名目殖利率、T10YIE 通膨補償及 DFII10 不可互相冒充；本模組使用 Treasury 官方 10Y TIPS Real Yield。

## 3. Forward 估值模組（獨立視圖）

### 指標

- Fed Forward P/E：Fed Financial Stability Report 附錄公布的 S&P 500 aggregate forward P/E 月末序列。
- Fed Equity Premium：Fed 定義為 aggregate forward E/P 減去 expected real Treasury yield。
- Fed expected real Treasury yield 依 10 年期 CPI 通膨預測及平滑名目殖利率曲線估計；不可用 DGS10 或 DFII10 直接代替。

### 資料版本與現況

- Forward P/E 與 Equity Premium 以 Fed 每次發布的表格／報告版本為獨立 vintage 保存；不得覆寫舊報告版本。
- 2026-05 可讀表格：Forward P/E 覆蓋 1990-01 至 2026-04；Equity Premium 覆蓋 1991-10 至 2026-04。
- Fed 2026-11 報告於 2026-11-13 發布，資料截至 2026-10-28；目前可取得 PDF 圖表及定性說明，但沒有可解析的完整數值表。
- 因此儀表板必須區分「最新可核實數值：2026-04」與「最新報告觀察：2026-11 報告／資料截至 2026-10-28」。禁止從 PDF 圖形目測反推數值，也禁止把 2026-04 數字標成 2026-10 最新值。
- 2025-11 與 2026-05 版本的重疊月份確有修訂，Forward P/E 甚至每個重疊月份均有差異；資料層需保存報告發布日、資料截止日、來源 URL、原始檔 SHA-256、欄位定義及覆蓋範圍。

## 4. 儀表板資訊層級

### 長期估值模式

上方主要數字卡：
1. Shiller CAPE（倍）
2. CAPE Earnings Yield（%）
3. 10Y TIPS Real Yield（月平均，%）
4. CAPE EY − 10Y TIPS Real Yield（pp）

儀表板需同時顯示資料月份、兩來源最後更新／擷取時間及共同歷史起點。spread 小於零時只描述「CAPE 盈餘殖利率低於 10 年期 TIPS 實質殖利率」；不直接宣告股票必然高估或應賣出。

### Forward 估值模式

上方數字卡：
1. Forward P/E（倍）
2. Forward Earnings Yield（由 1 / Forward P/E 計算，若 Fed 表格定義及精度允許）
3. Fed Equity Premium（pp）
4. 最新可核實月份與 Fed 報告版本

若 Forward Earnings Yield 不是 Fed 原表獨立欄位，必須標示為本專案依 Forward P/E 倒數換算，不能冒稱 Fed 官方另行發布值。不得自行反推 Fed Expected Real Yield 作為官方觀測值。

## 5. 下方歷史互動圖

- 長期估值主圖：CAPE Earnings Yield 與 10Y TIPS Real Yield 雙線；可切換顯示 spread。
- Forward 模組：Forward P/E 與 Equity Premium 分開呈現，避免不同單位共用單一縱軸；提供清楚的指標切換或上下分圖。
- 支援時間範圍縮放、拖曳平移、重設全期間；桌面滑鼠與手機觸控均可操作。
- 懸浮提示需顯示實際月份、原始值、單位、來源版本；缺值月份保持缺口，不連線、不補值。
- 軸線依目前可視區間自動調整；不得因縮放造成資料線被裁切或錯誤地把缺值連起來。
- 圖例名稱必須使用完整中文名稱，英文縮寫作輔助，不只顯示代碼。

## 6. 資料保存與版本管理

建議專案資料結構（實際檔案建立前先依現有 repo 慣例核對）：

- `data/tac-chart2/raw/shiller/`：原始官方 XLS 快照。
- `data/tac-chart2/raw/treasury/`：每日 Treasury XML 快照。
- `data/tac-chart2/raw/fed/`：每次 Fed 報告的原始 HTML／PDF／可讀表格。
- `data/tac-chart2/normalized/`：標準化月資料及各版本資料集。
- `data/tac-chart2/manifest.json`：來源 URL、抓取時間、SHA-256、觀測涵蓋、欄位、版本、缺值與修訂資訊。
- `research/tac-chart2/`：圖表 HTML、資料處理程式、QA、決策紀錄。

規則：
- 原始來源快照不可覆寫；每次擷取新增版本。
- 正規化資料可重建，但需保留來源快照與處理程式版本。
- 月資料不得填補缺值；所有計算保留未四捨五入精度，僅顯示層格式化。
- 同一月份的來源修訂要記錄版本差異，不靜默覆寫既有 vintage。
- 來源失敗時保留 last-good 資料，並在頁面標明資料截止日，不得清空圖表或偽造最新值。

## 7. 驗收 Gate（開發前即固定）

### 資料 Gate
- Shiller 月份唯一、遞增、無重複；日期解析需通過 1871.1 等非直觀日期格式測試。
- CAPE 有效起點、最後月份與官方原始檔一致；CAPE EY 逐筆等於 100 / CAPE（容許浮點精度誤差）。
- Treasury 日資料日期唯一、數值與官方 XML 一致；月平均可由每日列獨立重算。
- Spread 只在兩端都有值時計算，且逐月等於 CAPE EY − Treasury monthly mean。
- Fed 每個 vintage 的資料筆數、起訖月份、報告發布日、資料截止日均正確；修訂比較不得覆寫舊版。
- 2026-10 基準核對：CAPE 40.71、CAPE EY 2.4564%、TIPS 月均 2.7824%、spread -0.3260 pp。

### 功能 Gate
- 時間縮放、拖曳、重設、hover、指標切換及手機觸控皆實測。
- 缺值不插值、不前值填補、不跨缺口連線。
- 雙單位圖表不共用誤導性軸線。
- 重新載入頁面後資料及互動正常，不依賴本機快取或開發環境路徑。

### 視覺與相容性 Gate
- 以現有 TAC Chart 3 已發布頁面作視覺參考，不複製其資料／程式實作。
- 桌面、平板、手機至少各一個標準視窗實測；手機基準寬度 360px。
- 檢查標題、儀表板卡片、圖表、圖例、資料註記、來源區無重疊、截斷或橫向溢出。
- GitHub Pages 以 main 實際 URL 載入驗收，不以 GitHub 原始碼存在或 Actions 成功代替瀏覽器驗收。

### 發布 Gate
- 圖表本體先在 main 專屬路徑完成；資料 Gate、功能 Gate、視覺 Gate 全數通過後，才更新 `interactive-charts/index.html` 上架卡片及 README。
- 不修改首頁 `index.html`、既有 Chart 3 或工具欄入口。
- 每次寫入後回讀同一路徑，核對內容、SHA、差異及保護檔案未變更。

## 8. 本階段結論與尚未開始項目

已完成：來源策略、資料頻率、日期配對、公式、歷史覆蓋、Fed vintage 修訂限制、儀表板資訊層級、互動規格及驗收 Gate。

尚未完成：資料快照正式入庫、標準化資料產生、資料處理程式、Chart 2 HTML、瀏覽器 QA、Pages URL 驗收及索引上架。

本文件是 Chart 2 的 main 分支設計基準；不得把規格完成誤報為圖表完成。