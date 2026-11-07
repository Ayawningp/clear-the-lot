# Delay Receipt

> For a nonprofit project manager choosing between two Orange County cities: shows how long each city's approvals really take, what that waiting costs per home, and how much it multiplies the funding gap.

**Team:** <!-- TODO: team name -->
**Members:** Ashton Peng (builder) · <!-- TODO: presenter and other members -->
**Lane:** 2 Clear it
**Built at:** Claude Impact Lab: UCI × SoCal Affordable Housing, November 7, 2026

> Prototype, not legal or financial advice.

## The real user

A nonprofit project manager with a small affordable *ownership* project that could go in one of two Orange County cities (event scenario C02, a made-up user). Nobody can give them a realistic approval timeline, and the cost of delay shows up later as a fundraising emergency. The family's purchase price is fixed, so every extra month of waiting lands directly on the funding gap.

**Before:** they choose a city on reputation and anecdotes.
**After:** a side-by-side receipt for each city. It shows the median months per approval stage (with sample size and uncertainty), the dollar cost of that waiting per home, and how much the waiting multiplies the funding gap.

In the event's worked example, a 10-month slip raised total cost about **18%** ($454k → $535k) but grew the gap about **7x** (about $13.6k → about $95k). Figures from the event's synthetic example deal. **ASSUMPTION.**

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

**Demo video:** <!-- TODO: link, or "uploaded on the hub" -->
**Live demo:** <!-- TODO: link, optional -->

### How it works

**1. Stitching yearly reports into projects.** Each yearly APR report only includes the dates that happened in that reporting year. A project approved in 2021, permitted in 2023 and finished in 2025 appears in three different reports. We combine those rows into one project:

1. **Clean:** reduce APNs to digits only; uppercase addresses and standardize suffixes; parse dates. The raw values are kept alongside.
2. **Match, in order:** exact APN within a city → prior APN to current APN → normalized address within a city. The rule that matched is stored in `match_method`, and the overall match rate is shown in the app.
3. **One date per stage:** if rows disagree on a stage's date, we keep the earliest and set a `conflict` flag.
4. **Order check:** a later stage dated before an earlier one is flagged and excluded. Durations are never negative.
5. **Like-for-like filter:** owner-tenure projects only. ADUs and rentals never enter the ownership comparison.
6. **Streamlined split** (if the Table A join works): timelines are shown separately for SB 35 streamlined and regular approvals.

**Match rate:** <!-- TODO (builder, by 12:30) --> · **Fallback triggered?** <!-- TODO: yes/no — if yes, timelines are per-year counts of projects reaching each stage -->

**2. Timeline statistics.**

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

**3. Receipt math.**

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

How the defaults were derived: the worked example ends with a $95k gap after a 10-month slip that grew it about 7x. That puts the gap before the slip at about $95k / 7 ≈ $13.6k, and the slip's added cost at about $81.4k, or about $8.1k per month.

## How Claude is used

- **Building it:** Claude helped write the build spec, the pipeline, the tests and the Streamlit screens. The ten offline tests were written first and define "working."
- **Inside the tool:** on the Compare tab, Claude writes a one-page board memo comparing the two cities. It works only from a JSON object of numbers the pipeline computed: medians, intervals, counts, labels, still-waiting counts, match rate, receipt figures, the assumptions used, and the limitations. The prompt forbids any number not in the input, requires "unknown" for missing fields, and requires every assumption to be named as one.
- **What a person checks:** a guard compares every number in the memo against the input. If any number fails, the memo is shown with a warning for a person to review. If the API call fails, the app shows a saved backup memo (`data/sample/memo_backup.md`).

## Try it

Runs offline from the committed sample data. You need Python 3.11+ and git. No API key is needed, except to generate a new memo.

```bash
git clone https://github.com/Ayawningp/clear-the-lot.git
cd clear-the-lot
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # optional: add your own ANTHROPIC_API_KEY to generate memos
python -m pytest -q           # offline tests
streamlit run app.py
```

Environment variables: `ANTHROPIC_API_KEY` (optional, memo only). It goes in your local `.env`, which git ignores. No keys are in this repo.

<!-- TODO (builder, by 1:50): confirm exact commands in a fresh clone; paste actual pytest output below -->

```
<!-- TODO: pytest output -->
```

## Sources and assumptions

| Item | Source or assumption | Date checked |
|---|---|---|
| APR Table A2: per-project entitlement, permit and occupancy dates; APN; address; unit type; tenure; unit counts | [data.ca.gov](https://data.ca.gov/dataset/housing-element-annual-progress-report-apr-data-by-jurisdiction-and-year), resource `fe505d9b-8c36-42ba-ba30-08bc4f34e022` | <!-- TODO --> |
| APR Table A: per-application submitted date, outcome, SB 35 flag | [data.ca.gov](https://data.ca.gov/dataset/housing-element-annual-progress-report-apr-data-by-jurisdiction-and-year), resource `c78b769d-cc02-4050-91ef-79ded665b5a8` | <!-- TODO --> |
| Dates appear only in the reporting year they happen | [HCD APR instructions](https://www.hcd.ca.gov/sites/default/files/docs/planning-and-community/housing-element-annual-progress-report-instructions.pdf) | <!-- TODO --> |
| Gap before delay `G0` ≈ $13.6k per home | ASSUMPTION, derived from the event's synthetic example deal (`lanes/3-fund-it/data/synthetic-example-deal.json`) | Nov 7, 2026 |
| Carrying cost `c` ≈ $8.1k per home per month | ASSUMPTION, derived from the same synthetic deal | Nov 7, 2026 |
| Pre-loan carrying cost `c0` | ASSUMPTION, user input | n/a |

Every number we made up is labelled ASSUMPTION here and in the tool.

**Cities pulled:** <!-- TODO (builder, by 11:30): e.g. Irvine, Anaheim, Santa Ana, Huntington Beach, Fullerton -->
**Demo pair:** <!-- TODO (builder, by 1:15) -->
**Exact field names:** see [`docs/fields.md`](docs/fields.md).

We query only the OC cities we need through the data.ca.gov datastore API, cache the raw responses once, and never re-fetch inside the app.

## What is real and what is mocked

| Part | Status |
|---|---|
| Approval timelines from APR Tables A and A2 | <!-- TODO: working / partly working --> |
| Match rate, project counts, still-waiting counts | <!-- TODO --> |
| Receipt math and gap multiplier | working; dollar inputs are ASSUMPTION |
| Carrying cost and baseline gap | mocked (from the event's synthetic deal) |
| Claude board memo | <!-- TODO --> |
| Backup memo shown if the API fails | mocked |

<!-- TODO (builder, by 12:30): add anything else mocked, e.g. if the fallback was triggered -->

## Where it gets things wrong

- The data **can't separate city-caused delay from developer-caused delay.**
- Project complexity is only partly controlled (owner tenure, size range, streamlined split).
- The APR has **no cancellation data**, so stalled projects are reported as "no further activity reported," not as cancelled.
- Cities with fewer than 10 comparable projects show "Insufficient evidence" instead of a median. That is unknown, not fast.
- Rows that can't be stitched across years drop out; the match rate on screen shows how many.
- All dollar figures come from **one synthetic deal**. Don't use them for a real budget.

## Next steps

- **Next month:** a nonprofit could use the Timelines tab as-is to set expectations with its board, replacing the synthetic dollar inputs with its own carrying cost and gap.
- **One more week:** pull every OC city (and then any California city, since every city files an APR); add a Kaplan-Meier estimate that treats still-waiting projects as censored; split results by project size; check the stitched timelines against a few cities' own permit records.

## Data and privacy

This project uses only public or provided data. It contains no personal information about real tenants, buyers or residents. The APR includes project addresses, so the tool shows only project counts and city-level results, never individual addresses. It does not file applications or contact any city or person.

## License

MIT, see the [LICENSE](LICENSE) file in this repo.
