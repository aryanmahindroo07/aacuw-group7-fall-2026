-- Both labeled versions retain all 1,458 WA 2010 tracts. Never analyze both
-- versions as independent observations: filter sample AND included_in_analysis.
CREATE OR REPLACE TABLE tract_analysis AS
WITH versions AS (
    SELECT 'area_weighted' AS sample, * FROM nri_weighted
    UNION ALL
    SELECT 'strict_1to1' AS sample, * FROM nri_strict
), joined AS (
    SELECT v.sample, g.*, a.tract_name, a.income_raw,
           a.median_household_income, ln(a.median_household_income) AS log_median_income,
           a.poverty_rate, a.GEOID IS NULL AS missing_acs_record,
           a.median_household_income IS NULL AS missing_income,
           a.poverty_rate IS NULL AS missing_poverty,
           v.* EXCLUDE (sample, GEOID), c.min_nri_coverage,
           CASE WHEN v.sample = 'strict_1to1' AND NOT g.is_one_to_one THEN 'not_one_to_one'
                WHEN g.missing_life_expectancy THEN 'missing_life_expectancy'
                WHEN a.median_household_income IS NULL THEN 'missing_income'
                WHEN v.nri_area_coverage IS NULL OR v.nri_area_coverage < c.min_nri_coverage THEN 'low_nri_coverage'
                WHEN v.overall_risk_score IS NULL THEN 'missing_overall_risk'
                WHEN v.overall_risk_area_coverage < c.min_nri_coverage THEN 'low_overall_score_coverage'
                ELSE 'included' END AS analysis_status
    FROM geography_audit g JOIN versions v USING (GEOID)
    LEFT JOIN acs a ON g.GEOID = a.GEOID
    CROSS JOIN analysis_config c
)
SELECT *, analysis_status = 'included' AS included_in_analysis FROM joined;

CREATE OR REPLACE TABLE tract_audit AS SELECT * FROM tract_analysis;
CREATE OR REPLACE TABLE exclusion_counts AS
SELECT sample, analysis_status, count(*) AS tracts
FROM tract_analysis GROUP BY sample, analysis_status;
