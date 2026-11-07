"""Gates for timeline summaries (plan tests 5 and 6) and the data contract the screens read."""
import math

import pandas as pd
import pytest

from timelines import REQUIRED_COLUMNS, sample_label, summarize


def make(city, stage, done_months, n_waiting=0):
    rows = [
        {"city": city, "project_id": f"{city}-{stage}-{i}", "stage": stage, "months": m, "status": "done"}
        for i, m in enumerate(done_months)
    ]
    rows += [
        {"city": city, "project_id": f"{city}-{stage}-w{i}", "stage": stage, "months": math.nan, "status": "waiting"}
        for i in range(n_waiting)
    ]
    return pd.DataFrame(rows)


@pytest.mark.parametrize(
    "n,label",
    [(0, "Insufficient evidence"), (9, "Insufficient evidence"), (10, "Preliminary"),
     (19, "Preliminary"), (20, "Moderate"), (29, "Moderate"), (30, "More reliable")],
)
def test_sample_labels(n, label):
    assert sample_label(n) == label


def test_small_sample_shows_no_median():
    out = summarize(make("City A", "ent_to_permit", [5, 6, 7]), n_boot=200, seed=0)
    row = out.iloc[0]
    assert row["label"] == "Insufficient evidence"
    assert pd.isna(row["median"]) and pd.isna(row["ci_low"]) and pd.isna(row["ci_high"])
    assert row["n_done"] == 3


def test_waiting_projects_counted_not_used_as_durations():
    df = make("City A", "ent_to_permit", [10.0] * 12, n_waiting=5)
    row = summarize(df, n_boot=200, seed=0).iloc[0]
    assert row["n_done"] == 12
    assert row["n_waiting"] == 5
    assert row["median"] == pytest.approx(10.0)


def test_median_and_interval_ordered():
    df = make("City B", "app_to_ent", list(range(1, 25)))
    row = summarize(df, n_boot=500, seed=1).iloc[0]
    assert row["median"] == pytest.approx(12.5)
    assert row["ci_low"] <= row["median"] <= row["ci_high"]
    assert row["label"] == "Moderate"


def test_summary_is_deterministic_with_seed():
    df = make("City B", "app_to_ent", list(range(1, 25)))
    a = summarize(df, n_boot=300, seed=7)
    b = summarize(df, n_boot=300, seed=7)
    pd.testing.assert_frame_equal(a, b)


def test_negative_duration_rejected():
    df = make("City A", "ent_to_permit", [3, -1] + [4] * 10)
    with pytest.raises(ValueError):
        summarize(df, n_boot=100, seed=0)


def test_missing_columns_rejected():
    df = make("City A", "ent_to_permit", [3] * 10).drop(columns=["status"])
    with pytest.raises(ValueError):
        summarize(df, n_boot=100, seed=0)


def test_contract_columns():
    assert set(REQUIRED_COLUMNS) == {"city", "project_id", "stage", "months", "status"}
