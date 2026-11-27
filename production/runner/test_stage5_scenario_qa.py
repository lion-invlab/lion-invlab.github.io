import unittest
from run_stage5 import evaluate_scenario_qa


class Stage5ScenarioQATests(unittest.TestCase):
    def test_no_material_change_scan_is_not_applicable(self):
        result=evaluate_scenario_qa(
            {"political_scan":{"findings":[],"no_material_change_note":"六個領域均已掃描，沒有重大且可核實的政策變化。"}},
            [],
            {"scenario_analysis_coverage":0,"scenario_analysis_status":"NOT_TESTED"},
            {"scenario_analysis_coverage":0},
        )
        self.assertEqual(result["status"],"NOT_APPLICABLE")
        self.assertEqual(result["coverage"],0)
        self.assertIn("沒有重大",result["reason"])

    def test_no_material_change_requires_zero_consistent_coverage(self):
        with self.assertRaisesRegex(ValueError,"zero scenario coverage"):
            evaluate_scenario_qa(
                {"political_scan":{"findings":[],"no_material_change_note":"無重大變化。"}},
                ["基準情境"],
                {"scenario_analysis_coverage":1,"scenario_analysis_status":"PARTIAL"},
                {"scenario_analysis_coverage":1},
            )

    def test_findings_require_all_three_scenarios(self):
        findings=[{"title":"已核實政策事件","domain":"us_policy"}]
        with self.assertRaisesRegex(ValueError,"must cover base, risk, and severe"):
            evaluate_scenario_qa(
                {"political_scan":{"findings":findings}},
                ["基準情境：維持現況。"],
                {"scenario_analysis_coverage":1,"scenario_analysis_status":"PARTIAL"},
                {"scenario_analysis_coverage":1},
            )

    def test_findings_with_all_three_scenarios_pass(self):
        findings=[{"title":"已核實政策事件","domain":"us_policy"}]
        result=evaluate_scenario_qa(
            {"political_scan":{"findings":findings}},
            ["基準情境：維持現況。","風險情境：政策擴大。","嚴重情境：衝擊升級。"],
            {"scenario_analysis_coverage":3,"scenario_analysis_status":"PASS"},
            {"scenario_analysis_coverage":3},
        )
        self.assertEqual(result["status"],"PASS")
        self.assertEqual(result["coverage"],3)

    def test_empty_findings_without_no_change_reason_are_not_applicable(self):
        with self.assertRaisesRegex(ValueError,"must cover base, risk, and severe"):
            evaluate_scenario_qa(
                {"political_scan":{"findings":[]}},
                [],
                {"scenario_analysis_coverage":0,"scenario_analysis_status":"NOT_TESTED"},
                {"scenario_analysis_coverage":0},
            )


if __name__=="__main__":
    unittest.main()
