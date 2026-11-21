# [build-tac-report:2026-11-23] Rebuild Monday after retrospective prototype and list-slot repair.
#!/usr/bin/env python3
"""Simulation-only DOM updater. Never edits formal scripts or approved master."""
from __future__ import annotations
import argparse, copy, hashlib, json, re, sys, subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from bs4 import BeautifulSoup, Comment, NavigableString
from calendar_source_guard import load_authoritative_calendar, project_calendar_data
from earnings_judgment import render_status, consensus_evidence_label, apply_judgment

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "simulation-lab/baseline/mother-template-manifest.json"
QA_CONTRACT = ROOT / "simulation-lab/baseline/mother-template-qa-contract.md"
ACTIVE_RULES = ROOT / "simulation-lab/TAC_WORK_RULES_SIM.md"
CANDIDATE_RULES = ROOT / "simulation-lab/TAC_WORK_RULES_SIM_1.4_DRAFT.md"

def sha_blob(text: str) -> str:
    b=text.encode("utf-8")
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def normalize_market_label(value):
    """Normalize insignificant whitespace while preserving the original label for display."""
    return re.sub(r"\s+", "", str(value or "")).casefold()


def populate_fedwatch_two_slots(fed, data):
    """Update the two approved FedWatch cards without cloning or rebuilding DOM."""
    rows = fed.select(".fc-prob")
    bar = fed.select_one(".fc-split-bar")
    legend = fed.select_one(".fc-split-legend")
    segments = bar.select(":scope > span") if bar else []
    entries = legend.select(":scope > span") if legend else []
    if len(rows) != 2 or bar is None or legend is None or len(segments) != 2 or len(entries) != 2:
        raise ValueError("FedWatch mother template must retain exactly two cards, bar segments and legend entries")
    outcomes = data.get("fedwatch", {}).get("probabilities") or []
    def pending(message):
        for row in rows:
            set_text(unique(row, "strong", "probability"), "待核實")
            set_text(unique(row, ".fc-range", "range"), message)
            set_text(unique(row, ".fc-prob-label span:not(.fc-dot)", "label"), "機率待核實")
        bar.attrs["hidden"] = "hidden"
        bar.attrs.pop("aria-label", None)
        for entry in entries:
            if len(entry.contents) >= 3:
                entry.contents[1].replace_with("機率資料待核實 ")
                set_text(entry.contents[-1], "—")
        return message
    if not outcomes:
        return pending("未取得 05:25 前可用快照")
    total = sum(float(item["probability"]) for item in outcomes)
    if abs(total - 100) > 0.2:
        raise ValueError(f"FedWatch distribution totals {total}")
    holds = [item for item in outcomes if item.get("outcome") == "hold"]
    hikes = [item for item in outcomes if item.get("outcome") == "hike"]
    # The approved mother has only hold + one hike slot. Do not manufacture a
    # third card or silently omit cut/other outcomes; fail the visual display closed.
    if len(outcomes) != 2 or len(holds) != 1 or len(hikes) != 1:
        detail = "；".join(
            f'{item.get("outcome", "unknown")} {item.get("rate_range", "區間待核實")} {float(item.get("probability", 0)):.1f}%'
            for item in outcomes
        )
        return pending("情境數量／類型超出母版兩卡規格；完整分布見資料時間與快照口徑：" + detail)
    ordered = [holds[0], hikes[0]]
    current_range = data.get("fedwatch", {}).get("current_target_range")
    if not current_range or holds[0].get("rate_range") != current_range:
        raise ValueError("FedWatch hold outcome does not match the current target range")
    labels = ["維持不變", "升息"]
    for row, item, label in zip(rows, ordered, labels):
        set_text(unique(row, "strong", "probability"), f'{float(item["probability"]):.1f}%')
        set_text(unique(row, ".fc-range", "range"), item.get("rate_range", "區間待核實"))
        set_text(unique(row, ".fc-prob-label span:not(.fc-dot)", "label"), label)
    for segment, entry, label, item in zip(segments, entries, labels, ordered):
        segment["style"] = f'width:{float(item["probability"]):.1f}%'
        if len(entry.contents) < 3:
            raise ValueError("FedWatch legend entry lost its approved child structure")
        entry.contents[1].replace_with(label + " ")
        set_text(entry.contents[-1], f'{float(item["probability"]):.1f}%')
    bar.attrs.pop("hidden", None)
    bar["aria-label"] = "；".join(
        f'{label} {float(item["probability"]):.1f}%'
        for label, item in zip(labels, ordered)
    )
    return None


def populate_fed_weekly_agenda(soup, data):
    """Fill only the pre-existing Fed agenda slots; never rebuild its outer DOM."""
    box = soup.select_one("#fed .fc-fomc-weekly-events")
    if box is None:
        raise ValueError("Approved mother template missing #fed .fc-fomc-weekly-events")
    title = box.select_one(".fc-fomc-weekly-events-title")
    listing = box.select_one(".fc-fomc-weekly-events-list")
    prototype = box.select_one(".fc-fomc-weekly-event-template")
    empty = box.select_one(".fc-fomc-weekly-events-empty")
    missing_slots = [name for name, node in (("title", title), ("list", listing), ("prototype", prototype), ("empty", empty)) if node is None]
    if missing_slots:
        raise ValueError("Fed weekly agenda template slots are incomplete: " + ", ".join(missing_slots))
    if title.get_text(" ", strip=True) != "本週聯準會官員行程":
        raise ValueError("Fed weekly agenda title slot changed unexpectedly")
    week_start = str(data.get("calendar", {}).get("week_start", ""))[:10]
    week_end = str(data.get("calendar", {}).get("week_end", ""))[:10]
    speaker_pattern = re.compile(
        r"Fed|Federal Reserve|Waller|Bowman|Goolsbee|Barkin|Logan|Schmid|Jefferson|Barr|Daly|Hammack|Williams",
        re.I,
    )
    records = [
        event for event in data.get("calendar", {}).get("events", [])
        if speaker_pattern.search(str(event.get("name", "")))
        and week_start <= str(event.get("date", ""))[:10] <= week_end
        and str(event.get("status", "upcoming")).lower() not in {"cancelled"}
    ]
    records.sort(key=lambda event: str(event.get("date", "")))
    # The list is a dedicated dynamic slot. Keep the list wrapper and fixed
    # prototype intact; remove only previously rendered event instances.
    for old in list(listing.select(":scope > .fc-fomc-weekly-event")):
        old.decompose()
    rendered_names = []
    for event in records:
        event_date = datetime.fromisoformat(str(event["date"]).replace("Z", "+00:00"))
        status = str(event.get("status", "upcoming")).lower()
        status_label = "已發表" if status in {"released", "published", "completed"} else "預定"
        date_label = f"{status_label}｜{event_date.month}/{event_date.day} {['一','二','三','四','五','六','日'][event_date.weekday()]} {event_date:%H:%M}"
        row = copy.deepcopy(prototype)
        row.attrs = {key: list(value) if isinstance(value, list) else value for key, value in prototype.attrs.items()}
        # The mother prototype's fixed 94px date column crushes long names and
        # analysis on phones. Keep the same event DOM slots, but stack the
        # date above the speaker/content for readable narrow screens.
        row["style"] = "display:grid;grid-template-columns:minmax(0,1fr);gap:4px;padding:10px 0;border-top:1px solid #e1e7ee;"
        row["class"] = [name for name in row.get("class", []) if name != "fc-fomc-weekly-event-template"]
        row["class"].append("fc-fomc-weekly-event")
        row.attrs.pop("hidden", None)
        row.attrs.pop("data-fed-event-template", None)
        date_slot = row.select_one(".fc-fomc-weekly-event-date")
        name_slot = row.select_one(".fc-fomc-weekly-event-name")
        impact_slot = row.select_one(".fc-fomc-weekly-event-impact")
        link_slot = row.select_one(".fc-fomc-weekly-event-source")
        if not all((date_slot, name_slot, impact_slot, link_slot)):
            raise ValueError("Fed weekly agenda event prototype slots are incomplete")
        date_slot.string = date_label
        name_slot.string = str(event.get("name", ""))
        impact_slot.string = str(event.get("impact", ""))
        source_url = str(event.get("source_url", ""))
        if source_url.startswith("https://"):
            link_slot["href"] = source_url
            link_slot.attrs.pop("hidden", None)
        else:
            link_slot.attrs["hidden"] = "hidden"
            link_slot.attrs.pop("href", None)
        listing.append(row)
        rendered_names.append(str(event.get("name", "")))
    if records:
        empty.attrs["hidden"] = "hidden"
    else:
        empty.attrs.pop("hidden", None)
    rendered_text = listing.get_text(" ", strip=True)
    missing = [name for name in rendered_names if name and name not in rendered_text]
    if missing:
        raise ValueError("Fed weekly agenda omitted verified events: " + "; ".join(missing))
    return len(records)


def reject_cfd_cash_index_quotes(data):
    """Prevent an explicitly identified CFD index series from rendering as a cash-index close."""
    rejected = []
    for name, record in data.get("global_markets", {}).items():
        if not isinstance(record, dict):
            continue
        source = record.get("source") if isinstance(record.get("source"), dict) else {}
        quote_type = str(source.get("quote_type") or "").strip().lower()
        if quote_type in {"cfd_index_reference_series", "cfd_cash_index_proxy"}:
            prior = {
                key: record.get(key)
                for key in ("display", "change_display", "source_name", "source_url")
                if record.get(key) not in (None, "")
            }
            if prior:
                record["rejected_reference"] = {
                    **(record.get("rejected_reference") or {}),
                    **prior,
                    "reason": "CFD reference series is not an eligible cash-index close",
                }
            record["display"] = "待核實"
            record["change_display"] = "待核實"
            record["qa_status"] = "cfd_index_reference_rejected"
            rejected.append(name)
    return rejected

def set_text(node, value):
    """Replace a plain leaf-text slot only; fail closed rather than erase nested mother DOM."""
    if node is None:
        raise ValueError("set_text target node is missing")
    if any(getattr(child, "name", None) for child in node.contents):
        raise ValueError(
            f"set_text refused to erase child elements in <{node.name}>; update an approved leaf text slot"
        )
    node.clear()
    node.append(str(value))

def set_text_preserving_child_elements(node, value):
    """Update an existing text slot; never add or remove source-link DOM."""
    if node is None:
        raise ValueError("text container is missing")
    text_nodes = [
        child for child in node.contents
        if isinstance(child, NavigableString) and str(child).strip()
    ]
    if text_nodes:
        text_nodes[0].replace_with(str(value))
        return True
    # Some source disclosures contain only anchors. Do not invent a new text
    # node or overwrite link labels; leave those mother-owned links untouched.
    for candidate in node.descendants:
        if not isinstance(candidate, NavigableString) or not str(candidate).strip():
            continue
        parent = candidate.parent
        inside_link = False
        while parent is not None and parent is not node:
            if getattr(parent, "name", None) == "a":
                inside_link = True
                break
            parent = parent.parent
        if not inside_link:
            candidate.replace_with(str(value))
            return True
    return False


def set_calendar_status_heading(heading, text, status_key):
    """Update the existing badge text slot while preserving its mother-owned wrapper."""
    if heading is None:
        raise ValueError("calendar status heading missing")
    badge = heading.select_one(".earnings-badge")
    if badge is not None:
        set_text(badge, text)
        badge["class"] = ["earnings-badge", status_key]
    else:
        set_text(heading, text)
    heading["class"] = ["calendar-status-heading", status_key]

def update_contract_link_label(label_link, contract_label, source_meta, instrument_url=None, instrument_key=None, display_name=None):
    """Keep the visible product name short; full contract/month belongs in source details only."""
    if label_link is None:
        return False
    base_label = str(display_name or label_link.get_text(" ", strip=True).split("（", 1)[0]).strip()
    set_text(label_link, base_label)
    target_url = instrument_url or source_meta.get("url", "")
    if not str(target_url).startswith("https://hk.investing.com/"):
        raise ValueError("commodity instrument link must target the corresponding Investing.com HK page")
    expected_paths = {
        "WTI原油期貨": "crude-oil-historical-data",
        "Brent原油期貨": "brent-oil-historical-data",
        "黃金期貨GC": "gold-historical-data",
        "白銀期貨SI": "silver-historical-data",
    }
    normalized_key = "".join(str(instrument_key or base_label).split())
    expected_path = expected_paths.get(normalized_key)
    if expected_path and expected_path not in str(target_url):
        raise ValueError(f"{base_label}: Investing.com link does not match the instrument history page")
    label_link["href"] = target_url
    label_link["target"] = "_blank"
    label_link["rel"] = "noopener"
    return True


def parse_taipei_local_datetime(value, field_name):
    """Parse a date/time as Asia/Taipei; naive values are defined as Taipei-local."""
    raw = str(value or "").strip()
    if not raw:
        raise ValueError(f"{field_name} is required for calendar classification")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} is not a valid ISO date/time: {raw}") from exc
    taipei = timezone(timedelta(hours=8))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=taipei)
    else:
        parsed = parsed.astimezone(taipei)
    return parsed.replace(tzinfo=None)


def has_release_status_evidence(item):
    """Only dedicated publication-status/actual sources count; schedule URLs do not."""
    for key in ("report_layer_status_source", "status_source", "actual_source"):
        source = item.get(key)
        if isinstance(source, dict) and str(source.get("url") or "").startswith("https://"):
            return True
    for key in ("report_layer_status_source_url", "status_source_url", "actual_source_url"):
        if str(item.get(key) or "").startswith("https://"):
            return True
    return False


def calendar_actual_display(item, report_cutoff):
    """Render publication uncertainty honestly without inventing an actual value."""
    state = item.get("_calendar_publication_state", "scheduled")
    if state == "released":
        return item.get("actual") or "已公布；實際值待核實"
    if state == "cancelled":
        return "已取消"
    if state == "postponed":
        return "已延期；改期資訊待核實"
    if state == "pending_verification":
        return (
            "公告已發布；實際值待核實"
            if has_release_status_evidence(item)
            else "公布狀態待核實"
        )
    if item.get("status") == "pending_verification":
        return "公布狀態待核實"
    return f"尚未公布（資料截點 {report_cutoff}）"


def classify_calendar_group(item, report_iso, report_cutoff):
    """Classify by Taiwan-local date/cutoff while keeping unverified status unpromoted."""
    status = str(item.get("status") or item.get("status_in_db") or "").lower()
    event_text = str(item.get("event_date") or item.get("date") or "")
    event_dt = parse_taipei_local_datetime(event_text, "calendar event_date")
    cutoff_dt = parse_taipei_local_datetime(report_cutoff, "report_cutoff_taipei")
    report_day = datetime.strptime(str(report_iso)[:10], "%Y-%m-%d").date()
    event_day = event_dt.date()
    time_known = item.get("time_known") is True

    if status in ("released", "published", "completed"):
        state = "released"
    elif status == "postponed":
        state = "postponed"
    elif status in ("cancelled", "canceled"):
        state = "cancelled"
    elif status == "pending_verification":
        state = (
            "pending_verification"
            if event_day < report_day or (event_day == report_day and time_known and event_dt <= cutoff_dt)
            else "scheduled"
        )
    elif event_day < report_day or (event_day == report_day and time_known and event_dt <= cutoff_dt):
        # A scheduled time has elapsed, but no verified publication status exists.
        state = "pending_verification"
    else:
        state = "scheduled"
    item["_calendar_publication_state"] = state

    if state == "released":
        return "published"
    if state in ("postponed", "cancelled"):
        return "upcoming"
    if event_day < report_day:
        return "published"
    if event_day == report_day:
        if time_known and event_dt <= cutoff_dt:
            return "published"
        return "today"
    return "upcoming"


def validate_calendar_group_order(panel, label):
    groups = panel.select(":scope > .calendar-status-group")
    if len(groups) != 3:
        raise ValueError(f"{label}: expected exactly three mother status groups, got {len(groups)}")
    actual = []
    for group in groups:
        heading = group.select_one(".calendar-status-heading")
        classes = set(heading.get("class", [])) if heading else set()
        key = next((name for name in ("today", "upcoming", "published") if name in classes), None)
        actual.append(key)
    if actual != ["today", "upcoming", "published"]:
        raise ValueError(f"{label}: mother tab order changed or duplicated: {actual}")
    return True


def reset_calendar_listing(listing, card_class, empty_text, has_items):
    """Remove stale prototype cards and stale empty-state copy while preserving the mother list wrapper."""
    if listing is None:
        raise ValueError("calendar list wrapper missing")
    for child in list(listing.contents):
        if isinstance(child, NavigableString):
            child.extract()
        elif getattr(child, "name", None) == "details" and card_class in child.get("class", []):
            child.decompose()
        else:
            raise ValueError(f"unexpected child in mother calendar list: <{getattr(child, 'name', None)}>")
    if not has_items:
        listing.append(empty_text)


def apply_earnings_star_style(card, item):
    """Match the cloned card's star-level classes to its actual TAC star rating."""
    stars = int(item.get("stars") or 0)
    company = card.select_one(".earnings-company-name")
    if company is None:
        raise ValueError("earnings company name slot missing")
    card_classes = [c for c in card.get("class", []) if c != "five-star-earnings"]
    company_classes = [c for c in company.get("class", []) if c != "five-star-company"]
    if stars >= 5:
        card_classes.append("five-star-earnings")
        company_classes.append("five-star-company")
    card["class"] = card_classes
    company["class"] = company_classes


SUMMARY_HEADING_LABELS = {"總結", "摘要", "市場情緒", "Summary", "Market Summary"}

def apply_consensus_projection(data, projection, calendar_source):
    """Attach SHA-pinned TAC-observed consensus references to upcoming cards only."""
    if projection.get("calendar_blob_sha") != calendar_source["current"]["blob_sha"]:
        raise ValueError("W47 consensus projection does not match the authoritative main calendar blob SHA")
    if projection.get("branch_scope") != "simulation/tac-process-lab-2026-11-06":
        raise ValueError("consensus projection is not from the isolated simulation branch")
    if data.get("earnings", {}).get("week_id") != projection.get("week_id", "2026-W47"):
        raise ValueError("consensus projection week does not match report earnings week")
    by_id = {x.get("id"): x for x in data.get("earnings", {}).get("events", [])}
    applied = 0
    for row in projection.get("records", []):
        target = by_id.get(row.get("event_id"))
        if target is None or target.get("event_date") != row.get("event_date"):
            raise ValueError(f"consensus projection event identity mismatch: {row.get('ticker')}")
        released = target.get("status") in ("released", "published", "completed")
        if released and any(target.get(key) not in (None, "") for key in ("eps_estimate", "revenue_estimate")):
            raise ValueError(f"refusing to overwrite existing post-release consensus fields: {row.get('ticker')}")
        actual_before = {
            key: target.get(key)
            for key in ("eps_actual", "revenue_actual", "actual", "financial_judgment")
        }
        target.update({
            "eps_estimate": row.get("eps_estimate"),
            "eps_estimate_display": row.get("eps_estimate_display"),
            "eps_estimate_currency": row.get("eps_currency"),
            "eps_estimate_period": row.get("reporting_period"),
            "eps_estimate_basis_code": None,
            "eps_analyst_count": row.get("eps_analyst_count"),
            "eps_evidence_label": row.get("eps_evidence_label"),
            "eps_basis_display": row.get("eps_basis_display"),
            "eps_methodology": row.get("eps_methodology"),
            "revenue_estimate": row.get("revenue_estimate"),
            "revenue_estimate_display": row.get("revenue_estimate_display"),
            "revenue_estimate_currency": row.get("revenue_currency"),
            "revenue_estimate_unit": row.get("revenue_unit"),
            "revenue_estimate_period": row.get("reporting_period"),
            "revenue_estimate_basis_code": None,
            "revenue_analyst_count": row.get("revenue_analyst_count"),
            "revenue_evidence_label": row.get("revenue_evidence_label"),
            "revenue_basis_display": row.get("revenue_basis_display"),
            "consensus_source_url": row.get("source_url"),
            "consensus_source_name": row.get("source_name"),
            "consensus_observed_at": row.get("eps_snapshot", {}).get("observed_at"),
        })
        if target.get("eps_estimate") != row.get("eps_estimate") or target.get("revenue_estimate") != row.get("revenue_estimate"):
            raise ValueError(f"consensus projection assignment failed for {row.get('ticker')}")
        if any(target.get(key) != value for key, value in actual_before.items()):
            raise ValueError(f"consensus projection changed actual-result fields for {row.get('ticker')}")
        applied += 1
    if applied != len(projection.get("records", [])):
        raise ValueError("consensus projection did not apply every record")
    print(f"PASS: applied TAC-observed consensus projection to {applied} W47 earnings cards")
    return data


def validate_summary_title(value):
    """Require the black h1 slot to contain a concise market-takeaway, not a section label."""
    raw = str(value or "")
    if "｜" in raw or "\n" in raw or "\r" in raw:
        raise ValueError("summary_title must be a single line without body separators")
    title = " ".join(raw.split())
    if not title:
        raise ValueError("summary_title is required: black summary h1 must contain yesterday's one-line market takeaway")
    if title.casefold() in {x.casefold() for x in SUMMARY_HEADING_LABELS}:
        raise ValueError(f"summary_title is a generic section label ({title!r}); provide a one-line market takeaway")
    if len(title) < 8 or len(title) > 36:
        raise ValueError(f"summary_title must be a concise 8–36 character market takeaway; got {len(title)}")
    return title


def populate_summary_points_preserving_dom(node, points):
    """Update the mother-owned summary labels/text nodes without rebuilding its paragraph DOM."""
    if not isinstance(points, list) or not points:
        raise ValueError("summary_points must be a non-empty list aligned to the mother template")
    labels = node.find_all(["b", "strong"], recursive=False)
    if len(labels) != len(points):
        raise ValueError(
            f"summary_points count {len(points)} does not match mother template slots {len(labels)}"
        )
    for index, (label, point) in enumerate(zip(labels, points)):
        if not isinstance(point, dict) or not str(point.get("label", "")).strip() or not str(point.get("text", "")).strip():
            raise ValueError(f"summary_points[{index}] requires non-empty label and text")
        label.string = str(point["label"]).strip()
        content = label.next_sibling
        # Monday's approved paragraph uses <b><br/>text</b>; weekday's
        # approved paragraph uses <b>text</b><br/>. Preserve either mother shape.
        if getattr(content, "name", None) == "br":
            content = content.next_sibling
        while isinstance(content, NavigableString) and not str(content).strip():
            content = content.next_sibling
        if not isinstance(content, NavigableString):
            raise ValueError(f"summary_points[{index}] mother paragraph is missing its original text slot")
        content.replace_with(str(point["text"]).strip())
    return len(labels)


def set_market_observation(node, title, value):
    """Update existing heading/text nodes in place; never clear or rebuild the observation DOM."""
    if node is None:
        raise ValueError("market observation target node is missing")
    if isinstance(value, dict):
        title = str(value.get("heading") or title)
        raw = str(value.get("text") or "").strip()
    else:
        raw = str(value or "").strip()
    if "｜" in raw and raw.startswith("📌"):
        raw = raw.split("｜", 1)[1].strip()

    heading = node.find("b", recursive=False)
    line_break = next((child for child in node.children if getattr(child, "name", None) == "br"), None)

    def first_text_after(anchor):
        sibling = anchor.next_sibling if anchor is not None else None
        while sibling is not None:
            if isinstance(sibling, NavigableString) and str(sibling).strip():
                return sibling
            if getattr(sibling, "name", None):
                candidate = next((x for x in sibling.descendants if isinstance(x, NavigableString) and str(x).strip()), None)
                if candidate is not None:
                    return candidate
            sibling = sibling.next_sibling
        return None

    text_slot = first_text_after(line_break or heading)
    if text_slot is None and heading is None:
        text_slot = next((x for x in node.descendants if isinstance(x, NavigableString) and str(x).strip()), None)
    if text_slot is None:
        raise ValueError(
            "market observation has no existing text slot: "
            + str(node.name) + " class=" + " ".join(node.get("class", []))
        )
    if heading is not None:
        if str(title).strip():
            heading.string = title
        text_slot.replace_with(raw)
    else:
        text_slot.replace_with(title + "｜" + raw)


def unique(root, selector, label):
    nodes=root.select(selector)
    if len(nodes)!=1:
        raise ValueError(f"{label}: selector {selector!r} count={len(nodes)}")
    return nodes[0]

def source_link(url, label):
    a=BeautifulSoup("", "html.parser").new_tag("a", href=url, target="_blank", rel="noopener")
    a.string=label
    return a


def set_value_slot(node, value):
    """Replace content inside an approved value slot while retaining its wrapper."""
    if node is None:
        raise ValueError("approved value slot missing")
    node.clear()
    if isinstance(value, (list, tuple)):
        for index, part in enumerate(value):
            if index:
                node.append(BeautifulSoup("", "html.parser").new_tag("br"))
            if hasattr(part, "name"):
                node.append(part)
            else:
                node.append(str(part))
    else:
        node.append(str(value))


def earnings_metric_display(item, metric):
    actual_key, estimate_key = (
        ("eps_actual", "eps_estimate") if metric == "eps"
        else ("revenue_actual", "revenue_estimate")
    )
    actual_display = item.get(f"{metric}_actual_display") or (
        str(item.get(actual_key)) if item.get(actual_key) is not None else "未取得"
    )
    estimate_display = item.get(f"{metric}_estimate_display") or (
        str(item.get(estimate_key)) if item.get(estimate_key) is not None else "未取得"
    )
    state = earnings_comparison_status(item, metric)
    status = earnings_status_label(item, metric, state)
    basis = item.get("eps_basis") if metric == "eps" else item.get("revenue_actual_basis")
    parts = [f"實際：{actual_display}", f"預期：{estimate_display}", f"比較：{status}"]
    if basis:
        parts.append(f"口徑：{basis}")
    reason = item.get(f"{metric}_comparison_reason")
    if state == "pending" and reason:
        parts.append(f"原因：{reason}")
    return "；".join(parts)


def update_actual_results_grid(grid, item):
    """Fill the two existing EPS/revenue cards; never clear or recreate card DOM."""
    if grid is None:
        raise ValueError("published earnings results grid missing from approved prototype")
    cards = grid.find_all("div", class_="earnings-actual-card", recursive=False)
    if len(cards) != 2:
        raise ValueError(f"published earnings grid must retain two mother cards; found {len(cards)}")
    for card, metric, label in zip(cards, ("eps", "revenue"), ("EPS", "營收")):
        state = earnings_comparison_status(item, metric)
        if state not in ("beat", "miss", "inline", "pending"):
            state = "pending"
        card["class"] = ["earnings-actual-card", state]
        title = card.select_one(".earnings-actual-card-title")
        set_text(title, label)
        lines = card.select(".earnings-actual-line")
        if len(lines) != 2:
            raise ValueError(f"{label} actual card must retain two comparison lines")
        actual_key, estimate_key = (
            ("eps_actual", "eps_estimate") if metric == "eps"
            else ("revenue_actual", "revenue_estimate")
        )
        actual_display = item.get(f"{metric}_actual_display") or (
            str(item.get(actual_key)) if item.get(actual_key) is not None else "未取得"
        )
        estimate_display = item.get(f"{metric}_estimate_display") or (
            str(item.get(estimate_key)) if item.get(estimate_key) is not None else "未取得"
        )
        for line, caption, value in zip(
            lines, ("實際", "預期"), (actual_display, estimate_display)
        ):
            caption_node = line.select_one("span")
            value_node = line.select_one("strong")
            set_text(caption_node, caption)
            set_text(value_node, value)
        status_node = card.select_one(".earnings-actual-status")
        if status_node is None:
            raise ValueError(f"{label} actual card status slot missing")
        status_node["class"] = ["earnings-actual-status", state]
        set_text(status_node, earnings_status_label(item, metric, state))
        notes = card.select(".earnings-actual-note")
        if not notes:
            raise ValueError(f"{label} actual card evidence note slot missing")
        evidence = consensus_evidence_label(item, metric)
        if metric == "eps" and state == "pending" and item.get("eps_basis"):
            evidence = (evidence + "；" if evidence else "") + "EPS口徑：" + str(item["eps_basis"])
        note_text = evidence or "比較口徑／額外說明待核實"
        set_text(notes[0], note_text)
        for extra in notes[1:]:
            set_text(extra, "")


def fill_earnings_source_slot(value_node, item):
    parts = []
    actual_url = item.get("actual_source_url") or item.get("source_url")
    actual_name = item.get("actual_source_name") or item.get("source_name") or "實際財報來源"
    if actual_url:
        parts.append(source_link(actual_url, actual_name))
    else:
        parts.append("實際財報來源待核實")
    status_source = item.get("report_layer_status_source") or {}
    if status_source.get("url"):
        parts.extend(["公告狀態參考：", source_link(status_source["url"], status_source.get("name") or "第三方發布報導")])
    consensus_url = item.get("consensus_source_url")
    if consensus_url and consensus_url != actual_url:
        parts.extend(["公告前共識：", source_link(consensus_url, item.get("consensus_source_name") or "共識來源")])
        observed = item.get("consensus_observed_at")
        if observed:
            observed_tw = datetime.fromisoformat(str(observed).replace("Z", "+00:00")).astimezone(timezone(timedelta(hours=8))).strftime("%m/%d %H:%M")
            counts = []
            if item.get("eps_analyst_count") is not None:
                counts.append(f"EPS {item['eps_analyst_count']}位")
            if item.get("revenue_analyst_count") is not None:
                counts.append(f"營收 {item['revenue_analyst_count']}位")
            parts.append(f"（公告前快照 {observed_tw} 台灣時間{'；' + '／'.join(counts) if counts else ''}）")
    set_value_slot(value_node, parts)


def update_published_earnings_detail_fields(details, item, clock):
    fields = details.find_all("div", class_="earnings-detail-field", recursive=False)
    if not fields:
        raise ValueError("published earnings detail-field prototypes missing")
    seen = set()
    for field in fields:
        label_node = field.select_one("label")
        value_node = field.select_one(".earnings-detail-value")
        if label_node is None or value_node is None:
            raise ValueError("published earnings detail-field mother slots incomplete")
        name = label_node.get_text(" ", strip=True)
        if "公布時段" in name:
            session = {"before_market": "盤前", "after_market": "盤後"}.get(item.get("session"), "時段待核實")
            text_value = (
                f"財報發布：{session}（發布時間待核實）；電話會議：{clock}"
                if item.get("time_type") == "call_time"
                else f"財報發布：{session}；時間：{clock if item.get('time_known') else '時間待核實'}"
            )
            set_text(value_node, text_value)
            seen.add("timing")
        elif "EPS" in name and "營收" not in name:
            set_text(value_node, earnings_metric_display(item, "eps"))
            seen.add("eps")
        elif "營收" in name:
            set_text(value_node, earnings_metric_display(item, "revenue"))
            seen.add("revenue")
        elif "財報判讀" in name:
            reaction = item.get("price_reaction") or "股價反應待核實"
            set_text(value_node, earnings_commentary(item) + "；股價反應：" + str(reaction))
            seen.add("commentary")
        elif "股價" in name:
            reaction = item.get("price_reaction") or "股價反應待核實"
            reaction_url = item.get("price_reaction_source_url")
            if reaction_url:
                set_value_slot(value_node, [str(reaction), "｜", source_link(reaction_url, item.get("price_reaction_source") or "股價來源")])
            else:
                set_text(value_node, reaction)
            seen.add("reaction")
        elif "來源" in name:
            fill_earnings_source_slot(value_node, item)
            seen.add("source")
        else:
            raise ValueError(f"unsupported published earnings mother field: {name}")
    if not ({"commentary", "reaction"} & seen) or "source" not in seen:
        raise ValueError(f"published earnings card missing commentary/reaction or source slot: {sorted(seen)}")


def update_upcoming_earnings_detail_fields(details, item, day, clock, session_label, timing_value):
    fields = details.find_all("div", class_="earnings-detail-field", recursive=False)
    if not fields:
        raise ValueError("upcoming earnings detail-field prototypes missing")
    raw_status = str(item.get("status") or item.get("status_in_db") or "").lower()
    schedule = (
        "已取消；不再列為預定發布"
        if raw_status in ("cancelled", "canceled")
        else (
            f"已延期；改期至 {day}（{session_label}；{timing_value} 台灣時間）"
            if raw_status == "postponed"
            else (
                f"財報發布：{session_label}（發布時間待核實）；電話會議：{clock}"
                if item.get("time_type") == "call_time"
                else f"即將公布；{day}（{session_label}；{timing_value} 台灣時間）"
            )
        )
    )
    eps_est = item.get("eps_estimate_display") or (str(item.get("eps_estimate")) if item.get("eps_estimate") is not None else "預期資料尚未取得")
    rev_est = item.get("revenue_estimate_display") or (str(item.get("revenue_estimate")) if item.get("revenue_estimate") is not None else "預期資料尚未取得")
    eps_count = f"（{item['eps_analyst_count']} 位分析師）" if item.get("eps_analyst_count") is not None else "（分析師數未提供）"
    rev_count = f"（{item['revenue_analyst_count']} 位分析師）" if item.get("revenue_analyst_count") is not None else "（分析師數未提供）"
    eps_basis = item.get("eps_basis_display") or item.get("eps_basis") or "平台 EPS 預期口徑（細項未完整揭露）"
    rev_basis = item.get("revenue_basis_display") or "平台 Revenue 預期口徑（細項未完整揭露）"
    eps_line = f"EPS 預估：{eps_est}{eps_count}；口徑：{eps_basis}；共識證據：{item.get('eps_evidence_label') or '平台共識參考'}"
    rev_line = f"營收預估：{rev_est}{rev_count}；口徑：{rev_basis}；共識證據：{item.get('revenue_evidence_label') or '平台共識參考'}"
    observed = item.get("consensus_observed_at")
    if observed:
        observed_tw = datetime.fromisoformat(str(observed).replace("Z", "+00:00")).astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
        observed_line = f"共識觀測時間：{observed_tw} 台灣時間"
    else:
        observed_line = "共識觀測時間：未提供"
    if len(fields) == 1:
        label_node = fields[0].select_one("label")
        value_node = fields[0].select_one(".earnings-detail-value")
        if label_node is None or value_node is None:
            raise ValueError("single-slot Monday earnings prototype is incomplete")
        set_text(label_node, "財報預估、共識與發布資訊")
        # Monday's approved mother has one detail-field wrapper. Preserve that
        # wrapper, but render its contents as clearly separated labelled rows
        # instead of one undifferentiated paragraph.
        detail_rows = [
            ("發布資訊", schedule),
            ("EPS 預估", eps_line.replace("EPS 預估：", "", 1)),
            ("營收預估", rev_line.replace("營收預估：", "", 1)),
            ("共識時間", observed_line.replace("共識觀測時間：", "", 1)),
            ("資料判讀", item.get("judgment") or item.get("source_notes") or "觀察重點待核實"),
        ]
        fragments = []
        for row_index, (row_label, row_value) in enumerate(detail_rows):
            row = BeautifulSoup("", "html.parser").new_tag("div")
            row["class"] = ["earnings-detail-line"]
            row["style"] = "padding:6px 0;line-height:1.55;" + ("border-bottom:1px solid #dfe5e8;" if row_index < len(detail_rows)-1 else "")
            label = BeautifulSoup("", "html.parser").new_tag("strong")
            label["style"] = "display:block;font-size:12px;color:#53616b;margin-bottom:2px;"
            label.string = row_label
            value = BeautifulSoup("", "html.parser").new_tag("span")
            value.string = str(row_value)
            row.append(label)
            row.append(value)
            fragments.append(row)
        set_value_slot(value_node, fragments)
    elif len(fields) == 5:
        mapped = {
            "公布時段": schedule,
            "EPS": eps_line,
            "營收": rev_line,
            "財報判讀": item.get("judgment") or item.get("source_notes") or "觀察重點待核實",
        }
        seen = set()
        for field in fields:
            label_node = field.select_one("label")
            value_node = field.select_one(".earnings-detail-value")
            if label_node is None or value_node is None:
                raise ValueError("weekday earnings prototype is incomplete")
            name = label_node.get_text(" ", strip=True)
            if "公布時段" in name:
                key = "公布時段"
            elif "EPS" in name and "營收" not in name:
                key = "EPS"
            elif "營收" in name:
                key = "營收"
            elif "財報判讀" in name or "觀察重點" in name:
                key = "財報判讀"
            elif "來源" in name:
                fill_earnings_source_slot(value_node, item)
                seen.add("來源")
                continue
            else:
                raise ValueError(f"unsupported upcoming earnings mother field: {name}")
            set_text(value_node, mapped[key])
            seen.add(key)
        if seen != set(mapped) | {"來源"}:
            raise ValueError(f"weekday upcoming earnings fields incomplete: {sorted(seen)}")
    else:
        raise ValueError(f"unsupported upcoming earnings mother field count: {len(fields)}")


def validate_economic_card(card, context, expected_toggle):
    """Enforce the approved five-zone DOM contract on every rendered economic card."""
    details = card.find("div", class_="econ-details", recursive=False)
    if details is None:
        raise ValueError(f"{context}: .econ-details missing or not a direct child")
    children = [node for node in details.find_all("div", recursive=False)]
    if len(children) != 3:
        raise ValueError(f"{context}: expected exactly three direct detail zones, got {len(children)}")
    grid, impact, source = children
    if "econ-primary-grid" not in grid.get("class", []):
        raise ValueError(f"{context}: first detail zone must be .econ-primary-grid")
    expected = ["econ-prev", "econ-forecast", "econ-actual"]
    fields = grid.find_all("div", class_="econ-field", recursive=False)
    actual = [next((c for c in f.get("class", []) if c in expected), None) for f in fields]
    if actual != expected:
        raise ValueError(f"{context}: primary grid fields must be {expected}, got {actual}")
    for field, label in zip(fields, ("前值", "市場預估", "實際")):
        label_node = field.find("label", recursive=False)
        if label_node is None or label_node.get_text(strip=True) != label or field.select_one(".econ-value") is None:
            raise ValueError(f"{context}: malformed {label} field")
    for field, cls, label in ((impact, "econ-impact", "市場影響"), (source, "econ-source", "資料來源")):
        classes = field.get("class", [])
        label_node = field.find("label", recursive=False)
        if cls not in classes or "wide" not in classes or label_node is None or label_node.get_text(strip=True) != label or field.select_one(".econ-value") is None:
            raise ValueError(f"{context}: malformed full-width {label} field")
    grid_style = " ".join(str(x) for x in card.find_all("style"))
    # CSS is owned by the approved mother; validate the corresponding rule in the document separately.
    summary = card.find("summary", recursive=False)
    if summary is None or len(summary.find_all("span", class_=expected_toggle, recursive=False)) != 1:
        raise ValueError(f"{context}: expected exactly one {expected_toggle} control in summary")
    return True


def set_economic_source(card, item):
    field = card.select_one(".econ-source .econ-value")
    if field is None:
        raise ValueError("economic card source value node missing")
    field.clear()
    if item.get("source_url") and str(item["source_url"]).startswith("https://"):
        field.append(source_link(item["source_url"], item.get("source_name") or "來源"))
    else:
        field.append("來源待核實")

def recalculate_released_earnings(data, observed_at):
    """Recalculate released cards in both current and Monday retrospective sections."""
    counts = {"earnings": 0, "last_week_earnings": 0}
    for section in counts:
        for item in data.get(section, {}).get("events", []):
            if item.get("status") in ("released", "published", "completed"):
                apply_judgment(item, observed_at)
                counts[section] += 1
    return counts

def apply_report_layer_earnings_actuals(data):
    """Apply post-cutoff issuer results to this report only; never mutate main calendar JSON."""
    overlays = data.get("report_layer_earnings_actuals", [])
    if not overlays:
        return 0
    cutoff_text = str(data.get("report_cutoff_taipei") or "")[:16]
    try:
        cutoff = datetime.strptime(cutoff_text, "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise ValueError("report-layer earnings overlay requires an explicit Taipei report cutoff") from exc
    by_id = {x.get("id"): x for x in data.get("earnings", {}).get("events", [])}
    applied = 0
    for overlay in overlays:
        event_id = overlay.get("event_id")
        target = by_id.get(event_id)
        if target is None:
            raise ValueError(f"report-layer earnings overlay event not found in authoritative calendar: {event_id}")
        if target.get("ticker") != overlay.get("ticker") or target.get("event_date") != overlay.get("event_date"):
            raise ValueError(f"report-layer earnings overlay identity mismatch: {event_id}")
        event_dt = datetime.fromisoformat(str(target.get("event_date")))
        event_local = event_dt.astimezone(timezone(timedelta(hours=8))).replace(tzinfo=None) if event_dt.tzinfo else event_dt
        if event_local > cutoff:
            raise ValueError(f"report-layer earnings overlay is later than report cutoff: {event_id}")
        if target.get("status") in ("released", "published", "completed") or any(
            target.get(k) not in (None, "") for k in ("eps_actual", "revenue_actual")
        ):
            raise ValueError(f"refusing to overwrite authoritative post-release actuals: {event_id}")
        source = overlay.get("actual_source")
        if not isinstance(source, dict) or not str(source.get("url") or "").startswith("https://"):
            raise ValueError(f"report-layer earnings overlay lacks a verifiable issuer source: {event_id}")
        allowed = (
            "eps_actual", "eps_actual_display", "eps_actual_basis", "eps_actual_basis_code",
            "eps_actual_currency", "eps_actual_period", "revenue_actual", "revenue_actual_display",
            "revenue_actual_basis", "revenue_actual_basis_code", "revenue_actual_currency",
            "revenue_actual_unit", "revenue_actual_period", "judgment",
            "price_reaction",
        )
        for key in allowed:
            if key in overlay:
                target[key] = overlay[key]
        target["status"] = "released"
        target["report_layer_only"] = True
        target["actual_source"] = source
        target["source"] = source
        target["source_url"] = source["url"]
        target["source_name"] = source.get("name") or "發行公司官方公告"
        applied += 1
    return applied

def apply_report_layer_earnings_status(data):
    """Mark an elapsed release as published-but-unverified without fabricating actuals."""
    overlays = data.get("report_layer_earnings_status", [])
    if not overlays:
        return 0
    cutoff_text = str(data.get("report_cutoff_taipei") or "")[:16]
    try:
        cutoff = datetime.strptime(cutoff_text, "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise ValueError("report-layer earnings status requires an explicit Taipei report cutoff") from exc
    by_id = {x.get("id"): x for x in data.get("earnings", {}).get("events", [])}
    applied = 0
    for overlay in overlays:
        event_id = overlay.get("event_id")
        target = by_id.get(event_id)
        if target is None:
            raise ValueError(f"report-layer earnings status event not found in authoritative calendar: {event_id}")
        if target.get("ticker") != overlay.get("ticker") or target.get("event_date") != overlay.get("event_date"):
            raise ValueError(f"report-layer earnings status identity mismatch: {event_id}")
        event_dt = datetime.fromisoformat(str(target.get("event_date")))
        event_local = event_dt.astimezone(timezone(timedelta(hours=8))).replace(tzinfo=None) if event_dt.tzinfo else event_dt
        if event_local > cutoff:
            raise ValueError(f"report-layer earnings status is later than report cutoff: {event_id}")
        if overlay.get("status") != "pending_verification":
            raise ValueError(f"report-layer status overlay may only set pending_verification: {event_id}")
        if target.get("status") in ("released", "published", "completed") or any(
            target.get(k) not in (None, "") for k in ("eps_actual", "revenue_actual")
        ):
            raise ValueError(f"refusing to downgrade authoritative released actuals: {event_id}")
        source = overlay.get("status_source")
        if not isinstance(source, dict) or not str(source.get("url") or "").startswith("https://"):
            raise ValueError(f"report-layer earnings status lacks a verifiable publication-status source: {event_id}")
        target["status"] = "pending_verification"
        target["report_layer_status_only"] = True
        target["report_layer_status_source"] = source
        target["report_layer_status_note"] = overlay.get("note") or (
            "公告時間已過，第三方報導指出結果已發布；發行公司官方實際值尚待核實，" 
            "因此不填入實際EPS／營收，也不作優於／低於預期判斷。"
        )
        applied += 1
    return applied

def apply_last_week_earnings_actuals(data):
    """Apply verified late-reported earnings to Monday's prior-week projection only."""
    overlays = data.get("last_week_earnings_actuals", [])
    if not overlays:
        return 0
    events = data.get("last_week_earnings", {}).get("events", [])
    by_id = {str(item.get("id")): item for item in events}
    cutoff_text = str(data.get("report_cutoff_taipei") or "")[:16]
    try:
        cutoff = datetime.strptime(cutoff_text, "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise ValueError("last-week earnings overlays require an explicit Taipei report cutoff") from exc
    applied = 0
    allowed = (
        "eps_actual", "eps_actual_display", "eps_actual_basis", "eps_actual_basis_code",
        "eps_actual_currency", "eps_actual_period", "revenue_actual", "revenue_actual_display",
        "revenue_actual_basis", "revenue_actual_basis_code", "revenue_actual_currency",
        "revenue_actual_unit", "revenue_actual_period", "judgment", "price_reaction",
    )
    for row in overlays:
        event_id = str(row.get("event_id") or "").strip()
        target = by_id.get(event_id)
        if target is None:
            raise ValueError(f"last-week earnings overlay event not found: {event_id}")
        if target.get("ticker") != row.get("ticker") or target.get("event_date") != row.get("event_date"):
            raise ValueError(f"last-week earnings overlay identity mismatch: {event_id}")
        event_dt = datetime.fromisoformat(str(target.get("event_date") or target.get("date") or ""))
        event_local = event_dt.astimezone(timezone(timedelta(hours=8))).replace(tzinfo=None) if event_dt.tzinfo else event_dt
        if event_local > cutoff:
            raise ValueError(f"last-week earnings overlay is later than report cutoff: {event_id}")
        if target.get("status") in ("released", "published", "completed") or any(
            target.get(k) not in (None, "") for k in ("eps_actual", "revenue_actual")
        ):
            raise ValueError(f"refusing to overwrite authoritative prior-week earnings actuals: {event_id}")
        source = row.get("actual_source")
        if not isinstance(source, dict) or not str(source.get("url") or "").startswith("https://"):
            raise ValueError(f"last-week earnings overlay lacks a verifiable issuer source: {event_id}")
        for key in allowed:
            if key in row:
                target[key] = row[key]
        target["status"] = "released"
        target["report_layer_only"] = True
        target["actual_source"] = source
        target["source"] = source
        target["source_url"] = source["url"]
        target["source_name"] = source.get("name") or "發行公司官方公告"
        applied += 1
    print(f"PASS: applied {applied} prior-week earnings actuals in report layer; main JSON remains read-only")
    return applied


def apply_last_week_economic_overrides(data):
    """Apply verified late-reported economic actuals to Monday's report projection only."""
    overrides = data.get("last_week_economic_overrides", [])
    if not overrides:
        return 0
    events = data.get("last_week_calendar", {}).get("events", [])
    by_id = {str(item.get("id")): item for item in events}
    cutoff_text = str(data.get("report_cutoff_taipei") or "")[:16]
    try:
        cutoff = datetime.strptime(cutoff_text, "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise ValueError("last-week economic overrides require an explicit Taipei report cutoff") from exc
    applied = 0
    for row in overrides:
        event_id = str(row.get("event_id") or "").strip()
        target = by_id.get(event_id)
        if target is None:
            raise ValueError(f"last-week economic override event not found: {event_id}")
        if target.get("status") not in ("upcoming", "scheduled") or target.get("actual") not in (None, ""):
            raise ValueError(f"last-week economic override refused: event is not an unreleased empty record: {event_id}")
        event_dt = datetime.fromisoformat(str(target.get("date") or ""))
        event_local = event_dt.astimezone(timezone(timedelta(hours=8))).replace(tzinfo=None) if event_dt.tzinfo else event_dt
        if event_local > cutoff:
            raise ValueError(f"last-week economic override is later than report cutoff: {event_id}")
        actual = str(row.get("actual") or "").strip()
        if len(actual) < 3 or re.match(r"^https?://", actual, re.I):
            raise ValueError(f"last-week economic override actual must be explanatory data text: {event_id}")
        source_url = str(row.get("source_url") or "").strip()
        if not source_url.startswith("https://"):
            raise ValueError(f"last-week economic override lacks a verifiable HTTPS source: {event_id}")
        target["actual"] = actual
        target["status"] = "released"
        target["source_url"] = source_url
        target["source_name"] = str(row.get("source_name") or "官方發布來源")
        target["report_layer_only"] = True
        target["actual_source_note"] = str(row.get("note") or "simulation report-layer correction; authoritative main JSON unchanged")
        applied += 1
    print(f"PASS: applied {applied} last-week economic actuals in report layer; main JSON remains read-only")
    return applied


def apply_calendar_impact_overrides(data):
    """Repair known URL-corrupted impact text in the report layer only."""
    overrides = data.get("calendar_impact_overrides", [])
    if not overrides:
        return 0
    events = data.get("calendar", {}).get("events", [])
    by_id = {str(item.get("id")): item for item in events}
    applied = 0
    for row in overrides:
        event_id = str(row.get("event_id") or "").strip()
        target = by_id.get(event_id)
        if target is None:
            raise ValueError(f"calendar impact override event not found: {event_id}")
        current = str(target.get("impact") or "").strip()
        if not re.match(r"^https?://", current, re.I):
            raise ValueError(f"calendar impact override refused: source field is not a URL for {event_id}")
        # In the authoritative W48 schema the source URL was mistakenly placed
        # in impact_judgment while source is a plain-text source name. Preserve
        # that URL as source_url before replacing the corrupted impact field.
        existing_source_url = str(target.get("source_url") or "").strip()
        if existing_source_url and not existing_source_url.startswith("https://"):
            raise ValueError(f"calendar impact override found an invalid existing source_url: {event_id}")
        if not existing_source_url:
            target["source_url"] = current
        if not target.get("source_name") and isinstance(target.get("source"), str):
            target["source_name"] = target["source"]
        replacement = str(row.get("impact") or "").strip()
        if len(replacement) < 20 or re.match(r"^https?://", replacement, re.I):
            raise ValueError(f"calendar impact override must be explanatory text, not a URL: {event_id}")
        target["impact"] = replacement
        target["impact_override_note"] = str(row.get("note") or "simulation report-layer correction; authoritative main JSON unchanged")
        applied += 1
    print(f"PASS: applied {applied} report-layer calendar impact corrections; main JSON remains read-only")
    return applied


def earnings_comparison_status(item, metric):
    """Read the persisted, versioned judgment; HTML assembly never infers Beat/Miss."""
    return render_status(item, metric)


def earnings_status_label(item, metric, state):
    """Name missing consensus explicitly when actual results are already published."""
    labels = {
        "beat": "優於預期",
        "miss": "低於預期",
        "inline": "符合預期",
    }
    if item.get("_calendar_publication_state") == "cancelled":
        return "已取消"
    if item.get("_calendar_publication_state") == "postponed":
        return "已延期／改期後續公布"
    if state == "pending":
        if item.get("_calendar_publication_state") == "pending_verification":
            return (
                "公告已發布；實際值待核實"
                if has_release_status_evidence(item)
                else "公布狀態待核實"
            )
        if item.get("status") == "pending_verification":
            return "公布狀態待核實"
        reason = str(item.get(f"{metric}_comparison_reason") or "")
        if reason.startswith("comparison_inputs_not_comparable:"):
            return "比較資料尚未齊備"
        actual_key, estimate_key = (
            ("eps_actual", "eps_estimate") if metric == "eps"
            else ("revenue_actual", "revenue_estimate")
        )
        actual, estimate = item.get(actual_key), item.get(estimate_key)
        if actual not in (None, "") and estimate in (None, ""):
            return "比較資料尚未齊備"
        return "尚未公布"
    return labels.get(state, "尚未公布")


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
        "pending": "尚未公布",
    }
    render_state = item.get("_calendar_publication_state")
    raw = "" if render_state in ("cancelled", "postponed") else str(item.get("judgment") or "").strip()
    kept = []
    if render_state == "cancelled":
        kept.append("財報已取消；不作實際值或優於／低於預期判讀。")
    elif render_state == "postponed":
        kept.append("財報已延期；以最新改期資訊為準，不作原定日期的公布判讀。")
    elif render_state == "pending_verification" or (render_state is None and item.get("status") == "pending_verification"):
        if has_release_status_evidence(item):
            note = item.get("report_layer_status_note") or (
                "公告已發布；發行公司官方實際值尚待核實，因此不填入實際 EPS／營收，也不作優於／低於預期判斷。"
            )
        else:
            note = "預定時間已過，但尚無可核實的發布證據；實際值及優於／低於預期判斷均待核實。"
        kept.append(note)
    elif item.get("status") == "pending_verification":
        kept.append("公布狀態待核實；在取得可核實發布證據前，不填入實際值或作優於／低於預期判斷。")
    for fragment in re.split(r"(?<=[。！？])\s*|[；;]\s*|(?<=\.)\s+(?=[A-Z])", raw):
        part = fragment.strip()
        if not part:
            continue
        # Drop stale legacy "not yet published / values incomplete" labels;
        # the current status is regenerated below from actual/estimate fields.
        legacy_pending = bool(re.search(
            r"(?:EPS|營收|revenue).{0,40}(?:尚未公布／數值尚未齊備|預期資料尚未取得|尚未公布)",
            part,
            flags=re.IGNORECASE,
        ))
        if legacy_pending:
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
        # Directional verdicts are regenerated below from the single-source
        # judgment engine. Never retain an old matching verdict: doing so
        # duplicates EPS/revenue labels each time a Monday retrospective card
        # is recalculated.
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

    summary = "；".join(
        f"{metric.upper() if metric == 'eps' else '營收'}：{earnings_status_label(item, metric, statuses[metric])}"
        for metric in ("eps", "revenue")
    )
    return ("；".join(kept) + ("；" if kept else "") + summary)


def parse_fear_greed_score(value):
    """Return a validated 0..100 Fear & Greed score, or None when unavailable."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        score = float(value)
    else:
        match = re.fullmatch(r"\s*(\d{1,3}(?:\.\d+)?)\s*(?:/100)?\s*", str(value or ""))
        if not match:
            return None
        score = float(match.group(1))
    return score if 0 <= score <= 100 else None


def fear_greed_band(value):
    """Map the validated 0..100 CNN Fear & Greed score to its canonical five bands."""
    score = parse_fear_greed_score(value)
    if score is None:
        return ("Unavailable", "待核實")
    if score <= 24:
        return ("Extreme Fear", "極度恐懼")
    if score <= 44:
        return ("Fear", "恐懼")
    if score <= 55:
        return ("Neutral", "中性")
    if score <= 74:
        return ("Greed", "貪婪")
    return ("Extreme Greed", "極度貪婪")


def apply_fear_greed_status(status_node, value):
    """Keep the visible English/Chinese sentiment labels synchronized with the score."""
    english, chinese = fear_greed_band(value)
    english_node = status_node.select_one("span")
    chinese_node = status_node.select_one("b")
    if english_node is None or chinese_node is None:
        raise ValueError("CNN Fear & Greed status must contain English span and Chinese bold label")
    set_text(english_node, english)
    set_text(chinese_node, chinese)
    status_node["aria-label"] = f"{english} / {chinese}"
    return english, chinese


def apply_fear_greed_marker(marker, value):
    """Bind the visible marker to the validated source score, overriding mother CSS."""
    numeric_score = parse_fear_greed_score(value)
    if numeric_score is None:
        marker["style"] = "display: none !important;"
        marker["aria-hidden"] = "true"
        marker.attrs.pop("data-score", None)
        marker.attrs.pop("aria-label", None)
        return None
    marker["style"] = f"left: {numeric_score:g}% !important;"
    marker["data-score"] = f"{numeric_score:g}"
    marker["aria-label"] = f"Fear and Greed score {numeric_score:g} out of 100"
    marker.attrs.pop("aria-hidden", None)
    return numeric_score


def set_leaf_text_preserving_dom(node, value, context):
    """Replace only a leaf text slot; refuse to delete or flatten child elements."""
    if node is None:
        raise ValueError(f"{context}: required mother text slot missing")
    if any(getattr(child, "name", None) for child in node.contents):
        raise ValueError(f"{context}: target contains child elements; refusing destructive text replacement")
    text_nodes = [child for child in node.contents if isinstance(child, NavigableString)]
    if text_nodes:
        text_nodes[0].replace_with(str(value))
        for extra in text_nodes[1:]:
            extra.extract()
    else:
        node.append(str(value))


def replace_text_after_bold_preserving_dom(container, replacements, context):
    """Update existing text nodes after fixed bold labels; keep every b/br wrapper intact."""
    found = set()
    for label in container.find_all(["b", "strong"]):
        key = label.get_text(" ", strip=True).rstrip("：: ")
        if key not in replacements:
            continue
        sibling = label.next_sibling
        while sibling is not None and isinstance(sibling, NavigableString) and not str(sibling).strip():
            sibling = sibling.next_sibling
        if not isinstance(sibling, NavigableString):
            raise ValueError(f"{context}: text slot after label {key!r} is missing or not a text node")
        sibling.replace_with(" " + str(replacements[key]))
        found.add(key)
    missing = sorted(set(replacements) - found)
    if missing:
        raise ValueError(f"{context}: approved bold labels missing: {missing}")


def populate_earnings_health_dashboard_preserving_dom(health, earnings_health, monday):
    """Populate the approved dashboard's existing text slots without rebuilding its cards or layout."""
    if health is None:
        raise ValueError("S&P 500 earnings-health dashboard missing from approved mother")
    required = (
        "as_of_date", "reported_pct", "eps_beat_pct", "revenue_beat_pct",
        "blended_eps_yoy", "blended_revenue_yoy", "eps_surprise",
        "forward_pe", "interpretation", "source_url",
    )
    missing = [key for key in required if not str(earnings_health.get(key, "")).strip()]
    if missing:
        raise ValueError("FactSet earnings-health snapshot missing fields: " + ", ".join(missing))
    if not str(earnings_health["source_url"]).startswith("https://"):
        raise ValueError("FactSet earnings-health snapshot must include an HTTPS source URL")

    direct_divs = health.find_all("div", recursive=False)
    if len(direct_divs) != 5 or "title" not in direct_divs[0].get("class", []):
        raise ValueError("S&P 500 earnings-health mother structure changed; expected title/core/grid/interpretation/next-step")
    title, core, grid, interpretation, next_steps = direct_divs
    title_small = title.find("small", recursive=False)
    set_leaf_text_preserving_dom(
        title_small,
        f"{earnings_health.get('source', 'FactSet')}｜{earnings_health['as_of_date']}（{earnings_health.get('period', 'Q3 2026')}；{earnings_health['reported_pct']} 成份股已公布）",
        "earnings-health snapshot title",
    )

    core_parts = core.find_all("div", recursive=False)
    if len(core_parts) != 3:
        raise ValueError("earnings-health core interpretation must retain its three mother text slots")
    surprise_avg = earnings_health.get("eps_surprise_avg_5y", "待核實")
    headline = (
        f"{earnings_health.get('period', '本季')}獲利與營收年增仍強；"
        f"EPS 平均超預期 {earnings_health['eps_surprise']}，需與歷史均值比較。"
    )
    description = (
        f"截至 {earnings_health['as_of_date']}，{earnings_health['reported_pct']} 的 S&P 500 成份股已公布財報；"
        f"混合 EPS 年增 {earnings_health['blended_eps_yoy']}、混合營收年增 {earnings_health['blended_revenue_yoy']}。"
        f"{earnings_health['interpretation']}"
    )
    set_leaf_text_preserving_dom(core_parts[1], headline, "earnings-health core headline")
    set_leaf_text_preserving_dom(core_parts[2], description, "earnings-health core explanation")

    cards = grid.find_all("div", recursive=False)
    expected_card_count = 4 if monday else 3
    if len(cards) != expected_card_count:
        raise ValueError(
            f"earnings-health mother card count changed: expected {expected_card_count}, got {len(cards)}"
        )
    seen = set()
    for index, card in enumerate(cards, 1):
        parts = card.find_all("div", recursive=False)
        if len(parts) != 3:
            raise ValueError(f"earnings-health card #{index} must retain label/value/note slots")
        label = parts[0].get_text(" ", strip=True)
        if "混合盈餘年增率" in label:
            key = "mixed_eps"
            value = earnings_health["blended_eps_yoy"]
            prior = earnings_health.get("prior_blended_eps_yoy")
            note = f"前期 {prior}；{earnings_health['as_of_date']} FactSet 快照" if prior else f"FactSet 快照｜{earnings_health['as_of_date']}"
        elif "EPS 優於預期" in label:
            key = "eps_beat"
            value = earnings_health["eps_beat_pct"]
            note = (
                f"高於 5 年均值 {earnings_health.get('eps_beat_avg_5y', '待核實')}／"
                f"10 年均值 {earnings_health.get('eps_beat_avg_10y', '待核實')}"
            )
        elif "EPS 平均超預期幅度" in label or "平均 EPS 超預期幅度" in label:
            key = "eps_surprise"
            value = earnings_health["eps_surprise"]
            note = (
                f"5 年均值 {earnings_health.get('eps_surprise_avg_5y', '待核實')}／"
                f"10 年均值 {earnings_health.get('eps_surprise_avg_10y', '待核實')}"
            )
        elif "混合營收年增率" in label:
            key = "mixed_revenue"
            value = earnings_health["blended_revenue_yoy"]
            prior = earnings_health.get("prior_blended_revenue_yoy")
            note = f"前期 {prior}；{earnings_health['as_of_date']} FactSet 快照" if prior else f"FactSet 快照｜{earnings_health['as_of_date']}"
        else:
            raise ValueError(f"unmapped earnings-health mother card label: {label!r}")
        if key in seen:
            raise ValueError(f"duplicate earnings-health mother card: {key}")
        seen.add(key)
        if "｜" in label:
            label = label.split("｜", 1)[0] + "｜" + earnings_health["as_of_date"]
            set_leaf_text_preserving_dom(parts[0], label, f"earnings-health card #{index} label")
        set_leaf_text_preserving_dom(parts[1], value, f"earnings-health card #{index} value")
        set_leaf_text_preserving_dom(parts[2], note, f"earnings-health card #{index} note")
    expected_keys = {"mixed_eps", "eps_beat", "eps_surprise"}
    if monday:
        expected_keys.add("mixed_revenue")
    if seen != expected_keys:
        raise ValueError(f"earnings-health mother card mapping mismatch: {sorted(seen)}")

    interpretation_parts = interpretation.find_all("div", recursive=False)
    if len(interpretation_parts) != 2:
        raise ValueError("earnings-health interpretation block must retain its title and body")
    body = interpretation_parts[1]
    if monday:
        replacements = {
            "正面": (
                f"{earnings_health['eps_beat_pct']} EPS、{earnings_health['revenue_beat_pct']} 營收優於預期；"
                f"混合 EPS 年增 {earnings_health['blended_eps_yoy']}、營收年增 {earnings_health['blended_revenue_yoy']}。"
                f"Mag 7 EPS 成長 {earnings_health.get('mag7_eps_growth', '待核實')}、其他 493 家 {earnings_health.get('other_493_eps_growth', '待核實')}。"
            ),
            "保留": (
                f"EPS 平均超預期 {earnings_health['eps_surprise']}，5 年均值 {surprise_avg}；"
                f"營收平均超預期 {earnings_health.get('revenue_surprise', '待核實')}。"
                f"Mag 7 EPS 成長 {earnings_health.get('mag7_eps_growth', '待核實')}；"
                f"其他 493 家公司 EPS 成長 {earnings_health.get('other_493_eps_growth', '待核實')}。"
            ),
            "估值": (
                f"Forward 12M P/E {earnings_health['forward_pe']}；"
                f"5 年均值 {earnings_health.get('forward_pe_avg_5y', '待核實')}／"
                f"10 年均值 {earnings_health.get('forward_pe_avg_10y', '待核實')}。"
            ),
        }
    else:
        replacements = {
            "混合營收年增率": f"{earnings_health['blended_revenue_yoy']}（{earnings_health['as_of_date']} FactSet 快照）",
            "營收優於預期公司比率": (
                f"{earnings_health['revenue_beat_pct']}；5 年均值 "
                f"{earnings_health.get('revenue_beat_avg_5y', '待核實')}／10 年均值 "
                f"{earnings_health.get('revenue_beat_avg_10y', '待核實')}"
            ),
            "保留": (
                f"EPS 平均超預期 {earnings_health['eps_surprise']}，5 年均值 {surprise_avg}；"
                f"Forward 12M P/E {earnings_health['forward_pe']}，"
                f"5 年均值 {earnings_health.get('forward_pe_avg_5y', '待核實')}／"
                f"10 年均值 {earnings_health.get('forward_pe_avg_10y', '待核實')}；"
                f"Mag 7 EPS 成長 {earnings_health.get('mag7_eps_growth', '待核實')}；"
                f"其他 493 家公司 EPS 成長 {earnings_health.get('other_493_eps_growth', '待核實')}；"
                f"{earnings_health['interpretation']}"
            ),
        }
    replace_text_after_bold_preserving_dom(body, replacements, "earnings-health interpretation")

    replace_text_after_bold_preserving_dom(
        next_steps,
        {"接下來看三件事": (
            "EPS 超預期幅度能否回升、營收成長能否延續，以及獲利成長是否持續擴散至更多產業。"
        )},
        "earnings-health next steps",
    )
    # The approved Monday mother carried a stale October-only S&P 500
    # calendar sentence. Refresh its existing trailing span from the current
    # report snapshot; never leave a previous report week's count/date behind.
    stale_week_note = next_steps.find("span")
    if stale_week_note is not None:
        week_start = str(data.get("earnings", {}).get("week_start", ""))
        week_end = str(data.get("earnings", {}).get("week_end", ""))
        snapshot_date = str(earnings_health.get("as_of_date", ""))
        if not (week_start and week_end and snapshot_date):
            raise ValueError("earnings-health current-week note requires week range and FactSet snapshot date")
        set_leaf_text_preserving_dom(
            stale_week_note,
            f"FactSet 快照截至 {snapshot_date}；本週公司公布時程請以 {week_start}～{week_end} 財報行事曆為準。",
            "earnings-health current-week note",
        )

    source_details = health.find("details", recursive=False)
    source_body = source_details.find("div", recursive=False) if source_details else None
    if source_body is None:
        raise ValueError("earnings-health source disclosure body missing")
    source_text = next(
        (node for node in source_body.contents if isinstance(node, NavigableString) and str(node).strip()),
        None,
    )
    if source_text is None:
        raise ValueError("earnings-health source disclosure text slot missing")
    source_text.replace_with(
        f"{earnings_health.get('source', 'FactSet')}；統計截點 {earnings_health['as_of_date']}。"
        "混合盈餘／營收成長率結合已公布實績與尚未公布公司的分析師預估。"
    )
    source_link_node = source_body.find("a")
    if source_link_node is None:
        raise ValueError("earnings-health source link slot missing from approved mother")
    source_link_node["href"] = earnings_health["source_url"]
    source_link_node.string = "FactSet 官方報告"
    return {"cards": len(cards), "card_keys": sorted(seen), "source_date": earnings_health["as_of_date"]}



def update_market_sentiment_interpretation_preserving_dom(sentiment_section, sentiment_text):
    """Update the existing final sentiment card's text slot without rebuilding its wrapper."""
    if sentiment_section is None:
        raise ValueError("market sentiment section missing from approved mother")
    cards = sentiment_section.select(".sbox")
    if not cards:
        raise ValueError("market sentiment interpretation card missing from approved mother")
    interpretation = cards[-1]
    parts = interpretation.find_all("div", recursive=False)
    if len(parts) != 2 or "label" not in parts[0].get("class", []):
        raise ValueError("market sentiment interpretation mother card must retain label and body slots")
    if parts[0].get_text(" ", strip=True) != "📌 核心解讀":
        raise ValueError("market sentiment interpretation label changed unexpectedly")
    set_leaf_text_preserving_dom(parts[1], sentiment_text, "market sentiment interpretation")
    return interpretation


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--expected-master-sha", required=True)
    ap.add_argument("--key-levels-live", help="optional live OHLC capture envelope produced by collect_key_levels_ohlc.py")
    ap.add_argument("--price-reactions", help="optional Yahoo Finance earnings reaction capture JSON")
    ap.add_argument("--earnings-consensus-projection", help="optional SHA-pinned TAC-observed earnings consensus projection")
    args=ap.parse_args()
    data=json.loads(Path(args.data).read_text())
    # Gate 0: never trust calendar copies embedded in fixtures or the simulation branch.
    # Fetch origin/main and read both ISO weeks from that immutable main commit only.
    calendar_source = load_authoritative_calendar(data["report_date"])
    data.update(project_calendar_data(calendar_source))
    apply_last_week_economic_overrides(data)
    apply_last_week_earnings_actuals(data)
    apply_calendar_impact_overrides(data)
    # Recalculate released cards in both the current week and Monday's prior-week section.
    # Numeric consensus/actual pairs are sufficient; PIT and basis metadata remain disclosures.
    recalculate_released_earnings(
        data, data.get("report_cutoff_taipei") or data["report_date"]
    )
    if args.earnings_consensus_projection:
        consensus_projection=json.loads(Path(args.earnings_consensus_projection).read_text(encoding="utf-8"))
        apply_consensus_projection(data, consensus_projection, calendar_source)
        # Apply pre-release estimates first, then recalculate already-released cards.
        recalculate_released_earnings(
            data, data.get("report_cutoff_taipei") or data["report_date"]
        )
    elif data.get("report_date") == "2026-11-16":
        data["earnings_consensus_projection_status"] = {
            "status": "not_available",
            "source": "main_calendar_only",
            "reason": (
                "The authoritative main W47 calendar contains no accepted EPS/revenue "
                "consensus values. Per SIM-1.3, upcoming earnings cards must display "
                "預期資料尚未取得. Do not read simulation-branch calendar snapshots or infer estimates."
            ),
        }
    report_layer_actuals_applied = apply_report_layer_earnings_actuals(data)
    if report_layer_actuals_applied:
        recalculate_released_earnings(
            data, data.get("report_cutoff_taipei") or data["report_date"]
        )
    report_layer_status_applied = apply_report_layer_earnings_status(data)
    if args.price_reactions:
        reaction_doc=json.loads(Path(args.price_reactions).read_text(encoding="utf-8"))
        reaction_calendar_side = "previous" if datetime.fromisoformat(data["report_date"]).weekday() == 0 else "current"
        if (reaction_doc.get("main_commit_sha") != calendar_source["main_commit_sha"]
                or reaction_doc.get("calendar_blob_sha") != calendar_source[reaction_calendar_side]["blob_sha"]
                or reaction_doc.get("calendar_side", reaction_calendar_side) != reaction_calendar_side):
            raise ValueError("earnings price reaction snapshot does not match the authoritative report-week calendar SHA")
        reaction_map=reaction_doc.get("reactions",{})
        reaction_target = "last_week_earnings" if reaction_calendar_side == "previous" else "earnings"
        for event in data.get(reaction_target,{}).get("events",[]):
            reaction=reaction_map.get(event.get("id"))
            if reaction:
                event["price_reaction"]=reaction.get("display")
                event["price_reaction_source"]=reaction.get("source")
                event["price_reaction_source_url"]=reaction.get("source_url")
    is_live_key_levels = False
    if args.key_levels_live:
        live=json.loads(Path(args.key_levels_live).read_text(encoding="utf-8"))
        if live.get("report_date") != data.get("report_date"):
            raise ValueError("live key-level report_date does not match report JSON")
        is_live_key_levels = (
            bool(live.get("captured_at_taipei"))
            and live.get("captured_at_taipei") != "fixture-only"
            and live.get("source") != "deterministic fixture; not live market data"
        )
        levels=live.get("key_levels")
        if not isinstance(levels, dict) or levels.get("baseline_date") != live.get("trading_date"):
            raise ValueError("live key-level baseline_date/trading_date mismatch")
        required_keys=("dow","sp500","nasdaq","sox","russell2000")
        rows=levels.get("items")
        if not isinstance(rows,list) or [row.get("key") for row in rows] != list(required_keys):
            raise ValueError("live key-level artifact must contain the five required indices in canonical order")
        for row in rows:
            if row.get("trading_date") != live.get("trading_date") or row.get("quote_type") != "cash_index":
                raise ValueError(f"live key-level row has invalid trading date or quote type: {row.get('key')}")
            if not row.get("source_name") or not str(row.get("url","")).startswith("https://"):
                raise ValueError(f"live key-level row missing source attribution: {row.get('key')}")
            if not all(row.get(field) for field in ("s2","s1","p","r1","r2","ohlc")):
                raise ValueError(f"live key-level row missing calculated levels/OHLC: {row.get('key')}")
        data["key_levels"]=levels
    # Explicit CFD index proxies must never render as official/cash index closes.
    rejected_cfd_indices = reject_cfd_cash_index_quotes(data)
    # Fail closed on quote records without a traceable source and item-level date.
    # A top-level trading_date is not evidence that every market item was updated that day.
    market_groups = ["global_markets", "bonds", "fx", "energy", "metals"]
    for group_name in market_groups:
        for item_name, record in data.get(group_name, {}).items():
            source = record.get("source") if isinstance(record, dict) else None
            if not isinstance(source, dict) or not source.get("name") or not source.get("url") or not source.get("data_date"):
                if isinstance(record, dict):
                    record["display"] = "待核實"
                    record["change_display"] = "待核實"
                    record["qa_status"] = "missing_item_source_or_date"
    for key in ["vix", "move", "fear_greed"]:
        record = data.get("risk", {}).get(key, {})
        source = record.get("source") if isinstance(record, dict) else None
        item_date = (source or {}).get("data_date") or record.get("as_of_date") or record.get("as_of")
        if not isinstance(source, dict) or not source.get("name") or (not source.get("url") and source.get("quote_type") != "user_supplied_market_quote_screenshot") or not item_date:
            record["display"] = "待核實"
            record["change_display"] = "待核實"
            record["qa_status"] = "missing_item_source_or_date"
    sector_sources = data.get("sector_sources", {})
    for ticker in list(data.get("sectors", {})):
        source = sector_sources.get(ticker, {})
        if not source.get("name") or not source.get("url") or not source.get("data_date"):
            data["sectors"][ticker] = "待核實"
    report_date=datetime.fromisoformat(data["report_date"]).date()
    if data.get("timezone")!="Asia/Taipei": raise SystemExit("timezone mismatch")
    monday = report_date.weekday()==0
    manifest=json.loads(MANIFEST.read_text())
    template_record = manifest["templates"]["monday" if monday else "weekdays"]
    master_path = ROOT / template_record.get("simulation_path", "simulation-lab/baseline/weekday-mother-template.html")
    raw = master_path.read_text(encoding="utf-8")
    actual=sha_blob(raw)
    approved=template_record["simulation_blob_sha"]
    if actual!=approved or actual!=args.expected_master_sha:
        raise SystemExit(f"SIMULATION MASTER SHA FAIL actual={actual} manifest={approved} expected={args.expected_master_sha}")
    if report_date.weekday()>=5: raise SystemExit("weekend report date is not allowed")
    report_iso=report_date.isoformat()
    report_label=f"{report_date.year}/{report_date.month:02d}/{report_date.day:02d}"
    report_weekday="一二三四五六日"[report_date.weekday()]
    report_cutoff=str(data.get("report_cutoff_taipei") or f"{report_label} 05:25")
    previous_trade=data.get("trading_date","待核實")
    key_levels_date_label = previous_trade[5:].replace("-", "/") if len(previous_trade) == 10 else previous_trade
    report_context=f"週一版；美股行情採 {previous_trade} 正式收盤，其他市場依各自最近交易日核對。" if monday else f"週二至週五版；行情採 {previous_trade} 最近正式收盤。"
    soup=BeautifulSoup(raw,"html.parser")
    # Remove a legacy hidden test meta tag whose stale text says key levels are unverified.
    # The generated report now includes source-checked five-index S2/S1/P/R1/R2 levels.
    for stale_meta in soup.find_all("meta", attrs={"name": "tac-correction-test"}):
        stale_meta.decompose()
    provenance = {"repository": "lion-invlab/lion-invlab.github.io", "branch": "main", "main_commit_sha": calendar_source["main_commit_sha"], "current": {k:v for k,v in calendar_source["current"].items() if k != "payload"}, "previous": {k:v for k,v in calendar_source["previous"].items() if k != "payload"}, "mode": "READ_ONLY"}
    head_node = soup.select_one("head")
    if head_node is None: raise ValueError("HTML head missing; cannot record authoritative calendar provenance")
    head_node.append(Comment(" TAC_CALENDAR_SOURCE " + json.dumps(provenance, ensure_ascii=False, separators=(",", ":"))))
    fed_title = soup.select_one(".fed-live-title")
    if fed_title: set_text(fed_title, "Fed 限時動態")
    for anchor in soup.select("#tac-assets-panel-3 .energy-card .row > b a"):
        label = anchor.get_text(" ", strip=True)
        if label == "WTI原油期貨": set_text(anchor, "WTI 原油期貨")
        elif label == "Brent原油期貨": set_text(anchor, "Brent 原油期貨")
    # Date/title: update only existing text nodes.
    for node in soup.select(".top .report-date, header .report-date"):
        if node.get_text(strip=True):
            # Keep the approved compact inline header; market-basis detail belongs in report content, not the masthead.
            set_text(node,f"｜{report_label}（{report_weekday}）")
    for node in soup.select(".top .date, header .date, .date-line"):
        if node.get_text(strip=True):
            set_text(node,f"{report_label}（{report_weekday}）")
    for node in soup.select("title"):
        set_text(node,f"TAC 投資早報｜{report_label}")
    # Refresh the date shown in the "今日觀察重點" section title.
    focus_heading = soup.select_one(".today-focus-title")
    if focus_heading:
        heading_text = focus_heading.get_text(" ", strip=True)
        if "今日觀察重點" in heading_text:
            heading_text = f"今日觀察重點｜{report_label}（{report_weekday}）"
        set_text(focus_heading, heading_text)
    # The mother template carries a historical report-date meta tag; replace it for every daily build.
    report_date_meta = soup.select_one('meta[name="report-date"]')
    if report_date_meta:
        report_date_meta["content"] = report_iso
    # Enforce the mother-locked daily-report boundary: no one-off DOM/CSS injection is allowed.
    # Extraordinary-event content must first have a mother-owned slot and an approved CSS contract.
    special = data.get("special_focus")
    if special:
        raise ValueError(
            "special_focus cannot be injected into the daily report: no mother-owned slot is approved; "
            "refusing to append custom DOM or CSS"
        )

    # Update the approved summary card's text slot without changing wrappers.
    bluf=unique(soup,"#overview > section.grid.two > article.card.bluf","summary")
    summary=unique(bluf, ".key, .bluf-content, p","summary content")
    summary_title = validate_summary_title(data.get("summary_title"))
    set_text(unique(bluf, "h1", "summary headline"), summary_title)
    populate_summary_points_preserving_dom(summary, data.get("summary_points"))
    # Market sentiment narrative: replace the dedicated final interpretation card,
    # not metric source/disclosure blocks (the mother template has no paragraph slot).
    sent=unique(soup,"#sentiment","sentiment")
    interpretation = update_market_sentiment_interpretation_preserving_dom(sent, data["sentiment"])
    rendered_summary_title = unique(bluf, "h1", "summary headline").get_text(" ", strip=True)
    if rendered_summary_title != summary_title or rendered_summary_title in SUMMARY_HEADING_LABELS:
        raise ValueError("summary headline failed semantic DOM verification")
    if data.get("sentiment") and data["sentiment"] not in interpretation.get_text(" ", strip=True):
        raise ValueError("market sentiment interpretation did not render from current report data")
    if "10/27 已核實" in sent.get_text(" ", strip=True):
        raise ValueError("stale mother-template sentiment interpretation remains")
    # Rebuild every news card's complete data-bearing fields from the current JSON.
    # Never retain mother-template source URLs, publication timestamps or report-window labels.
    from urllib.parse import urlparse
    # Derive the report-specific news window before rendering either news section.
    news_window_start = (report_date - timedelta(days=3 if monday else 1)).strftime("%Y/%m/%d")
    news_window_start_label = news_window_start + " 12:00"
    news_cutoff = str(data.get("news_cutoff_taipei") or report_cutoff)
    try:
        news_cutoff_dt = datetime.strptime(news_cutoff[:16], "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise ValueError("news_cutoff_taipei must be an explicit Taipei YYYY-MM-DD HH:MM timestamp") from exc
    news_start_dt = datetime.strptime(news_window_start + " 12:00", "%Y/%m/%d %H:%M")
    if news_cutoff_dt < news_start_dt:
        raise ValueError("news cutoff precedes the Monday/weekday news-window start")
    news_window_end_label = news_cutoff_dt.strftime("%Y/%m/%d %H:%M")
    news_window_label = f"{news_window_start_label}–{news_window_end_label}（台灣時間）"
    for section_id, items_key, expected, section_label in [
        ("global-focus","focus_news",5,"全球焦點"),
        ("headlines","headlines",10,"市場熱門頭條")
    ]:
        box=unique(soup,f"#{section_id}",section_id)
        nodes=box.select(".newsitem")
        items=data[items_key]
        if len(items)!=expected:
            raise ValueError(f"{items_key}: expected exactly {expected} current records, got {len(items)}")
        if len(nodes)<expected:
            raise ValueError(f"{section_id}: mother cards {len(nodes)} < {expected}")
        for idx,item in enumerate(items):
            if not item.get("title") or not item.get("summary") or not item.get("url") or not item.get("published_at_tw"):
                raise ValueError(f"{items_key}[{idx}]: title/summary/url/published_at_tw required")
            if not str(item["url"]).startswith("https://"):
                raise ValueError(f"{items_key}[{idx}]: non-HTTPS source URL")
            node=nodes[idx]
            title=unique(node,".news-title, h3, h4, strong",f"{section_id}[{idx}] title")
            prefix=(f"{idx+1}. " if section_id=="global-focus" else f"{idx+1:02d}｜")
            set_text(title,prefix+item["title"])
            summary_nodes=node.select(".news-summary, p, .summary")
            if not summary_nodes:
                raise ValueError(f"{section_id}[{idx}]: summary slot missing")
            set_text(summary_nodes[0],item["summary"])
            meta=unique(node,".newsmeta",f"{section_id}[{idx}] source metadata")
            meta.clear()
            host=urlparse(item["url"]).hostname or "原始來源"
            source=soup.new_tag("a",href=item["url"],target="_blank",rel="noopener")
            published_source = str(item.get("published_at_source") or item['published_at_tw'])
            source_timezone = str(item.get("source_timezone") or "Asia/Taipei")
            published_display = f"{published_source} {source_timezone}" if source_timezone == "Asia/Taipei" else f"{published_source} {source_timezone}（台灣 {item['published_at_tw']}）"
            updated_source = str(item.get("updated_at_source") or item.get("updated_at_tw") or "原文未標示")
            updated_tw = str(item.get("updated_at_tw") or "原文未標示")
            updated_display = updated_source if ("未標示" in updated_source or "未提供絕對時間" in updated_source) else f"{updated_source}（台灣 {updated_tw}）"
            source.string=f"{host}｜原文發布 {published_display}｜最後更新 {updated_display}｜閱讀原文 ↗"
            meta.append(source)
        # Keep the report date and window visible in both news section headers.
        panel_meta=box.select_one(".tab-panel-meta")
        if panel_meta:
            set_text(panel_meta,f"{section_label}｜報告日期 {report_label}｜新聞時間窗：{news_window_label}")
        warning=box.select_one(".news-window-warning")
        if warning and section_id=="global-focus":
            set_text(warning,f"新聞時間窗｜{news_window_label}（台灣時間）。以下 5 則逐則列出發布時間與原始來源；不以行情報價或波動率數據充當新聞。")
    # Replace stale mother-template market snapshot labels; never leave its old 10/23 dates.
    for section_id, section_label in [
        ("global-markets", "全球主要股市"),
        ("bonds", "美債殖利率"),
        ("fx", "外匯"),
        ("tac-assets-panel-3", "能源期貨"),
        ("tac-assets-panel-4", "貴金屬期貨"),
    ]:
        section = unique(soup, f"#{section_id}", section_label)
        for meta in section.select(".tab-panel-meta"):
            set_text(meta, f"{section_label}｜報告基準日 {previous_trade}；各項報價均附資料日期與來源，來源不完整者不納入比較。" )
        for detail in section.select("details.source-details"):
            body = detail.select_one(".source")
            if body:
                set_text_preserving_child_elements(body, f"本區報告基準日：{previous_trade}。逐項來源與報價日期需以當次資料快照核對；若該項未附可核實來源，不沿用母版舊來源，該項不列入本次比較並列入待補資料清單。" )
    # Region quote rows are separate DOM nodes from the U.S. market tab.
    region_rows = {
        "香港恆生指數":"香港恆生指數", "上海綜合指數":"上海綜合指數", "深證成指":"深證成指",
        "日經 225":"日經 225", "韓國 KOSPI":"韓國 KOSPI", "台灣加權指數":"台灣加權指數",
        "新加坡海峽時報指數 STI":"新加坡海峽時報指數 STI", "澳洲 S&P/ASX 200":"澳洲 S&P/ASX 200",
        "英國 FTSE 100":"英國 FTSE 100", "德國 DAX":"德國 DAX", "法國 CAC 40":"法國 CAC 40",
        "STOXX Europe 600":"STOXX Europe 600",
    }
    # The two approved mothers expose regional quotes in different, SHA-locked DOM locations.
    # Monday retains legacy regional panels; Tue-Fri uses the three native global-market tabs.
    region_panel_specs = [
        ("#asia" if monday else "#tac-global-panel-1", "亞洲", 0),
        ("#tac-region-panel-2" if monday else "#tac-global-panel-2", "歐洲", 1),
    ]
    for selector, region_label, comment_index in region_panel_specs:
        panel = unique(soup, selector, f"{region_label} regional quote panel")
        for row in panel.select(".row"):
            label_node = row.select_one("a.global-index-link")
            if not label_node:
                continue
            key = region_rows.get(label_node.get_text(" ", strip=True))
            if not key:
                continue
            record = data.get("global_markets", {}).get(key, {})
            values = row.select("span.r")
            if len(values) >= 2:
                set_text(values[0], record.get("display", "待核實"))
                change = str(record.get("change_display", "待核實"))
                set_text(values[1], change)
                state = "up" if change.startswith("+") else "down" if change.startswith(("−", "-")) else "flat"
                values[1]["class"] = ["r", state] if change != "待核實" else ["r", "warn"]
        meta = panel.select_one(".tab-panel-meta")
        if meta:
            set_text(meta, f"{region_label}市場｜逐項行情以各自資料日期及來源註記；未附來源者不納入本次比較。" )
        for details_node in panel.select("details.source-details, details.region-source"):
            body = details_node.select_one(".source")
            if body:
                body.clear()
                for label, record in data.get("global_markets", {}).items():
                    if label not in region_rows:
                        continue
                    src = record.get("source") if isinstance(record, dict) else None
                    if isinstance(src, dict) and src.get("name") and src.get("url") and src.get("data_date"):
                        body.append(f"{label}｜{src['name']}｜{src['data_date']}｜")
                        body.append(source_link(src["url"], "來源"))
                        body.append("；")
    # All observation cards use the same semantic DOM: bold 📌 heading + line break + paragraph.
    # Target the active global-market tab panels explicitly; the former #asia / #tac-region-panel-2
    # selectors belonged to legacy region tabs and left the visible Asia tab stale.
    narrative_targets = [
        ("#tac-global-panel-0", "📌 美股觀察", "global_markets", 0),
        ("#tac-global-panel-1", "📌 亞股觀察", "global_markets", 1),
        ("#tac-global-panel-2", "📌 歐股觀察", "global_markets", 3),
        ("#asia", "📌 亞股摘要", "global_markets", 1),
        ("#tac-region-panel-2", "📌 歐股摘要", "global_markets", 3),
        ("#tac-assets-panel-0", "📌 產業觀察", "sectors", None),
        ("#bonds", "📌 債券觀察", "bonds", None),
        ("#fx", "📌 匯率觀察", "fx", None),
        ("#tac-assets-panel-3", "📌 原油觀察", "energy", None),
        ("#tac-assets-panel-4", "📌 貴金屬觀察", "metals", None),
    ]
    required_observations = [
        ("#tac-global-panel-1", "📌 亞股觀察", 1),
        ("#tac-global-panel-2", "📌 歐股觀察", 3),
    ]
    comments = data.get("market_comments", {}).get("global_markets", [])
    for selector, heading, idx in required_observations:
        section = unique(soup, selector, heading)
        note = unique(section, ".market-reason", heading + " card")
        value = comments[idx] if idx < len(comments) else ""
        if not str(value).strip():
            raise ValueError(heading + " content missing from report data")
        set_market_observation(note, heading, value)
    for selector, heading, group_key, idx in narrative_targets:
        if selector in {"#tac-global-panel-1", "#tac-global-panel-2"}:
            continue
        section = soup.select_one(selector)
        if section is None:
            continue
        note = section.select_one(".market-reason")
        if note:
            if group_key == "global_markets":
                comments = data.get("market_comments", {}).get(group_key, [])
                value = comments[idx] if idx is not None and idx < len(comments) else ""
            else:
                value = data.get("market_comments", {}).get(group_key, "")
            if value:
                set_market_observation(note, heading, value)
    # Ensure all quote cards carry current per-item dates in the visible heading.
    # Current report label belongs to source link and section only; never duplicate timezone suffixes.
    for market_section in soup.select("#global-markets, #bonds, #fx, #tac-assets-panel-3, #tac-assets-panel-4"):
        meta_node = market_section.select_one(".tab-panel-meta")
        if meta_node:
            title_text = market_section.select_one(".tac-section-heading h2, .title")
            title_label = title_text.get_text(" ", strip=True) if title_text else "市場行情"
            set_text(meta_node, f"{title_label}｜資料基準 {previous_trade}；各品項日期與交易型態依來源逐項列示。")
    # Refresh report masthead, status banner and footer for this report date.
    for node in soup.select(".top .status, header .status, .status"):
        if node.get_text(strip=True):
            set_text(node, f"{report_label}（{report_weekday}）｜{'週一審核版' if monday else '週二至週五審核版'}；行情資料基準 {previous_trade}，各指標依項目日期與來源判讀")
    review_notice = str(data.get("review_notice", "")).strip()
    scope_note = (
        f"五項關鍵價位採 {key_levels_date_label} 同日現金指數 OHLC 人工覆核，依傳統樞紐點公式計算 S2/S1/P/R1/R2；"
        f"其餘44項行情、新聞與行事曆為 {report_cutoff} 查核快照"
        if is_live_key_levels else
        "本版使用固定資料快照，未宣稱即時全自動更新"
    )
    for warning in soup.select(".data-sync-warning"):
        set_text(warning, f"模擬審核版｜報告日期 {report_iso}｜{scope_note}。{review_notice} 來源或日期不足的行情不列入主畫面，並列入待補資料清單；本檔未發布至正式首頁。" )
    footer = soup.select_one("footer.footer")
    if footer:
        set_text(footer, f"TAC 投資早報｜{report_label}（{report_weekday}）審核版｜行情資料基準 {previous_trade}｜{scope_note}；{review_notice}。資訊整理與教育用途，不構成投資建議。")
    # Remove duplicate timezone suffix from preformatted window label.
    news_window_label = news_window_label.replace("（台灣時間）", "")
    # The three Today Focus tabs are updated atomically below; do not clear their approved DOM here.
    # Update only the explicitly historical FactSet snapshot; its historical date remains intentional.
    # Update existing global-market value slots by exact Chinese label.
    gm=unique(soup,"#global-markets","global markets")
    for label,record in data["global_markets"].items():
        normalized_label = normalize_market_label(label)
        rows=[r for r in gm.select(".row") if normalized_label in normalize_market_label(r.get_text(" ",strip=True))]
        if len(rows)!=1: raise ValueError(f"global market row {label!r} count={len(rows)}")
        vals=rows[0].select("span.r")
        if len(vals)<1: raise ValueError(f"global market value slot missing: {label}")
        set_text(vals[0],record.get("display","待核實"))
        if len(vals)>1 and record.get("change_display") is not None:
            set_text(vals[1],record["change_display"])
    # Industry ETF rows: keep exact original 11 rows and order by verified % change.
    sectors=unique(soup,"#tac-assets-panel-0","sector panel")
    sector_rows=sectors.select(".sector-row")
    if len(sector_rows)!=11: raise ValueError(f"sector row count={len(sector_rows)}")
    for row in sector_rows:
        ticker_match=re.search(r"\b(XLK|XLY|XLB|XLU|XLI|XLV|XLF|XLC|XLRE|XLP|XLE)\b",row.get_text(" ",strip=True))
        if not ticker_match: raise ValueError("unidentified sector ETF row")
        ticker=ticker_match.group(1)
        slot=unique(row,"span.r",f"ETF {ticker} value")
        set_text(slot,data["sectors"].get(ticker,"待核實"))
    # Sort verified daily changes descending; unknown values stay after verified rows.
    # Python's stable sort preserves the original ETF order when changes are equal.
    def sector_ticker(row):
        match=re.search(r"\b(XLK|XLY|XLB|XLU|XLI|XLV|XLF|XLC|XLRE|XLP|XLE)\b",row.get_text(" ",strip=True))
        if not match: raise ValueError("unidentified sector ETF row during ranking")
        return match.group(1)
    def sector_change(row):
        raw=row.select_one("span.r").get_text(strip=True)
        normalized=raw.replace("%","").replace("−","-").replace("－","-").replace("+","").strip()
        if not re.fullmatch(r"-?\d+(?:\.\d+)?",normalized):
            return None
        return float(normalized)
    ranked=[]
    for row in sector_rows:
        ticker=sector_ticker(row)
        change=sector_change(row)
        ranked.append((row,ticker,change))
    ranked.sort(key=lambda item: (item[2] is None, -(item[2] if item[2] is not None else 0)))
    ranked_rows_for_source = [row for row, _, _ in ranked]
    # Sector source list explicitly calls out every item without complete provenance.
    sector_meta = soup.select_one("#tac-assets-panel-0 .tab-panel-meta")
    if sector_meta:
        set_text(sector_meta, f"11檔產業ETF單日漲跌幅｜{previous_trade}美股收盤｜所有列示項目均附可追溯來源與資料日期；缺漏者不納入排序" )
    sector_source = soup.select_one("#tac-assets-panel-0 details .source")
    if sector_source:
        sector_source.clear()
        for ticker in [x[1] for x in ranked]:
            src = data.get("sector_sources", {}).get(ticker, {})
            if src.get("name") and src.get("url") and src.get("data_date"):
                sector_source.append(f"{ticker}｜{src['name']}｜{src['data_date']}｜")
                sector_source.append(source_link(src["url"], "來源"))
                sector_source.append("；")
            else:
                sector_source.append(f"{ticker}｜待核實（缺來源或資料日期）；")
    sector_list=sector_rows[0].parent
    for rank,(row,ticker,change) in enumerate(ranked, start=1):
        rank_node=unique(row,".rank",f"ETF {ticker} rank")
        set_text(rank_node,str(rank))
        value_node=unique(row,"span.r",f"ETF {ticker} value")
        if change is None:
            set_text(value_node,"待核實")
            value_node["class"]=["r","pending"]
        else:
            value_node["class"]=["r","up" if change>0 else "down" if change<0 else "flat"]
        sector_list.append(row)
    # Hard gate: displayed order, rank labels and values must agree.
    displayed=sector_list.select(".sector-row")
    if len(displayed)!=11:
        raise ValueError(f"sector ranking output count={len(displayed)}")
    displayed_tickers=[]
    displayed_changes=[]
    for expected_rank,row in enumerate(displayed,start=1):
        rank_text=unique(row,".rank","sector rank").get_text(strip=True)
        if rank_text!=str(expected_rank):
            raise ValueError(f"sector rank mismatch: expected {expected_rank}, got {rank_text}")
        displayed_tickers.append(sector_ticker(row))
        displayed_changes.append(sector_change(row))
    expected_tickers=[ticker for _,ticker,_ in ranked]
    if displayed_tickers!=expected_tickers:
        raise ValueError("sector ETF DOM order differs from computed ranking order")
    verified=[x for x in displayed_changes if x is not None]
    if verified!=sorted(verified,reverse=True):
        raise ValueError("sector ETF order is not descending by verified daily change")
    first_pending=next((i for i,x in enumerate(displayed_changes) if x is None),len(displayed_changes))
    if any(x is not None for x in displayed_changes[first_pending:]):
        raise ValueError("verified sector ETF appears after an unverified ETF")
    # The sector ETF panel also carries source prose and a dated heading; refresh both.
    sector_meta = sectors.select_one(".tab-panel-meta")
    if sector_meta:
        set_text(sector_meta, f"11檔產業ETF單日漲跌幅｜{previous_trade}美股收盤｜已核實項目依單日漲跌幅降序；未核實項目列後")
    sector_source = sectors.select_one("details.sector-source .source") or sectors.select_one("details.source-details .source")
    if sector_source:
        sector_source.clear()
        verified_sector_lines = []
        for ticker in [sector_ticker(row) for row in ranked_rows_for_source]:
            item = data.get("sector_sources", {}).get(ticker, {})
            if item.get("name") and item.get("url") and item.get("data_date"):
                sector_source.append(f"{ticker}｜{item['name']}｜{item['data_date']}｜")
                sector_source.append(source_link(item["url"], "原始來源"))
                sector_source.append("；")
        pending_tickers = [ticker for ticker in data.get("sectors", {}) if ticker not in data.get("sector_sources", {})]
        if pending_tickers:
            sector_source.append("未核實（缺來源／日期，未沿用母版數據）： " + "、".join(pending_tickers))
    # Date and item provenance in every region tab are updated from the same records.
    for selector, _, _ in region_panel_specs:
        panel = soup.select_one(selector)
        if panel:
            region_meta = panel.select_one(".tab-panel-meta")
            if region_meta:
                set_text(region_meta, f"{selector}｜市場報價資料基準 {previous_trade}；無逐項來源與日期者不納入本次比較。" )
    # Classify global market moves according to the report color convention (rise red, fall green).
    for row in gm.select(".row"):
        spans = row.select("span.r")
        if len(spans) >= 2:
            change = spans[1].get_text(strip=True)
            state = "up" if change.startswith("+") else "down" if change.startswith(("−", "-")) else "flat"
            spans[1]["class"] = ["r", state] if change != "待核實" else ["r", "warn"]
    # Replace all remaining old source paragraphs in risk and market cards with current evidence state.
    # Refresh quote metadata for every instrument group; unresolved rows are explicitly listed.
    for group_id, records in [
        ("global-markets", data.get("global_markets", {})),
        ("bonds", data.get("bonds", {})),
        ("fx", data.get("fx", {})),
        ("tac-assets-panel-3", data.get("energy", {})),
        ("tac-assets-panel-4", data.get("metals", {})),
    ]:
        group = soup.select_one("#" + group_id)
        if not group:
            continue
        summary = []
        for instrument, record in records.items():
            source = record.get("source") if isinstance(record, dict) else None
            if isinstance(source, dict) and source.get("name") and source.get("url") and source.get("data_date"):
                summary.append((record.get("display_name") or instrument, source, record.get("contract_label")))
        for details_node in group.select("details.source-details"):
            source_node = details_node.select_one(".source")
            if source_node:
                source_node.clear()
                if summary:
                    for instrument, source, contract_label in summary:
                        source_node.append(f"{instrument}｜{source['name']}｜")
                        if contract_label:
                            source_node.append(f"合約：{contract_label}｜")
                        source_node.append(f"{source['data_date']}｜")
                        source_node.append(source_link(source["url"], source.get("link_label", "歷史數據")))
                        if source.get("note"):
                            source_node.append(f"｜補充：{source['note']}")
                        source_node.append("；")
                else:
                    source_node.append("本區沒有具備來源、URL 與逐項資料日期的可核實報價；相關列不納入本次比較。")
    # Bonds, FX, oil and metals are exact-label bindings.
    for container_id,records in [("bonds",data["bonds"]),("fx",data["fx"]),("tac-assets-panel-3",data["energy"]),("tac-assets-panel-4",data["metals"])]:
        container=unique(soup,f"#{container_id}",container_id)
        for label,record in records.items():
            # Display labels may add Latin/Chinese spacing (e.g. "WTI 原油期貨").
            # Match the stable semantic label independent of presentation whitespace.
            normalized_label="".join(str(label).split())
            rows=[r for r in container.select(".row")
                  if normalized_label in "".join(r.get_text(" ",strip=True).split())]
            if len(rows)!=1: raise ValueError(f"{container_id}/{label}: rows={len(rows)}")
            contract_label = record.get("contract_label")
            source_meta = record.get("source") or {}
            label_link = rows[0].select_one("b a")
            if contract_label:
                update_contract_link_label(label_link, contract_label, source_meta, record.get("instrument_url"), instrument_key=label, display_name=record.get("display_name"))
            elif label_link and str(source_meta.get("url") or "").startswith("https://"):
                # The visible instrument link must open the exact source page used for its quote.
                label_link["href"] = source_meta["url"]
                label_link["target"] = "_blank"
                label_link["rel"] = "noopener"
            vals=rows[0].select("span.r")
            if not vals: raise ValueError(f"missing value {container_id}/{label}")
            set_text(vals[0],record.get("display","待核實"))
            if len(vals)>1 and record.get("change_display") is not None:
                change_text = str(record["change_display"]).strip()
                set_text(vals[1], change_text)
                # TAC convention: positive/rising = red (.up); negative/falling = green (.down).
                # Recompute the semantic class from the refreshed value; never retain stale mother-template classes.
                numeric_change = re.match(r"^[+＋]?\s*([0-9][0-9,]*(?:\.[0-9]+)?)", change_text)
                negative_change = re.match(r"^[-−－]\s*([0-9][0-9,]*(?:\.[0-9]+)?)", change_text)
                for cls in ("up", "down", "flat"):
                    if cls in vals[1].get("class", []):
                        vals[1]["class"].remove(cls)
                current_classes = list(vals[1].get("class", []))
                if negative_change:
                    current_classes.append("down")
                elif numeric_change:
                    amount = float(numeric_change.group(1).replace(",", ""))
                    current_classes.append("flat" if amount == 0 else "up")
                else:
                    current_classes.append("pending")
                vals[1]["class"] = current_classes
    # Validate TAC directional colors by visible label after contract codes are moved to source disclosures.
    for container_id, records in [("bonds", data["bonds"]), ("fx", data["fx"]),
                                  ("tac-assets-panel-3", data["energy"]), ("tac-assets-panel-4", data["metals"])]:
        container = unique(soup, f"#{container_id}", container_id)
        for label, record in records.items():
            if record.get("change_display") is None:
                continue
            normalized_label = "".join(str(record.get("display_name") or label).split())
            row = next((r for r in container.select(".row")
                        if normalized_label in "".join(r.get_text(" ", strip=True).split())), None)
            if row is None:
                raise ValueError(f"{container_id}/{label}: directional QA row missing")
            change = row.select("span.r")
            if len(change) < 2:
                raise ValueError(f"{container_id}/{label}: directional QA change span missing")
            cls = change[1].get("class", [])
            value = str(record["change_display"]).strip()
            parsed_change = re.match(r"^([+＋\\-−－]?)\\s*([0-9][0-9,]*(?:\\.[0-9]+)?)", value)
            if parsed_change:
                sign = parsed_change.group(1)
                amount = float(parsed_change.group(2).replace(",", ""))
                expected = "down" if sign in ("-", "−", "－") else "flat" if amount == 0 else "up"
            else:
                expected = None
            if expected and expected not in cls:
                raise ValueError(f"{container_id}/{label}: TAC direction class mismatch for {value}: {cls}, expected {expected}")
    # Refresh risk quote value, move, source and date together. Never retain mother-template quote annotations.
    for key,label in [("vix","VIX"),("move","MOVE")]:
        record = data["risk"][key]
        rows=[r for r in sent.select(".sbox") if (r.select_one(".label-en") and r.select_one(".label-en").get_text(" ",strip=True).strip()==label)]
        if not rows: raise ValueError(f"{label} row not found")
        source = record.get("source") or {}
        is_verified = bool(source.get("name") and source.get("data_date") and (source.get("url") or source.get("quote_type") == "user_supplied_market_quote_screenshot"))
        if key == "move" and str(record.get("as_of_date", "")).startswith("未取得"):
            is_verified = False
        if not is_verified:
            record["display"] = "待核實"
            record["change_display"] = "待核實"
        for row in rows:
            # Preserve the approved mother-template MOVE destination even when the
            # dated value itself is supported by a user-supplied screenshot. The link
            # opens the instrument page; source details below continue to identify
            # the actual evidence type and must not imply that this run scraped it.
            if key == "move":
                title_link = row.select_one(".label a.tac-market-link")
                if title_link and not title_link.get("href"):
                    title_link["href"] = "https://hk.investing.com/indices/ice-bofaml-move"
            strong=row.select("strong")
            if not strong: raise ValueError(f"{label} value slot missing")
            set_text(strong[-1],record.get("display","待核實"))
            change_nodes = row.select(".up, .down, .warn, .flat")
            if change_nodes:
                change_node = change_nodes[0]
                set_text(change_node,record.get("change_display","待核實"))
                change_text = str(record.get("change_display","待核實"))
                change_state = "up" if change_text.startswith("+") else "down" if change_text.startswith(("−","-")) else "flat"
                change_node["class"] = [change_state] if change_text != "待核實" else ["warn"]
            source_node = row.select_one(".source-details .source")
            if source_node:
                source_node.clear()
                if is_verified:
                    source_node.append(f'{source.get("name")}｜資料日期 {source.get("data_date")}｜')
                    if source.get("url"):
                        source_node.append(source_link(source["url"], "查看原始資料"))
                    if source.get("note"):
                        source_node.append("｜" + str(source["note"]))
                else:
                    reason = "來源或資料日期未核實，母版舊數值及變動率已清除。"
                    if record.get("as_of_date"):
                        reason = str(record["as_of_date"]) + "；" + reason
                    source_node.append(reason)
    fg=sent.select(".cnn-fg-preview")
    if fg:
        score=fg[0].select_one(".fg6-score-main")
        if score: set_text(score,data["risk"]["fear_greed"].get("display","待核實"))
    # FedWatch: preserve the mother template's two probability-card slots.
    fed=unique(soup,"#fed .fed-live-watch","FedWatch panel")
    fedwatch_layout_note = populate_fedwatch_two_slots(fed, data)
    ts=data["fedwatch"].get("updated_at_tw","未取得 05:25 前快照")
    for span in fed.select(".fc-split-head span"):
        if "資料時間" in span.get_text() or "官方截圖" in span.get_text() or "Investing.com" in span.get_text():
            set_text(span,f"Fed Rate Monitor｜{ts}")
    # Replace stale mother-template disclaimer with the actual verified snapshot state.
    snapshot_note = f"Investing.com Fed Rate Monitor｜目標會議 {data['fedwatch'].get('target_meeting','待核實')}｜更新時間 {ts}。" + ((" " + fedwatch_layout_note) if fedwatch_layout_note else "")
    snapshot_detail = fed.select_one("details")
    if snapshot_detail:
        detail_body = snapshot_detail.select_one("div")
        if detail_body:
            set_text(detail_body, snapshot_note + " 本版採頁面所列機率分布，非舊截圖或自行估算。")
    source_line = fed.select_one(".fc-source")
    if source_line:
        for text_node in list(source_line.find_all(string=True)):
            if "本次資料截點未取得可核實的機率快照" in str(text_node):
                text_node.replace_with("｜" + snapshot_note)
    # Replace current-week calendar cards from the current W46 records.
    def dateparts(v):
        try:
            z=datetime.fromisoformat(v); return z.strftime("%m/%d"), z.strftime("%H:%M") if z.hour or z.minute else "時間未確認"
        except Exception: return "日期待核實","時間未確認"
    def groupkey(x):
        return classify_calendar_group(x, report_iso, report_cutoff)
    def startext(x):
        n=max(0,min(5,int(x.get("stars") or 0))); return "★"*n+"☆"*(5-n)
    def putfield(card,label,value):
        candidates = {"市場影響": {"市場影響", "觀察重點"}}.get(label, {label})
        matches = [field for field in card.select(".econ-field")
                   if field.select_one("label") and field.select_one("label").get_text(strip=True) in candidates]
        if len(matches) != 1:
            raise ValueError(f"economic card field {label!r}: expected exactly one match, got {len(matches)}")
        field = matches[0]
        lab = field.select_one("label")
        if lab.get_text(strip=True) == "觀察重點":
            set_text(lab, "市場影響")
        value_node = field.select_one(".econ-value")
        if value_node is None:
            raise ValueError("economic card value node missing: " + label)
        set_text(value_node, value if value is not None else "未提供")
    cal=unique(soup,"#calendar","economic calendar")
    econ=data.get("calendar",{}).get("events",[])
    if not econ: raise ValueError("current-week economic calendar data missing")
    title=cal.select_one(".title small")
    if title: set_text(title,"%s～%s｜%s｜資料截點 %s 台灣時間" % (data["calendar"]["week_start"],data["calendar"]["week_end"],data["calendar"]["week_id"],report_cutoff))
    panels=unique(cal,".week-econ-panels","economic panels")
    econ_templates=panels.select("details.econ-event")
    template=next((c for c in econ_templates if len(c.select(".econ-field"))>=5 and any(
        f.select_one("label") and f.select_one("label").get_text(strip=True) in {"市場影響","觀察重點"}
        for f in c.select(".econ-field")
    )),None)
    if template is None: raise ValueError("five-zone economic calendar template missing from approved Monday mother")
    validate_economic_card(template, "approved current-week economic prototype", "econ-toggle")
    template_html=str(template)  # freeze the approved prototype before replacing any list instances
    econ_groups=panels.select(":scope > .calendar-status-group")
    if len(econ_groups)!=3: raise ValueError(f"economic calendar must retain exactly three mother status groups; found {len(econ_groups)}")
    for group in econ_groups:
        if group.select_one(".calendar-status-heading") is None:
            raise ValueError("economic calendar mother status heading missing")
    for group,(key,label) in zip(econ_groups,[("today","今日公布"),("upcoming","即將公布"),("published","已公布")]):
        items=[x for x in econ if groupkey(x)==key]
        heading=group.select_one(".calendar-status-heading")
        display_label = ("已公布／待核實" if key=="published" and any(x.get("_calendar_publication_state")!="released" for x in items) else ("即將公布／含已延期、已取消" if key=="upcoming" and any(x.get("_calendar_publication_state") in ("postponed","cancelled") for x in items) else label))
        set_calendar_status_heading(heading,f"{display_label}｜重要性★★★★☆以上（{len(items)}項）",key)
        listing=group.select_one(".econ-event-list")
        if listing is None:
            empty=group.select_one(".calendar-status-empty")
            if empty is None: raise ValueError(f"economic calendar {key} group has neither event-list nor empty-state slot")
            if not items:
                set_text(empty,"目前沒有符合本分頁條件的已核實重要經濟事件。")
                continue
            classes=[c for c in empty.get("class",[]) if c!="calendar-status-empty"]
            empty["class"]=classes+["econ-event-list"]
            listing=empty
        reset_calendar_listing(listing,"econ-event","目前沒有符合本分頁條件的已核實重要經濟事件。",bool(items))
        for x in items:
            card=BeautifulSoup(template_html,"html.parser").select_one("details.econ-event")
            day,clock=dateparts(x.get("date",""))
            if not x.get("time_known",False): clock="時間未確認"
            for sel,val in [(".econ-date",day),(".econ-time",clock),(".econ-country",x.get("region","")),(".econ-name",x.get("name","")),(".econ-stars",startext(x))]:
                node=card.select_one(sel)
                if node: set_text(node,val)
            for field in card.select(".econ-field"):
                lab=field.select_one("label")
                if lab and lab.get_text(strip=True)=="觀察重點": set_text(lab,"市場影響")
            card["class"]=["econ-event","five-star" if int(x.get("stars") or 0)>=5 else "four-star"]
            putfield(card,"前值",x.get("previous")); putfield(card,"市場預估",x.get("forecast"))
            putfield(card,"實際",calendar_actual_display(x, report_cutoff))
            putfield(card,"市場影響",x.get("impact") or "待核實")
            set_economic_source(card, x)
            validate_economic_card(card, f"current-week economic event {x.get('id') or x.get('name')}", "econ-toggle")
            listing.append(card)
    validate_calendar_group_order(panels,"economic calendar")
    earn=unique(soup,"#earnings","earnings calendar")
    earnings=data.get("earnings",{}).get("events",[])
    if not earnings: raise ValueError("current-week earnings calendar data missing")
    title=earn.select_one(".title small")
    if title: set_text(title,"%s～%s｜%s｜資料截點 %s 台灣時間" % (data["earnings"]["week_start"],data["earnings"]["week_end"],data["earnings"]["week_id"],report_cutoff))
    ep=unique(earn,".week-earnings-panels","earnings panels")
    earnings_mother_cards=ep.select("details.earnings-accordion")
    et=next((c for c in earnings_mother_cards if c.select_one(".earnings-results-grid") is None),None)
    eg=next((g for g in ep.select(".calendar-status-group") if g.select_one(".earnings-accordion-list")),None)
    if not et or not eg: raise ValueError("upcoming earnings calendar mother prototype missing")
    earnings_template_html=str(et)  # freeze the approved upcoming-card prototype
    published_template=next((c for c in earnings_mother_cards if c.select_one(".earnings-results-grid")),None)
    if monday:
        retrospective_prototype=soup.select_one("#last-week-earnings .earnings-accordion-list details.earnings-accordion")
        if retrospective_prototype is not None and retrospective_prototype.select_one(".earnings-results-grid") is not None:
            published_template=retrospective_prototype
    published_template_html=str(published_template) if published_template is not None else None
    earnings_groups=ep.select(":scope > .calendar-status-group")
    if len(earnings_groups)!=3: raise ValueError(f"earnings calendar must retain exactly three mother status groups; found {len(earnings_groups)}")
    for group in earnings_groups:
        if group.select_one(".calendar-status-heading") is None:
            raise ValueError("earnings calendar mother status heading missing")
    def earnings_groupkey(x):
        return classify_calendar_group(x, report_iso, report_cutoff)
    for group,(key,label) in zip(earnings_groups,[("today","今日公布"),("upcoming","即將公布"),("published","已公布")]):
        items=[x for x in earnings if earnings_groupkey(x)==key]
        heading=group.select_one(".calendar-status-heading")
        display_label=("已公布／待核實" if key=="published" and any(x.get("_calendar_publication_state")!="released" for x in items) else ("後續公布／含已延期、已取消" if key=="upcoming" and any(x.get("_calendar_publication_state") in ("postponed","cancelled") for x in items) else label))
        set_calendar_status_heading(heading,f"{display_label}｜TAC 四星／五星（{len(items)}家）",key)
        listing=group.select_one(".earnings-accordion-list")
        if listing is None:
            empty=group.select_one(".calendar-status-empty")
            if empty is None: raise ValueError(f"earnings calendar {key} group has neither accordion-list nor empty-state slot")
            if not items:
                set_text(empty,"目前沒有符合本分頁條件的已核實重要財報事件。")
                continue
            classes=[c for c in empty.get("class",[]) if c!="calendar-status-empty"]
            empty["class"]=classes+["earnings-accordion-list"]
            listing=empty
        reset_calendar_listing(listing,"earnings-accordion","目前沒有符合本分頁條件的已核實重要財報事件。",bool(items))
        for x in items:
            if earnings_groupkey(x) == "published":
                if not published_template_html:
                    raise ValueError("published earnings require an approved mother results-card prototype")
                card=BeautifulSoup(published_template_html,"html.parser").select_one("details.earnings-accordion")
            else:
                card=BeautifulSoup(earnings_template_html,"html.parser").select_one("details.earnings-accordion")
            if card is None:
                raise ValueError("Frozen earnings mother prototype could not be parsed")
            day,clock=dateparts(x.get("date",""))
            if not x.get("time_known",False):
                clock="時間未確認"
            session_label=("盤前" if x.get("session")=="before_market" else "盤後" if x.get("session")=="after_market" else "時段待核實")
            clock_label=("電話會議 "+clock if x.get("time_type")=="call_time" else clock)
            fields=[
                (".earnings-us-date",day),
                (".earnings-tw-date",session_label+"；"+clock_label),
                (".earnings-company-name",x.get("company","")),
                (".earnings-company-sub",str(x.get("ticker",""))+"｜"+str(x.get("industry",""))),
                (".earnings-stars",startext(x)),
            ]
            for sel,val in fields:
                node=card.select_one(sel)
                if node:
                    set_text(node,val)
            apply_earnings_star_style(card, x)
            details=card.select_one(".earnings-accordion-details")
            if details is None:
                raise ValueError("earnings card detail container missing")
            if earnings_groupkey(x) == "published":
                update_actual_results_grid(details.select_one(".earnings-results-grid"),x)
                update_published_earnings_detail_fields(details,x,clock)
            else:
                timing_value=("時間待核實" if not x.get("time_known",False) else clock)
                update_upcoming_earnings_detail_fields(
                    details,x,day,clock,session_label,timing_value
                )
            listing.append(card)
    validate_calendar_group_order(ep,"earnings calendar")
    # Fail closed if any already-released company is missing from the published accordion
    # or appears in more than one status group.
    # The published accordion includes past events even when actual results remain unverified.
    # Such cards must still use the side-by-side EPS/revenue layout with explicit missing-value labels.
    published_expected_tickers={str(x.get("ticker","")).upper() for x in earnings
                                if earnings_groupkey(x) == "published"}
    published_heading=ep.select_one(".calendar-status-heading.published")
    published_group=published_heading.find_parent(class_="calendar-status-group") if published_heading else None
    if published_group is None: raise ValueError("published earnings group missing")
    # Verify every published earnings card uses the two-column results grid and separate analysis/reaction/source blocks.
    for published_card in published_group.select("details.earnings-accordion"):
        published_details=published_card.select_one(".earnings-accordion-details")
        ticker_node=published_card.select_one(".earnings-company-sub")
        ticker=ticker_node.get_text(" ",strip=True) if ticker_node else "unknown ticker"
        results_grid=(published_details.find("div", class_="earnings-results-grid", recursive=False)
                      if published_details is not None else None)
        actual_cards=(results_grid.find_all("div", class_="earnings-actual-card", recursive=False)
                      if results_grid is not None else [])
        if published_details is None or len(actual_cards) != 2:
            detail_html=str(published_details)[:1200] if published_details is not None else "missing details container"
            raise ValueError(f"published earnings card missing side-by-side EPS/revenue result cards: {ticker}; details={detail_html}")
        # Guard both the outer card count and the individual Actual/Estimate rows.
        card_titles=[node.select_one(".earnings-actual-card-title").get_text(" ",strip=True)
                     if node.select_one(".earnings-actual-card-title") else ""
                     for node in actual_cards]
        if card_titles != ["EPS","營收"]:
            raise ValueError(f"published earnings result card titles/order invalid: {ticker}; {card_titles}")
        for result_card in actual_cards:
            row_labels=[row.find("span",recursive=False).get_text(" ",strip=True)
                        if row.find("span",recursive=False) else ""
                        for row in result_card.find_all("div",class_="earnings-actual-line",recursive=False)]
            if row_labels != ["實際","預期"]:
                raise ValueError(f"published earnings value rows must be exactly 實際/預期 once each: {ticker}; {row_labels}")
        direct_fields=published_details.find_all("div", class_="earnings-detail-field", recursive=False)
        required_labels={label.get_text(" ",strip=True) for field in direct_fields for label in field.find_all("label", recursive=False)}
        monday_labels={"財報判讀","股價當日表現","來源"}
        weekday_labels={"公布時段","EPS 預估／實際","營收預估／實際","財報判讀與股價反應","資料來源"}
        if not (monday_labels.issubset(required_labels) or weekday_labels.issubset(required_labels)):
            raise ValueError(f"published earnings card missing required mother sections: {ticker}; {sorted(required_labels)}")
    published_tickers={str(n.get_text(" ",strip=True)).split("｜",1)[0].strip().upper()
                       for n in published_group.select(".earnings-company-sub")}
    if published_expected_tickers != published_tickers:
        raise ValueError(f"published earnings classification mismatch: expected {sorted(published_expected_tickers)}, rendered {sorted(published_tickers)}")
    for status_class in ("today","upcoming"):
        status_heading=ep.select_one(f".calendar-status-heading.{status_class}")
        group_node=status_heading.find_parent(class_="calendar-status-group") if status_heading else None
        if group_node:
            other={str(n.get_text(" ",strip=True)).split("｜",1)[0].strip().upper()
                   for n in group_node.select(".earnings-company-sub")}
            overlap=other & published_expected_tickers
            if overlap: raise ValueError(f"published earnings duplicated outside published group: {sorted(overlap)}")
    # Monday retrospective: populate dedicated prior-week sections from W45 only.
    if monday:
        last_econ = data.get("last_week_calendar", {})
        last_earn = data.get("last_week_earnings", {})
        lw = unique(soup, "#last-week-calendar", "last-week economic calendar")
        lw_title = lw.select_one(".title small")
        if lw_title:
            set_text(lw_title, f"{last_econ.get('week_start','')}～{last_econ.get('week_end','')}｜{last_econ.get('week_id','')}｜上週五星事件")
        lw_details = unique(lw, "details.last-week-calendar-collapse", "last-week economic collapse")
        lw_list = unique(lw_details, ".econ-event-list", "last-week economic list")
        lw_template = lw_list.select_one("details.econ-event")
        if lw_template is None: raise ValueError("Monday mother last-week economic card template missing")
        # Reuse the approved five-zone current-week card DOM, but retain the
        # retrospective summary/toggle shell from the Monday mother.
        lw_summary_template = lw_template.select_one("summary")
        if lw_summary_template is None: raise ValueError("Monday retrospective summary prototype missing")
        # Freeze the summary before decompose() destroys its parent card and descendants.
        lw_summary_prototype = copy.deepcopy(lw_summary_template)
        for old_card in lw_list.find_all("details", class_="econ-event", recursive=False):
            old_card.decompose()
        for x in last_econ.get("events", []):
            if int(x.get("stars") or 0) < 5 or x.get("status") != "released": continue
            card = BeautifulSoup(template_html, "html.parser").find("details", class_="econ-event")
            summary_clone = copy.deepcopy(lw_summary_prototype)
            card_summary = card.find("summary", recursive=False)
            if summary_clone is None or card_summary is None:
                raise ValueError("Monday retrospective economic summary prototype is incomplete")
            card_summary.replace_with(summary_clone)
            day, clock = dateparts(x.get("date", ""))
            if not x.get("time_known", False): clock = "時間未確認"
            for sel, val in [(".econ-date", day), (".econ-time", clock), (".econ-country", x.get("region", "")), (".econ-name", x.get("name", "")), (".econ-stars", startext(x))]:
                node = card.select_one(sel)
                if node: set_text(node, val)
            card["class"] = ["econ-event", "five-star"]
            putfield(card, "前值", x.get("previous"))
            putfield(card, "市場預估", x.get("forecast"))
            putfield(card, "實際", x.get("actual"))
            putfield(card, "市場影響", x.get("impact") or "未提供")
            set_economic_source(card, x)
            validate_economic_card(card, f"previous-week economic event {x.get('id') or x.get('name')}", "econ-event-toggle")
            lw_list.append(card)
        if not lw_list.select("details.econ-event"): raise ValueError("W45 has no verified five-star published economic events")
        lw_range=f"{last_econ.get('week_start','')[5:7]}/{last_econ.get('week_start','')[8:10]}～{last_econ.get('week_end','')[5:7]}/{last_econ.get('week_end','')[8:10]}"
        lw_summary=lw_details.select_one("summary")
        if lw_summary: set_text(lw_summary, f"展開上週經濟行事曆（{lw_range}）")
        lw_heading=lw.select_one(".calendar-status-heading.published")
        if lw_heading: set_text(lw_heading, "上週已公布｜全球五顆星重要經濟事件")
        le = unique(soup, "#last-week-earnings", "last-week earnings")
        le_title = le.select_one(".title small")
        if le_title: set_text(le_title, f"{last_earn.get('week_start','')}～{last_earn.get('week_end','')}｜{last_earn.get('week_id','')}｜上週五星財報")
        le_details = unique(le, "details.last-week-earnings-collapse", "last-week earnings collapse")
        le_list = unique(le_details, ".earnings-accordion-list", "last-week earnings list")
        le_template = le_list.select_one("details.earnings-accordion")
        if le_template is None: raise ValueError("Monday mother last-week earnings card template missing")
        le_template_html = str(le_template)  # freeze before removing the original card from the live list
        for old_card in le_list.find_all("details", class_="earnings-accordion", recursive=False):
            old_card.decompose()
        for x in last_earn.get("events", []):
            if int(x.get("stars") or 0) < 5 or x.get("status") != "released": continue
            card = BeautifulSoup(le_template_html, "html.parser").find("details", class_="earnings-accordion")
            if card is None: raise ValueError("Frozen Monday retrospective earnings prototype could not be parsed")
            day, clock = dateparts(x.get("date", ""))
            if not x.get("time_known", False): clock = "時間未確認"
            fields = [(".earnings-us-date", day), (".earnings-tw-date", ("盤前" if x.get("session")=="before_market" else "盤後" if x.get("session")=="after_market" else "時段待核實")+"；"+clock), (".earnings-company-name", x.get("company","")), (".earnings-company-sub", str(x.get("ticker",""))+"｜"+str(x.get("industry",""))), (".earnings-stars", startext(x))]
            for sel, val in fields:
                node = card.select_one(sel)
                if node: set_text(node, val)
            details = card.select_one(".earnings-accordion-details")
            if details:
                grid = details.select_one(".earnings-results-grid")
                update_actual_results_grid(grid, x)
                update_published_earnings_detail_fields(details, x, clock)
            le_list.append(card)
        if not le_list.select("details.earnings-accordion"): raise ValueError("W45 has no verified five-star published earnings")
        le_range=f"{last_earn.get('week_start','')[5:7]}/{last_earn.get('week_start','')[8:10]}～{last_earn.get('week_end','')[5:7]}/{last_earn.get('week_end','')[8:10]}"
        le_summary=le_details.select_one("summary")
        if le_summary: set_text(le_summary, f"展開上週財報行事曆（{le_range}）")
        le_heading=le.select_one(".calendar-status-heading.published")
        if le_heading: set_text(le_heading, "上週已公布｜五星財報，依公布日期排序")
        le_source=le.select_one(".source")
        if le_source: set_text(le_source, f"排序依美國公司實際公布日期（{le_range.replace('～','→')}）；台灣時間另列。僅納入重要性五星的已公布代表性公司，非所有市場財報完整清單。EPS 及營收採 GAAP／非 GAAP 時已註明口徑；未能核實的欄位明確標示待核。")


    # Remove stale mother-template dates from news, CNN, FactSet and FedWatch panels.
    news_window = soup.select_one("#news-scan .news-window-warning")
    if news_window:
        set_text(news_window, f"新聞時間窗｜{news_window_label}（台灣時間）。每則新聞均核對原始發布時間、來源時區、台灣換算時間、最後更新狀態及原文連結；未符合時間窗的資料不納入。")
    health = soup.select_one("#sp500-earnings-health")
    if health:
        populate_earnings_health_dashboard_preserving_dom(health, data.get("earnings_health") or {}, monday)
    fed = soup.select_one("#fed")
    if fed:
        meeting = fed.select_one(".fc-fomc-meeting b")
        if meeting: set_text(meeting, "2026/12/08–12/09")
        press = fed.select_one(".fc-fomc-press b")
        if press: set_text(press, "2026/12/10 03:30")
        rate = fed.select_one(".fc-fomc-rate b")
        current_target_range = data.get("fedwatch", {}).get("current_target_range", "待核實")
        if rate: set_text(rate, current_target_range.replace("–", "%–") + ("%" if current_target_range != "待核實" and not current_target_range.endswith("%") else ""))
        rate_date = fed.select_one(".fc-fomc-rate small")
        if rate_date: set_text(rate_date, "Fed官方最新資料：2026/10/29")
        # Preserve the mother-template's existing FOMC observation node.
        # Verified weekly Fed speaker events are rendered only in the fixed
        # .fc-fomc-weekly-events mother-template slot below.
        fed_source = fed.select_one(".fc-source")
        if fed_source:
            fed_source.clear()
            fed_source.append("資料來源：")
            for url, label in [
                ("https://www.investing.com/central-banks/fed-rate-monitor","Investing.com Fed Rate Monitor"),
                ("https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html","CME FedWatch"),
                ("https://www.federalreserve.gov/newsevents/pressreleases/monetary20261028a.htm","Fed 10/28官方聲明"),
                ("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm","Fed官方會議日曆")
            ]:
                fed_source.append(source_link(url,label)); fed_source.append("｜")
            snapshot_note = f"12/09會議機率資料更新：{data.get('fedwatch',{}).get('updated_at_tw','時間待核實')}；採頁面公布值，非自行估算。"
            fed_source.append(snapshot_note)
        probabilities = data.get("fedwatch", {}).get("probabilities", [])
        watch=fed.select_one(".fed-live-watch")
        if watch:
            bar=watch.select_one(".fc-split-bar")
            if bar and probabilities:
                bar["aria-label"]="；".join(f"{x.get('rate_range')} {float(x.get('probability',0)):.1f}%" for x in probabilities)
                bar.attrs.pop("style", None)
            elif bar:
                bar["aria-label"]="未取得 2026/11/09 05:25 前可核實的 FedWatch 機率快照"
                bar["style"]="display:none"
            note=watch.select_one("details > div")
            legend_items=watch.select(".fc-split-legend > span")
            if note:
                if probabilities:
                    set_text(note, f"本次報告資料截點為 {report_cutoff}（台灣時間）。Investing.com Fed Rate Monitor 於 {data.get('fedwatch',{}).get('updated_at_tw','時間待核實')} 提供 2026/12/09 會議機率；本版依來源頁面公布值呈現，不以舊截圖或自行估算代替。")
                else:
                    set_text(note, f"本次報告資料截點為 {report_cutoff}（台灣時間）。未取得該截點前可核實的 FedWatch 機率快照，因此不填入推估機率。")
    fg = soup.select_one(".cnn-fg-preview")
    if fg:
        fg_record = data.get("risk", {}).get("fear_greed", {})
        fg_value = fg_record.get("display", "待核實")
        fg_source = fg_record.get("source", {})
        fg_date = fg_record.get("as_of", previous_trade)
        date_node = fg.select_one(".fg6-date")
        if date_node:
            source_label = "CNN官方歷史讀值" if "FGScore" not in str(fg_source.get("name","")) else "FGScore｜CNN Provider Index備援"
            set_text(date_node, f"{source_label}｜{fg_date}")
        score = fg.select_one(".fg6-score-main")
        if score: set_leaf_text_preserving_dom(score, fg_value, "CNN Fear & Greed numeric score")
        marker = fg.select_one(".fg6-marker")
        if marker is None:
            raise ValueError("CNN Fear & Greed marker missing from approved mother template")
        # The numeric source field is preferred; display is the existing fixture fallback.
        # This inline !important overrides the approved mother's fixed left:23%!important.
        apply_fear_greed_marker(marker, fg_record.get("value", fg_value))
        status = fg.select_one(".fg6-status")
        if status is None:
            raise ValueError("CNN Fear & Greed status label missing from approved mother template")
        band = apply_fear_greed_status(status, fg_record.get("value", fg_value))
        klass = fg.select_one(".fg6-class")
        if klass: set_text(klass, band[0])
        explanation = fg_source.get("note") or "未取得可核實的官方歷史讀值，暫不判定市場恐懼或貪婪程度。"
        explain = fg.select_one(".fg6-explain")
        if explain: set_text(explain, explanation)
        source_detail = fg.select_one(".source-details .source")
        if source_detail:
            source_detail.clear()
            source_detail.append(explanation)
    # Refresh regional market tabs using the location registered for each approved mother.
    region_specs = [
        (region_panel_specs[0][0], {"台灣加權指數":"台灣加權指數","香港恆生指數":"香港恆生指數","上海綜合指數":"上海綜合指數","深證成指":"深證成指","日經225":"日經 225","日經 225":"日經 225","韓國KOSPI":"韓國 KOSPI","韓國 KOSPI":"韓國 KOSPI"}, 0, f"亞洲市場｜{previous_trade}各市場當地正式收盤", [
            ("https://apnews.com/article/806f71d95105bc7efbc760b194dd8cad","AP市場報導"),
            ("https://www.investing.com/indices/japan-ni225-historical-data","Nikkei 225"),
            ("https://www.investing.com/indices/kospi-historical-data","KOSPI"),
            ("https://www.investing.com/indices/taiwan-weighted-historical-data","TWSE"),
            ("https://www.investing.com/indices/hang-sen-40-historical-data","Hang Seng"),
            ("https://www.investing.com/indices/shanghai-composite-historical-data","Shanghai"),
            ("https://www.investing.com/indices/shenzhen-composite-historical-data","Shenzhen")
        ]),
        (region_panel_specs[1][0], {"英國FTSE 100":"英國 FTSE 100","英國 FTSE100":"英國 FTSE 100","德國DAX":"德國 DAX","德國 DAX":"德國 DAX","法國CAC 40":"法國 CAC 40","法國 CAC 40":"法國 CAC 40","STOXX Europe 600":"STOXX Europe 600"}, 1, f"歐洲市場｜{previous_trade}各市場當地正式收盤", [
            ("https://www.investing.com/indices/uk-100-historical-data","FTSE 100"),
            ("https://www.investing.com/indices/germany-30-historical-data","DAX"),
            ("https://www.investing.com/indices/france-40-historical-data","CAC 40"),
            ("https://www.investing.com/indices/stoxx-600-historical-data","STOXX Europe 600")
        ])
    ]
    for selector, row_map, comment_index, meta_text, links in region_specs:
        panel = unique(soup, selector, "regional market panel")
        meta = panel.select_one(".tab-panel-meta")
        if meta: set_text(meta, meta_text)
        normalized_map = {"".join(str(label).split()): key for label, key in row_map.items()}
        for row in panel.select(".row"):
            label = row.select_one("a.global-index-link")
            if not label: continue
            normalized_label = "".join(label.get_text(" ", strip=True).split())
            key = normalized_map.get(normalized_label)
            record = data.get("global_markets", {}).get(key) if key else None
            spans = row.select("span.r")
            if record and len(spans) >= 2:
                set_text(spans[0], record.get("display","待核實"))
                change = record.get("change_display","待核實")
                set_text(spans[1], change)
                state = "up" if "+" in str(change) else "down" if ("−" in str(change) or "-" in str(change)) else "flat"
                spans[1]["class"] = ["r", state] if change != "待核實" else ["r", "warn"]
        reason = panel.select_one(".market-reason")
        comments = data.get("market_comments", {}).get("global_markets", [])
        if reason and comment_index < len(comments): set_market_observation(reason, "", comments[comment_index])
        source = panel.select_one(".source")
        if source:
            source.clear()
            source.append("資料來源：")
            for url, label in links:
                source.append(source_link(url,label)); source.append(" ")

    # Observation content is preserved as source text, and overwritten only when full copy provided.
    view=unique(soup,"#view","market observation")
    if data.get("observation"):
        market_tab_label = unique(view, 'label[for="focus-tab-market"]', "market observation tab label")
        set_text(market_tab_label, "盤面觀察重點")
        panel=unique(view,".focus-panel.focus-market","market observation text")
        set_market_observation(panel.select_one(".key") or panel, "盤面觀察重點", data["observation"])

    # Populate all three existing Today Focus tabs; never leave stale mother-template text.
    levels_panel = unique(view, ".focus-panel.focus-levels", "key levels tab")
    levels_box = unique(levels_panel, ".key", "key levels content")
    disclosure_selector = "details.compact-disclosure" if monday else "details.source-details"
    disclosure = levels_box.select_one(disclosure_selector)
    if disclosure is None:
        raise ValueError(f"key levels source/method disclosure missing from approved {'Monday' if monday else 'weekday'} mother template")
    # The .key element is the approved dynamic content slot. Preserve its
    # mother-owned disclosure node and wrapper; render the five pivot labels
    # as simple vertical text/line-break content, without injecting new cards.
    disclosure.extract()
    for child in list(levels_box.contents):
        child.extract()
    levels_data = data.get("key_levels") or {}
    level_items = levels_data.get("items", [])
    if len(level_items) == 5:
        for item in level_items:
            title = soup.new_tag("b")
            title.string = str(item["name"]) + "："
            levels_box.append(title)
            for zh_label, field in (
                ("第二支撐", "s2"),
                ("第一支撐", "s1"),
                ("中樞", "p"),
                ("第一壓力", "r1"),
                ("第二壓力", "r2"),
            ):
                levels_box.append(soup.new_tag("br"))
                levels_box.append(f"{zh_label}：{item[field]}")
            levels_box.append(soup.new_tag("br"))
            levels_box.append(soup.new_tag("br"))
    else:
        levels_box.append("五項關鍵價位 OHLC 尚未完成同日現金指數核實，暫不提供支撐／中樞／壓力數值。")
        levels_box.append(soup.new_tag("br"))
    levels_box.append(disclosure)
    detail_body = disclosure.select_one("div") if monday else disclosure.select_one(".source")
    if detail_body is None:
        raise ValueError("key levels source/method disclosure body missing from selected mother template")
    detail_body.clear()
    if len(level_items) == 5:
        detail_body.append(f"基準交易日：{levels_data['baseline_date']}（美國當地正式收盤）。{levels_data['formula']} ")
        for item in level_items:
            detail_body.append(soup.new_tag("br"))
            detail_body.append(f"{item['name']}｜{item['ohlc']}｜")
            detail_body.append(source_link(item["url"], item.get("source_name") or "OHLC source"))
            detail_body.append("。")
    else:
        detail_body.append("本次五項現金指數 OHLC 未能在同一交易日與正式收盤點位完成一致性核實；因此不沿用母版舊數值，也不以 CFD／期貨替代。")
    if data.get("core_observation"):
        core_panel = unique(view, ".focus-panel.focus-core", "core observation tab")
        callout = unique(core_panel, ".callout", "core observation content")
        # Update the mother-owned heading and direct text slot in place. Do not
        # clear/rebuild the callout or move/remove its disclosure subtree.
        title_node = callout.find("b", recursive=False)
        if title_node is None:
            raise ValueError("core observation mother heading slot missing")
        title_node.string = data["core_observation"].get("heading", "今日核心觀察") + "："
        main_text = next(
            (child for child in callout.children
             if isinstance(child, NavigableString) and str(child).strip()),
            None,
        )
        if main_text is None:
            raise ValueError("core observation mother text slot missing")
        core_text = str(data["core_observation"].get("text", "")).strip()
        disclosure = callout.select_one("details.compact-disclosure")
        if monday and disclosure is None:
            raise ValueError("Monday core-observation disclosure missing from approved mother template")
        if disclosure is None:
            # Weekday mother has no disclosure; keep its native child structure
            # and place optional detail in the existing text node.
            extra = str(data["core_observation"].get("details", "")).strip()
            main_text.replace_with(core_text + (("；補充：" + extra) if extra else ""))
        else:
            main_text.replace_with(core_text)
            detail_nodes = disclosure.find_all("div", recursive=False)
            if len(detail_nodes) != 2:
                raise ValueError(
                    f"core observation disclosure must retain its two mother-owned detail slots; found {len(detail_nodes)}"
                )
            first_heading = detail_nodes[0].find("b", recursive=False)
            if first_heading is None:
                raise ValueError("core observation disclosure heading slot missing")
            first_heading.string = "本次核心觀察依據："
            first_bolds = detail_nodes[0].find_all("b", recursive=False)
            if len(first_bolds) > 1:
                first_bolds[1].string = "其他補充："
            first_texts = [
                child for child in detail_nodes[0].contents
                if isinstance(child, NavigableString) and str(child).strip()
            ]
            if not first_texts:
                raise ValueError("core observation disclosure primary text slot missing")
            detail_text = str(data["core_observation"].get("details", "")).strip()
            first_texts[0].replace_with(detail_text or "本次未提供額外補充內容。")
            for extra_index, extra_text in enumerate(first_texts[1:]):
                extra_text.replace_with(
                    "其餘補充資料已整併於上方。" if extra_index == 0
                    else "本段其他說明已整併於上方。"
                )
            second_texts = [
                child for child in detail_nodes[1].contents
                if isinstance(child, NavigableString) and str(child).strip()
            ]
            if not second_texts:
                raise ValueError("core observation disclosure secondary text slot missing")
            second_texts[0].replace_with("本次未提供其他獨立補充；請以本報告資料日期與來源註記為準。")
            for extra_text in second_texts[1:]:
                extra_text.replace_with("")
    else:
        raise ValueError("core_observation data missing; refusing to retain stale mother-template core text")
    # Fail closed if any Today Focus tab is stale, missing, or only partially assembled.
    focus_tabs = {
        "market": unique(view, ".focus-panel.focus-market", "market tab"),
        "levels": unique(view, ".focus-panel.focus-levels", "levels tab"),
        "core": unique(view, ".focus-panel.focus-core", "core tab"),
    }
    if len(view.select(".focus-tab-labels label")) != 3 or len(view.select(".focus-panels > .focus-panel")) != 3:
        raise ValueError("Today Focus must retain exactly three approved tabs and panels")
    observation_text = data["observation"].get("text", "") if isinstance(data["observation"], dict) else str(data["observation"])
    if observation_text not in focus_tabs["market"].get_text(" ", strip=True):
        raise ValueError("market observation text did not assemble")
    levels_text = focus_tabs["levels"].get_text(" ", strip=True)
    level_items = (data.get("key_levels") or {}).get("items", [])
    if len(level_items) == 5:
        required_level_fields = ("s2", "s1", "p", "r1", "r2")
        if any(item[field] not in levels_text for item in level_items for field in required_level_fields):
            raise ValueError("one or more of the five same-day cash-index key levels did not assemble")
        required_chinese_labels = ("第二支撐", "第一支撐", "中樞", "第一壓力", "第二壓力")
        if any(label not in levels_text for label in required_chinese_labels):
            raise ValueError("key levels must use all five Chinese labels in vertical rows")
    elif "暫不提供支撐" not in levels_text:
        raise ValueError("pending key levels state did not assemble")
    if data["core_observation"]["text"] not in focus_tabs["core"].get_text(" ", strip=True):
        raise ValueError("core observation text did not assemble")
    visible_focus_heading = soup.select_one(".today-focus-title")
    if visible_focus_heading and report_label not in visible_focus_heading.get_text(" ", strip=True):
        raise ValueError("today-focus heading retained a stale report date")
    report_date_meta = soup.select_one('meta[name="report-date"]')
    if report_date_meta and report_date_meta.get("content") != report_iso:
        raise ValueError("report-date metadata did not match report_date")
    focus_text = view.get_text(" ", strip=True)
    if "10/23" in focus_text or "2026/10/23" in focus_text:
        raise ValueError("stale 10/23 mother-template text remains in Today Focus")
    if data.get("bonds", {}).get("2年期美債殖利率", {}).get("change_display") == "待核實":
        raise ValueError("2-year Treasury daily change remains unresolved")
    for item in level_items:
        if not any(a.get("href") == item["url"] for a in focus_tabs["levels"].select("a")):
            raise ValueError("key level OHLC source link missing for " + item.get("name", "unknown index"))
    # Enforce the selected template's weekday-specific section contract.
    monday_only_ids = ("#last-week-calendar", "#last-week-earnings")
    if monday:
        for selector in monday_only_ids:
            unique(soup, selector, "Monday-only section")
    elif any(soup.select(selector) for selector in monday_only_ids):
        raise ValueError("weekday mother/output must not contain Monday-only previous-week sections")
    # Populate the fixed, mother-template-owned Fed weekly agenda slots.
    populate_fed_weekly_agenda(soup, data)
    # Final FactSet freshness gate: prevent a stale hard-coded earnings panel from passing QA.
    final_health = unique(soup, "#sp500-earnings-health", "S&P 500 earnings health")
    health_text = final_health.get_text(" ", strip=True)
    expected_health = data.get("earnings_health", {})
    required_health_values = (
        "as_of_date", "reported_pct", "eps_beat_pct", "revenue_beat_pct",
        "blended_eps_yoy", "blended_revenue_yoy", "eps_surprise", "forward_pe",
        "mag7_eps_growth", "other_493_eps_growth",
    )
    missing_health_values = [
        key for key in required_health_values
        if not str(expected_health.get(key, "")).strip()
    ]
    if missing_health_values:
        raise ValueError("FactSet fixture missing required rendered values: " + ", ".join(missing_health_values))
    mismatched_health_values = [
        key for key in required_health_values
        if str(expected_health[key]) not in health_text
    ]
    if mismatched_health_values:
        raise ValueError(
            "S&P 500 earnings-health panel does not match the dated fixture values: "
            + ", ".join(mismatched_health_values)
        )
    factset_source = final_health.select_one("details a")
    if not factset_source or factset_source.get("href") != expected_health.get("source_url"):
        raise ValueError("FactSet source link is missing or does not match the dated fixture URL")
    # Commodity month/code belongs in collapsed source details, never in the visible meta or observation copy.
    for panel_id, records in (("tac-assets-panel-3", data.get("energy", {})), ("tac-assets-panel-4", data.get("metals", {}))):
        panel = unique(soup, f"#{panel_id}", panel_id)
        meta_text = (panel.select_one(".tab-panel-meta") or soup.new_tag("div")).get_text(" ", strip=True)
        reason_text = (panel.select_one(".market-reason") or soup.new_tag("div")).get_text(" ", strip=True)
        source_text = " ".join(node.get_text(" ", strip=True) for node in panel.select("details.source-details .source"))
        for instrument, record in records.items():
            contract_label = str(record.get("contract_label") or "").strip()
            if not contract_label:
                continue
            if contract_label in meta_text or contract_label in reason_text:
                raise ValueError(f"{panel_id}/{instrument}: full contract label leaked outside source details")
            if contract_label not in source_text:
                raise ValueError(f"{panel_id}/{instrument}: contract label missing from source details")
            # Compare display labels independent of harmless Latin/Chinese spacing in the locked mother.
            visible_name = str(record.get("display_name") or instrument).strip()
            visible_row = next(
                (node for node in panel.select(".row")
                 if visible_name in node.get_text(" ", strip=True)),
                None,
            )
            visible_link = visible_row.select_one("b a") if visible_row else None
            if visible_link is None or "".join(visible_link.get_text(" ", strip=True).split()) != "".join(visible_name.split()):
                raise ValueError(f"{panel_id}/{instrument}: visible name must be {visible_name!r}; contract details belong in source disclosure")
            source = record.get("source") or {}
            if source.get("quote_type") != "investing_historical_close":
                raise ValueError(f"{panel_id}/{instrument}: quote must use Investing.com historical close, not Last/preliminary")
            if source.get("url") != record.get("instrument_url"):
                raise ValueError(f"{panel_id}/{instrument}: source URL and product link must be the same history page")
            if "historical-data" not in str(source.get("url") or ""):
                raise ValueError(f"{panel_id}/{instrument}: source URL must be an Investing.com historical-data page")
            if str(record.get("display") or "").replace(",", "") != str(source.get("history_close") or "").replace(",", ""):
                raise ValueError(f"{panel_id}/{instrument}: displayed quote differs from the captured historical close")
            if str(record.get("change_display") or "") != str(source.get("history_change") or ""):
                raise ValueError(f"{panel_id}/{instrument}: displayed daily change differs from the captured historical row")
    # Commodity commentary must match the settlement values actually displayed.
    energy_text = soup.select_one("#tac-assets-panel-3 .market-reason")
    if energy_text and "延遲 Last" in energy_text.get_text(" ", strip=True):
        raise ValueError("Commodity commentary still conflicts with displayed settlement prices")
    # FINAL regional observation render. Keep the three global-market tabs aligned
    # with the fixture contract (0=US, 1=Asia, 3=Europe) after all earlier mutations.
    final_region_observations = [
        ("#tac-global-panel-0", "📌 美股觀察", 0),
        ("#tac-global-panel-1", "📌 亞股觀察", 1),
        ("#tac-global-panel-2", "📌 歐股觀察", 3),
    ]
    final_comments = data.get("market_comments", {}).get("global_markets", [])
    for selector, heading, idx in final_region_observations:
        panel = unique(soup, selector, heading + " final panel")
        note = unique(panel, ".market-reason", heading + " final card")
        value = final_comments[idx] if idx < len(final_comments) else ""
        if not str(value).strip():
            raise ValueError(heading + " final content missing from report data")
        set_market_observation(note, heading, value)
    for selector, heading, idx in final_region_observations:
        rendered = unique(soup, selector, heading + " final panel").select_one(".market-reason")
        if heading not in rendered.get_text(" ", strip=True) or len(rendered.get_text(" ", strip=True)) < len(heading) + 10:
            raise ValueError(heading + " final observation failed DOM verification")
    # The Monday mother also retains two legacy regional summary panels. Re-render
    # these last so their commentary cannot remain cross-wired to the quote-row indices.
    legacy_region_observations = [
        ("#asia", "📌 亞股摘要", 1),
        ("#tac-region-panel-2", "📌 歐股摘要", 3),
    ]
    for selector, heading, idx in legacy_region_observations:
        panel = soup.select_one(selector)
        if panel is None:
            continue
        note = panel.select_one(".market-reason")
        if note is None:
            raise ValueError(heading + " legacy summary slot missing")
        value = final_comments[idx] if idx < len(final_comments) else ""
        if not str(value).strip():
            raise ValueError(heading + " legacy summary data missing")
        set_market_observation(note, heading, value)
        rendered = note.get_text(" ", strip=True)
        expected_body = str(value).split("｜", 1)[1].strip() if "｜" in str(value) else str(value).strip()
        if expected_body not in rendered:
            raise ValueError(heading + " legacy summary final render mismatch")
    # Final whole-report economic card gate: current-week and Monday retrospective
    # cards must all satisfy the same five-zone DOM contract before serialization.
    current_cards = soup.select("#calendar .week-econ-panels details.econ-event")
    if not current_cards:
        raise ValueError("no current-week economic cards rendered")
    for index, card in enumerate(current_cards, 1):
        validate_economic_card(card, f"final current-week card #{index}", "econ-toggle")
    if monday:
        previous_cards = soup.select("#last-week-calendar .last-week-calendar-collapse .econ-event-list details.econ-event")
        if not previous_cards:
            raise ValueError("no five-star previous-week economic cards rendered")
        for index, card in enumerate(previous_cards, 1):
            validate_economic_card(card, f"final previous-week card #{index}", "econ-event-toggle")
    # Embed immutable source identities into the exact HTML that will be QA'd and delivered.
    report_meta = soup.select_one('meta[name="report-date"]')
    if report_meta is None or report_meta.get("content") != report_iso:
        raise ValueError("approved mother report-date metadata missing or mismatched")
    build_provenance = {
        "report_date": report_iso,
        "build_commit_sha": subprocess.run(["git", "rev-parse", "HEAD"], check=True, text=True, capture_output=True).stdout.strip(),
        "template_key": "monday" if monday else "weekdays",
        "template_path": str(master_path.relative_to(ROOT)),
        "template_blob_sha": actual,
        "manifest_path": str(MANIFEST.relative_to(ROOT)),
        "manifest_blob_sha": sha_blob(MANIFEST.read_text(encoding="utf-8")),
        "qa_contract_path": str(QA_CONTRACT.relative_to(ROOT)),
        "qa_contract_blob_sha": sha_blob(QA_CONTRACT.read_text(encoding="utf-8")),
        "active_rules_path": str(ACTIVE_RULES.relative_to(ROOT)),
        "active_rules_blob_sha": sha_blob(ACTIVE_RULES.read_text(encoding="utf-8")),
        "candidate_rules_path": str(CANDIDATE_RULES.relative_to(ROOT)),
        "candidate_rules_blob_sha": sha_blob(CANDIDATE_RULES.read_text(encoding="utf-8")),
        "fixture_path": str(Path(args.data)),
        "fixture_blob_sha": sha_blob(Path(args.data).read_text(encoding="utf-8")),
        "builder_path": str(Path(__file__).relative_to(ROOT)),
        "builder_blob_sha": sha_blob(Path(__file__).read_text(encoding="utf-8")),
        # Repository and branch metadata live on each week record, not the
        # top-level calendar envelope returned by load_authoritative_calendar().
        "calendar_repository": calendar_source["current"]["repository"],
        "calendar_branch": calendar_source["current"]["branch"],
        "calendar_main_commit_sha": calendar_source["main_commit_sha"],
        "calendar_current_path": calendar_source["current"]["path"],
        "calendar_current_blob_sha": calendar_source["current"]["blob_sha"],
        "calendar_previous_path": calendar_source["previous"]["path"],
        "calendar_previous_blob_sha": calendar_source["previous"]["blob_sha"],
        "mode": "simulation-only",
        "review_ready": not bool(data.get("review_ready_blockers", [])),
        "review_ready_blockers": data.get("review_ready_blockers", []),
        "data_audit": {
            "quality_note": data.get("quality_note", ""),
            "warning_note": data.get("warning_note", ""),
            "pending_items": data.get("pending_items", []),
            "report_cutoff_taipei": data.get("report_cutoff_taipei", ""),
            "news_window_taipei": data.get("news_window_taipei", "")
        }
    }
    provenance_comment = Comment(" TAC_BUILD_PROVENANCE " + json.dumps(build_provenance, ensure_ascii=False, separators=(",", ":")) + " ")
    soup.head.append(provenance_comment)
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(str(soup),encoding="utf-8")
    print(json.dumps({"output":str(out),"master_sha":actual,"report_date":report_iso,"template":"monday" if monday else "weekdays","builder_sha":build_provenance["builder_blob_sha"],"fixture_sha":build_provenance["fixture_blob_sha"],"calendar_main_commit_sha":calendar_source["main_commit_sha"],"calendar_current_blob_sha":calendar_source["current"]["blob_sha"],"calendar_previous_blob_sha":calendar_source["previous"]["blob_sha"],"sections_updated":["title","summary","sentiment","news","global_markets","sectors","bonds","fx","energy","metals","risk","fedwatch","calendar headings","five-index OHLC key levels","commodity contract labels","review readiness and data audit"],"review_ready":not bool(data.get("review_ready_blockers", [])),"calendar_source":provenance},ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
