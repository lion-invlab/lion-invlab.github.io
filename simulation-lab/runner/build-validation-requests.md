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
