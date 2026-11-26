# HANDOFF CONTRACT v1.1

Every stage handoff is scoped to one run_id and report_date and includes schema_version, stage, created_at with timezone, input_refs and SHA-256, output_refs and SHA-256, status_summary, unresolved_items, warnings and consumer_notes.

Stage 1 passes report date, trading date, selected mother template, exact SHA, Manifest and read-only calendar commit/weekly JSON SHAs.
Stage 2 passes frozen 44-item market snapshot, per-field observations, screenshot/browser provenance, source manifest, metadata audit and receipt SHA. No downstream stage may mutate or re-fetch locked quotes.
Stage 3 passes calendar/earnings projection and source references; source weekly JSON remains read-only.
Stage 4 passes five/ten news items, three summary points, five ordered analysis layers, six-domain political scan and evidence.
Stage 5 passes HTML bytes, HTML SHA-256, render manifest, QA sidecar and complete input receipt.
Stage 6 passes main preview three-file delivery, remote Git blob SHA checks, Pages workflow result and public URL verification.

On receive, validate run_id, report_date, schema, SHA and required fields. Never use a same-named artifact from a different run. Preserve uncertainty; downstream consumers cannot promote PENDING/MISSING/TOOL_READ_FAILURE to verified.
