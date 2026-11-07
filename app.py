"""Delay Receipt: Streamlit app. Run: streamlit run app.py"""
import math

import pandas as pd
import streamlit as st

from memo import LIMITATIONS, build_memo_input, generate_memo, load_backup
from pipeline import DATA_PULLED, build
from receipt import DEFAULTS, SUMMABLE, city_difference, money, receipt, receipt_lines
from timelines import STAGE_LABELS

st.set_page_config(page_title="Delay Receipt", layout="wide")

APR_URL = "https://data.ca.gov/dataset/housing-element-annual-progress-report-apr-data-by-jurisdiction-and-year"
HCD_URL = ("https://www.hcd.ca.gov/sites/default/files/docs/planning-and-community/"
           "housing-element-annual-progress-report-instructions.pdf")
DEAL = "claude-impact-lab-uci/lanes/3-fund-it/data/synthetic-example-deal.json"
EVENT_REPO = "https://github.com/travcjohnson/claude-impact-lab-uci"
SAME_DAY_WARN = 0.5


@st.cache_data(show_spinner="Stitching APR rows into projects...")
def load(min_units, max_units):
    return build(min_units=min_units, max_units=max_units)


# ---------------- sidebar ----------------
st.sidebar.header("Assumptions")
st.sidebar.caption("Every dollar figure is an ASSUMPTION. Defaults are derived from the event's "
                   f"synthetic worked example (`{DEAL}`). Edit them for your own deal.")
c = st.sidebar.number_input("c: carrying cost per home per month, loan drawn ($) — ASSUMPTION",
                            value=DEFAULTS["c"]["value"], step=100, min_value=0)
loan_not_drawn = st.sidebar.toggle("Construction loan not yet drawn before permit", value=False)
c0 = st.sidebar.number_input("c0: carrying cost per home per month before loan ($) — ASSUMPTION",
                             value=DEFAULTS["c0"]["value"], step=100, min_value=0,
                             disabled=not loan_not_drawn)
g0 = st.sidebar.number_input("G0: gap per home with no extra delay ($) — ASSUMPTION",
                             value=DEFAULTS["g0"]["value"], step=100, min_value=1)
units = st.sidebar.number_input("Homes in your project", value=6, step=1, min_value=1)
include_build = st.sidebar.toggle("Include permit → occupancy (mostly construction time)", value=False,
                                  help="Off by default: this stage is driven largely by the builder, "
                                       "not the city's approval process.")
STAGES_USED = ["app_ent", "ent_bp"] + (["bp_co"] if include_build else [])
st.sidebar.header("Comparison pool")
unit_range = st.sidebar.slider("Units per project (like-for-like filter)", 1, 200, (1, 200))
st.sidebar.caption("Owner tenure only. ADUs and rentals are always excluded.")

r = load(*unit_range)
summary, match = r["summary"], r["match"]
baseline = {s: v["median"] for s, v in r["county"].items() if not math.isnan(v["median"])}
data_end = r["data_end"].date().isoformat()
cities = sorted(summary["city"].unique())

# ---------------- header ----------------
st.title("Delay Receipt")
st.markdown("**Waiting barely raises the price of an affordable home. It multiplies the funding gap.**")
st.warning("Prototype, not legal or financial advice. Talk to a professional before making decisions.")


def fmt_stage_row(row):
    if row["n"] < 10:
        med = "Insufficient evidence"
        ci = "—"
    else:
        med = f"{row['median']:.1f}"
        ci = f"{row['ci_low']:.1f} – {row['ci_high']:.1f}"
    flag = ""
    if row["n"] >= 10 and row["same_day_share"] >= SAME_DAY_WARN:
        flag = f"⚠ {row['same_day_share']:.0%} same-day dates (reporting convention?)"
    return pd.Series({
        "City": row["city"].title(), "Stage": row["stage_label"], "Median months": med,
        "90% CI (months)": ci, "Approvals (n)": int(row["n"]), "Parcels": int(row["parcels_finished"]),
        "Evidence": row["label"], "Still waiting": int(row["still_waiting"]), "Note": flag,
    })


def stage_months(city):
    """Medians usable in a receipt: n >= 10 and not mostly same-day artifacts."""
    out, notes = {}, {}
    for _, row in summary[summary["city"] == city].iterrows():
        if row["stage"] not in SUMMABLE:
            continue
        if row["n"] < 10:
            notes[row["stage"]] = "insufficient evidence"
        elif row["same_day_share"] >= SAME_DAY_WARN:
            notes[row["stage"]] = "mostly same-day dates; not used"
        else:
            out[row["stage"]] = float(row["median"])
    return out, notes


tab_t, tab_r, tab_c, tab_l = st.tabs(["Timelines", "Receipt", "Compare", "Limitations"])

# ---------------- Timelines ----------------
with tab_t:
    m1, m2, m3 = st.columns(3)
    m1.metric("Ownership projects (parcels)", f"{match['projects']:,}")
    m2.metric("Cross-year match rate", f"{match['cross_year_rate']:.0%}",
              help="Share of projects whose rows were linked across two or more reporting years.")
    m3.metric("Data through", data_end)
    st.caption("Matched by: " + ", ".join(f"{k} {v:,}" for k, v in match["by_method"].items())
               + ". Counts are **approval batches**: parcels in one city sharing the same start date "
                 "count once, so a 300-lot subdivision is one data point, not 300.")
    default = [x for x in ["LAGUNA BEACH", "YORBA LINDA", "DANA POINT", "SAN JUAN CAPISTRANO",
                           "IRVINE", "ANAHEIM", "SANTA ANA", "FULLERTON", "HUNTINGTON BEACH"] if x in cities]
    pick = st.multiselect("Cities", cities, default=default, format_func=str.title)
    stage_pick = st.multiselect("Stages", list(STAGE_LABELS), default=list(STAGE_LABELS),
                                format_func=STAGE_LABELS.get)
    view = summary[summary["city"].isin(pick) & summary["stage"].isin(stage_pick)]
    if view.empty:
        st.info("No data for this selection.")
    else:
        st.dataframe(view.apply(fmt_stage_row, axis=1), hide_index=True, width='stretch')
    missing = [x.title() for x in pick if x not in set(view["city"])]
    if missing:
        st.info("No ownership projects with stage dates for: " + ", ".join(missing))
    n_stream = int(r["projects"]["streamlined"].sum())
    st.caption(f"Streamlined (SB 35) split: only {n_stream} ownership projects in this pool carry an SB 35 "
               "flag, too few to compare streamlined vs regular approvals. "
               "\"Still waiting\" = reached the stage with no next-stage date reported by "
               f"{data_end}; the APR does not record cancellations.")

# ---------------- Receipt ----------------
with tab_r:
    city = st.selectbox("City", cities, index=cities.index("LAGUNA BEACH") if "LAGUNA BEACH" in cities else 0,
                        format_func=str.title)
    months, notes = stage_months(city)
    rec = receipt(months, c=c, c0=c0, g0=g0, units=units, loan_not_drawn=loan_not_drawn,
                  baseline=baseline, stages=STAGES_USED)
    if not rec["lines"]:
        st.error("Unknown: no stage in this city has enough evidence for a receipt.")
    else:
        st.metric("Gap multiplier vs a typical OC timeline", f"{rec['multiplier']:.1f}x",
                  help="(G0 + delay cost) / G0, where delay cost charges only months beyond the "
                       "countywide median. Uses ASSUMPTION dollar figures.")
        st.markdown(f"Per home the gap goes from **{money(rec['gap_before'])}** at a typical OC pace to "
                    f"**{money(rec['gap_after'])}** at {city.title()}'s median pace.")
        st.code("\n".join(receipt_lines(rec)), language=None)
        for s, why in notes.items():
            if s in STAGES_USED:
                st.caption(f"{STAGE_LABELS[s]}: {why}; not counted.")
        st.caption("\"Typical\" = median over all Orange County approval batches for that stage "
                   "(same-day 0-month batches left out): "
                   + "; ".join(f"{STAGE_LABELS[s]} {baseline[s]:.1f} months (n={r['county'][s]['n']})"
                               for s in STAGES_USED if s in baseline)
                   + ". G0 is the gap at that typical pace, so only the extra months are charged.")

# ---------------- Compare ----------------
with tab_c:
    col_a, col_b = st.columns(2)
    city_a = col_a.selectbox("City A", cities, format_func=str.title,
                             index=cities.index("YORBA LINDA") if "YORBA LINDA" in cities else 0)
    city_b = col_b.selectbox("City B", cities, format_func=str.title,
                             index=cities.index("LAGUNA BEACH") if "LAGUNA BEACH" in cities else 1)
    ma, na = stage_months(city_a)
    mb, nb = stage_months(city_b)
    comparisons = []
    rows = []
    def cell(vals, why, s):
        return f"{vals[s]:.1f} mo" if s in vals else why.get(s, "unknown")

    for s in STAGES_USED:
        a_val, b_val = ma.get(s), mb.get(s)
        if a_val is None or b_val is None:
            rows.append({"Stage": STAGE_LABELS[s], city_a.title(): cell(ma, na, s),
                         city_b.title(): cell(mb, nb, s), "Difference per home": "unknown"})
            continue
        diff = city_difference(a_val, b_val, c)
        comparisons.append({"stage": STAGE_LABELS[s], "city_a_median_months": round(a_val, 1),
                            "city_b_median_months": round(b_val, 1),
                            "months_difference_b_minus_a": round(b_val - a_val, 1),
                            "dollar_difference_per_home_assumption": round(diff),
                            "dollar_difference_project_assumption": round(diff * units)})
        rows.append({"Stage": STAGE_LABELS[s], city_a.title(): f"{a_val:.1f} mo",
                     city_b.title(): f"{b_val:.1f} mo", "Difference per home": money(diff)})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch')
    if comparisons:
        total_diff = sum(x["dollar_difference_per_home_assumption"] for x in comparisons)
        cheaper, dearer = (city_a, city_b) if total_diff >= 0 else (city_b, city_a)
        st.subheader(f"Choosing {cheaper.title()} over {dearer.title()} saves about "
                     f"{money(abs(total_diff))} per home in waiting "
                     f"({money(abs(total_diff) * units)} for {units} homes).")
        st.caption("Only stages where both cities have 10+ approval batches are compared. "
                   "Medians, not guarantees: see the intervals on the Timelines tab.")
    else:
        st.info("Unknown: these two cities share no stage with enough evidence to compare.")

    st.divider()
    st.markdown("#### Board memo (written by Claude from the numbers above)")
    if st.button("Write board memo"):
        assumptions = {
            "c_monthly_carrying_cost_per_home": c, "c0_before_loan": c0 if loan_not_drawn else None,
            "g0_gap_per_home_before_delay": g0, "homes_in_project": units,
            "basis": "ASSUMPTIONS derived from the event's synthetic worked example "
                     "(a 10-month slip grew a $95k gap about 7x).",
        }
        mi = build_memo_input(city_a, city_b, summary, match, assumptions, comparisons, data_end)
        with st.spinner("Asking Claude..."):
            res = generate_memo(mi)
        if res["source"] == "backup":
            st.warning(f"Claude API unavailable ({res.get('error', 'unknown error')}). "
                       "Showing the saved backup memo, which may compare different cities.")
        elif not res["guard_ok"]:
            st.error("Number check FAILED: the memo contains numbers not in the input: "
                     + ", ".join(res["bad_numbers"]) + ". Do not use it without checking.")
        else:
            st.success("Number check passed: every number in the memo appears in the pipeline's output.")
        st.markdown(res["text"])
        with st.expander("Memo input (JSON)"):
            st.json(mi)

# ---------------- Limitations ----------------
with tab_l:
    st.markdown("#### What this can't tell you")
    for x in LIMITATIONS:
        st.markdown(f"- {x}")
    st.markdown(
        "- Counts are approval batches (same city, same stage start date); this is a proxy for a project, "
        "not an exact one.\n"
        "- Some cities report the same date for two stages (e.g. entitlement and permit). Those stages are "
        "flagged ⚠ and left out of receipts.\n"
        "- Huntington Beach and several other cities have too few ownership projects with stage dates.")
    st.markdown("#### What is real and what is assumed")
    st.markdown(f"- **Real:** stage dates, counts, match rate, from APR Tables A and A2 (downloaded {DATA_PULLED}, "
                f"reporting years through {r['latest_year']}).\n"
                f"- **ASSUMPTION:** c, c0, G0, from the synthetic deal (`{DEAL}`), not a real project.\n"
                "- **Backup:** if the Claude API fails, a saved memo is shown and labeled.")
    st.markdown(f"#### Sources\n- [APR data by jurisdiction and year, data.ca.gov]({APR_URL}) "
                f"(Table A `c78b769d-…`, Table A2 `fe505d9b-…`), downloaded {DATA_PULLED}\n"
                f"- [HCD APR instructions]({HCD_URL}): dates are reported only in the year they happen\n"
                "- [Event repo](" + EVENT_REPO + ") worked example: `docs/background.md`, `" + DEAL + "`")

st.divider()
st.caption(f"Sources: California HCD Housing Element APR Tables A & A2 via data.ca.gov (downloaded {DATA_PULLED}, "
           f"data through {data_end}) · Dollar figures: ASSUMPTION from the event's synthetic deal · "
           "Prototype, not legal or financial advice.")
