#!/usr/bin/env python3
"""Offline invariants for TAC S&P 500 Investing.com incremental updater."""
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
# Investing.com dictionary response, ISO dates and decimal close.
parsed=m.parse_chart({"payload":{"data":[{"date":"2026-11-12","close":"6,832.15"}]}})
assert parsed=={"2026-11-12":683215}
# Investing.com legacy table-style array response.
parsed=m.parse_chart({"payload":[["2026-11-12",6800,6840,6790,6832.15,0]]})
assert parsed=={"2026-11-12":683215}
# Locale-formatted date.
parsed=m.parse_chart({"payload":{"historical":[{"date":"12/11/2026","close":"6,832.15"}]}})
assert parsed=={"2026-11-12":683215}
# Reject unknown response shape and conflicting duplicate dates.
for payload in ({"payload":{"unexpected":[]}}, {"payload":{"data":[{"date":"2026-11-12","close":"6832"},{"date":"2026-11-12","close":"6833"}]}}):
 try:
  m.parse_chart(payload)
  raise AssertionError("invalid Investing.com payload accepted")
 except RuntimeError:
  pass
print("S&P500 Investing.com updater offline tests: PASS")
