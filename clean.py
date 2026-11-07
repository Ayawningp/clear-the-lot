"""Normalize APR rows: APN to digits, addresses to a standard form, dates to Timestamps.
Raw values stay in their original columns; normalized values go in new lowercase columns."""
import re

import pandas as pd

SUFFIXES = {
    "STREET": "ST", "AVENUE": "AVE", "BOULEVARD": "BLVD", "DRIVE": "DR", "ROAD": "RD",
    "LANE": "LN", "COURT": "CT", "PLACE": "PL", "CIRCLE": "CIR", "PARKWAY": "PKWY",
    "TERRACE": "TER", "HIGHWAY": "HWY", "WAY": "WAY", "NORTH": "N", "SOUTH": "S",
    "EAST": "E", "WEST": "W",
}


def norm_apn(s) -> str:
    """Digits only. Returns '' when there are no digits or only zeros."""
    d = re.sub(r"\D", "", str(s or ""))
    return "" if d.strip("0") == "" else d


def norm_address(s) -> str:
    """Uppercase, punctuation removed, spaces collapsed, common suffixes standardized.
    Keeps only the first line (multi-line fields carry city/ZIP on later lines)."""
    s = str(s or "").upper()
    if s in ("", "NAN", "NONE"):
        return ""
    s = re.sub(r"[.,#]", " ", s)
    words = [SUFFIXES.get(w, w) for w in s.split()]
    return " ".join(words)


def parse_date(s):
    return pd.to_datetime(s, errors="coerce", format="mixed") if str(s).strip() else pd.NaT


def _dates(col: pd.Series) -> pd.Series:
    col = col.astype(str).str.strip().replace({"": None, "nan": None, "None": None})
    return pd.to_datetime(col, errors="coerce", format="mixed").dt.normalize()


def _num(col: pd.Series) -> pd.Series:
    return pd.to_numeric(col, errors="coerce").fillna(0)


def _base(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["city"] = out["JURIS_NAME"].astype(str).str.strip().str.upper()
    out["year"] = pd.to_numeric(out["YEAR"], errors="coerce").astype("Int64")
    out["apn_norm"] = out["APN"].map(norm_apn)
    out["prior_apn_norm"] = out["PRIOR_APN"].map(norm_apn)
    out["addr_norm"] = out["STREET_ADDRESS"].map(norm_address)
    out["UNIT_CAT"] = out["UNIT_CAT"].astype(str).str.strip()
    out["TENURE"] = out["TENURE"].astype(str).str.strip()
    return out


def clean_a2(df: pd.DataFrame) -> pd.DataFrame:
    out = _base(df)
    out["ent_date"] = _dates(out["ENT_APPROVE_DT1"])
    out["bp_date"] = _dates(out["BP_ISSUE_DT1"])
    out["co_date"] = _dates(out["CO_ISSUE_DT1"])
    out["ent_units"] = _num(out["NO_ENTITLEMENTS"])
    out["bp_units"] = _num(out["NO_BUILDING_PERMITS"])
    out["co_units"] = _num(out["NO_OTHER_FORMS_OF_READINESS"])
    out["sb35"] = out["APPROVE_SB35"].astype(str).str.strip().str.upper().isin(["Y", "YES"])
    return out


def clean_a(df: pd.DataFrame) -> pd.DataFrame:
    out = _base(df)
    out["app_date"] = _dates(out["APP_SUBMIT_DT"])
    out["sb35"] = out["APP_SUBMITTED_SB35"].astype(str).str.strip().str.upper().isin(["Y", "YES"])
    return out
