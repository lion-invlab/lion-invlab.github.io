#!/usr/bin/env python3
"""Read-only ORTEX TEST-key feasibility probe; never writes calendar data."""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://api.ortex.com/api/v11/stock"
WINDOW = {"from_date": "2026-11-05", "to_date": "2026-11-13", "period_type": "quarterly", "page_size": 100, "format": "json"}
CANDIDATES = [("NASDAQ", "AAPL"), ("NASDAQ", "MSFT"), ("NYSE", "AMC")]

def request_one(namespace: str, ticker: str) -> dict:
    query = urllib.parse.urlencode(WINDOW)
    url = f"{BASE}/{urllib.parse.quote(namespace)}/{urllib.parse.quote(ticker)}/estimates/consensus/?{query}"
    observed_at = datetime.now(timezone.utc).isoformat()
    req = urllib.request.Request(url, headers={"Ortex-Api-Key": "TEST", "Accept": "application/json", "User-Agent": "TAC-Ortex-TEST-Probe/1.0"})
    status, headers, raw = None, {}, b""
    try:
        with urllib.request.urlopen(req, timeout=35) as response:
            status = response.status
            headers = {k.lower(): v for k, v in response.headers.items()}
            raw = response.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        headers = {k.lower(): v for k, v in exc.headers.items()} if exc.headers else {}
        raw = exc.read()
    except Exception as exc:
        return {"namespace": namespace, "ticker": ticker, "url": url, "observed_at": observed_at,
                "transport_error": f"{type(exc).__name__}: {exc}", "http_status": None,
                "raw_response": None, "raw_response_sha256": None}
    raw_text = raw.decode("utf-8", errors="replace")
    try:
        payload = json.loads(raw_text)
    except Exception:
        payload = None
    rows = payload.get("data", []) if isinstance(payload, dict) else []
    sample = []
    for row in rows[:12]:
        if isinstance(row, dict):
            wanted = ("date", "periodType", "periodEndDate", "fiscalYear", "fiscalQuarter", "currency",
                      "estimateAsOf", "epsConsensusMean", "epsNumEstimates",
                      "revenueConsensusMean", "revenueNumEstimates")
            sample.append({k: row.get(k) for k in wanted if k in row})
    return {
        "namespace": namespace, "ticker": ticker, "url": url, "observed_at": observed_at,
        "http_status": status, "content_type": headers.get("content-type"),
        "response_generated_at": payload.get("meta", {}).get("responseGeneratedAt") if isinstance(payload, dict) else None,
        "test_key_note": payload.get("meta", {}).get("testKeyNote") if isinstance(payload, dict) else None,
        "request_echo": payload.get("request") if isinstance(payload, dict) else None,
        "resolved": payload.get("resolved") if isinstance(payload, dict) else None,
        "instrument": payload.get("instrument") if isinstance(payload, dict) else None,
        "meta": payload.get("meta") if isinstance(payload, dict) else None,
        "pagination": payload.get("pagination") if isinstance(payload, dict) else None,
        "data_rows": len(rows),
        "sample_rows": sample,
        "row_field_names": sorted({k for row in rows if isinstance(row, dict) for k in row}),
        "raw_response": raw_text,
        "raw_response_sha256": hashlib.sha256(raw).hexdigest(),
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    results = [request_one(ns, ticker) for ns, ticker in CANDIDATES]
    successful = [r for r in results if r.get("http_status") == 200 and r.get("data_rows", 0) > 0]
    report = {
        "probe": "ortex_consensus_test_key",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "source_priority_impact": "none; research only; SIM-1.2 unchanged",
        "production_database_write": False,
        "requested_window": WINDOW,
        "candidates": results,
        "verdict": "HTTP_200_WITH_ROWS" if successful else "NO_USABLE_TEST_RESPONSE",
        "limitations": [
            "TEST key sample may be date/region restricted and is not proof of paid-plan coverage.",
            "Normalized EPS basis is not yet mapped to GAAP/Adjusted or Basic/Diluted.",
            "No public redistribution licence has been established by this technical probe.",
            "No result from this probe is eligible for W46 backfill or production judgment."
        ]
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "verdict": report["verdict"],
        "candidates": [{
            "ticker": f'{r.get("namespace")}/{r.get("ticker")}',
            "http_status": r.get("http_status"),
            "data_rows": r.get("data_rows", 0),
            "transport_error": r.get("transport_error"),
            "fields": r.get("row_field_names", [])
        } for r in results],
        "output": str(out)
    }, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
