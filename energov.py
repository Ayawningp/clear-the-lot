"""Pull permit and plan (entitlement) records from a city's public Tyler EnerGov
Citizen Self Service portal, one month at a time.

Prototype. Read-only: it runs the same search the public search page runs. It files nothing
and contacts no one.

Polite by design (ground rules: no scraping at volume):
  * one request every `delay_seconds` (default 4), 100 rows per page (the portal's own maximum)
  * each finished month is cached, so a re-run never re-requests it (use --refresh to force)
  * stops on the first block-like response (403/429) instead of retrying

Privacy: addresses and parcel numbers are replaced by the same one-way hashes extract.py
uses, so rows can be stitched (and joined to the APR sample) without storing either. Permit
numbers, project names and descriptions are never written to disk.

Add a city in data/portal/cities.json. Run:
  python energov.py --city laguna_beach --start 2025-01 --end 2025-06
  python energov.py --city laguna_beach --start 2025-01 --end 2025-01 --list-types
"""
import argparse
import calendar
import copy
import csv
import datetime as dt
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from clean import norm_address, norm_apn
from extract import _hash

ROOT = Path(__file__).parent
PORTAL = ROOT / "data" / "portal"
UA = "Mozilla/5.0 (research prototype; low-rate)"
PAGE_SIZE = 100

# EnerGov search modules. id = the portal's SearchModule/FilterModule value; `criteria` = the
# block of the search form to fill; `sort` = the portal's own "sort by number" key.
MODULES = {
    "permits": {"id": 2, "criteria": "PermitCriteria", "type": "PermitTypeId",
                "status": "PermitStatusId", "sort": "PermitNumber.keyword"},
    "plans": {"id": 3, "criteria": "PlanCriteria", "type": "PlanTypeId",
              "status": "PlanStatusId", "sort": "PlanNumber.keyword"},
}
FIELDS = ["record_key", "module", "apply_month", "case_type", "work_class", "status",
          "applied", "issued", "finaled", "completed", "expires", "apn_key", "addr_key"]


def load_city(key: str) -> dict:
    cities = json.loads((PORTAL / "cities.json").read_text(encoding="utf-8"))
    if key not in cities or key.startswith("_"):
        sys.exit(f"Unknown city '{key}'. Known: {[k for k in cities if not k.startswith('_')]}")
    return cities[key]


class EnerGov:
    def __init__(self, city: dict):
        self.base = city["base_url"].rstrip("/")
        self.api = self.base + "/api"
        self.delay = city.get("delay_seconds", 4)
        self.requests = 0
        self.headers = {"User-Agent": UA, "Accept": "application/json, text/plain, */*",
                        "Content-Type": "application/json;charset=UTF-8",
                        "Origin": self.base.split("/apps/")[0], "Referer": self.base}
        # The tenant id and name differ per city; the portal publishes them.
        tenants = [t for t in self._call("/tenants/gettenantslist") if t.get("IsActive")]
        if len(tenants) != 1:
            sys.exit(f"Expected one active tenant, found {[t['TenantName'] for t in tenants]}.")
        t = tenants[0]
        self.headers.update({"tenantId": str(t["TenantID"]), "tenantName": t["TenantName"],
                             "Tyler-TenantUrl": t["TenantUrl"], "Tyler-Tenant-Culture": "en-US"})
        self.criteria = self._call("/energov/search/criteria")  # the portal's blank search form

    def _call(self, path: str, body: dict | None = None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.api + path, data=data, headers=self.headers,
                                     method="POST" if body is not None else "GET")
        for attempt in (1, 2, 3):
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    out = json.load(resp)
                break
            except urllib.error.HTTPError as e:
                if e.code in (403, 429):
                    sys.exit(f"HTTP {e.code}: the portal may be blocking us. Stopping; do not retry soon.")
                if attempt == 3:
                    sys.exit(f"HTTP {e.code} three times on {path}. Stopping.")
                time.sleep(30)
            except OSError as e:  # dropped or reset connection, timeout, DNS
                # A reset can be the portal's way of saying "slow down": back off for minutes.
                if attempt == 3:
                    sys.exit(f"Network error three times on {path}: {e}. Stopping.")
                print(f"  connection problem ({e}); waiting {90 * attempt}s", flush=True)
                time.sleep(90 * attempt)
        self.requests += 1
        time.sleep(self.delay)
        if not out.get("Success"):
            sys.exit(f"Portal refused {path}: {out.get('ErrorMessage')}")
        return out["Result"]

    def search(self, module: str, d_from: str, d_to: str, page: int) -> dict:
        m = MODULES[module]
        paging = dict(PageNumber=page, PageSize=PAGE_SIZE, SortAscending=True, SortBy=m["sort"])
        body = copy.deepcopy(self.criteria)
        body.update(SearchModule=m["id"], FilterModule=m["id"], ExactMatch=True, **paging)
        # Type and status must be "none", not null: the portal's own page sends that, and the
        # server answers HTTP 500 without it.
        body[m["criteria"]].update({m["type"]: "none", m["status"]: "none",
                                    "ApplyDateFrom": d_from, "ApplyDateTo": d_to}, **paging)
        return self._call("/energov/search/search", body)


def _day(s) -> str:
    return s[:10] if s else ""


def to_row(e: dict, module: str) -> dict:
    """Keep type, status and dates. Hash the identifiers. Drop everything else."""
    return {
        "record_key": hashlib.sha256(e["CaseId"].encode()).hexdigest()[:16],
        "module": module,
        "apply_month": (e.get("ApplyDate") or "")[:7],
        "case_type": e.get("CaseType") or "",
        "work_class": e.get("CaseWorkclass") or "",
        "status": e.get("CaseStatus") or "",
        "applied": _day(e.get("ApplyDate")),
        "issued": _day(e.get("IssueDate")),
        "finaled": _day(e.get("FinalDate")),
        "completed": _day(e.get("CompleteDate")),
        "expires": _day(e.get("ExpireDate")),
        "apn_key": _hash(norm_apn(e.get("MainParcel")), digits_only=True),
        "addr_key": _hash(norm_address(e.get("AddressDisplay")), digits_only=False),
    }


def fetch_month(client: EnerGov, module: str, year: int, month: int) -> list[dict]:
    # Pad a day each side because the server's time zone handling is unknown, then keep
    # exactly the rows whose applied date falls in the month.
    last = calendar.monthrange(year, month)[1]
    d_from = (dt.date(year, month, 1) - dt.timedelta(days=1)).isoformat() + "T00:00:00.000Z"
    d_to = (dt.date(year, month, last) + dt.timedelta(days=2)).isoformat() + "T00:00:00.000Z"
    tag, rows, seen, page = f"{year}-{month:02d}", [], set(), 1
    while True:
        res = client.search(module, d_from, d_to, page)
        for e in res.get("EntityResults") or []:
            row = to_row(e, module)
            if row["apply_month"] == tag and row["record_key"] not in seen:
                seen.add(row["record_key"])
                rows.append(row)
        pages = res.get("TotalPages") or 0
        print(f"  {module} {tag} page {page}/{pages}: {len(rows)} kept", flush=True)
        if page >= pages:
            return rows
        page += 1


def months(start: str, end: str):
    y, m = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    while (y, m) <= (ey, em):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def run(city_key: str, modules: list[str], start: str, end: str, refresh: bool) -> None:
    city = load_city(city_key)
    if city.get("platform") != "energov":
        sys.exit(f"{city_key} is not an EnerGov portal.")
    cache = PORTAL / "cache" / city_key
    cache.mkdir(parents=True, exist_ok=True)
    client = None
    for module in modules:
        for y, m in months(start, end):
            f = cache / f"{module}_{y}-{m:02d}.csv"
            if f.exists() and not refresh:
                continue
            client = client or EnerGov(city)  # only connect if something is missing
            write_csv(f, fetch_month(client, module, y, m))
        # Rebuild the combined file from every cached month, de-duplicated.
        seen, rows = set(), []
        for f in sorted(cache.glob(f"{module}_*.csv")):
            for r in read_csv(f):
                if r["record_key"] not in seen:
                    seen.add(r["record_key"])
                    rows.append(r)
        out = PORTAL / f"{city_key}_{module}.csv"
        write_csv(out, rows)
        span = f"{rows[0]['apply_month']} to {rows[-1]['apply_month']}" if rows else "no rows"
        print(f"{module}: {len(rows)} rows ({span}) -> {out.relative_to(ROOT)}", flush=True)
    print(f"{client.requests if client else 0} requests sent to {city['name']}'s portal.")


def list_types(city_key: str, modules: list[str]) -> None:
    from collections import Counter
    for module in modules:
        f = PORTAL / f"{city_key}_{module}.csv"
        if not f.exists():
            continue
        rows = read_csv(f)
        print(f"\n{module}: type / work class (count)")
        for (t, w), n in Counter((r["case_type"], r["work_class"]) for r in rows).most_common():
            print(f"  {n:5d}  {t}  /  {w}")
        print(f"{module}: status (count)")
        for s, n in Counter(r["status"] for r in rows).most_common():
            print(f"  {n:5d}  {s}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--city", required=True)
    p.add_argument("--modules", nargs="+", default=["plans", "permits"], choices=list(MODULES))
    p.add_argument("--start", required=True, help="first applied month, YYYY-MM")
    p.add_argument("--end", required=True, help="last applied month, YYYY-MM")
    p.add_argument("--refresh", action="store_true", help="re-request months already cached")
    p.add_argument("--list-types", action="store_true", help="print types and statuses found")
    a = p.parse_args()
    run(a.city, a.modules, a.start, a.end, a.refresh)
    if a.list_types:
        list_types(a.city, a.modules)
