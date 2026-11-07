"""Stitch yearly APR rows into one row per project.

Matching rules, applied in this order (all within one city):
  1. apn        same normalized APN
  2. prior_apn  a row's PRIOR_APN equals another row's APN
  3. address    same normalized street address, used only when a row has no APN
                (conservative: two different APNs at one address are not merged)

match_method on a project = the weakest rule needed to build it
(single_row < apn < prior_apn < address). Each stage keeps its earliest date; if the
rows disagree, conflict_<stage> is set. One APN often carries several permits (one per
home), so a bp conflict usually means phased permits, not bad data.
"""
import pandas as pd

RANK = {"single_row": 0, "apn": 1, "prior_apn": 2, "address": 3}
STAGES = ["ent", "bp", "co"]


def ownership_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Like-for-like filter: owner tenure, no ADUs. Applied BEFORE stitching so an ADU or
    rental row on the same parcel can never leak a date into an ownership project."""
    return df[(df["TENURE"] == "Owner") & (df["UNIT_CAT"] != "ADU")].copy()


def adu_rows(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["UNIT_CAT"] == "ADU"].copy()


class _DSU:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


def _link(df: pd.DataFrame):
    n = len(df)
    dsu = _DSU(n)
    method = ["single_row"] * n
    city = df["city"].tolist()
    apn = df["apn_norm"].tolist()
    prior = df["prior_apn_norm"].tolist()
    addr = df["addr_norm"].tolist()

    def mark(i, j, m):
        dsu.union(i, j)
        for k in (i, j):
            if RANK[m] > RANK[method[k]]:
                method[k] = m

    # 1. exact APN
    first_by_apn = {}
    for i in range(n):
        if apn[i]:
            key = (city[i], apn[i])
            if key in first_by_apn:
                mark(first_by_apn[key], i, "apn")
            else:
                first_by_apn[key] = i
    # 2. prior APN -> current APN
    for i in range(n):
        if prior[i] and prior[i] != apn[i]:
            j = first_by_apn.get((city[i], prior[i]))
            if j is not None:
                mark(j, i, "prior_apn")
    # 3. address, only for rows without an APN
    first_by_addr = {}
    for i in range(n):
        if addr[i] and apn[i]:
            first_by_addr.setdefault((city[i], addr[i]), i)
    for i in range(n):
        if addr[i] and not apn[i]:
            key = (city[i], addr[i])
            if key in first_by_addr:
                mark(first_by_addr[key], i, "address")
            else:
                first_by_addr[key] = i
    return [dsu.find(i) for i in range(n)], method


def stitch(df: pd.DataFrame) -> pd.DataFrame:
    """One row per project. Input: output of clean.clean_a2 (optionally filtered)."""
    df = df.reset_index(drop=True).copy()
    if df.empty:
        return pd.DataFrame(columns=["project_id", "city", "match_method", "conflict", "order_issue"]
                            + [f"{s}_date" for s in STAGES])
    roots, method = _link(df)
    df["_root"] = roots
    df["_method_rank"] = [RANK[m] for m in method]

    g = df.groupby("_root", sort=False)
    out = pd.DataFrame({
        "city": g["city"].first(),
        "apn_norm": g["apn_norm"].agg(lambda s: next((x for x in s if x), "")),
        "unit_cat": g["UNIT_CAT"].agg(lambda s: s.mode().iat[0]),
        "tenure": g["TENURE"].agg(lambda s: s.mode().iat[0]),
        "n_rows": g.size(),
        "n_years": g["year"].nunique(),
        "first_year": g["year"].min(),
        "last_year": g["year"].max(),
        "sb35": g["sb35"].any(),
        "units": pd.concat([g["ent_units"].sum(), g["bp_units"].sum(), g["co_units"].sum()],
                           axis=1).max(axis=1),
        "_method_rank": g["_method_rank"].max(),
    })
    inv = {v: k for k, v in RANK.items()}
    out["match_method"] = out["_method_rank"].map(inv)
    for s in STAGES:
        col = f"{s}_date"
        out[col] = g[col].min()
        out[f"conflict_{s}"] = g[col].nunique() > 1
    out["conflict"] = out[[f"conflict_{s}" for s in STAGES]].any(axis=1)

    # order check: a later stage dated before an earlier one
    e, b, c = out["ent_date"], out["bp_date"], out["co_date"]
    out["order_issue_ent_bp"] = (b < e).fillna(False)
    out["order_issue_bp_co"] = (c < b).fillna(False)
    out["order_issue_ent_co"] = (c < e).fillna(False)
    out["order_issue"] = out[["order_issue_ent_bp", "order_issue_bp_co", "order_issue_ent_co"]].any(axis=1)

    out = out.drop(columns="_method_rank").reset_index(drop=True)
    out.insert(0, "project_id", range(1, len(out) + 1))
    return out


def attach_applications(projects: pd.DataFrame, a_clean: pd.DataFrame) -> pd.DataFrame:
    """Join Table A application dates onto projects by (city, APN), then by prior APN.
    Adds app_date (earliest), conflict_app, sb35_app and app_match. Address joins are
    not attempted for Table A."""
    p = projects.copy()
    a = a_clean[a_clean["apn_norm"] != ""]
    grp = a.groupby(["city", "apn_norm"])
    apps = pd.DataFrame({
        "app_date": grp["app_date"].min(),
        "conflict_app": grp["app_date"].nunique() > 1,
        "sb35_app": grp["sb35"].any(),
    }).reset_index()
    p = p.merge(apps, on=["city", "apn_norm"], how="left")
    p["app_match"] = p["app_date"].notna().map({True: "apn", False: ""})
    p["conflict_app"] = p["conflict_app"].astype("boolean").fillna(False).astype(bool)
    p["sb35_app"] = p["sb35_app"].astype("boolean").fillna(False).astype(bool)
    p["order_issue_app_ent"] = (p["ent_date"] < p["app_date"]).fillna(False)
    p["conflict"] = p["conflict"] | p["conflict_app"]
    p["order_issue"] = p["order_issue"] | p["order_issue_app_ent"]
    p["streamlined"] = p["sb35"] | p["sb35_app"]
    return p


def match_rate(projects: pd.DataFrame) -> dict:
    """Share of projects whose rows span more than one reporting year (i.e. a cross-year link
    was made), plus counts by match_method."""
    n = len(projects)
    cross = int((projects["n_years"] > 1).sum()) if n else 0
    return {
        "projects": n,
        "cross_year_projects": cross,
        "cross_year_rate": cross / n if n else 0.0,
        "by_method": projects["match_method"].value_counts().to_dict() if n else {},
    }
