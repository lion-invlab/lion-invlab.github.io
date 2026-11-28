from __future__ import annotations
import unittest
from run_stage2 import validate_fedwatch_observation

WR_SHA="a"*64
CONTEXT={"report_date":"2026-11-30","trading_date":"2026-11-27"}

def valid_payload():
    return {
        "status":"VERIFIED",
        "source_name":"Investing.com Fed Rate Monitor",
        "source_url":"https://www.investing.com/central-banks/fed-rate-monitor",
        "report_date":"2026-11-30",
        "trading_date":"2026-11-27",
        "captured_at_utc":"2026-11-30T21:12:00Z",
        "target_meeting":"2026-12-16",
        "current_target_range":"3.75%-4.00%",
        "updated_at_tw":"2026-11-30 05:12",
        "probabilities":[{"outcome":"hold","rate_range":"3.75%-4.00%","probability":68.2},{"outcome":"cut","rate_range":"3.50%-3.75%","probability":31.8}],
        "web_reader_ref":"turn-fedwatch-test",
        "web_line_start":10,
        "web_line_end":22,
        "reason":None,
        "stage2_wr_sha256":WR_SHA
    }

class FedWatchObservationTests(unittest.TestCase):
    def test_valid_two_outcome_snapshot_is_bound_and_preserved(self):
        result=validate_fedwatch_observation(valid_payload(),{"wr_sha256":WR_SHA},CONTEXT)
        self.assertEqual(result["status"],"VERIFIED")
        self.assertEqual(result["current_target_range"],"3.75%-4.00%")
        self.assertEqual(len(result["probabilities"]),2)
        self.assertEqual(len(result["observation_sha256"]),64)

    def test_missing_observation_blocks_silent_empty_fedwatch(self):
        with self.assertRaisesRegex(ValueError,"missing the independent FedWatch"):
            validate_fedwatch_observation(None,{"wr_sha256":WR_SHA},CONTEXT)

    def test_worker_wr_digest_is_not_a_fedwatch_gate(self):
        payload=valid_payload()
        payload["stage2_wr_sha256"]="b"*64
        result=validate_fedwatch_observation(payload,{},CONTEXT)
        self.assertEqual(result["status"],"VERIFIED")

    def test_dates_must_match_the_same_run(self):
        payload=valid_payload()
        payload["trading_date"]="2026-11-26"
        with self.assertRaisesRegex(ValueError,"dates do not match"):
            validate_fedwatch_observation(payload,{"wr_sha256":WR_SHA},CONTEXT)

    def test_probability_distribution_must_sum_to_100(self):
        payload=valid_payload()
        payload["probabilities"][0]["probability"]=60
        with self.assertRaisesRegex(ValueError,"not 100%"):
            validate_fedwatch_observation(payload,{"wr_sha256":WR_SHA},CONTEXT)

    def test_unavailable_status_carries_no_unverified_probabilities(self):
        payload=valid_payload()
        payload.update({"status":"TOOL_READ_FAILURE","target_meeting":None,"current_target_range":None,"updated_at_tw":None,"probabilities":[],"web_reader_ref":None,"web_line_start":None,"web_line_end":None,"reason":"Investing.com Fed Rate Monitor could not be read."})
        result=validate_fedwatch_observation(payload,{"wr_sha256":WR_SHA},CONTEXT)
        self.assertEqual(result["status"],"TOOL_READ_FAILURE")
        self.assertEqual(result["probabilities"],[])

    def test_unavailable_status_cannot_carry_old_probabilities(self):
        payload=valid_payload()
        payload.update({"status":"SOURCE_NO_DATA","reason":"No current meeting distribution was available."})
        with self.assertRaisesRegex(ValueError,"must not carry unverified"):
            validate_fedwatch_observation(payload,{"wr_sha256":WR_SHA},CONTEXT)

if __name__=="__main__":
    unittest.main()
