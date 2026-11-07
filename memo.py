"""Claude board memo from structured numbers, with a guard that every number in the memo
appears in the input. Key comes from the ANTHROPIC_API_KEY environment variable."""
import json
import re
from pathlib import Path

MODEL = "claude-sonnet-5-5"   # the spec asks for a fast Sonnet-class model
BACKUP_PATH = Path(__file__).parent / "data" / "sample" / "memo_backup.md"
DISCLAIMER = "Prototype, not legal or financial advice."

LIMITATIONS = [
    "The data cannot separate city-caused delay from developer-caused delay.",
    "Project complexity is only partly controlled (owner tenure, no ADUs, unit-count range, streamlined split).",
    "The APR has no cancellation data; projects with no next-stage date are 'no further activity reported'.",
    "Only projects whose earlier stage was reported in 2018 or later can be timed, which biases long timelines out.",
    "All dollar figures come from one synthetic deal and are ASSUMPTIONS.",
]

SYSTEM = f"""You write one-page board memos for a nonprofit that builds affordable ownership homes.
You compare two Orange County cities' approval timelines and what the waiting costs.

Rules:
- Use ONLY numbers that appear in the JSON input. Do not compute new numbers, round differently than
  the input already does, or bring in outside facts, statutes, fees or dates.
- If a field is missing, null or labeled "Insufficient evidence", say "unknown" for it.
- Every dollar figure is an ASSUMPTION; say so next to it.
- Report sample sizes and labels next to medians.
- Include a short "Limitations" section listing every item in the input's limitations list.
- No individual project addresses.
- Plain language, under 350 words, headings allowed, no tables.
- End with exactly this line: {DISCLAIMER}"""


def build_memo_input(city_a: str, city_b: str, summary, match: dict, assumptions: dict,
                     comparisons: list[dict], data_end: str) -> dict:
    """Structured numbers only. summary: timelines.summarize() output."""
    def city_block(city):
        rows = summary[summary["city"] == city]
        stages = {}
        for _, r in rows.iterrows():
            ok = r["n"] >= 10
            stages[r["stage_label"]] = {
                "median_months": round(float(r["median"]), 1) if ok else None,
                "ci90_low_months": round(float(r["ci_low"]), 1) if ok else None,
                "ci90_high_months": round(float(r["ci_high"]), 1) if ok else None,
                "approval_batches": int(r["n"]),
                "sample_label": r["label"],
                "still_waiting_batches": int(r["still_waiting"]),
                "share_reported_same_day": round(float(r["same_day_share"]), 2) if ok else None,
            }
        return {"city": city, "stages": stages}

    return {
        "data": f"California HCD Housing Element Annual Progress Reports, Tables A and A2, "
                f"Orange County, reporting years through {data_end[:4]}",
        "city_a": city_block(city_a),
        "city_b": city_block(city_b),
        "cross_year_match_rate_percent": round(100 * match["cross_year_rate"], 1),
        "projects_in_comparison_pool": match["projects"],
        "comparisons": comparisons,
        "assumptions": assumptions,
        "limitations": LIMITATIONS,
        "confidence_interval_percent": 90,
    }


# ---------- number guard ----------
_NUM = re.compile(r"(?<![A-Za-z0-9.])(\$?)(\d[\d,]*(?:\.\d+)?)\s?([kKmM%x×]?)(?![A-Za-z0-9])")
_LIST_MARKER = re.compile(r"^\s*\d+[.)]\s", re.MULTILINE)


def _numbers_in_text(text: str):
    """Yield (display_string, value, tolerance) for each number in free text."""
    text = _LIST_MARKER.sub(" ", text)
    for m in _NUM.finditer(text):
        raw = m.group(2).replace(",", "")
        try:
            num = float(raw)
        except ValueError:
            continue
        decimals = len(raw.split(".")[1]) if "." in raw else 0
        suffix = m.group(3).lower()
        mult = {"k": 1e3, "m": 1e6}.get(suffix, 1.0)
        yield m.group(0).strip(), num * mult, 0.5 * 10 ** (-decimals) * mult, suffix == "%"


def _input_values(obj) -> list[float]:
    vals = []
    if isinstance(obj, bool):
        return vals
    if isinstance(obj, (int, float)):
        vals.append(float(obj))
    elif isinstance(obj, str):
        vals += [v for _, v, _, _ in _numbers_in_text(obj)]
    elif isinstance(obj, dict):
        for k, v in obj.items():
            vals += _input_values(k) + _input_values(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            vals += _input_values(v)
    return vals


def guard(memo: str, memo_input: dict) -> tuple[bool, list[str]]:
    """True if every number in the memo matches a number in the input (at the precision shown).
    Percent figures may also match an input fraction (0.42 -> 42%)."""
    allowed = _input_values(memo_input) + _input_values(DISCLAIMER)
    bad = []
    for shown, val, tol, is_pct in _numbers_in_text(memo):
        cands = allowed + ([a * 100 for a in allowed] if is_pct else [])
        if not any(abs(val - a) <= tol + 1e-9 for a in cands):
            bad.append(shown)
    return (not bad), bad


# ---------- generation ----------
def _text(resp) -> str:
    return "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", "") == "text")


def generate_memo(memo_input: dict, client=None) -> dict:
    """One Claude call. Returns {text, guard_ok, bad_numbers, source}. Never raises:
    on any API failure it returns the saved backup memo (source='backup')."""
    try:
        if client is None:
            import anthropic
            client = anthropic.Anthropic()
        resp = client.beta.messages.create(
            model=MODEL,
            max_tokens=4000,
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=SYSTEM,
            messages=[{"role": "user", "content":
                       "Write the board memo from this JSON input only:\n\n"
                       + json.dumps(memo_input, indent=2, sort_keys=True, default=str)}],
        )
        if getattr(resp, "stop_reason", None) == "refusal":
            raise RuntimeError("model declined")
        text = _text(resp).strip()
        if not text:
            raise RuntimeError("empty response")
        ok, bad = guard(text, memo_input)
        return {"text": text, "guard_ok": ok, "bad_numbers": bad, "source": "claude"}
    except Exception as e:  # demo safety: fall back to the saved memo
        return {"text": load_backup(), "guard_ok": None, "bad_numbers": [],
                "source": "backup", "error": f"{type(e).__name__}: {e}"}


def load_backup() -> str:
    if BACKUP_PATH.exists():
        return BACKUP_PATH.read_text(encoding="utf-8")
    return "No backup memo saved yet.\n\n" + DISCLAIMER
