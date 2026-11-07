"""Delay Receipt: Streamlit app. Run: streamlit run app.py

Layout follows the "Delay Receipt screens" design (teal header, pill tabs, receipt card).
All numbers come from pipeline.build() and receipt.receipt(); this file only lays them out.
"""
import html
import math

import pandas as pd
import streamlit as st

from memo import LIMITATIONS, build_memo_input, generate_memo, load_backup
from pipeline import DATA_PULLED, build
from receipt import DEFAULTS, SUMMABLE, city_difference, receipt
from timelines import STAGE_LABELS

st.set_page_config(page_title="Delay Receipt", page_icon="🏠", layout="wide")

APR_URL = "https://data.ca.gov/dataset/housing-element-annual-progress-report-apr-data-by-jurisdiction-and-year"
HCD_URL = ("https://www.hcd.ca.gov/sites/default/files/docs/planning-and-community/"
           "housing-element-annual-progress-report-instructions.pdf")
DEAL = "claude-impact-lab-uci/lanes/3-fund-it/data/synthetic-example-deal.json"
EVENT_REPO = "https://github.com/travcjohnson/claude-impact-lab-uci"
BACKGROUND_URL = EVENT_REPO + "/blob/main/docs/background.md"
SAME_DAY_WARN = 0.5

# Plain-language stage names used on screen (the data's own labels stay in STAGE_LABELS).
FRIENDLY = {
    "app_ent": "Application to approval",
    "ent_bp": "Approval to building permit",
    "bp_co": "Building permit to move-in",
    "ent_co": "Approval to move-in (whole path)",
}
BADGE = {   # sample-size label -> (background, text)
    "Insufficient evidence": ("#F3E1E1", "#7A1F1F"),
    "Preliminary": ("#FCE8C3", "#6B3E00"),
    "Moderate": ("#E3F1E8", "#1E5631"),
    "More reliable": ("#D7ECEF", "#0F3D4A"),
}
TEAL, TEAL_LIGHT = "#175264", "#8CC7C4"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Public+Sans:wght@400;600;700;800&display=swap');
.stApp, .stApp p, .stApp li, .stApp label, .stApp td, .stApp th, .stApp h1, .stApp h2, .stApp h3,
.stApp input, .stApp button, .stApp summary p { font-family: 'Public Sans', system-ui, sans-serif; }
[data-testid="stToolbar"] { display: none; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { max-width: 1200px; padding-top: 1.2rem; padding-bottom: 3rem; }
section[data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid #E6E2D8; }
.dr-head { background: #175264; color: #fff; border-radius: 14px; padding: 16px 24px; display: flex;
  flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px 24px; }
.dr-head .brand { display: flex; align-items: center; gap: 12px; font-size: 22px; font-weight: 800; letter-spacing: -0.01em; }
.dr-head .tagline { font-size: 15px; color: #D7ECEF; }
.dr-note { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; padding: 10px 4px 0; font-size: 15px; }
.pill { font-size: 12px; font-weight: 700; letter-spacing: 0.04em; padding: 3px 10px; border-radius: 999px; white-space: nowrap; display: inline-block; }
/* tabs as pills */
.stTabs [role="tablist"] { gap: 6px !important; flex-wrap: wrap; border-bottom: 0 !important; box-shadow: none !important; }
.stTabs [role="tab"]::after, .stTabs [role="tab"]::before { display: none !important; }
.stTabs [role="tablist"] > :not([role="tab"]) { display: none !important; }
.stTabs [role="tablist"] { margin: 14px 0 8px; border: 0; }
.stTabs [role="tab"] { padding: 10px 20px !important; border-radius: 999px !important; height: auto; color: #1d70b8; font-weight: 600; background: transparent; }
.stTabs [role="tab"]:hover { background: #EEF5F6; }
.stTabs [role="tab"] p { font-size: 16px; font-weight: 600; }
.stTabs [role="tab"][aria-selected="true"] { background: #175264 !important; color: #fff !important; }
.stTabs [aria-selected="true"] p { color: #fff; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none !important; }
h1.dr { margin: 6px 0 6px; font-size: 38px; font-weight: 800; line-height: 1.15; letter-spacing: -0.015em; color: #1F2A30; padding: 0; }
p.lede { margin: 0 0 18px; font-size: 19px; color: #3D4A51; max-width: 780px; }
.card { background: #fff; border: 1px solid #E6E2D8; border-radius: 16px; padding: 22px 26px; margin-bottom: 18px; }
.card h2, .dr-h2 { margin: 0 0 12px; font-size: 21px; font-weight: 700; color: #1F2A30; padding: 0; }
.info { display: flex; gap: 14px; align-items: flex-start; padding: 14px 18px; background: #EEF5F6; border-radius: 12px; margin-bottom: 18px; font-size: 15px; }
.info .dot { flex: none; width: 28px; height: 28px; border-radius: 50%; background: #175264; color: #fff; font-weight: 800; display: flex; align-items: center; justify-content: center; }
.legend { display: flex; gap: 18px; font-size: 14px; color: #3D4A51; flex-wrap: wrap; }
.legend span.sw { display: inline-block; width: 14px; height: 14px; border-radius: 4px; margin-right: 6px; vertical-align: -2px; }
.barrow { display: grid; grid-template-columns: 220px minmax(0, 1fr); gap: 6px 16px; align-items: center; margin-top: 14px; }
.barrow .lab { font-size: 15px; font-weight: 600; grid-row: span 2; }
.bar { display: flex; align-items: center; gap: 10px; font-size: 14px; color: #3D4A51; }
.bar div { height: 18px; border-radius: 6px; min-width: 3px; max-width: 86%; }
.bar span { white-space: nowrap; }
.muted { color: #55636A; font-size: 14px; }
table.dr { width: 100%; border-collapse: collapse; font-size: 15px; }
table.dr th { text-align: left; padding: 12px 14px; font-weight: 700; border-bottom: 2px solid #1F2A30; }
table.dr td { padding: 12px 14px; border-bottom: 1px solid #ECE8DF; }
table.dr tr:last-child td { border-bottom: 0; }
table.dr .r { text-align: right; }
.hero { background: #175264; color: #fff; border-radius: 20px; padding: 30px; min-height: 420px; display: flex; flex-direction: column; gap: 12px; }
.hero .k { font-size: 16px; font-weight: 600; color: #D7ECEF; margin: 0; }
.hero .big { font-size: 96px; font-weight: 800; line-height: 1; letter-spacing: -0.03em; margin: 0; }
.hero .txt { font-size: 18px; line-height: 1.45; margin: 0; }
.hero .warn { margin-top: auto; display: flex; gap: 10px; padding: 12px 14px; background: rgba(255,255,255,0.1); border-radius: 12px; font-size: 14px; color: #E9F4F5; }
.receipt { background: #FFFDF6; border: 1px solid #E8E1CC; border-radius: 16px; padding: 28px 32px; box-shadow: 0 10px 30px rgba(23,82,100,0.08); display: flex; flex-direction: column; gap: 14px; font-size: 15px; }
.receipt .ttl { text-align: center; font-family: 'IBM Plex Mono', ui-monospace, monospace; font-weight: 600; letter-spacing: 0.16em; margin: 0; }
.receipt .sub { text-align: center; color: #55636A; font-size: 14px; margin: 0; }
.receipt .rule { border-top: 2px dotted #D6CDB2; }
.receipt .line { display: flex; justify-content: space-between; gap: 16px; font-family: 'IBM Plex Mono', ui-monospace, monospace; font-size: 14px; }
.receipt .line .what { font-family: 'Public Sans', sans-serif; font-size: 16px; font-weight: 600; margin: 0; }
.receipt .row { display: flex; justify-content: space-between; gap: 16px; margin: 0; }
.receipt .total { padding: 14px 16px; background: #FCE8C3; border-radius: 10px; color: #4A2B00; align-items: baseline; }
.good { color: #1E5631; }
.banner { display: flex; flex-wrap: wrap; gap: 14px 22px; align-items: center; padding: 22px 26px; background: #E3F1E8; border-radius: 16px; color: #133D22; margin-bottom: 20px; }
.banner p { margin: 0; flex: 1 1 420px; font-size: 20px; line-height: 1.45; }
.city { background: #fff; border: 1px solid #E6E2D8; border-radius: 16px; padding: 24px 26px; display: flex; flex-direction: column; gap: 12px; }
.city.slow { border: 2px solid #175264; }
.city .top { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.city h3 { margin: 0; font-size: 22px; font-weight: 700; padding: 0; }
.city .row { display: flex; justify-content: space-between; gap: 12px; margin: 0; }
.city hr { border: 0; border-top: 1px solid #ECE8DF; margin: 0; }
.lims { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 18px; margin-bottom: 20px; }
.lims div { background: #fff; border: 1px solid #E6E2D8; border-radius: 16px; padding: 22px; }
.lims h3 { margin: 10px 0 6px; font-size: 18px; font-weight: 700; padding: 0; }
.lims p { margin: 0; color: #3D4A51; }
div.stButton > button { font-size: 17px; font-weight: 700; padding: 10px 22px; border: 0; border-radius: 6px; background: #00703c; color: #fff; box-shadow: 0 3px 0 #002d18; }
div.stButton > button:hover { background: #005a30; color: #fff; }
.memo { background: #FBFAF7; border-radius: 12px; padding: 4px 22px 10px; }
</style>
"""


def show(markup: str) -> None:
    """Render HTML. Lines are de-indented so Markdown never treats them as code blocks."""
    st.markdown(" ".join(line.strip() for line in markup.splitlines()), unsafe_allow_html=True)


def esc(s) -> str:
    return html.escape(str(s))


def city_name(c: str) -> str:
    return esc(c.title())


def usd(x: float) -> str:
    """Dollar figure for HTML. The dagger points to the ASSUMPTION footnote on every screen.
    &#36; keeps Streamlit's Markdown from reading $...$ as math."""
    sign = "−" if x < 0 else ""
    return f"{sign}&#36;{abs(x):,.0f}<sup>†</sup>"


def badge(label: str) -> str:
    bg, fg = BADGE.get(label, ("#EEE", "#333"))
    return f'<span class="pill" style="background:{bg};color:{fg}">{esc(label)}</span>'


@st.cache_data(show_spinner="Stitching the state's yearly reports into projects...")
def load(min_units, max_units):
    return build(min_units=min_units, max_units=max_units)


# ---------------- sidebar: your project ----------------
st.sidebar.markdown("## Your project")
st.sidebar.caption("Starting numbers come from the event's example home. Change them to match yours.")
unit_range = st.sidebar.slider("Units per project to compare (like-for-like)", 1, 200, (1, 200))
r = load(*unit_range)
summary, match = r["summary"], r["match"]
data_end = r["data_end"].date().isoformat()
cities = sorted(summary["city"].unique())


def pick(label, default, key):
    idx = cities.index(default) if default in cities else 0
    return st.sidebar.selectbox(label, cities, index=idx, format_func=str.title, key=key)


city_a = pick("First city", "YORBA LINDA", "city_a")
city_b = pick("Second city", "LAGUNA BEACH", "city_b")
units = st.sidebar.number_input("Homes in your project", value=6, step=1, min_value=1)
with st.sidebar.expander("Change the cost assumptions"):
    st.caption("Every dollar figure is an ASSUMPTION, derived from the event's synthetic example home "
               f"(`{DEAL}`).")
    c = st.number_input("Carrying cost per home per month ($)", value=DEFAULTS["c"]["value"], step=100, min_value=0)
    g0 = st.number_input("Starting gap per home ($)", value=DEFAULTS["g0"]["value"], step=100, min_value=1)
    loan_not_drawn = st.toggle("Construction loan not drawn before the permit", value=False)
    c0 = st.number_input("Monthly cost before the loan ($)", value=DEFAULTS["c0"]["value"], step=100,
                         min_value=0, disabled=not loan_not_drawn)
    include_build = st.toggle("Include permit to move-in (mostly construction)", value=False,
                              help="Off by default: this step depends mostly on the builder, not the city.")
st.sidebar.caption("Owner-occupied homes only. ADUs and rentals are always left out.")
STAGES_USED = ["app_ent", "ent_bp"] + (["bp_co"] if include_build else [])
FOOTNOTE = (f"† ASSUMPTION. Estimated at &#36;{c:,.0f} a month per home and a &#36;{g0:,.0f} starting gap, "
            "both derived from the event's example home, not a real project.")


def stage_months(city):
    """Medians usable in a receipt: 10+ approval batches and not mostly same-day dates."""
    out, notes = {}, {}
    for _, row in summary[summary["city"] == city].iterrows():
        if row["stage"] not in SUMMABLE:
            continue
        if row["n"] < 10:
            notes[row["stage"]] = "not enough data"
        elif row["same_day_share"] >= SAME_DAY_WARN:
            notes[row["stage"]] = "mostly same-day dates, not used"
        else:
            out[row["stage"]] = float(row["median"])
    return out, notes


months_a, notes_a = stage_months(city_a)
months_b, notes_b = stage_months(city_b)
common = [s for s in STAGES_USED if s in months_a and s in months_b]

# ---------------- header ----------------
st.markdown(CSS, unsafe_allow_html=True)
show(f"""
<div class="dr-head">
  <div class="brand"><svg aria-hidden="true" width="34" height="34" viewBox="0 0 34 34" fill="none" stroke="#FFFFFF"
    stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 16 17 6l12 10"/><path d="M8 14v14h18V14"/>
    <path d="M14 28v-7h6v7"/></svg>The Delay Receipt</div>
  <div class="tagline">For nonprofits choosing where to build affordable homes in Orange County</div>
</div>
<div class="dr-note"><span class="pill" style="background:#E3F1E8;color:#1E5631">REAL DATA</span>
  Approval dates from the reports every Orange County city files with the state, through {data_end[:4]}.
  Dollar amounts are estimates.</div>
""")

tab_t, tab_r, tab_c, tab_l = st.tabs(["1. Timelines", "2. Receipt", "3. Compare", "4. What this can't tell you"])

# ---------------- 1. Timelines ----------------
with tab_t:
    show("""<h1 class="dr">How long does building really take?</h1>
    <p class="lede">Typical months at each step for owner-occupied homes, from the reports every city files with the state.</p>
    <div class="info"><span class="dot">i</span><span>These are medians of <strong>finished</strong> steps.
    Projects still waiting are counted separately, because leaving them out makes a city look faster than it is.
    A 300-lot subdivision approved on one day counts once, not 300 times.</span></div>""")

    shown = [s for s in STAGES_USED if s in months_a or s in months_b]
    if shown:
        top = max([months_a.get(s, 0) for s in shown] + [months_b.get(s, 0) for s in shown]) or 1
        total_a = sum(months_a[s] for s in common)
        total_b = sum(months_b[s] for s in common)
        slower = city_b if total_b > total_a else city_a
        heading = (f"{city_name(slower)} takes longer to get from application to permit" if common and total_a != total_b
                   else "Median months at each step")

        def bar(months, s, color, bold):
            if s not in months:
                return '<div class="bar"><span class="muted">not enough data</span></div>'
            w = 100 * months[s] / top
            weight = "font-weight:700;color:#1F2A30" if bold else ""
            return (f'<div class="bar"><div style="width:{w:.1f}%;background:{color}"></div>'
                    f'<span style="{weight}">{months[s]:.1f} mo</span></div>')

        rows = "".join(f'<div class="barrow"><span class="lab">{FRIENDLY[s]}</span>'
                       f'{bar(months_a, s, TEAL_LIGHT, False)}{bar(months_b, s, TEAL, True)}</div>' for s in shown)
        show(f"""<div class="card"><div style="display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px 24px;align-items:baseline">
        <h2>{heading}</h2><div class="legend"><span><span class="sw" style="background:{TEAL_LIGHT}"></span>{city_name(city_a)}</span>
        <span><span class="sw" style="background:{TEAL}"></span>{city_name(city_b)}</span></div></div>
        {rows}<p class="muted" style="margin:14px 0 0">Bars scaled to {top:.0f} months. Data through {data_end}.</p></div>""")
    else:
        st.info("Neither city has enough finished projects for these steps. Pick other cities in the sidebar.")

    def city_table(city):
        order = list(FRIENDLY)
        rows = summary[summary["city"] == city].sort_values("stage", key=lambda s: s.map(order.index))
        body = ""
        for _, row in rows.iterrows():
            ok = row["n"] >= 10
            med = f"{row['median']:.1f}" if ok else "unknown"
            rng = f"{row['ci_low']:.1f} to {row['ci_high']:.1f}" if ok else "—"
            note = ""
            if ok and row["same_day_share"] >= SAME_DAY_WARN:
                note = f' <span class="muted">⚠ {row["same_day_share"]:.0%} same-day dates</span>'
            body += (f'<tr><td>{FRIENDLY.get(row["stage"], esc(row["stage_label"]))}{note}</td>'
                     f'<td class="r"><strong>{med}</strong></td><td>{rng}</td><td class="r">{int(row["n"])}</td>'
                     f'<td class="r">{int(row["still_waiting"])}</td><td>{badge(row["label"])}</td></tr>')
        if not body:
            body = '<tr><td colspan="6">No ownership projects with stage dates.</td></tr>'
        show(f"""<h3 class="dr-h2">{city_name(city)}, step by step</h3><div class="card" style="overflow-x:auto;padding:6px 10px">
        <table class="dr"><thead><tr><th>Step</th><th class="r">Typical months</th><th>Likely range (90%)</th>
        <th class="r">Finished</th><th class="r">Still waiting</th><th>How sure</th></tr></thead><tbody>{body}</tbody></table></div>""")

    city_table(city_a)
    city_table(city_b)

    with st.expander("All Orange County cities"):
        allv = summary[summary["stage"].isin(STAGES_USED)].copy()
        allv["Median months"] = allv.apply(lambda x: round(x["median"], 1) if x["n"] >= 10 else None, axis=1)
        allv = allv.rename(columns={"n": "Finished", "still_waiting": "Still waiting", "label": "How sure"})
        allv["City"] = allv["city"].str.title()
        allv["Step"] = allv["stage"].map(FRIENDLY)
        st.dataframe(allv[["City", "Step", "Median months", "Finished", "Still waiting", "How sure"]],
                     hide_index=True, width="stretch")
    st.caption(f"{match['projects']:,} ownership projects; {match['cross_year_rate']:.0%} linked across two or more "
               "yearly reports. \"Still waiting\" means a step started with no next date reported; the reports "
               "don't record cancellations.")

# ---------------- 2. Receipt ----------------
with tab_r:
    show("""<h1 class="dr">Here's what waiting costs</h1><p class="lede">Every extra month adds carrying costs:
    loan interest, taxes and insurance. The family's price can't rise to cover them, so they land on your funding gap.</p>""")
    # The receipt is always for the slower of your two cities, priced against the faster one's schedule.
    b_extra = sum(months_b[s] - months_a[s] for s in common)
    rc, base_city = (city_b, city_a) if b_extra >= 0 else (city_a, city_b)
    m_r, m_base = (months_b, months_a) if rc == city_b else (months_a, months_b)
    rec = receipt(m_r, c=c, c0=c0, g0=g0, units=units, loan_not_drawn=loan_not_drawn,
                  baseline={s: m_base[s] for s in common}, stages=common)

    if not common or rc == base_city:
        st.info("Unknown: pick two different cities that both have enough finished projects for the same steps.")
    else:
        extra_months = sum(ln["extra"] for ln in rec["lines"])
        grows = rec["delay_cost"] >= 0
        verb = f"<strong>{abs(extra_months):.1f} more months</strong>" if grows else f"<strong>{abs(extra_months):.1f} fewer months</strong>"
        lines = ""
        for ln in rec["lines"]:
            longer = ln["extra"] >= 0
            cls = "" if longer else "good"
            word = "longer" if longer else "shorter"
            lines += (f'<div class="line"><div><p class="what">{FRIENDLY[ln["stage"]]}</p>'
                      f'<p class="{cls}" style="margin:0;color:{"#55636A" if longer else "#1E5631"}">'
                      f'{abs(ln["extra"]):.1f} months {word} × &#36;{ln["rate"]:,.0f}</p></div>'
                      f'<p class="{cls}" style="margin:0;white-space:nowrap;font-weight:600">{usd(ln["cost"])}</p></div>')
        skipped = [f'{FRIENDLY[s]}: not compared ({(notes_a | notes_b).get(s, "not enough data in one city")})'
                   for s in STAGES_USED if s not in common]
        skipped_html = "".join(f'<p class="muted" style="margin:0">{esc(x)}</p>' for x in skipped)
        left, right = st.columns([1, 1.35], gap="large")
        with left:
            show(f"""<div class="hero"><p class="k">Your funding gap {"grows" if grows else "shrinks"}</p>
            <p class="big">{rec["multiplier"]:.1f}×</p>
            <p class="txt">{city_name(rc)} takes {verb} than {city_name(base_city)}. That turns a <strong>{usd(rec["gap_before"])}</strong>
            gap into <strong>{usd(rec["gap_after"])}</strong> per home.</p>
            <div class="warn"><span>⚠</span><span>Dollar figures are estimates based on the event's example home, not a real project.
            The months are real.</span></div></div>""")
        with right:
            show(f"""<div class="receipt"><p class="ttl">DELAY RECEIPT</p>
            <p class="sub">{city_name(rc)} compared with {city_name(base_city)} · per home</p><div class="rule"></div>
            {lines}{skipped_html}<div class="rule"></div>
            <div class="row" style="font-weight:700;font-size:17px"><span>{"Extra" if grows else "Saved"} waiting cost per home</span><span>{usd(rec["delay_cost"])}</span></div>
            <div class="row" style="color:#3D4A51"><span>For your {units} homes</span><span>{usd(rec["delay_cost_project"])}</span></div>
            <div class="rule"></div>
            <div class="row" style="color:#3D4A51"><span>Gap on {city_name(base_city)}'s schedule</span><span>{usd(rec["gap_before"])}</span></div>
            <div class="row total"><span style="font-weight:700;font-size:17px">Gap per home in {city_name(rc)}</span>
            <span style="font-weight:800;font-size:24px">{usd(rec["gap_after"])}</span></div>
            <p class="muted" style="text-align:center;margin:0;font-size:13px">{FOOTNOTE}</p></div>""")

# ---------------- 3. Compare ----------------
with tab_c:
    show("""<h1 class="dr">Which city gets you to keys sooner?</h1>
    <p class="lede">The same project, two cities. The faster schedule keeps your funding gap small.</p>""")
    comparisons = []
    for s in common:
        a_val, b_val = months_a[s], months_b[s]
        diff = city_difference(a_val, b_val, c)
        comparisons.append({"stage": STAGE_LABELS[s], "city_a_median_months": round(a_val, 1),
                            "city_b_median_months": round(b_val, 1),
                            "months_difference_b_minus_a": round(b_val - a_val, 1),
                            "dollar_difference_per_home_assumption": round(diff),
                            "dollar_difference_project_assumption": round(diff * units)})
    if not common or city_a == city_b:
        st.info("Unknown: these two cities share no step with enough evidence to compare.")
    else:
        rec_ab = receipt(months_b, c=c, c0=c0, g0=g0, units=units, loan_not_drawn=loan_not_drawn,
                         baseline={s: months_a[s] for s in common}, stages=common)
        fast, slow = (city_a, city_b) if rec_ab["delay_cost"] >= 0 else (city_b, city_a)
        save = abs(rec_ab["delay_cost"])
        mult = (g0 + save) / g0
        months_of = {city_a: months_a, city_b: months_b}
        show(f"""<div class="banner"><svg aria-hidden="true" width="40" height="40" viewBox="0 0 40 40" fill="none"
        stroke="#1E5631" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="20" cy="20" r="17"/>
        <path d="m12 20 6 6 10-12"/></svg><p>Building in <strong>{city_name(fast)}</strong> saves about
        <strong>{usd(save)} per home</strong>, or <strong>{usd(save * units)}</strong> across your {units} homes, in waiting costs.</p>
        <span class="pill" style="background:#fff;color:#6B3E00">ESTIMATE</span></div>""")

        def card(city, is_slow):
            m = months_of[city]
            other = months_of[fast]
            tot = sum(m[s] for s in common)
            sub = (f"About {tot:.1f} months, the faster schedule" if not is_slow
                   else f"About {tot:.1f} months, {tot - sum(other[s] for s in common):.1f} longer")
            tag = (f'<span class="pill" style="background:#E3F1E8;color:#1E5631;font-size:13px">Baseline · 1.0×</span>'
                   if not is_slow else
                   f'<span class="pill" style="background:#175264;color:#fff;font-size:13px">{mult:.1f}× the gap</span>')
            rows = ""
            for s in common:
                extra = ""
                if is_slow:
                    d = (m[s] - other[s]) * c
                    color = "#55636A" if d >= 0 else "#1E5631"
                    extra = f' <span style="color:{color};font-weight:400">· {usd(d)}</span>'
                rows += f'<p class="row"><span>{FRIENDLY[s]}</span><span style="font-weight:600">{m[s]:.1f} mo{extra}</span></p>'
            gap = g0 + save if is_slow else g0
            return (f'<div class="city{" slow" if is_slow else ""}"><div class="top"><div><h3>{city_name(city)}</h3>'
                    f'<p class="muted" style="margin:2px 0 0;font-size:15px">{sub}</p></div>{tag}</div><hr>{rows}<hr>'
                    f'<p class="row" style="align-items:baseline"><strong>Gap per home</strong>'
                    f'<span style="font-size:24px;font-weight:800;color:{TEAL if is_slow else "#1F2A30"}">{usd(gap)}</span></p></div>')

        col1, col2 = st.columns(2, gap="medium")
        with col1:
            show(card(fast, False))
        with col2:
            show(card(slow, True))
        prelim = [f"{city_name(cn)} {FRIENDLY[s].lower()}" for cn in (city_a, city_b)
                  for _, row in summary[(summary["city"] == cn) & summary["stage"].isin(common)].iterrows()
                  for s in [row["stage"]] if row["label"] == "Preliminary"]
        note = f" Preliminary (10–19 projects): {', '.join(prelim)}." if prelim else ""
        show(f'<p class="muted" style="margin:10px 0 22px">{FOOTNOTE} Medians, not guarantees: see the ranges on the Timelines tab.{note}</p>')

    show("""<h2 class="dr-h2" style="font-size:26px;font-weight:800">Share it with your board</h2>
    <p style="color:#3D4A51;margin:0 0 12px">Claude writes a one-page summary using only the numbers on this page,
    then the app checks every number it used.</p>""")
    if st.button("Write the board memo", disabled=not common):
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
            st.success("Checked: every number in this memo appears in the app's data.")
        with st.container(border=True):
            st.markdown(res["text"].replace("$", "\\$"))
        with st.expander("Memo input (JSON)"):
            st.json(mi)

# ---------------- 4. Limitations ----------------
ICONS = {
    "people": '<circle cx="13" cy="12" r="5"/><circle cx="25" cy="12" r="5"/><path d="M4 30c0-5 4-9 9-9s9 4 9 9"/><path d="M22 21.5c.9-.3 1.9-.5 3-.5 5 0 9 4 9 9"/>',
    "build": '<rect x="5" y="14" width="10" height="16" rx="1"/><rect x="19" y="6" width="12" height="24" rx="1"/><path d="M9 19h2M9 24h2M23 11h4M23 16h4M23 21h4"/>',
    "clock": '<circle cx="18" cy="18" r="13"/><path d="M18 10v8l5 3"/>',
    "dollar": '<circle cx="18" cy="18" r="13"/><path d="M22 13.5c-1-1-2.4-1.5-4-1.5-2.5 0-4 1.2-4 3s1.6 2.5 4 3 4 1.2 4 3-1.5 3-4 3c-1.7 0-3.2-.6-4.2-1.6"/><path d="M18 9v3M18 24v3"/>',
    "link": '<path d="M15 21a6 6 0 0 0 8.5 0l5-5a6 6 0 0 0-8.5-8.5l-1.5 1.5"/><path d="M21 15a6 6 0 0 0-8.5 0l-5 5a6 6 0 0 0 8.5 8.5l1.5-1.5"/>',
    "cal": '<rect x="5" y="8" width="26" height="22" rx="2"/><path d="M5 14h26M12 5v6M24 5v6"/>',
}
with tab_l:
    items = [
        ("people", "Who caused the wait", "The reports can't separate a slow city review from a developer who paused the project."),
        ("build", "Harder projects take longer", "We compare owner-occupied projects of similar size, but some cities simply get more complex ones."),
        ("clock", "Stalled projects", "Cancellations aren't recorded, so a stalled project shows as \"still waiting\"."),
        ("dollar", "The dollar amounts", "They're estimates from one example home in the event's materials, not a real project's costs."),
        ("link", "Linking the yearly reports",
         f"Each report only has that year's dates. We could link {match['cross_year_rate']:.0%} of projects across years; the rest show only one step."),
        ("cal", "A short history", "Reports start in 2018, so very long timelines that began earlier are missing, and some cities report two steps on the same day."),
    ]
    cards = "".join(f'<div><svg aria-hidden="true" width="36" height="36" viewBox="0 0 36 36" fill="none" stroke="#175264" '
                    f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{ICONS[i]}</svg>'
                    f'<h3>{esc(t)}</h3><p>{esc(d)}</p></div>' for i, t, d in items)
    show(f"""<h1 class="dr">What this can't tell you</h1>
    <p class="lede">We'd rather you know the limits up front. Use these numbers to ask better questions, not as a final answer.</p>
    <div class="lims">{cards}</div>
    <div class="card"><h2>Where the numbers come from</h2><ul style="margin:0;padding-left:22px">
    <li><a href="{APR_URL}">Housing Element Annual Progress Reports (Tables A and A2), California Department of Housing and Community Development</a>, downloaded {DATA_PULLED}, data through {data_end}</li>
    <li><a href="{HCD_URL}">How cities fill in those reports (HCD instructions)</a>: dates are reported only in the year they happen</li>
    <li><a href="{BACKGROUND_URL}">The event's example home</a>: a &#36;95k gap after a 10-month slip, about 7 times larger (synthetic, ASSUMPTION)</li>
    </ul><p class="muted" style="margin:10px 0 0">Prototype, not legal or financial advice.</p></div>""")
    with st.expander("Full list of limitations"):
        for x in LIMITATIONS:
            st.markdown(f"- {x}")
