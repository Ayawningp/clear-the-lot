# Plan: Orange County approval and permit wait rankings

**Status:** plan, partly built. Written November 7, 2026. Rewritten November 10, 2026 to fix the
goal on two rankings.

> Prototype, not legal or financial advice. A long wait in this data does not prove the city caused
> it: neither source can separate city delay from applicant delay.

## Goal

Rank Orange County's 34 jurisdictions on two waits, each with its own ranking:

1. **Approval wait:** application → entitlement approval.
2. **Permit wait:** entitlement approval → building permit.

Everything else (build time, occupancy, a statewide site) is out of scope until both rankings hold up
for Orange County.

## Next steps

In order. Steps 1 to 3 need a person; the rest are code. The reasons are in
[What blocks each ranking](#what-blocks-each-ranking) and the full sequence is in [Phases](#phases).

| # | Step | Who | Done when |
|---|---|---|---|
| 1 | Confirm the Laguna Beach portal link on the city's own website and read its terms of use. | A person | We have a yes or no on whether we may pull and publish, with a source and date in `cities.json`. If no, the pulled CSVs come out of the repo. |
| 2 | Decide the open definitions: what "applied" means in a portal, and whether ADUs are ranked. | The team | Both rows in [Decisions](#decisions-for-the-team) have an answer. |
| 3 | List which of the 34 jurisdictions have a public permit portal, and on which system. | A person | `cities.json` or a new table has every jurisdiction marked EnerGov, other, none or unknown, each with a source and date. |
| 4 | Count applications that have no approval yet, so the approval wait shows who is still waiting. | Code (`stitch.py`, `timelines.py`) | The approval wait table has a non-zero still-waiting column, with a test. |
| 5 | Add flags for near-zero medians, a high same-day share, and out-of-year and future dates. | Code (`timelines.py`) | San Juan Capistrano's 0.4 months is flagged automatically, with thresholds written down and tested. |
| 6 | Join Laguna Beach portal records to the APR sample by parcel hash. | Code (new) | We know how many projects appear in both sources and how far their dates differ. |
| 7 | Make `portal_link.py` use the merged sites from `portal_master.py`, and limit how far back an entitlement can link. | Code | The link file and the master file give the same counts. |
| 8 | Add a second Tyler EnerGov city from the list in step 3. | Code, after steps 1 and 3 | Both metrics are computed for two cities, and we know what had to change. |
| 9 | Have a planner review the metric definitions and the Laguna Beach type lists. | A person | The `ASSUMPTION` notes in `cities.json` are confirmed or corrected. |

Steps 4 to 7 don't depend on the people steps and can start now. Step 8 should wait for step 1: if
the terms don't allow it, we should not pull a second city the same way.

## The two metrics

| | 1. Approval wait | 2. Permit wait |
|---|---|---|
| **Starts** | Housing application submitted | Last land use approval received ("completed entitlement") |
| **Ends** | Last land use approval received | First building permit issued |
| **APR fields** | `APP_SUBMIT_DT` (Table A) → `ENT_APPROVE_DT1` (Table A2) | `ENT_APPROVE_DT1` → `BP_ISSUE_DT1` (Table A2) |
| **Portal fields** | Plan record `applied` → `completed`, for approved entitlement plans | Last approved entitlement `completed` at the site → housing permit `issued` |
| **Unit counted** | One approval batch (APR) or one entitlement record (portal) | One approval batch (APR) or one housing permit (portal) |
| **Reported as** | Median months, 90% interval, count, number still waiting | Same |

HCD's definitions [2]: "application submitted" means a submittal "determined complete by the
jurisdiction", and "completed entitlement" means all land use approvals needed for a building permit
have been received, with "no additional action required" (p. 5).

**ASSUMPTION:** the portal mappings are ours, not HCD's or the city's. The plan record's `completed`
date stands in for approval, and the portal's `applied` date stands in for application. What each
city means by those dates is unknown. The team will decide how to treat "applied".

**Which projects count.** The two sources do not cover the same projects today:

| | APR | Portal (Laguna Beach) |
|---|---|---|
| Included | Owner-occupied, non-ADU, 1 to 200 units | New single-family, ADU and new mixed-use permits; all approved entitlement plans |
| Tenure known | Yes | No |
| ADUs | Excluded | Included |

The team needs to pick one population for the ranking (see [Decisions](#decisions-for-the-team)).

## Where we stand today

### Approval wait, from the APR

Owner-occupied, 1-200 units, cities with 10 or more approval batches. Computed November 10, 2026 from
the November 7 download [5].

| City | Median months | 90% interval | Batches | Same-day share | Left out for date order |
|---|---:|---|---:|---:|---:|
| Costa Mesa | 5.6 | 4.0 to 7.9 | 24 | 0% | 12 |
| Westminster | 5.2 | 3.7 to 7.4 | 22 | 0% | 2 |
| Dana Point | 5.2 | 4.3 to 9.4 | 23 | 4% | 2 |
| Garden Grove | 3.0 | 2.6 to 3.0 | 12 | 0% | 4 |
| Yorba Linda | 2.7 | 1.3 to 4.1 | 22 | 14% | 1 |
| Orange | 2.5 | 0.8 to 5.2 | 19 | 26% | 2 |
| Placentia | 2.4 | 1.5 to 4.9 | 20 | 10% | 1 |
| Laguna Beach | 2.3 | 1.0 to 3.9 | 56 | 25% | 19 |
| Laguna Niguel | 1.2 (check reporting) | 0.0 to 4.9 | 10 | 50% | 1 |
| Anaheim | 0.0 (check reporting) | 0.0 to 0.0 | 31 | 81% | 3 |

Not rankable: every other jurisdiction has fewer than 10 batches, including Buena Park, Fullerton and
Irvine (9 each) and Santa Ana (8).

### Permit wait, from the APR

Same filter and date [5].

| City | Median months | 90% interval | Batches | Still waiting | Same-day share |
|---|---:|---|---:|---:|---:|
| Cypress | 15.7 | 9.6 to 27.0 | 10 | 1 | 10% |
| Santa Ana | 15.2 | 10.6 to 23.5 | 10 | 5 | 0% |
| Costa Mesa | 14.5 | 11.2 to 17.6 | 15 | 18 | 0% |
| Laguna Beach | 12.5 | 10.7 to 13.8 | 48 | 36 | 0% |
| Orange | 11.3 | 8.1 to 16.7 | 13 | 12 | 0% |
| Dana Point | 10.5 | 8.1 to 12.9 | 14 | 13 | 0% |
| Placentia | 8.7 | 5.3 to 18.1 | 17 | 13 | 0% |
| Westminster | 7.7 | 4.3 to 22.5 | 10 | 14 | 0% |
| Yorba Linda | 5.2 | 1.7 to 8.2 | 24 | 8 | 21% |
| San Juan Capistrano | 0.4 (check reporting) | 0.2 to 0.6 | 34 | 1 | 6% |
| Anaheim | 0.0 (check reporting) | 0.0 to 8.0 | 64 | 2 | 59% |
| Fullerton | 0.0 (check reporting) | 0.0 to 0.0 | 27 | 2 | 74% |

Not rankable: every other jurisdiction has fewer than 10 batches, including Buena Park and Laguna
Niguel (8 each) and Garden Grove (7).

### Laguna Beach, from the city portal

Records applied January 2023 to October 2026, pulled November 10, 2026 [6]. Details in `progress.md`.

| Metric | Portal | APR | Comparable? |
|---|---|---|---|
| Approval wait | 2.4 months (969 approved entitlements, all project types) | 2.3 months (56 batches) | Not the same projects. The portal figure includes entitlements for non-housing work. |
| Permit wait | 12.6 months for new single-family (23 permits); 8.3 months for all housing types including ADUs (118 permits) | 12.5 months (48 batches) | Not the same projects. The APR figure excludes ADUs. |

The two sources land close together on both metrics for the one city we can compare. That is
encouraging, not a confirmation: it is one city, and the samples differ.

### What this adds up to

| | Approval wait | Permit wait |
|---|---:|---:|
| Jurisdictions in the filtered APR sample | 33 | 33 |
| With 10+ batches | 10 | 12 |
| Of those, flagged for same-day or near-zero dates | 2 (Anaheim, Laguna Niguel) | 3 (Anaheim, Fullerton, San Juan Capistrano) |
| **Rankable today** | **8** | **9** |

Seven cities are rankable on both: Costa Mesa, Dana Point, Laguna Beach, Orange, Placentia,
Westminster and Yorba Linda. Neither ranking can order its slowest cities with confidence, because
their intervals overlap. One of the 34 jurisdictions has no rows in the filtered sample; which one has
not been checked.

## What blocks each ranking

**Approval wait**

- **Few applications join.** Only 8.4% of stitched projects at 1-200 units have an application date.
  This is the main reason most jurisdictions can't be ranked.
- **Each city decides when an application is "complete".** Table A field 4 asks for the submitted
  date, or the date it was determined complete if it was incomplete at submittal [2]. Nothing records
  which one a city used.
- **Dates out of order.** Laguna Beach has 19 batches and Costa Mesa 12 left out because the
  entitlement date comes before the application date.
- **No one is shown as still waiting.** The still-waiting count is 0 for every city, because
  `stitch.py` only attaches applications to projects that already have a Table A2 row. An application
  with no approval yet is never counted, so this ranking can't see stalled applications.

**Permit wait**

- **Same-day and near-zero dates.** Fullerton reports 74% same-day and Anaheim 59%. San Juan
  Capistrano's median is 0.4 months. Today's check only catches exactly 0 months.
- **Many projects are still waiting.** Costa Mesa has more batches waiting (18) than finished (15).
  A median of finished projects is biased short.
- **Ministerial and discretionary projects are mixed.** Table A field 14 records which path a project
  took [2], and `extract.py` currently drops Table A's `PROJECT_TYPE`.
- **Impossible dates.** The latest entitlement date in the file is July 10, 2028.

**Both**

- **The APR can be 15 months old.** A permit issued in January 2026 may not appear until the report
  due April 1, 2027.
- **The data is self-reported and not verified by HCD** [1].

## How the two sources work together

1. **The APR is the base.** It covers every jurisdiction with one set of definitions, so the county
   ranking is built on it.
2. **Portals fill gaps and check the APR, city by city.** A portal has an applied date on every
   record and shows what is still waiting. It can make an unrankable city rankable, starting with the
   approval wait, where the APR is weakest.
3. **Never blend sources in one number.** Each ranked row is labeled `APR` or `City portal`. Where a
   city has both, show both and the difference.
4. **A portal number is ranked only when** its type lists have been reviewed by a planner, the city's
   terms of use have been checked by a person, and it has 10 or more records.
5. **Which Orange County cities have a public portal, and on which system, is unknown.** We have
   used one: Laguna Beach, on Tyler EnerGov. Listing the rest is the first task in Phase 2.

## Ranking rules

These apply to both rankings.

- **Rank in tiers.** Separate cities only when their intervals do. Choose the exact tier method in
  Phase 3.
- **A minimum of 10 batches or records.** Below that, the city is listed as "not enough data" and is
  never shown as fast.
- **Flagged cities sit outside the ranking.** Flags: a high same-day share, a median near zero, dates
  outside the reporting year, and future dates. Choose the thresholds in Phase 1.
- **Count what is still waiting.** Use a Kaplan-Meier estimate so stalled projects count. Label them
  "no further activity reported", because the APR has no cancellation data.
- **Split ministerial from discretionary if the data allows.** Check whether Table A's project type
  field joins well enough, given the low application join rate.
- **Show the evidence on every row:** count, interval, still-waiting count, flags, source (`APR` or
  `City portal`), latest data date, and a link to the source.
- **Word it carefully.** Say "longest reported wait", and put the city-versus-applicant caveat next to
  the ranking.
- **Give cities a way to respond.** A public page explains how to dispute a number. Corrections to APR
  data go through HCD's revised APR process [3].

## Keeping it current

| Question | Answer | Source |
|---|---|---|
| How often is the APR file published? | Weekly is the stated frequency. | data.ca.gov [1] |
| Does it really change weekly? | Unknown. We have two update dates, October 30 and November 6, 2026. | `docs/fields.md`; [1] |
| How often do cities report? | Once a year, for the previous calendar year, due April 1. | HCD instructions p. 1 [2] |
| Can old reports change? | Yes. Revised APRs for 2018 through 2024 are accepted. | HCD webinar slide 12 [3] |
| How current is a portal? | Unknown. Records carry a status, but we have not checked how quickly a city updates them. | [6] |

**Sources disagree:** the APR dataset's metadata gives its coverage as 2018 to 2022, but the file has
reporting years through 2025. Trust the file, and raise the mismatch with HCD.

```
Check APR metadata -> Changed? -> Download -> Validate -> Run pipeline -> Compare -> Publish
     no change: record "checked, no change" and stop
     validation fails: keep last good version and alert the team
```

Portal pulls run separately and re-request only recent months. For Laguna Beach the pace is one
request every 8 seconds; at 4 seconds the portal reset the connection after about 50 requests. Stop
on any block. How often to re-pull is a Phase 2 decision.

Publish two dates on the site: **last checked** and **data last changed**. "Updated this week" can't
imply "includes this week's permits".

## Phases

Each phase ends with a check, so we don't build more than the evidence supports.

| Phase | Work | Done when |
|---|---|---|
| **1. Fix the APR rankings** | Count applications that have no approval yet. Try to raise the application join rate. Keep Table A's project type field. Add near-zero, out-of-year and future-date flags with thresholds. Add tests. | Both tables above are regenerated with flags and still-waiting counts, and we know how many more cities became rankable. |
| **2. Portal coverage** | A person lists which of the 34 jurisdictions have a public permit portal and on which system, with a source and date, and checks each one's terms. Add a second Tyler EnerGov city. Make `portal_link.py` use merged sites and limit how far back an entitlement can link. | We know how many unrankable cities a portal could cover, and the scraper works for two cities. |
| **3. Ranking method** | Add Kaplan-Meier, tiers and the ministerial split. Have a planner review the metric definitions and the portal type lists. Join portal and APR records by parcel hash for Laguna Beach. | Rankings hold up when the method changes slightly, or the instability is shown. We have a measured APR-versus-portal difference for at least one city. |
| **4. Orange County site** | Two ranked tables, a methods page, a dispute page and a change log, on a scheduled job. | The site runs unattended for 4 weeks, and one failed validation is caught correctly. |
| **5. Validate with users** | Show it to a nonprofit and a city. | A real user says they would use it, and we know the error rate. |

**Done so far (November 10, 2026):** the APR pipeline produces both tables; the Laguna Beach portal
scraper, link and master file work (`progress.md`).

## Decisions for the team

| Decision | Recommendation | Why |
|---|---|---|
| Which projects count? | Owner-occupied, non-ADU, 1-200 units for the ranking; show ADUs separately | It matches the APR pipeline and the tool's purpose. The portal can't tell tenure, so its numbers need that caveat. |
| One combined score or two rankings? | Two rankings, side by side | A city can be quick to approve and slow to permit. Laguna Beach is 2.3 months on approval and 12.5 on permits. |
| What counts as "applied" in a portal? | Undecided; the team will set this | The portal doesn't say whether it is submittal or deemed complete. |
| First or last entitlement? | Last | It matches HCD's "completed entitlement". In the Laguna Beach portal data the first gives 9.9 months against 8.4. |
| How is portal data used? | As a cross-check and gap-filler, labeled, never blended | One city so far, with unreviewed type lists. |
| Is it a "worst cities" list? | Lead with the waits, and also show the fastest cities | Cities are more likely to engage, and it shows what's achievable. |
| Who owns the definitions? | Name one person, and have a planner review | Someone has to keep these judgment calls current. |

## Out of scope for now

- **Build time and "complete".** The APR's occupancy date accepts a certificate of occupancy, final
  inspection, notice of completion or final permit, and no field says which was used [2][4].
  Huntington Beach reports 440 permit rows and no occupancy dates. Neither ranking in this plan ends at
  occupancy, so this does not block them. The earlier analysis is in this file's git history.
- **Statewide.** The APR file covers every county, so the APR side would extend. Portals would not
  without per-city work.

## Small fix to make next

`docs/fields.md` marks `NO_OTHER_FORMS_OF_READINESS` as "INFERRED, not confirmed". The Table A2 data
dictionary now confirms it is the number of units issued certificates of occupancy or other forms of
readiness. [4]

## Sources

Sources 1 to 4 checked November 7, 2026. Source 6 checked November 10, 2026.

1. [APR dataset, data.ca.gov](https://data.ca.gov/dataset/housing-element-annual-progress-report-apr-data-by-jurisdiction-and-year): frequency, last updated date (November 6, 2026), coverage and self-reporting statement. Rights: "No restrictions on public use". License: "not specified".
2. [HCD APR Instructions](https://www.hcd.ca.gov/sites/default/files/docs/planning-and-community/housing-element-annual-progress-report-instructions.pdf) (PDF dated January 30, 2026): definitions on p. 5, Table A fields 4 and 14, and Table A2 fields 5, 8, 10 and 11. Gov. Code § 65400.
3. [HCD 2025 APR webinar slides](https://www.hcd.ca.gov/sites/default/files/docs/planning-and-community/2025-apr-webinar-slides.pdf) (PDF dated December 30, 2025): timeline on slide 4, revisions on slide 12.
4. [APR Table A2 data dictionary](https://publish.data.ca.gov/dataset/81b0841f-2802-403e-b48e-2ef4b751f77c/resource/354a375a-821d-4d4e-97ab-4d79c2925fce/download/annualprogressreport_tablea2_datadictionary-2.docx) (last updated October 1, 2026): `CO_ISSUE_DT1` and `NO_OTHER_FORMS_OF_READINESS`.
5. Orange County APR figures: computed from `data/sample/oc_tablea.csv` and `oc_tablea2.csv` with `pipeline.build(1, 200)`, using the data downloaded on November 7, 2026.
6. [Laguna Beach Citizen Self Service portal](https://lagunabeachca-energovweb.tylerhost.net/apps/selfservice) (Tyler EnerGov), checked November 10, 2026: public permit and plan search, no login. No `robots.txt` or terms of use found. Figures computed from `data/portal/laguna_beach_master.csv` with `portal_master.py`.
