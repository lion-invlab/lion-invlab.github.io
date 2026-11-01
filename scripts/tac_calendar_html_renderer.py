#!/usr/bin/env python3
"""Render TAC weekly calendar snapshots into approved Monday / weekday HTML masters.

Only the four calendar section bodies are replaced. The source master files are
read-only inputs and are never modified in place.
"""
from __future__ import annotations
import argparse
from datetime import date, datetime
from html import escape
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

TW = ZoneInfo("Asia/Taipei")
DOW = "一二三四五六日"


def esc(value):
    return escape(str(value if value not in (None, "") else "待核實"), quote=True)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def parse_event_dt(event):
    raw = event.get("event_date")
    if not raw:
        raise ValueError("event missing event_date: " + str(event.get("id")))
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        raise ValueError("event_date must include timezone: " + str(event.get("id")))
    return dt.astimezone(TW)


def date_label(dt):
    return f"{dt.month}/{dt.day}（{DOW[dt.weekday()]}）"


def week_bounds(snapshot):
    year, week = map(int, snapshot["meta"]["week_id"].split("-W"))
    monday = date.fromisocalendar(year, week, 1)
    return monday, monday + __import__("datetime").timedelta(days=4)


def range_label(snapshot):
    start, end = week_bounds(snapshot)
    return f"{start.month}/{start.day}～{end.month}/{end.day}"


def source_html(source):
    if not isinstance(source, dict):
        return "待核實"
    name = esc(source.get("name") or source.get("publisher") or "資料來源")
    url = source.get("url")
    if not url or not str(url).startswith(("https://", "http://")):
        return name
    return f'<a href="{esc(url)}" target="_blank" rel="noopener">{name}</a>'


def econ_card(event):
    dt = parse_event_dt(event)
    time = dt.strftime("%H:%M") if event.get("time_known", True) else "時間待核實"
    stars = int(event.get("importance_stars", 0))
    star_text = "★" * stars + "☆" * (5 - stars)
    cls = "five-star" if stars == 5 else "four-star"
    actual = event.get("actual")
    actual_text = actual if actual not in (None, "") else ("尚未公布" if event.get("status") != "released" else "待核實")
    previous = event.get("previous") if event.get("previous_applicable", True) else "不適用"
    forecast = event.get("forecast") if event.get("forecast_applicable", True) else "不適用"
    impact = event.get("impact_judgment") or "待補充市場影響判讀"
    return (
        f'<details class="econ-event {cls}"><summary><div class="econ-meta">'
        f'<span class="econ-date">{esc(date_label(dt))}</span>'
        f'<span class="econ-time">{esc(time)}</span>'
        f'<span class="econ-country">{esc(event.get("region"))}</span>'
        f'<div class="econ-name">{esc(event.get("event_name"))}</div>'
        f'<div class="econ-stars">{star_text}</div></div>'
        '<span aria-hidden="true" class="econ-toggle"></span></summary><div class="econ-details">'
        f'<div class="econ-field"><label>前值</label><div class="econ-value">{esc(previous)}</div></div>'
        f'<div class="econ-field"><label>市場預估</label><div class="econ-value">{esc(forecast)}</div></div>'
        f'<div class="econ-field"><label>實際</label><div class="econ-value">{esc(actual_text)}</div></div>'
        f'<div class="econ-field"><label>市場影響</label><div class="econ-value">{esc(impact)}</div></div>'
        f'<div class="econ-field wide"><label>資料來源</label><div class="econ-value">{source_html(event.get("source"))}</div></div>'
        '</div></details>'
    )


def earnings_card(event):
    dt = parse_event_dt(event)
    stars = int(event.get("importance_stars", 0))
    star_text = "★" * stars + "☆" * (5 - stars)
    session = {"before_market": "盤前", "after_market": "盤後", "during_market": "盤中"}.get(event.get("session"), "公布時段待核實")
    if not event.get("time_known", True):
        session = "公布時段待核實"
    tw_date = date_label(dt)
    name = esc(event.get("company"))
    ticker = esc(event.get("ticker"))
    industry = esc(event.get("industry") or "產業分類待核實")
    eps_actual = event.get("eps_actual")
    eps_est = event.get("eps_estimate")
    rev_actual = event.get("revenue_actual")
    rev_est = event.get("revenue_estimate")
    eps_status = event.get("eps_comparison_status")
    rev_status = event.get("revenue_comparison_status")

    def actual_card(label, actual, estimate, status, unit, basis=None):
        state = {"beat": "beat", "above": "beat", "miss": "miss", "below": "miss", "met": "met", "in_line": "met"}.get(status, "pending")
        state_text = {"beat": "高於預期", "miss": "低於預期", "met": "符合預期", "pending": "尚待核實"}[state]
        a = "尚未公布" if actual in (None, "") else f"{actual}{unit}"
        e = "待核實" if estimate in (None, "") else f"{estimate}{unit}"
        note = f'<div class="earnings-actual-note">{esc(basis)}</div>' if basis else ""
        return (f'<div class="earnings-actual-card {state}"><div class="earnings-actual-card-title">{label}</div>'
                f'<div class="earnings-actual-line"><span>實際</span><strong>{esc(a)}</strong></div>'
                f'<div class="earnings-actual-line"><span>預期</span><strong>{esc(e)}</strong></div>'
                f'<div class="earnings-actual-status {state}">{state_text}</div>{note}</div>')

    eps = actual_card("EPS", eps_actual, eps_est, eps_status, f" {event.get('eps_currency') or 'USD'}")
    revenue = actual_card("營收", rev_actual, rev_est, rev_status,
                          f" {event.get('revenue_currency') or 'USD'}{event.get('revenue_unit') or ''}")
    judgment = event.get("financial_judgment") or "待補充財報判讀；未核實前不作優劣結論。"
    reaction = event.get("stock_price_reaction") or "待核實；須以財報公布後首個正常交易日收盤表現為準。"
    return (
        f'<details class="earnings-accordion {"five-star-earnings" if stars == 5 else ""}">'
        '<summary class="earnings-accordion-summary"><div class="earnings-summary-main">'
        f'<div class="earnings-summary-dates"><span class="earnings-us-date">{esc(dt.strftime("%m/%d"))}（美股）</span>'
        f'<span class="earnings-tw-date">台灣時間 {esc(tw_date)}｜{session}</span></div>'
        f'<div class="earnings-company-name {"five-star-company" if stars == 5 else ""}">{name}</div>'
        f'<div class="earnings-company-sub">{ticker}｜{industry}</div><div class="earnings-stars">{star_text}</div>'
        '</div><span aria-hidden="true" class="earnings-accordion-toggle"></span></summary>'
        '<div class="earnings-accordion-details"><div class="earnings-results-grid">'
        f'{eps}{revenue}</div>'
        f'<div class="earnings-detail-field wide"><label>財報判讀</label><div class="earnings-detail-value">{esc(judgment)}</div></div>'
        f'<div class="earnings-detail-field wide"><label>股價當日表現</label><div class="earnings-detail-value">{esc(reaction)}</div></div>'
        f'<div class="earnings-detail-field wide"><label>資料來源</label><div class="earnings-detail-value">{source_html(event.get("source"))}；共識：{source_html(event.get("consensus_source"))}</div></div>'
        '</div></details>'
    )


def status_groups(events, report_date, kind):
    ordered = sorted(events, key=lambda e: parse_event_dt(e))
    groups = {"today": [], "upcoming": [], "published": []}
    for event in ordered:
        d = parse_event_dt(event).date()
        if event.get("status") == "released" or d < report_date:
            groups["published"].append(event)
        elif d == report_date:
            groups["today"].append(event)
        else:
            groups["upcoming"].append(event)
    labels = {"today": "今日公布", "upcoming": "即將公布", "published": "已公布"}
    item_class = "econ-event-list" if kind == "economic" else "earnings-accordion-list"
    renderer = econ_card if kind == "economic" else earnings_card
    result = []
    for key in ("today", "upcoming", "published"):
        rows = groups[key]
        title = labels[key] + ("｜重要性 4–5 星" if key != "published" else "｜已公布事件")
        content = "".join(renderer(row) for row in rows) or '<div class="calendar-status-empty">本分類目前沒有符合重要性 4–5 星且已核實的事件。</div>'
        result.append(f'<div class="calendar-status-group"><h4 class="calendar-status-heading {key}">{title}</h4><div class="{item_class}">{content}</div></div>')
    return "".join(result)


def archive_section(events, kind, start, end):
    title = "上週經濟行事曆" if kind == "economic" else "上週財報行事曆"
    collapse = "last-week-calendar-collapse" if kind == "economic" else "last-week-earnings-collapse"
    item_class = "econ-event-list" if kind == "economic" else "earnings-accordion-list"
    renderer = econ_card if kind == "economic" else earnings_card
    rows = sorted(events, key=lambda e: parse_event_dt(e))
    cards = "".join(renderer(e) for e in rows) or '<div class="calendar-status-empty">上週沒有符合規則的已公布五星事件。</div>'
    body = f'<div class="calendar-status-group"><h4 class="calendar-status-heading published">上週已公布｜五星事件，依日期排序</h4><div class="{item_class}">{cards}</div></div>'
    return (f'<article class="card calendar-card" style="grid-column:1 / -1"><div class="title" style="color:#b42332!important">'
            f'{title} <small>{start}～{end}｜台灣時間 UTC+8</small></div>'
            f'<details class="{collapse}"><summary>展開{title}（{start}～{end}）</summary>{body}</details></article>')


def find_section_bounds(html, section_id):
    match = re.search(r'<section\b[^>]*\bid=["\\']' + re.escape(section_id) + r'["\\'][^>]*>', html, re.I)
    if not match:
        raise ValueError("approved master missing section anchor: " + section_id)
    depth, pos = 1, match.end()
    token = re.compile(r'<section\b|</section\s*>', re.I)
    for m in token.finditer(html, pos):
        if m.group(0).lower().startswith("<section"):
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                return match.start(), m.end(), match.group(0)
    raise ValueError("unbalanced section: " + section_id)


def replace_section(html, section_id, inner):
    start, end, _ = find_section_bounds(html, section_id)
    opening_end = html.index(">", start) + 1
    closing_start = html.rfind("</section", opening_end, end)
    return html[:opening_end] + inner + html[closing_start:]


def render(template_path, snapshot_path, output_path, mode):
    template = Path(template_path).read_text(encoding="utf-8")
    snap = load(snapshot_path)
    meta = snap.get("meta", {})
    report_date = date.fromisoformat(meta["report_date"])
    start, end = range_label(snap).split("～")
    econ = status_groups(snap.get("economic_calendar", []), report_date, "economic")
    earnings = status_groups(snap.get("earnings_calendar", []), report_date, "earnings")
    template = replace_section(template, "calendar",
        f'<article class="card calendar-card" style="grid-column:1 / -1"><div class="title" style="color:#b42332!important">本週經濟行事曆 <small>{start}～{end}｜台灣時間 UTC+8</small></div>'
        '<div class="week-econ-tabs"><input checked id="week-econ-today" name="week-econ-tab" type="radio"/>'
        '<input id="week-econ-upcoming" name="week-econ-tab" type="radio"/><input id="week-econ-published" name="week-econ-tab" type="radio"/>'
        '<div class="week-econ-tab-labels"><label for="week-econ-today">今日公布</label><label for="week-econ-upcoming">即將公布</label><label for="week-econ-published">已公布</label></div>'
        f'<div class="week-econ-panels">{econ}</div></div></article>')
    template = replace_section(template, "earnings",
        f'<article class="card calendar-card" style="grid-column:1 / -1"><div class="title" style="color:#b42332!important">本週財報行事曆 <small>{start}～{end}｜台灣時間 UTC+8</small></div>'
        '<div class="week-earnings-tabs"><input checked id="week-earnings-today" name="week-earnings-tab" type="radio"/>'
        '<input id="week-earnings-upcoming" name="week-earnings-tab" type="radio"/><input id="week-earnings-published" name="week-earnings-tab" type="radio"/>'
        '<div class="week-earnings-tab-labels"><label for="week-earnings-today">今日公布</label><label for="week-earnings-upcoming">即將公布</label><label for="week-earnings-published">已公布</label></div>'
        f'<div class="week-earnings-panels">{earnings}</div></div></article>')
    if mode == "monday":
        for key, section_id, kind in (
            ("previous_economic_calendar", "last-week-calendar", "economic"),
            ("previous_earnings_calendar", "last-week-earnings", "earnings"),
        ):
            if key not in snap:
                raise ValueError("Monday snapshot missing " + key)
            current_start, _ = week_bounds(snap)
            previous_start = current_start - __import__("datetime").timedelta(days=7)
            previous_end = previous_start + __import__("datetime").timedelta(days=4)
            inner = archive_section(snap[key], kind, f"{previous_start.month}/{previous_start.day}", f"{previous_end.month}/{previous_end.day}")
            template = replace_section(template, section_id, inner)
    else:
        if 'id="last-week-calendar"' in template or 'id="last-week-earnings"' in template:
            raise ValueError("weekday master must not contain Monday-only archive anchors")
    if mode == "monday" and ('id="last-week-calendar"' not in template or 'id="last-week-earnings"' not in template):
        raise ValueError("Monday master archive anchors were lost")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(template, encoding="utf-8")
    print(json.dumps({"output": str(output), "mode": mode, "report_date": meta["report_date"],
        "sections_replaced": ["calendar", "earnings"] + (["last-week-calendar", "last-week-earnings"] if mode == "monday" else []),
        "event_counts": {"economic": len(snap.get("economic_calendar", [])), "earnings": len(snap.get("earnings_calendar", [])),
            "previous_economic": len(snap.get("previous_economic_calendar", [])), "previous_earnings": len(snap.get("previous_earnings_calendar", []))},
        "source_master_unchanged": True}, ensure_ascii=False, indent=2))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--template", required=True)
    p.add_argument("--snapshot", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--mode", choices=("monday", "weekday"), required=True)
    a = p.parse_args()
    render(a.template, a.snapshot, a.output, a.mode)


if __name__ == "__main__":
    main()
