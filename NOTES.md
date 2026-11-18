# Project notes

## Status — November 17, 2026 (Pacific time)

The pipeline completed with real CDC, Census and FEMA inputs. ACS was downloaded in the user's terminal using CENSUS_API_KEY; the agent reused the validated local file. No key is printed, stored in the provenance log, or committed. The earlier missing-key blocker is resolved.

The ACS downloader, full cleaning, the first-look script and `src/validate.py` all ran successfully. Outputs are the DuckDB, CSV and SQLite `tract_analysis` table, four chart PNGs, pairwise correlation counts, and descriptive model results. Data files and databases remain ignored by Git.

## Source validation and real column names

- USALEEP: `Tract ID`, `e(0)`, `se(e(0))`, `Abridged life table flag`. There are 1,370 published WA estimates; all life expectancy values are numeric. Of the 1,458 Census 2010 tracts, 88 lack a record. Nothing is imputed.
- ACS: a JSON table, not an HTML Missing Key page, with all 1,458 WA 2010 tracts. B19013_001E is median household income. Metadata confirms B17001_001E is the population whose poverty status is determined and B17001_002E is the population below poverty. Poverty rate is 100 times their ratio.
- ACS income has 15 special negative codes and one null. The negative codes mean an estimate is unavailable, not that household income is negative. All 16 are flagged as missing; none has a USALEEP estimate, so they remove no additional main-sample tracts. Zero/nonpositive income is excluded because its logarithm cannot be used. Thirteen tracts have no usable poverty denominator; all 1,370 main-sample poverty rates are available.
- FEMA: official item/dictionary v1.20.0; row NRI_VER is the literal date December 2025. We use the current FEMA Inland Flooding field. Scores are RISK_SCORE, DRGT_RISKS, WFIR_RISKS, HWAV_RISKS, CFLD_RISKS, and IFLD_RISKS. Not Applicable/Insufficient Data ratings leave scores missing. No Rating with a real zero score is retained.
- FEMA has 1,772 of 1,784 WA 2020 tracts (99.327%). All 431 null coastal-flooding scores are rated Not Applicable. Other selected raw scores have no null values. EAL_VALT remains in the source table but no dollar total or rating is averaged or used in final analysis.
- The legacy FEMA page redirects; raw official ArcGIS query JSON is retained and serialized to CSV. Its count endpoint, fields, version, state filter and completeness are checked. See data/README.md for exact URLs and dates.

## Area-weighted main crosswalk

The national relationship file has 126,450 intersections; 3,078 have WA 2020 tracts. A preliminary old count of 1,471 included 13 neighboring-state 2010 IDs; the WA 2010 count is 1,458. National intersections are retained when checking whether a tract has only one counterpart, so cross-state overlaps cannot create false strict matches.

For the main crosswalk, both IDs start with state FIPS 53. Real fields are GEOID_TRACT_10, GEOID_TRACT_20, AREALAND_PART, and AREALAND_TRACT_10. Each old tract has a consistent total land area; its national intersection land areas sum exactly to that total. Tracts and parts are not dropped merely for being small.

```
weight_ij = intersecting land area_ij / total land area_i
score_i = sum(weight_ij * score_j for valid scores)
          / sum(weight_ij for valid scores)
nri_area_coverage_i = sum(weight_ij for matched WA FEMA records)
```

Scores are calculated separately for all six fields. Missing/Not Applicable scores contribute neither numerator nor denominator. Without a positive-area valid score, the result is null. The denominator covers the whole old tract, including any tiny part outside WA; filtering to WA does not shrink it. Floating-point addition can differ from one by about 1e-16; validation allows 1e-12 numerical tolerance without changing data.

Ten tracts have zero land area, so their land-based coverage and weighted scores are undefined. All lack USALEEP estimates. Every positive-land main-sample tract has at least 99.9939% matched-area and valid overall-score coverage. This does not imply full population coverage.

The cutoff defaults to 0.95 in src/clean.py and is configurable via --min-nri-coverage; analysis_config stores it in DuckDB. Main eligibility requires life expectancy, positive income, overall risk, and both matched-area and valid overall-score coverage at or above the cutoff. Hazard-specific correlations/models require that hazard's valid coverage to reach the same cutoff. Weighted values remain stored even below the cutoff. Fourteen tracts have a non-null coastal score based on less than 95% land and are omitted from coastal analysis. In total, 323 main-sample tracts fail the coastal-score requirement, leaving 1,047. No missing coastal scores become zero.

tract_analysis retains all 1,458 tracts in each version: sample='area_weighted' and sample='strict_1to1', or 2,916 exported rows. The unique key is (sample, GEOID); GEOID is a 2010 tract ID. GEOID2020 identifies the counterpart only when strict matching is possible, otherwise it is null. included_in_analysis and analysis_status preserve exclusion decisions. Never combine the two versions as independent observations.

## Counts and sample comparison

| Main sequence | Removed | Remaining |
|---|---:|---:|
| WA 2010 universe | — | 1,458 |
| Missing USALEEP estimate | 88 | 1,370 |
| Missing/nonpositive income after that | 0 | 1,370 |
| Low matched NRI land coverage after that | 0 | 1,370 |
| Missing/low-coverage overall risk after that | 0 | 1,370 |

The strict check requires one old tract to intersect only one new tract, and that new tract to intersect only that old tract. It counts all intersections, including water and tiny boundary changes. It leaves 392 pairs: 1,066 tracts fail the rule and 19 remaining pairs lack life expectancy, leaving 373. All 373 have income and FEMA scores. Of all 392 pairs, 385 match FEMA (98.214%); the seven unmatched pairs already lack life expectancy.

The area crosswalk adds 997 eligible tracts and avoids using unchanged boundaries as the main selection rule. The strict sample is a selected subset, not an independent replication.

## Descriptive analysis

Ordinary least squares (OLS) fits a straight-line association. Each tract receives equal weight. Both models include an intercept and use the same complete records for each score:

1. life expectancy ~ risk score
2. life expectancy ~ risk score + ln(median household income)

Log income means the natural logarithm, allowing a curved relationship between dollar income and life expectancy. Coefficients below are **years per 10 risk-score points**. Partial correlations use residuals after controlling for log income. No spatial adjustment, uncertainty intervals or statistical-significance claims are made.

| Sample | n | Overall-risk Pearson r | Risk-only coefficient | Log-income-adjusted coefficient | Change |
|---|---:|---:|---:|---:|---:|
| Area-weighted | 1,370 | +0.069268 | +0.087617 | +0.117471 | +0.029854 |
| Strict 1:1 | 373 | +0.100183 | +0.127776 | +0.100865 | −0.026911 |

The weak positive overall-risk association remains after adjustment in both samples. Adjustment increases the main coefficient but decreases the strict coefficient. This does not demonstrate that hazards improve health or that overall NRI is an effective predictive model.

| Hazard | Main n | Main adjusted coefficient | Strict n | Strict adjusted coefficient |
|---|---:|---:|---:|---:|
| Drought | 1,370 | +0.121967 | 373 | +0.149048 |
| Wildfire | 1,370 | +0.199772 | 373 | +0.172572 |
| Heat wave | 1,370 | −0.151659 | 373 | −0.193459 |
| Coastal flooding | 1,047 | +0.050518 | 302 | +0.086103 |
| Inland flooding | 1,370 | +0.113506 | 373 | +0.095346 |

Hazard directions match between samples, while magnitudes differ. Main-sample mean life expectancy rises across income quartiles: 77.15, 79.03, 80.37 and 82.16 years. Each correlation pair reports its usable n.

## Verification and resolved implementation issues

- src/validate.py independently recomputes all six weighted scores and matched-area coverage with pandas from raw inputs, agreeing to numerical tolerance.
- DuckDB, CSV and SQLite round trips agree for all 2,916 rows. SQLite integrity passes; GEOIDs remain 11-character strings and its composite unique index prevents duplicate sample/tract rows.
- Independent centered scalar formulas verify both overall-risk OLS fits in both samples. Pairwise correlation counts are independently checked.
- Initial round-trip validation inferred numeric-looking life-table flag strings as numbers when reading CSV. Explicit string types and normalized text nulls resolve this validation-reader issue; the source values were unchanged.
- NumPy matrix-vector multiplication emitted floating-point warnings despite finite OLS results on this system. Writing the two-variable fitted values explicitly avoids that path. Independent coefficient calculations agree; the analysis rerun is warning-free.
- All four PNGs were opened and visually inspected for labels, clipping and readable sample sizes. The original strict-only pipeline also passed before the crosswalk change. Its earlier linear-income result is superseded by the requested log-income models in both samples.
- System Python 3.9/LibreSSL still emits a requests/urllib3 compatibility warning on downloader startup. Downloads succeeded; Python 3.10+ with OpenSSL is recommended. No warning is suppressed.

## Interpretation limits and unfinished extras

- Area weights assume uniform scores over land, rather than population. Scores are national relative measures; their averages are approximate summaries, not official FEMA 2010 scores. They are not physical exposure units.
- FEMA's mixed-period hazard/exposure inputs are later than the outcome and income data. This is a cross-period tract association, not a causal climate-change estimate or an out-of-sample prediction test.
- Overall NRI includes non-climate hazards and social vulnerability/community resilience. Income adjustment does not isolate physical exposure. Other confounding, spatial dependence, ecological bias and ACS/USALEEP uncertainty remain.
- Optional WA DOH EHD air-quality data are deferred: the WTN portal describes downloadable tables, but a stable direct tract file with verified year/boundaries was not established. No PM2.5 values are invented. Source: https://doh.wa.gov/data-and-statistical-reports/washington-tracking-network-wtn/washington-environmental-health-disparities-map
- Optional TIGER/GeoPandas choropleths are deferred. The requested scatter, boxplot, correlation table and extra coefficient chart are complete. No core pipeline blocker remains.
