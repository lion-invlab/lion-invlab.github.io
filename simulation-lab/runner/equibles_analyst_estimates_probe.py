#!/usr/bin/env python3
"""Read-only Equibles analyst-estimates API access and PIT coverage probe.

The API key is read only from EQUIBLES_API_KEY. It is never printed, persisted,
or included in request URLs. Raw JSON responses are archived without secrets.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://api.equibles.com/v1/stocks/{ticker}/analyst-estimates"
TARGETS = {
    "NVDA": {"event_date": "2026-11-17", "period_markers": ("2026-10-31", "Q ending 2026-10-31")},
    "WMT": {"event_date": "2026-11-19", "period_markers": ("2026-10-31", "Q ending 2026-10-31")},
    "BIDU": {"event_date": "2026-11-16", "period_markers": ("2026-09-30", "Q ending 2026-09-30")},
}

def get_json(ticker: str, snapshot_id: str | None = None) -> tuple[dict, bytes, int]:
    key = os.environ.get("EQUIBLES_API_KEY", "").strip()
    if not key:
        raise RuntimeError("EQUIBLES_API_KEY is not configured in this workflow run")
    params = {"limit": "100"}
    if snapshot_id:
        params["snapshotId"] = snapshot_id
    url = BASE.format(ticker=ticker) + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={"Authorization": "Bearer " + key, "Accept": "application/json",
                 "User-Agent": "TAC-Earnings-PIT-Probe/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=35) as response:
            raw = response.read()
            status = response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        status = exc.code
    try:
        payload = json.loads(raw.decode("utf-8")) if raw else {}
    except Exception:
        payload = {"_parse_error": "response was not valid JSON", "_body_excerpt": raw[:500].decode("utf-8", "replace")}
    return payload, raw, status

def summarize(ticker: str, payload: dict, raw: bytes, status: int, archive: Path) -> dict:
    digest = hashlib.sha256(raw).hexdigest()
    archive.mkdir(parents=True, exist_ok=True)
    raw_path = archive / f"{ticker}-{digest}.json"
    if not raw_path.exists():
        raw_path.write_bytes(raw)
    cfg = TARGETS[ticker]
    rows = payload.get("data") if isinstance(payload.get("data"), list) else []
    snapshots = payload.get("snapshots") if isinstance(payload.get("snapshots"), list) else []
    period_rows = [r for r in rows if isinstance(r, dict) and any(
        marker.casefold() in str(r.get("period", "")).casefold() for marker in cfg["period_markers"]
    )]
    def metric_summary(metric: str) -> dict:
        matches = [r for r in period_rows if str(r.get("metric", "")).casefold() == metric.casefold()]
        avg = next((r for r in matches if str(r.get("statistic", "")).casefold() in {"average", "mean"}), None)
        count = next((r for r in matches if "analyst" in str(r.get("statistic", "")).casefold() and "count" in str(r.get("statistic", "")).casefold()), None)
        return {
            "row_count": len(matches),
            "average": avg.get("value") if avg else None,
            "unit": avg.get("unit") if avg else None,
            "basis": avg.get("basis") if avg else None,
            "period": avg.get("period") if avg else (matches[0].get("period") if matches else None),
            "analyst_count": count.get("value") if count else None,
            "statistics": sorted({str(r.get("statistic")) for r in matches}),
            "publication_labels": sorted({str(r.get("publicationLabel")) for r in matches if r.get("publicationLabel")}),
        }
    captured = payload.get("capturedAt")
    verified = payload.get("verifiedAt")
    event_date = cfg["event_date"]
    def before_event(value):
        if not isinstance(value, str) or not value:
            return False
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            cutoff = datetime.fromisoformat(event_date).replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc) < cutoff
        except Exception:
            return False
    return {
        "ticker": ticker, "http_status": status,
        "api_status": payload.get("status"), "provider": payload.get("provider"),
        "coverage_note": payload.get("coverageNote"), "stale": payload.get("stale"),
        "snapshot_id": payload.get("snapshotId"),
        "captured_at": captured, "verified_at": verified,
        "captured_before_event_date": before_event(captured),
        "verified_before_event_date": before_event(verified),
        "event_date": event_date, "expected_period_markers": list(cfg["period_markers"]),
        "eps": metric_summary("EPS"), "revenue": metric_summary("Revenue"),
        "snapshot_history": snapshots,
        "snapshots_meta": payload.get("snapshotsMeta"),
        "data_meta": payload.get("meta"),
        "raw_response_ref": str(raw_path), "raw_response_sha256": digest,
    }

def main() -> int:
    out = Path("simulation-lab/output/equibles-analyst-estimates-probe.json")
    archive = Path("simulation-lab/output/equibles-raw")
    results = []
    for ticker in TARGETS:
        payload, raw, status = get_json(ticker)
        results.append(summarize(ticker, payload, raw, status, archive))
        time.sleep(0.5)
    verdict = "API_ACCESS_OK" if all(x["http_status"] == 200 for x in results) else "API_ACCESS_FAILED"
    report = {
        "probe": "equibles_analyst_estimates_read_only",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "branch_scope": "simulation/tac-process-lab-2026-11-06",
        "requests_used": len(results),
        "targets": results,
        "verdict": verdict,
        "limitations": [
            "This probe does not modify calendar JSON, earnings records, judgment rules, HTML, main, or schedules.",
            "API capturedAt/verifiedAt are provider snapshot verification times; source publicationLabel and accounting basis must be assessed separately.",
            "Missing basis, analyst count, exact fiscal period, or source publication evidence remains unresolved; no Beat/Miss is inferred.",
            "Only the latest verified snapshot is queried in this first access test; historical snapshotId retrieval is a subsequent validation stage."
        ],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "verdict": verdict,
        "targets": [{
            "ticker": x["ticker"], "http_status": x["http_status"],
            "provider": x["provider"], "snapshot_id": x["snapshot_id"],
            "captured_at": x["captured_at"], "verified_at": x["verified_at"],
            "eps": x["eps"], "revenue": x["revenue"],
            "raw_response_sha256": x["raw_response_sha256"],
        } for x in results],
        "output": str(out)
    }, ensure_ascii=False, indent=2))
    return 0 if verdict == "API_ACCESS_OK" else 1

if __name__ == "__main__":
    raise SystemExit(main())
