# DATA SCHEMA v1.1

All stage artifacts are scoped to one Run ID and report date. Times use ISO-8601 with explicit timezone; report timezone is Asia/Taipei. Null is null, never zero.

## Stage 2 market fixture
The exact 44 item IDs and order are derived from the selected SIM-1.4 mother template and production Manifest; no parallel hand-maintained list may diverge. Count groups: 17 global indices (SOX included), 11 sector ETFs, 3 Treasury yields, 6 FX, 4 commodities, 3 risk/sentiment indicators (VIX, MOVE, CNN Fear & Greed). FedWatch is independent.

Each row records item_id, instrument_identity, source_url, quote_type, unit, trading_date, report_date, required fields, value, change, change_percent, status, input_method, source_role, observed_at, observation_record_sha256, evidence_path, evidence_sha256, locked and notes. For screenshot evidence, each field records USER_PROVIDED_SCREENSHOT and its own evidence path/hash/received_at; browser-read fields record INVESTING_HISTORICAL_PAGE and actual browser observation. Mixed-source rows preserve field-level provenance.

The per-run fixture is blank-first: clear all prior close/change/score/OHLC/observations/screenshots/evidence hashes/timestamps and any embedded old quote values, while retaining identifiers, URLs, schema, date metadata and non-market content. Apply only current-run evidence. Never commit the daily populated fixture as a reusable baseline.

## Stage 2 receipt
Bind report_date, trading_date, workflow_run_id, attempt, commit SHA, batch_id, 44-row identity set, status counts, fixture SHA-256, observation bundle SHA-256, 44-row source manifest SHA-256, metadata audit SHA-256 and per-row observation record hashes. Counts must account for all 44 rows. Receipt freezes the snapshot; Stages 3–6 are read-only.

## FedWatch
Independent object: observed_at, meeting_date, current_target_range, outcomes/rate ranges/probabilities, source URL/name, status, evidence. Validate probabilities and rendered values together; do not infer probabilities from stale data.

## Calendar
Read-only projection from `data/calendar/weeks/YYYY-Www.json`; preserve original event IDs, local date/time/timezone, country/company, category, actual, consensus, status, impact/rating and source references. Stage 3 never writes the source JSON.

## News and analysis
Five Global Focus News and ten Market Hot Headlines. Each item includes canonical URL, publisher, published_at, timezone, observed_at, summary and status. Analysis contains summary_points (exactly three), market_analysis keys political, policy_industry, macro, markets, strategy, each with non-empty paragraphs and source evidence, plus six-domain political_scan and concise market observation. Source evidence remains in internal data; summary and five-layer visible slots do not render source lists.

## Builder and delivery provenance
Render manifest binds all input SHAs, mother path/blob SHA, Manifest SHA, QA contract SHA, Builder SHA, report_date, Run ID, output HTML SHA-256 and QA results. Delivery receipt binds HTML/QA Git blob SHA and SHA-256, main commit, Pages deployment and public URL verification.

## Screenshot sidecar
The exact parser contract is `production/input/market-screenshot-observations.schema.json`. Root keys: report_date, trading_date, observations. Each observation keys: group, name, data_date, source_url, instrument_identity, fields. Each field key is one of close/change/open/high/low/score/band and its object carries value, field_name, evidence_path, evidence_sha256, captured_at and optional quote_timestamp. The original image must be stored under `production/input/screenshots/YYYY-MM-DD/`; parser recomputes the hash and requires the fixture source URL and trading date to match exactly.
