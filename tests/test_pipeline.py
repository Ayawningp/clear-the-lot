"""Gates 1-6 and 10: stitching, conflicts, ordering, sample sizes, still waiting, filters.
All fixtures are made up. No network."""
import numpy as np
import pandas as pd

from conftest import a2_row
from clean import clean_a2
from stitch import stitch, ownership_rows
from timelines import durations, summarize, sample_label


def _projects(make_a2, rows):
    return stitch(clean_a2(make_a2(rows)))


# 1. Cross-year link
def test_cross_year_link(make_a2):
    p = _projects(make_a2, [
        a2_row(2021, apn="111-222-33", ent="2021-03-01"),
        a2_row(2023, apn="11122233", bp="2023-02-15"),   # same APN, different formatting
        a2_row(2025, apn="111 222 33", co="2025-01-10"),
    ])
    assert len(p) == 1
    row = p.iloc[0]
    assert row["ent_date"] == pd.Timestamp("2021-03-01")
    assert row["bp_date"] == pd.Timestamp("2023-02-15")
    assert row["co_date"] == pd.Timestamp("2025-01-10")
    assert row["n_years"] == 3
    assert row["match_method"] == "apn"


# 2. Prior APN
def test_prior_apn_link(make_a2):
    p = _projects(make_a2, [
        a2_row(2021, apn="111-222-33", ent="2021-03-01"),
        a2_row(2023, apn="999-888-77", prior="111-222-33", bp="2023-02-15"),
    ])
    assert len(p) == 1
    assert p.iloc[0]["bp_date"] == pd.Timestamp("2023-02-15")
    assert p.iloc[0]["match_method"] == "prior_apn"


def test_different_cities_do_not_link(make_a2):
    p = _projects(make_a2, [
        a2_row(2021, apn="111-222-33", city="TESTVILLE", ent="2021-03-01"),
        a2_row(2023, apn="111-222-33", city="OTHERTOWN", bp="2023-02-15"),
    ])
    assert len(p) == 2


def test_address_link_when_apn_missing(make_a2):
    p = _projects(make_a2, [
        a2_row(2021, apn="111-222-33", addr="12 Example Street", ent="2021-03-01"),
        a2_row(2023, apn="", addr="12  EXAMPLE ST", bp="2023-02-15"),
    ])
    assert len(p) == 1
    assert p.iloc[0]["match_method"] == "address"


# 3. Conflicts
def test_conflict_keeps_earliest_and_flags(make_a2):
    p = _projects(make_a2, [
        a2_row(2023, bp="2023-06-01"),
        a2_row(2023, bp="2023-03-01"),
    ])
    assert len(p) == 1
    assert p.iloc[0]["bp_date"] == pd.Timestamp("2023-03-01")
    assert bool(p.iloc[0]["conflict_bp"]) is True
    assert bool(p.iloc[0]["conflict"]) is True


def test_no_conflict_when_dates_agree(make_a2):
    p = _projects(make_a2, [a2_row(2023, bp="2023-06-01"), a2_row(2023, bp="2023-06-01")])
    assert bool(p.iloc[0]["conflict"]) is False


# 4. Order
def test_out_of_order_flagged_and_excluded(make_a2):
    p = _projects(make_a2, [
        a2_row(2022, ent="2022-05-01"),
        a2_row(2022, bp="2022-01-01"),   # permit before entitlement
    ])
    d = durations(p)
    ent_bp = d[d["stage"] == "ent_bp"]
    assert ent_bp.empty or ent_bp["months"].isna().all()
    assert bool(p.iloc[0]["order_issue"]) is True
    assert (d["months"].dropna() >= 0).all()


# 5. Small samples
def test_small_sample_gives_insufficient_evidence(make_a2):
    rows = [a2_row(2021, apn=f"100-000-{i:02d}", ent=f"2021-01-{i+1:02d}", bp=f"2021-07-{i+1:02d}") for i in range(9)]
    s = summarize(_projects(make_a2, rows), data_end=pd.Timestamp("2025-12-31"))
    r = s[(s["city"] == "TESTVILLE") & (s["stage"] == "ent_bp")].iloc[0]
    assert r["n"] == 9
    assert r["label"] == "Insufficient evidence"
    assert pd.isna(r["median"])


def test_sample_labels():
    assert sample_label(9) == "Insufficient evidence"
    assert sample_label(10) == "Preliminary"
    assert sample_label(19) == "Preliminary"
    assert sample_label(20) == "Moderate"
    assert sample_label(29) == "Moderate"
    assert sample_label(30) == "More reliable"


def test_median_and_ci_with_enough_projects(make_a2):
    rows = [a2_row(2021, apn=f"100-000-{i:02d}", ent=f"2021-01-{i+1:02d}", bp=f"2021-07-{i+1:02d}") for i in range(12)]
    s = summarize(_projects(make_a2, rows), data_end=pd.Timestamp("2025-12-31"))
    r = s[(s["city"] == "TESTVILLE") & (s["stage"] == "ent_bp")].iloc[0]
    assert r["label"] == "Preliminary"
    assert abs(r["median"] - 6.0) < 0.2
    assert r["ci_low"] <= r["median"] <= r["ci_high"]


# 6. Still waiting
def test_entitlement_without_permit_is_still_waiting(make_a2):
    rows = [a2_row(2021, apn=f"100-000-{i:02d}", ent=f"2021-01-{i+1:02d}", bp=f"2021-07-{i+1:02d}") for i in range(10)]
    rows.append(a2_row(2021, apn="555-555-55", ent="2021-03-15"))  # never permitted
    p = _projects(make_a2, rows)
    d = durations(p)
    waiting = d[(d["stage"] == "ent_bp") & d["still_waiting"]]
    assert len(waiting) == 1
    assert waiting["months"].isna().all()   # not a short duration
    s = summarize(p, data_end=pd.Timestamp("2025-12-31"))
    r = s[s["stage"] == "ent_bp"].iloc[0]
    assert r["n"] == 10
    assert r["still_waiting"] == 1


def test_co_without_permit_date_is_not_still_waiting(make_a2):
    p = _projects(make_a2, [a2_row(2021, ent="2021-01-01"), a2_row(2023, co="2023-05-01")])
    d = durations(p)
    assert not d[d["stage"] == "ent_bp"]["still_waiting"].any()


def test_parcels_approved_same_day_count_as_one_batch(make_a2):
    # a made-up 40-lot subdivision: 40 APNs, one entitlement date -> 1 approval batch
    rows = [a2_row(2021, apn=f"200-000-{i:02d}", ent="2021-02-01", bp="2021-08-01") for i in range(40)]
    s = summarize(_projects(make_a2, rows), data_end=pd.Timestamp("2025-12-31"))
    r = s[s["stage"] == "ent_bp"].iloc[0]
    assert r["n"] == 1
    assert r["parcels_finished"] == 40
    assert r["label"] == "Insufficient evidence"


# 10. Filters
def test_renter_and_adu_never_in_ownership(make_a2):
    raw = make_a2([
        a2_row(2022, apn="100-000-01", tenure="Owner", cat="SFA", bp="2022-01-01"),
        a2_row(2022, apn="100-000-02", tenure="Renter", cat="5+", bp="2022-01-01"),
        a2_row(2022, apn="100-000-03", tenure="Owner", cat="ADU", bp="2022-01-01"),
        # same APN as an ownership project: the ADU row must not merge into it
        a2_row(2023, apn="100-000-01", tenure="Owner", cat="ADU", co="2023-01-01"),
        a2_row(2023, apn="100-000-01", tenure="Renter", cat="SFA", co="2023-02-01"),
    ])
    owned = ownership_rows(clean_a2(raw))
    assert set(owned["TENURE"]) == {"Owner"}
    assert "ADU" not in set(owned["UNIT_CAT"])
    p = stitch(owned)
    assert len(p) == 1
    assert pd.isna(p.iloc[0]["co_date"])   # CO came only from ADU / renter rows
