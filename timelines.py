"""Timeline summaries per city and stage.

Input contract (what stitch.py must produce, one row per project per stage):
    city        str    jurisdiction name
    project_id  str    stitched project key
    stage       str    one of receipt.STAGES
    months      float  duration in months; NaN when status == "waiting"
    status      str    "done" (both dates known) or "waiting" (start date known, no end date yet)

Medians use finished projects only, so they are biased short when many projects are still waiting.
The waiting count is reported next to every median for that reason.
"""
import numpy as np
import pandas as pd

from receipt import STAGES

REQUIRED_COLUMNS = ("city", "project_id", "stage", "months", "status")
MIN_N_FOR_MEDIAN = 10


def sample_label(n: int) -> str:
    if n < 10:
        return "Insufficient evidence"
    if n < 20:
        return "Preliminary"
    if n < 30:
        return "Moderate"
    return "More reliable"


def bootstrap_median_ci(values: np.ndarray, n_boot: int, seed: int, level: float = 0.90) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    draws = rng.choice(values, size=(n_boot, len(values)), replace=True)
    medians = np.median(draws, axis=1)
    tail = (1 - level) / 2
    return float(np.quantile(medians, tail)), float(np.quantile(medians, 1 - tail))


def summarize(df: pd.DataFrame, n_boot: int = 2000, seed: int = 0) -> pd.DataFrame:
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")
    done = df[df["status"] == "done"]
    if (done["months"] < 0).any():
        raise ValueError("negative durations found; stitch.py must flag and exclude out-of-order dates")
    if done["months"].isna().any():
        raise ValueError("'done' rows must have a duration")

    rows = []
    for (city, stage), group in df.groupby(["city", "stage"], sort=True):
        values = group.loc[group["status"] == "done", "months"].to_numpy(dtype=float)
        n_done = len(values)
        n_waiting = int((group["status"] == "waiting").sum())
        median = ci_low = ci_high = np.nan
        if n_done >= MIN_N_FOR_MEDIAN:
            median = float(np.median(values))
            ci_low, ci_high = bootstrap_median_ci(values, n_boot, seed)
        rows.append({
            "city": city, "stage": stage, "n_done": n_done, "n_waiting": n_waiting,
            "median": median, "ci_low": ci_low, "ci_high": ci_high, "label": sample_label(n_done),
        })
    return pd.DataFrame(rows)


def stage_months(summary: pd.DataFrame, city: str) -> tuple[dict, list]:
    """Median months per stage for one city, for the receipt.

    A stage with no median (insufficient evidence, or absent) counts as 0 months in the totals and is
    listed in `unknown`, so the screens can say the receipt is partial instead of hiding it.
    """
    city_rows = summary[summary["city"] == city].set_index("stage")
    months, unknown = {}, []
    for stage in STAGES:
        if stage in city_rows.index and not pd.isna(city_rows.loc[stage, "median"]):
            months[stage] = float(city_rows.loc[stage, "median"])
        else:
            months[stage] = 0.0
            unknown.append(stage)
    return months, unknown
