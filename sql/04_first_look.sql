-- Examples for DuckDB or SQLPad's SQLite connection to project.sqlite.
SELECT COUNT(*) AS tracts, MIN(life_expectancy) AS min_life_expectancy,
       MAX(life_expectancy) AS max_life_expectancy,
       AVG(median_household_income) AS mean_tract_median_income
FROM tract_analysis;

SELECT overall_risk_rating, COUNT(*) AS tracts, AVG(life_expectancy) AS mean_life_expectancy
FROM tract_analysis GROUP BY overall_risk_rating ORDER BY mean_life_expectancy;
