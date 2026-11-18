-- Examples for DuckDB or SQLPad's SQLite connection to project.sqlite.
SELECT COUNT(*) AS tracts, MIN(life_expectancy) AS min_life_expectancy,
       MAX(life_expectancy) AS max_life_expectancy,
       AVG(median_household_income) AS mean_tract_median_income
FROM tract_analysis WHERE sample = 'area_weighted' AND included_in_analysis;

SELECT sample, analysis_status, COUNT(*) AS tracts
FROM tract_analysis GROUP BY sample, analysis_status ORDER BY sample, analysis_status;
