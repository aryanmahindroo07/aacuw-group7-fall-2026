# Small tasks for team commits

Four starter workstreams; confirm owners together (the slides list five members). Each person should run the pipeline and commit their own documentation or chart improvement.

1. **USALEEP owner — TODO name:** read CDC's record layout; document life table flags and standard errors; explain the missing-tract audit in 3 sentences. Commit: `docs: explain USALEEP coverage and estimate flags`.
2. **FEMA owner — TODO name:** read the saved dictionary and metadata; document each selected hazard, the inland/riverine change, and why overall risk is not climate-only. Review the risk scatter labels. Commit: `docs: describe NRI hazard scores and limitations`.
3. **ACS owner — TODO name:** get a local Census API key, run the downloader, verify B17001 numerator/denominator labels, document sentinel values and income top-coding, review the income boxplot. Commit: `docs: verify ACS income and poverty definitions`.
4. **SQL and visuals owner — TODO name:** run the SQL join and inspect `tract_audit.csv`; summarize exclusions, review the pairwise correlation counts, and add a chart caption. Commit: `docs: explain tract join losses and first findings`.

Aryan can coordinate the pipeline and help whichever workstream has two people. Do not share API keys in commits. Run `git status` before committing; generated raw data/databases stay local.

## Follow-up work

- Supply `CENSUS_API_KEY` locally and finish the end-to-end run. Do not claim a correlation until real complete inputs exist.
- Review unadjusted versus income-adjusted results, plus hazard-specific results; choose 2–3 visuals.
- If feasible, install GeoPandas and fetch appropriate Census TIGER boundaries for side-by-side maps; show excluded tracts distinctly.
- Find a stable WA DOH tract download and confirm measurement year/geography before adding PM2.5.
- Discuss sensitivity to the strict reciprocal mapping (no undocumented overlap threshold).
- Prepare a 5–7 minute talk with limitations and each teammate's contribution.
