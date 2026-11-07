"""Extract Orange County rows from the statewide APR downloads.

Replaces the spec's fetch.py: the team downloaded the full CSVs from data.ca.gov
once, so the app never calls the API (no scraping, no re-fetching).

Inputs (git-ignored, too big for GitHub):
  data/raw/tablea.csv   APR Table A,  resource c78b769d-cc02-4050-91ef-79ded665b5a8
  data/raw/tablea2.csv  APR Table A2, resource fe505d9b-8c36-42ba-ba30-08bc4f34e022
Outputs (committed, small):
  data/sample/oc_tablea.csv, data/sample/oc_tablea2.csv

Run:  python extract.py
"""
import csv
import hashlib
import sys
from pathlib import Path

from clean import norm_address, norm_apn

ROOT = Path(__file__).parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "sample"

# Columns we keep. Income-band columns are dropped to keep the committed files small.
# APN, PRIOR_APN and STREET_ADDRESS are replaced by one-way hashes (pseudonymize) so the
# public repo carries no addresses or parcel numbers; NOTES, PROJECT_NAME, STD_ADDRESS and
# JURS_TRACKING_ID (a city permit number that can be looked up to find the address) dropped.
KEEP_A = [
    "JURIS_NAME", "CNTY_NAME", "YEAR", "PRIOR_APN", "APN", "STREET_ADDRESS",
    "UNIT_CAT", "TENURE", "APP_SUBMIT_DT",
    "TOT_PROPOSED_UNITS", "TOT_APPROVED_UNITS", "TOT_DISAPPROVED_UNITS",
    "APP_SUBMITTED_SB35", "APPLICATION_STATUS",
]
KEEP_A2 = [
    "JURIS_NAME", "CNTY_NAME", "YEAR", "PRIOR_APN", "APN", "STREET_ADDRESS",
    "UNIT_CAT", "TENURE",
    "ENT_APPROVE_DT1", "NO_ENTITLEMENTS",
    "BP_ISSUE_DT1", "NO_BUILDING_PERMITS",
    "CO_ISSUE_DT1", "NO_OTHER_FORMS_OF_READINESS",
    "APPROVE_SB35",
]


def _hash(s: str, digits_only: bool) -> str:
    """One-way key so the public sample carries no addresses or parcel numbers.
    Equal inputs give equal keys, which is all stitching needs."""
    if not s:
        return ""
    h = hashlib.sha256(s.encode("utf-8")).hexdigest()
    return str(int(h[:15], 16)) if digits_only else "H" + h[:16].upper()


def pseudonymize(row: dict) -> dict:
    row["APN"] = _hash(norm_apn(row["APN"]), digits_only=True)
    row["PRIOR_APN"] = _hash(norm_apn(row["PRIOR_APN"]), digits_only=True)
    row["STREET_ADDRESS"] = _hash(norm_address(row["STREET_ADDRESS"]), digits_only=False)
    return row


def extract(src: Path, dst: Path, keep: list[str], county: str = "Orange") -> int:
    csv.field_size_limit(10**9)
    n = 0
    with open(src, newline="", encoding="utf-8", errors="replace") as f_in, \
         open(dst, "w", newline="", encoding="utf-8") as f_out:
        reader = csv.DictReader(f_in)
        missing = [c for c in keep if c not in reader.fieldnames]
        if missing:
            sys.exit(f"{src.name}: missing expected columns {missing}. Re-check docs/fields.md.")
        writer = csv.DictWriter(f_out, fieldnames=keep)
        writer.writeheader()
        for row in reader:
            if row["CNTY_NAME"].strip().lower() == county.lower():
                # collapse embedded newlines, then drop identifying values
                writer.writerow(pseudonymize({k: " ".join(row[k].split()) for k in keep}))
                n += 1
    return n


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    na = extract(RAW / "tablea.csv", OUT / "oc_tablea.csv", KEEP_A)
    na2 = extract(RAW / "tablea2.csv", OUT / "oc_tablea2.csv", KEEP_A2)
    print(f"Table A:  {na} Orange County rows -> data/sample/oc_tablea.csv")
    print(f"Table A2: {na2} Orange County rows -> data/sample/oc_tablea2.csv")
