#!/usr/bin/env python3
"""TAC earnings card rendering adapter; never calculates Beat/Miss independently."""
import re
from tac_earnings_judgment import render_status

def earnings_comparison_status(item, metric):
    """Read the persisted, versioned judgment; HTML assembly never infers Beat/Miss."""
    return render_status(item, metric)

def earnings_commentary(item):
    """Keep editorial prose consistent with the engine's persisted EPS/revenue statuses."""
    statuses = {
        "eps": earnings_comparison_status(item, "eps"),
        "revenue": earnings_comparison_status(item, "revenue"),
    }
    labels = {
        "beat": "優於預期",
        "miss": "低於預期",
        "inline": "符合預期",
        "pending": "比較口徑待核實",
        "incomparable": "比較口徑不相容",
        "consensus_divergent": "市場共識來源分歧",
    }
    raw = str(item.get("judgment") or "").strip()
    kept = []
    for fragment in re.split(r"(?<=[。！？])\s*|[；;]\s*|(?<=\.)\s+(?=[A-Z])", raw):
        part = fragment.strip()
        if not part:
            continue
        directional = bool(re.search(
            r"符合預期|(?:高於|低於|優於|超過|不及).{0,40}(?:共識|預期)|"
            r"Beat|Miss|(?:above|below|higher|lower).{0,35}(?:consensus|expectations)|"
            r"exceed(?:ed|s)? expectations|miss(?:ed)? expectations|outperform(?:ed|s)?|"
            r"underperform(?:ed|s)?",
            part,
            flags=re.IGNORECASE,
        ))
        if not directional:
            kept.append(part)
            continue
        has_eps = bool(re.search(r"\bEPS\b|每股|per[- ]share", part, flags=re.IGNORECASE))
        has_revenue = bool(re.search(r"營收|revenue|net sales", part, flags=re.IGNORECASE))
        # An unqualified directional sentence is ambiguous; do not preserve it.
        if not has_eps and not has_revenue:
            continue
        if has_eps and not has_revenue:
            status = statuses["eps"]
            if status not in {"beat", "miss", "inline"}:
                continue
            if status == "beat" and re.search(r"低於.{0,40}(?:共識|預期)|不及.{0,40}(?:共識|預期)|Miss|below.{0,35}(?:consensus|expectations)|lower.{0,35}(?:consensus|expectations)|miss(?:ed)? expectations|underperform(?:ed|s)?", part, re.I):
                continue
            if status == "miss" and re.search(r"高於.{0,40}(?:共識|預期)|優於預期|Beat|above.{0,35}(?:consensus|expectations)|higher.{0,35}(?:consensus|expectations)|exceed(?:ed|s)? expectations", part, re.I):
                continue
            if status == "inline":
                continue
        elif has_revenue and not has_eps:
            status = statuses["revenue"]
            if status not in {"beat", "miss", "inline"}:
                continue
            if status == "beat" and re.search(r"低於.{0,40}(?:共識|預期)|不及.{0,40}(?:共識|預期)|Miss|below.{0,35}(?:consensus|expectations)|lower.{0,35}(?:consensus|expectations)|miss(?:ed)? expectations|underperform(?:ed|s)?", part, re.I):
                continue
            if status == "miss" and re.search(r"高於.{0,40}(?:共識|預期)|優於預期|Beat|above.{0,35}(?:consensus|expectations)|higher.{0,35}(?:consensus|expectations)|exceed(?:ed|s)? expectations", part, re.I):
                continue
            if status == "inline":
                continue
        else:
            # A sentence covering both metrics is only safe when both are directional
            # and it contains no polarity conflict. Otherwise the whole sentence is removed.
            if any(statuses[m] not in {"beat", "miss", "inline"} for m in ("eps", "revenue")):
                continue
            if statuses["eps"] == "inline" or statuses["revenue"] == "inline":
                continue
            if re.search(r"高於.{0,40}(?:共識|預期)|優於預期|Beat|above.{0,35}(?:consensus|expectations)|higher.{0,35}(?:consensus|expectations)|exceed(?:ed|s)? expectations", part, re.I) and "miss" in {statuses["eps"], statuses["revenue"]}:
                continue
            if re.search(r"低於.{0,40}(?:共識|預期)|不及.{0,40}(?:共識|預期)|Miss|below.{0,35}(?:consensus|expectations)|lower.{0,35}(?:consensus|expectations)|miss(?:ed)? expectations|underperform(?:ed|s)?", part, re.I) and "beat" in {statuses["eps"], statuses["revenue"]}:
                continue
        kept.append(part)

    summary = "；".join(f"{metric.upper() if metric == 'eps' else '營收'}：{labels[statuses[metric]]}" for metric in ("eps", "revenue"))
    return ("；".join(kept) + ("；" if kept else "") + summary)


