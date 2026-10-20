#!/usr/bin/env python3
"""Fetch and validate CNN Fear & Greed data before updating the preview JSON."""
import json
import os
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
OUT = Path("preview/cnn-fear-greed.json")
headers = {
    "User-Agent": os.getenv("CNN_FETCH_USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.cnn.com",
    "Referer": "https://www.cnn.com/",
}
req = Request(URL, headers=headers)
with urlopen(req, timeout=25) as response:
    if response.status != 200:
        raise RuntimeError(f"CNN returned HTTP {response.status}")
    payload = json.loads(response.read().decode("utf-8"))

headline = payload.get("fear_and_greed")
if not isinstance(headline, dict):
    raise RuntimeError("Missing fear_and_greed object")
score = headline.get("score")
rating = headline.get("rating")
timestamp = headline.get("timestamp")
if not isinstance(score, (int, float)) or not 0 <= float(score) <= 100:
    raise RuntimeError(f"Invalid score: {score!r}")
if not isinstance(rating, str) or not rating.strip():
    raise RuntimeError(f"Invalid rating: {rating!r}")
if not isinstance(timestamp, str) or not timestamp.strip():
    raise RuntimeError(f"Invalid timestamp: {timestamp!r}")
# Validate timestamp before touching the prior data file.
datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

result = {
    "source": "CNN Fear & Greed Index",
    "source_url": URL,
    "score": round(float(score), 2),
    "rating": rating.lower().strip(),
    "timestamp": timestamp,
    "fetched_at_utc": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
}
OUT.parent.mkdir(parents=True, exist_ok=True)
tmp = OUT.with_suffix(".json.tmp")
tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
tmp.replace(OUT)
print(json.dumps(result, ensure_ascii=False))
