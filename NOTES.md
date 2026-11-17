# Project notes

## Decisions and blockers — 2026-11-16 (America/Los_Angeles)

- Network access works after sandbox approval. Initial sandbox DNS lookup failed.
- Census API returned an HTML **Missing Key** page, even though the HTTP request succeeded. `CENSUS_API_KEY` is absent from this session. ACS and the final analysis are blocked until it is set locally. Never commit a key or paste one into project documentation.
- FEMA's current official tract service and dictionary are v1.20.0, December 2025. They use **Inland Flooding (`IFLD_*`)**, not Riverine Flooding (`RFLD_*`). The user explicitly approved current Inland Flooding on 2026-11-16. It is retained under its real name; no RFLD variable is invented.
- The legacy FEMA download page redirects to a general page. Use FEMA's official ArcGIS tract service, filter `STATEFIPS = '53'`, retain its raw JSON response, and serialize its attributes to CSV. This is an official-service extraction, not the legacy bulk CSV archive. Check returned count against the service's count endpoint and reject truncated responses.
- Census relationship file has 3,078 intersections, 1,471 distinct 2010 tracts and 1,784 distinct 2020 tracts. A strict reciprocal 1:1 match across **all** intersections yields only 392 pairs, losing 1,079 2010 tracts (73.4%). Do not discard small intersections or invent an area threshold. A future sensitivity analysis could revisit this with an explicit, documented method.
- USALEEP Washington has 1,370 rows, all with numeric life expectancy. There are 101 Census 2010 tracts absent from this file; these must be flagged as unavailable, not imputed.
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
