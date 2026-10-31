import unittest

from tac_repeat_group_validator import GroupSpec, validate_repeat_groups


SPEC = GroupSpec("economic", "#calendar .event-list", ".event-card")


def page(cards, extra="", wrapper_class="event-list"):
    return (
        '<!doctype html><html><head><style>.card{}</style>'
        '<script>window.keep=true;</script></head><body>'
        '<main id="report"><section id="calendar"><h2>經濟行事曆</h2>'
        f'<div class="{wrapper_class}"><h3>即將公布</h3>{cards}{extra}</div>'
        '</section><button id="plus" aria-label="新增">＋</button></main>'
        '</body></html>'
    )


def card(name="CPI", extra_class=""):
    return (
        f'<article class="event-card {extra_class}".strip()>'
        '<details><summary>日期與事件</summary>'
        f'<p>{name}</p><div class="source">來源</div></details></article>'
    ).replace('class="event-card ".strip()"', 'class="event-card"')


class RepeatGroupValidatorTests(unittest.TestCase):
    def test_exact_clone_can_be_added(self):
        baseline = page(card("CPI"))
        candidate = page(card("CPI") + card("PCE"))
        self.assertTrue(validate_repeat_groups(baseline, candidate, [SPEC])["pass"])

    def test_card_can_be_removed(self):
        baseline = page(card("CPI") + card("PCE"))
        candidate = page(card("CPI"))
        self.assertTrue(validate_repeat_groups(baseline, candidate, [SPEC])["pass"])

    def test_zero_cards_allowed_when_wrapper_remains(self):
        baseline = page(card("CPI"))
        candidate = page("")
        self.assertTrue(validate_repeat_groups(baseline, candidate, [SPEC])["pass"])

    def test_altered_card_class_fails(self):
        baseline = page(card("CPI"))
        candidate = page(card("CPI", "changed"))
        self.assertFalse(validate_repeat_groups(baseline, candidate, [SPEC])["pass"])

    def test_wrapper_change_fails(self):
        baseline = page(card("CPI"))
        candidate = page(card("CPI"), wrapper_class="different")
        self.assertFalse(validate_repeat_groups(baseline, candidate, [SPEC])["pass"])

    def test_fixed_sibling_change_fails(self):
        baseline = page(card("CPI"))
        candidate = page(card("CPI"), extra='<button class="new-control">+</button>')
        self.assertFalse(validate_repeat_groups(baseline, candidate, [SPEC])["pass"])

    def test_wrapper_count_change_fails(self):
        baseline = page(card("CPI"))
        candidate = page(card("CPI")).replace(
            '<div class="event-list"><h3>即將公布</h3>',
            '<div class="event-list"><h3>即將公布</h3><div class="event-list"><h3>第二組</h3>'
        ).replace('</div></section>', '</div></div></section>')
        result = validate_repeat_groups(baseline, candidate, [SPEC])
        self.assertFalse(result["groups"]["economic"]["wrapper_count_equal"])

    def test_non_variable_group_cannot_change_count(self):
        baseline = page(card("CPI"))
        candidate = page(card("CPI") + card("PCE"))
        fixed = GroupSpec("economic", "#calendar .event-list", ".event-card", False)
        self.assertFalse(validate_repeat_groups(baseline, candidate, [fixed])["pass"])


if __name__ == "__main__":
    unittest.main()
