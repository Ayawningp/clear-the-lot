# Progress: city permit portal scraper

**Date:** November 10, 2026. **Status:** working for one city (Laguna Beach). Not part of the app yet.

> Prototype, not legal or financial advice. A long wait in this data does not prove the city caused
> it: the portal can't separate city delay from applicant delay.

## What we did

We tested whether a city's own permit portal can give us the dates the state APR data can't. It can.
We pulled Laguna Beach's public permit and planning records, linked entitlement approvals to housing
building permits, and merged everything into one file that tracks each property's dates.

| Step | Script | Output |
|---|---|---|
| Pull plans and permits, one month at a time | `energov.py` | `data/portal/laguna_beach_plans.csv`, `laguna_beach_permits.csv` |
| Link entitlements to housing permits | `portal_link.py` | `data/portal/laguna_beach_ent_to_permit.csv` |
| Merge into one timeline per site | `portal_master.py` | `data/portal/laguna_beach_master.csv` |

Run them with the project's `.venv` Python (the system Python has no pandas):

```
python energov.py --city laguna_beach --start 2023-01 --end 2026-10 --list-types
python portal_link.py --city laguna_beach
python portal_master.py --city laguna_beach
```

## Source

Laguna Beach Citizen Self Service (Tyler EnerGov):
<https://lagunabeachca-energovweb.tylerhost.net/apps/selfservice>, checked November 10, 2026.
Public search, no login.

**Not yet confirmed by a person:**

- That the city's own website links to this portal. The city site refused our automated request.
- The portal's terms of use. We found no `robots.txt` (404) and no terms page.

Both should be checked before any larger pull or before publishing results.

## What we pulled

Records applied January 2023 to October 2026:

| | Records | With a parcel number |
|---|---:|---:|
| Plans (planning and plan check cases) | 9,825 | 9,646 |
| Permits | 9,483 | 9,382 |

The portal reports 57,839 permits in total, so its history goes back well before 2023. We have not
pulled the earlier years.

We keep type, work class, status and the applied, issued, finaled, completed and expiry dates.
Addresses and parcel numbers are replaced with the same one-way hashes `extract.py` uses for the APR
sample. Permit numbers, project names and descriptions are never saved.

## What we learned about scraping

1. **Go slower than the advice suggests.** At one request every 4 seconds the portal reset the
   connection after about 50 requests. At one every 8 seconds, the remaining 216 requests finished
   with no errors. We don't know the portal's actual limit.
2. **The search needs an exact request shape.** Permit and plan searches fail with a server error
   unless the type and status filters are sent as `"none"` rather than empty. That is what the
   portal's own search page sends. We expect other Tyler cities to behave the same way, but have not
   tested one.
3. **Cache every month.** The first long pull failed partway. Because each finished month is saved,
   the re-run picked up where it stopped. The scraper also backs off for minutes on a dropped
   connection and stops on a 403 or 429.
4. **Each city needs its own type lists.** Type names are set by the city. Laguna Beach has 89 plan
   type and work class combinations and 119 for permits.

## Results

### Building permit application to issuance (first test, permits applied January to June 2025)

Across all 1,178 permits the median is 0 days, because 546 of the 1,014 issued permits were issued
the day they were applied for (reroofs, electrical, plumbing). The all-permit number says nothing
about housing. Housing-related types take months: new single-family homes had a median of 231 days
(7 issued of 10), and attached ADUs 127.5 days (14 issued of 20).

### Entitlement to building permit (permits applied January 2023 to October 2026)

Wait is from the last approved entitlement on the parcel to building permit issuance.

| Permit type | Housing permits | Linked and issued | Median months | Middle half (months) | Entitled, no permit yet | No entitlement found |
|---|---:|---:|---:|---|---:|---:|
| All housing types | 452 | 117 | 8.4 | 5.6 to 14.2 | 99 | 236 |
| ADU attached | 241 | 64 | 7.4 | 5.5 to 14.3 | 46 | 131 |
| ADU detached | 106 | 24 | 6.4 | 4.8 to 10.5 | 26 | 56 |
| New single-family residence | 88 | 23 | 12.6 | 10.4 to 15.1 | 26 | 39 |

- **Cross-check with the APR.** New single-family homes show a 12.6-month median here. `plan.md`
  has 12.5 months for Laguna Beach from the APR. With 23 permits this could be coincidence, and
  the two samples are not the same projects, but it is our first comparison between the sources.
- **Projects still waiting.** The 99 entitled permits with no issuance have waited a median of
  13.0 months so far, longer than the median for those that finished. Medians of finished permits
  are biased short.
- **First or last entitlement.** 62 of the 117 had more than one entitlement on the parcel.
  Measured from the first one, the median is 9.9 months.

### Application to approval (same pull, from the master file)

`portal_master.py` also writes both waits onto each row of the master file: `days_apply_to_approval`
on plan rows and `days_approval_to_permit` on housing permit rows.

- **The master file is housing only.** It keeps housing permits (new single-family, ADU, new mixed
  use) and entitlement-type plans, and only at sites that have at least one housing record: 1,119
  records at 453 sites, down from 19,308 records at 5,288 sites. Reroofs, electrical, plumbing,
  remodels, additions and plan checks are dropped. ASSUMPTION: this is our reading of "housing
  relevant". Known gap: an entitlement for a new home with no building permit application yet can't
  be told apart from design review for a deck, so it is dropped until the permit appears.
- **Application to approval, all entitlements in the pull:** a median of 2.4 months across 969
  approved entitlements. Design review 2.3 (576), coastal development permit 2.4 (233), variance 2.8
  (78), conditional use permit 1.4 (39), ADU review 3.7 (33). The APR gives 2.3 months for Laguna
  Beach.
- **Application to approval, housing sites only (what the master file holds):** 2.6 months across
  405 approved entitlements.
- **Approval to permit, matched by site:** 8.3 months across 118 issued housing permits. The link
  file above matches by parcel only and finds 117.
- **Dates out of order:** in the full pull, 65 plans have a completed date before their applied
  date, 4 of them entitlements. They are not corrected. The cause is unknown.

## Assumptions

All of these are the team's choices, marked `ASSUMPTION` in the code and in
`data/portal/cities.json`. None is a city or HCD definition. A planner should review them.

| Assumption | What we chose |
|---|---|
| Which plans are entitlements | Design Review, Coastal Development Permit (not exemptions or waivers), Variance, Conditional Use Permit, ADU review, Second Residential Unit, parcel maps |
| Which are left out | "Residential Planning Entitlements" (1,371 records). Its only work class is "Zoning Plan Check", which looks like a step inside the building permit. Including it would shorten the waits. Unconfirmed. |
| When an entitlement is approved | Status is Approved, Completed, Cleared, or Cleared subject to requirements, and the record has a `completed` date |
| What the entitlement date is | The plan's `completed` date. What the city means by it is unknown. |
| Which permits are housing | New single-family, ADU and new mixed-use types. The portal has no "new multifamily" type. |
| How a permit finds its entitlement | Same parcel, entitlement completed on or before the permit was issued. Nothing in the search results says which entitlement belongs to which permit. |
| What "applied" means | Unknown. It could be the submittal date or the date the application was deemed complete. The team will decide how to treat it. |
| What a site is (master file) | Every address and parcel that any record connects |

## Where it gets things wrong

- **Half of housing permits found no entitlement.** 236 of 452. The cause is unknown: the approval
  may predate 2023, the project may be ministerial, or the parcel may not match.
- **The link can pick the wrong entitlement.** An unrelated approval on the same parcel, such as
  design review for a deck, can be linked to a later ADU permit.
- **Addresses and parcels don't always agree.** 147 addresses map to more than one parcel and 112
  parcels to more than one address. Likely reasons are ADUs with their own address, lot splits and
  condos, but we can't verify that from hashed data.
- **Some merged sites may be wrong.** Across the full pull, 145 of 5,288 sites join more than one
  address or parcel, and the largest joins 8 addresses and 35 parcels. Those large sites have no
  housing records, so they are not in the housing-only master file, where 22 sites join more than one
  key and none joins more than 2 addresses and 2 parcels. A wrong parcel number can still chain two
  unrelated properties.
- **The link and the master file group differently.** `portal_link.py` joins on parcel only and does
  not use the merged sites yet.
- **Small samples.** 23 issued new-home permits is not enough to rank a city.

## Adding another city

For a Tyler EnerGov city:

1. Copy the Laguna Beach entry in `data/portal/cities.json` and change `base_url`.
2. Pull one month with `--list-types`.
3. Fill the four type and status lists from what prints, and write down why.

Tenant settings are discovered automatically. Cities on Accela or other portals need a new fetcher
that writes the same CSV columns; the link and master scripts would then work unchanged. We have only
run this against Laguna Beach.

## Next steps

- A person confirms the portal link on the city's website and checks its terms.
- A planner reviews the entitlement and housing type lists.
- Make `portal_link.py` use the merged sites, and limit how far back an entitlement can be linked.
- Pull records from before 2023 to see how many "no entitlement found" permits it explains.
- Compare portal timelines with the APR sample. Both use the same parcel hash, so they can be joined.
- Try a second EnerGov city to test how much carries over.
