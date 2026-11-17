-- ACS publishes negative sentinel codes. Keep their raw values for inspection,
-- and expose unavailable estimates as NULL (never as zero).
CREATE OR REPLACE TABLE acs AS
WITH estimates AS (
    SELECT lpad(state, 2, '0') || lpad(county, 3, '0') || lpad(tract, 6, '0') AS GEOID,
           NAME AS tract_name,
           CAST(B19013_001E AS DOUBLE) AS income_raw,
           CAST(B17001_001E AS DOUBLE) AS poverty_universe_raw,
           CAST(B17001_002E AS DOUBLE) AS poverty_count_raw
    FROM acs_input
)
SELECT *, CASE WHEN income_raw >= 0 THEN income_raw END AS median_household_income,
       CASE WHEN poverty_universe_raw > 0 AND poverty_count_raw >= 0
            THEN 100.0 * poverty_count_raw / poverty_universe_raw END AS poverty_rate
FROM estimates;

