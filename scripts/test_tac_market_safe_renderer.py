#!/usr/bin/env python3
"""Tests for the contract-driven TAC market renderer."""
import json
import re
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

    def test_fedwatch_updates_probability_ranges_bars_legend_and_fomc(self):
        html = ('<section id="fed"><div class="fc-probs-refined">'
                '<div class="fc-prob fc-hold"><div class="fc-prob-label"><span>維持不變</span></div><strong>90.0%</strong><div class="fc-range">維持 3.75%–4.00%</div></div>'
                '<div class="fc-prob fc-hike"><div class="fc-prob-label"><span>升息一碼</span></div><strong>10.0%</strong><div class="fc-range">升至 4.00%–4.25%</div></div>'
                '<div class="fc-split-bar" role="img" aria-label="舊標籤"><span class="fc-split-hold" style="width:90%"></span><span class="fc-split-hike" style="width:10%"></span></div>'
                '<div class="fc-split-legend"><span>維持不變 <b>90.0%</b></span><span>升息一碼 <b>10.0%</b></span></div>'
                '<details><summary>資料時間與快照口徑</summary><div>舊稽核文字</div></details></div>'
                '<div class="fc-fomc"><div class="fc-fomc-meeting"><span>FOMC 會議</span><b>舊會議</b></div>'
                '<div class="fc-fomc-rate"><span>目前目標利率</span><b>舊利率</b></div></div></section>')
        contract = {"groups":{"fedwatch":{
            "container":"#fed","outcomes":{
                "hold":{"label":"維持不變","row":".fc-hold","probability_selector":"strong","rate_range_selector":".fc-range","bar_selector":".fc-split-hold","legend_index":0},
                "hike_one":{"label":"升息一碼","row":".fc-hike","probability_selector":"strong","rate_range_selector":".fc-range","bar_selector":".fc-split-hike","legend_index":1}},
            "split_bar_selector":".fc-split-bar","legend_selector":".fc-split-legend",
            "audit_container_selector":".fc-probs-refined","audit_selector":"details",
            "fomc":{"meeting_row":".fc-fomc-meeting","meeting_value_selector":"b","rate_row":".fc-fomc-rate","rate_value_selector":"b"}}}}
        snapshot = {"fedwatch":{"probabilities":{
            "hold":{"probability":93.4,"rate_range":"維持 3.75%–4.00%"},
            "hike_one":{"probability":6.6,"rate_range":"升至 4.00%–4.25%"}},
            "target_meeting":"2026/12/08–12/09","updated_at":"2026/11/02 05:00 台灣時間",
            "target_rate_range":"3.75%–4.00%","audit_text":"CME FedWatch 快照：2026/11/02 05:00 台灣時間；維持 93.4%，升息一碼 6.6%。","aria_label":"維持利率 93.4%，升息一碼 6.6%；CME FedWatch 快照時間 2026/11/02 05:00 台灣時間"}}
        result = render_market_html(html,{"groups":{},"fedwatch":snapshot["fedwatch"]},contract)
        self.assertIn("<strong>93.4%</strong>",result)
        self.assertIn("維持 3.75%–4.00%",result)
        self.assertIn('style="width:93.4%"',result)
        self.assertIn('style="width:6.6%"',result)
        self.assertIn("<b>93.4%</b>",result)
        self.assertIn("2026/12/08–12/09",result)
        self.assertIn("3.75%–4.00%",result)
        self.assertIn("2026/11/02 05:00 台灣時間",result)

    def test_fedwatch_probability_sum_must_equal_100(self):
        contract = {"groups":{"fedwatch":{"container":"#fed","outcomes":{"hold":{},"hike_one":{}}}}}
        html = '<section id="fed"></section>'
        snapshot = {"fedwatch":{"probabilities":{"hold":{"probability":80,"rate_range":"a"},"hike_one":{"probability":10,"rate_range":"b"}},
                    "target_meeting":"x","updated_at":"x","target_rate_range":"x","audit_text":"x","aria_label":"x"}}
        with self.assertRaisesRegex(ValueError,"sum to"):
            render_market_html(html,{"groups":{},"fedwatch":snapshot["fedwatch"]},contract)

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

    def test_real_dual_masters_fedwatch_noop_preserves_every_byte(self):
        binding = json.loads((ROOT / "scripts/tac_html_binding_map.json").read_text(encoding="utf-8"))
        spec = binding["groups"]["fedwatch"]
        for label, relative in binding["templates"].items():
            with self.subTest(template=label):
                source = (ROOT / relative).read_text(encoding="utf-8")
                parser = SourceTreeParser(source)
                parser.feed(source)
                parser.close()
                containers = select(parser.root, spec["container"])
                self.assertEqual(len(containers), 1)
                container = containers[0]
                probabilities = {}
                for key, outcome in spec["outcomes"].items():
                    rows = select(container, outcome["row"])
                    self.assertEqual(len(rows), 1, f"{label}.{key} row")
                    strong = select(rows[0], outcome["probability_selector"])
                    ranges = select(rows[0], outcome["rate_range_selector"])
                    self.assertEqual(len(strong), 1)
                    self.assertEqual(len(ranges), 1)
                    p_text = "".join(x.text for x in spans_inside(strong[0], parser.spans)).strip()
                    p_match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)%", p_text)
                    self.assertIsNotNone(p_match, p_text)
                    range_text = "".join(x.text for x in spans_inside(ranges[0], parser.spans)).strip()
                    probabilities[key] = {"probability":float(p_match.group(1)), "rate_range":range_text}
                split = select(container, spec["split_bar_selector"])
                self.assertEqual(len(split), 1)
                aria_label = split[0].attrs.get("aria-label")
                self.assertTrue(aria_label)
                meeting_row = select(container, spec["fomc"]["meeting_row"])
                rate_row = select(container, spec["fomc"]["rate_row"])
                self.assertEqual(len(meeting_row), 1)
                self.assertEqual(len(rate_row), 1)
                meeting = select(meeting_row[0], "b")
                rate = select(rate_row[0], "b")
                self.assertEqual(len(meeting), 1)
                self.assertEqual(len(rate), 1)
                meeting_text = "".join(x.text for x in spans_inside(meeting[0], parser.spans)).strip()
                rate_text = "".join(x.text for x in spans_inside(rate[0], parser.spans)).strip()
                details = select(select(container, spec["audit_container_selector"])[0], spec["audit_selector"])
                self.assertEqual(len(details), 1)
                audit_divs = [n for n in descendants(details[0]) if n.tag == "div" and spans_inside(n, parser.spans)]
                self.assertEqual(len(audit_divs), 1)
                audit_text = "".join(x.text for x in spans_inside(audit_divs[0], parser.spans)).strip()
                time_match = re.search(r"20\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}\s*（?台灣時間", audit_text)
                if not time_match:
                    time_match = re.search(r"20\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}\s*台灣時間", aria_label)
                self.assertIsNotNone(time_match, f"{label}: cannot recover snapshot time")
                snapshot = {"groups":{}, "fedwatch":{
                    "probabilities":probabilities,
                    "target_meeting":meeting_text,
                    "updated_at":time_match.group(0),
                    "target_rate_range":rate_text,
                    "audit_text":audit_text,
                    "aria_label":aria_label
                }}
                self.assertEqual(render_market_html(source,snapshot,binding),source,
                                 f"{label}: FedWatch no-op must preserve every byte")

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
