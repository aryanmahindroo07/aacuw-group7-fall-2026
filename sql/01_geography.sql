-- Inputs are pandas frames registered by src/clean.py. All IDs enter as strings.
CREATE OR REPLACE TABLE tract_relationship AS
SELECT DISTINCT lpad(GEOID_TRACT_10, 11, '0') AS GEOID,
       lpad(GEOID_TRACT_20, 11, '0') AS GEOID2020,
       CAST(AREALAND_PART AS DOUBLE) AS land_overlap_m2,
       CAST(AREALAND_TRACT_10 AS DOUBLE) AS land_area_2010_m2,
       CAST(AREAWATER_PART AS DOUBLE) AS water_overlap_m2
FROM relationship_input;

-- Count ALL intersections, including water and tiny boundary intersections.
CREATE OR REPLACE TABLE tract_mapping AS
WITH pairs AS (SELECT DISTINCT GEOID, GEOID2020 FROM tract_relationship),
counts AS (
    SELECT *, count(*) OVER (PARTITION BY GEOID) AS n_2020_per_2010,
           count(*) OVER (PARTITION BY GEOID2020) AS n_2010_per_2020
    FROM pairs
)
SELECT *, n_2020_per_2010 = 1 AND n_2010_per_2020 = 1
          AND starts_with(GEOID2020, '53') AS is_one_to_one
FROM counts;

CREATE OR REPLACE TABLE life_expectancy AS
SELECT lpad("Tract ID", 11, '0') AS GEOID,
       CAST("e(0)" AS DOUBLE) AS life_expectancy,
       CAST("se(e(0))" AS DOUBLE) AS life_expectancy_se,
       "Abridged life table flag" AS life_table_flag
FROM usaleep_input;

CREATE OR REPLACE TABLE geography_audit AS
SELECT g.GEOID, m.GEOID2020,
       m.GEOID IS NOT NULL AS is_one_to_one,
       u.GEOID IS NULL AS missing_usaleep_record,
       u.life_expectancy IS NULL AS missing_life_expectancy,
       u.life_expectancy, u.life_expectancy_se, u.life_table_flag
FROM (SELECT DISTINCT GEOID FROM tract_mapping) g
LEFT JOIN tract_mapping m ON g.GEOID = m.GEOID AND m.is_one_to_one
LEFT JOIN life_expectancy u ON g.GEOID = u.GEOID
WHERE starts_with(g.GEOID, '53');
