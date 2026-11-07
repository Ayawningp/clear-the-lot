"""Turn stage durations into the dollars they add to the funding gap.

Defaults are derived from the event's synthetic worked example
(the event repo's lanes/3-fund-it/data/synthetic-example-deal.json and docs/background.md): a 10-month slip
grew the fundraising gap "about 7 times" to $95k. So the gap before was about
$95k / 7 = $13.6k and the slip added about $81.4k, about $8.1k per month.
These are ASSUMPTIONS, not measurements. "About 7x" is rounded, so the true values are uncertain.
"""
from timelines import STAGE_LABELS

DEFAULTS = {
    "c": {"value": 8100, "label": "ASSUMPTION",
          "basis": "Monthly carrying cost per home once the construction loan is drawn. "
                   "Derived: ($95k - $95k/7) / 10 months, from the event's synthetic worked example."},
    "c0": {"value": 8100, "label": "ASSUMPTION",
           "basis": "Monthly carrying cost per home before the loan is drawn. No source; "
                    "defaults to c until the user enters their own figure."},
    "g0": {"value": 13600, "label": "ASSUMPTION",
           "basis": "Gap per home with no extra delay. Derived: $95k / 7, from the event's "
                    "synthetic worked example."},
}
PRE_PERMIT = {"app_ent", "ent_bp"}
SUMMABLE = ["app_ent", "ent_bp", "bp_co"]   # ent_co overlaps these, so it is never added in


def money(x: float) -> str:
    """Every dollar figure in the app goes through here, so every one carries the tag."""
    sign = "-" if x < 0 else ""
    x = abs(x)
    if x >= 1_000_000:
        s = f"${x / 1_000_000:.2f}M"
    elif x >= 1000:
        s = f"${x / 1000:.1f}k"
    else:
        s = f"${x:,.0f}"
    return f"{sign}{s} [ASSUMPTION]"


def receipt(stage_months: dict, c: float, c0: float, g0: float, units: int = 1,
            loan_not_drawn: bool = False, baseline: dict | None = None,
            stages: list[str] | None = None) -> dict:
    """baseline: months per stage already priced into G0 (e.g. the countywide median).
    Only months beyond the baseline are charged; a faster-than-baseline city gets a negative
    line (it shrinks the gap). With no baseline, every month is charged (the spec's formula)."""
    baseline = baseline or {}
    stages = stages or SUMMABLE
    lines = []
    total = 0.0
    for stage in stages:
        m = stage_months.get(stage)
        if m is None or m != m:   # missing or NaN -> unknown, not zero
            continue
        base = baseline.get(stage, 0.0)
        extra = m - base
        use_c0 = loan_not_drawn and stage in PRE_PERMIT
        rate = c0 if use_c0 else c
        cost = extra * rate
        total += cost
        lines.append({"stage": stage, "label": STAGE_LABELS[stage], "months": m, "baseline": base,
                      "extra": extra, "rate": rate, "cost": cost, "rate_name": "c0" if use_c0 else "c"})
    gap_after = g0 + total
    return {
        "lines": lines,
        "delay_cost": total,
        "gap_before": g0,
        "gap_after": gap_after,
        "multiplier": gap_after / g0 if g0 else float("nan"),
        "units": units,
        "delay_cost_project": total * units,
        "gap_after_project": gap_after * units,
        "missing_stages": [s for s in stages if stage_months.get(s) is None
                           or stage_months.get(s) != stage_months.get(s)],
    }


def city_difference(months_a: float, months_b: float, c: float) -> float:
    """Per home: what city B's extra months cost compared with city A."""
    return (months_b - months_a) * c


def receipt_lines(r: dict) -> list[str]:
    out = []
    for ln in r["lines"]:
        if ln["baseline"]:
            out.append(f"{ln['label']}: {ln['months']:.1f} months vs {ln['baseline']:.1f} typical "
                       f"= {ln['extra']:+.1f} months x {money(ln['rate'])}/month = {money(ln['cost'])}")
        else:
            out.append(f"{ln['label']}: {ln['months']:.1f} months x {money(ln['rate'])}/month "
                       f"= {money(ln['cost'])}")
    for s in r["missing_stages"]:
        out.append(f"{STAGE_LABELS[s]}: unknown (not enough data); not counted")
    out.append(f"Delay cost per home: {money(r['delay_cost'])}")
    out.append(f"Gap per home: {money(r['gap_before'])} before delay -> {money(r['gap_after'])} after "
               f"({r['multiplier']:.1f}x)")
    out.append(f"Whole project ({r['units']} homes): delay cost {money(r['delay_cost_project'])}, "
               f"gap {money(r['gap_after_project'])}")
    return out
