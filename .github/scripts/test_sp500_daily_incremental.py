#!/usr/bin/env python3
"""Offline invariants for TAC S&P 500 incremental compact updater."""
import datetime as dt, importlib.util, tempfile, json
from pathlib import Path
spec=importlib.util.spec_from_file_location("sp500_updater", ".github/scripts/update_sp500_daily_incremental.py")
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
start=dt.date(1993,12,31)
rows={(start+dt.timedelta(days=i)).isoformat():45927+i for i in range(m.MIN_BOOTSTRAP_ROWS)}
obj=m.encode_compact(rows,{"test":True})
with tempfile.TemporaryDirectory() as td:
 p=Path(td)/"sample.json"; p.write_text(json.dumps(obj))
 assert m.decode_compact(p)==rows
day=dt.datetime(2026,11,12,9,30,tzinfo=m.ET)
raw={"result":{"meta":{"symbol":"^GSPC"},"timestamp":[int(day.timestamp())],"indicators":{"quote":[{"close":[6832.15]}]}}}
parsed=m.parse_chart(raw)
assert parsed=={"2026-11-12":683215}
try:
 m.parse_chart({"result":{"meta":{"symbol":"^SPY"},"timestamp":[],"indicators":{"quote":[{"close":[]}]}}})
 raise AssertionError("wrong instrument accepted")
except RuntimeError:
 pass
print("S&P500 updater offline tests: PASS")
