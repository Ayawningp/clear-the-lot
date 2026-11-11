"""Merge a city's pulled plans and permits into one master CSV, grouped by site, so every
dated step at a property can be read top to bottom.

A site is every address key and parcel key that any record connects. If one record has
address A on parcel P and another has address B on parcel P, then A, B and P are one site.
This keeps a main house and its ADU address, or a lot before and after a split, together.
ASSUMPTION: a shared address or parcel means the same property. That can over-merge, for
example a large multi-unit parcel or a wrongly entered parcel number chaining sites
together; `site_addresses` and `site_parcels` show how many keys each site joined, so big
ones can be checked.

One row per portal record. Rows are sorted by site, then by applied date. `site_seq` numbers
the records at a site in that order and `site_records` is how many it has. All keys are
one-way hashes; no address or parcel number is stored. Records the portal lists with neither
an address nor a parcel keep a blank site key and sort last.

Durations (days; blank when a date is missing or the row is the wrong kind):
  * `days_apply_to_approval`: plans only, applied -> completed. `is_entitlement` says whether
    the plan counts as an approved entitlement under the lists in data/portal/cities.json.
  * `days_apply_to_issue`: permits only, applied -> issued.
  * `days_approval_to_permit`: housing permits only (`is_housing_permit`), from
    `approval_date` -> issued. `approval_date` is the LAST approved entitlement completed at
    the same site on or before the permit was issued (or before today if not yet issued).
ASSUMPTION: the same team-made rules as portal_link.py, except that this file matches by
site, not by parcel alone, so its counts differ slightly from the ent_to_permit file. An
unrelated earlier approval at the same site can be picked up by mistake.

Run:  python portal_master.py --city laguna_beach
"""
import argparse
import csv
import datetime as dt
from collections import Counter, defaultdict

from energov import PORTAL, ROOT, load_city, read_csv
from portal_link import is_entitlement

FIELDS = ["site_key", "site_seq", "site_records", "site_addresses", "site_parcels", "addr_key",
          "apn_key", "module", "case_type", "work_class", "status", "applied", "completed",
          "issued", "finaled", "expires", "is_entitlement", "days_apply_to_approval",
          "is_housing_permit", "days_apply_to_issue", "approval_date",
          "days_approval_to_permit", "record_key"]


def _days(start: str, end: str):
    if not start or not end:
        return ""
    return (dt.date.fromisoformat(end) - dt.date.fromisoformat(start)).days


def add_durations(rows: list[dict], city: dict, today: dt.date) -> None:
    """Fill the duration columns in place. Rows must already carry `site_key`."""
    approvals = defaultdict(list)  # site -> completed dates of approved entitlements
    dead = set(city.get("permit_dead_statuses", []))
    for r in rows:
        plan = r["module"] == "plans"
        ent = plan and is_entitlement(r, city)
        r["is_entitlement"] = ("yes" if ent else "no") if plan else ""
        r["days_apply_to_approval"] = _days(r["applied"], r["completed"]) if plan else ""
        r["days_apply_to_issue"] = "" if plan else _days(r["applied"], r["issued"])
        housing = not plan and r["case_type"] in city["housing_permit_types"] and r["status"] not in dead
        r["is_housing_permit"] = "" if plan else ("yes" if housing else "no")
        if ent and r["site_key"]:
            approvals[r["site_key"]].append(r["completed"])
    for r in rows:
        r["approval_date"] = r["days_approval_to_permit"] = ""
        if r["is_housing_permit"] != "yes":
            continue
        cutoff = r["issued"] or today.isoformat()
        before = [d for d in approvals.get(r["site_key"], []) if d <= cutoff]
        if before:
            r["approval_date"] = max(before)
            r["days_approval_to_permit"] = _days(r["approval_date"], r["issued"])


def site_keys(rows: list[dict]) -> dict:
    """Map every address key and parcel key to its site (connected group of keys)."""
    parent = {}

    def find(k):
        parent.setdefault(k, k)
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    for r in rows:
        keys = [k for k in (r["addr_key"], r["apn_key"]) if k]
        for k in keys:
            find(k)
        if len(keys) == 2:
            x, y = find(keys[0]), find(keys[1])
            if x != y:
                parent[max(x, y)] = min(x, y)  # smallest key is the root: stable across runs
    return {k: find(k) for k in parent}


def build(plans: list[dict], permits: list[dict], city: dict, today: dt.date) -> list[dict]:
    rows = plans + permits
    root = site_keys(rows)
    addrs, parcels, counts = defaultdict(set), defaultdict(set), Counter()
    for r in rows:
        r["site_key"] = "S" + root[r["addr_key"] or r["apn_key"]] if (r["addr_key"] or r["apn_key"]) else ""
        counts[r["site_key"]] += 1
        if r["addr_key"]:
            addrs[r["site_key"]].add(r["addr_key"])
        if r["apn_key"]:
            parcels[r["site_key"]].add(r["apn_key"])
    add_durations(rows, city, today)
    rows.sort(key=lambda r: (r["site_key"] == "", r["site_key"], r["applied"], r["module"]))
    out, seq, prev = [], 0, None
    for r in rows:
        s = r["site_key"]
        seq = seq + 1 if s == prev else 1
        prev = s
        out.append({**{k: r.get(k, "") for k in FIELDS}, "site_seq": seq, "site_records": counts[s],
                    "site_addresses": len(addrs[s]) if s else "", "site_parcels": len(parcels[s]) if s else ""})
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--city", required=True)
    a = ap.parse_args()
    city = load_city(a.city)
    rows = build(read_csv(PORTAL / f"{a.city}_plans.csv"), read_csv(PORTAL / f"{a.city}_permits.csv"),
                 city, dt.date.today())
    out = PORTAL / f"{a.city}_master.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    keyed = [r for r in rows if r["site_key"]]
    sites = {r["site_key"]: r for r in keyed}
    both = ({r["site_key"] for r in keyed if r["module"] == "plans"}
            & {r["site_key"] for r in keyed if r["module"] == "permits"})
    merged = [r for r in sites.values() if r["site_addresses"] > 1 or r["site_parcels"] > 1]
    big = max(sites.values(), key=lambda r: r["site_addresses"] + r["site_parcels"])
    print(f"{city['name']}: {len(rows)} records at {len(sites)} sites "
          f"({len(both)} have both a plan and a permit; {len(rows) - len(keyed)} records have no key)")
    print(f"{len(merged)} sites join more than one address or parcel; the largest joins "
          f"{big['site_addresses']} addresses and {big['site_parcels']} parcels ({big['site_records']} records)")
    print(f"-> {out.relative_to(ROOT)}")
