#!/usr/bin/env python3
"""Build renderer-ready TAC economic and earnings calendar panels from weekly JSON.

The adapter is read-only: it never edits the weekly calendar database or mother
templates. It maps events to status lists that physically exist in the selected
approved template and fails closed if a non-empty status has no list container.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from render_tac_market_safe import SourceTreeParser, select, spans_inside

WEEKDAYS = ("一", "二", "三", "四", "五", "六", "日")
TAIPEI = ZoneInfo("Asia/Taipei")
NEW_YORK = ZoneInfo("America/New_York")
CURRENCY_PREFIX = {
    "USD": "US$", "GBP": "£", "EUR": "€", "JPY": "¥",
    "CAD": "C$", "AUD": "A$", "CHF": "CHF "
}


def parse_aware(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}: timezone-aware ISO datetime required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label}: invalid ISO datetime") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label}: timezone offset required")
    return parsed


def iso_week_bounds(day: date) -> tuple[date, date]:
    monday = day - timedelta(days=day.weekday())
    return monday, monday + timedelta(days=4)


def validate_week(data: dict[str, Any], expected_start: date, label: str) -> None:
    if not isinstance(data, dict) or not isinstance(data.get("events"), dict):
        raise ValueError(f"{label}: weekly calendar object/events missing")
    start, end = iso_week_bounds(expected_start)
    if date.fromisoformat(data.get("week_start", "")) != start:
        raise ValueError(f"{label}: week_start mismatch; expected {start.isoformat()}")
    if date.fromisoformat(data.get("week_end", "")) != end:
        raise ValueError(f"{label}: week_end mismatch; expected {end.isoformat()}")
    for kind in ("economic", "earnings"):
        if not isinstance(data["events"].get(kind), list):
            raise ValueError(f"{label}: events.{kind} must be an array")


def fmt_day(day: date) -> str:
    return f"{day.month:02d}/{day.day:02d}（{WEEKDAYS[day.weekday()]}）"


def display_value(value: Any, missing: str = "待核實") -> str:
    if value is None or value == "":
        return missing
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, float):
        return f"{value:,.4f}".rstrip("0").rstrip(".")
    return str(value)


def source_links(records: list[Any]) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            continue
        url, name = record.get("url"), record.get("name")
        if not isinstance(url, str) or not url.startswith("https://") or not isinstance(name, str) or not name.strip():
            continue
        if url in seen:
            continue
        seen.add(url)
        links.append({"url": url, "text": name.strip()})
    if not links:
        raise ValueError("calendar event has no valid HTTPS source link")
    return links


def event_day(row: dict[str, Any], label: str) -> date:
    return parse_aware(row.get("event_date"), f"{label}.event_date").astimezone(TAIPEI).date()


def select_events(rows: list[dict[str, Any]], start: date, end: date,
                  label: str) -> list[dict[str, Any]]:
    selected = []
    seen_ids: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"{label}[{index}]: event must be an object")
        stars = row.get("importance_stars")
        if stars not in (4, 5):
            continue
        ident = row.get("id")
        if not isinstance(ident, str) or not ident.strip() or ident in seen_ids:
            raise ValueError(f"{label}[{index}]: unique non-empty event id required")
        seen_ids.add(ident)
        day = event_day(row, f"{label}[{index}]")
        if not start <= day <= end:
            raise ValueError(f"{label}.{ident}: event date outside declared week")
        if row.get("status") not in {"upcoming", "released"}:
            raise ValueError(f"{label}.{ident}: unsupported status {row.get('status')!r}")
        selected.append(row)
    selected.sort(key=lambda row: parse_aware(row["event_date"], f"{label}.{row['id']}.event_date"))
    return selected


def bucket_current_week(rows: list[dict[str, Any]], report_day: date,
                        label: str) -> dict[str, list[dict[str, Any]]]:
    buckets = {"today": [], "upcoming": [], "published": []}
    for row in rows:
        day = event_day(row, f"{label}.{row['id']}")
        status = row["status"]
        if day == report_day:
            buckets["today"].append(row)
        elif day > report_day:
            if status == "released":
                raise ValueError(f"{label}.{row['id']}: future-dated event cannot be released")
            buckets["upcoming"].append(row)
        else:
            if status != "released":
                raise ValueError(f"{label}.{row['id']}: past event is not marked released")
            buckets["published"].append(row)
    return buckets


def list_contracts(template_html: str, container_selector: str,
                   list_selector: str, card_selector: str,
                   field_selector: str, label_selector: str) -> list[dict[str, Any]] | None:
    """Read status and approved detail-field labels from each real template list prototype."""
    parser = SourceTreeParser(template_html)
    parser.feed(template_html)
    parser.close()
    containers = select(parser.root, container_selector)
    if not containers:
        return None
    if len(containers) != 1:
        raise ValueError(f"{container_selector}: template container missing or duplicated")
    contracts = []
    for list_node in select(containers[0], list_selector):
        group = list_node.parent
        while group is not None and "calendar-status-group" not in group.classes:
            group = group.parent
        if group is None:
            raise ValueError(f"{list_selector}: list is not inside a calendar-status-group")
        headings = select(group, "h4.calendar-status-heading")
        if len(headings) != 1:
            raise ValueError(f"{list_selector}: status heading missing or duplicated")
        heading_text = "".join(span.text for span in spans_inside(headings[0], parser.spans)).strip()
        if "今日" in heading_text:
            status = "today"
        elif "即將公布" in heading_text:
            status = "upcoming"
        elif "已公布" in heading_text:
            status = "published"
        else:
            raise ValueError(f"{list_selector}: unrecognized status heading {heading_text[:80]!r}")
        cards = select(list_node, card_selector)
        field_labels: list[str] = []
        if cards:
            fields = select(cards[0], field_selector)
            for field_node in fields:
                labels = select(field_node, label_selector)
                if len(labels) != 1:
                    raise ValueError(f"{list_selector}: prototype field label missing or duplicated")
                label_text = "".join(span.text for span in spans_inside(labels[0], parser.spans)).strip()
                if not label_text:
                    raise ValueError(f"{list_selector}: prototype field label is empty")
                field_labels.append(label_text)
        contracts.append({"status": status, "field_labels": field_labels, "has_prototype": bool(cards)})
    return contracts

def event_list_payload(rows: list[dict[str, Any]], status: str,
                       kind: str, field_labels: list[str]) -> list[dict[str, Any]]:
    if rows and not field_labels:
        raise ValueError(f"{kind}.{status}: non-empty list has no approved card/detail prototype")
    if kind == "economic":
        return [economic_item(row, status, field_labels) for row in rows]
    return [earnings_item(row, status) for row in rows]


def economic_item(row: dict[str, Any], status: str,
                  field_labels: list[str]) -> dict[str, Any]:
    dt = parse_aware(row["event_date"], f"economic.{row['id']}.event_date").astimezone(TAIPEI)
    time_known = row.get("time_known", True)
    time_text = dt.strftime("%H:%M") if time_known else "待核實"
    actual_missing = "尚未公布" if status != "published" else "待核實"
    refs = [row.get("source"), row.get("data_reference"), row.get("consensus_source")]
    value_by_label = {
        "前值": {"label": "前值", "text": display_value(row.get("previous"))},
        "預估": {"label": "預估", "text": display_value(row.get("forecast"))},
        "市場預估": {"label": "市場預估", "text": display_value(row.get("forecast"))},
        "實際": {"label": "實際", "text": display_value(row.get("actual"), actual_missing)},
        "市場影響": {"label": "市場影響", "text": display_value(row.get("impact_judgment"))},
        "觀察重點": {"label": "觀察重點", "text": display_value(row.get("impact_judgment"))},
        "來源": {"label": "來源", "links": source_links(refs)},
        "資料來源": {"label": "資料來源", "links": source_links(refs)},
    }
    fields = []
    for label in field_labels:
        if label not in value_by_label:
            raise ValueError(f"economic.{row['id']}: unsupported mother-template detail label {label!r}")
        fields.append(value_by_label[label])
    return {
        "expected_name": None,
        "date": fmt_day(dt.date()),
        "time": time_text,
        "country": display_value(row.get("region")),
        "name": display_value(row.get("event_name")),
        "stars_text": "★★★★★" if row["importance_stars"] == 5 else "★★★★☆",
        "fields": fields,
    }


def currency_amount(value: Any, currency: Any, unit: Any = None,
                    missing: str = "待核實") -> str:
    if value is None or value == "":
        return missing
    prefix = CURRENCY_PREFIX.get(str(currency or "").upper(), f"{currency} " if currency else "")
    try:
        number = float(value)
        rendered = f"{number:,.4f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        rendered = str(value)
    suffix = ""
    unit_text = str(unit or "").lower()
    if unit_text in {"b", "usd billions", "billions", "billion"}:
        suffix = "B"
    elif unit_text in {"m", "usd millions", "millions", "million"}:
        suffix = "M"
    elif unit_text in {"k", "usd thousands", "thousands", "thousand"}:
        suffix = "K"
    return f"{prefix}{rendered}{suffix}"


def session_label(session: Any) -> str:
    return {
        "before_market": "盤前",
        "after_market": "盤後",
        "during_market": "盤中",
        "unknown": "公布時段待核實",
    }.get(str(session), "公布時段待核實")


def earnings_result(title: str, actual: Any, expected: Any,
                    currency: Any, unit: Any, status: Any, note: Any,
                    event_status: str) -> dict[str, str]:
    compare = status if status in {"beat", "miss"} else "pending"
    missing_actual = "待核實" if event_status == "released" else "尚未公布"
    return {
        "title": title,
        "actual": currency_amount(actual, currency, unit, missing_actual),
        "expected": currency_amount(expected, currency, unit),
        "status_text": {"beat": "高於預期", "miss": "低於預期", "pending": "待核實"}[compare],
        "card_class": compare,
        "status_class": compare,
        "note": display_value(note, "待核實"),
    }


def earnings_item(row: dict[str, Any], status: str) -> dict[str, Any]:
    dt_tw = parse_aware(row["event_date"], f"earnings.{row['id']}.event_date").astimezone(TAIPEI)
    dt_us = dt_tw.astimezone(NEW_YORK)
    session = session_label(row.get("session"))
    us_date = fmt_day(dt_us.date())
    if row.get("session") in {"before_market", "after_market", "during_market"}:
        us_date += session
    if row.get("time_known") is True:
        tw_date = f"台灣時間 {fmt_day(dt_tw.date())} {dt_tw.strftime('%H:%M')}"
    else:
        tw_date = f"台灣時間 {fmt_day(dt_tw.date())}；精確時刻待核實"
    ticker = row.get("ticker") or "代碼待核實"
    industry = row.get("industry") or "產業待核實"
    refs = [row.get("source"), row.get("consensus_source"),
            row.get("revenue_consensus_source"), row.get("price_reaction_source")]
    if status == "published":
        fields = [
            {"label": "財報判讀", "text": display_value(row.get("financial_judgment"))},
            {"label": "股價當日表現", "text": display_value(row.get("stock_price_reaction"))},
            {"label": "資料來源", "links": source_links(refs)},
        ]
        results = [
            earnings_result("EPS", row.get("eps_actual"), row.get("eps_estimate"),
                            row.get("eps_currency"), None, row.get("eps_comparison_status"),
                            row.get("eps_note"), status),
            earnings_result("營收", row.get("revenue_actual"), row.get("revenue_estimate"),
                            row.get("revenue_currency"), row.get("revenue_unit"),
                            row.get("revenue_comparison_status"), row.get("revenue_note"), status),
        ]
    else:
        timing = f"{session}；{tw_date}" if row.get("time_known") else f"{session}；{tw_date}"
        fields = [
            {"label": "公布時段", "text": timing},
            {"label": "EPS 預估／實際", "text": f"預估 {currency_amount(row.get('eps_estimate'), row.get('eps_currency'))}；實際 {currency_amount(row.get('eps_actual'), row.get('eps_currency'), missing='尚未公布')}"},
            {"label": "營收預估／實際", "text": f"預估 {currency_amount(row.get('revenue_estimate'), row.get('revenue_currency'), row.get('revenue_unit'))}；實際 {currency_amount(row.get('revenue_actual'), row.get('revenue_currency'), row.get('revenue_unit'), '尚未公布')}"},
            {"label": "財報判讀與股價反應", "text": display_value(row.get("financial_judgment") or row.get("stock_price_reaction"))},
            {"label": "資料來源", "links": source_links(refs)},
        ]
        results = []
    return {
        "expected_company": None,
        "us_date": us_date,
        "tw_date": tw_date,
        "company": display_value(row.get("company")),
        "company_sub": f"{ticker}｜{industry}",
        "stars_text": "★★★★★" if row["importance_stars"] == 5 else "★★★★☆",
        "fields": fields,
        "results": results,
    }


def build_calendar_snapshot(current_week: dict[str, Any],
                            previous_week: dict[str, Any] | None,
                            report_date: str, template_html: str,
                            binding: dict[str, Any]) -> dict[str, Any]:
    report_day = date.fromisoformat(report_date)
    current_start, current_end = iso_week_bounds(report_day)
    validate_week(current_week, current_start, "current_week")
    monday_report = report_day.weekday() == 0
    previous_start = current_start - timedelta(days=7)
    previous_end = current_start - timedelta(days=3)
    if monday_report:
        if previous_week is None:
            raise ValueError("Monday report requires the previous ISO-week calendar database")
        validate_week(previous_week, previous_start, "previous_week")
    elif previous_week is not None:
        raise ValueError("previous_week data is only allowed for Monday reports")

    result: dict[str, Any] = {}
    for kind, group_name in (("economic", "economic_calendar"), ("earnings", "earnings_calendar")):
        panel_specs = binding.get("groups", {}).get(group_name, {}).get("panels", {})
        if not panel_specs:
            raise ValueError(f"binding map missing {group_name}.panels")
        rows = select_events(current_week["events"][kind], current_start, current_end, f"current_week.{kind}")
        buckets = bucket_current_week(rows, report_day, f"current_week.{kind}")
        panels: dict[str, Any] = {}
        for panel_key, panel_spec in panel_specs.items():
            if panel_key == "last_week":
                if not monday_report:
                    continue
                prior_rows = select_events(previous_week["events"][kind], previous_start, previous_end,
                                           f"previous_week.{kind}")
                invalid = [row["id"] for row in prior_rows if row["status"] != "released"]
                if invalid:
                    raise ValueError(f"previous_week.{kind}: prior-week events must be released: {invalid}")
                contracts = list_contracts(template_html, panel_spec["container"], panel_spec["list_selector"],
                                           panel_spec.get("event_selector", panel_spec.get("item_selector")),
                                           ".econ-field" if kind == "economic" else ".earnings-detail-field",
                                           "label")
                if contracts is None:
                    raise ValueError(f"Monday mother template missing {group_name}.last_week container")
                lists = []
                for contract in contracts:
                    status = contract["status"]
                    items = event_list_payload(prior_rows if status == "published" else [], status, kind,
                                               contract["field_labels"])
                    if items and not contract["has_prototype"]:
                        raise ValueError(f"{group_name}.last_week.{status}: no approved card prototype")
                    lists.append({"items": items})
                if "published" not in [x["status"] for x in contracts] and prior_rows:
                    raise ValueError(f"{group_name}.last_week has prior-week events but no published list container")
                panels[panel_key] = {"lists": lists}
            elif panel_key == "current_week":
                contracts = list_contracts(template_html, panel_spec["container"], panel_spec["list_selector"],
                                           panel_spec.get("event_selector", panel_spec.get("item_selector")),
                                           " .econ-field" if kind == "economic" else " .earnings-detail-field",
                                           "label")
                if contracts is None:
                    continue
                lists = []
                for contract in contracts:
                    status = contract["status"]
                    items = event_list_payload(buckets[status], status, kind, contract["field_labels"])
                    if items and not contract["has_prototype"]:
                        raise ValueError(f"{group_name}.current_week.{status}: no approved card prototype")
                    lists.append({"items": items})
                missing = [status for status, rows_for_status in buckets.items()
                           if rows_for_status and status not in [x["status"] for x in contracts]]
                if missing:
                    raise ValueError(
                        f"{group_name}.current_week: non-empty status bucket(s) {missing} "
                        "have no approved list container in this mother template"
                    )
                panels[panel_key] = {"lists": lists}
        result[group_name] = {"panels": panels}
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report-date", required=True)
    ap.add_argument("--current-week", required=True)
    ap.add_argument("--previous-week")
    ap.add_argument("--template", required=True)
    ap.add_argument("--binding", default="scripts/tac_html_binding_map.json")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    try:
        report_day = date.fromisoformat(args.report_date)
        current = json.loads((ROOT / args.current_week).read_text(encoding="utf-8"))
        previous = json.loads((ROOT / args.previous_week).read_text(encoding="utf-8")) if args.previous_week else None
        template = (ROOT / args.template).read_text(encoding="utf-8")
        binding = json.loads((ROOT / args.binding).read_text(encoding="utf-8"))
        snapshot = build_calendar_snapshot(current, previous, report_day.isoformat(), template, binding)
        output = (ROOT / args.output).resolve()
        protected = {
            (ROOT / "index.html").resolve(),
            (ROOT / "TAC_WORK_RULES.md").resolve(),
            (ROOT / "母版專區/TAC_母版_週一_2026-10-28_最終定版.html").resolve(),
            (ROOT / "母版專區/TAC_母版_週二至週五_2026-10-28_最終定版.html").resolve(),
        }
        if output in protected or output == (ROOT / args.template).resolve():
            raise ValueError("refusing to overwrite a protected or input path")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        counts = {
            group: sum(len(x["items"]) for panel in data["panels"].values()
                       for x in panel["lists"])
            for group, data in snapshot.items()
        }
        print(f"PASS: calendar snapshot built for {report_day.isoformat()}: {counts}")
        return 0
    except Exception as exc:
        print(f"CALENDAR ADAPTER BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
