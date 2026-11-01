# TAC Weekly Calendar Database (prototype)

This directory is the proposed weekly source of truth for economic and earnings calendar events. It is a prototype on a non-production branch; WR v3.7 remains authoritative.

## Lifecycle
1. Monday initializes one ISO week file (e.g. `2026-W45.json`).
2. Tue-Fri performs idempotent upserts by stable event `id`; it must not recreate or duplicate events.
3. Each daily report reads the week file and emits an immutable daily snapshot. A later correction updates the weekly record and audit trail, not an already approved report.
4. On the next Monday, the prior week remains available as an archive. The previous-week renderer filters to released TAC 5-star events only.
5. Current-week panels retain TAC 4- and 5-star events only. These thresholds mirror WR v3.7; do not reinterpret external 1-3 star ratings as TAC ratings.

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
- `../../scripts/tac_weekly_calendar_db.py`: stdlib CLI for validate, idempotent upsert, daily snapshot export, and safe snapshot merge.
