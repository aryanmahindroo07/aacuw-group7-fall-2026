## Title and question

**Climate hazard risk and life expectancy in Washington**

Does climate-related hazard risk still predict life expectancy across Washington State census tracts after controlling for income?

## Team

AACUW Group 7, Fall 2026. **Intermediate, Route B (visuals).**
Launch slides list Anumita Basani, Aryan Mahindroo, Stephanie Balderas, Jiselle Vargas Salazar, and Dylan Huynh. TODO: confirm roster and task ownership.

## Data

- [CDC/NCHS USALEEP](https://www.cdc.gov/nchs/nvss/usaleep/usaleep.html): life expectancy at birth, 2010–2015; Washington, 2010 tracts.
- [FEMA National Risk Index](https://www.arcgis.com/home/item.html?id=9da4eeb936544335a6db0cd7a8448a51): v1.20.0, December 2025; WA 2020 tract geography. Drought, wildfire, heat wave, coastal flooding, **inland flooding** (user-approved current replacement for the requested riverine flooding), overall risk and expected annual loss.
- [ACS 2015 five-year API](https://api.census.gov/data/2015/acs/acs5.html): 2011–2015 median household income `B19013_001E`; poverty = `100 * B17001_002E / B17001_001E`.
- [Census tract relationship files](https://www.census.gov/geographies/reference-files/time-series/geo/relationship-files.2020.html): reciprocal 1:1 mappings only, no interpolation.
- Optional WA DOH EHD and maps deferred; details in [NOTES.md](NOTES.md).

Downloads began **2026-11-16 Pacific time**. Exact URLs, UTC timestamps, sizes and SHA-256 checksums are in [data/README.md](data/README.md) and `data/download_log.json`. Raw data and generated databases are ignored by Git.

## How to run

Python 3.9+ (3.10+ recommended). Run from the repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
# Set CENSUS_API_KEY in your local environment before downloading ACS.
python src/download.py
python src/clean.py
python notebooks/01_first_look.py
```

The current session has **no Census API key**; the API returned “Missing Key.” Obtain one at https://api.census.gov/data/key_signup.html and set `CENSUS_API_KEY` locally (do not commit it). The downloader logs failures and continues independent downloads, then exits nonzero if any required source failed. Existing validated, checksum-matching downloads are reused; `--refresh` redownloads them. `--only usaleep relationship nri` downloads independent sources without ACS. `python src/clean.py --audit-only` runs geography/life-expectancy and available NRI checks without ACS. Small JSON audit summaries are committed; detailed tract audit CSVs stay local.

Cleaning creates `data/clean/project.duckdb` with `tract_analysis` plus audit tables, `tract_analysis.csv`, and `project.sqlite` with a `tract_analysis` table and GEOID primary key. It refuses to build these analysis exports if any required source is missing or invalid. SQLPad needs a server-side SQLite connection with access to the exported file (a local file is not automatically uploaded to hosted SQLPad).

```sql
SELECT GEOID, life_expectancy, median_household_income, overall_risk_score
FROM tract_analysis
ORDER BY life_expectancy;
```

## Findings

Verified inputs: **1,370 USALEEP rows**, **1,458 Census 2010 tracts**, **1,784 Census 2020 tracts**. Only **392 reciprocal 1:1 pairs** survive the strict geography rule; 1,066 2010 tracts are excluded before other missing-data checks. USALEEP has no blank life expectancy among its published WA rows, but 88 Census tracts are absent from that file. Of the 392 pairs, 19 lack life expectancy, leaving **373 with life expectancy and a FEMA match before ACS checks**. FEMA contains **1,772 WA tracts** (99.3% of the 2020 universe); 385 of the 392 strict pairs match FEMA (98.2%).

**Answer and correlations: pending ACS key and a successful complete run.** No numbers are estimated or fabricated. The analysis script will save a scatter by income quartile, income boxplot, correlation table with pair counts, and descriptive income-adjusted results. TODO: review generated results and choose 2–3 presentation charts.

## Repo map

- `src/download.py`: validated official downloads and provenance log.
- `src/clean.py`: pandas input/schema checks, DuckDB SQL execution, audits and exports.
- `sql/`: normalization, strict tract mapping, joins and descriptive queries.
- `notebooks/01_first_look.py`: runnable first-look script (notebook alternative).
- `data/raw/`: local original downloads; `data/clean/`: local outputs and audit reports.
- `charts/`: PNG figures and small result tables after a complete run.
- `NOTES.md`: blockers, assumptions and limitations; `TODO.md`: teammate starter work.

## Limits and next steps

The strict mapping loses most 2010 tracts; report selection bias. NRI is later than the health/income data, includes non-climate hazards, and embeds vulnerability/resilience. These are tract-level associations, not evidence that climate change caused a lifespan difference. See [NOTES.md](NOTES.md) for all caveats.

Next: supply a Census API key, run and review the full pipeline, inspect join losses/missingness, evaluate income-adjusted hazard associations, and add linked maps if time permits. Midpoint: November 18; final talk: December 2, 2026 (launch slides).
