# TAC SIM-1.4｜雙母版 Build 驗證請求

本檔只記錄 simulation 分支的驗證請求，不是早報資料來源，不納入 Builder／規則／QA Contract SHA。

## 2026-11-23（一）Monday fixture

- Request: 完整 build + QA，僅輸出 simulation preview；不得修改 main/index.html、正式母版或正式行事曆 JSON。
- Candidate Builder: `simulation-lab/runner/build_review_html.py` — `68726bce554ea166bc4bf1f9fa95f28d2fba321b`
- Candidate SIM-1.4 DRAFT: `simulation-lab/TAC_WORK_RULES_SIM_1.4_DRAFT.md` — `ad9fc500d8f0837a8ef29178d811423d2d855db8` (normative text only; historical logs moved to `simulation-lab/analysis/SIM-1.4_DRAFT_HISTORY.md`)
- Candidate QA Contract v1.11 DRAFT: `simulation-lab/baseline/mother-template-qa-contract.md` — `f7c1d065c20d1d6fbc187525dbe98a58295b070f`
- Manifest: `simulation-lab/baseline/mother-template-manifest.json` — `1496a510d144d340c41b642592675233d5bd2917`
- Monday mother: `simulation-lab/baseline/monday-mother-template.html` — `36f29bcb37816348756f9233b60f0429d675a76e`
- Weekday mother: `simulation-lab/baseline/weekday-mother-template.html` — `19e77a2f34f06a0f1a53d1eeaf875ac5e1345b96`
- Expected report date: `2026-11-23`
- Required result: sidecar must record the exact candidate SHA values above; QA_PASSED and review_ready must be reported separately; all remaining data freshness blockers must remain explicit.


## Rebuild after normative draft cleanup

- Request: rerun 2026-11-23 Monday fixture against the streamlined normative SIM-1.4 DRAFT; same Builder, QA Contract v1.11, Manifest and two mother SHAs.
- Frozen SIM-1.4 DRAFT SHA: `ad9fc500d8f0837a8ef29178d811423d2d855db8`.
- No changes to Builder, QA Contract, Manifest or mother templates after this freeze.


## Rebuild after commodity source-only contract cleanup

- Request: rebuild 2026-11-23 Monday fixture with compact mother labels; all full contract codes/months must appear only in collapsed source details.
- Builder SHA: `91bf76d0440a66bf89a0dd0e9059b04003e75f78`.
- Fixture SHA: `8b09e24eb45d33da46981148420234e649d8a634`.
- SIM-1.4 DRAFT SHA: `bcb03f2f1baf624992b654c5557d1d6d90eea2df`.
- QA Contract v1.12 DRAFT SHA: `814c6a247074277703edb95fb6e1dcbd8868fda3`.
- Manifest SHA: `1496a510d144d340c41b642592675233d5bd2917`.
- Monday mother SHA: `36f29bcb37816348756f9233b60f0429d675a76e`.
- Weekday mother SHA: `19e77a2f34f06a0f1a53d1eeaf875ac5e1345b96`.
- Expected report date: `2026-11-23`.
- Required: verify Investing.com direct history-page hrefs; full contract code/month only in collapsed source details; no full contract label in product rows, tab meta or market-reason; source details show exact contract label.
- Required: report `QA_PASSED`, `review_ready`, `data_review_ready`, and SIM-1.4 Builder approval as separate states; simulation branch only.
