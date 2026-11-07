"""Gates for the receipt math (plan tests 7 and 8)."""
import pytest

from receipt import (
    Assumptions,
    city_difference,
    delay_cost,
    extra_cost,
    gap_after,
    gap_multiplier,
    money,
    receipt_lines,
)

ZERO = {"app_to_ent": 0, "ent_to_permit": 0, "permit_to_co": 0}


def defaults():
    return Assumptions(c=8_100, c0=4_000, g0=13_600, units=8, loan_drawn=True)


def test_worked_example_reproduces_about_7x():
    a = defaults()
    months = {"app_to_ent": 0, "ent_to_permit": 10, "permit_to_co": 0}
    # the worked example: 10 months beyond the schedule the $13.6k gap assumes
    assert extra_cost(months, ZERO, a) == pytest.approx(81_000)
    assert gap_after(months, ZERO, a) == pytest.approx(94_600)
    assert gap_multiplier(months, ZERO, a) == pytest.approx(94_600 / 13_600)
    assert 6.9 < gap_multiplier(months, ZERO, a) < 7.0


def test_baseline_waiting_is_not_charged_twice():
    a = defaults()
    baseline = {"app_to_ent": 8, "ent_to_permit": 7, "permit_to_co": 14}
    assert extra_cost(baseline, baseline, a) == pytest.approx(0)
    assert gap_multiplier(baseline, baseline, a) == pytest.approx(1.0)


def test_faster_than_baseline_shrinks_the_gap():
    a = defaults()
    baseline = {"app_to_ent": 8, "ent_to_permit": 7, "permit_to_co": 14}
    faster = {"app_to_ent": 6, "ent_to_permit": 7, "permit_to_co": 14}
    assert extra_cost(faster, baseline, a) == pytest.approx(-2 * 8_100)
    assert gap_multiplier(faster, baseline, a) < 1.0


def test_loan_not_drawn_uses_c0_before_permit_only():
    a = Assumptions(c=8_100, c0=4_000, g0=13_600, units=1, loan_drawn=False)
    months = {"app_to_ent": 2, "ent_to_permit": 3, "permit_to_co": 4}
    # pre-permit stages at c0, construction stage at c
    assert delay_cost(months, a) == pytest.approx(5 * 4_000 + 4 * 8_100)


def test_city_difference_per_home_and_project():
    a = defaults()
    months_a = {"app_to_ent": 8, "ent_to_permit": 6, "permit_to_co": 6}
    months_b = {"app_to_ent": 12, "ent_to_permit": 12, "permit_to_co": 6}
    per_home, per_project = city_difference(months_a, months_b, a)
    assert per_home == pytest.approx(81_000)
    assert per_project == pytest.approx(81_000 * 8)


def test_city_difference_respects_loan_not_drawn():
    a = Assumptions(c=8_100, c0=4_000, g0=13_600, units=2, loan_drawn=False)
    months_a = {"app_to_ent": 0, "ent_to_permit": 0, "permit_to_co": 0}
    months_b = {"app_to_ent": 5, "ent_to_permit": 0, "permit_to_co": 0}
    per_home, per_project = city_difference(months_a, months_b, a)
    assert per_home == pytest.approx(5 * 4_000)
    assert per_project == pytest.approx(5 * 4_000 * 2)


def test_negative_months_rejected():
    with pytest.raises(ValueError):
        delay_cost({"app_to_ent": -1, "ent_to_permit": 0, "permit_to_co": 0}, defaults())


def test_zero_gap_rejected_for_multiplier():
    a = Assumptions(c=8_100, c0=4_000, g0=0, units=1, loan_drawn=True)
    with pytest.raises(ValueError):
        gap_multiplier({"app_to_ent": 1, "ent_to_permit": 0, "permit_to_co": 0}, ZERO, a)


def test_money_always_tagged():
    assert money(81_000) == "$81,000 (ASSUMPTION)"


def test_every_receipt_line_with_dollars_is_tagged():
    lines = receipt_lines({"app_to_ent": 6, "ent_to_permit": 9, "permit_to_co": 12},
                          {"app_to_ent": 5, "ent_to_permit": 6, "permit_to_co": 12}, "City A", defaults())
    assert len(lines) >= 4
    for line in lines:
        if "$" in line:
            assert "ASSUMPTION" in line, line


def test_money_negative_sign_before_dollar():
    assert money(-8_100) == "-$8,100 (ASSUMPTION)"
