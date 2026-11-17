-- Names verified against FEMA's December 2025 v1.20.0 dictionary and records.
-- Scores/ratings remain distinct. Inland flooding is explicitly NOT named riverine.
CREATE OR REPLACE TABLE nri AS
SELECT lpad(TRACTFIPS, 11, '0') AS GEOID2020, NRI_VER AS nri_release,
       CAST(RISK_SCORE AS DOUBLE) AS overall_risk_score, RISK_RATNG AS overall_risk_rating,
       CAST(EAL_VALT AS DOUBLE) AS expected_annual_loss,
       CAST(DRGT_RISKS AS DOUBLE) AS drought_risk_score, DRGT_RISKR AS drought_risk_rating,
       CAST(WFIR_RISKS AS DOUBLE) AS wildfire_risk_score, WFIR_RISKR AS wildfire_risk_rating,
       CAST(HWAV_RISKS AS DOUBLE) AS heat_wave_risk_score, HWAV_RISKR AS heat_wave_risk_rating,
       CAST(CFLD_RISKS AS DOUBLE) AS coastal_flooding_risk_score, CFLD_RISKR AS coastal_flooding_risk_rating,
       CAST(IFLD_RISKS AS DOUBLE) AS inland_flooding_risk_score, IFLD_RISKR AS inland_flooding_risk_rating
FROM nri_input
WHERE STATEFIPS = '53';
