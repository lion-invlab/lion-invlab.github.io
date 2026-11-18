#!/usr/bin/env python3
import json, tempfile, unittest
from pathlib import Path
from prepare_sp500_research_import import convert
from build_tac_chart3_synchronized_release import decode_sp500

URL = "https://www.investing.com/indices/us-spx-500-historical-data"
STAMP = "2026-11-18T12:00:00+00:00"

class ImportTests(unittest.TestCase):
    def test_converts_investing_csv_and_round_trips(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "sp500.csv"
            source.write_text("Date,Price,Open\nNov 17, 2026,\"6,800.25\",\"6,790.00\"\nNov 16, 2026,\"6,750.50\",\"6,740.00\"\n", encoding="utf-8")
            compact = root / "compact.json"
            provenance = root / "provenance.json"
            result = convert(source, compact, provenance, URL, STAMP)
            self.assertEqual(result["rows"], 2)
            self.assertEqual(result["start"], "2026-11-16")
            self.assertEqual(result["end"], "2026-11-17")
            decoded = decode_sp500(json.loads(compact.read_text()))
            self.assertEqual([x["value"] for x in decoded], [6750.5, 6800.25])
            p = json.loads(provenance.read_text())
            self.assertEqual(p["source_sha256"], json.loads(compact.read_text())["source_dataset_sha256"])
            self.assertEqual(p["method"], "manual_csv_export_import")

    def test_rejects_non_investing_source(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); source = root / "sp500.csv"
            source.write_text("Date,Price\n\\"Nov 17, 2026\\",6800\n")
            with self.assertRaisesRegex(ValueError, "Investing.com"):
                convert(source, root/"c.json", root/"p.json", "https://example.com/data.csv", STAMP)

    def test_rejects_duplicate_dates(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); source = root / "sp500.csv"
            source.write_text("Date,Price\n\\"Nov 17, 2026\\",6800\n\\"Nov 17, 2026\\",6801\n")
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                convert(source, root/"c.json", root/"p.json", URL, STAMP)

if __name__ == "__main__":
    unittest.main()
