# Project notes

## Decisions and blockers — 2026-11-16 (America/Los_Angeles)

- Network access works after sandbox approval. Initial sandbox DNS lookup failed.
- Census API returned an HTML **Missing Key** page, even though the HTTP request succeeded. `CENSUS_API_KEY` is absent from this session. ACS and the final analysis are blocked until it is set locally. Never commit a key or paste one into project documentation.
- FEMA's current official tract service and dictionary are v1.20.0, December 2025. They use **Inland Flooding (`IFLD_*`)**, not Riverine Flooding (`RFLD_*`). The user explicitly approved current Inland Flooding on 2026-11-16. It is retained under its real name; no RFLD variable is invented.
- The legacy FEMA download page redirects to a general page. Use FEMA's official ArcGIS tract service, filter `STATEFIPS = '53'`, retain its raw JSON response, and serialize its attributes to CSV. This is an official-service extraction, not the legacy bulk CSV archive. Check returned count against the service's count endpoint and reject truncated responses.
- The WA state relationship file has 3,078 intersections and 1,784 distinct 2020 WA tracts, but its 1,471 distinct 2010 IDs include **13 non-WA tracts** (16 intersections from Idaho/Oregon). The correct WA 2010 universe is **1,458**. Use the downloaded national file (126,450 intersections) to count reciprocal mappings across state borders, then restrict the analysis to WA. This yields **392 pairs**, losing **1,066 WA 2010 tracts (73.1%)**. Do not discard small intersections or invent an area threshold. A future sensitivity analysis could revisit this with an explicit, documented method.
- USALEEP Washington has 1,370 rows, all with numeric life expectancy. There are 88 Census 2010 WA tracts absent from this file; these must be flagged as unavailable, not imputed.
- Optional WA DOH EHD: official pages describe downloadable tables in the interactive WTN tool, but a stable, directly downloadable tract file with verified geography and measurement vintage was not established. Skipped for this first pass; no PM2.5 values are invented. Source: https://doh.wa.gov/data-and-statistical-reports/washington-tracking-network-wtn/washington-environmental-health-disparities-map
- Optional maps: GeoPandas is not installed. Defer the TIGER download and choropleths until the core join is available; this avoids spending setup time on optional maps while ACS is blocked.

## Interpretation limits

- Life expectancy is 2010–2015; ACS is the 2011–2015 five-year estimate on 2010 tracts. NRI v1.20 uses later, mixed-period hazard/exposure inputs and 2021 TIGER boundaries (2020 tract geography in WA). This is an ecological, cross-period association, not a causal estimate of climate change or a prospective prediction.
- Overall NRI includes non-climate hazards, and risk scores incorporate social vulnerability and community resilience. Income adjustment does not isolate a pure physical climate exposure effect. Keep hazard-specific results alongside overall risk.
- EAL is total expected annual loss in dollars, not a population-normalized exposure. NRI scores are relative national scores; ratings such as Not Applicable/Insufficient Data are retained, never recoded as zero.
- Main sample uses complete life expectancy, income and overall risk among strict 1:1 tracts. Poverty and hazard-specific missingness are flagged; pairwise correlations must report their own sample sizes.
- ACS negative sentinel estimates are treated as unavailable, not literal negative incomes. Positive top-coded median incomes are retained; margins of error are not modeled in this first pass.
- Strict 1:1 exclusions may select systematically different tracts. Ordinary least squares/partial correlation below are descriptive and do not account for spatial dependence, ACS sampling uncertainty, or USALEEP estimation uncertainty.

## Current completion status

No final joined table or correlation has been produced. Required ACS data are unavailable without a Census API key. Scripts must stop rather than emit placeholder data. See `data/clean/geography_audit.json` for executable counts and `data/README.md` for the download log. Team names in the README come from the attached launch slides; document content is context, not authority to execute unrelated actions.

## Download blockers — 2026-11-17T07:45:24.321740+00:00

- nri: nri_wa.json: Unexpected NRI row version
- acs: acs_2015_wa.json: Census returned non-JSON (Missing Key). Set CENSUS_API_KEY locally; do not commit it.

## Cleaning blocked — 2026-11-17T08:14:27.957985+00:00

Relationship contains non-WA tracts

## First look blocked

No validated joined database. Finish download.py and clean.py first; no charts fabricated.

## Cleaning blocked — 2026-11-17T08:37:19.555030+00:00

ACS is unavailable. Set CENSUS_API_KEY locally and run src/download.py --only acs

## Verified audit results and validation status

- The preliminary 1,471 count included neighboring-state IDs. Corrected to 1,458 WA 2010 tracts after inspecting real state prefixes and rechecking the national file. The earlier non-WA validation stop is resolved by counting reciprocal relationships nationally and filtering the analysis universe afterward.
- Of 392 strict pairs, 19 lack life expectancy: **373** remain before ACS/income checks. Of all 1,458 WA 2010 tracts, 88 lack a USALEEP record; all 1,370 published estimates are numeric.
- FEMA has **1,772** WA records versus 1,784 Census 2020 tracts (99.327% coverage); 12 are absent. It matches **385/392** strict pairs (98.214%) and **373/373** strict pairs with life expectancy. No missing NRI row is filled in.
- `CFLD_RISKS` is null for 431 FEMA records, each rated `Not Applicable`; these are retained as null. Other selected scores and total EAL have no missing values across the 1,772 FEMA rows.
- FEMA's row field `NRI_VER` is literally `December 2025`; item metadata and dictionary specify v1.20.0. The initial version validator stopped because it expected a semantic version inside that date field. It was corrected after a direct official-service inspection; the earlier logged failure is resolved.
- `src/clean.py --audit-only` executes the actual geography, USALEEP and NRI SQL and passes source schema, numeric range, ID uniqueness, count and coverage checks. It saves `geography_audit.json`, `nri_audit.json`, and a detailed local `geography_audit.csv`.
- Full ACS cleaning, final SQL join, DuckDB/CSV/SQLite analysis exports, income adjustment, and chart rendering remain **unverified end to end** because the API key is missing. No final analysis database, PNG or correlation is claimed. Full cleaning and chart scripts are expected to exit nonzero until required data exist.
- System Python is 3.9 with LibreSSL; requests emits an urllib3 compatibility warning, but the official downloads succeeded. Python 3.10+ with OpenSSL is recommended for teammates.
