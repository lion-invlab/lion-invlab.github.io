# TAC Chart 3｜資料授權與公開展示稽核

稽核日期：2026-11-14  
適用分支：`research/chart3-sp500-integration-20261114`  
狀態：研究分支內部稽核；不是法律意見，也不代表已取得授權。

## 判定原則

- FRED/ALFRED API 可存取，不等於底層資料可任意再散布。
- 以各 FRED series 頁面標示的版權類別及 FRED 現行條款為準。
- 「Copyrighted: Citation Required」與「Copyrighted: Pre-Approval Required」必須區分。
- 公開互動圖表、可下載原始資料、將資料納入公開資料庫，是不同使用方式；不得把其中一種許可推定成其他用途也獲准。
- 未確認前，不公開完整原始序列下載。

## 序列逐項結果

| Series | FRED 頁面版權分類 | 資料來源 | 研究分支處理 |
|---|---|---|---|
| VIXCLS | Copyrighted: Citation Required | Cboe Options Exchange | 需保留 Cboe/FRED 歸屬及來源連結；公開互動展示可依 FRED 條款評估，但不得推定可再散布原始資料 |
| NFCI | Copyrighted: Citation Required | Federal Reserve Bank of Chicago | 需標示 Chicago Fed/FRED；公開互動展示與原始資料再散布分開審查 |
| NFCICREDIT | Copyrighted: Citation Required | Federal Reserve Bank of Chicago | 同 NFCI；並註明為 NFCI 子指數，不可當成獨立第二份風險來源 |
| STLFSI4 | Copyrighted: Citation Required | Federal Reserve Bank of St. Louis | 需標示 St. Louis Fed/FRED；公開互動展示與原始資料再散布分開審查 |
| S&P 500 | Copyrighted: Pre-Approval Required | S&P Dow Jones Indices LLC | 未取得 S&P 書面授權前，不得公開重製指數數值序列或其衍生資料 |

## 官方依據

1. FRED API Terms of Use：第三方資料權利不因 FRED API 存取而被覆蓋；使用者須遵守資料所有人限制。  
   https://fred.stlouisfed.org/docs/api/terms_of_use.html
2. FRED Legal Terms：區分 Pre-Approval Required、Citation Required、Public Domain；Citation Required 的商業展示須符合其歸屬要求及使用限制。  
   https://fred.stlouisfed.org/legal/
3. VIXCLS：Cboe 來源，頁面分類 Copyrighted: Citation Required。  
   https://fred.stlouisfed.org/series/VIXCLS
4. NFCI：Chicago Fed 來源，頁面分類 Copyrighted: Citation Required。  
   https://fred.stlouisfed.org/series/NFCI
5. NFCICREDIT：Chicago Fed 來源，頁面分類 Copyrighted: Citation Required。  
   https://fred.stlouisfed.org/series/NFCICREDIT
6. STLFSI4：St. Louis Fed 來源，頁面分類 Copyrighted: Citation Required。  
   https://fred.stlouisfed.org/series/STLFSI4
7. S&P 500：S&P DJI 來源，頁面分類 Copyrighted: Pre-Approval Required；FRED 頁面明確指出重製須事先取得 S&P 書面許可。  
   https://fred.stlouisfed.org/series/SP500
   https://www.spglobal.com/spdji/en/documents/legal/dow-jones-indexes-terms-conditions.pdf

## S&P 500 歷史資料的額外問題

目前合併資料涵蓋 1927-12-30 至 2026-11-10；來源 metadata 記錄：
- 長歷史 CSV：1927-12-30 至 2019-12-23，23,104 筆。
- FRED 重疊／近期資料：2016-11-11 至 2026-11-10，非空 2,512 筆。
- FRED 與長歷史來源重疊 783 筆，最大差異 1.050048828125 點。
- 原始長歷史 CSV 的提供者／授權文件尚未在本分支 provenance metadata 中完整記錄。

FRED 官方頁面指出，FRED 與 S&P DJI 的協議包含 10 年日資料；這不能作為 1927 年起完整歷史序列的公開授權依據。長歷史 CSV 的來源與使用權必須另行查明。

## 發布閘門

- [ ] S&P DJI 書面授權確認：允許公開展示、保存歷史、計算衍生指標及公開下載（若有）。
- [ ] 1927-2016 長歷史 CSV 的原始來源與授權文件補齊。
- [ ] 四項 FRED 指標確認公開互動圖表的展示方式、歸屬文字及是否允許向訪客提供原始序列下載。
- [ ] 圖表、資料檔、下載檔與截圖均保留必要來源及版權標示。
- [ ] 未獲授權的資料不進入公開 GitHub Pages、公開 JSON 或可下載 artifact。

**目前結論：四項 FRED 指標的頁面分類均為 Citation Required，不能一概說成必須先取得個別書面許可；但 S&P 500 明確屬 Pre-Approval Required，且長歷史資料來源尚未釐清。因此整個五序列公開產品仍未解除發布阻擋。**
