#!/usr/bin/env python3
"""Capture Investing.com 3-star economic calendar events in Taiwan time.

The source request is made against Investing.com's calendar service. The parser
keeps only source-native 3-star events and retains the original row ID and
capture provenance. This is a source adapter, not an editorial impact analysis.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

API_URLS = ("https://hk.investing.com/economic-calendar/Service/getCalendarFilteredData", "https://www.investing.com/economic-calendar/Service/getCalendarFilteredData")
JSON_API_URL = "https://it.investing.com/economic-calendar/getCalendarFilteredData"
SOURCE_URL = "https://hk.investing.com/economic-calendar/"
SOURCE_NAME = "Investing.com 香港站"
TAIPEI = ZoneInfo("Asia/Taipei")
# Investing.com legacy calendar timezone code for GMT. Returned event times
# are interpreted as UTC and converted explicitly to Asia/Taipei below.
GMT_TIMEZONE_ID = 56


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


def day_from_header(row) -> date | None:
    cell = row.find(id=re.compile(r"^theDay\d+$"))
    if cell is None:
        return None
    stamp = int(re.sub(r"\D", "", cell.get("id", "")))
    return datetime.fromtimestamp(stamp, tz=timezone.utc).date()


def parse_calendar_html(html: str, observed_at: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("tr")
    current_day: date | None = None
    result: list[dict] = []
    for row in rows:
        row_id = row.get("id") or ""
        if not row_id.startswith("eventRowId_"):
            header_day = day_from_header(row)
            if header_day is not None:
                current_day = header_day
            continue
        if current_day is None:
            raise ValueError("calendar event row appeared before its date header")
        event_id = row_id.removeprefix("eventRowId_")
        tds = row.find_all("td", recursive=False)
        time_cell = row.select_one("td.first.left")
        currency_cell = row.select_one("td.flagCur")
        importance_cell = row.select_one("td.sentiment")
        event_cell = row.select_one("td.left.event")
        if not all((time_cell, currency_cell, importance_cell, event_cell)):
            raise ValueError(f"event {event_id}: required source columns are missing")
        star_raw = importance_cell.get("data-img_key") or ""
        star_match = re.search(r"bull(\d)", star_raw)
        if not star_match:
            continue
        stars = int(star_match.group(1))
        if stars != 3:
            continue
        event_time = parse_event_time(time_cell.get_text(" ", strip=True))
        if event_time is None:
            # All-day events retain the calendar date and are anchored at Taiwan midnight.
            taipei_dt = datetime.combine(current_day, time.min, tzinfo=TAIPEI)
        else:
            source_dt = datetime.combine(current_day, event_time, tzinfo=timezone.utc)
            taipei_dt = source_dt.astimezone(TAIPEI)
        currency = clean(currency_cell.get_text(" ", strip=True))
        region = clean(currency_cell.find("span").get("title") if currency_cell.find("span") else None) or currency or "Global"
        actual = clean((row.select_one(f"#eventActual_{event_id}") or row).get_text(" ", strip=True) if row.select_one(f"#eventActual_{event_id}") else None)
        forecast = clean((row.select_one(f"#eventForecast_{event_id}") or row).get_text(" ", strip=True) if row.select_one(f"#eventForecast_{event_id}") else None)
        previous = clean((row.select_one(f"#eventPrevious_{event_id}") or row).get_text(" ", strip=True) if row.select_one(f"#eventPrevious_{event_id}") else None)
        captured = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
        status = "released" if actual is not None else ("upcoming" if taipei_dt > captured else "pending_verification")
        result.append({
            "id": str(event_id),
            "event_date": taipei_dt.isoformat(),
            "region": region,
            "event_name": clean(event_cell.get_text(" ", strip=True)) or "Unnamed event",
            "importance_stars": 3,
            "previous": previous,
            "forecast": forecast,
            "actual": actual,
            "status": status,
            "impact_judgment": None,
            "source": {
                "name": SOURCE_NAME,
                "url": SOURCE_URL,
                "published_at": None,
                "observed_at": observed_at,
                "publisher": SOURCE_NAME,
                "notes": "Investing.com 原生 3 星事件；來源時間先按 GMT 解析，再換算 Asia/Taipei。"
            }
        })
    result.sort(key=lambda item: item["event_date"])
    return result


def parse_json_calendar_rows(rows: list[dict], observed_at: str) -> list[dict]:
    """Parse the current Investing.com JSON calendar response only when its native impact field is explicit."""
    import hashlib

    result = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Investing.com JSON calendar row must be an object")
        star_raw = next((row.get(key) for key in
                         ("importance", "importance_stars", "importance_id", "impact", "importance_level")
                         if row.get(key) is not None), None)
        if isinstance(star_raw, dict):
            star_raw = next((star_raw.get(k) for k in ("value", "level", "id", "name") if star_raw.get(k) is not None), None)
        star_text = str(star_raw).strip().lower() if star_raw is not None else ""
        if star_text in {"3", "bull3", "high", "high impact"}:
            stars = 3
        elif star_text in {"1", "2", "bull1", "bull2", "low", "medium", "low impact", "medium impact"}:
            continue
        else:
            raise ValueError("Investing.com JSON row lacks a recognized native importance value; keys=" + ",".join(row.keys()))

        raw_date = row.get("event_date_utc") or row.get("event_date")
        if raw_date is None:
            raise ValueError("Investing.com JSON row lacks event_date_utc/event_date")
        if isinstance(raw_date, (int, float)):
            stamp = float(raw_date)
            if stamp > 10_000_000_000:
                stamp /= 1000
            event_dt = datetime.fromtimestamp(stamp, tz=timezone.utc)
        else:
            parsed = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
            event_dt = parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
        taipei_dt = event_dt.astimezone(TAIPEI)

        event_name = clean(row.get("event") or row.get("event_name") or row.get("name"))
        if not event_name:
            raise ValueError("Investing.com JSON row lacks event name")
        currency = clean(row.get("currency") or row.get("country_code")) or "Global"
        region = clean(row.get("country") or row.get("region")) or currency
        event_id = clean(str(row.get("id") or row.get("event_id") or "")) or hashlib.sha1(
            f"{taipei_dt.isoformat()}|{currency}|{event_name}".encode("utf-8")
        ).hexdigest()[:16]
        actual = clean(str(row.get("actual"))) if row.get("actual") is not None else None
        forecast = clean(str(row.get("forecast"))) if row.get("forecast") is not None else None
        previous = clean(str(row.get("previous"))) if row.get("previous") is not None else None
        captured = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
        status = "released" if actual is not None else ("upcoming" if taipei_dt > captured else "pending_verification")
        result.append({
            "id": event_id, "event_date": taipei_dt.isoformat(), "region": region,
            "event_name": event_name, "importance_stars": stars,
            "previous": previous, "forecast": forecast, "actual": actual,
            "status": status, "impact_judgment": None,
            "source": {
                "name": SOURCE_NAME, "url": SOURCE_URL, "published_at": None,
                "observed_at": observed_at, "publisher": SOURCE_NAME,
                "notes": "Investing.com 原生 JSON 日曆資料；保留來源明示 3 星評級，事件時間依 event_date_utc 換算 Asia/Taipei。"
            }
        })
    result.sort(key=lambda item: item["event_date"])
    return result


def fetch_json_calendar_events(start: date, end: date, client: requests.Session,
                               observed_at: str, user_agent: str) -> list[dict]:
    start_utc = datetime.combine(start, time.min, tzinfo=timezone.utc)
    end_utc = datetime.combine(end, time.max, tzinfo=timezone.utc)
    payload = {
        "dateFrom": int(start_utc.timestamp()),
        "dateTo": int(end_utc.timestamp()),
        "timeZone": 8,
        "eventsType": "custom",
        "customEvents": "1762"
    }
    headers = {
        "User-Agent": user_agent,
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://it.investing.com",
        "Referer": "https://it.investing.com/economic-calendar/"
    }
    response = client.post(JSON_API_URL, json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    body = response.json()
    rows = body.get("data") if isinstance(body, dict) else None
    if not isinstance(rows, list):
        raise ValueError("Investing.com JSON calendar response data is not an array")
    if not rows:
        raise ValueError("Investing.com JSON calendar returned no rows for requested date range")
    return parse_json_calendar_rows(rows, observed_at)


def fetch_events(start: date, end: date, session: requests.Session | None = None) -> tuple[list[dict], str]:
    if end < start:
        raise ValueError("end date must be on or after start date")
    if (end - start).days > 30:
        raise ValueError("calendar capture range cannot exceed 31 calendar days")
    client = session or requests.Session()
    observed_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "dateFrom": start.isoformat(), "dateTo": end.isoformat(),
        "timeZone": GMT_TIMEZONE_ID, "timeFilter": "time_only",
        "currentTab": "custom", "submitFilters": 1, "limit_from": 0
    }
    user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36"
    all_events: dict[str, dict] = {}
    for page in range(20):
        body = None
        last_error = None
        for api_url in API_URLS:
            host = api_url.split("/economic-calendar/", 1)[0]
            headers = {
                "User-Agent": user_agent, "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
                "Origin": host, "Referer": host + "/economic-calendar/"
            }
            try:
                # Establish a normal same-site session before calling the calendar service.
                client.get(host + "/economic-calendar/", headers={"User-Agent": user_agent}, timeout=20)
                response = client.post(api_url, data=payload, headers=headers, timeout=30)
                response.raise_for_status()
                candidate = response.json()
                html = candidate.get("data") if isinstance(candidate, dict) else None
                if not isinstance(html, str):
                    raise ValueError("Investing.com calendar response did not contain HTML data")
                body = candidate
                break
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
        if body is None:
            try:
                json_events = fetch_json_calendar_events(start, end, client, observed_at, user_agent)
                return json_events, observed_at
            except (requests.RequestException, ValueError) as json_error:
                raise RuntimeError(
                    "Investing.com calendar unavailable on HK/global HTML endpoints and JSON fallback: "
                    + str(last_error) + "; JSON fallback: " + str(json_error)
                )
        page_events = parse_calendar_html(body["data"], observed_at)
        before = len(all_events)
        for item in page_events:
            all_events[item["id"]] = item
        if len(all_events) == before:
            break
        payload["limit_from"] += 1
    else:
        raise ValueError("Investing.com calendar pagination exceeded safety limit")
    return sorted(all_events.values(), key=lambda item: item["event_date"]), observed_at

def build_payload(args) -> dict:
    start = date.fromisoformat(args.start_date)
    end = date.fromisoformat(args.end_date)
    events, observed_at = fetch_events(start, end)
    group = args.group
    if group == "previous":
        event_key, coverage_key = "previous_economic_events", "previous_economic_calendar"
    else:
        event_key, coverage_key = "economic_events", "economic_calendar"
    return {
        "report_date": args.report_date,
        "trading_date": args.trading_date,
        "observed_at": observed_at,
        "source": {"name": SOURCE_NAME, "url": SOURCE_URL, "publisher": SOURCE_NAME},
        event_key: events,
        "coverage": {
            coverage_key: {
                "status": "complete",
                "source_refs": [SOURCE_URL],
                "checked_at": observed_at
            }
        }
    }


def self_test() -> None:
    observed = "2026-10-31T12:00:00+00:00"
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
    events = parse_calendar_html(fixture, observed)
    assert len(events) == 2
    by_id = {event["id"]: event for event in events}
    assert by_id["123"]["importance_stars"] == 3
    assert by_id["123"]["event_name"] == "Nonfarm Payrolls"
    assert by_id["123"]["actual"] == "200K"
    assert by_id["123"]["event_date"].endswith("+08:00")
    assert by_id["125"]["event_name"] == "Three star all-day event"
    assert by_id["125"]["event_date"].endswith("T00:00:00+08:00")
    assert by_id["125"]["status"] == "pending_verification"
    print("PASS: source-native 3-star filtering, GMT-to-Taipei conversion and actual-value parsing")
    json_events = parse_json_calendar_rows([
        {"id": "json-3", "event_date_utc": int(datetime(2026, 11, 2, 13, 30, tzinfo=timezone.utc).timestamp()),
         "currency": "USD", "country": "United States", "event": "ISM Manufacturing PMI",
         "importance": 3, "actual": None, "forecast": "51.0", "previous": "50.8"},
        {"id": "json-2", "event_date_utc": int(datetime(2026, 11, 2, 14, 0, tzinfo=timezone.utc).timestamp()),
         "currency": "USD", "country": "United States", "event": "Medium event",
         "importance": 2, "actual": None, "forecast": None, "previous": None}
    ], observed)
    assert len(json_events) == 1 and json_events[0]["importance_stars"] == 3
    assert json_events[0]["event_date"].endswith("+08:00")
    print("PASS: JSON fallback preserves native 3-star ratings and converts UTC to Taipei")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--report-date")
    parser.add_argument("--trading-date")
    parser.add_argument("--group", choices=["current", "previous"], default="current")
    parser.add_argument("--output")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    required = ("start_date", "end_date", "report_date", "trading_date", "output")
    if any(not getattr(args, key) for key in required):
        parser.error("--start-date, --end-date, --report-date, --trading-date and --output are required")
    payload = build_payload(args)
    Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"group": args.group, "events": len(payload.get("economic_events", payload.get("previous_economic_events", []))), "coverage": payload["coverage"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
