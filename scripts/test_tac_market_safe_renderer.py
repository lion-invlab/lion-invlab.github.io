#!/usr/bin/env python3
"""Tests for the contract-driven TAC market renderer."""
import json
import re
import sys
from html import unescape
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_tac_market_safe import (SourceTreeParser, render_market_html, resolve_row, select, slot_text_span, spans_inside, label_key, descendants, coalesce_spans)


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

    def test_schema_top_level_market_groups_are_accepted(self):
        html = ('<main id="global-markets"><div class="row"><b>道瓊工業指數</b>'
                '<span class="r">100</span><span class="r up">+1.0%</span></div></main>'
                '<div id="sectors"><div class="sector-row"><b>XLK</b><span class="r up">+0.5%</span></div></div>')
        contract = minimal_contract()
        snapshot = {
            "global_indices": {"dow": {"value": "101", "change": "+1.5%"}},
            "sectors": {"xlk": {"change": "+0.8%"}},
        }
        result = render_market_html(html, snapshot, contract)
        self.assertIn('<span class="r">101</span>', result)
        self.assertIn('<span class="r up">+1.5%</span>', result)
        self.assertIn('<span class="r up">+0.8%</span>', result)

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

    def test_summary_and_observation_text_slots_render_without_structure_changes(self):
        binding = {"groups":{"editorial":{
            "summary":{"container":".bluf","headline_selector":"h1","body_selector":"p"},
            "observation":{"container":"#view","market_panel":".focus-market","levels_panel":".focus-levels","core_panel":".focus-core",
                          "market_text_selector":".key","levels_text_selector":".key","core_text_selector":".callout"}}}}
        observation = ('<section id="view">'
                       '<div class="focus-panel focus-market"><div class="key"><b>市場觀點</b><br/>市場舊文</div></div>'
                       '<div class="focus-panel focus-levels"><div class="key"><b>道瓊：</b>舊支撐<br/><b>S&amp;P：</b>舊壓力<br/><b>SOX：</b>舊區間</div></div>'
                       '<div class="focus-panel focus-core"><div class="callout"><b>今日核心觀察：</b>核心舊文</div></div>'
                       '</section>')
        for segment_count in (3,5):
            with self.subTest(segment_count=segment_count):
                labels = "".join(f"<b>段落{i+1}</b><br/>" for i in range(segment_count))
                old_text = "".join(f"舊內容{i+1}" for i in range(segment_count))
                html = f'<article class="bluf"><h1>舊標題</h1><p>{labels}{old_text}</p></article>' + observation
                # Construct paragraph as distinct text nodes following each bold label.
                pieces = "".join(f"<b>段落{i+1}</b><br/>舊內容{i+1}" for i in range(segment_count))
                html = f'<article class="bluf"><h1>舊標題</h1><p>{pieces}</p></article>' + observation
                snapshot = {"groups":{},"editorial":{
                    "headline":"新標題",
                    "body_segments":[f"新內容{i+1}" for i in range(segment_count)],
                    "market_text":"新的市場觀點",
                    "levels_segments":["新道瓊支撐","新 S&P 壓力","新 SOX 區間"],
                    "core_text":"新的核心觀察"
                }}
                result = render_market_html(html,snapshot,binding)
                self.assertIn("<h1>新標題</h1>",result)
                for i in range(segment_count):
                    self.assertIn(f"新內容{i+1}",result)
                self.assertIn("新的市場觀點",result)
                self.assertIn("新道瓊支撐",result)
                self.assertIn("新 S&amp;P 壓力",result)
                self.assertIn("新 SOX 區間",result)
                self.assertIn("新的核心觀察",result)
                self.assertIn("<b>段落1</b><br/>",result)
                self.assertIn('class="focus-panel focus-levels"',result)

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
                fed_binding = {"rules":binding["rules"],"groups":{"fedwatch":spec}}
                self.assertEqual(render_market_html(source,snapshot,fed_binding),source,
                                 f"{label}: FedWatch no-op must preserve every byte")

    def test_real_dual_masters_editorial_noop_preserves_every_byte(self):
        binding = json.loads((ROOT / "scripts/tac_html_binding_map.json").read_text(encoding="utf-8"))
        spec = binding["groups"]["editorial"]
        for label, relative in binding["templates"].items():
            with self.subTest(template=label):
                source = (ROOT / relative).read_text(encoding="utf-8")
                parser = SourceTreeParser(source)
                parser.feed(source)
                parser.close()
                summary_nodes = select(parser.root, spec["summary"]["container"])
                self.assertEqual(len(summary_nodes),1)
                headlines = select(summary_nodes[0],spec["summary"]["headline_selector"])
                body_nodes = select(summary_nodes[0],spec["summary"]["body_selector"])
                self.assertEqual(len(headlines),1)
                self.assertEqual(len(body_nodes),1)
                headline_spans = [x for x in spans_inside(headlines[0],parser.spans) if x.text.strip()]
                body_spans = coalesce_spans([x for x in spans_inside(body_nodes[0],parser.spans) if x.parent is body_nodes[0] and x.text.strip()])
                self.assertEqual(len(headline_spans),1)
                editorial = {"headline":headline_spans[0].text,"body_segments":[unescape(x.text) for x in body_spans]}
                for field_name,panel_key,content_key in (
                    ("market_text","market_panel","market_text_selector"),
                    ("levels_segments","levels_panel","levels_text_selector"),
                    ("core_text","core_panel","core_text_selector")):
                    panels = select(parser.root,spec["observation"][panel_key])
                    self.assertEqual(len(panels),1)
                    content = select(panels[0],spec["observation"][content_key])
                    self.assertEqual(len(content),1)
                    direct = coalesce_spans([x for x in spans_inside(content[0],parser.spans) if x.parent is content[0] and x.text.strip()])
                    if len(direct) == 1:
                        editorial[field_name] = unescape(direct[0].text)
                    else:
                        editorial[field_name] = [unescape(x.text) for x in direct]
                editorial_binding = {"groups":{"editorial":spec}}
                self.assertEqual(render_market_html(source,{"groups":{},"editorial":editorial},editorial_binding),source,
                                 f"{label}: editorial no-op must preserve every byte")

    def test_real_dual_masters_news_noop_preserves_every_byte(self):
        binding = json.loads((ROOT / "scripts/tac_html_binding_map.json").read_text(encoding="utf-8"))
        spec = binding["groups"]["news"]
        for label, relative in binding["templates"].items():
            with self.subTest(template=label):
                source = (ROOT / relative).read_text(encoding="utf-8")
                parser = SourceTreeParser(source)
                parser.feed(source)
                parser.close()
                news_data = {}
                for panel_key, panel_spec in spec["panels"].items():
                    containers = select(parser.root,panel_spec["container"])
                    self.assertEqual(len(containers),1,f"{label}.{panel_key} container")
                    container = containers[0]
                    meta = select(container,panel_spec["meta_selector"])
                    self.assertEqual(len(meta),1)
                    meta_spans = coalesce_spans([x for x in spans_inside(meta[0],parser.spans) if x.text.strip()])
                    self.assertEqual(len(meta_spans),1)
                    panel = {"meta_text":unescape(meta_spans[0].text),"items":[]}
                    warnings = select(container,panel_spec["warning_selector"])
                    if warnings:
                        warning_spans = coalesce_spans([x for x in spans_inside(warnings[0],parser.spans) if x.text.strip()])
                        self.assertEqual(len(warnings),1)
                        self.assertEqual(len(warning_spans),1)
                        panel["window_text"] = unescape(warning_spans[0].text)
                    item_nodes = select(container,panel_spec["item_selector"])
                    for item_node in item_nodes:
                        titles = select(item_node,panel_spec["title_selector"])
                        summaries = select(item_node,panel_spec["summary_selector"])
                        source_containers = select(item_node,panel_spec["sources_container_selector"])
                        self.assertEqual(len(titles),1)
                        self.assertEqual(len(summaries),1)
                        self.assertEqual(len(source_containers),1)
                        title_spans = coalesce_spans([x for x in spans_inside(titles[0],parser.spans) if x.text.strip()])
                        summary_spans = coalesce_spans([x for x in spans_inside(summaries[0],parser.spans) if x.text.strip()])
                        self.assertEqual(len(title_spans),1)
                        self.assertEqual(len(summary_spans),1)
                        item = {"title":unescape(title_spans[0].text),"summary":unescape(summary_spans[0].text),"sources":[]}
                        anchors = select(source_containers[0],panel_spec["source_selector"])
                        for anchor in anchors:
                            anchor_spans = coalesce_spans([x for x in spans_inside(anchor,parser.spans) if x.text.strip()])
                            self.assertEqual(len(anchor_spans),1)
                            item["sources"].append({"url":anchor.attrs["href"],"text":unescape(anchor_spans[0].text)})
                        panel["items"].append(item)
                    news_data[panel_key] = panel
                news_binding = {"groups":{"news":spec}}
                self.assertEqual(render_market_html(source,{"groups":{},"news":news_data},news_binding),source,
                                 f"{label}: news no-op must preserve every byte")

    def test_real_dual_masters_economic_calendar_noop_preserves_every_byte(self):
        binding = json.loads((ROOT / "scripts/tac_html_binding_map.json").read_text(encoding="utf-8"))
        spec = binding["groups"]["economic_calendar"]
        selectors = spec["selectors"]
        for label, relative in binding["templates"].items():
            with self.subTest(template=label):
                source = (ROOT / relative).read_text(encoding="utf-8")
                parser = SourceTreeParser(source)
                parser.feed(source)
                parser.close()
                panels = {}
                for panel_key, panel_spec in spec["panels"].items():
                    containers = select(parser.root,panel_spec["container"])
                    if not containers:
                        continue
                    self.assertEqual(len(containers),1)
                    items = []
                    for event in select(containers[0],panel_spec["event_selector"]):
                        def one_text(selector):
                            nodes = select(event,selector)
                            self.assertEqual(len(nodes),1)
                            spans = coalesce_spans([x for x in spans_inside(nodes[0],parser.spans) if x.text.strip()])
                            self.assertEqual(len(spans),1)
                            return unescape(spans[0].text)
                        name = one_text(selectors["name"])
                        item = {"expected_name":name,"date":one_text(selectors["date"]),
                                "time":one_text(selectors["time"]),"country":one_text(selectors["country"]),
                                "name":name,"stars_text":one_text(selectors["stars"]),"fields":[]}
                        detail = select(event,selectors["details"])
                        self.assertEqual(len(detail),1)
                        for field in select(detail[0],selectors["field"]):
                            labels = select(field,selectors["field_label"])
                            values = select(field,selectors["field_value"])
                            self.assertEqual(len(labels),1)
                            self.assertEqual(len(values),1)
                            label_text = unescape("".join(x.text for x in spans_inside(labels[0],parser.spans))).strip()
                            anchors = select(values[0],selectors["source_link"])
                            if anchors:
                                links=[]
                                for anchor in anchors:
                                    spans=coalesce_spans([x for x in spans_inside(anchor,parser.spans) if x.text.strip()])
                                    self.assertEqual(len(spans),1)
                                    links.append({"url":anchor.attrs["href"],"text":unescape(spans[0].text)})
                                item["fields"].append({"label":label_text,"links":links})
                            else:
                                spans=coalesce_spans([x for x in spans_inside(values[0],parser.spans) if x.text.strip()])
                                self.assertEqual(len(spans),1,f"{label}.{panel_key}.{name}.{label_text}")
                                item["fields"].append({"label":label_text,"text":unescape(spans[0].text)})
                        items.append(item)
                    panels[panel_key]={"items":items}
                calendar_binding={"groups":{"economic_calendar":spec}}
                self.assertEqual(render_market_html(source,{"groups":{},"economic_calendar":{"panels":panels}},calendar_binding),source,
                                 f"{label}: economic calendar no-op must preserve every byte")

    def test_real_dual_masters_earnings_calendar_noop_preserves_every_byte(self):
        binding = json.loads((ROOT / "scripts/tac_html_binding_map.json").read_text(encoding="utf-8"))
        spec = binding["groups"]["earnings_calendar"]
        sel = spec["selectors"]
        for template_label, relative in binding["templates"].items():
            with self.subTest(template=template_label):
                source = (ROOT / relative).read_text(encoding="utf-8")
                parser = SourceTreeParser(source)
                parser.feed(source)
                parser.close()
                panels={}
                for panel_key,panel_spec in spec["panels"].items():
                    containers=select(parser.root,panel_spec["container"])
                    if not containers:
                        continue
                    self.assertEqual(len(containers),1)
                    items=[]
                    for accordion in select(containers[0],panel_spec["item_selector"]):
                        def one(selector,root=accordion):
                            nodes=select(root,selector)
                            self.assertEqual(len(nodes),1,f"{template_label}.{panel_key}.{selector}")
                            spans=coalesce_spans([x for x in spans_inside(nodes[0],parser.spans) if x.text.strip()])
                            self.assertEqual(len(spans),1,f"{template_label}.{panel_key}.{selector} text")
                            return unescape(spans[0].text)
                        company=one(sel["company"])
                        item={"expected_company":company,"us_date":one(sel["us_date"]),"tw_date":one(sel["tw_date"]),
                              "company":company,"company_sub":one(sel["company_sub"]),"stars_text":one(sel["stars"]),
                              "fields":[],"results":[]}
                        details=select(accordion,sel["details"])
                        self.assertEqual(len(details),1)
                        for field in select(details[0],sel["detail_field"]):
                            labels=select(field,sel["detail_label"]); values=select(field,sel["detail_value"])
                            self.assertEqual(len(labels),1); self.assertEqual(len(values),1)
                            field_label=unescape("".join(x.text for x in spans_inside(labels[0],parser.spans))).strip()
                            anchors=select(values[0],"a")
                            if anchors:
                                links=[]
                                for anchor in anchors:
                                    spans=coalesce_spans([x for x in spans_inside(anchor,parser.spans) if x.text.strip()])
                                    self.assertEqual(len(spans),1)
                                    links.append({"url":anchor.attrs["href"],"text":unescape(spans[0].text)})
                                item["fields"].append({"label":field_label,"links":links})
                            else:
                                spans=coalesce_spans([x for x in spans_inside(values[0],parser.spans) if x.text.strip()])
                                self.assertEqual(len(spans),1,f"{template_label}.{company}.{field_label}")
                                item["fields"].append({"label":field_label,"text":unescape(spans[0].text)})
                        for card in select(details[0],sel["result_card"]):
                            title=one(sel["result_title"],card)
                            lines=select(card,sel["result_line"])
                            self.assertEqual(len(lines),2)
                            line_values=[]
                            for line in lines:
                                spans=select(line,"strong")
                                self.assertEqual(len(spans),1)
                                line_values.append(unescape("".join(x.text for x in spans_inside(spans[0],parser.spans))).strip())
                            status=one(sel["result_status"],card)
                            note=one(sel["result_note"],card)
                            card_classes=card.classes.intersection({"beat","miss","pending"})
                            status_nodes=select(card,sel["result_status"])
                            self.assertEqual(len(card_classes),1)
                            self.assertEqual(len(status_nodes),1)
                            status_classes=status_nodes[0].classes.intersection({"beat","miss","pending"})
                            self.assertEqual(len(status_classes),1)
                            item["results"].append({"title":title,"actual":line_values[0],"expected":line_values[1],
                                                    "status_text":status,"card_class":next(iter(card_classes)),
                                                    "status_class":next(iter(status_classes)),"note":note})
                        items.append(item)
                    panels[panel_key]={"items":items}
                earnings_binding={"groups":{"earnings_calendar":spec}}
                self.assertEqual(render_market_html(source,{"groups":{},"earnings_calendar":{"panels":panels}},earnings_binding),source,
                                 f"{template_label}: earnings no-op must preserve every byte")

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
