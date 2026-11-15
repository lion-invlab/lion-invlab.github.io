#!/usr/bin/env python3
"""Read-only Equibles historical snapshot/PIT evidence probe.

Uses only EQUIBLES_API_KEY from the environment. Never prints or persists it.
Queries the current snapshot index, then pins each returned historical snapshotId
and archives every raw response with SHA-256. No earnings/calendar records change.
"""
from __future__ import annotations
import hashlib, json, os, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://api.equibles.com/v1/stocks/{ticker}/analyst-estimates"
TARGETS = {
    "NVDA": {"event_date": "2026-11-17", "period_markers": ("2026-10-31",)},
    "WMT": {"event_date": "2026-11-19", "period_markers": ("2026-10-31",)},
    "BIDU": {"event_date": "2026-11-16", "period_markers": ("2026-09-30",)},
}
MAX_REQUESTS = 90  # leave headroom under the documented 100/day shared quota

class Probe:
    def __init__(self):
        self.key = os.environ.get("EQUIBLES_API_KEY", "").strip()
        if not self.key:
            raise RuntimeError("EQUIBLES_API_KEY is not configured")
        self.calls = 0
        self.archive = Path("simulation-lab/output/equibles-raw")
        self.archive.mkdir(parents=True, exist_ok=True)

    def get(self, ticker, params=None):
        if self.calls >= MAX_REQUESTS:
            raise RuntimeError("Safety stop: 90-request probe budget reached")
        self.calls += 1
        query = urllib.parse.urlencode(params or {"limit": "100"})
        url = BASE.format(ticker=ticker) + ("?" + query if query else "")
        req = urllib.request.Request(url, headers={
            "Authorization": "Bearer " + self.key,
            "Accept": "application/json",
            "User-Agent": "TAC-Earnings-PIT-Historical-Probe/1.0",
        })
        try:
            with urllib.request.urlopen(req, timeout=35) as response:
                raw, status = response.read(), response.status
        except urllib.error.HTTPError as exc:
            raw, status = exc.read(), exc.code
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            payload = {"_parse_error": True, "_body_excerpt": raw[:300].decode("utf-8", "replace")}
        digest = hashlib.sha256(raw).hexdigest()
        path = self.archive / f"{ticker}-{self.calls:03d}-{digest}.json"
        path.write_bytes(raw)
        return payload, status, digest, str(path)

def iso_before(value, cutoff):
    if not isinstance(value, str) or not value:
        return False
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        end = datetime.fromisoformat(cutoff).replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc) < end
    except Exception:
        return False

def metric_rows(payload, metric, period_markers):
    rows = payload.get("data") if isinstance(payload.get("data"), list) else []
    return [r for r in rows if isinstance(r, dict)
            and str(r.get("metric", "")).casefold() == metric.casefold()
            and any(m in str(r.get("period", "")) for m in period_markers)]

def metric_evidence(payload, metric, period_markers):
    rows = metric_rows(payload, metric, period_markers)
    avg = next((r for r in rows if str(r.get("statistic", "")).casefold() in {"average", "mean"}), None)
    count = next((r for r in rows if "analyst" in str(r.get("statistic", "")).casefold() and "count" in str(r.get("statistic", "")).casefold()), None)
    return {
        "row_count": len(rows),
        "average": avg.get("value") if avg else None,
        "unit": avg.get("unit") if avg else None,
        "basis": avg.get("basis") if avg else None,
        "period": avg.get("period") if avg else (rows[0].get("period") if rows else None),
        "analyst_count": count.get("value") if count else None,
        "statistics": sorted({str(r.get("statistic")) for r in rows}),
        "publication_labels": sorted({str(r.get("publicationLabel")) for r in rows if r.get("publicationLabel")}),
        "basis_values": sorted({str(r.get("basis")) for r in rows if r.get("basis") is not None}),
        "footnotes": sorted({str(r.get("footnotes")) for r in rows if r.get("footnotes")}),
    }

def main():
    p = Probe()
    results = []
    for ticker, cfg in TARGETS.items():
        first, status, digest, raw_path = p.get(ticker, {"limit": "100", "snapshotOffset": "0"})
        snaps = first.get("snapshots") if isinstance(first.get("snapshots"), list) else []
        smeta = first.get("snapshotsMeta") if isinstance(first.get("snapshotsMeta"), dict) else {}
        history = []
        for snap in snaps:
            sid = snap.get("id")
            if not sid:
                continue
            pinned, pstatus, pdigest, ppath = p.get(ticker, {"limit": "100", "snapshotId": sid})
            cap = pinned.get("capturedAt") or snap.get("capturedAt")
            ver = pinned.get("verifiedAt")
            history.append({
                "snapshot_id": sid,
                "http_status": pstatus,
                "captured_at": cap,
                "verified_at": ver,
                "publication_label": pinned.get("publicationLabel", snap.get("publicationLabel")),
                "captured_before_event_date": iso_before(cap, cfg["event_date"]),
                "verified_before_event_date": iso_before(ver, cfg["event_date"]),
                "eps": metric_evidence(pinned, "EPS", cfg["period_markers"]),
                "revenue": metric_evidence(pinned, "Revenue", cfg["period_markers"]),
                "raw_response_ref": ppath,
                "raw_response_sha256": pdigest,
                "provider": pinned.get("provider"),
                "coverage_note": pinned.get("coverageNote"),
                "status": pinned.get("status"),
            })
            time.sleep(0.25)
        results.append({
            "ticker": ticker,
            "event_date": cfg["event_date"],
            "initial_http_status": status,
            "provider": first.get("provider"),
            "coverage_note": first.get("coverageNote"),
            "stale": first.get("stale"),
            "newer_snapshot_pending": first.get("newerSnapshotPending"),
            "snapshot_index": snaps,
            "snapshots_meta": smeta,
            "history_snapshots_fetched": len(history),
            "history": history,
            "initial_raw_response_ref": raw_path,
            "initial_raw_response_sha256": digest,
        })
        time.sleep(0.25)
    out = {
        "probe": "equibles_historical_snapshot_pit_evidence",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "branch_scope": "simulation/tac-process-lab-2026-11-06",
        "requests_used": p.calls,
        "request_budget": MAX_REQUESTS,
        "targets": results,
        "interpretation": {
            "capture_time_is_not_data_as_of": True,
            "publication_label_is_recorded_separately": True,
            "missing_basis_or_publication_evidence_is_not_imputed": True,
            "pre_release_eligibility_not_granted_by_this_probe": True,
            "source_urls_and_verification_evidence": "Equibles documentation says these are retained internally; API payload may not expose them.",
        },
    }
    path = Path("simulation-lab/output/equibles-historical-pit-audit.json")
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "probe": out["probe"], "requests_used": p.calls, "output": str(path),
        "targets": [{
            "ticker": x["ticker"], "initial_http_status": x["initial_http_status"],
            "snapshot_count_reported": x["snapshots_meta"].get("total"),
            "snapshot_count_fetched": x["history_snapshots_fetched"],
            "snapshot_ids": [h["snapshot_id"] for h in x["history"]],
            "basis_nonnull_eps": sum(bool(h["eps"]["basis_values"]) for h in x["history"]),
            "basis_nonnull_revenue": sum(bool(h["revenue"]["basis_values"]) for h in x["history"]),
            "publication_label_nonnull": sum(bool(h["publication_label"]) for h in x["history"]),
        } for x in results]
    }, ensure_ascii=False, indent=2))
    return 0 if all(x["initial_http_status"] == 200 for x in results) else 1

if __name__ == "__main__":
    raise SystemExit(main())
