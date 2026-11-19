# Small tasks for team commits

The data pipeline, ACS download, area crosswalk, exports and first charts are complete. Four starter workstreams remain; confirm owners together (the slides list five members). Each teammate should commit their own review, caption or improvement.

1. **USALEEP owner — Dylan Huynh:** read CDC's record layout, explain estimate flags/standard errors, and caption the 88 tracts with no published estimate. Commit: `docs: explain USALEEP coverage and estimate flags`.
2. **FEMA owner — TODO name:** review the dictionary, explain why overall risk is not climate-only, and compare heat-wave and wildfire results. We use the current FEMA Inland Flooding field. Commit: `docs: explain hazard-specific findings`.
3. **ACS owner — TODO name:** review poverty numerator/denominator labels, explain special negative missing-data codes and income top-coding, and caption the income boxplot. The API download is complete; obtaining a key is not an open task. Commit: `docs: explain ACS measures and income chart`.
4. **SQL and visuals owner — TODO name:** query one sample at a time, explain land weights and the 95% cutoff, and compare the 1,370 main tracts with the 373 strict tracts. Review correlation pair counts. Commit: `docs: explain crosswalk and sample sensitivity`.

Aryan can coordinate and help the workstream with two people. Run `python src/validate.py` after changing calculations. Do not share keys or commit raw data/databases.

## Next improvements

- Select 2–3 presentation visuals and review captions together. Explain the weak positive overall-risk association without implying that hazards improve health.
- Consider sensitivity to coverage cutoffs, population weighting, physical hazard measures and spatial dependence.
- Add linked maps with appropriate Census boundaries if feasible; show missing life-expectancy tracts separately.
- Find a stable WA DOH download and confirm measurement year and boundaries before adding PM2.5.
- Prepare a 5–7 minute talk and list each teammate's contribution. Midpoint: November 18; final talk: December 2, 2026.
