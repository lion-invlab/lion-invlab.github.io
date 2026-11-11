#!/usr/bin/env python3
"""TAC Chart 3 FRED/ALFRED archive downloader. Never prints the API key."""
import csv, hashlib, json, os, sys, time, urllib.parse, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime, timezone

BASE = "https://api.stlouisfed.org/fred"
SERIES = {
    "VIXCLS": "1990-01-01",
    "NFCI": "1971-01-01",
    "NFCICREDIT": "1971-01-01",
    "STLFSI4": "1993-12-01",
}

def request_json(endpoint, params, key, retries=3):
    q = dict(params, api_key=key, file_type="json")
    url = BASE + "/" + endpoint + "?" + urllib.parse.urlencode(q)
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent":"TAC-Decision-Charts/1.0"})
            with urllib.request.urlopen(req, timeout=90) as r:
                data = json.loads(r.read().decode("utf-8"))
            if "error_code" in data:
                raise RuntimeError(str(data))
            return data, url.split("?")[0]
        except urllib.error.HTTPError as e:
            # Preserve the provider response body for diagnosis; never print request URLs or API keys.
            try:
                body = e.read().decode("utf-8", errors="replace")[:2000]
            except Exception:
                body = ""
            last = RuntimeError(f"HTTP {e.code}: {body or e.reason}")
            if attempt + 1 < retries:
                time.sleep(2 ** attempt)
        except Exception as e:
            last = e
            if attempt + 1 < retries:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"{endpoint} request failed: {last}")

def write_json(path, obj):
    raw = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest(), len(raw)

def write_csv(path, rows, sid, retrieved, source_url, label):
    fields = ["series_id","observation_date","value","realtime_start","realtime_end",
              "retrieved_at","source_url","source_method","license_status","quality_flags"]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for row in rows:
            d = row.get("date", "")
            value = row.get("value", "")
            flags = []
            if not d: flags.append("missing_observation_date")
            if value in ("", ".", None): flags.append("source_missing_value")
            if not row.get("realtime_start"): flags.append("release_vintage_not_per_observation")
            w.writerow({"series_id":sid,"observation_date":d,"value":value,
                        "realtime_start":row.get("realtime_start",""),
                        "realtime_end":row.get("realtime_end",""),
                        "retrieved_at":retrieved,"source_url":source_url,
                        "source_method":label,
                        "license_status":"review_required_before_redistribution",
                        "quality_flags":";".join(flags)})
    return hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size

def main():
    key = os.environ.get("FRED_API_KEY", "").strip()
    if len(key) != 32 or not key.isalnum() or key.lower() != key:
        raise SystemExit("FRED_API_KEY missing or malformed; expected 32 lowercase alphanumeric characters.")
    root = Path("artifacts/tac-chart3")
    root.mkdir(parents=True, exist_ok=True)
    retrieved = datetime.now(timezone.utc).isoformat(timespec="seconds")
    manifest = {"project":"TAC Chart 3","retrieved_at":retrieved,
                "api":"FRED/ALFRED official API","series":{},"failures":[]}
    for sid, start in SERIES.items():
        print(f"START {sid}", flush=True)
        sd = root / sid; sd.mkdir(exist_ok=True)
        entry = {"observation_start":start,"status":"RUNNING","files":[]}
        try:
            # FRED observations defaults realtime_start/end to TODAY. If no release
            # exists on that calendar date, the API returns HTTP 400. Resolve the
            # latest actual vintage first, then query the current snapshot as-of it.
            # Page the complete vintage-date index rather than assuming one page is enough.
            dates = []
            vintage_pages = []
            offset = 0
            while True:
                page, vurl = request_json("series/vintagedates",
                    {"series_id":sid,"sort_order":"asc","limit":10000,"offset":offset}, key)
                page_dates = page.get("vintage_dates", [])
                vintage_pages.append(page)
                dates.extend(page_dates)
                print(f"  {sid} vintage-date index offset={offset}: {len(page_dates)} dates", flush=True)
                if len(page_dates) < 10000:
                    break
                offset += len(page_dates)
            vintages = {"series_id":sid,"vintage_dates":dates,"page_count":len(vintage_pages),
                        "count":len(dates),"source_endpoint":vurl}
            vh,vb = write_json(sd/f"{sid}_vintage_dates.json", vintages)
            entry["files"].append({"name":f"{sid}_vintage_dates.json","sha256":vh,"bytes":vb})
            if not dates: raise RuntimeError("vintage_dates empty")
            latest_vintage = dates[-1]
            entry["latest_vintage_date"] = latest_vintage
            entry["vintage_date_count"] = len(dates)
            current, url = request_json("series/observations",
                {"series_id":sid,"observation_start":start,"observation_end":datetime.now(timezone.utc).date().isoformat(),
                 "realtime_start":latest_vintage,"realtime_end":latest_vintage,"output_type":1,"sort_order":"asc","limit":100000,"offset":0}, key)
            h,n = write_json(sd/f"{sid}_current_output_type1.json", current)
            entry["files"].append({"name":f"{sid}_current_output_type1.json","sha256":h,"bytes":n})
            rows = current.get("observations",[])
            ch,cn = write_csv(sd/f"{sid}_current.csv", rows, sid, retrieved, url, "FRED API output_type=1 current vintage")
            entry["files"].append({"name":f"{sid}_current.csv","sha256":ch,"bytes":cn})
            entry["current_observations"] = len(rows)
            if not rows: raise RuntimeError("current observations empty")

            initial, iurl = request_json("series/observations",
                {"series_id":sid,"observation_start":start,"observation_end":datetime.now(timezone.utc).date().isoformat(),
                 "realtime_start":latest_vintage,"realtime_end":latest_vintage,"output_type":4,"sort_order":"asc","limit":100000,"offset":0}, key)
            ih,ib = write_json(sd/f"{sid}_initial_release_output_type4.json", initial)
            entry["files"].append({"name":f"{sid}_initial_release_output_type4.json","sha256":ih,"bytes":ib})
            ir = initial.get("observations",[])
            ich,icn = write_csv(sd/f"{sid}_initial_release.csv", ir, sid, retrieved, iurl, "FRED API output_type=4 initial release")
            entry["files"].append({"name":f"{sid}_initial_release.csv","sha256":ich,"bytes":icn})
            entry["initial_release_observations"] = len(ir)

            change_rows = 0
            # API JSON output_type 3 permits up to 2,000 vintage dates per request.
            batch_size = 500
            total_batches = (len(dates) + batch_size - 1) // batch_size
            for ix in range(0, len(dates), batch_size):
                batch = dates[ix:ix+batch_size]
                batch_no = ix//batch_size + 1
                print(f"  START {sid} vintage batch {batch_no}/{total_batches}: {len(batch)} dates", flush=True)
                batch_started = time.monotonic()
                payload, purl = request_json("series/observations",
                    {"series_id":sid,"observation_start":start,
                     "observation_end":datetime.now(timezone.utc).date().isoformat(),
                     "output_type":3,"vintage_dates":",".join(batch),
                     "sort_order":"asc","limit":100000,"offset":0}, key)
                name = f"{sid}_vintage_changes_{ix//500+1:03d}.json"
                ph,pb = write_json(sd/name, payload)
                entry["files"].append({"name":name,"sha256":ph,"bytes":pb})
                count = len(payload.get("observations",[]))
                change_rows += count
                print(f"  DONE {sid} vintage batch {batch_no}/{total_batches}: {len(batch)} dates, {count} change rows, {time.monotonic()-batch_started:.1f}s", flush=True)
            entry["vintage_change_rows"] = change_rows
            entry["status"] = "PASS"
            print(f"PASS {sid}: current={len(rows)}, initial={len(ir)}, vintages={len(dates)}, changes={change_rows}", flush=True)
        except Exception as e:
            entry["status"] = "FAIL"
            entry["error"] = str(e)
            manifest["failures"].append({"series_id":sid,"error":str(e)})
            print(f"FAIL {sid}: {e}", file=sys.stderr, flush=True)
        manifest["series"][sid] = entry
    manifest["overall_status"] = "PASS" if all(x["status"]=="PASS" for x in manifest["series"].values()) else "PARTIAL_OR_FAIL"
    mh,mn = write_json(root/"manifest.json", manifest)
    print(f"MANIFEST sha256={mh} bytes={mn}")
    print(f"OVERALL_STATUS={manifest['overall_status']}")
    if manifest["failures"]:
        raise SystemExit(2)

if __name__ == "__main__":
    main()
