"""The Delay Receipt: Streamlit screens.

Run:  streamlit run app.py
Reads data/processed/durations.csv when stitch.py has produced it; otherwise the MOCK sample.
"""
from pathlib import Path

import pandas as pd
import streamlit as st

from memo import LIMITATIONS, generate_memo, unsupported_numbers
from receipt import (
    DEFAULT_C, DEFAULT_G0, STAGE_NAMES, STAGES, Assumptions, city_difference, extra_cost,
    gap_after, gap_multiplier, money, receipt_lines,
)
from timelines import stage_months, summarize

REAL_PATH = Path("data/processed/durations.csv")
MOCK_PATH = Path("data/sample/mock_durations.csv")
BACKUP_MEMO = Path("data/sample/memo_backup.md")
SOURCES = [
    ("HCD Housing Element Annual Progress Report data (Tables A and A2), data.ca.gov",
     "https://data.ca.gov/dataset/housing-element-annual-progress-report-apr-data-by-jurisdiction-and-year"),
    ("HCD APR instructions (date fields; dates reported only in the year they happen)",
     "https://www.hcd.ca.gov/sites/default/files/docs/planning-and-community/housing-element-annual-progress-report-instructions.pdf"),
    ("Claude Impact Lab worked example (SYNTHETIC deal: $95k gap, 10-month slip, about 7x)",
     "https://github.com/travcjohnson/claude-impact-lab-uci/blob/main/docs/background.md"),
]

st.set_page_config(page_title="Delay Receipt", layout="wide")


@st.cache_data
def load(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


@st.cache_data
def summary_for(df: pd.DataFrame) -> pd.DataFrame:
    return summarize(df, n_boot=2000, seed=0)


is_mock = not REAL_PATH.exists()
durations = load(str(MOCK_PATH if is_mock else REAL_PATH))
summary = summary_for(durations)
cities = sorted(summary["city"].unique())

st.title("The Delay Receipt")
st.caption("Waiting doesn't raise the price much. It multiplies the gap.")
st.warning("Prototype, not legal or financial advice. Dollar figures are assumptions, labeled ASSUMPTION.")
if is_mock:
    st.error("MOCK DATA: cities and timelines are invented so the screens can be built. "
             "Real data loads from data/processed/durations.csv once it exists.")

# ---- Sidebar: assumptions -------------------------------------------------------------------
st.sidebar.header("Assumptions")
st.sidebar.caption("Defaults come from the event's synthetic worked example. Edit them for your project.")
c = st.sidebar.number_input("Monthly carrying cost per home, loan drawn ($) — ASSUMPTION",
                            min_value=0, value=DEFAULT_C, step=100)
loan_drawn = st.sidebar.checkbox("Construction loan already drawn before permit", value=True)
c0 = st.sidebar.number_input("Monthly cost per home before the loan is drawn ($) — ASSUMPTION",
                             min_value=0, value=DEFAULT_C, step=100, disabled=loan_drawn)
g0 = st.sidebar.number_input("Gap per home with no extra delay ($) — ASSUMPTION",
                             min_value=1, value=DEFAULT_G0, step=100)
units = st.sidebar.number_input("Homes in the project", min_value=1, value=8, step=1)
a = Assumptions(c=c, c0=c0, g0=g0, units=units, loan_drawn=loan_drawn)

city_a = st.sidebar.selectbox("City A", cities, index=0)
city_b = st.sidebar.selectbox("City B", cities, index=min(1, len(cities) - 1))

totals = {city: sum(stage_months(summary, city)[0].values()) for city in cities}
fastest = min(cities, key=lambda city: totals[city])
baseline_name = st.sidebar.selectbox(
    "Baseline: the schedule your gap assumes", cities, index=cities.index(fastest),
    help="Your no-extra-delay gap already includes this schedule's waiting. "
         "Only months beyond it are added. Default: the fastest city in the data.")
baseline_months, baseline_unknown = stage_months(summary, baseline_name)


def stage_table(city: str) -> pd.DataFrame:
    rows = summary[summary["city"] == city].set_index("stage").reindex(list(STAGES))
    return pd.DataFrame({
        "Stage": [STAGE_NAMES[s] for s in STAGES],
        "Median months": [("unknown" if pd.isna(m) else f"{m:.1f}") for m in rows["median"]],
        "90% interval": [("—" if pd.isna(lo) else f"{lo:.1f} to {hi:.1f}")
                         for lo, hi in zip(rows["ci_low"], rows["ci_high"])],
        "Projects finished": rows["n_done"].fillna(0).astype(int).to_list(),
        "No further activity reported": rows["n_waiting"].fillna(0).astype(int).to_list(),
        "Evidence": rows["label"].fillna("Insufficient evidence").to_list(),
    })


def show_receipt(city: str) -> tuple[dict, list]:
    months, unknown = stage_months(summary, city)
    st.subheader(city)
    st.metric(f"Gap multiplier vs {baseline_name} (ASSUMPTION)",
              f"{gap_multiplier(months, baseline_months, a):.1f}x",
              help="(gap on the baseline schedule + extra waiting cost) / gap on the baseline schedule")
    for line in receipt_lines(months, baseline_months, baseline_name, a):
        st.write(line)
    missing = sorted(set(unknown) | set(baseline_unknown))
    if missing:
        st.info("Partial receipt: " + ", ".join(STAGE_NAMES[s] for s in missing)
                + " has too little evidence in this city or the baseline and is left out of the totals.")
    return months, unknown


tab_t, tab_r, tab_c, tab_l = st.tabs(["Timelines", "Receipt", "Compare", "Limitations"])

with tab_t:
    st.header("How long does it really take?")
    st.caption("Median months per stage for owner-occupied projects. Medians count finished projects only, "
               "so they run short when many projects show no further activity.")
    for city in (city_a, city_b):
        st.subheader(city)
        st.dataframe(stage_table(city), hide_index=True)
    chart = (summary[summary["city"].isin([city_a, city_b])]
             .assign(Stage=lambda d: d["stage"].map(STAGE_NAMES))
             .pivot(index="Stage", columns="city", values="median"))
    st.bar_chart(chart)

with tab_r:
    st.header("The receipt")
    show_receipt(city_a)

with tab_c:
    st.header("Side by side")
    left, right = st.columns(2)
    with left:
        months_a, unknown_a = show_receipt(city_a)
    with right:
        months_b, unknown_b = show_receipt(city_b)
    per_home, per_project = city_difference(months_a, months_b, a)
    cheaper, dearer = (city_a, city_b) if per_home >= 0 else (city_b, city_a)
    st.success(f"Choosing {cheaper} over {dearer} avoids about {money(abs(per_home))} per home "
               f"and {money(abs(per_project))} for {units} homes in waiting costs.")
    if unknown_a or unknown_b:
        st.info("At least one stage is unknown, so this difference is partial.")

    st.subheader("Board memo (Claude)")
    payload = {
        "data_is_mock": is_mock,
        "cities": {
            city: {
                "stages": stage_table(city).to_dict(orient="records"),
                "extra_waiting_cost_per_home_vs_baseline_assumption": round(extra_cost(months, baseline_months, a)),
                "gap_per_home_assumption": round(gap_after(months, baseline_months, a)),
                "gap_multiplier_vs_baseline_assumption": round(gap_multiplier(months, baseline_months, a), 1),
            }
            for city, months in ((city_a, months_a), (city_b, months_b))
        },
        "difference_per_home_assumption": round(abs(per_home)),
        "difference_per_project_assumption": round(abs(per_project)),
        "lower_cost_city": cheaper,
        "baseline_city": baseline_name,
        "assumptions": {"monthly_cost_loan_drawn": c, "monthly_cost_before_loan": c0,
                        "loan_drawn": loan_drawn, "gap_with_no_extra_delay": g0, "homes": units},
        "limitations": LIMITATIONS,
    }
    if st.button("Write the memo with Claude"):
        memo = generate_memo(payload)
        bad = unsupported_numbers(memo, payload)
        if bad:
            st.error(f"Guard: the memo used numbers not in our data ({', '.join(bad)}). Check before sharing.")
        st.markdown(memo)
    if BACKUP_MEMO.exists() and st.button("Show the saved backup memo"):
        st.markdown(BACKUP_MEMO.read_text())

with tab_l:
    st.header("What this can't tell you")
    for item in LIMITATIONS:
        st.write("- " + item)
    if is_mock:
        st.write("- **The data on these screens is MOCK.**")
    st.subheader("Sources")
    for name, url in SOURCES:
        st.markdown(f"- [{name}]({url})")
