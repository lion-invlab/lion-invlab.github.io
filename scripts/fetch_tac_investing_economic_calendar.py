#!/usr/bin/env python3
"""Parse a saved Investing.com Hong Kong economic-calendar HTML capture.

Investing.com does not provide a public calendar API. This utility deliberately
does not call or bypass its protected service endpoint. It parses an HTML file
captured through the normal website interface, retains all rows and records provider stars only as provenance,
and defaults coverage to incomplete until a human confirms the full date range.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

SOURCE_URL = "https://hk.investing.com/economic-calendar/"
SOURCE_NAME = "Investing.com"
TAIPEI = ZoneInfo("Asia/Taipei")


def clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = re.sub(r"\s+", " ", value).strip()
    return None if value in {"", "-", "--", "—", "N/A"} else value


def parse_event_time(value: str | None) -> time | None:
    value = clean(value)
    if value is None or value.lower() in {"all day", "tentative"}:
        return None
    for fmt in ("%H:%M", "%I:%M %p", "%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    return None


def day_from_header(row, source_tz: ZoneInfo) -> date | None:
    cell = row.find(id=re.compile(r"^theDay\d+$"))
    if cell is None:
        return None
    stamp = int(re.sub(r"\D", "", cell.get("id", "")))
    return datetime.fromtimestamp(stamp, tz=timezone.utc).astimezone(source_tz).date()


def collect_calendar_dates(html: str, source_tz: ZoneInfo) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    dates = []
    for row in soup.select("tr"):
        day = day_from_header(row, source_tz)
        if day is not None:
            dates.append(day.isoformat())
    return sorted(set(dates))


def parse_calendar_html(html: str, observed_at: str, source_tz: ZoneInfo, source_url: str = SOURCE_URL) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    current_day: date | None = None
    result: list[dict] = []
    for row in soup.select("tr"):
        row_id = row.get("id") or ""
        if not row_id.startswith("eventRowId_"):
            header_day = day_from_header(row, source_tz)
            if header_day is not None:
                current_day = header_day
            continue
        if current_day is None:
            raise ValueError("calendar event row appeared before its date header")
        event_id = row_id.removeprefix("eventRowId_")
        time_cell = row.select_one("td.first.left")
        currency_cell = row.select_one("td.flagCur")
        importance_cell = row.select_one("td.sentiment")
        event_cell = row.select_one("td.left.event")
        if not all((time_cell, currency_cell, importance_cell, event_cell)):
            raise ValueError(f"event {event_id}: required source columns are missing")
        star_match = re.search(r"bull(\d)", importance_cell.get("data-img_key") or "")
        source_importance_stars = int(star_match.group(1)) if star_match else None
        event_time = parse_event_time(time_cell.get_text(" ", strip=True))
        local_source_time = event_time or time.min
        source_dt = datetime.combine(current_day, local_source_time, tzinfo=source_tz)
        taipei_dt = source_dt.astimezone(TAIPEI)
        currency = clean(currency_cell.get_text(" ", strip=True))
        country = currency_cell.find("span")
        region = clean(country.get("title") if country else None) or currency or "Global"

        def cell_value(name: str) -> str | None:
            cell = row.select_one(f"#event{name}_{event_id}")
            return clean(cell.get_text(" ", strip=True)) if cell else None

        actual = cell_value("Actual")
        forecast = cell_value("Forecast")
        previous = cell_value("Previous")
        captured = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
        status = "released" if actual is not None else ("upcoming" if taipei_dt > captured else "pending_verification")
        result.append({
            "id": str(event_id),
            "event_date": taipei_dt.isoformat(),
            "region": region,
            "event_name": clean(event_cell.get_text(" ", strip=True)) or "Unnamed event",
            "importance_stars": None,
            "importance_basis": "pending_tac_assessment",
            "importance_basis_source": None,
            "source_importance_stars": source_importance_stars,
            "previous": previous,
            "forecast": forecast,
            "actual": actual,
            "status": status,
            "impact_judgment": None,
            "source": {
                "name": SOURCE_NAME,
                "url": source_url,
                "published_at": None,
                "observed_at": observed_at,
                "publisher": SOURCE_NAME,
                "notes": "由 Investing.com 官方公開網頁介面擷取的 HTML；來源原生星等僅作參考留存，不等同 TAC 評級，須另行獨立評定，來源網址記錄實際成功的區域站點。"
            }
        })
    result.sort(key=lambda item: item["event_date"])
    return result


def build_payload(args) -> dict:
    source_tz = ZoneInfo(args.source_timezone)
    observed_at = datetime.now(timezone.utc).astimezone(TAIPEI).isoformat()
    html = Path(args.input_html).read_text(encoding="utf-8")
    source_match = re.search(r"<!--\s*tac-source-url:\s*(https?://[^\s]+)\s*-->", html)
    source_url = source_match.group(1).strip() if source_match else SOURCE_URL
    events = parse_calendar_html(html, observed_at, source_tz, source_url)
    checked_dates = collect_calendar_dates(html, source_tz)
    report_day = date.fromisoformat(args.report_date)
    current_week_start = report_day.fromordinal(report_day.toordinal() - report_day.weekday())
    week_start = current_week_start if args.group == "current" else date.fromordinal(current_week_start.toordinal() - 7)
    expected_dates = [(date.fromordinal(week_start.toordinal() + i)).isoformat() for i in range(5)]
    verified_weekdays = sorted(set(checked_dates) & set(expected_dates))
    full_week_present = set(expected_dates).issubset(set(checked_dates))
    if args.group == "previous":
        event_key, coverage_key = "previous_economic_events", "previous_economic_calendar"
    else:
        event_key, coverage_key = "economic_events", "economic_calendar"
    status = "complete" if args.coverage_verified and full_week_present else "incomplete"
    return {
        "report_date": args.report_date,
        "trading_date": args.trading_date,
        "observed_at": observed_at,
        "source": {"name": SOURCE_NAME, "url": source_url, "publisher": SOURCE_NAME},
        event_key: events,
        "coverage": {
            coverage_key: {
                "status": status,
                "source_refs": [source_url],
                "checked_at": observed_at,
                "checked_dates": verified_weekdays
            }
        }
    }


def self_test() -> None:
    observed = "2026-10-31T12:00:00+08:00"
    fixture = """
    <table>
      <tr><td id="theDay1792972800">Monday</td></tr>
      <tr id="eventRowId_123"><td class="first left">14:30</td>
        <td class="flagCur"><span title="united states"></span>USD</td>
        <td class="sentiment" data-img_key="bull3"></td>
        <td class="left event">Nonfarm Payrolls</td>
        <td id="eventActual_123">200K</td><td id="eventForecast_123">180K</td>
        <td id="eventPrevious_123">175K</td></tr>
      <tr id="eventRowId_124"><td class="first left">15:00</td>
        <td class="flagCur"><span title="united states"></span>USD</td>
        <td class="sentiment" data-img_key="bull2"></td>
        <td class="left event">Medium event</td></tr>
      <tr id="eventRowId_125"><td class="first left">All Day</td>
        <td class="flagCur"><span title="euro zone"></span>EUR</td>
        <td class="sentiment" data-img_key="bull3"></td>
        <td class="left event">Three star all-day event</td></tr>
    </table>
    """
    events = parse_calendar_html(fixture, observed, ZoneInfo("UTC"))
    assert len(events) == 3
    by_id = {event["id"]: event for event in events}
    assert by_id["123"]["importance_stars"] is None
    assert by_id["123"]["source_importance_stars"] == 3
    assert by_id["124"]["source_importance_stars"] == 2
    assert by_id["123"]["event_name"] == "Nonfarm Payrolls"
    assert by_id["123"]["actual"] == "200K"
    assert by_id["123"]["event_date"].endswith("+08:00")
    assert by_id["125"]["event_name"] == "Three star all-day event"
    assert by_id["125"]["status"] == "pending_verification"
    print("PASS: all source rows retained; provider stars separated from TAC assessment")
    print("PASS: offline HTML parser does not call Investing.com protected endpoints")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-html")
    parser.add_argument("--source-timezone", default="Asia/Taipei")
    parser.add_argument("--report-date")
    parser.add_argument("--trading-date")
    parser.add_argument("--group", choices=["current", "previous"], default="current")
    parser.add_argument("--coverage-verified", action="store_true",
                        help="set only after confirming the saved HTML covers the full requested date range")
    parser.add_argument("--output")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    required = ("input_html", "report_date", "trading_date", "output")
    if any(not getattr(args, key) for key in required):
        parser.error("--input-html, --report-date, --trading-date and --output are required")
    payload = build_payload(args)
    Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    event_key = "previous_economic_events" if args.group == "previous" else "economic_events"
    coverage_key = "previous_economic_calendar" if args.group == "previous" else "economic_calendar"
    print(json.dumps({
        "group": args.group,
        "events": len(payload[event_key]),
        "coverage": payload["coverage"][coverage_key]["status"]
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
