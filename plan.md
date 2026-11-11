# Plan: Permit Wait Leaderboard

**Status:** future plan, mostly not built. Written November 7, 2026. Updated November 10, 2026:
a first city permit portal scraper works for Laguna Beach (see
[Second source: city permit portals](#second-source-city-permit-portals) and `progress.md`).

**Vision:** a public website, refreshed weekly, that ranks California cities by how long housing
permits take. It starts in Orange County and uses the state's Annual Progress Report (APR) data.

> Prototype, not legal or financial advice. A long wait in this data does not prove the city caused
> it: the APR can't separate city delay from developer delay.

## What we need to get right

1. **The file refreshes weekly, but the facts mostly change once a year.** Cities file their APRs
   annually, due April 1. A weekly site is possible, but most weeks it will probably show no change.
2. **Standardizing "complete" won't fix the permit-wait number.** "Complete" affects stages that end
   at occupancy. The permit wait ends at the building permit, so its bigger problem is how cities
   report the start date (see [Standardizing "complete"](#standardizing-complete)).
3. **We can't standardize "complete" from the APR alone.** One date field accepts several kinds of
   document, and nothing records which kind a city used. We have to find out city by city.
4. **Only about 10 of the 34 Orange County jurisdictions can be ranked today**, and the slowest cities
   can't be confidently ordered against each other. The site should show tiers, not a strict 1-2-3.

## What the sources say about update frequency

| Question | Answer | Source |
|---|---|---|
| How often is the file published? | **Weekly** is the stated frequency. We had heard monthly, but found no source for that. | data.ca.gov dataset page [1] |
| Does it really change weekly? | **Unknown.** We have two update dates, October 30 and November 6, 2026. | `docs/fields.md`; data.ca.gov [1] |
| How often do cities report? | Once a year, covering the previous calendar year, due April 1. | HCD instructions p. 1 [2] |
| When does new data arrive? | For the 2025 report, HCD began accepting submissions on January 2, 2026. | HCD webinar slide 4 [3] |
| Can old reports change? | Yes. Revised APRs for 2018 through 2024 are accepted. | HCD webinar slide 12 [3] |
| Is the data verified? | No. It is self-reported, and HCD does not independently verify it. | data.ca.gov [1] |

**Sources disagree:** the dataset's metadata gives its coverage as 2018 to 2022, but the file has
reporting years through 2025. Trust the file, and raise the mismatch with HCD.

**How old the data can be:** a permit issued in January 2026 may not appear until the report due
April 1, 2027, about 15 months later. The site must show this. "Updated this week" can't imply
"includes this week's permits."

## Standardizing "complete"

"Complete" means three different things in the APR:

| Stage | HCD's wording [2] | Comparison problem |
|---|---|---|
| Application | "Application submitted" means a submittal "determined complete by the jurisdiction" (p. 5). Table A field 4 asks for the submitted date, or the date it was determined complete if it was incomplete at submittal. | Each city decides when an application is complete. Only 8.6% of our stitched ownership projects join to an application date. |
| Entitlement | "Completed Entitlement" means all land use approvals needed for a building permit have been received, with "no additional action required" (p. 5). | Some cities report the same date for entitlement and permit. The form has a ministerial or discretionary field (Table A field 14), and those paths may not be comparable. |
| Occupancy | A certificate of occupancy "or other evidence of readiness for occupancy (e.g., final inspection, notice of completion)" (p. 5). Table A2 also adds "final permit". | **This is the inconsistency we heard about.** The date field (`CO_ISSUE_DT1`) accepts any of these, and no field says which one was used. [2][4] |

The form's own instructions also conflict. Table A2 says "activity from prior years may be included
but is not required", while fields 5, 8 and 11 say to leave a date blank if it falls outside the
reporting year. [2]

### What we see in the Orange County data

Owner-occupied, non-ADU rows from the November 7, 2026 download. These are patterns, not proof of why
a city reports this way. **The causes are unknown.**

| Pattern | Evidence |
|---|---|
| A city reports no completions | Huntington Beach: 440 rows with a permit date, 0 with an occupancy date |
| Occupancy rows per permit row vary widely | 0.49 (Laguna Beach) to 2.17 (Brea), among cities with 50+ permit rows and at least one occupancy date. Phased projects and timing explain some of this. |
| Occupancy dates outside the reporting year | 770 rows, including 218 of 466 in Buena Park and 85 of 143 in Fullerton |
| Entitlement and permit share a date in the same row | 234 rows, including 136 in Fullerton |
| Permit wait close to zero | Median entitlement → permit: Fullerton and Anaheim 0.0 months, San Juan Capistrano 0.4 months |
| Impossible dates | The latest entitlement date in the file is July 10, 2028 |

### Proposed standard

**ASSUMPTION:** these are our proposed definitions, not HCD's. Have a planner or city staff member
review them before publishing.

| Term | Proposed definition | Data |
|---|---|---|
| **Permit wait** (headline) | Completed entitlement → first building permit | `ENT_APPROVE_DT1`, `BP_ISSUE_DT1` |
| **Application wait** (secondary) | Application determined complete → completed entitlement | `APP_SUBMIT_DT`, `ENT_APPROVE_DT1` |
| **Complete** | Evidence of readiness issued for all permitted units. Until reported completed units reach permitted units, the project is "partially complete". | `CO_ISSUE_DT1`, `NO_OTHER_FORMS_OF_READINESS`, `NO_BUILDING_PERMITS` |
| **Build time** (secondary, never in the headline) | First building permit → complete | as above |

Using "all permitted units" means changing `stitch.py`, which now keeps the **earliest** date per
stage. That date is the first completed home, not the finished project. Keep both first and last dates.

### How to handle city differences

1. **Build a city definitions file**, `data/city_definitions.csv`. Columns: city, stage, what the city
   reports (certificate of occupancy, final inspection, final permit, notice of completion, or
   `unknown`), source URL, date checked and who checked it. **Every city starts as `unknown`.**
2. **Fill it from public sources first**, such as city APR documents and permit pages. A person can
   then contact city staff. Claude can draft that message, but a person sends it.
3. **Label each city's completion data:** `Confirmed definition` or `As reported, definition unknown`.
   Only rank build time among cities with confirmed, comparable definitions.
4. **Never apply an adjustment factor we haven't measured.** To estimate the gap between, say, final
   inspection and certificate of occupancy, get both dates from a city's own permit records, and only
   with permission. Until then, the size of that gap is unknown.
5. **Flag reporting patterns automatically:** no occupancy dates, mostly same-day dates, dates outside
   the reporting year, and future dates. Today's same-day check only catches exactly 0 months, so it
   misses cases like San Juan Capistrano's 0.4 months.

## Second source: city permit portals

Added November 10, 2026. Details, results and limits are in `progress.md`.

**What changed:** we can now pull a city's own permit and planning records. `energov.py` reads
Laguna Beach's public Tyler EnerGov portal [6], `portal_link.py` links entitlement approvals to
housing building permits, and `portal_master.py` merges both into one timeline per site.

**Why it matters for this plan:**

| Problem in this plan | What the portal adds | Limit |
|---|---|---|
| The APR arrives up to 15 months late | Portal records are current, and each has a status | We have not checked how quickly the city updates them |
| The APR can't tell which projects are stalled | Permits not yet issued are visible, with their status | The portal has no reason for a delay |
| Only 8.6% of stitched projects join to an application date | Every record has an applied date | What "applied" means there is unknown; the team will decide how to treat it |
| We planned to check stitched timelines against city records (Phase 4) | The portal uses the same parcel hash as the APR sample, so the two can be joined | Not done yet |
| Each city defines "complete" differently | Permits carry separate issued and finaled dates | The search results don't show certificates of occupancy |

**First result:** for Laguna Beach permits applied January 2023 to October 2026, the median wait from
last entitlement to building permit is 8.4 months across 117 linked housing permits (middle half 5.6
to 14.2), and 12.6 months for 23 new single-family homes. The APR figure below is 12.5 months. The
samples are small and are not the same projects, so this is a first comparison, not a confirmation.

**ASSUMPTION:** which plan types count as entitlements and which permits count as housing are our
choices from the portal's type names, listed in `data/portal/cities.json`. A planner has not reviewed
them. 236 of 452 housing permits found no entitlement, and the cause is unknown.

**What this does not change:** the APR stays the statewide source. Portals are city by city, each
needs its own type lists, and we have run only one. A portal number should not go on the leaderboard
until the definitions are reviewed and the city's terms are checked.

**Rules for pulling:** one request every 8 seconds for Laguna Beach (at 4 seconds the portal reset the
connection after about 50 requests), every finished month cached, and stop on any block. A person
still needs to confirm the portal link on the city's website and check its terms of use.

## Leaderboard rules

Today's permit-wait results, owner-occupied, 1-200 units, approval batches:

| City | Median months | 90% interval | Batches | Still waiting |
|---|---|---:|---:|---:|
| Cypress | 15.7 | 9.6 to 27.0 | 10 | 1 |
| Santa Ana | 15.2 | 10.6 to 23.5 | 10 | 5 |
| Costa Mesa | 14.5 | 11.2 to 17.6 | 15 | 18 |
| Laguna Beach | 12.5 | 10.7 to 13.8 | 48 | 36 |
| Orange | 11.3 | 8.1 to 16.7 | 13 | 12 |
| Dana Point | 10.5 | 8.1 to 12.9 | 14 | 13 |
| Placentia | 8.7 | 5.3 to 18.1 | 17 | 13 |
| Westminster | 7.7 | 4.3 to 22.5 | 10 | 14 |
| Yorba Linda | 5.2 | 1.7 to 8.2 | 24 | 8 |
| San Juan Capistrano | 0.4 (check reporting) | 0.2 to 0.6 | 34 | 1 |

Anaheim and Fullerton also have 10+ batches, but are left out because most of their dates are same-day.
The top eight intervals all overlap, so "Cypress is the slowest" is not a claim this data supports.

The rules that follow from this:

- **Rank in tiers.** Separate cities only when the evidence does. Choose the exact tier method in
  Phase 2.
- **Treat "unknown" as its own group.** Cities with fewer than 10 batches, or with flagged reporting,
  sit outside the ranking and are never shown as fast. This matches the app's current cutoff.
- **Count projects still waiting.** Medians of finished projects are biased short, which can flatter a
  city with many stalled projects. Costa Mesa has more batches waiting (18) than finished (15). Use a
  Kaplan-Meier estimate for the ranking, as the README's next steps already suggest. Label these
  projects "no further activity reported", because the APR has no cancellation data.
- **Rank ministerial and discretionary projects separately if the data allows.** `extract.py` currently
  drops Table A's `PROJECT_TYPE`. Check whether it holds this split and how well it joins, given the
  low application join rate.
- **Show the evidence on every row:** batches, interval, match rate, latest report filed, definition
  label, and a link to the source.
- **Give cities a way to respond.** Add a public page explaining how to dispute a number. Corrections
  to the source data go through HCD's revised APR process. [3]
- **Word it carefully.** Use "longest reported wait", and put the city-versus-developer caveat next to
  the ranking.

## Weekly pipeline

```
Check metadata -> Changed? -> Download -> Validate -> Run pipeline -> Compare -> Publish
     no change: record "checked, no change" and stop
     validation fails: keep last good version and alert the team
```

| Step | Work | Reuses |
|---|---|---|
| Check | Read `last_modified` from the data.ca.gov API. Download only when it changes; Table A2 alone is about 281 MB. | new |
| Download | Save the files outside git, with a checksum and the date. | `extract.py` input |
| Validate | Stop if columns are missing, row counts fall sharply, or a city disappears. | `extract.py` column check |
| Run | Same cleaning, stitching and statistics, with county as a setting. | `clean.py`, `stitch.py`, `timelines.py` |
| Compare | Save each run's results, and list which cities changed and why (new filing or revision). | new |
| Publish | Static site built from JSON, with two dates: **last checked** and **data last changed**. | new |

**Hosting:** a scheduled GitHub Action and a static site should be enough. The Streamlit app stays as
the detailed tool for project managers. Hosting limits and costs still need checking.

**Filing season:** from January to April, some cities will have new reports and others won't. Show each
city's latest report year, and rank only on a reporting window every ranked city has filed.

**Privacy and rules:** keep hashing APNs and addresses, and show only city-level results. The pipeline
files nothing and contacts no one.

## Phases

Each phase ends with a check, so we don't build more than the evidence supports.

| Phase | Work | Done when |
|---|---|---|
| **0. Check the assumptions** | Save weekly metadata and row counts for 8 weeks, and compare what changes. A person asks HCD about the refresh schedule and the 2018-2022 coverage. Ask 2-3 cities how they report completion. | We know how much really changes each week and whether the definitions differ as we heard. |
| **1. Standard and flags** | Review the definitions with a planner. Add first and last dates, the definitions file and automatic flags, with tests. | Every Orange County city has a flag summary and a definition label, even if it's `unknown`. |
| **2. Ranking** | Add Kaplan-Meier, tiers and the ministerial split. Compare results before and after. | Rankings hold up when the method changes slightly, or the instability is shown. |
| **3. Orange County site** | Add the weekly job, static site, methods page, dispute page and change log. | The site runs unattended for 4 weeks, and one failed validation is caught correctly. |
| **4. Validate with users** | Show it to a nonprofit and a city. Check stitched timelines against a few cities' own records, with permission. **Started November 10, 2026:** Laguna Beach portal records are pulled and linked, but not yet joined to the APR sample. | A real user says they would use it, and we know the error rate. |
| **5. Go statewide** | Run every county, which is the same data file, and add county views. | Flags and labels scale without checking every city by hand. |

## Decisions for the team

| Decision | Recommendation | Why |
|---|---|---|
| What is the headline number? | Entitlement → building permit | It's closest to "permit wait", and 12 cities have enough data, versus 10 for application → entitlement. |
| Owner only, or rentals too? | Owner first, then test all tenures | Owner matches today's tool, but rentals could add evidence. |
| What's the update cadence? | Check weekly, and publish only when data changes | Avoids implying freshness we don't have. |
| Which unit count filter? | Keep 1-200 for now | It's the current app default. Test sensitivity in Phase 2. |
| Is it a "worst cities" list? | Lead with the wait times, and also show the fastest cities and biggest improvers | Cities are more likely to engage, and it shows what's achievable. |
| Who owns the definitions? | Name one person, and have a planner review | Someone has to keep these judgment calls current. |
| How do we use portal data? | As a cross-check and a freshness signal first, not as the ranking | One city, unreviewed type lists, and half of housing permits unlinked. |
| Which city portal is next? | A second Tyler EnerGov city in Orange County | It tests how much of the scraper carries over. Which cities use EnerGov is not yet listed. |

## Small fix to make next

`docs/fields.md` marks `NO_OTHER_FORMS_OF_READINESS` as "INFERRED, not confirmed". The Table A2 data
dictionary now confirms it is the number of units issued certificates of occupancy or other forms of
readiness. [4]

## Sources

All checked November 7, 2026.

1. [APR dataset, data.ca.gov](https://data.ca.gov/dataset/housing-element-annual-progress-report-apr-data-by-jurisdiction-and-year): frequency, last updated date (November 6, 2026), coverage and self-reporting statement. Rights: "No restrictions on public use". License: "not specified".
2. [HCD APR Instructions](https://www.hcd.ca.gov/sites/default/files/docs/planning-and-community/housing-element-annual-progress-report-instructions.pdf) (PDF dated January 30, 2026): definitions on p. 5, Table A fields 4 and 14, and Table A2 fields 5, 8, 10 and 11. Gov. Code § 65400.
3. [HCD 2025 APR webinar slides](https://www.hcd.ca.gov/sites/default/files/docs/planning-and-community/2025-apr-webinar-slides.pdf) (PDF dated December 30, 2025): timeline on slide 4, revisions on slide 12.
4. [APR Table A2 data dictionary](https://publish.data.ca.gov/dataset/81b0841f-2802-403e-b48e-2ef4b751f77c/resource/354a375a-821d-4d4e-97ab-4d79c2925fce/download/annualprogressreport_tablea2_datadictionary-2.docx) (last updated October 1, 2026): `CO_ISSUE_DT1` and `NO_OTHER_FORMS_OF_READINESS`.
5. Orange County figures: computed from `data/sample/oc_tablea2.csv` and `pipeline.build(1, 200)`, using the data downloaded on November 7, 2026.
6. [Laguna Beach Citizen Self Service portal](https://lagunabeachca-energovweb.tylerhost.net/apps/selfservice) (Tyler EnerGov), checked November 10, 2026: public permit and plan search, no login. No `robots.txt` or terms of use found. Figures computed from `data/portal/laguna_beach_*.csv` with `portal_link.py`.
