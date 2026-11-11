"""Link entitlement approvals to housing building permits on the same parcel, using the
rows energov.py pulled from a city's public permit portal.

Prototype, not legal or financial advice. A long wait here does not prove the city caused
it: the portal can't separate city delay from applicant delay.

Every rule below is an ASSUMPTION made by the team. None is a city or HCD definition.
  * Which plan types count as entitlements, which statuses count as approved, and which
    permit types count as housing: the lists in data/portal/cities.json.
  * "Entitlement date" = the plan record's `completed` date. What the city means by that
    date is unknown.
  * A permit is linked to every approved entitlement on the same parcel that completed on
    or before the permit was issued (or before today, if it has not been issued). Nothing
    in the search results says which entitlement belongs to which permit, so an unrelated
    earlier approval on the same parcel can be linked by mistake.
  * Headline wait = LAST such entitlement -> permit issued, following HCD's "completed
    entitlement" (all approvals received). The FIRST entitlement date is kept too.

Run:  python portal_link.py --city laguna_beach
"""
import argparse
import csv
import datetime as dt
import statistics
from collections import defaultdict

from energov import PORTAL, ROOT, load_city, read_csv

OUT_FIELDS = ["permit_key", "permit_type", "parcel_key", "outcome", "n_entitlements",
              "entitlement_types", "ent_first", "ent_last", "permit_applied", "permit_issued",
              "days_last_ent_to_issue", "days_first_ent_to_issue", "days_waiting_so_far"]


def _d(s):
    return dt.date.fromisoformat(s) if s else None


def parcel(r: dict) -> str:
    """Parcel number hash, or the address hash when the portal has no parcel number."""
    return r["apn_key"] or r["addr_key"]


def is_entitlement(r: dict, city: dict) -> bool:
    return (r["case_type"].startswith(tuple(city["entitlement_plan_type_prefixes"]))
            and r["work_class"] not in city["entitlement_exclude_work_classes"]
            and r["status"] in city["entitlement_approved_statuses"]
            and bool(r["completed"]))


def link(plans: list[dict], permits: list[dict], city: dict, today: dt.date) -> list[dict]:
    ents = defaultdict(list)
    for r in plans:
        if is_entitlement(r, city) and parcel(r):
            ents[parcel(r)].append(r)
    dead = set(city.get("permit_dead_statuses", []))
    out = []
    for p in permits:
        if p["case_type"] not in city["housing_permit_types"] or p["status"] in dead:
            continue
        issued = _d(p["issued"])
        cutoff = issued or today
        found = sorted((e for e in ents.get(parcel(p), []) if _d(e["completed"]) <= cutoff),
                       key=lambda e: e["completed"])
        row = dict.fromkeys(OUT_FIELDS, "")
        row.update(permit_key=p["record_key"], permit_type=p["case_type"], parcel_key=parcel(p),
                   permit_applied=p["applied"], permit_issued=p["issued"], n_entitlements=len(found))
        if not found:
            row["outcome"] = "no entitlement found"
        else:
            first, last = _d(found[0]["completed"]), _d(found[-1]["completed"])
            row.update(ent_first=first.isoformat(), ent_last=last.isoformat(),
                       entitlement_types="; ".join(sorted({e["case_type"] for e in found})))
            if issued:
                row.update(outcome="issued", days_last_ent_to_issue=(issued - last).days,
                           days_first_ent_to_issue=(issued - first).days)
            else:
                row.update(outcome="no permit issued yet", days_waiting_so_far=(today - last).days)
        out.append(row)
    return out


def summarize(rows: list[dict]) -> list[str]:
    lines = [f"{'permit type':44s} {'permits':>7s} {'linked+issued':>13s} {'median mo':>9s} "
             f"{'middle half (mo)':>17s} {'waiting':>7s} {'no ent.':>7s}"]
    groups = defaultdict(list)
    for r in rows:
        groups[r["permit_type"]].append(r)
        groups["ALL HOUSING TYPES"].append(r)
    for name, rs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        mo = sorted(r["days_last_ent_to_issue"] / 30.44 for r in rs if r["outcome"] == "issued")
        waiting = sum(r["outcome"] == "no permit issued yet" for r in rs)
        none = sum(r["outcome"] == "no entitlement found" for r in rs)
        if len(mo) >= 2:
            q = statistics.quantiles(mo, n=4, method="inclusive")
            med, mid = f"{statistics.median(mo):9.1f}", f"{q[0]:6.1f} to {q[2]:5.1f}"
        elif mo:
            med, mid = f"{mo[0]:9.1f}", "n/a"
        else:
            med, mid = "unknown", "n/a"
        lines.append(f"{name[:44]:44s} {len(rs):7d} {len(mo):13d} {med:>9s} {mid:>17s} {waiting:7d} {none:7d}")
    return lines


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--city", required=True)
    a = ap.parse_args()
    city = load_city(a.city)
    for k in ("entitlement_plan_type_prefixes", "entitlement_approved_statuses", "housing_permit_types"):
        if not city.get(k):
            raise SystemExit(f"cities.json: '{k}' is empty for {a.city}. Run energov.py --list-types and fill it.")
    plans = read_csv(PORTAL / f"{a.city}_plans.csv")
    permits = read_csv(PORTAL / f"{a.city}_permits.csv")
    rows = link(plans, permits, city, dt.date.today())
    out = PORTAL / f"{a.city}_ent_to_permit.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"{city['name']}: entitlement -> building permit (ASSUMPTION-based link; see file header)")
    print(f"Plans {len(plans)}, permits {len(permits)}, housing permits considered {len(rows)}")
    print("\n".join(summarize(rows)))
    print(f"-> {out.relative_to(ROOT)}")
