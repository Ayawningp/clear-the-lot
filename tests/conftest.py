import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

A2_COLS = [
    "JURIS_NAME", "CNTY_NAME", "YEAR", "PRIOR_APN", "APN", "STREET_ADDRESS",
    "UNIT_CAT", "TENURE",
    "ENT_APPROVE_DT1", "NO_ENTITLEMENTS",
    "BP_ISSUE_DT1", "NO_BUILDING_PERMITS",
    "CO_ISSUE_DT1", "NO_OTHER_FORMS_OF_READINESS",
    "APPROVE_SB35", "STD_ADDRESS",
]


def a2_row(year, apn="111-222-33", city="TESTVILLE", ent="", bp="", co="",
           prior="", addr="1 MADE UP STREET", cat="SFA", tenure="Owner", units=1):
    """One made-up APR Table A2 row (fixture only; not a real project)."""
    return {
        "JURIS_NAME": city, "CNTY_NAME": "Orange", "YEAR": str(year),
        "PRIOR_APN": prior, "APN": apn, "STREET_ADDRESS": addr,
        "UNIT_CAT": cat, "TENURE": tenure,
        "ENT_APPROVE_DT1": ent, "NO_ENTITLEMENTS": str(units if ent else 0),
        "BP_ISSUE_DT1": bp, "NO_BUILDING_PERMITS": str(units if bp else 0),
        "CO_ISSUE_DT1": co, "NO_OTHER_FORMS_OF_READINESS": str(units if co else 0),
        "APPROVE_SB35": "N", "STD_ADDRESS": "",
    }


@pytest.fixture
def make_a2():
    def _make(rows):
        return pd.DataFrame(rows, columns=A2_COLS).astype(str)
    return _make
