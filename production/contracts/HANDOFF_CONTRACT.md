# HANDOFF CONTRACT v1.2

Every stage handoff is scoped to one immutable `run_id` and `report_date`, and includes schema_version, stage, created_at with timezone, input_refs and SHA-256, output_refs and SHA-256, status_summary, unresolved_items, warnings and consumer_notes. A date match alone never establishes identity.

## Stage 1 → ChatGPT Stage 2

Stage 1 creates exactly one Run directory at `production/runs/<run_id>/` and writes:
- `run-context.json`
- `report-data.json` (blank-first 44-row fixture)
- `stage1-receipt.json`

The Stage 1 receipt records the SHA-256 of the exact Run context and fixture bytes. ChatGPT must read these exact Run-local inputs; it must not select a Run by report date or "latest" timestamp.

## ChatGPT Stage 2 input package

ChatGPT writes the following files into that same Run directory:
- `market-history-web-observations.json` (exactly 44 rows)
- `cnn-fear-greed-observation.json` (only when an official CNN observation exists)
- `market-screenshot-observations.json` and original screenshot bytes (only when screenshot inputs exist)
- `stage2-chatgpt-handoff.json` (the package manifest)

The handoff manifest binds `run_id`, `report_date`, `trading_date`, `stage1_receipt_sha256`, `run_context_sha256`, `stage1_fixture_sha256`, capture timestamp, fixed Run-local filenames and SHA-256 for every observation/sidecar file, plus a SHA-256 inventory for every original screenshot byte file. All three Stage 1 identity hashes are recalculated from the actual Run-local bytes by the receiver; values copied from another Run are rejected.

The market observation file must match the approved schema, contain exactly 44 unique instrument identities, and every row's target_date must equal this Run's trading_date. CNN and screenshot evidence must carry the same Run dates. Screenshot evidence bytes must exist inside the Run directory and match their declared SHA-256.

## Stage 2 Complete marker and receiver

ChatGPT may commit the completed Run directory only after writing all files and reading them back to verify their SHA-256. The commit message must contain exactly one marker of the form `[stage2-complete:<run_id>]`.

The Main receiver accepts only the exact Run ID in that marker, validates the Stage 1 receipt/context/fixture hashes and all bundle hashes, then writes a Run-local acknowledgement receipt. It must not search by report_date, choose the newest Run, or accept files from another Run. A duplicate handoff for the same Run is idempotent only when every input SHA is identical; changed bytes require rejection.

## Stage 2 Runner boundary

After the handoff is acknowledged, the Runner performs deterministic schema, identity, date, source, row-count, field, screenshot-byte and SHA checks; populates the blank fixture; freezes the market snapshot; and creates manifest, audit, receipt and S&P 500 Chart 3 handoff. It does not browse market pages or substitute sources. Missing bundle, missing file, malformed SHA, wrong Run/date, stale package, or any byte mismatch fails closed.

## Stage 2 partial recovery

A PARTIAL bundle remains attached to the original Run. Locked VERIFIED rows and their evidence hashes are immutable. ChatGPT may submit a revision that changes only unresolved rows; the receiver compares the prior acknowledgement and row-level hashes, rejects any changed locked row, and records a new handoff revision under the same Run. No new Run and no cross-Run observation reuse are permitted.

## Stage 3 → Stage 6

Stage 2 passes frozen 44-item market snapshot, per-field observations, screenshot/browser provenance, source manifest, metadata audit and receipt SHA. No downstream stage may mutate or re-fetch locked quotes.

Stage 3 passes calendar/earnings projection and source references; source weekly JSON remains read-only.

Stage 4 passes five/ten news items, three summary points, five ordered analysis layers, six-domain political scan and evidence. Editorial JSON is stored in the same Run and binds the market snapshot and research bundle SHA.

Stage 5 passes HTML bytes, HTML SHA-256, render manifest, QA sidecar and complete input receipt.

Stage 6 passes main preview three-file delivery, remote Git blob SHA checks, Pages workflow result and public URL verification.

On every receive, validate run_id, report_date, trading_date, schema, SHA and required fields. Never use a same-named artifact from a different Run. Preserve uncertainty; downstream consumers cannot promote PENDING/MISSING/TOOL_READ_FAILURE to verified.
