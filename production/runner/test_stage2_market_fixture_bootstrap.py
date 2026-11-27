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
            name=(("vix","move","fear_greed")[i] if group=="risk" else f"{group}_{i}")
            data[group][name]={"display":"1,234.50" if group!="bonds" else "4.652%",
                **({"contract_label": f"{group.upper()}_CONTRACT_1"} if group in ("energy","metals") else {}),
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
                "source_page_fetched":True,
                "read_status":"SOURCE_NO_DATA" if (group,name)==pending else "PAGE_CONTENT_READ_SUCCESS",
                "read_method":"CNN_OFFICIAL_PREVIOUS_CLOSE" if is_fg else "PLAYWRIGHT_RENDERED_HISTORY_TABLE",
                "observed_value":None if (group,name)==pending else ("15" if is_fg else ("4.652" if group=="bonds" else "100.00")),
                "observed_change":None if (group,name)==pending else ("極度恐懼" if is_fg else ("-0.41" if group=="bonds" else "+0.50")),
                "contract_label": item.get("contract_label"),
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
        original["risk"]["move"]["source"].update({
            "previous_close":98.84,"open":"101.14","high":"101.27","low":"98.79",
            "screenshot_sha256":"a"*64,"screenshot_capture_time_taipei":"2026-11-25T06:47:00+08:00",
            "user_screenshot_observation":{"value":97.54,"change":-1.30,"change_percent":-1.32,
                "evidence_file":"image(20261125-223709).png","evidence_sha256":"b"*64},
            "quote_timestamp_source":"2026-11-24 16:17 GMT-5",
        })
        blank=blank_fixture(original)
        self.assertEqual(blank["stage2_market_bootstrap"]["preexisting_market_values_used"],False)
        for group in ("energy","metals"):
            for item in blank[group].values():
                self.assertTrue(item["contract_label"].endswith("_CONTRACT_1"))
        move_source=blank["risk"]["move"]["source"]
        for stale in ("previous_close","open","high","low","screenshot_sha256",
                      "screenshot_capture_time_taipei","user_screenshot_observation","quote_timestamp_source"):
            self.assertNotIn(stale,move_source)
        self.assertNotIn("97.54",move_source["note"])
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
        for row in rows:
            if row["group"] in ("energy","metals"):
                row.pop("contract_label",None)
                row["observed_row_text"]=f"Test Futures - {row['name']}_CONTRACT_1 | 100.00 | +0.50%"
        payload={"report_date":"2026-11-26","trading_date":"2026-11-25","observations":rows}
        result=populate_fixture(blank,payload)
        self.assertEqual(result["stage2_market_bootstrap"]["verified_count"],43)
        self.assertEqual(result["stage2_market_bootstrap"]["pending_count"],1)
        self.assertEqual(result["risk"]["move"]["display"],"待核實")
        self.assertEqual(result["risk"]["move"]["source"]["verification_status"],"PENDING")
        self.assertEqual(result["bonds"]["bonds_0"]["display"],"4.652%")
        self.assertEqual(result["bonds"]["bonds_0"]["change_display"],"-1.9 bp")
        self.assertEqual(result["sectors"]["XLE"],"+0.50%")
        self.assertEqual(result["energy"]["energy_0"]["contract_label"],"energy_0_CONTRACT_1")
        self.assertEqual(result["metals"]["metals_0"]["contract_label"],"metals_0_CONTRACT_1")
        self.assertEqual(result["risk"]["fear_greed"]["display"],"15")
        self.assertEqual(result["risk"]["fear_greed"]["change_display"],"極度恐懼")
        self.assertEqual(blank["global_markets"]["global_markets_0"]["display"],"待擷取")

    def test_current_run_contract_label_is_taken_from_observation(self):
        blank=blank_fixture(fixture())
        rows=observation_rows(blank)
        for row in rows:
            if row["group"]=="energy" and row["name"]=="energy_0":
                row["contract_label"]="2027年1月 (OIL)"
                row["observed_row_text"]="2026年11月25日 | 100.00 | +0.50% | WTI原油期貨 - 2027年1月 (OIL)"
        result=populate_fixture(blank,{"report_date":"2026-11-26","trading_date":"2026-11-25","observations":rows})
        self.assertEqual(result["energy"]["energy_0"]["contract_label"],"2027年1月 (OIL)")

    def test_partial_screenshot_value_survives_page_read_failure(self):
        blank=blank_fixture(fixture())
        key=("risk","move")
        blank["risk"]["move"]["display"]="98.12"
        blank["risk"]["move"]["source"]["close_value"]=98.12
        rows=observation_rows(blank,pending=key)
        move=next(x for x in rows if (x["group"],x["name"])==key)
        move["source_page_fetched"]=False
        move["read_status"]="TOOL_READ_FAILURE"
        move["status"]="TOOL_READ_FAILURE"
        move["field_evidence"]={"close":{"source_type":"USER_PROVIDED_SCREENSHOT",
            "evidence_path":"production/input/screenshots/2026-11-26/move.png",
            "evidence_sha256":"a"*64,"value":"98.12"}}
        result=populate_fixture(blank,{"report_date":"2026-11-26","trading_date":"2026-11-25","observations":rows})
        self.assertEqual(result["risk"]["move"]["display"],"98.12")
        self.assertEqual(result["risk"]["move"]["change_display"],"待核實")
        self.assertEqual(result["risk"]["move"]["source"]["verification_status"],"PENDING")

    def test_screenshot_provenance_is_not_mislabeled_as_primary_page(self):
        original=fixture()
        original["risk"]["move"]["source"]["source_role"]="PRIMARY"
        original["risk"]["fear_greed"]["source"]["source_role"]="BACKUP_1"
        blank=blank_fixture(original)
        self.assertNotIn("source_role",blank["risk"]["move"]["source"])
        self.assertEqual(blank["risk"]["fear_greed"]["source"]["source_role"],"BACKUP_1")
        rows=observation_rows(blank)
        move=next(x for x in rows if (x["group"],x["name"])==("risk","move"))
        move.update({
            "status":"VERIFIED","read_status":"USER_PROVIDED_SCREENSHOT_CONFIRMED",
            "read_method":"USER_PROVIDED_SCREENSHOT","provenance":"CURRENT_USER_PROVIDED_SCREENSHOT",
            "source_page_fetched":False,"observed_date":"2026-11-25",
            "instrument_identity":"Merrill Lynch Option Volatility Estimate (INDEXNYSEGIS: MOVE)",
            "instrument_identity_status":"VERIFIED","screenshot_instrument_identity_status":"VERIFIED",
            "field_mapping_status":"VERIFIED","observed_value":"97.54","observed_change":"-1.32",
            "observed_value_field":"Price","observed_change_field":"Change %",
            "field_evidence":{
                "close":{"source_type":"USER_PROVIDED_SCREENSHOT","evidence_path":"screenshots/move.png","evidence_sha256":"a"*64,"value":"97.54"},
                "change":{"source_type":"USER_PROVIDED_SCREENSHOT","evidence_path":"screenshots/move.png","evidence_sha256":"a"*64,"value":"-1.32"},
            },
        })
        result=populate_fixture(blank,{"report_date":"2026-11-26","trading_date":"2026-11-25","observations":rows})
        source=result["risk"]["move"]["source"]
        self.assertEqual(source["verification_status"],"VERIFIED")
        self.assertEqual(source["source_role"],"USER_PROVIDED_SCREENSHOT")
        self.assertFalse(source["source_page_fetched"])
        self.assertEqual(result["risk"]["move"]["display"],"97.54")
        self.assertEqual(result["risk"]["move"]["change_display"],"-1.32%")

    def test_screenshot_observation_cannot_be_overwritten_by_market_closed(self):
        blank=blank_fixture(fixture())
        rows=observation_rows(blank)
        blank["risk"]["move"]["display"]="97.54"
        blank["risk"]["move"]["change_display"]="-1.32%"
        row=next(x for x in rows if (x["group"],x["name"])==("risk","move"))
        row.update({"status":"MARKET_CLOSED","read_status":"MARKET_CLOSED",
                    "observed_value":None,"observed_change":None,
                    "source_page_fetched":True,"provenance":"CURRENT_CHATGPT_WEB_OPEN_OBSERVATION",
                    "read_method":"USER_PROVIDED_SCREENSHOT","prior_observation_reused":False,
                    "instrument_identity":"MOVE Index","finished_at_utc":"2026-11-26T22:00:00Z",
                    "closure_evidence_url":"https://www.nyse.com/markets/hours-calendars",
                    "closure_evidence_text":"Official calendar says closed.",
                    "closure_evidence_reader_ref":"turn1view0","closure_evidence_line_start":10,
                    "closure_evidence_line_end":12,
                    "field_evidence":{
                        "close":{"source_type":"USER_PROVIDED_SCREENSHOT","value":"97.54"},
                        "change":{"source_type":"USER_PROVIDED_SCREENSHOT","value":"-1.32"},
                    }})
        result=populate_fixture(blank,{"report_date":"2026-11-26","trading_date":"2026-11-25","observations":rows})
        item=result["risk"]["move"]
        self.assertEqual(item["source"]["verification_status"],"PENDING")
        self.assertEqual(item["display"],"97.54")
        self.assertEqual(item["change_display"],"-1.32%")

    def test_move_closed_uses_sifma_fixed_income_calendar(self):
        original=fixture()
        original["report_date"]="2026-11-27"
        original["trading_date"]="2026-11-26"
        for group in ("global_markets","bonds","fx","energy","metals","risk"):
            for item in (original.get(group) or {}).values():
                (item.get("source") or {})["data_date"]="2026-11-26"
        for source in (original.get("sector_sources") or {}).values():
            source["data_date"]="2026-11-26"
        blank=blank_fixture(original)
        rows=observation_rows(blank)
        for observation in rows:
            observation["target_date"]="2026-11-26"
        row=next(x for x in rows if (x["group"],x["name"])==("risk","move"))
        row.update({
            "status":"MARKET_CLOSED","read_status":"MARKET_CLOSED",
            "observed_value":None,"observed_change":None,
            "source_page_fetched":True,"provenance":"CURRENT_CHATGPT_WEB_OPEN_OBSERVATION",
            "read_method":"CHATGPT_WEB_OPEN_HISTORICAL_PAGE","prior_observation_reused":False,
            "instrument_identity":"ICE BofAML MOVE (MOVE)","instrument_identity_status":"VERIFIED",
            "field_mapping_status":"VERIFIED","observed_value_field":"收市","observed_change_field":"升跌（%）",
            "observed_headers":["日期","收市","開市","高","低","成交量","升跌（%）"],
            "observed_row_text":"Target date is a SIFMA full fixed-income market holiday; no MOVE close is expected.",
            "finished_at_utc":"2026-11-27T00:00:00Z",
            "closure_evidence_url":"https://www.sifma.org/news/press-releases/sifma-fixed-income-market-close-recommendations-in-the-u-s-the-u-k-and-japan-for-thanksgiving-day-2026",
            "closure_evidence_text":"SIFMA recommends a full US fixed-income market close on November 26, 2026.",
            "closure_evidence_reader_ref":"SIFMA_TEST_REF","closure_evidence_line_start":15,
            "closure_evidence_line_end":25,
        })
        result=populate_fixture(blank,{"report_date":"2026-11-27","trading_date":"2026-11-26","observations":rows})
        item=result["risk"]["move"]
        self.assertEqual(item["display"],"-")
        self.assertEqual(item["change_display"],"休市")
        self.assertEqual(item["source"]["verification_status"],"CLOSED")
        self.assertEqual(item["source"]["market_calendar_evidence"]["status"],"CLOSED")
        self.assertIn("sifma.org",item["source"]["market_calendar_evidence"]["url"])

    def test_per_instrument_target_dates_are_preserved(self):
        blank=blank_fixture(fixture())
        rows=observation_rows(blank)
        row=next(x for x in rows if (x["group"],x["name"])==("global_markets","global_markets_0"))
        row["target_date"]="2026-11-24"
        row["observed_date"]="2026-11-24"
        result=populate_fixture(blank,{"report_date":"2026-11-26","trading_date":"2026-11-25","observations":rows})
        source=result["global_markets"]["global_markets_0"]["source"]
        self.assertEqual(source["data_date"],"2026-11-24")
        self.assertEqual(result["trading_date"],"2026-11-25")

    def test_rejects_wrong_date_and_duplicate_or_missing_rows(self):
        blank=blank_fixture(fixture())
        rows=observation_rows(blank)
        with self.assertRaises(ValueError):
            populate_fixture(blank,{"report_date":"2026-11-26","trading_date":"2026-11-24","observations":rows})
        with self.assertRaises(ValueError):
            populate_fixture(blank,{"report_date":"2026-11-26","trading_date":"2026-11-25","observations":rows[:-1]})
        with self.assertRaises(ValueError):
            populate_fixture(blank,{"report_date":"2026-11-26","trading_date":"2026-11-25","observations":rows+[rows[0]]})

    def test_market_closed_requires_official_calendar_evidence(self):
        blank=blank_fixture(fixture())
        rows=observation_rows(blank)
        row=next(x for x in rows if (x["group"],x["name"])==("global_markets","global_markets_0"))
        row.update({"status":"MARKET_CLOSED","read_status":"MARKET_CLOSED",
                    "observed_value":None,"observed_change":None,
                    "source_page_fetched":True,"provenance":"CURRENT_CHATGPT_WEB_OPEN_OBSERVATION",
                    "read_method":"CHATGPT_WEB_OPEN_HISTORICAL_PAGE","prior_observation_reused":False,
                    "instrument_identity":"global_markets_0","finished_at_utc":"2026-11-26T22:00:00Z",
                    "closure_evidence_url":"https://www.nyse.com/markets/hours-calendars",
                    "closure_evidence_reader_ref":"turn1view0","closure_evidence_line_start":10,
                    "closure_evidence_line_end":12})
        result=populate_fixture(blank,{"report_date":"2026-11-26","trading_date":"2026-11-25","observations":rows})
        item=result["global_markets"]["global_markets_0"]
        self.assertEqual(item["display"],"待核實")
        self.assertEqual(item["change_display"],"待核實")
        self.assertEqual(item["source"]["verification_status"],"PENDING")

    def test_rejects_non_official_calendar_host_even_with_https_and_text(self):
        blank=blank_fixture(fixture())
        rows=observation_rows(blank)
        row=next(x for x in rows if (x["group"],x["name"])==("global_markets","global_markets_0"))
        row.update({"status":"MARKET_CLOSED","read_status":"MARKET_CLOSED",
                    "observed_value":None,"observed_change":None,
                    "source_page_fetched":True,"provenance":"CURRENT_CHATGPT_WEB_OPEN_OBSERVATION",
                    "read_method":"CHATGPT_WEB_OPEN_HISTORICAL_PAGE","prior_observation_reused":False,
                    "instrument_identity":"global_markets_0","finished_at_utc":"2026-11-26T22:00:00Z",
                    "closure_evidence_url":"https://www.example.com/official-calendar",
                    "closure_evidence_reader_ref":"turn1view0","closure_evidence_line_start":10,
                    "closure_evidence_line_end":12})
        result=populate_fixture(blank,{"report_date":"2026-11-26","trading_date":"2026-11-25","observations":rows})
        item=result["global_markets"]["global_markets_0"]
        self.assertEqual(item["display"],"待核實")
        self.assertEqual(item["change_display"],"待核實")
        self.assertEqual(item["source"]["verification_status"],"PENDING")

    def test_official_market_closure_applies_to_sector_rows(self):
        blank=blank_fixture(fixture())
        rows=observation_rows(blank)
        row=next(x for x in rows if (x["group"],x["name"])==("sectors","XLE"))
        row.update({"status":"MARKET_CLOSED","read_status":"MARKET_CLOSED",
                    "observed_value":None,"observed_change":None,
                    "source_page_fetched":True,"provenance":"CURRENT_CHATGPT_WEB_OPEN_OBSERVATION",
                    "read_method":"CHATGPT_WEB_OPEN_HISTORICAL_PAGE","prior_observation_reused":False,
                    "instrument_identity":"XLE ETF","instrument_identity_status":"VERIFIED",
                    "field_mapping_status":"VERIFIED","finished_at_utc":"2026-11-26T22:00:00Z",
                    "closure_evidence_url":"https://www.asx.com.au/markets/trade-our-cash-market",
                    "closure_evidence_text":"ASX official calendar confirms the market is closed on 2026-11-25.",
                    "closure_evidence_reader_ref":"turn1view0","closure_evidence_line_start":10,
                    "closure_evidence_line_end":12})
        result=populate_fixture(blank,{"report_date":"2026-11-26","trading_date":"2026-11-25","observations":rows})
        self.assertEqual(result["sectors"]["XLE"],"休市")
        self.assertEqual(result["sector_sources"]["XLE"]["history_close"],"-")
        self.assertEqual(result["sector_sources"]["XLE"]["change_display"],"休市")
        self.assertEqual(result["sector_sources"]["XLE"]["verification_status"],"CLOSED")

    def test_official_market_closure_uses_dash_for_value_and_reason_for_change(self):
        blank=blank_fixture(fixture())
        rows=observation_rows(blank)
        row=next(x for x in rows if (x["group"],x["name"])==("global_markets","global_markets_0"))
        row.update({"status":"MARKET_CLOSED","read_status":"MARKET_CLOSED",
                    "observed_value":None,"observed_change":None,
                    "source_page_fetched":True,"provenance":"CURRENT_CHATGPT_WEB_OPEN_OBSERVATION",
                    "read_method":"CHATGPT_WEB_OPEN_HISTORICAL_PAGE","prior_observation_reused":False,
                    "instrument_identity":"global_markets_0","finished_at_utc":"2026-11-26T22:00:00Z",
                    "closure_evidence_url":"https://www.nyse.com/markets/hours-calendars",
                    "closure_evidence_text":"NYSE official calendar confirms the market is closed on 2026-11-25.",
                    "closure_evidence_reader_ref":"turn1view0","closure_evidence_line_start":10,
                    "closure_evidence_line_end":12})
        result=populate_fixture(blank,{"report_date":"2026-11-26","trading_date":"2026-11-25","observations":rows})
        item=result["global_markets"]["global_markets_0"]
        self.assertEqual(item["display"],"-")
        self.assertEqual(item["change_display"],"休市")
        self.assertEqual(item["source"]["verification_status"],"CLOSED")
        self.assertEqual(item["source"]["market_calendar_evidence"]["status"],"CLOSED")

 # Regression: metals labels are parsed from the observed row text, including its row key.
 # 11/27 Main capture trigger after closure manifest alignment.
if __name__=="__main__":
    unittest.main()
