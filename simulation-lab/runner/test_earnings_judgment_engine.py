#!/usr/bin/env python3
"""Regression tests for the practical TAC earnings comparison engine."""
from earnings_judgment import ENGINE_VERSION, VALID_STATUSES, evaluate_metric, apply_judgment, render_status, render_summary, consensus_evidence_label

def record(eps_actual, eps_estimate, revenue_actual, revenue_estimate):
    return {
        "id": "earn-test-1", "ticker": "EX",
        "eps_actual": eps_actual, "eps_estimate": eps_estimate,
        "revenue_actual": revenue_actual, "revenue_estimate": revenue_estimate,
        # Deliberately no PIT snapshots or full basis disclosure.
        "source": {"name":"Issuer", "url":"https://example.com/actual", "observed_at":"2026-11-15T08:00:00+08:00"},
        "consensus_source": {"name":"Yahoo Finance", "url":"https://finance.yahoo.com/quote/EX/analysis/", "observed_at":"2026-11-14T08:00:00+08:00"},
        "revenue_consensus_source": {"name":"Yahoo Finance", "url":"https://finance.yahoo.com/quote/EX/analysis/", "observed_at":"2026-11-14T08:00:00+08:00"},
    }

def main():
    assert ENGINE_VERSION == "1.4.0"
    assert VALID_STATUSES == {"beat", "miss", "inline", "pending"}
    x=record(1.20,1.00,9.2,8.7)
    assert evaluate_metric(x,"eps")["status"] == "beat"
    assert evaluate_metric(x,"revenue")["status"] == "beat"
    x=record(0.90,1.00,8.0,8.7)
    assert evaluate_metric(x,"eps")["status"] == "miss"
    assert evaluate_metric(x,"revenue")["status"] == "miss"
    x=record(1.005,1.00,8.75,8.7)
    assert evaluate_metric(x,"eps")["status"] == "inline"
    assert evaluate_metric(x,"revenue")["status"] == "inline"
    # Negative EPS: a smaller loss than expected is a beat.
    x=record(-0.13,-0.72,0.0,0.0)
    assert evaluate_metric(x,"eps")["status"] == "beat"
    assert evaluate_metric(x,"revenue")["status"] == "inline"
    # Missing PIT and detailed methodology must not block numeric comparison.
    x=record(2.47,2.40,108.73,105.0)
    assert evaluate_metric(x,"eps")["status"] == "beat"
    assert evaluate_metric(x,"revenue")["status"] == "beat"
    # Selected Yahoo estimate remains usable without PIT, analyst count,
    # raw archive, statistic or detailed GAAP/Adjusted metadata.
    x = record(2.70, 2.50, 115.8, 110.0)
    x.update({
        "event_date": "2026-11-24T21:00:00+08:00",
        "eps_estimate_period": "2026 Q3",
        "revenue_estimate_period": "2026 Q3",
        "eps_consensus_snapshots": [{
            "snapshot_id": "a" * 64, "event_id": "earn-test-1", "ticker": "EX",
            "metric": "EPS", "event_date": "2026-11-24T21:00:00+08:00", "value": 2.50,
            "period": "2026 Q3", "source_level": 1, "provider": "Yahoo Finance",
            "source_url": x["consensus_source"]["url"], "observed_at": None,
            "data_as_of": None, "basis_code": None, "raw_response_ref": None,
            "period_end_date": None, "statistic": None,
        }],
        "consensus_source": {
            **x["consensus_source"], "snapshot_id": "a" * 64
        },
    })
    assert consensus_evidence_label(x, "eps") == "來源已記錄（PIT／補充欄位非採用門檻）"
    assert evaluate_metric(x, "eps")["status"] == "beat"
    # Explicitly non-comparable currency/unit/basis data maps to pending,
    # not a fifth public status. The reason remains available for audit.
    x=record(0.54,0.69,0.9314,1.14)
    x["revenue_actual_currency"] = "CHF"
    x["revenue_estimate_currency"] = "USD"
    result = evaluate_metric(x,"revenue")
    assert result["status"] == "pending"
    assert result["reason"].startswith("comparison_inputs_not_comparable:")
    assert result["status"] in VALID_STATUSES and result["reason"].startswith("comparison_inputs_not_comparable:")

    # Metrics remain independent.
    x=record(1.1,1.0,None,8.7)
    assert evaluate_metric(x,"eps")["status"] == "beat"
    assert evaluate_metric(x,"revenue")["status"] == "pending"
    apply_judgment(x,"2026-11-15T13:00:00+08:00")
    assert x["judgment_engine_version"] == ENGINE_VERSION
    assert render_status(x,"eps") == "beat"
    assert render_status(x,"revenue") == "pending"
    assert "優於預期" in render_summary(x)
    print("PASS: four-state numerical comparison, 1% inline band, negative EPS, no PIT/basis gate, independent metrics")

if __name__ == "__main__":
    main()
