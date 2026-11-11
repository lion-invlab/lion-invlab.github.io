#!/usr/bin/env python3
"""Decision-date historical availability reconstruction from existing ALFRED event chunks.
For decision date T, only observation_date <= T and vintage_date < T are eligible.
Same-day vintages are excluded because exact intraday release times are unavailable.
No interpolation, resampling, synthetic observations, or source mutation.
"""
import argparse, json, statistics
from bisect import bisect_left, bisect_right
from datetime import date, timedelta, datetime, timezone
from pathlib import Path
import analyze_tac_chart3_stress_episodes as base

SERIES = base.S
EPISODES = base.E

def build_index(data, series):
    obs = sorted(data[series])
    vals = {o: sorted(data[series][o].items()) for o in obs}
    dates = {o: [v for v, _ in vals[o]] for o in obs}
    return obs, vals, dates

def asof_latest(data, series, asof, index=None):
    """Latest numeric observation actually available strictly before decision date."""
    obs, vals, dates = index or build_index(data, series)
    i = bisect_right(obs, asof) - 1
    asof_date = date.fromisoformat(asof)
    while i >= 0:
        o = obs[i]
        j = bisect_left(dates[o], asof) - 1
        if j >= 0:
            vintage, raw = vals[o][j]
            value = base.num(raw)
            # If the latest vintage is '.', that observation is missing at this as-of date.
            if value is not None:
                return {"observation_date": o, "vintage_date": vintage, "value": value,
                        "age_days": (asof_date - date.fromisoformat(o)).days}
        i -= 1
    return None

def first_numeric_vintage(data, series, observation):
    vals = [(v, base.num(raw)) for v, raw in data[series][observation].items()]
    vals = [v for v, value in vals if value is not None]
    return min(vals) if vals else None

def snapshot_summary(data, series, start, end):
    idx = build_index(data, series)
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    snaps, day = [], first
    while day <= last:
        snap = asof_latest(data, series, day.isoformat(), idx)
        if snap:
            snaps.append({"as_of_date": day.isoformat(), **snap})
        day += timedelta(days=1)
    total = (last - first).days + 1
    ages = [x["age_days"] for x in snaps]
    return {
        "evaluation_days": total,
        "days_with_numeric_latest_known_observation": len(snaps),
        "share_of_days_with_numeric_latest_known_observation": len(snaps) / total,
        "first_as_of_date_with_data": snaps[0]["as_of_date"] if snaps else None,
        "last_as_of_date_with_data": snaps[-1]["as_of_date"] if snaps else None,
        "unique_observation_dates_seen": len({x["observation_date"] for x in snaps}),
        "median_observation_age_days": statistics.median(ages) if ages else None,
        "max_observation_age_days": max(ages) if ages else None,
        "snapshot_at_start": asof_latest(data, series, start, idx),
        "snapshot_at_end": asof_latest(data, series, end, idx),
        "interpretation": "Daily as-of queries; repeated snapshots are not new observations or a forward-filled source series."
    }

def release_summary(data, series, start, end):
    obs_dates = sorted(o for o in data[series] if start <= o <= end)
    records = []
    for o in obs_dates:
        first = first_numeric_vintage(data, series, o)
        lag = (date.fromisoformat(first) - date.fromisoformat(o)).days if first else None
        records.append({"observation_date": o, "first_numeric_vintage_date": first,
                        "release_lag_calendar_days": lag,
                        "available_before_episode_end": bool(first and first < end)})
    released = [x for x in records if x["first_numeric_vintage_date"]]
    lags = [x["release_lag_calendar_days"] for x in released]
    return {
        "event_observation_dates_in_archive": len(obs_dates),
        "event_observations_with_any_numeric_vintage": len(released),
        "event_observations_first_released_strictly_before_episode_end": sum(x["available_before_episode_end"] for x in records),
        "event_observations_first_released_during_episode": sum(bool(x["first_numeric_vintage_date"] and start <= x["first_numeric_vintage_date"] < end) for x in records),
        "first_numeric_release_date": min((x["first_numeric_vintage_date"] for x in released), default=None),
        "median_initial_release_lag_calendar_days": statistics.median(lags) if lags else None,
        "max_initial_release_lag_calendar_days": max(lags) if lags else None,
        "observation_release_records": records,
        "rule": "First vintage with numeric value; available by episode end only if vintage_date < episode_end."
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--artifact-dir", type=Path, required=True)
    p.add_argument("--output-json", type=Path, default=Path("tac_chart3_historical_asof.json"))
    args = p.parse_args()
    data, files = base.load(args.artifact_dir)
    out = {
        "project": "TAC Chart 3 historical as-of availability reconstruction",
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "as_of_rule": "Decision date T: observation_date <= T and vintage_date < T; same-day vintages excluded due unavailable intraday release clock.",
        "source": "Existing ALFRED output_type=3 chunks only; no new download.",
        "input_chunk_file_count": len(files), "input_chunk_files": files,
        "episodes": {},
        "limitations": [
            "Date-level, conservative reconstruction; not intraday release-time reconstruction.",
            "Observation date, vintage date and decision date are kept distinct; latest known value can be stale.",
            "Repeated daily snapshots are not additional source observations.",
            "No interpolation, resampling, imputation or forward-filled source series.",
            "NFCICREDIT is part of NFCI, not independent confirmation.",
            "No S&P 500 return data; no return backtest or predictive claim."
        ]
    }
    for episode, (start, end, _, _) in EPISODES.items():
        out["episodes"][episode] = {}
        for series in SERIES:
            out["episodes"][episode][series] = {
                "event_window": [start, end],
                "daily_asof_snapshot_summary": snapshot_summary(data, series, start, end),
                "event_observation_initial_release_summary": release_summary(data, series, start, end)
            }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({ep: {s: {
        "days_with_data": v["daily_asof_snapshot_summary"]["days_with_numeric_latest_known_observation"],
        "evaluation_days": v["daily_asof_snapshot_summary"]["evaluation_days"],
        "median_age_days": v["daily_asof_snapshot_summary"]["median_observation_age_days"],
        "event_observations": v["event_observation_initial_release_summary"]["event_observation_dates_in_archive"],
        "released_by_episode_end": v["event_observation_initial_release_summary"]["event_observations_first_released_strictly_before_episode_end"],
        "median_release_lag_days": v["event_observation_initial_release_summary"]["median_initial_release_lag_calendar_days"],
        "first_release": v["event_observation_initial_release_summary"]["first_numeric_release_date"]
    } for s, v in ss.items()} for ep, ss in out["episodes"].items()}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
