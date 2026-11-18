#!/usr/bin/env python3
import hashlib, json, tempfile, unittest
from pathlib import Path
from build_sp500_from_tac_report_history import convert, canonical

def record(day, close, source):
    item={
        "schema_version":"1.0","series_id":"SP500","instrument":"S&P 500 cash price index",
        "report_date":"2026-11-18","observation_date":day,
        "open":close-5,"high":close+5,"low":close-10,"close":close,
        "source_name":source,
        "source_url":"https://finance.yahoo.com/quote/%5ESPX/history/" if source.startswith("Yahoo") else "https://www.investing.com/indices/us-spx-500-historical-data",
        "source_note":"S&P 500 現金指數，non-CFD",
        "retrieved_at":"2026-11-18T05:00:00+08:00",
        "retrieval_method":"reused_from_tac_daily_report_verified_ohlc"
    }
    item["record_sha256"]=hashlib.sha256(canonical(item)).hexdigest()
    return item

class BuildSp500HistoryTests(unittest.TestCase):
    def test_compacts_history_and_preserves_mixed_daily_sources(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); src=root/"daily.jsonl"; compact=root/"compact.json"; prov=root/"prov.json"
            rows=[
                record("2026-11-16",7416.59,"Yahoo Finance ^SPX cash index"),
                record("2026-11-17",7340.53,"Investing.com S&P 500 cash index")
            ]
            src.write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in rows)+"\n",encoding="utf-8")
            result=convert(src,compact,prov)
            c=json.loads(compact.read_text()); p=json.loads(prov.read_text())
            self.assertEqual(result["rows"],2)
            self.assertEqual(c["rows"],2)
            self.assertEqual(len(p["observations"]),2)
            self.assertEqual(p["observations"][0]["source_name"],"Yahoo Finance ^SPX cash index")
            self.assertEqual(p["observations"][1]["source_name"],"Investing.com S&P 500 cash index")
            self.assertEqual(c["source_dataset_sha256"],p["source_sha256"])

    def test_rejects_tampered_record_hash(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); src=root/"daily.jsonl"
            item=record("2026-11-16",7416.59,"Yahoo Finance ^SPX cash index")
            item["close"]=7000
            src.write_text(json.dumps(item,ensure_ascii=False)+"\n",encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"record_sha256 mismatch"):
                convert(src,root/"compact.json",root/"prov.json")

    def test_rejects_cfd(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); src=root/"daily.jsonl"
            item=record("2026-11-16",7416.59,"Yahoo Finance ^SPX cash index")
            item["source_note"]="S&P 500 cash index CFD"
            body={k:v for k,v in item.items() if k!="record_sha256"}
            item["record_sha256"]=hashlib.sha256(canonical(body)).hexdigest()
            src.write_text(json.dumps(item,ensure_ascii=False)+"\n",encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"CFD"):
                convert(src,root/"compact.json",root/"prov.json")

if __name__=="__main__":
    unittest.main()
