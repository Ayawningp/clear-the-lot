"""End-to-end: committed OC sample -> projects -> per-city stage summaries.
Run `python pipeline.py` to print match rates and project counts."""
from pathlib import Path

import pandas as pd

from clean import clean_a, clean_a2
from stitch import attach_applications, match_rate, ownership_rows, stitch
from timelines import pooled_baseline, summarize

ROOT = Path(__file__).parent
SAMPLE = ROOT / "data" / "sample"
DATA_PULLED = "2026-11-07"    # date the team downloaded the APR CSVs from data.ca.gov


def load_raw():
    a = pd.read_csv(SAMPLE / "oc_tablea.csv", dtype=str, keep_default_na=False)
    a2 = pd.read_csv(SAMPLE / "oc_tablea2.csv", dtype=str, keep_default_na=False)
    return a, a2


def build(min_units: int = 1, max_units: int = 10_000):
    a_raw, a2_raw = load_raw()
    a, a2 = clean_a(a_raw), clean_a2(a2_raw)
    latest_year = int(a2["year"].max())
    data_end = pd.Timestamp(f"{latest_year}-12-31")

    owned = ownership_rows(a2)
    projects = attach_applications(stitch(owned), a)
    projects = projects[(projects["units"] >= min_units) & (projects["units"] <= max_units)]
    summary = summarize(projects, data_end=data_end)
    # countywide pool: every OC approval batch, used as the "typical" baseline in receipts
    county = pooled_baseline(projects)
    summary_split = summarize(projects, data_end=data_end, by=("city", "streamlined"))
    return {
        "projects": projects,
        "summary": summary,
        "county": county,
        "summary_split": summary_split,
        "match": match_rate(projects),
        "data_end": data_end,
        "latest_year": latest_year,
        "rows_a2": len(a2), "rows_owned": len(owned), "rows_a": len(a),
    }


if __name__ == "__main__":
    pd.set_option("display.width", 200, "display.max_rows", 200)
    r = build()
    p = r["projects"]
    print("A2 rows:", r["rows_a2"], " ownership non-ADU rows:", r["rows_owned"], " projects:", len(p))
    print("match:", r["match"])
    print("app join rate:", round((p["app_date"].notna()).mean(), 3),
          " streamlined projects:", int(p["streamlined"].sum()))
    print("conflict rate:", round(p["conflict"].mean(), 3), " order issues:", int(p["order_issue"].sum()))
    print("\nunits per project:\n", p["units"].describe())
    s = r["summary"]
    piv = s.pivot_table(index="city", columns="stage", values="n", aggfunc="sum", fill_value=0)
    print("\nfinished durations per city/stage:\n", piv.sort_values("ent_bp", ascending=False))
