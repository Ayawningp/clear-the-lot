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

Run:  python portal_master.py --city laguna_beach
"""
import argparse
import csv
from collections import Counter, defaultdict

from energov import PORTAL, ROOT, load_city, read_csv

FIELDS = ["site_key", "site_seq", "site_records", "site_addresses", "site_parcels", "addr_key",
          "apn_key", "module", "case_type", "work_class", "status", "applied", "completed",
          "issued", "finaled", "expires", "record_key"]


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


def build(plans: list[dict], permits: list[dict]) -> list[dict]:
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
    rows = build(read_csv(PORTAL / f"{a.city}_plans.csv"), read_csv(PORTAL / f"{a.city}_permits.csv"))
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
