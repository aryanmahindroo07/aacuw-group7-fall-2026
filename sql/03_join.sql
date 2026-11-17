-- Audit starts at the FULL Census 2010 tract universe, not only published USALEEP.
CREATE OR REPLACE TABLE tract_audit AS
SELECT g.*, a.tract_name, a.income_raw, a.median_household_income, a.poverty_rate,
       a.GEOID IS NULL AS missing_acs_record,
       a.median_household_income IS NULL AS missing_income,
       a.poverty_rate IS NULL AS missing_poverty,
       n.GEOID2020 IS NULL AS missing_nri_record,
       n.* EXCLUDE (GEOID2020),
       n.overall_risk_score IS NULL AS missing_overall_risk,
       n.drought_risk_score IS NULL AS missing_drought_risk,
       n.wildfire_risk_score IS NULL AS missing_wildfire_risk,
       n.heat_wave_risk_score IS NULL AS missing_heat_wave_risk,
       n.coastal_flooding_risk_score IS NULL AS missing_coastal_flooding_risk,
       n.inland_flooding_risk_score IS NULL AS missing_inland_flooding_risk,
       -- Mutually exclusive sequential exclusion reason makes drops add up.
       CASE WHEN NOT g.is_one_to_one THEN 'not_reciprocal_one_to_one'
            WHEN g.missing_life_expectancy THEN 'missing_life_expectancy'
            WHEN a.GEOID IS NULL THEN 'missing_acs_record'
            WHEN a.median_household_income IS NULL THEN 'missing_income'
            WHEN n.GEOID2020 IS NULL THEN 'missing_nri_record'
            WHEN n.overall_risk_score IS NULL THEN 'missing_overall_risk'
            ELSE 'included' END AS analysis_status
FROM geography_audit g
LEFT JOIN acs a ON g.GEOID = a.GEOID
LEFT JOIN nri n ON g.GEOID2020 = n.GEOID2020;

CREATE OR REPLACE TABLE tract_analysis AS
SELECT * FROM tract_audit WHERE analysis_status = 'included';

CREATE OR REPLACE TABLE exclusion_counts AS
SELECT analysis_status, count(*) AS tracts FROM tract_audit GROUP BY analysis_status;
