#!/usr/bin/env python3
"""Tests for the contract-driven TAC market renderer."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_tac_market_safe import (SourceTreeParser, render_market_html, resolve_row, select, slot_text_span, spans_inside, label_key)


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

    }}


class SafeMarketRendererTests(unittest.TestCase):
    def test_contract_driven_text_only_render(self):
        html = ('<main id="global-markets"><div class="row"><b>道瓊工業指數</b>'
                '<span class="r">100</span><span class="r up">+1.0%</span></div></main>'
                '<div id="sectors"><div class="sector-row"><b>XLK</b><span class="r up">+0.5%</span></div></div>')
        contract = minimal_contract()
        snapshot = {"groups":{
            "global_indices":{"dow":{"value":"101","change":"+1.5%"}},
            "sectors":{"xlk":{"change":"+0.8%"}},
            "bonds":{}, "fx":{}, "energy":{}, "precious_metals":{}
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
        with self.assertRaisesRegex(ValueError,"status class transition is not authorized"):
            render_market_html(html,snapshot,contract)

    def test_status_class_transitions_preserve_other_tokens(self):
        html = '<main id="global-markets"><div class="row"><b>道瓊工業指數</b><span class="r">100</span><span class="r up trend-good">+1.0%</span></div></main>'
        contract = minimal_contract()
        contract["rules"] = {"allow_mapped_status_class_token_transition": True, "status_class_map": {"positive":"up","negative":"down","neutral":"flat","warning":"warn"}, "pending_value_text":"待核實"}
        contract["groups"] = {"global_indices":contract["groups"]["global_indices"]}
        snapshot = {"groups":{"global_indices":{"dow":{"value":"99","change":"-1.0%"}}}}
        result = render_market_html(html,snapshot,contract)
        self.assertIn('class="r down trend-good"', result)
        self.assertIn('<span class="r down trend-good">-1.0%</span>', result)

    def test_status_class_transitions_both_directions_and_flat_warn(self):
        def run(old, new):
            initial = {"up":"+1.0%", "down":"-1.0%", "flat":"0.0%", "warn":"待核實"}[old]
            html = f'<main id="global-markets"><div class="row"><b>道瓊工業指數</b><span class="r">100</span><span class="r {old}">{initial}</span></div></main>'
            contract = minimal_contract()
            contract["rules"] = {"allow_mapped_status_class_token_transition": True, "status_class_map": {"positive":"up","negative":"down","neutral":"flat","warning":"warn"}, "pending_value_text":"待核實"}
            contract["groups"] = {"global_indices":contract["groups"]["global_indices"]}
            snapshot = {"groups":{"global_indices":{"dow":{"value":"100","change":new}}}}
            return render_market_html(html,snapshot,contract)
        self.assertIn('class="r down"', run("up", "-1.0%"))
        self.assertIn('class="r up"', run("down", "+1.0%"))
        self.assertIn('class="r flat"', run("up", "0.0%"))
        self.assertIn('class="r warn"', run("flat", "待核實"))

    def test_missing_or_ambiguous_status_class_fails_closed(self):
        for classes in ("r", "r up down"):
            with self.subTest(classes=classes):
                html = f'<main id="global-markets"><div class="row"><b>道瓊工業指數</b><span class="r">100</span><span class="{classes}">+1.0%</span></div></main>'
                contract = minimal_contract()
                contract["rules"] = {"allow_mapped_status_class_token_transition": True}
                contract["groups"] = {"global_indices":contract["groups"]["global_indices"]}
                snapshot = {"groups":{"global_indices":{"dow":{"value":"99","change":"-1.0%"}}}}
                with self.assertRaisesRegex(ValueError, "exactly one existing status class token"):
                    render_market_html(html,snapshot,contract)

    def test_risk_indicators_update_with_risk_specific_status_mapping(self):
        html = ('<article id="sentiment">'
                '<div class="sbox"><div class="label"><span class="label-en">VIX</span></div><strong>19.45</strong><span class="warn">+2.21%</span></div>'
                '<div class="sbox"><div class="label"><span class="label-en">MOVE</span></div><strong>103.31</strong><span class="down">-3.30%</span></div>'
                '<section class="sbox cnn-fg-preview"><div class="fg6-title"><span class="label-en">CNN Fear &amp; Greed</span></div><span class="fg6-score-main">21.0</span></section>'
                '</article>')
        contract = {"rules":{"allow_mapped_status_class_token_transition":True,
                             "pending_value_text":"待核實",
                             "status_class_map":{"positive":"up","negative":"down","neutral":"flat","warning":"warn"}},
                    "groups":{"risk_indicators":{"container":"#sentiment","records":{
                        "vix":{"row":".sbox","key_text":"VIX","value_selector":"strong","change_selector":".warn,.up,.down,.flat",
                               "status_class_map":{"positive":"warn","negative":"down","neutral":"flat","warning":"warn"}},
                        "move":{"row":".sbox","key_text":"MOVE","value_selector":"strong","change_selector":".warn,.up,.down,.flat",
                                "status_class_map":{"positive":"warn","negative":"down","neutral":"flat","warning":"warn"}},
                        "cnn_fear_greed":{"row":".cnn-fg-preview","key_text":"CNN Fear & Greed","value_selector":".fg6-score-main","change_selector":None}
                    }}}}
        snapshot = {"groups":{}, "risk_indicators":{
            "vix":{"value":"20.10","change":"-1.50%"},
            "move":{"value":"101.00","change":"+1.20%"},
            "cnn_fear_greed":{"value":"28.0"}
        }}
        result = render_market_html(html,snapshot,contract)
        self.assertIn('<strong>20.10</strong><span class="down">-1.50%</span>',result)
        self.assertIn('<strong>101.00</strong><span class="warn">+1.20%</span>',result)
        self.assertIn('<span class="fg6-score-main">28.0</span>',result)
        self.assertIn('cnn-fg-preview',result)

    def test_missing_group_key_fails_closed(self):
        html = '<main id="global-markets"><div class="row"><b>道瓊工業指數</b><span class="r">100</span><span class="r up">+1.0%</span></div></main>'
        contract = minimal_contract()
        contract["groups"] = {"global_indices":contract["groups"]["global_indices"]}
        with self.assertRaisesRegex(ValueError,"key mismatch"):
            render_market_html(html,{"groups":{"global_indices":{}}},contract)

    def test_real_dual_masters_resolve_every_mapped_market_slot(self):
        binding = json.loads((ROOT / "scripts/tac_html_binding_map.json").read_text(encoding="utf-8"))
        for label, relative in binding["templates"].items():
            with self.subTest(template=label):
                source = (ROOT / relative).read_text(encoding="utf-8")
                parser = SourceTreeParser(source)
                parser.feed(source)
                parser.close()
                snapshot_groups = {}
                for group_name, spec in binding["groups"].items():
                    if group_name not in {"global_indices","sectors","bonds","fx","energy","precious_metals"}:
                        continue
                    containers = select(parser.root, spec["container"])
                    self.assertEqual(len(containers), 1, f"{label}.{group_name} container")
                    group = {}
                    keys = spec.get("key_by_label", spec.get("key_by_ticker", {}))
                    for key in keys:
                        row = resolve_row(group_name, key, spec, containers[0], parser.spans)
                        value_span, _ = slot_text_span(row, spec["value_selector"], int(spec.get("value_index",0)), parser.spans, f"{group_name}.{key}.value")
                        record = {spec["snapshot_fields"]["display_value"]: value_span.text}
                        change_field = spec["snapshot_fields"].get("display_change")
                        if change_field:
                            change_span, _ = slot_text_span(row, spec["change_selector"], int(spec.get("change_index",1)), parser.spans, f"{group_name}.{key}.change")
                            record[change_field] = change_span.text
                        group[key] = record
                    snapshot_groups[group_name] = group
                risk_spec = binding["groups"]["risk_indicators"]
                risk_container = select(parser.root, risk_spec["container"])
                self.assertEqual(len(risk_container), 1, f"{label}.risk_indicators container")
                risk_snapshot = {}
                for risk_key, risk_record in risk_spec["records"].items():
                    needle = "".join(ch.casefold() for ch in risk_record["key_text"] if ch.isalnum())
                    risk_rows = select(risk_container[0], risk_record["row"])
                    hits = []
                    for row in risk_rows:
                        key_nodes = select(row, risk_record.get("key_selector", risk_record["row"]))
                        if len(key_nodes) == 1 and needle == label_key("".join(
                            span.text for span in spans_inside(key_nodes[0], parser.spans)
                        )):
                            hits.append(row)
                    self.assertEqual(len(hits), 1, f"{label}.risk_indicators.{risk_key} row")
                    value_nodes = select(hits[0], risk_record["value_selector"])
                    self.assertEqual(len(value_nodes), 1, f"{label}.risk_indicators.{risk_key} value")
                    value_spans = [span for span in spans_inside(value_nodes[0], parser.spans) if span.text.strip()]
                    self.assertEqual(len(value_spans), 1, f"{label}.risk_indicators.{risk_key} value text")
                    record = {"value": value_spans[0].text}
                    if risk_record.get("change_selector"):
                        change_nodes = select(hits[0], risk_record["change_selector"])
                        self.assertEqual(len(change_nodes), 1, f"{label}.risk_indicators.{risk_key} change")
                        change_spans = [span for span in spans_inside(change_nodes[0], parser.spans) if span.text.strip()]
                        self.assertEqual(len(change_spans), 1, f"{label}.risk_indicators.{risk_key} change text")
                        record["change"] = change_spans[0].text
                    risk_snapshot[risk_key] = record
                rendered = render_market_html(source, {"groups":snapshot_groups, "risk_indicators":risk_snapshot}, binding)
                self.assertEqual(rendered, source, f"{label}: no-op snapshot must preserve every byte")

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
