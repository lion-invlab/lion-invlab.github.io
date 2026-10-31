import unittest

from tac_template_structure_fingerprint import inspect_html, compare

class FingerprintTests(unittest.TestCase):
    def test_daily_text_and_links_are_ignored(self):
        a = inspect_html('<main id="x"><a href="/old">Old</a></main>')
        b = inspect_html('<main id="x"><a href="/new">New</a></main>')
        self.assertTrue(compare(a, b)["pass"])

    def test_class_change_fails(self):
        a = inspect_html('<main id="x" class="card"></main>')
        b = inspect_html('<main id="x" class="panel"></main>')
        self.assertFalse(compare(a, b)["checks"]["fixed_dom_structure_equal"])

    def test_inline_script_change_fails(self):
        a = inspect_html('<script>const x = 1;</script>')
        b = inspect_html('<script>const x = 2;</script>')
        self.assertFalse(compare(a, b)["checks"]["inline_css_js_equal"])

    def test_duplicate_ids_are_reported(self):
        result = inspect_html('<div id="dup"></div><p id="dup"></p>')
        self.assertEqual(result["duplicate_ids"], ["dup"])

    def test_unclosed_tags_fail_closed(self):
        result = inspect_html('<main><section></main>')
        self.assertTrue(result["parse_warnings"])

    def test_void_elements_do_not_remain_open(self):
        result = inspect_html('<main><input id="choice"><p>ok</p></main>')
        self.assertEqual(result["parse_warnings"], [])

if __name__ == "__main__":
    unittest.main()
