# TAC 投資早報自動化｜實作狀態交接

更新日期：2026-11-02（台灣時間）  
隔離分支：`tac-renderer-safe-refactor-20261102`  
最近完整 CI：Run [41350066261](https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41350066261)  
狀態：Renderer／日曆／Orchestrator 測試通過；完整即時資料自動化尚未完成。

## 已完成且通過測試

1. **Safe Renderer**：以雙母版為來源，依 Binding Map 更新核准欄位；動態卡片只能在映射清單內增刪。
2. **週一空狀態受控擴充**：只在原有 status group 內，以同一 panel 的母版原型建立缺少的清單容器；沒有事件時保留原空狀態。
3. **Calendar Adapter**：讀取 ISO week JSON，依報告日期分流、四／五星篩選、來源欄位、台灣／美東時間與財報 EPS／營收欄位渲染。
4. **Snapshot Composer**：合併經驗證的市場 Snapshot、行事曆 Snapshot 與新聞／分析片段，拒絕 key collision。
5. **市場顯示轉換器**：將 schema 數值格式化為 Renderer 顯示字串；pending/missing 顯示「待核實」，market_closed 顯示「休市」，未知單位 fail closed。
6. **FedWatch primary capture 與安全 mapping**：Investing.com Fed Rate Monitor 已明確標記為 WR 指定優先來源；擷取器記錄來源更新時間、當前目標區間及各會議分布。只有下一場會議恰為「當前區間＋上調 25bp」兩結果時，才映射 hold／one hike；未核實時顯示「待核實」、機率條寬度為 0。CME 不取代 Investing.com。
7. **報告日期欄位**：同步更新 title、`.report-date`、`meta[name="report-date"]`；週一狀態列採報告日期，週二至週五狀態列採交易日期。
8. **市場資料 Bundle Runner**：`scripts/capture_tac_market_bundle.py` 統一執行 17 大指數、11 大產業 ETF、美債 2Y／10Y／30Y、6 組外匯、WTI／Brent、黃金／白銀、VIX／MOVE、CNN Fear & Greed 及 Investing.com Fed Rate Monitor 擷取，輸出可供 Orchestrator 使用的行情片段與 capture manifest；Treasury FRED 備援只填補官方 Treasury 缺漏欄位，不覆蓋已核實官方值。
9. **Review-only Orchestrator**：`scripts/run_tac_daily_pipeline.py` 讀取行情片段、ISO week 行事曆資料庫及新聞／分析片段，使用 Manifest 指定母版，只產出 `review/YYYY-MM-DD-review.html`；同名檔案拒絕覆寫，不部署首頁。
10. **瀏覽器視覺回歸**：Chromium 對週一及平日渲染頁面進行桌機 1440px、平板 768px、手機 320px 檢查；另與核准母版比對區塊幾何、計算樣式、水平溢出及互動。
11. **整合測試**：使用 2026-11-02 週一資料，從市場 Snapshot、W45/W44 行事曆、5 則全球焦點、10 則熱門頭條，成功產出 review HTML；測試確認正式首頁、WR、雙母版檔案未被改動。

## CI 驗收

- [完整 CI Run 41350066261](https://github.com/lion-invlab/lion-invlab.github.io/actions/runs/41350066261)：success。
- `safe-text-patch`：success。
- `browser-visual-regression`：success。
- 六組 viewport 測試通過；兩份母版各自與核准母版比對通過。
- Artifact：`tac-browser-visual-regression`（Run 41350066261）。

## 尚未完成／不可宣稱完成

1. **即時行情完整擷取尚未完成實際 live run**：已建立 Bundle Runner 與各組 collector，涵蓋 17 大指數、11 大產業 ETF、美債 2Y／10Y／30Y、6 組外匯、WTI／Brent、黃金／白銀、VIX／MOVE 及 CNN Fear & Greed；目前 CI 只驗證 parser／來源身分／日期契約的合成測試，尚未在真實截稿時間執行完整 live capture 並逐項核對 Investing.com 頁面回傳內容。
2. **新聞與編輯分析尚非自動取得**：Orchestrator 要求本次輸入 5 則全球焦點、10 則市場熱門頭條及 editorial fragment；不會沿用母版舊內容，但新聞研究與分析尚未接成自動來源管線。
3. **FedWatch verified mapping 需真實頁面驗證**：已改為 Investing.com Fed Rate Monitor primary capture，並建立當前目標區間＋25bp 的嚴格映射；但真實頁面是否提供可辨識的 current target range，仍需 live run 驗證。若標籤無法可靠解析或結果不符合兩種 UI 情境，畫面維持待核實。
4. **新聞／分析及每日排程尚未完成**：Bundle Runner 可產出行情與 FedWatch capture，但新聞 5 則、熱門頭條 10 則及 editorial fragment 尚未接入自動來源管線；每日排程亦未接入完整產製與瀏覽器驗收。
5. **真實當日審核版尚未完成**：CI 用合成行情與測試新聞做結構／視覺測試；不得把測試數值當成真實市場報價。

## 安全邊界

- 所有本輪程式變更留在隔離分支；沒有合併 PR。
- 正式 WR、Manifest、雙母版及首頁沒有修改。
- Orchestrator 不可直接部署 `index.html`。
- 使用者核准前不得修改正式首頁。
- WR v3.13 第 26 節草案位於 `review/WR_v3.13_第26節修訂草案.md`，待使用者審核，不具正式規範效力。

## 建議下一階段順序

1. 完成 FX／能源／貴金屬／VIX／MOVE／CNN Fear & Greed 的 source capture adapters，統一 provenance、data date、observed_at、quote type、fallback 與 pending 規則。
2. 定義並測試 FedWatch verified outcome mapping；未能可靠對應時維持待核實。
3. 將新聞蒐集、時間窗篩選、來源連結及 editorial fragment 接入 pipeline。
4. 將完整資料來源接入 Orchestrator，執行真實資料的完整 review HTML 及當日瀏覽器回歸。
5. 最後才評估每日排程；使用者核准 review 後才允許正式首頁更新。
