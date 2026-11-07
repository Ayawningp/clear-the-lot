"""MOCK durations so the screens run before real data is stitched.

Every value here is invented. City names carry "(MOCK)" so they can never be mistaken for real
Orange County cities. Replace with data/processed/durations.csv from stitch.py.
"""
import numpy as np
import pandas as pd

from receipt import STAGES
from timelines import REQUIRED_COLUMNS

# (city, stage) -> (typical months, projects finished, projects still waiting). All invented.
MOCK_SPEC = {
    ("City A (MOCK)", "app_to_ent"): (8, 24, 3),
    ("City A (MOCK)", "ent_to_permit"): (7, 22, 4),
    ("City A (MOCK)", "permit_to_co"): (13, 20, 6),
    ("City B (MOCK)", "app_to_ent"): (14, 31, 6),
    ("City B (MOCK)", "ent_to_permit"): (11, 27, 8),
    ("City B (MOCK)", "permit_to_co"): (14, 12, 9),
}


def make_mock_durations(seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for (city, stage), (typical, n_done, n_waiting) in MOCK_SPEC.items():
        months = rng.lognormal(mean=np.log(typical), sigma=0.35, size=n_done).round(1)
        for i, m in enumerate(months):
            rows.append({"city": city, "project_id": f"{city}|{stage}|{i}", "stage": stage,
                         "months": float(m), "status": "done"})
        for i in range(n_waiting):
            rows.append({"city": city, "project_id": f"{city}|{stage}|w{i}", "stage": stage,
                         "months": np.nan, "status": "waiting"})
    df = pd.DataFrame(rows, columns=list(REQUIRED_COLUMNS))
    assert set(df["stage"]) == set(STAGES)
    return df


if __name__ == "__main__":
    out = "data/sample/mock_durations.csv"
    make_mock_durations(seed=0).to_csv(out, index=False)
    print(f"wrote {out}")
