# TAC_WORK_RULES.md｜第 26 節修訂草案（v3.13 提案）

- 基準：main 分支正式 WR v3.12（本文件僅為隔離分支審閱草案）
- 範圍：補充第 26 節第五步的 Renderer 動態清單、報告日期欄位、顯示轉換與每日審核版 Orchestrator 契約
- 狀態：待使用者核准；不得視為正式 WR 或發布授權
- 不修改：正式 WR、Manifest、雙母版、正式首頁

## 建議修訂位置

第 26 節「第五步｜母版渲染、資料完整性與視覺品質驗收」第 1 點，在既有 Renderer 權限敘述後增列以下條文：

### 5.1 動態清單與空狀態容器的受控例外

1. 新聞、經濟行事曆及財報行事曆的動態卡片，只能在 Binding Map 明確映射的清單／狀態容器內增刪；卡片必須以同一面板、同一資料類型的核准母版卡片原型複製，不得自行設計或改用其他類型原型。
2. 若核准母版某個 `.calendar-status-group` 只有 Binding Map 指定的空狀態提示（`.calendar-status-empty`），沒有對應清單容器，且本次 Snapshot 該狀態確有一筆以上合格事件，Renderer 得在該狀態群組內，以同一面板既有核准清單容器的標籤／屬性及卡片原型建立清單；建立時僅能替換該群組內的空狀態提示節點。
3. 新清單的容器標籤、class 與卡片完整標記，必須直接複製同一面板中已存在的核准原型；不得新增 CSS、JavaScript、互動、ID、狀態標題或其他外層結構。
4. 若該狀態沒有事件，必須保留原空狀態提示，不得建立空清單，也不得移除或改寫提示文字。
5. 若空狀態提示缺失／重複、清單原型不存在／不唯一、卡片原型無法辨識、原型不屬於同一面板或資料欄位不符合原型，必須 fail closed，停止該份審核版交付；不得猜測、跨面板複製或自行修補版面。
6. 建立清單後，僅可在新清單內按 Snapshot 筆數複製／刪除卡片，並在卡片內依既有欄位契約調整明細列。經濟事件、未公布財報及已公布財報各自使用原本核准的卡片結構；財報 EPS／營收雙實績卡片不得省略或與經濟事件卡片混用。
7. 動態修改完成後，必須驗證：狀態群組數量與順序不變、狀態標題與 tabs 不變、無事件群組保留原提示、有事件群組已移除原提示並只新增一個清單、卡片數量與 Snapshot 相符、所有卡片欄位正確，以及動態群組以外 HTML 原始碼 byte-for-byte 不變。
8. 上述權限僅適用於 Binding Map 明確指定的空狀態選擇器與清單原型；不得推廣為允許 Renderer 任意新增／刪除 DOM 節點。不得修改母版檔、Manifest、CSS、JavaScript、導航、標題、tabs、互動或正式首頁。


### 5.2 報告日期與行情顯示欄位

1. 每份審核版必須由 Snapshot 的 `meta.report_date` 更新 HTML `<title>`、`.report-date` 及 `meta[name="report-date"]`；不得沿用母版示範日期。
2. 頁首 `.status` 日期依母版契約更新：週一版使用報告日期；週二至週五版使用 Snapshot 的交易日期。日期與星期名稱須一致，缺欄位或格式不符即 fail closed。
3. 正規化行情 Snapshot 的數值欄位，必須經明確的 Renderer 顯示轉換器處理後才可寫入 HTML。顯示小數位依資產類型固定；漲跌值必須依來源提供的 `change_unit` 格式化，不得猜測單位。
4. `pending_verification`／`missing` 顯示「待核實」；`market_closed` 顯示「休市」。不得把 null、舊值或推估值轉成看似已核實的報價。
5. 不支援或缺少的單位、非數值的 verified 報價、日期不符、報價口徑不明，均須停止該份審核版，不得自行補值。

### 5.3 FedWatch 顯示安全契約

1. 正規化 FedWatch 的 rate-range 機率陣列，不得僅依陣列順序推定「維持不變」或「升息一碼」。
2. 若 FedWatch 狀態為 `pending_verification`／`missing`，畫面須明確顯示「待核實」，機率條寬度為 0，不得顯示假設機率。
3. 若狀態為 verified，必須提供明確 outcome mapping 的 Renderer payload；每個結果的機率須介於 0–100，總和須為 100（允許既有數值精度誤差），並保留來源與更新時間供稽核。缺少 mapping 或驗證失敗即 fail closed。

### 5.4 每日審核版 Orchestrator 契約

1. Orchestrator 只接受已通過 Snapshot Schema 驗證且含來源、觀測時間、交易日期及報價口徑的行情片段；依報告日期選取核准週一或週二至週五母版。
2. Orchestrator 依 ISO week 讀取本週行事曆資料庫；週一另讀取上一週資料庫。行事曆仍由 Adapter 依母版欄位契約分流及渲染。
3. 新聞與編輯分析必須由本次輸入片段提供，不得複製母版舊新聞或舊分析。全球焦點新聞固定 5 則，市場熱門頭條固定 10 則；資料不足即停止交付，不以舊內容湊數。
4. Orchestrator 只產出 `review/YYYY-MM-DD-review.html` 審核版；若同名檔案已存在不得覆寫。不得更新正式首頁、正式 WR、Manifest 或雙母版。
5. 產出後須完成日期／欄位／來源／行事曆檢查，並以 Chromium 比對核准母版，完成桌機、平板及 320px 手機的版面、水平溢出與互動驗收。任一失敗即停止交付。
6. 只有使用者核准審核版後，才可進入正式首頁更新流程；CI 通過或 Orchestrator 成功，不構成發布授權。

## 建議同步更新 Binding Map 的說明

`rules.dynamic_region_policy` 應明確列出「mapped calendar empty-state placeholders」為受控動態區域；經濟及財報各 panel 應明確映射 `empty_state_selector: ".calendar-status-empty"`。這是程式契約，不代表正式母版內容已變更。

## 驗收邊界

- 本草案不改寫第 26 節六步驟順序，也不放寬第五步的母版結構、功能及視覺驗收。
- 程式單元測試／CI 通過，不等於即時資料來源、新聞、FedWatch 及每日排程已全部完成。
- 目前已具備 review-only Orchestrator 與雙母版瀏覽器視覺回歸；但 Investing.com 全部行情欄位的自動擷取、新聞／分析片段的自動取得、FedWatch verified outcome mapping、每日排程及正式發布授權流程仍須分別完成驗收。
- 視覺回歸需同時比對核准母版與實際當日審核版；不得以單純 HTML 能開啟代替視覺驗收。
- 正式採納本修訂，必須由使用者確認後另行修改 main 分支正式 WR；本草案本身不具規範效力。
