#!/usr/bin/env python3
import json, tempfile, unittest, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/".github"/"scripts"))
from handoff_sp500_to_chart3 import build_payload
from append_tac_sp500_daily_increment import append_handoff
FIXTURE=ROOT/"simulation-lab/fixtures/report-data-2026-11-23.json"
class HandoffTests(unittest.TestCase):
 def setUp(self): self.data=json.loads(FIXTURE.read_text(encoding="utf-8"))
 def test_fixture_conversion(self):
  p=build_payload(self.data); s=p["sp500"]["source"]
  self.assertEqual((p["report_date"],p["trading_date"],p["sp500"]["value"]),("2026-11-23","2026-11-20",6910.39))
  self.assertEqual(s["quote_type"],"cash_index_close")
  self.assertEqual(s["observed_at"],"2026-11-22T17:15:52+08:00")
  self.assertIn("investing.com",s["url"])
 def test_append_is_idempotent(self):
  p=build_payload(self.data)
  with tempfile.TemporaryDirectory() as td:
   ledger=Path(td)/"sp500.jsonl"
   a=append_handoff(p,ledger); b=append_handoff(p,ledger)
   rows=[json.loads(x) for x in ledger.read_text().splitlines()]
   self.assertEqual((a["status"],b["status"],len(rows)),("APPENDED","NOOP_IDENTICAL_OBSERVATION",1))
   self.assertEqual(rows[0]["observation_date"],"2026-11-20")
   self.assertEqual(rows[0]["close"],6910.39)
   self.assertEqual(rows[0]["source_name"],"Investing.com｜S&P 500 歷史數據（Real-time derived）")
 def test_rejects_cfd_date_value_and_missing_timestamp(self):
  self.data["global_markets"]["標普500指數"]["source"]["quote_type"]="cfd_close"
  with self.assertRaisesRegex(ValueError,"cash_index_close"): build_payload(self.data)
  self.setUp(); self.data["global_markets"]["標普500指數"]["source"]["data_date"]="2026-11-19"
  with self.assertRaisesRegex(ValueError,"trading_date"): build_payload(self.data)
  self.setUp(); self.data["global_markets"]["標普500指數"]["source"]["close_value"]="6,900.00"
  with self.assertRaisesRegex(ValueError,"does not match"): build_payload(self.data)
  self.setUp(); self.data["global_markets"]["標普500指數"]["source"]["checked_at_tw"]=None
  with self.assertRaisesRegex(ValueError,"checked_at_tw"): build_payload(self.data)
 def test_rejects_unverified_source(self):
  self.data["global_markets"]["標普500指數"]["source"]["verification_status"]="PENDING"
  with self.assertRaisesRegex(ValueError,"VERIFIED"): build_payload(self.data)
if __name__=="__main__": unittest.main()
