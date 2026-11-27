# RUN CONTRACT v1.1

- report_date and scheduling use Asia/Taipei. Each run has unique run_id, workflow_run_id, attempt, starting commit SHA, MASTER WR SHA, six Stage WR SHAs, contracts SHA, Manifest SHA, selected mother SHA and QA contract SHA.
- One active production run per report_date. Concurrency never cancels or overwrites an active report build. A manual `recover` may create one replacement Run only when the sole prior Run for that date has not reached Stage 5/6 delivery; it records `supersedes_run_id` and preserves the prior Run unchanged. Multiple prior Runs or any delivered preview block automatic supersession.
- Work products and receipts live under `production/runs/<run_id>/`; these are per-run evidence, not a second permanent market/calendar database.
- Mandatory Stage WR preflight: each Stage must read its complete own WR before work; Stage 1 records its own WR SHA evidence and Stage 2–6 compare against the Stage 1 pinned governance blob SHA. Missing, empty, unreadable, unpinned or drifted WR blocks that Stage. Every stage receipt records the `wr_preflight` evidence object.
- Downstream handoffs must verify each required upstream receipt's `wr_preflight` stage key, WR path, Git blob SHA and Stage 1 pinned commit against the same Run governance snapshot. A producer cannot pass a stage onward without valid WR proof.
- Each Stage records status, start/end, inputs, outputs, hashes, warnings, errors, retry count and handoff.
- Reuse output only if run_id, report_date, schema, input hashes and output hash validate. Never reuse old fixture quotes or mix runs.
- Recovery resumes from the last valid stage; do not repeat already locked external reads. Retry only unresolved items or failed stage.
- Overall states: RUNNING, PARTIAL, FAILED, REVIEW_READY, DELIVERED, PUBLISHED. REVIEW_READY means content and required QA passed; DELIVERED means main preview and public Pages URL verified; PUBLISHED requires separate user approval and formal homepage/archive completion.
