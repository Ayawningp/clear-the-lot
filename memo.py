"""Claude board memo comparing two cities, plus a guard that rejects any number not in the input."""
import json
import os
import re

NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")

LIMITATIONS = [
    "The data cannot separate city-caused delay from developer-caused delay.",
    "Project complexity is only partly controlled (owner tenure, size range, streamlined split).",
    "The progress reports do not record cancellations; stalled projects show as 'no further activity reported'.",
    "Dollar figures come from one synthetic example deal and are assumptions.",
]

SYSTEM = (
    "You write a one-page memo for a housing nonprofit's board comparing two cities' approval timelines. "
    "Use ONLY numbers that appear in the JSON you are given, written exactly as given (no rounding, "
    "no new numbers, no percentages you compute). If something is missing, say it is unknown. "
    "Call every dollar figure an assumption. Include every item in 'limitations'. "
    "Plain language, under 250 words. End with: Prototype, not legal or financial advice."
)


def _canonical(token: str) -> str:
    value = float(token.replace(",", ""))
    return str(int(value)) if value.is_integer() else repr(value)


def numbers_in_input(obj) -> set[str]:
    found: set[str] = set()
    if isinstance(obj, dict):
        for value in obj.values():
            found |= numbers_in_input(value)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            found |= numbers_in_input(value)
    elif isinstance(obj, bool):
        pass
    elif isinstance(obj, (int, float)):
        found.add(_canonical(str(obj)))
    elif isinstance(obj, str):
        found |= {_canonical(t) for t in NUMBER.findall(obj)}
    return found


def unsupported_numbers(text: str, payload) -> list[str]:
    allowed = numbers_in_input(payload)
    seen = []
    for token in NUMBER.findall(text):
        value = _canonical(token)
        if value not in allowed and value not in seen:
            seen.append(value)
    return seen


def generate_memo(payload: dict) -> str:
    """Calls the Claude API. Needs ANTHROPIC_API_KEY in the environment."""
    import anthropic  # imported here so the guard and its tests run without the SDK installed

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=os.environ.get("MEMO_MODEL", "claude-sonnet-5-5"),
        max_tokens=800,
        system=SYSTEM,
        messages=[{"role": "user", "content": json.dumps(payload, indent=2)}],
    )
    return response.content[0].text
