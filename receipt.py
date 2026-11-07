"""Receipt math: turns months of waiting into dollars and a gap multiplier.

Every dollar figure here rests on assumptions (see Assumptions). Defaults are derived from the
event's SYNTHETIC worked example ($95k gap after a 10-month slip that grew it about 7x), not from
any real project. Every dollar string produced by this module is tagged ASSUMPTION.
"""
from dataclasses import dataclass

STAGES = ("app_to_ent", "ent_to_permit", "permit_to_co")
STAGE_NAMES = {
    "app_to_ent": "Application to approval",
    "ent_to_permit": "Approval to building permit",
    "permit_to_co": "Building permit to move-in",
}
# Stages that happen before the construction loan is normally drawn (ASSUMPTION: loan drawn at permit).
PRE_LOAN_STAGES = ("app_to_ent", "ent_to_permit")

DEFAULT_C = 8_100     # ASSUMPTION: monthly carrying cost per home, derived from the worked example
DEFAULT_G0 = 13_600   # ASSUMPTION: gap per home with no extra delay, derived from the worked example


@dataclass(frozen=True)
class Assumptions:
    c: float          # monthly carrying cost per home once the construction loan is drawn
    c0: float         # monthly carrying cost per home before the loan is drawn
    g0: float         # gap per home with no extra delay
    units: int        # homes in the project
    loan_drawn: bool  # True: every stage costs c. False: pre-permit stages cost c0.
    # g0 is the gap on the BASELINE schedule; only months beyond that baseline add to it.


def _check(months: dict) -> None:
    missing = set(STAGES) - set(months)
    if missing:
        raise ValueError(f"missing stages: {sorted(missing)}")
    for stage in STAGES:
        if months[stage] < 0:
            raise ValueError(f"negative months for {stage}: {months[stage]}")


def stage_rate(stage: str, a: Assumptions) -> float:
    if not a.loan_drawn and stage in PRE_LOAN_STAGES:
        return a.c0
    return a.c


def delay_cost(months: dict, a: Assumptions) -> float:
    """Dollars per home added by waiting: sum over stages of months x monthly cost."""
    _check(months)
    return sum(months[s] * stage_rate(s, a) for s in STAGES)


def extra_cost(months: dict, baseline: dict, a: Assumptions) -> float:
    """Waiting cost per home beyond the baseline schedule. The baseline's own waiting is already
    inside g0, so only the difference is added. Negative when faster than the baseline."""
    return delay_cost(months, a) - delay_cost(baseline, a)


def gap_after(months: dict, baseline: dict, a: Assumptions) -> float:
    return a.g0 + extra_cost(months, baseline, a)


def gap_multiplier(months: dict, baseline: dict, a: Assumptions) -> float:
    if a.g0 <= 0:
        raise ValueError("gap before delay (g0) must be positive to compute a multiplier")
    return gap_after(months, baseline, a) / a.g0


def city_difference(months_a: dict, months_b: dict, a: Assumptions) -> tuple[float, float]:
    """Extra waiting cost of city B over city A, per home and per project, using the same per-stage
    rates as the receipts. Negative means city B is cheaper."""
    per_home = delay_cost(months_b, a) - delay_cost(months_a, a)
    return per_home, per_home * a.units


def money(x: float) -> str:
    sign = "-" if round(x) < 0 else ""
    return f"{sign}${abs(x):,.0f} (ASSUMPTION)"


def receipt_lines(months: dict, baseline: dict, baseline_name: str, a: Assumptions) -> list[str]:
    """Itemized receipt for one city against the baseline schedule, per home. Every dollar line is tagged."""
    _check(months)
    _check(baseline)
    lines = []
    for s_ in STAGES:
        diff = months[s_] - baseline[s_]
        rate = stage_rate(s_, a)
        lines.append(f"{STAGE_NAMES[s_]}: {months[s_]:.1f} months ({diff:+.1f} vs {baseline_name}) "
                     f"x {money(rate)}/month = {money(diff * rate)}")
    extra = extra_cost(months, baseline, a)
    lines.append(f"Extra waiting cost per home vs {baseline_name}: {money(extra)}")
    lines.append(f"Extra waiting cost for {a.units} homes: {money(extra * a.units)}")
    lines.append(f"Gap per home: {money(a.g0)} on {baseline_name}'s schedule -> {money(gap_after(months, baseline, a))}")
    return lines
