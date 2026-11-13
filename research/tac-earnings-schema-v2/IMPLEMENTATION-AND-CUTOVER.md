# TAC 已公布財報小卡｜Schema v2 切換實作與驗收紀錄

日期：2026-11-13
狀態：乾淨 cutover branch；CI 已通過；尚未部署 main。

## 1. 分支隔離

- Base branch：`main`
- Base HEAD：`d271d1226ba1c19b431118c9967d57d2bce678fa`
- Branch：`earnings-schema-v2-cutover-2026-11-13`
- 相對 main：8 個核心實作檔案（含 CI workflow），另有 1 份切換說明；只新增、不修改現有正式檔案。
- 本分支不含 simulation branch 的 WR、W46 JSON、preview、Chart 3 或其他工作內容。
- main 沒有被本次工作修改；沒有 PR、merge、正式 JSON 寫入或排程啟用。

## 2. 實作檔案

- `schemas/tac-earnings-record-v2.schema.json`：EPS／Revenue v2 record schema。
- `scripts/tac_earnings_judgment.py`：唯一 EPS／Revenue 判讀引擎及保守 v1 migration adapter。
- `scripts/tac_earnings_render.py`：HTML 狀態讀取與評論方向性防矛盾 adapter。
- `scripts/validate_tac_earnings_v2.py`：JSON Schema + engine consistency validator。
- `scripts/preview_tac_earnings_v2_migration.py`：W45/W46 純記憶體遷移試算及 CSV export；不寫回來源 JSON。
- `scripts/test_tac_earnings_judgment.py`、`scripts/test_tac_earnings_render.py`：判讀與評論回歸測試。
- `.github/workflows/tac-earnings-schema-v2.yml`：隔離 CI。

## 3. CI 驗收

<badge>PASS</badge>

- Workflow run：`43381382184`
- Job：`131739688442`
- Commit：`57bd9b4cd44111b5cba41f90d98f198399f5ed9d`
- Conclusion：success
- 測試通過：
  - EPS／Revenue basis、currency、period、unit、source、consensus conflict、negative EPS。
  - renderer 僅讀取 versioned judgment。
  - commentary 不得在 Pending／Incomparable 時宣稱 Beat／Miss；不得與方向性狀態相反。
  - JSON Schema directional evidence gate。
  - stored status 必須與 engine 即時計算一致。
  - legacy v1 record 不冒充 v2。

## 4. W45／W46 真實資料遷移試算

使用 main branch 原始週檔，只在記憶體轉換；`source_records_unchanged=true`。

| 週檔 | 已公布財報 | EPS Beat | EPS Miss | EPS Incomparable | EPS Pending | Revenue Beat | Revenue Pending |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-W45 | 41 | 0 | 0 | 0 | 41 | 0 | 41 |
| 2026-W46 | 42 | 11 | 1 | 3 | 27 | 2 | 40 |
| 合計 | 83 | 11 | 1 | 3 | 68 | 2 | 81 |

W46 細節：
- EPS 可保留方向性結果 12 筆；3 筆因 actual／estimate basis 不一致列 Incomparable。
- Revenue 只有 CEG、MNDY 兩筆具備可接受的比較口徑；其餘 40 筆 Pending。
- Pending 是證據不足，不是判定財報表現差；不得把舊 Beat／Miss 沿用成新規則結論。
- W45 41 筆全部 Pending，反映舊資料未具備足夠 basis／source evidence，需逐筆補證據後再判讀。

CI run 同時確認原始週檔沒有被遷移函式修改。

## 5. 責任邊界

- **唯一判讀者：** `tac_earnings_judgment.py`。
- **資料庫：** 保存來源、原始 basis 描述、標準化欄位及 engine 結果。
- **HTML renderer：** 只讀取 versioned status；自由文字評論必須通過一致性 guard。
- **GitHub Actions：** 可執行 validator／engine／migration preview；本 branch workflow 目前只測試，不寫正式 JSON。
- **04:35 ChatGPT automation：** 已保存 Schema v2 fail-closed prompt，但目前 disabled。它尚未證明可直接執行 GitHub Python 程式；不能僅靠 prompt 宣稱已呼叫引擎。

## 6. 正式切換尚缺的 Gate

1. 確認唯一 04:35 writer 的實際執行架構：由 automation 呼叫可執行的 GitHub Action，或把唯一 writer 正式遷移至 GitHub Actions。不可同時存在兩個 JSON writer。
2. 把資料擷取／標準化／判讀／驗證／原子寫入整合為同一條正式 writer；確認來源更新不會覆蓋既有已核實欄位。
3. 完成 W45/W46 逐筆遷移資料補證；尤其 81 筆 Revenue Pending 不可直接轉成方向性結果。
4. 將 HTML commentary guard 接入正式早報組裝流程；目前 main 沒有對應的正式 assembler Python entry point，simulation builder 不能冒充 production integration。
5. 以 main-based clean branch 完成 PR review；正式 main 只在審核通過後部署。
6. 完成隔日增量更新演練、JSON schema validation、回讀 SHA、05:25 唯讀檢查。
7. 經使用者明確核准後才恢復 04:35 automation。

## 7. 明確禁止

- 不直接合併原 simulation branch（其與 main diverged，包含大量其他工作）。
- 不在 v2 writer 尚未就緒前把 main W45/W46 的 `schema_version` 改成 2。
- 不把 migration preview 寫回正式 JSON。
- 不重新啟用 04:35 automation。
- 不把隔離 CI PASS 說成 production ready。

## 8. 可逐筆查核的遷移 CSV

- 最新 CI run：`43381589178`（commit `35f22630de954bbc054f7fa087e97140817aea34`），completed/success。
- Artifact：`tac-earnings-v2-migration-preview`，ID `14017365190`，SHA-256 `14f132fb16ad00aa247e7ba87b2d61a25acad552d7bea9ba85d18216257354fa`。
- CSV 含 W45/W46 共 83 筆公司逐筆資料：舊狀態、新狀態、EPS／Revenue 比較原因及 basis code。
- 已下載並檢查 CSV：83 rows；W45 41、W46 42；與 CI log 的統計一致。
- CSV 是純遷移預覽，不是正式 JSON 寫入結果。
