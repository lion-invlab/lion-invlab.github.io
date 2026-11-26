# QA CONTRACT v1.1

詳細母版 DOM／互動／視覺檢查只以 `production/contracts/MOTHER_TEMPLATE_QA.md` 為準，不另建第二份競爭清單。

## 四類必要 QA
1. Data/content：44 固定行情逐項有值或明確狀態；截圖／瀏覽器來源逐欄記錄；日期、標的、口徑及顯示值與 Stage 2 凍結收據一致；FedWatch 獨立且機率一致；行事曆／財報實際值與共識有證據；新聞時間窗與數量符合；五層分析完整；未核實值不得作事實。
2. Structural：星期母版與 SHA 正確；必要 DOM 槽位存在；ID 唯一；無未授權 CSS／JS／DOM 改動；週一回顧區塊存在，平日不得出現；固定區塊完整。
3. Visual/interaction：360、390、412、768、1440 px；驗證總結／分析／情緒間距、手機財報雙欄、Fed/FOMC 響應式、tabs、收折、工具欄泡泡及呼吸燈。未執行標 NOT_TESTED。
4. Integration/delivery：同一 Run ID／日期；pre-build receipt PASS／SHA；HTML SHA；QA／delivery provenance；僅三個 preview 日期檔變更；遠端回讀；Pages workflow 成功及公開 URL 實際驗證。

必要失敗不得 REVIEW_READY。非核心行情缺漏可明確呈現並讓無依賴工作繼續，但不得冒充已核實。不得增加重複驗證同一事實的冗餘 Gate。
