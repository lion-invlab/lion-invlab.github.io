# TAC 投資早報｜重要工作紀錄

> 本檔記錄重要決策、正式檔案變更、驗收與部署證據，不保存聊天逐字稿。正式規則以 `TAC_WORK_RULES.md` 為準；跨對話即時狀態以 `TAC_SESSION_STATE.md` 為準。每筆紀錄須區分已完成、待核實及未測試。

## 2026-11-02｜11/02 早報審核、核准發布與 Pages 部署

### 使用者決策
- 使用者審核 2026/11/02（週一）TAC 投資早報預覽版，明確表示「這版可以上傳首頁了」，核准將該版更新至正式首頁。
- 使用者要求總結及「盤面觀察重點／📌評論」不要被報價來源、時間、合約或其他技術口徑說明佔據篇幅；市場分析應聚焦結論、驅動、影響及觀察條件。

### 規則更新
- 更新唯一正式規則 `TAC_WORK_RULES.md`，加入 G1「總結」及 G3「盤面觀察重點與📌評論」的精簡原則：主畫面不展開資料來源、時間、現貨／期貨、合約月份、平台差異及備援方式；必要限制僅作最短提示，完整技術說明放在收折式「資料來源／計算方式」區。
- 規則更新 commit：`df2563b9614c65d1a82ccd677a0ac480b2cc419b`。
- 更新後 WR blob SHA：`95496c71eb6a52ae02422cc5b1747f11947291b9`。

### 11/02 預覽內容修正
- 預覽路徑：`preview/2026-11-02.html`。
- 總結中的 FedWatch 延遲快照描述已精簡，保留 12/09 會議升息一碼機率 69.8% 及「非即時」必要提示；來源時間與技術口徑留在資料來源區。
- USD/TWD 評論移除平台參考價、牌告及定盤口徑的冗長說明。
- 修正總結標題，恢復核准母版原文「總結」，沒有把「盤面觀察重點」錯放在總結標題。
- 預覽文字修正相關 commits：`079a974492bec459130704865ca32f5328f10349`、`255d8e51f4bee574d916c9ba2321cc4fecb20c4d`、`5a124ef393e1d3aacf135992b20d2f65553f3e53`。
- 最後為觸發正式部署驗證，在預覽檔加入不渲染的 HTML 註解；不改變報告視覺或正文。觸發 commit：`b46d50c4ecdd5a1861d5278ace559a292bd6b8d5`。
- 最新預覽 blob SHA：`a206e668944f5c617cc4282516ea53a78b25845e`。

### 正式首頁發布與部署
- 使用者已明確核准該版發布。
- `main/index.html` 已更新為核准預覽版內容；回讀確認首頁 blob SHA 與預覽正文版本相同，SHA：`0802cd3d9d014bc9d31a507562eea5d09b34e561`。
- 發布首頁 commit：`1a5d2b747d19148867f847873dd6598cdbecac09`。
- 初次更新後前台仍顯示舊版，查明原因：既有 `.github/workflows/pages.yml` 透過 `workflow_run` 接續 Structural Gate，且部署條件要求相應 commit 有 dated preview 變更；只更新 `index.html` 不會觸發該驗證／部署鏈。先前 Pages 成功部署發生在首頁更新 commit 之前，因此不能將 GitHub 檔案更新誤報為網站已上線。
- 已以預覽檔不渲染註解觸發既有流程，沒有直接繞過 Gate：
  - Structural Gate run `41381264105`：completed / success；head SHA `b46d50c4ecdd5a1861d5278ace559a292bd6b8d5`。
  - Pages deploy run `41381338839`：completed / success；head SHA 同為 `b46d50c4ecdd5a1861d5278ace559a292bd6b8d5`。
  - Deploy job 的「Verify deployed canonical preview URL」步驟已回報成功。
- 正式網站：https://lion-invlab.github.io/
- 預覽網址：https://lion-invlab.github.io/preview/2026-11-02.html

### 尚未完成／後續修正
- **已完成本次正式首頁更新及 Pages workflow 部署成功確認；**但需持續區分 GitHub Actions deploy success 與使用者裝置快取／瀏覽器顯示，若使用者仍見舊畫面，先強制重新整理或無痕檢查。
- Pages workflow 的正式發布觸發條件仍有結構性缺口：核准後只更新 `index.html` 不會自然觸發部署。需另立最小修正，讓正式首頁發布 commit 在既有驗證與核准閘門下能可靠部署，不應長期依賴預覽檔註解觸發。
- 不得因本次 deploy success 推定所有行情即時性、母版視覺差異及所有互動均已完全驗收；未實測項目仍依 QA 證據如實標示。


## 2026-11-02｜每日產製規格與排程健檢
- 回讀 main 上 WR v4.0、Manifest 及三個現存排程。確認 03:30 行事曆維護排程使用唯一路徑 data/calendar/weeks/YYYY-Www.json，責任限於 JSON 資料庫；05:25 冬令時間排程啟用，指令採用最新 WR、正確 weeks 路徑及 Investing.com Fed Rate Monitor；05:00 夏令時間排程原 prompt 仍含舊版 CME-only FedWatch 規則，與 WR 現行規定不一致。
- 已修正 05:00 排程 prompt：保留 EDT 啟動／EST 停止條件，將資料來源、FedWatch、星等、流程、QA、停止條件及發布閘門統一改為繼承 main 最新 WR，移除舊規格覆蓋風險。排程仍啟用，時間未變。
- WR 更新為 v4.1：明定 03:30 為資料庫唯一例行寫入入口，05:00／05:25 為同一早報流程的季節性入口；排程 prompt 不得另立或複製可能過期的內容規格；兩個早報排程只產出 preview，使用者核准前不得修改 index.html。
- WR v4.1 commit：2e3f6d8fe1ad9cc9da2dd3ab8c1d24e4be6cb6b1；新 blob SHA：78f0ebb13df6df5bf5d4bd2da8ced981fe0afb5c。
- 排程查核限制：05:25 的最新 last_run 記錄為 failed（run id 08392cbd-67e8-832f-a978-963b5c8c5887）；工具回傳的 latest_result 卻屬更早 run id f6f529cd-6410-8331-a946-630b1aceecb6，不能拿舊的路徑錯誤訊息當作這次失敗原因。05:25 排程目前 is_enabled=true，下一次應於 2026-11-03 05:25 Asia/Taipei 執行；失敗根因尚待取得該次執行對話／錯誤細節。
- 05:00 與 05:25 的季節切換依 America/New_York EDT/EST；目前為 EST，11/03 應由 05:25 排程負責。03:30、05:25 均啟用；05:00 在 EST 必須自行 no-op。
- 未修改 Manifest、雙母版、preview、index.html、行事曆 JSON。Pages workflow 正式首頁更新觸發缺口仍是另一項待辦，不屬於排程時間修正。
