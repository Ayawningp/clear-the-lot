# APR field names (Step 0)

Read from the headers of the full CSV downloads of the two tables on data.ca.gov
(dataset "Housing Element Annual Progress Report (APR) Data by Jurisdiction and Year",
https://data.ca.gov/dataset/housing-element-annual-progress-report-apr-data-by-jurisdiction-and-year).
Files downloaded by the team on 2026-11-07. Header read 2026-11-07.

| Table | Resource ID | Rows statewide (our download) | Orange County rows | Reporting years in OC |
|---|---|---|---|---|
| A  | `c78b769d-cc02-4050-91ef-79ded665b5a8` | 358,228 | 14,348 | 2018 to 2025 |
| A2 | `fe505d9b-8c36-42ba-ba30-08bc4f34e022` | 927,011 | 53,578 | 2018 to 2025 |

(The event's data list said 358,215 and 927,006 rows; our download is slightly larger,
consistent with the dataset being updated on 2026-10-30.)

## Fields we use

| What the spec needs | Table A field | Table A2 field | Notes |
|---|---|---|---|
| Jurisdiction | `JURIS_NAME` | `JURIS_NAME` | Uppercase city name, e.g. `IRVINE`. Unincorporated is `ORANGE COUNTY`. |
| County | `CNTY_NAME` | `CNTY_NAME` | `Orange` for OC. We filter on this. |
| Reporting year | `YEAR` | `YEAR` | |
| APN | `APN` | `APN` | Formats vary (`407-107-30`); normalized to digits only. |
| Prior APN | `PRIOR_APN` | `PRIOR_APN` | Usually blank. |
| Street address | `STREET_ADDRESS` | `STREET_ADDRESS` | Free text, sometimes multi-line. Used for matching only, never displayed. |
| Geocoded address | `STD_ADDRESS` | `STD_ADDRESS` | Added by the publisher (with `LATITUDE`, `LONGITUDE`, `SCORE`). |
| Local tracking ID | `JURS_TRACKING_ID` | `JURS_TRACKING_ID` | Often a per-permit number, so it changes between stages. Not used, and dropped from the committed sample: a city permit number can be looked up to find the address. |
| Unit category | `UNIT_CAT` | `UNIT_CAT` | Values seen: `SFD`, `SFA`, `2 to 4`, `5+`, `ADU`, `MH`. |
| Tenure | `TENURE` | `TENURE` | `Owner` or `Renter`. |
| Application submitted | `APP_SUBMIT_DT` | (none) | ISO date `YYYY-MM-DD`. |
| SB 35 flag | `APP_SUBMITTED_SB35` | `APPROVE_SB35` | A: `Yes`/`No`. A2: `Y`/`N`. |
| Application outcome | `APPLICATION_STATUS` | (none) | e.g. `Pending`, `Approved`. |
| Units proposed / approved | `TOT_PROPOSED_UNITS`, `TOT_APPROVED_UNITS` | (none) | |
| Entitlement date | (none) | `ENT_APPROVE_DT1` | ISO date. |
| Units entitled | (none) | `NO_ENTITLEMENTS` | |
| Building permit date | (none) | `BP_ISSUE_DT1` | ISO date. |
| Units permitted | (none) | `NO_BUILDING_PERMITS` | |
| Certificate of occupancy date | (none) | `CO_ISSUE_DT1` | ISO date. |
| Units completed | (none) | `NO_OTHER_FORMS_OF_READINESS` | INFERRED, not confirmed: it sits right after `CO_ISSUE_DT1`, the way `NO_BUILDING_PERMITS` follows `BP_ISSUE_DT1`, so it looks like the CO unit count. Check the HCD APR instructions before relying on it. We do not use it in any calculation. |

## How the data is shaped (observed, 2026-11-07)

- One A2 row is roughly one permit or one approval record, not one project. A project with
  several homes on one APN can show several rows in the same year (one per permit).
- Each yearly report carries only the dates that happened that year (HCD APR instructions), so
  one project's entitlement, permit and CO dates sit in different years' rows.
- Income-band columns (`VLOW_INCOME_DR`, `BP_LOW_INCOME_NDR`, ...) exist but are not used.

## Full headers

Table A:
`JURIS_NAME, CNTY_NAME, YEAR, PRIOR_APN, APN, STREET_ADDRESS, PROJECT_NAME, JURS_TRACKING_ID, UNIT_CAT, TENURE, APP_SUBMIT_DT, ACUTELY_LOW_INCOME_DR, ACUTELY_LOW_INCOME_NDR, EXTREMELY_LOW_INCOME_DR, EXTREMELY_LOW_INCOME_NDR, VLOW_INCOME_DR, VLOW_INCOME_NDR, LOW_INCOME_DR, LOW_INCOME_NDR, MOD_INCOME_DR, MOD_INCOME_NDR, ABOVE_MOD_INCOME, TOT_PROPOSED_UNITS, TOT_APPROVED_UNITS, TOT_DISAPPROVED_UNITS, APP_SUBMITTED_SB35, HISTORIC_SITES, DENSITY_BONUS_RECEIVED, DENSITY_BONUS_APPROVED, APPLICATION_STATUS, PROJECT_TYPE, NOTES, LATITUDE, LONGITUDE, STD_ADDRESS, SCORE`

Table A2:
`JURIS_NAME, CNTY_NAME, YEAR, PRIOR_APN, APN, STREET_ADDRESS, PROJECT_NAME, JURS_TRACKING_ID, UNIT_CAT, TENURE, ACUTELY_LOW_INCOME_DR, ACUTELY_LOW_INCOME_NDR, EXTREMELY_LOW_INCOME_DR, EXTREMELY_LOW_INCOME_NDR, VLOW_INCOME_DR, VLOW_INCOME_NDR, LOW_INCOME_DR, LOW_INCOME_NDR, MOD_INCOME_DR, MOD_INCOME_NDR, ABOVE_MOD_INCOME, ENT_APPROVE_DT1, NO_ENTITLEMENTS, BP_ACUTELY_LOW_INCOME_DR, BP_ACUTELY_LOW_INCOME_NDR, BP_EXTREMELY_LOW_INCOME_DR, BP_EXTREMELY_LOW_INCOME_NDR, BP_VLOW_INCOME_DR, BP_VLOW_INCOME_NDR, BP_LOW_INCOME_DR, BP_LOW_INCOME_NDR, BP_MOD_INCOME_DR, BP_MOD_INCOME_NDR, BP_ABOVE_MOD_INCOME, BP_ISSUE_DT1, NO_BUILDING_PERMITS, CO_ACUTELY_LOW_INCOME_DR, CO_ACUTELY_LOW_INCOME_NDR, CO_EXTREMELY_LOW_INCOME_DR, CO_EXTREMELY_LOW_INCOME_NDR, CO_VLOW_INCOME_DR, CO_VLOW_INCOME_NDR, CO_LOW_INCOME_DR, CO_LOW_INCOME_NDR, CO_MOD_INCOME_DR, CO_MOD_INCOME_NDR, CO_ABOVE_MOD_INCOME, CO_ISSUE_DT1, NO_OTHER_FORMS_OF_READINESS, EXTR_LOW_INCOME_UNITS, APPROVE_SB35, HISTORIC_SITES, INFILL_UNITS, FIN_ASSIST_NAME, DR_TYPE, NO_FA_DR, TERM_AFF_DR, DEM_DES_UNITS, DEM_OR_DES_UNITS, DEM_DES_UNITS_OWN_RENT, DENSITY_BONUS_TOTAL, DENSITY_BONUS_NUMBER_OTHER_INCENTIVES, DENSITY_BONUS_INCENTIVES, DENSITY_BONUS_RECEIVE_REDUCTION, NOTES, LATITUDE, LONGITUDE, STD_ADDRESS, SCORE`
