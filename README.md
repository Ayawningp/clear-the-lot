# Delay Receipt

**Waiting barely raises the price of an affordable home. It multiplies the funding gap. The Delay Receipt shows by how much, city by city.**

Repo: `clear-the-lot` · Claude Impact Lab: UCI × SoCal Affordable Housing · Lane 2: **Clear it**

> Prototype, not legal or financial advice.

---

## Who it's for

A nonprofit project manager with a small affordable *ownership* project that could go in one of two Orange County cities (event scenario C02).

- **Before:** they choose a city on reputation and anecdotes. Nobody can give a realistic approval timeline, and delay costs show up later as a fundraising emergency.
- **After:** a side-by-side receipt for each city. It shows the median months per approval stage (with sample size and uncertainty), the dollar cost of that waiting per home, and how much the waiting multiplies the funding gap.

## Why delay matters: the gap multiplier

The family's purchase price is fixed, so every extra dollar of project cost lands on the funding gap. In the event's worked example, a 10-month slip:

- raised total cost about **18%** ($454k → $535k)
- grew the gap about **7x** (about $13.6k → about $95k)

Figures from the event's synthetic example deal. **ASSUMPTION.**

<!-- TODO (builder, by 1:15): replace with the real demo headline, e.g.
"City B's extra N months turns $13.6k into $X per home." -->

## What we built

A Streamlit app with four tabs:

| Tab | What it shows |
|---|---|
| **Timelines** | For each city and approval stage: median months, 90% confidence interval, project count, sample-size label, and the number of projects still waiting. Overall match rate. |
| **Receipt** | One city's itemized receipt (e.g. "Waiting for permit: 9 months × $8.1k = $73k"), with the gap multiplier as the headline. Shown per home and per project. Assumptions are editable in the sidebar. |
| **Compare** | Two cities side by side ("choosing A saves about $X per home in waiting"), plus a Claude-written board memo. |
| **Limitations** | What the data can't tell you, what is mocked, data dates, and links to sources. |

## Data

All timeline data comes from California HCD's **Housing Element Annual Progress Reports (APR)**, which every city files each year. We query only the OC cities we need through the data.ca.gov datastore API, cache the raw responses once, and never re-fetch inside the app.

| Source | What it gives | Resource ID |
|---|---|---|
| APR Table A2 | Per project: entitlement, building permit and certificate-of-occupancy dates; APN; address; unit type; tenure; unit counts | `fe505d9b-8c36-42ba-ba30-08bc4f34e022` |
| APR Table A | Per application: date submitted, outcome, SB 35 streamlining flag | `c78b769d-cc02-4050-91ef-79ded665b5a8` |
| Event synthetic example deal | Default gap and carrying cost (see Receipt math) | `lanes/3-fund-it/data/synthetic-example-deal.json` |

**Cities pulled:** <!-- TODO (builder, by 11:30): confirm list, e.g. Irvine, Anaheim, Santa Ana, Huntington Beach, Fullerton -->
**Demo pair:** <!-- TODO (builder, by 1:15) -->
**Exact field names:** see [`docs/fields.md`](docs/fields.md).

## How it works

### 1. Stitching yearly reports into projects

Each yearly APR report only includes the dates that happened in that reporting year. A project approved in 2021, permitted in 2023 and finished in 2025 therefore appears in three different reports. We combine those rows into one project as follows:

1. **Clean:** reduce APNs to digits only; uppercase addresses and standardize suffixes; parse dates. The raw values are kept alongside.
2. **Match, in order:** exact APN within a city → prior APN to current APN → normalized address within a city. The rule that matched is stored in `match_method`, and the overall match rate is shown in the app.
3. **One date per stage:** if rows disagree on a stage's date, we keep the earliest and set a `conflict` flag.
4. **Order check:** a later stage dated before an earlier one is flagged and excluded. Durations are never negative.
5. **Like-for-like filter:** owner-tenure projects only. ADUs and rentals never enter the ownership comparison.
6. **Streamlined split** (if the Table A join works): timelines are shown separately for SB 35 streamlined and regular approvals.

**Match rate:** <!-- TODO (builder, by 12:30) --> · **Fallback triggered?** <!-- TODO: yes/no — if yes, timelines are per-year counts of projects reaching each stage -->

### 2. Timeline statistics

- Durations in months for each stage: application → entitlement, entitlement → permit, permit → occupancy, and end to end where all dates exist.
- **Median with a 90% bootstrap confidence interval** for each city and stage (2,000 resamples, fixed seed).
- **Sample-size labels:**

| Projects | Label | Median shown? |
|---|---|---|
| < 10 | Insufficient evidence | No |
| 10–19 | Preliminary | Yes, labeled |
| 20–29 | Moderate | Yes |
| 30+ | More reliable | Yes |

- **Still waiting:** projects that reached a stage but have no next-stage date by the latest reporting year. These are labeled "no further activity reported," because the APR doesn't record cancellations. A median computed over finished projects alone is biased short, since the slowest projects drop out of it.

### 3. Receipt math

| Symbol | Meaning | Default |
|---|---|---|
| `c` | Monthly carrying cost per home once the construction loan is drawn | $8.1k **ASSUMPTION** |
| `c0` | Monthly carrying cost per home before the loan is drawn | user input **ASSUMPTION** |
| `G0` | Gap per home with no extra delay | $13.6k **ASSUMPTION** |
| `units` | Homes in the project | user input |

```
delay cost        = Σ over stages (months_s × c_s),   c_s ∈ {c0, c}
gap after delay   = G0 + delay cost
gap multiplier    = (G0 + delay cost) / G0
city difference   = (months_B − months_A) × c        (per home)
```

**How the defaults were derived:** the worked example ends with a $95k gap after a 10-month slip that grew it about 7x. That puts the gap before the slip at about $95k / 7 ≈ $13.6k, and the slip's added cost at about $81.4k, or about $8.1k per month.

### 4. Claude board memo

On the Compare tab, Claude writes a one-page board memo comparing the two cities. It works only from a JSON object of numbers the pipeline computed: medians, intervals, counts, labels, still-waiting counts, match rate, receipt figures, the assumptions used, and the limitations.

- The prompt forbids any number not present in the input, requires "unknown" for missing fields, and requires every assumption to be named as one.
- **Guard:** every number in the generated memo is checked against the input. If any fails the check, the memo is shown with a warning.
- If the API call fails, the app shows a saved backup memo (`data/sample/memo_backup.md`).

## Limitations

- The data **can't separate city-caused delay from developer-caused delay.**
- Project complexity is only partly controlled (owner tenure, size range, streamlined split).
- The APR has **no cancellation data**, so stalled projects are reported as "no further activity reported."
- All dollar figures come from **one synthetic deal** and are tagged ASSUMPTION.
- Results are shown at city level only. No individual project addresses are displayed.
- Built in about 3.5 hours at a hackathon. Prototype only; nothing is filed or sent.

## What is real and what is mocked

| Real | Mocked / assumed |
|---|---|
| Approval timelines from APR Tables A and A2 | Carrying cost and baseline gap (from the event's synthetic deal) |
| Match rate, project counts, still-waiting counts | Backup memo used if the API fails |

<!-- TODO (builder, by 12:30): add anything else mocked, e.g. if the fallback was triggered -->

## Try it

Runs offline from the committed sample data. No API key is needed, except to generate a new memo.

```bash
git clone https://github.com/<your-username>/clear-the-lot.git
cd clear-the-lot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # optional: add ANTHROPIC_API_KEY to generate memos
streamlit run app.py
```

<!-- TODO (builder, by 1:50): confirm exact commands; test in a fresh clone -->

## Tests

Ten offline tests define "working." They were written before the implementation and run with `pytest`.

1. Cross-year rows with the same APN combine into one project
2. Prior APN links to current APN
3. Conflicting stage dates → keep earliest, flag conflict
4. Out-of-order stages flagged and excluded; no negative durations
5. Fewer than 10 projects → "Insufficient evidence," no median
6. Entitlement with no permit counts as still waiting, not as a short duration
7. Receipt math: G0 $13.6k, c $8.1k, 10 months → about $95k, about 7x
8. Every dollar figure carries an ASSUMPTION tag
9. Memo guard rejects numbers not in the input (mocked Claude, no network)
10. Rental and ADU rows never appear in the ownership comparison

```
<!-- TODO (builder, by 1:50): paste actual pytest output here -->
```

## Repo layout

```
fetch.py       pull OC rows from the API into data/raw/ (cached, polite paging)
clean.py       normalize APNs, addresses, dates
stitch.py      one row per project with stage dates + match_method
timelines.py   durations, medians, bootstrap CIs, sample-size labels, still-waiting
receipt.py     delay cost, gap, multiplier
memo.py        Claude board memo + number guard
app.py         Streamlit: Timelines, Receipt, Compare, Limitations
tests/         gates 1–10 with hand-made fixtures
data/sample/   small committed slice so the app runs offline
docs/fields.md exact APR field names
.env.example   ANTHROPIC_API_KEY= (name only)
```

## Sources

- [Event repo: claude-impact-lab-uci](https://github.com/travcjohnson/claude-impact-lab-uci): lane data list, worked example, ground rules
- [APR data by jurisdiction and year (data.ca.gov)](https://data.ca.gov/dataset/housing-element-annual-progress-report-apr-data-by-jurisdiction-and-year)
- [HCD Annual Progress Report instructions](https://www.hcd.ca.gov/sites/default/files/docs/planning-and-community/housing-element-annual-progress-report-instructions.pdf): Table A/A2 date fields; dates are reported only in the year they happen

<!-- TODO: add data pull dates -->

## Team

- **Builder:** Ashton Peng (UC Irvine, Applied Mathematics)
- **Presenter:** <!-- TODO -->
