# Delay Receipt: screens hand-off

The screens run today on MOCK data. Real data appears automatically once `stitch.py` writes
`data/processed/durations.csv` in the format below.

## Run it

```bash
pip install -r requirements.txt
python -m pytest -q          # 33 tests, all offline
streamlit run app.py
export ANTHROPIC_API_KEY=... # only needed for the memo button
```

## The one contract the builder must meet

`data/processed/durations.csv`, one row per project per stage:

| column | type | meaning |
|---|---|---|
| city | text | jurisdiction name |
| project_id | text | stitched project key |
| stage | text | `app_to_ent`, `ent_to_permit` or `permit_to_co` |
| months | number | duration in months; empty when status is `waiting` |
| status | text | `done` (both dates known) or `waiting` (start known, no end yet) |

Rules the summary code enforces (it raises an error rather than guessing):

- no negative months: stitch must flag and drop out-of-order dates first
- every `done` row has a duration
- owner-tenure, non-ADU projects only (filter before writing the file)

## What is where

| file | does | tested by |
|---|---|---|
| receipt.py | waiting cost vs a baseline schedule, gap multiplier, tagged dollar strings | tests/test_receipt.py |
| timelines.py | medians, 90% bootstrap intervals, sample-size labels, waiting counts | tests/test_timelines.py, tests/test_screen_helpers.py |
| memo.py | Claude memo + guard that flags any number not in the input | tests/test_memo_guard.py |
| mock_data.py | invented "City A (MOCK)" / "City B (MOCK)" data | tests/test_screen_helpers.py |
| app.py | four tabs: Timelines, Receipt, Compare, Limitations | tests/test_app_smoke.py (plumbing only, not layout) |

## The model, in one line

gap per home = gap on the baseline schedule (default $13.6k, ASSUMPTION) + (this city's waiting cost
- the baseline city's waiting cost), at $8.1k per month (ASSUMPTION). Both defaults are derived from
the event's synthetic worked example. The baseline defaults to the fastest city in the data.

## Not yet done

- fetch.py, clean.py, stitch.py (builder, per the spec doc)
- Kaplan-Meier (stretch)
- `data/sample/memo_backup.md`: save one good memo once the API works
- the app has not been opened in a real browser yet: check layout first thing
