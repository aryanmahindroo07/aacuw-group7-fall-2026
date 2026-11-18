-- Keep WA 2010 and WA 2020 intersections for the MAIN crosswalk.
-- The denominator remains the WHOLE 2010 tract's land area, including any
-- overlap outside WA. Boundary gaps therefore reduce coverage, not the denominator.
CREATE OR REPLACE TABLE crosswalk_parts AS
SELECT r.*, r.land_overlap_m2 / nullif(r.land_area_2010_m2, 0) AS land_weight,
       n.GEOID2020 IS NOT NULL AS matched_nri,
       n.* EXCLUDE (GEOID2020)
FROM tract_relationship r
LEFT JOIN nri n ON r.GEOID2020 = n.GEOID2020
WHERE starts_with(r.GEOID, '53') AND starts_with(r.GEOID2020, '53');

-- Sum(score * weight) / sum(valid weights). No population weights, no zero
-- fill, no averaging of ratings or dollar totals. A null score loses only its
-- own weight. Per-score coverage documents that loss separately from row coverage.
CREATE OR REPLACE TABLE nri_weighted AS
SELECT GEOID,
       CASE WHEN max(land_area_2010_m2) > 0
            THEN coalesce(sum(land_weight) FILTER (WHERE matched_nri), 0) END AS nri_area_coverage,
       sum(overall_risk_score * land_weight) / nullif(sum(land_weight) FILTER (WHERE overall_risk_score IS NOT NULL), 0) AS overall_risk_score,
       sum(drought_risk_score * land_weight) / nullif(sum(land_weight) FILTER (WHERE drought_risk_score IS NOT NULL), 0) AS drought_risk_score,
       sum(wildfire_risk_score * land_weight) / nullif(sum(land_weight) FILTER (WHERE wildfire_risk_score IS NOT NULL), 0) AS wildfire_risk_score,
       sum(heat_wave_risk_score * land_weight) / nullif(sum(land_weight) FILTER (WHERE heat_wave_risk_score IS NOT NULL), 0) AS heat_wave_risk_score,
       sum(coastal_flooding_risk_score * land_weight) / nullif(sum(land_weight) FILTER (WHERE coastal_flooding_risk_score IS NOT NULL), 0) AS coastal_flooding_risk_score,
       sum(inland_flooding_risk_score * land_weight) / nullif(sum(land_weight) FILTER (WHERE inland_flooding_risk_score IS NOT NULL), 0) AS inland_flooding_risk_score,
       coalesce(sum(land_weight) FILTER (WHERE overall_risk_score IS NOT NULL), 0) AS overall_risk_area_coverage,
       coalesce(sum(land_weight) FILTER (WHERE drought_risk_score IS NOT NULL), 0) AS drought_risk_area_coverage,
       coalesce(sum(land_weight) FILTER (WHERE wildfire_risk_score IS NOT NULL), 0) AS wildfire_risk_area_coverage,
       coalesce(sum(land_weight) FILTER (WHERE heat_wave_risk_score IS NOT NULL), 0) AS heat_wave_risk_area_coverage,
       coalesce(sum(land_weight) FILTER (WHERE coastal_flooding_risk_score IS NOT NULL), 0) AS coastal_flooding_risk_area_coverage,
       coalesce(sum(land_weight) FILTER (WHERE inland_flooding_risk_score IS NOT NULL), 0) AS inland_flooding_risk_area_coverage
FROM crosswalk_parts GROUP BY GEOID;

-- Strict check: one old tract overlaps exactly one new tract and that new tract
-- overlaps exactly one old tract. Count nationally, even tiny/water intersections.
CREATE OR REPLACE TABLE nri_strict AS
SELECT g.GEOID,
       w.nri_area_coverage,
       n.overall_risk_score, n.drought_risk_score, n.wildfire_risk_score,
       n.heat_wave_risk_score, n.coastal_flooding_risk_score, n.inland_flooding_risk_score,
       CASE WHEN n.overall_risk_score IS NOT NULL THEN w.overall_risk_area_coverage ELSE 0 END AS overall_risk_area_coverage,
       CASE WHEN n.drought_risk_score IS NOT NULL THEN w.drought_risk_area_coverage ELSE 0 END AS drought_risk_area_coverage,
       CASE WHEN n.wildfire_risk_score IS NOT NULL THEN w.wildfire_risk_area_coverage ELSE 0 END AS wildfire_risk_area_coverage,
       CASE WHEN n.heat_wave_risk_score IS NOT NULL THEN w.heat_wave_risk_area_coverage ELSE 0 END AS heat_wave_risk_area_coverage,
       CASE WHEN n.coastal_flooding_risk_score IS NOT NULL THEN w.coastal_flooding_risk_area_coverage ELSE 0 END AS coastal_flooding_risk_area_coverage,
       CASE WHEN n.inland_flooding_risk_score IS NOT NULL THEN w.inland_flooding_risk_area_coverage ELSE 0 END AS inland_flooding_risk_area_coverage
FROM geography_audit g
LEFT JOIN nri n ON g.GEOID2020 = n.GEOID2020 AND g.is_one_to_one
LEFT JOIN nri_weighted w ON g.GEOID = w.GEOID;
