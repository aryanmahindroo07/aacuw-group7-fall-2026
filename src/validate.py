"""Check real-data crosswalk calculations, exports, pair counts and OLS results.

Run after cleaning and first-look: python src/validate.py
This uses the downloaded data, never generated observations.
"""
import json
import math
import sqlite3
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, CLEAN = ROOT / 'data/raw', ROOT / 'data/clean'
SCORES = {'overall': 'RISK_SCORE', 'drought': 'DRGT_RISKS', 'wildfire': 'WFIR_RISKS',
          'heat_wave': 'HWAV_RISKS', 'coastal_flooding': 'CFLD_RISKS', 'inland_flooding': 'IFLD_RISKS'}


def main():
    with duckdb.connect(str(CLEAN / 'project.duckdb'), read_only=True) as con:
        frame = con.execute('SELECT * FROM tract_analysis ORDER BY sample, GEOID').df()
        weighted = con.table('nri_weighted').df().set_index('GEOID').sort_index()
    assert len(frame) == 2916 and not frame.duplicated(['sample', 'GEOID']).any()
    assert frame.GEOID.str.fullmatch(r'53\d{9}').all()
    assert 'expected_annual_loss' not in frame, 'Dollar totals must not be crosswalked as scores'

    # Independent pandas calculation starts from the raw Census and FEMA inputs.
    r = pd.read_csv(RAW / 'tract_relationship_national.txt', sep='|',
                    dtype={'GEOID_TRACT_10': str, 'GEOID_TRACT_20': str})
    r = r[r.GEOID_TRACT_10.str.startswith('53') & r.GEOID_TRACT_20.str.startswith('53')]
    n = pd.read_csv(RAW / 'nri_wa.csv', dtype={'TRACTFIPS': str})
    parts = r.merge(n, left_on='GEOID_TRACT_20', right_on='TRACTFIPS', how='left', validate='many_to_one')
    total = parts.groupby('GEOID_TRACT_10').AREALAND_TRACT_10.first().replace(0, np.nan)
    matched_area = parts.AREALAND_PART.where(parts.TRACTFIPS.notna(), 0).groupby(parts.GEOID_TRACT_10).sum()
    coverage = (matched_area / total).reindex(weighted.index)
    np.testing.assert_allclose(weighted.nri_area_coverage, coverage, atol=1e-12, equal_nan=True)
    for name, raw_score in SCORES.items():
        rating = 'RISK_RATNG' if name == 'overall' else raw_score.replace('_RISKS', '_RISKR')
        score = parts[raw_score].where(~parts[rating].isin(['Not Applicable', 'Insufficient Data']))
        area = parts.AREALAND_PART.where(score.notna(), 0)
        numerator = (score * parts.AREALAND_PART).groupby(parts.GEOID_TRACT_10).sum(min_count=1)
        denominator = area.groupby(parts.GEOID_TRACT_10).sum().replace(0, np.nan)
        expected = (numerator / denominator).reindex(weighted.index)
        np.testing.assert_allclose(weighted[name + '_risk_score'], expected, atol=1e-10, equal_nan=True)
    strict = frame[frame['sample'].eq('strict_1to1') & frame.included_in_analysis]
    direct = strict[['GEOID2020']].merge(n, left_on='GEOID2020', right_on='TRACTFIPS', validate='one_to_one')
    for name, raw_score in SCORES.items():
        rating = 'RISK_RATNG' if name == 'overall' else raw_score.replace('_RISKS', '_RISKR')
        expected = direct[raw_score].where(~direct[rating].isin(['Not Applicable', 'Insufficient Data']))
        np.testing.assert_allclose(strict[name + '_risk_score'], expected, atol=1e-10, equal_nan=True)

    # CSV must be read with string GEOIDs; SQLite stores them as TEXT.
    text_columns = frame.select_dtypes(include='object').columns
    csv = pd.read_csv(CLEAN / 'tract_analysis.csv', dtype={col: str for col in text_columns})
    with sqlite3.connect(CLEAN / 'project.sqlite') as db:
        sqlite_frame = pd.read_sql_query('SELECT * FROM tract_analysis ORDER BY sample, GEOID', db)
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    for exported in [csv, sqlite_frame]:
        for col in frame.columns:
            if pd.api.types.is_bool_dtype(frame[col]):
                exported[col] = exported[col].astype(bool)
        # Normalize equivalent None/NaN text nulls and preserve string flags/IDs.
        for col in text_columns:
            frame[col] = frame[col].astype('string')
            exported[col] = exported[col].astype('string')
        pd.testing.assert_frame_equal(frame, exported, check_dtype=False, atol=1e-10, rtol=1e-12)

    models = pd.read_csv(ROOT / 'charts/income_adjusted_associations.csv')
    # Scalar, centered residual formula independently checks both OLS fits.
    for label, group in frame[frame.included_in_analysis].groupby('sample'):
        x = group.overall_risk_score.to_list()
        y = group.life_expectancy.to_list()
        z = [math.log(v) for v in group.median_household_income]
        def centered(values):
            mean = math.fsum(values) / len(values)
            return [v - mean for v in values]
        x, y, z = centered(x), centered(y), centered(z)
        zz = math.fsum(v*v for v in z)
        xz = math.fsum(a*b for a, b in zip(x, z)) / zz
        yz = math.fsum(a*b for a, b in zip(y, z)) / zz
        xr = [a - xz*b for a, b in zip(x, z)]
        yr = [a - yz*b for a, b in zip(y, z)]
        before = 10 * math.fsum(a*b for a, b in zip(x, y)) / math.fsum(v*v for v in x)
        after = 10 * math.fsum(a*b for a, b in zip(xr, yr)) / math.fsum(v*v for v in xr)
        row = models[models['sample'].eq(label) & models.risk.eq('overall_risk_score')].iloc[0]
        assert row.n == len(group)
        assert math.isclose(row.years_per_10_risk_points_unadjusted, before, abs_tol=1e-10)
        assert math.isclose(row.years_per_10_risk_points_log_income_adjusted, after, abs_tol=1e-10)

    counts = pd.read_csv(ROOT / 'charts/correlation_pair_counts.csv', index_col=0)
    main_sample = frame[frame['sample'].eq('area_weighted') & frame.included_in_analysis]
    values = main_sample[counts.columns].copy()
    for name in SCORES:
        score = name + '_risk_score'
        values.loc[~main_sample[name + '_risk_area_coverage'].ge(main_sample.min_nri_coverage), score] = np.nan
    expected_counts = values.notna().astype(int).T @ values.notna().astype(int)
    pd.testing.assert_frame_equal(counts, expected_counts, check_names=False)
    report = dict(status='passed', crosswalk='independent pandas from raw inputs',
                  export_rows=len(frame), unique_2010_tracts=frame.GEOID.nunique(),
                  checks=['six weighted scores and matched-area coverage', 'strict scores equal original FEMA scores', 'CSV and SQLite round trips',
                          'SQLite integrity', 'both overall-risk OLS fits in both samples', 'correlation pair counts'])
    (CLEAN / 'validation_report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        with (ROOT / 'NOTES.md').open('a') as handle:
            handle.write(f'\n## Validation failed\n\n{type(exc).__name__}: {exc}\n')
        raise
