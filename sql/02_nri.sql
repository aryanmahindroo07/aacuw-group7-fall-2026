-- Names verified against FEMA's December 2025 v1.20.0 dictionary and records.
-- Scores/ratings remain distinct. Inland flooding is explicitly NOT named riverine.
CREATE OR REPLACE TABLE nri AS
SELECT lpad(TRACTFIPS, 11, '0') AS GEOID2020, NRI_VER AS nri_release,
       CASE WHEN RISK_RATNG NOT IN ('Not Applicable', 'Insufficient Data') THEN CAST(RISK_SCORE AS DOUBLE) END AS overall_risk_score, RISK_RATNG AS overall_risk_rating,
       CAST(EAL_VALT AS DOUBLE) AS expected_annual_loss,
       CASE WHEN DRGT_RISKR NOT IN ('Not Applicable', 'Insufficient Data') THEN CAST(DRGT_RISKS AS DOUBLE) END AS drought_risk_score, DRGT_RISKR AS drought_risk_rating,
       CASE WHEN WFIR_RISKR NOT IN ('Not Applicable', 'Insufficient Data') THEN CAST(WFIR_RISKS AS DOUBLE) END AS wildfire_risk_score, WFIR_RISKR AS wildfire_risk_rating,
       CASE WHEN HWAV_RISKR NOT IN ('Not Applicable', 'Insufficient Data') THEN CAST(HWAV_RISKS AS DOUBLE) END AS heat_wave_risk_score, HWAV_RISKR AS heat_wave_risk_rating,
       CASE WHEN CFLD_RISKR NOT IN ('Not Applicable', 'Insufficient Data') THEN CAST(CFLD_RISKS AS DOUBLE) END AS coastal_flooding_risk_score, CFLD_RISKR AS coastal_flooding_risk_rating,
       CASE WHEN IFLD_RISKR NOT IN ('Not Applicable', 'Insufficient Data') THEN CAST(IFLD_RISKS AS DOUBLE) END AS inland_flooding_risk_score, IFLD_RISKR AS inland_flooding_risk_rating
FROM nri_input
WHERE STATEFIPS = '53';
