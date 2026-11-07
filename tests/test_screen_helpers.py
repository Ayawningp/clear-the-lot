"""Gates for the pieces the screens read: the mock dataset follows the contract, and stage months
from a summary treat 'Insufficient evidence' as unknown rather than zero waiting."""
import math

import pandas as pd

from mock_data import make_mock_durations
from receipt import STAGES
from timelines import REQUIRED_COLUMNS, stage_months, summarize


def test_mock_follows_contract_and_is_labelled():
    df = make_mock_durations(seed=0)
    assert list(df.columns) == list(REQUIRED_COLUMNS)
    assert set(df["stage"]) == set(STAGES)
    assert set(df["status"]) == {"done", "waiting"}
    assert all("MOCK" in c for c in df["city"].unique())
    assert df.loc[df["status"] == "waiting", "months"].isna().all()
    assert (df.loc[df["status"] == "done", "months"] >= 0).all()


def test_mock_is_deterministic():
    pd.testing.assert_frame_equal(make_mock_durations(seed=3), make_mock_durations(seed=3))


def test_stage_months_marks_insufficient_stages_unknown():
    summary = pd.DataFrame([
        {"city": "X", "stage": "app_to_ent", "n_done": 12, "n_waiting": 0, "median": 6.0,
         "ci_low": 5.0, "ci_high": 7.0, "label": "Preliminary"},
        {"city": "X", "stage": "ent_to_permit", "n_done": 4, "n_waiting": 2, "median": math.nan,
         "ci_low": math.nan, "ci_high": math.nan, "label": "Insufficient evidence"},
        {"city": "X", "stage": "permit_to_co", "n_done": 30, "n_waiting": 1, "median": 11.0,
         "ci_low": 10.0, "ci_high": 12.0, "label": "More reliable"},
    ])
    months, unknown = stage_months(summary, "X")
    assert months == {"app_to_ent": 6.0, "ent_to_permit": 0.0, "permit_to_co": 11.0}
    assert unknown == ["ent_to_permit"]


def test_stage_missing_from_summary_is_unknown():
    summary = summarize(make_mock_durations(seed=0), n_boot=100, seed=0)
    city = summary["city"].iloc[0]
    trimmed = summary[~((summary["city"] == city) & (summary["stage"] == "permit_to_co"))]
    months, unknown = stage_months(trimmed, city)
    assert "permit_to_co" in unknown and months["permit_to_co"] == 0.0
