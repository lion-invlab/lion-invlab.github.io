import json
import sys
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("artifacts")
OUT.mkdir(parents=True, exist_ok=True)
report = {
    "probe_started_utc": datetime.now(timezone.utc).isoformat(),
    "method": "unofficial open-source calculation using public CME settlement data and FRED",
    "package": "cme-fedwatch",
    "status": "not_started",
}

try:
    from cme_fedwatch import get_probabilities

    data = get_probabilities()
    report["status"] = "retrieved"
    report["data"] = data

    meetings = data.get("meetings") or []
    report["validation"] = {
        "has_trade_date": bool(data.get("trade_date")),
        "has_meetings": bool(meetings),
        "meeting_count": len(meetings),
        "probability_checks": [],
    }
    for meeting in meetings:
        probabilities = meeting.get("probabilities") or {}
        numeric = {}
        for key, value in probabilities.items():
            try:
                numeric[key] = float(value)
            except (TypeError, ValueError):
                pass
        total = sum(numeric.values())
        report["validation"]["probability_checks"].append({
            "meeting_date": meeting.get("date"),
            "contract": meeting.get("contract"),
            "outcome_count": len(numeric),
            "probability_sum": round(total, 4),
            "sum_near_100": abs(total - 100.0) <= 0.2,
        })
    report["validation"]["all_probability_sums_near_100"] = bool(
        report["validation"]["probability_checks"]
    ) and all(x["sum_near_100"] for x in report["validation"]["probability_checks"])
    if not report["validation"]["has_trade_date"] or not report["validation"]["has_meetings"]:
        report["status"] = "retrieved_but_incomplete"
except Exception as exc:
    report["status"] = "failed"
    report["error"] = f"{type(exc).__name__}: {exc}"

report["probe_finished_utc"] = datetime.now(timezone.utc).isoformat()
(OUT / "cme-fedwatch-free-probe.json").write_text(
    json.dumps(report, indent=2, ensure_ascii=False, default=str),
    encoding="utf-8",
)
print(json.dumps({
    "status": report["status"],
    "trade_date": (report.get("data") or {}).get("trade_date"),
    "meeting_count": (report.get("validation") or {}).get("meeting_count", 0),
    "all_probability_sums_near_100": (report.get("validation") or {}).get("all_probability_sums_near_100"),
    "error": report.get("error"),
}, indent=2, ensure_ascii=False))
if report["status"] != "retrieved" or not report.get("validation", {}).get("all_probability_sums_near_100"):
    sys.exit(1)
