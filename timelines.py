"""Months per stage, medians with 90% bootstrap intervals, sample-size labels, still-waiting counts."""
import numpy as np
import pandas as pd

DAYS_PER_MONTH = 30.4375
STAGE_DEFS = [
    # key, start, end, label
    ("app_ent", "app_date", "ent_date", "Application → entitlement"),
    ("ent_bp", "ent_date", "bp_date", "Entitlement → building permit"),
    ("bp_co", "bp_date", "co_date", "Building permit → occupancy"),
    ("ent_co", "ent_date", "co_date", "Entitlement → occupancy (end to end)"),
]
STAGE_LABELS = {k: lab for k, _, _, lab in STAGE_DEFS}
N_DRAWS = 2000
SEED = 20261107
CI_LEVEL = 90


def sample_label(n: int) -> str:
    if n < 10:
        return "Insufficient evidence"
    if n < 20:
        return "Preliminary"
    if n < 30:
        return "Moderate"
    return "More reliable"


STAGE_ORDER = ["app_date", "ent_date", "bp_date", "co_date"]


def durations(projects: pd.DataFrame) -> pd.DataFrame:
    """Long table: one row per project (parcel) per stage it entered.
    months is NaN when the project is still waiting or the dates are out of order;
    durations are never negative. A project counts as still waiting only if it has no
    end date AND no later-stage date (a project with a CO is not waiting for a permit)."""
    rows = []
    for key, start, end, _ in STAGE_DEFS:
        if start not in projects or end not in projects:
            continue
        p = projects[projects[start].notna()]
        if p.empty:
            continue
        days = (p[end] - p[start]).dt.days
        out_of_order = (days < 0).fillna(False)
        later = [c for c in STAGE_ORDER[STAGE_ORDER.index(end) + 1:] if c in p]
        has_later = p[later].notna().any(axis=1) if later else pd.Series(False, index=p.index)
        missing_end = p[end].isna()
        waiting = missing_end & ~has_later
        months = (days / DAYS_PER_MONTH).where(~out_of_order & ~missing_end)
        rows.append(pd.DataFrame({
            "project_id": p["project_id"].values,
            "city": p["city"].values,
            "streamlined": p["streamlined"].values if "streamlined" in p else False,
            "stage": key,
            "start_date": p[start].values,
            "months": months.values,
            "still_waiting": waiting.values,
            "order_excluded": out_of_order.values,
        }))
    if not rows:
        return pd.DataFrame(columns=["project_id", "city", "streamlined", "stage", "start_date",
                                     "months", "still_waiting", "order_excluded"])
    d = pd.concat(rows, ignore_index=True)
    assert (d["months"].dropna() >= 0).all()
    return d


def batches(d: pd.DataFrame, by=("city",)) -> pd.DataFrame:
    """Collapse parcels into approval batches: same group, same stage, same stage start date.
    Large subdivisions file hundreds of parcels approved on one day; counting each parcel
    would overstate the evidence. Batch duration = median of its finished parcels."""
    keys = list(by) + ["stage", "start_date"]
    g = d.groupby(keys, sort=False, dropna=False)
    b = pd.DataFrame({
        "months": g["months"].median(),
        "parcels": g.size(),
        "any_finished": g["months"].count() > 0,
        "all_waiting": g["still_waiting"].all(),
        "any_order": g["order_excluded"].any(),
    }).reset_index()
    b["still_waiting"] = b["all_waiting"] & ~b["any_finished"]
    return b


def bootstrap_ci(values, n_draws=N_DRAWS, seed=SEED, level=CI_LEVEL):
    v = np.asarray(values, dtype=float)
    if len(v) == 0:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    meds = np.median(rng.choice(v, size=(n_draws, len(v)), replace=True), axis=1)
    lo = (100 - level) / 2
    return float(np.percentile(meds, lo)), float(np.percentile(meds, 100 - lo))


def pooled_baseline(projects: pd.DataFrame) -> dict:
    """Countywide 'typical' months per stage: median over all OC approval batches (batched within
    each city first). Batches of 0 months are dropped from the pool, since same-day dates look
    like a reporting convention. Returns {stage: {"median": m, "n": batches}}."""
    b = batches(durations(projects), by=("city",))
    out = {}
    for stage, g in b.groupby("stage"):
        v = g["months"].dropna()
        v = v[v > 0]
        out[stage] = {"median": float(np.median(v)) if len(v) >= 10 else np.nan, "n": int(len(v))}
    return out


def summarize(projects: pd.DataFrame, data_end: pd.Timestamp, by=("city",)) -> pd.DataFrame:
    """Per group and stage, counted in approval batches (see batches()):
    n finished batches, median (hidden when n < 10), 90% CI, label, still-waiting batches
    (no further activity reported by data_end), order-excluded parcels, parcel count."""
    d = durations(projects)
    by = list(by)
    b = batches(d, by=by)
    order_by = d.groupby(by + ["stage"])["order_excluded"].sum()
    parcels_by = d.groupby(by + ["stage"])["months"].count()
    waiting_parcels_by = d.groupby(by + ["stage"])["still_waiting"].sum()
    out = []
    for keys, grp in b.groupby(by + ["stage"], sort=True):
        keys = keys if isinstance(keys, tuple) else (keys,)
        done = grp["months"].dropna().to_numpy()
        n = len(done)
        label = sample_label(n)
        if n >= 10:
            med = float(np.median(done))
            lo, hi = bootstrap_ci(done)
        else:
            med = lo = hi = np.nan
        rec = dict(zip(by + ["stage"], keys))
        rec.update({
            "same_day_share": float((done == 0).mean()) if n else np.nan,
            "stage_label": STAGE_LABELS[rec["stage"]],
            "n": n, "median": med, "ci_low": lo, "ci_high": hi, "label": label,
            "still_waiting": int(grp["still_waiting"].sum()),
            "order_excluded": int(order_by.get(keys, 0)),
            "parcels_finished": int(parcels_by.get(keys, 0)),
            "parcels_still_waiting": int(waiting_parcels_by.get(keys, 0)),
            "data_end": data_end.date().isoformat(),
        })
        out.append(rec)
    return pd.DataFrame(out)
