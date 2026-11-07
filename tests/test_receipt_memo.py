"""Gates 7, 8, 9: receipt math, ASSUMPTION labels, memo guard (mocked Claude, no network)."""
import re

from receipt import DEFAULTS, receipt, receipt_lines, city_difference
from memo import guard, generate_memo


# 7. Receipt math
def test_receipt_math_matches_worked_example():
    r = receipt({"ent_bp": 10.0}, c=8100, c0=8100, g0=13600, units=1)
    assert abs(r["delay_cost"] - 81000) < 1
    assert abs(r["gap_after"] - 94600) < 1          # "about $95k"
    assert 6.5 < r["multiplier"] < 7.5             # "about 7x"


def test_defaults_are_the_derived_assumptions():
    assert DEFAULTS["g0"]["value"] == 13600
    assert DEFAULTS["c"]["value"] == 8100
    assert all("ASSUMPTION" in v["label"] for v in DEFAULTS.values())


def test_loan_not_drawn_uses_c0_before_permit():
    r = receipt({"app_ent": 4.0, "ent_bp": 6.0, "bp_co": 10.0},
                c=8100, c0=2000, g0=13600, units=1, loan_not_drawn=True)
    assert abs(r["delay_cost"] - (4 * 2000 + 6 * 2000 + 10 * 8100)) < 1


def test_project_totals_scale_with_units():
    r = receipt({"ent_bp": 10.0}, c=8100, c0=8100, g0=13600, units=6)
    assert abs(r["delay_cost_project"] - 6 * 81000) < 1


def test_baseline_charges_only_extra_months():
    r = receipt({"ent_bp": 16.0}, c=8100, c0=8100, g0=13600, units=1, baseline={"ent_bp": 6.0})
    assert abs(r["delay_cost"] - 81000) < 1
    fast = receipt({"ent_bp": 4.0}, c=8100, c0=8100, g0=13600, units=1, baseline={"ent_bp": 6.0})
    assert fast["delay_cost"] < 0 and fast["multiplier"] < 1


def test_receipt_lines_tag_baseline_lines():
    r = receipt({"ent_bp": 16.0}, c=8100, c0=8100, g0=13600, units=2, baseline={"ent_bp": 6.0})
    for line in receipt_lines(r):
        for m in MONEY.finditer(line):
            assert "ASSUMPTION" in line[m.end():m.end() + 20], line


def test_city_difference():
    assert abs(city_difference(6.0, 16.0, c=8100) - 81000) < 1


# 8. Labels
MONEY = re.compile(r"\$\s?[\d,]+(?:\.\d+)?[kM]?")


def test_every_dollar_figure_is_tagged():
    r = receipt({"app_ent": 4.0, "ent_bp": 6.0, "bp_co": 10.0},
                c=8100, c0=2000, g0=13600, units=6, loan_not_drawn=True)
    lines = receipt_lines(r)
    assert lines
    for line in lines:
        for m in MONEY.finditer(line):
            tail = line[m.end():m.end() + 20]
            assert "ASSUMPTION" in tail, f"untagged dollar figure in: {line!r}"


# 9. Memo guard
INPUT = {
    "city_a": {"name": "TESTVILLE", "ent_bp_median_months": 6.2, "n": 14},
    "city_b": {"name": "OTHERTOWN", "ent_bp_median_months": 11.5, "n": 22},
    "receipt": {"difference_per_home": 43470, "gap_multiplier": 4.2},
    "assumptions": {"c": 8100, "g0": 13600},
    "limitations": ["No cancellation data.", "SB 35 split may be incomplete."],
}


def test_guard_passes_memo_using_only_input_numbers():
    memo = ("TESTVILLE: median 6.2 months (n=14). OTHERTOWN: 11.5 months (n=22). "
            "Choosing TESTVILLE saves about $43.5k per home (ASSUMPTION: $8.1k per month). "
            "The gap grows 4.2x. SB 35 split may be incomplete.\n"
            "Prototype, not legal or financial advice.")
    ok, bad = guard(memo, INPUT)
    assert ok, bad


def test_guard_rejects_invented_number():
    memo = ("TESTVILLE: median 6.2 months. Permits cost $250k in fees in OTHERTOWN.\n"
            "Prototype, not legal or financial advice.")
    ok, bad = guard(memo, INPUT)
    assert not ok
    assert any("250" in b for b in bad)


class _FakeClient:
    """Stands in for anthropic.Anthropic; returns a fixed response, no network."""
    def __init__(self, text):
        self._text = text
        self.messages = self
        self.beta = self

    def create(self, **kwargs):
        class _Block:
            type = "text"
        b = _Block()
        b.text = self._text

        class _Resp:
            content = [b]
        return _Resp()


def test_generate_memo_with_mocked_client_runs_guard():
    bad_text = "OTHERTOWN takes 19 months.\nPrototype, not legal or financial advice."
    result = generate_memo(INPUT, client=_FakeClient(bad_text))
    assert result["guard_ok"] is False
    good_text = "OTHERTOWN takes 11.5 months (n=22).\nPrototype, not legal or financial advice."
    result = generate_memo(INPUT, client=_FakeClient(good_text))
    assert result["guard_ok"] is True
