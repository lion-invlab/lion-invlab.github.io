# TAC Weekly Calendar Database (prototype)

This directory is the proposed weekly source of truth for economic and earnings calendar events. It is a prototype on a non-production branch; WR v3.8 remains authoritative.

## Lifecycle
1. Monday initializes one ISO week file (e.g. `2026-W45.json`).
2. Tue-Fri performs idempotent upserts by stable event `id`; it must not recreate or duplicate events.
3. Each daily report reads the week file and emits a draft daily snapshot. After review approval, `approve-snapshot` locks the snapshot; a later correction updates the weekly record and audit trail, not an already approved report. `--replace` is permitted only for an explicitly marked draft snapshot.
4. On the next Monday, the prior week remains available as an archive. The previous-week renderer filters to released TAC 5-star events only.
5. Current-week panels retain TAC 4- and 5-star events only. These thresholds mirror WR v3.8; do not reinterpret external 1-3 star ratings as TAC ratings.

## Data contract
- All `event_date` values are ISO-8601 timestamps with an explicit offset; canonical display timezone is `Asia/Taipei`.
- Preserve the source's original timezone/time in event notes or dedicated source fields where available; never invent an unknown release time.
- Preserve actual, forecast, previous, EPS/revenue actual and consensus, basis, comparison status, financial judgment, price reaction, and separate source references.
- Coverage is tracked separately for economic and earnings streams. `incomplete` is a valid state and must remain visible; missing data is not evidence that no events exist.
- `audit` records initialization, upserts, and corrections. Stable IDs are immutable identifiers; changed facts are revisions to the same event.
- W44 is seeded from the 11/02 report's previous-week arrays as an archive candidate. Its incomplete coverage must not be silently promoted to complete.

## Files
- `weeks/2026-W45.json`: current-week seed from 2026-11-02 review content.
- `weeks/2026-W44.json`: prior-week archive candidate.
- `schema/tac-weekly-calendar.schema.json`: structural contract.
- `../../scripts/tac_weekly_calendar_db.py`: stdlib CLI for validate, idempotent upsert, daily snapshot export, explicit snapshot approval, and safe snapshot merge.


## Data integrity rules (prototype hardening)
- Once an event is marked `released`, an upsert cannot silently revert it to `upcoming`; corrections retain the released state and are recorded as revisions.
- If `time_known=false`, any stored clock component is a non-display placeholder only. Renderers must show the date with time pending verification, never display the placeholder as an event time.
- The JSON Schema star range is TAC-specific (4–5), consistent with the Python validator and WR v3.8.


## Earnings universe eligibility
- U.S.-domiciled issuers are included.
- A non-U.S. issuer is included only when its equity/ADR is listed on NYSE, Nasdaq, or NYSE American. The weekly record must carry the U.S. exchange, U.S. ticker, issuer country, and a traceable listing-evidence URL.
- OTC/OTCQX ADRs and securities trading only on non-U.S. exchanges are excluded. An ADR program by itself is not sufficient.
- Both current-week and previous-week earnings snapshots apply the same eligibility filter. Economic-calendar events are unaffected.
- Listing eligibility must be rechecked when an issuer changes venue, delists, or terminates its ADR program.
