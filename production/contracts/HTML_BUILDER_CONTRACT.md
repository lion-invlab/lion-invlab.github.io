# HTML BUILDER CONTRACT v1.1

## 唯一母版來源
- Manifest：`production/config/mother-template-manifest.json`。
- Monday：`production/templates/monday-mother-template.html`，SHA `710c944205ee05a86599ef5cd869f26c4a9ebde1`。
- Weekday：`production/templates/weekday-mother-template.html`，SHA `ff051c0cd22cf9267420c41e3952fa3178f0e45d`。
- 以上逐位元承接 SIM-1.4 baseline。不得讀取 main 舊 `母版專區/`、`index.html`、舊 preview 或 history 作母版。
- 詳細 QA：`production/contracts/MOTHER_TEMPLATE_QA.md`。

## Inputs
只接受同一 Run ID 的 Stage 1–4 輸出、PASS pre-build receipt、正式 Manifest 與 QA Contract；先驗證 SHA、Schema、日期與 Run ID。

## DOM 限制
- 依報告日期選擇 Monday／Weekday；週末不自動製作。
- 使用真正 DOM parser；只更新母版核准槽位，不可用 regex／字串切片。
- 不得重建 DOM、注入 CSS／JS、修改 class／ID／屬性／父子結構，或破壞 details、tabs、radio、互動。
- 五層 market-analysis 五個既有 content slots 須完整填入，順序固定；不得塞進總結小卡。
- 總結及五層文章可見區域不得顯示資料來源列／連結／收折區；來源留在 Fixture、Observation、receipt、QA sidecar。
- 商品可見名稱不附合約月份／代碼；完整合約資料留在既有來源說明槽位。
- 漲紅跌綠；不得改變母版色彩規則。

## Output
輸出當次 Run 工作目錄的 review.html、render manifest、QA sidecar。Stage 5 不寫 main/preview、index.html、history、calendar JSON 或母版。HTML 必須完整保留母版 CSS、JS、互動與響應式結構。


## Main Builder owner approval
- The main-path Builder is a distinct candidate even when its SIM-1.4 source Builder was approved.
- `production/config/builder-approval.json` is the sole approval record. `APPROVED_MAIN` and `approved_by_owner: true` are required.
- Approval is bound to the exact `production/runner/build_review_html.py` Git blob SHA. Any Builder change invalidates approval until the exact new blob is approved.
- Stage 5 enforces this record before creating production `REVIEW_READY`. Candidate fixture validation does not confer owner approval.
