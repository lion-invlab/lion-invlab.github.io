#!/usr/bin/env python3
"""Tests for the contract-driven TAC market renderer."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_tac_market_safe import render_market_html


def minimal_contract():
    return {"groups": {
        "global_indices": {
            "container": "#global-markets", "row": ".row",
            "key_by_label": {"dow": "道瓊工業指數"},
            "value_selector": "span.r", "change_selector": "span.r",
            "value_index": 0, "change_index": 1,
            "snapshot_fields": {"display_value": "value", "display_change": "change"}
        },
        "sectors": {
            "container": "#sectors", "row": ".sector-row",
            "key_by_ticker": {"xlk": "XLK"},
            "value_selector": "span.r",
            "snapshot_fields": {"display_value": "change", "display_change": None}
        },
        "bonds": {"container":"#bonds","row":".row","key_by_label":{},
                  "value_selector":"span.r","change_selector":"span.r","value_index":0,"change_index":1,
                  "snapshot_fields":{"display_value":"value","display_change":"change"}},
        "fx": {"container":"#fx","row":".row","key_by_label":{},
               "value_selector":"span.r","change_selector":"span.r","value_index":0,"change_index":1,
               "snapshot_fields":{"display_value":"value","display_change":"change"}},
        "energy": {"container":"#energy","row":".row","key_by_label":{},
                   "value_selector":"span.r","change_selector":"span.r","value_index":0,"change_index":1,
                   "snapshot_fields":{"display_value":"value","display_change":"change"}},
        "precious_metals": {"container":"#metals","row":".row","key_by_label":{},
                            "value_selector":"span.r","change_selector":"span.r","value_index":0,"change_index":1,
                            "snapshot_fields":{"display_value":"value","display_change":"change"}}
    }}


class SafeMarketRendererTests(unittest.TestCase):
    def test_contract_driven_text_only_render(self):
        html = ('<main id="global-markets"><div class="row"><b>道瓊工業指數</b>'
                '<span class="r">100</span><span class="r up">+1.0%</span></div></main>'
                '<div id="sectors"><div class="sector-row"><b>XLK</b><span class="r up">+0.5%</span></div></div>')
        contract = minimal_contract()
        snapshot = {"groups":{
            "global_indices":{"dow":{"value":"101","change":"+1.5%"}},
            "sectors":{"xlk":{"change":"+0.8%"}}
        }}
        result = render_market_html(html,snapshot,contract)
        self.assertIn('<span class="r">101</span>',result)
        self.assertIn('<span class="r up">+1.5%</span>',result)
        self.assertIn('<span class="r up">+0.8%</span>',result)
        self.assertEqual(html.count('<span class="r up">'),result.count('<span class="r up">'))

    def test_direction_change_is_blocked_not_miscolored(self):
        html = '<main id="global-markets"><div class="row"><b>道瓊工業指數</b><span class="r">100</span><span class="r up">+1.0%</span></div></main>'
        contract = minimal_contract()
        contract["groups"] = {"global_indices":contract["groups"]["global_indices"]}
        snapshot = {"groups":{"global_indices":{"dow":{"value":"99","change":"-1.0%"}}}}
        with self.assertRaisesRegex(ValueError,"direction class would be stale"):
            render_market_html(html,snapshot,contract)

    def test_missing_group_key_fails_closed(self):
        html = '<main id="global-markets"><div class="row"><b>道瓊工業指數</b><span class="r">100</span><span class="r up">+1.0%</span></div></main>'
        contract = minimal_contract()
        contract["groups"] = {"global_indices":contract["groups"]["global_indices"]}
        with self.assertRaisesRegex(ValueError,"key mismatch"):
            render_market_html(html,{"groups":{"global_indices":{}}},contract)

    def test_attributes_and_markup_are_preserved(self):
        html = '<main id="global-markets" class="locked"><div class="row" data-x="1"><b><a href="/dow">道瓊工業指數</a></b><span class="r">100</span><span class="r up">+1.0%</span></div></main>'
        contract = minimal_contract()
        contract["groups"] = {"global_indices":contract["groups"]["global_indices"]}
        snapshot = {"groups":{"global_indices":{"dow":{"value":"101","change":"+1.2%"}}}}
        result = render_market_html(html,snapshot,contract)
        self.assertIn('class="locked"',result)
        self.assertIn('data-x="1"',result)
        self.assertIn('<a href="/dow">道瓊工業指數</a>',result)
        self.assertIn('<span class="r up">+1.2%</span>',result)


if __name__ == "__main__":
    unittest.main()
