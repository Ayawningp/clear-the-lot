# Delay Receipt

> For a nonprofit project manager choosing between two Orange County cities: shows how long each city's approvals really take, from the state's own records, and what that waiting adds to the funding gap per home.

**Team:** <!-- TODO: team name -->
**Members:** Ashton Peng  · Toshiki Kobayashi · <!-- TODO: presenter and other members -->
**Lane:** 2 Clear it
**Built at:** Claude Impact Lab: UCI × SoCal Affordable Housing, November 7, 2026

> Prototype, not legal or financial advice.

## The real user

A nonprofit project manager with a small affordable *ownership* project that could go in one of two Orange County cities (event scenario C02, a made-up user). Nobody can give them a realistic approval timeline, and the cost of delay shows up later as a fundraising emergency. The family's purchase price is fixed, so every extra month of waiting lands directly on the funding gap.

**Before:** they choose a city on reputation and anecdotes.
**After:** a side-by-side receipt for each city. It shows the median months per approval stage (with sample size and uncertainty), the dollar cost of that waiting per home, and how much the waiting multiplies the funding gap.

**The demo:** from entitlement to building permit, the median Yorba Linda ownership approval took **5.2 months** and the median Laguna Beach one took **12.5 months** (APR data through 2025). At the assumed carrying cost, choosing Yorba Linda saves about **$56k per home** in waiting, about 4 times the whole $13.6k gap the project started with. Dollar figures are **ASSUMPTION**; the months are real.

Why it matters: in the event's worked example, a 10-month slip raised total cost about 18% ($454k → $535k) but grew the gap about **7x** (about $13.6k → about $95k). Figures from the event's synthetic example deal. **ASSUMPTION.**

## What we built

A Streamlit app with four tabs, running on real state data for every Orange County city:

| Tab | What it shows |
|---|---|
| **Timelines** | For each city and approval stage: median months, 90% confidence interval, number of approvals, sample-size label, and the number of projects still waiting. Overall project count, match rate and data date. |
| **Receipt** | An itemized receipt for the slower of your two cities, priced against the faster one's schedule (e.g. "Approval to building permit: 7.3 months longer × $8,100"), with the gap multiplier as the headline (Laguna Beach vs Yorba Linda: 5.1×). Shown per home and per project. Assumptions are editable in the sidebar. |
| **Compare** | Two cities side by side ("Building in Yorba Linda saves about $56,151 per home in waiting costs"), plus a Claude-written board memo. |
| **Limitations** | What the data can't tell you, what is real versus assumed, data dates, and links to sources. |

**Demo video:** <!-- TODO: link, or "uploaded on the hub" -->
**Live demo:** <!-- TODO: link, optional -->

### How it works

**1. Extracting the data.** The team downloaded the full statewide APR Table A and A2 files from data.ca.gov once (November 7, 2026). `extract.py` keeps only Orange County rows and the columns we use. Before anything is committed, APNs and street addresses are replaced by one-way hashes, and project names, notes, geocoded addresses and city permit numbers are dropped. The app never calls the API.

**2. Stitching yearly reports into projects.** Each yearly APR report only includes the dates that happened in that reporting year. A project approved in 2021, permitted in 2023 and finished in 2025 appears in three different reports. `clean.py` and `stitch.py` combine those rows into one project:

1. **Clean:** reduce APNs to digits only; uppercase addresses and standardize suffixes; parse dates.
2. **Filter first:** owner-tenure projects only. ADUs and rentals never enter the ownership comparison.
3. **Match, within a city, in order:** same APN → prior APN to current APN → same normalized address (only when a row has no APN). The rule used is stored in `match_method`.
4. **One date per stage:** if rows disagree on a stage's date, we keep the earliest and set a `conflict` flag. One APN often carries several permits (one per home), so most conflicts are phased permits, not bad data.
5. **Order check:** a later stage dated before an earlier one is flagged and excluded. Durations are never negative.

**Result:** 53,578 Orange County A2 rows → 33,160 ownership, non-ADU rows → **11,871 projects**. **28.6%** of them (3,394) were linked across two or more reporting years: 4,032 by APN, 5 by prior APN and 986 by address; 6,848 are single rows. The app's default 1–200 unit filter shows 11,832 projects and a 28% match rate.

**3. Timeline statistics** (`timelines.py`).

- Months for each stage: application → entitlement, entitlement → building permit, building permit → occupancy, and entitlement → occupancy end to end.
- **Approval batches, not parcels:** parcels in one city that share the same stage start date count once, so a 300-lot subdivision is one data point, not 300.
- **Median with a 90% bootstrap confidence interval** for each city and stage.
- **Sample-size labels:**

| Approval batches | Label | Median shown? |
|---|---|---|
| < 10 | Insufficient evidence | No |
| 10–19 | Preliminary | Yes, labeled |
| 20–29 | Moderate | Yes |
| 30+ | More reliable | Yes |

- **Still waiting:** projects that reached a stage but have no next-stage date by the end of 2025. These are labeled "no further activity reported," because the APR doesn't record cancellations. A median over finished projects alone is biased short, since the slowest projects drop out of it.
- **Same-day dates:** some cities report the same date for two stages. Stages where most dates are same-day are flagged ⚠ and left out of receipts.

**4. Receipt math** (`receipt.py`). The receipt charges only the months the slower city takes **beyond the faster city's schedule**, step by step, using only steps where both cities have 10+ approval batches. G0 is the gap on the faster city's schedule. A step where the slower city is quicker shows as a negative line. Permit → occupancy is mostly construction time, so it is off by default. (`receipt.py` can also price a city against the countywide median; `timelines.pooled_baseline` computes it.)

| Symbol | Meaning | Default |
|---|---|---|
| `c` | Monthly carrying cost per home once the construction loan is drawn | $8.1k **ASSUMPTION** |
| `c0` | Monthly carrying cost per home before the loan is drawn | $8.1k (same as `c` until the user enters their own) **ASSUMPTION** |
| `G0` | Gap per home on the faster city's schedule | $13.6k **ASSUMPTION** |
| `units` | Homes in the project | 6 (user input) |

```
delay cost        = Σ over stages ((months_s − typical_s) × c_s),   c_s ∈ {c0, c}
gap after delay   = G0 + delay cost
gap multiplier    = (G0 + delay cost) / G0
city difference   = (months_B − months_A) × c        (per home)
```

How the defaults were derived: the worked example ends with a $95k gap after a 10-month slip that grew it about 7x. That puts the gap before the slip at about $95k / 7 ≈ $13.6k, and the slip's added cost at about $81.4k, or about $8.1k per month. "About 7x" is rounded, so these are uncertain.

## How Claude is used

- **Building it:** Claude helped write the build spec, the pipeline, the tests and the Streamlit screens. The offline tests were written first and define "working."
- **Inside the tool:** on the Compare tab, Claude (`claude-sonnet-5-5`) writes a one-page board memo comparing the two cities. It works only from a JSON object of numbers the pipeline computed: medians, intervals, counts, labels, still-waiting counts, match rate, receipt figures, the assumptions used, and the limitations. The prompt forbids any number not in the input, requires "unknown" for missing fields, and requires every assumption to be named as one.
- **What a person checks:** a guard compares every number in the memo against the input. If any number fails, the app shows "Number check FAILED" and lists the numbers. If the API call fails, the app says so and shows a backup memo instead.

## Try it

Runs offline from the committed Orange County sample (about 7 MB). You need Python and git (tested with Python 3.14). No API key is needed, except to generate a new memo.

```bash
git clone https://github.com/Ayawningp/clear-the-lot.git
cd clear-the-lot
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # optional: add your own ANTHROPIC_API_KEY to generate memos
python -m pytest -q           # offline tests
python pipeline.py            # optional: print match rates and counts per city
streamlit run app.py
```

Environment variables: `ANTHROPIC_API_KEY` (optional, memo only). It goes in your local `.env`, which git ignores. No keys are in this repo.

To rebuild the sample from scratch, download the full Table A and A2 CSVs from data.ca.gov into `data/raw/tablea.csv` and `data/raw/tablea2.csv` (git-ignored, too big for GitHub) and run `python extract.py`.

Test output (Python 3.14.7, Windows, November 7, 2026):

```
$ python -m pytest -q
.........................                                                [100%]
25 passed
```

The tests cover cross-year and prior-APN linking, cities not linking to each other, address fallback, conflicting dates, out-of-order stages, sample-size labels, still-waiting counts, approval batches, renter/ADU exclusion, the receipt math against the worked example, the baseline, ASSUMPTION tags on every dollar figure, and the memo number guard (with a mocked Claude client, no network).

### Files

```
extract.py        statewide APR downloads → OC sample, with addresses and APNs hashed
clean.py          normalize APNs, addresses, dates
stitch.py         one row per project with stage dates, match_method, conflict and order flags
timelines.py      approval batches, medians, 90% bootstrap CIs, labels, still-waiting, baseline
receipt.py        delay cost vs a baseline schedule, gap, multiplier, ASSUMPTION tags
memo.py           Claude board memo + number guard + backup fallback
pipeline.py       end to end: sample → projects → per-city summaries
app.py            Streamlit: Timelines, Receipt, Compare, Limitations
tests/            25 offline tests with hand-made fixtures
data/sample/      OC rows from APR Tables A and A2 (hashed, committed)
docs/fields.md    exact APR field names and how the data is shaped
.env.example      ANTHROPIC_API_KEY= (name only)
```

## Sources and assumptions

| Item | Source or assumption | Date checked |
|---|---|---|
| APR Table A2: per-project entitlement, permit and occupancy dates; APN; address; unit type; tenure; unit counts | [data.ca.gov](https://data.ca.gov/dataset/housing-element-annual-progress-report-apr-data-by-jurisdiction-and-year), resource `fe505d9b-8c36-42ba-ba30-08bc4f34e022`, 927,011 rows statewide, 53,578 in Orange County, reporting years 2018–2025 | Downloaded Nov 7, 2026 |
| APR Table A: per-application submitted date, outcome, SB 35 flag | [data.ca.gov](https://data.ca.gov/dataset/housing-element-annual-progress-report-apr-data-by-jurisdiction-and-year), resource `c78b769d-cc02-4050-91ef-79ded665b5a8`, 358,228 rows statewide, 14,348 in Orange County | Downloaded Nov 7, 2026 |
| Dates appear only in the reporting year they happen | [HCD APR instructions](https://www.hcd.ca.gov/sites/default/files/docs/planning-and-community/housing-element-annual-progress-report-instructions.pdf) | Nov 7, 2026 |
| Exact field names | [docs/fields.md](docs/fields.md) | Nov 7, 2026 |
| Gap at a typical pace `G0` ≈ $13.6k per home | ASSUMPTION, derived from the event's synthetic example deal ([`synthetic-example-deal.json`](https://github.com/travcjohnson/claude-impact-lab-uci/blob/main/lanes/3-fund-it/data/synthetic-example-deal.json) in the event repo) | Nov 7, 2026 |
| Carrying cost `c` ≈ $8.1k per home per month | ASSUMPTION, derived from the same synthetic deal | Nov 7, 2026 |
| Pre-loan carrying cost `c0` | ASSUMPTION, no source; defaults to `c` | n/a |

Every number we made up is labelled ASSUMPTION here and in the tool.

**Cities:** all 34 Orange County jurisdictions, including unincorporated Orange County. Many have too few ownership projects for a median; the app says "Insufficient evidence" for those.
**Demo pair:** Yorba Linda and Laguna Beach, picked because both have 20+ approval batches for application → entitlement and entitlement → building permit.

## What is real and what is mocked

| Part | Status |
|---|---|
| Stage dates, approval counts, still-waiting counts, match rate | **real**, from APR Tables A and A2 |
| Medians, 90% intervals, sample-size labels, countywide baseline | working, tested, on real data |
| Receipt math and gap multiplier | working, tested; dollar inputs are ASSUMPTION |
| Carrying cost and baseline gap | **assumed** (from the event's synthetic deal) |
| Claude board memo and number guard | guard working and tested offline; a live memo needs an API key |
| Backup memo shown if the API fails | not saved yet (`data/sample/memo_backup.md`) <!-- TODO: save one good memo --> |
| Streamlined (SB 35) vs regular split | not possible: only 2 ownership projects carry an SB 35 flag |

## Where it gets things wrong

- **Only 28.6% of ownership projects link across years.** The rest are single rows, so many projects only ever show one stage. Medians come from the projects that did link, which may not be typical.
- The data **can't separate city-caused delay from developer-caused delay.**
- Project complexity is only partly controlled (owner tenure, no ADUs, unit-count range). Approval batches are a proxy for a project, not an exact one.
- The APR has **no cancellation data**, so stalled projects are reported as "no further activity reported," not as cancelled.
- Only projects whose earlier stage was reported in 2018 or later can be timed, which leaves out some of the longest timelines.
- Some cities report the same date for two stages; those stages are flagged and left out of receipts.
- Cities with fewer than 10 approval batches show "Insufficient evidence" instead of a median. That is unknown, not fast. Huntington Beach is one of them.
- A step where the slower city is quicker counts as a **negative** line (Laguna Beach is 0.4 months faster than Yorba Linda from application to approval), which partly offsets its longer permit step.
- All dollar figures come from **one synthetic deal**. Don't use them for a real budget.

## Next steps

- **Next month:** a nonprofit could use the Timelines tab as-is to set expectations with its board, replacing the synthetic dollar inputs with its own carrying cost and gap.
- **One more week:** raise the match rate (fuzzy address matching, using unit counts to link phased permits); extend to every California county, since every city files an APR; add a Kaplan-Meier estimate that treats still-waiting projects as censored; check the stitched timelines against a few cities' own permit records.

## Data and privacy

This project uses only public data. It contains no personal information about real tenants, buyers or residents. The APR includes project addresses and parcel numbers, so before anything is committed we replace APNs and street addresses with one-way hashes and drop project names, notes, geocoded addresses and city permit numbers. The tool shows only counts and city-level results, never individual projects. It does not file applications or contact any city or person.

## License

MIT, see the [LICENSE](LICENSE) file in this repo.
