"""Gate for the Claude memo (plan test 9): no number may appear that is not in the input. Offline."""
from memo import numbers_in_input, unsupported_numbers


INPUT = {
    "city_a": {"name": "City A", "median_months": 14.5, "n": 22},
    "city_b": {"name": "City B", "median_months": 24.5, "n": 31},
    "difference_per_home": 81000,
    "gap_multiplier": 6.96,
}


def test_memo_using_only_input_numbers_passes():
    memo = (
        "City A's median is 14.5 months across 22 projects; City B's is 24.5 months across 31. "
        "Choosing City A saves about $81,000 per home, a 6.96x gap multiplier."
    )
    assert unsupported_numbers(memo, INPUT) == []


def test_memo_with_invented_number_fails():
    memo = "City A's median is 14.5 months, and fees run $12,500 higher in City B."
    assert unsupported_numbers(memo, INPUT) == ["12500"]


def test_numbers_extracted_from_nested_input():
    assert {"14.5", "22", "24.5", "31", "81000", "6.96"} <= numbers_in_input(INPUT)
