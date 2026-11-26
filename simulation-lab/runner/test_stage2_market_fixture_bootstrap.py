#!/usr/bin/env python3
import copy
import unittest
from stage2_market_fixture_bootstrap import blank_fixture, populate_fixture

def fixture():
    data={"report_date":"2026-11-26","trading_date":"2026-11-25","timezone":"Asia/Taipei"}
    groups={"global_markets":17,"bonds":3,"fx":6,"energy":2,"metals":2,"risk":3}
    for group,count in groups.items():
        data[group]={}
        for i in range(count):
            name=("fear_greed" if group=="risk" and i==2 else f"{group}_{i}")
            data[group][name]={"display":"1,234.50" if group!="bonds" else "4.652%",
                "change_display":"-0.25%" if group!="bonds" else "-1.9 bp",
                "source":{"name":name,"url":f"https://example.com/{group}/{i}","data_date":"2026-11-25",
                    "quote_type":"treasury_yield" if group=="bonds" else "spot_daily_close",
                    "note":"test source","close_value":1234.5,"daily_change_percent":-0.25,
                    "history_close":1234.5,"history_change":-0.25,
                    "score_value":15 if name=="fear_greed" else None,"band":"極度恐懼" if name=="fear_greed" else None}}
    data["sectors"]={}; data["sector_sources"]={}
    for ticker in ("XLE","XLF","XLK","XLI","XLC","XLB","XLU","XLRE","XLY","XLP","XLV"):
        data["sectors"][ticker]="+0.50%"
        data["sector_sources"][ticker]={"name":ticker,"url":f"https://example.com/{ticker}",
            "data_date":"2026-11-25","quote_type":"ETF_daily_close","note":"ETF test source",
            "close_value":100.0,"daily_change_percent":0.5,"history_close":100.0,
            "history_change":0.5,"change_display":"+0.50%"}
    return data

def observation_rows(data, pending=None):
    rows=[]
    for group in ("global_markets","bonds","fx","energy","metals","risk"):
        for name,item in data[group].items():
            is_fg=name=="fear_greed"
            rows.append({"group":group,"name":name,"source_url":item["source"]["url"],
                "target_date":"2026-11-25","observed_date":None if (group,name)==pending else "2026-11-25",
                "status":"SOURCE_NO_DATA" if (group,name)==pending else "VERIFIED",
                "instrument_identity_status":"VERIFIED","field_mapping_status":"VERIFIED",
                "source_page_fetched":(group,name)!=pending,
                "read_method":"CNN_OFFICIAL_PREVIOUS_CLOSE" if is_fg else "PLAYWRIGHT_RENDERED_HISTORY_TABLE",
                "observed_value":None if (group,name)==pending else ("15" if is_fg else ("4.652" if group=="bonds" else "100.00")),
                "observed_change":None if (group,name)==pending else ("極度恐懼" if is_fg else ("-0.41" if group=="bonds" else "+0.50")),
                "finished_at_tw":"2026-11-26T06:00:00+08:00"})
    for ticker,src in data["sector_sources"].items():
        rows.append({"group":"sectors","name":ticker,"source_url":src["url"],
            "target_date":"2026-11-25","observed_date":"2026-11-25","status":"VERIFIED",
            "instrument_identity_status":"VERIFIED","field_mapping_status":"VERIFIED",
            "source_page_fetched":True,"read_method":"PLAYWRIGHT_RENDERED_HISTORY_TABLE",
            "observed_value":"100.00","observed_change":"+0.50",
            "finished_at_tw":"2026-11-26T06:00:00+08:00"})
    return rows

class BootstrapTests(unittest.TestCase):
    def test_blank_removes_all_previous_market_values(self):
        original=fixture()
        blank=blank_fixture(original)
        self.assertEqual(blank["stage2_market_bootstrap"]["preexisting_market_values_used"],False)
        for group in ("global_markets","bonds","fx","energy","metals","risk"):
            for item in blank[group].values():
                self.assertEqual(item["display"],"待擷取")
                self.assertEqual(item["change_display"],"待擷取")
                self.assertNotIn("close_value",item["source"])
                self.assertNotIn("daily_change_percent",item["source"])
        self.assertTrue(all(v=="待擷取" for v in blank["sectors"].values()))

    def test_apply_populates_from_observations_and_keeps_missing_pending(self):
        blank=blank_fixture(fixture())
        rows=observation_rows(blank,pending=("risk","move"))
        payload={"report_date":"2026-11-26","trading_date":"2026-11-25","observations":rows}
        result=populate_fixture(blank,payload)
        self.assertEqual(result["stage2_market_bootstrap"]["verified_count"],43)
        self.assertEqual(result["stage2_market_bootstrap"]["pending_count"],1)
        self.assertEqual(result["risk"]["move"]["display"],"待核實")
        self.assertEqual(result["risk"]["move"]["source"]["verification_status"],"PENDING")
        self.assertEqual(result["bonds"]["bonds_0"]["display"],"4.652%")
        self.assertEqual(result["bonds"]["bonds_0"]["change_display"],"-1.9 bp")
        self.assertEqual(result["sectors"]["XLE"],"+0.50%")
        self.assertEqual(result["risk"]["fear_greed"]["display"],"15")
        self.assertEqual(result["risk"]["fear_greed"]["change_display"],"極度恐懼")
        self.assertEqual(blank["global_markets"]["global_markets_0"]["display"],"待擷取")

    def test_rejects_wrong_date_and_duplicate_or_missing_rows(self):
        blank=blank_fixture(fixture())
        rows=observation_rows(blank)
        with self.assertRaises(ValueError):
            populate_fixture(blank,{"report_date":"2026-11-26","trading_date":"2026-11-24","observations":rows})
        with self.assertRaises(ValueError):
            populate_fixture(blank,{"report_date":"2026-11-26","trading_date":"2026-11-25","observations":rows[:-1]})
        with self.assertRaises(ValueError):
            populate_fixture(blank,{"report_date":"2026-11-26","trading_date":"2026-11-25","observations":rows+[rows[0]]})

if __name__=="__main__":
    unittest.main()
