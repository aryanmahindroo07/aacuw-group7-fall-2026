"""Validate real source schemas, execute DuckDB SQL, audit exclusions, export.

python src/clean.py --audit-only works with just USALEEP + relationship data.
No final table is emitted until all required inputs pass validation.
"""
import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, CLEAN = ROOT / 'data/raw', ROOT / 'data/clean'
HAZARDS = ['drought', 'wildfire', 'heat_wave', 'coastal_flooding', 'inland_flooding']


def require(frame, columns, source):
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f'{source}: missing columns {missing}; no schema substitution allowed')


def read_csv(name, sep=','):
    path = RAW / name
    if not path.exists():
        raise ValueError(f'Missing required source: {name}; run src/download.py')
    return pd.read_csv(path, sep=sep, dtype=str, encoding='utf-8-sig')


def check_ids(series, width, source, unique=False):
    # Reject decimals, scientific notation, empty IDs, or overlong values BEFORE padding.
    if series.isna().any() or not series.str.fullmatch(r'\d{1,' + str(width) + '}').all():
        raise ValueError(f'{source}: malformed geographic ID')
    padded = series.str.zfill(width)
    if unique and padded.duplicated().any():
        raise ValueError(f'{source}: duplicate geographic ID')
    return padded


def check_numeric(frame, columns, source):
    for column in columns:
        values = pd.to_numeric(frame[column], errors='coerce')
        if (frame[column].notna() & values.isna()).any():
            raise ValueError(f'{source}: unexpected nonnumeric {column}')
        if values.isin([float('inf'), float('-inf')]).any():
            raise ValueError(f'{source}: infinite {column}')


def sql(con, filename):
    con.execute((ROOT / 'sql' / filename).read_text())


def geography(con):
    u = read_csv('usaleep_wa.csv')
    r = read_csv('tract_relationship_national.txt', '|')
    require(u, ['Tract ID', 'e(0)', 'se(e(0))', 'Abridged life table flag'], 'USALEEP')
    require(r, ['GEOID_TRACT_10', 'GEOID_TRACT_20', 'AREALAND_TRACT_10', 'AREALAND_PART', 'AREAWATER_PART'], 'Relationship')
    u['Tract ID'] = check_ids(u['Tract ID'], 11, 'USALEEP', unique=True)
    for col in ['GEOID_TRACT_10', 'GEOID_TRACT_20']:
        r[col] = check_ids(r[col], 11, 'Relationship')
    if not u['Tract ID'].str.startswith('53').all():
        raise ValueError('USALEEP contains non-WA tracts')
    if not set(u['Tract ID']).issubset(set(r.GEOID_TRACT_10)):
        raise ValueError('USALEEP has IDs absent from the 2010 relationship universe')
    check_numeric(u, ['e(0)', 'se(e(0))'], 'USALEEP')
    life = pd.to_numeric(u['e(0)'])
    if ((life.dropna() <= 0) | (life.dropna() > 120)).any():
        raise ValueError('Unexpected life expectancy range')
    check_numeric(r, ['AREALAND_TRACT_10', 'AREALAND_PART', 'AREAWATER_PART'], 'Relationship')
    # Verify the denominator and complete partitions nationally, before WA filtering.
    land = r[['GEOID_TRACT_10', 'AREALAND_TRACT_10', 'AREALAND_PART']].copy()
    for col in ['AREALAND_TRACT_10', 'AREALAND_PART']:
        land[col] = pd.to_numeric(land[col])
        if land[col].isna().any() or (land[col] < 0).any():
            raise ValueError('Missing or negative relationship land area')
    if land.groupby('GEOID_TRACT_10').AREALAND_TRACT_10.nunique().max() != 1:
        raise ValueError('Inconsistent 2010 tract land-area denominator')
    totals = land.groupby('GEOID_TRACT_10').agg(total=('AREALAND_TRACT_10', 'first'), parts=('AREALAND_PART', 'sum'))
    if (totals.total - totals.parts).abs().max() != 0:
        raise ValueError('Relationship land intersections do not sum to full tract areas')
    con.register('usaleep_input', u)
    con.register('relationship_input', r)
    sql(con, '01_geography.sql')
    audit = con.table('geography_audit').df()
    counts = dict(national_relationship_rows=len(r),
                  wa_2020_relationship_rows=int(r.GEOID_TRACT_20.str.startswith('53').sum()),
                  census_2010_tracts=r.loc[r.GEOID_TRACT_10.str.startswith('53'), 'GEOID_TRACT_10'].nunique(),
                  census_2020_tracts=r.loc[r.GEOID_TRACT_20.str.startswith('53'), 'GEOID_TRACT_20'].nunique(), usaleep_rows=len(u),
                  usaleep_missing_estimates=int(life.isna().sum()),
                  missing_usaleep_records=int(audit.missing_usaleep_record.sum()),
                  one_to_one_pairs=int(audit.is_one_to_one.sum()),
                  excluded_by_strict_mapping=int((~audit.is_one_to_one).sum()),
                  one_to_one_with_life_expectancy=int((audit.is_one_to_one & ~audit.missing_life_expectancy).sum()))
    # Wide sanity bounds detect wrong state/geography without pretending approximations are exact.
    if not 1400 <= counts['census_2010_tracts'] <= 1550 or not 1700 <= counts['census_2020_tracts'] <= 1850:
        raise ValueError('WA tract counts are outside expected ranges; inspect before continuing')
    counts['usaleep_match_rate_2010'] = len(u) / counts['census_2010_tracts']
    counts['one_to_one_rate_2010'] = counts['one_to_one_pairs'] / counts['census_2010_tracts']
    audit.to_csv(CLEAN / 'geography_audit.csv', index=False)
    (CLEAN / 'geography_audit.json').write_text(json.dumps(counts, indent=2) + '\n')
    print(json.dumps(counts, indent=2))
    return counts


def full_sources(con):
    path = RAW / 'acs_2015_wa.json'
    if not path.exists():
        raise ValueError('ACS is unavailable. Set CENSUS_API_KEY locally and run src/download.py --only acs')
    obj = json.loads(path.read_text())
    if not isinstance(obj, list) or len(obj) < 2:
        raise ValueError('ACS response is not a populated table')
    a = pd.DataFrame(obj[1:], columns=obj[0])
    required = ['NAME', 'state', 'county', 'tract', 'B19013_001E', 'B17001_001E', 'B17001_002E']
    require(a, required, 'ACS')
    for col, width in [('state', 2), ('county', 3), ('tract', 6)]:
        a[col] = check_ids(a[col], width, 'ACS')
    if not a.state.eq('53').all():
        raise ValueError('ACS includes non-WA records')
    check_ids(a.state + a.county + a.tract, 11, 'ACS', unique=True)
    check_numeric(a, ['B19013_001E', 'B17001_001E', 'B17001_002E'], 'ACS')
    universe = pd.to_numeric(a.B17001_001E)
    poor = pd.to_numeric(a.B17001_002E)
    if ((universe >= 0) & (poor > universe)).any():
        raise ValueError('ACS poverty numerator exceeds its universe')
    # Verify definitions from the downloaded official metadata, not only column names.
    meta = json.loads((RAW / 'acs_B17001_metadata.json').read_text())['variables']
    if meta['B17001_001E']['label'] != 'Estimate!!Total' or meta['B17001_002E']['label'] != 'Estimate!!Total!!Income in the past 12 months below poverty level':
        raise ValueError('Unexpected B17001 definitions; stop and review')
    con.register('acs_input', a)
    sql(con, '02_acs.sql')
    nri_rows = nri_source(con)
    sql(con, '03_crosswalk.sql')
    sql(con, '04_join.sql')
    old = set(con.table('geography_audit').df().GEOID)
    if not set(a.state + a.county + a.tract).issubset(old) or len(a) != len(old):
        raise ValueError('ACS coverage differs from full WA 2010 universe; inspect before joining')
    return len(a), nri_rows


def nri_source(con):
    """NRI can be validated and audited independently while ACS is blocked."""
    n = read_csv('nri_wa.csv')
    dictionary = read_csv('nri_dictionary.csv')
    fields = ['TRACTFIPS', 'STATEFIPS', 'NRI_VER', 'RISK_SCORE', 'RISK_RATNG', 'EAL_VALT']
    for code in ['DRGT', 'WFIR', 'HWAV', 'CFLD', 'IFLD']:
        fields += [code + '_RISKS', code + '_RISKR']
    require(n, fields, 'NRI')
    if not set(fields).issubset(set(dictionary['Field Name'])) or set(dictionary.Version.dropna()) != {'1.20.0'}:
        raise ValueError('NRI dictionary does not match verified v1.20 schema')
    if not n.NRI_VER.eq('December 2025').all() or not n.STATEFIPS.eq('53').all():
        raise ValueError('Unexpected NRI state or release')
    n.TRACTFIPS = check_ids(n.TRACTFIPS, 11, 'NRI', unique=True)
    score_fields = [c for c in fields if c.endswith('_RISKS')] + ['RISK_SCORE']
    check_numeric(n, score_fields + ['EAL_VALT'], 'NRI')
    for col in score_fields:
        values = pd.to_numeric(n[col]).dropna()
        if ((values < 0) | (values > 100)).any():
            raise ValueError(f'NRI {col} outside 0–100; do not guess sentinel meanings')
    if (pd.to_numeric(n.EAL_VALT).dropna() < 0).any():
        raise ValueError('NRI has negative expected loss')
    con.register('nri_input', n)
    sql(con, '02_nri.sql')
    geography_frame = con.table('tract_relationship').df()
    new = set(geography_frame.loc[geography_frame.GEOID2020.str.startswith('53'), 'GEOID2020'])
    if not set(n.TRACTFIPS).issubset(new):
        raise ValueError('NRI includes tracts outside the verified WA 2020 geography')
    if len(n) != json.loads((RAW / 'nri_wa_count.json').read_text())['count']:
        raise ValueError('NRI CSV row count differs from official count response')
    matches = con.execute('''SELECT count(*) FROM geography_audit g JOIN nri n
                           ON g.GEOID2020 = n.GEOID2020 WHERE g.is_one_to_one''').fetchone()[0]
    with_life = con.execute('''SELECT count(*) FROM geography_audit g JOIN nri n
                             ON g.GEOID2020 = n.GEOID2020
                             WHERE g.is_one_to_one AND NOT g.missing_life_expectancy''').fetchone()[0]
    report = dict(nri_rows=len(n), census_2020_tracts=len(new),
                  census_2020_tracts_missing_nri=len(new - set(n.TRACTFIPS)),
                  nri_match_rate_2020=len(n) / len(new),
                  one_to_one_nri_matches=matches,
                  one_to_one_with_life_and_nri=with_life,
                  null_counts={c: int(n[c].isna().sum()) for c in score_fields + ['EAL_VALT']})
    (CLEAN / 'nri_audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return len(n)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit-only', action='store_true')
    parser.add_argument('--min-nri-coverage', type=float, default=0.95,
                        help='Required fraction of 2010 land covered by NRI (default: 0.95)')
    args = parser.parse_args()
    if not 0 <= args.min_nri_coverage <= 1:
        parser.error('--min-nri-coverage must be between 0 and 1')
    CLEAN.mkdir(parents=True, exist_ok=True)
    # Work in memory: failure cannot leave a half-built final database.
    con = duckdb.connect()
    con.execute('CREATE TABLE analysis_config AS SELECT ?::DOUBLE AS min_nri_coverage', [args.min_nri_coverage])
    try:
        counts = geography(con)
        if args.audit_only:
            if (RAW / 'nri_wa.csv').exists():
                nri_source(con)
            return
        counts['acs_rows'], counts['nri_rows'] = full_sources(con)
        frame = con.execute('SELECT * FROM tract_analysis ORDER BY sample, GEOID').df()
        if frame.empty or frame.duplicated(['sample', 'GEOID']).any():
            raise ValueError('Final table is empty or contains duplicate (sample, GEOID) pairs')
        if frame.groupby('sample').size().to_dict() != {'area_weighted': 1458, 'strict_1to1': 1458}:
            raise ValueError('Final table did not retain every WA 2010 tract in both versions')
        audit = frame[frame['sample'].eq('area_weighted')]
        if audit.nri_area_coverage.dropna().lt(0).any() or audit.nri_area_coverage.dropna().gt(1 + 1e-12).any():
            raise ValueError('Area coverage outside 0–1')
        exclusions = con.execute('SELECT * FROM exclusion_counts ORDER BY sample, analysis_status').df().to_dict('records')
        selected = frame[frame.included_in_analysis]
        if selected.empty:
            raise ValueError('No tracts pass the analysis filter')
        counts.update(export_rows=len(frame), min_nri_coverage=args.min_nri_coverage,
                      included_by_sample=selected.groupby('sample').size().to_dict(), exclusions=exclusions,
                      acs_join_matches=int((~audit.missing_acs_record).sum()),
                      missingness_flags={c: int(audit[c].sum()) for c in audit if c.startswith('missing_')})
        counts['acs_match_rate_2010'] = counts['acs_join_matches'] / counts['census_2010_tracts']
        counts['main_sequential_counts'] = dict(
            all_2010_tracts=len(audit),
            with_life_expectancy=int((~audit.missing_life_expectancy).sum()),
            also_with_income=int((~audit.missing_life_expectancy & ~audit.missing_income).sum()),
            also_with_nri_coverage=int((~audit.missing_life_expectancy & ~audit.missing_income & audit.nri_area_coverage.ge(args.min_nri_coverage)).sum()),
            included=int(audit.included_in_analysis.sum()))
        tables = ['tract_relationship', 'tract_mapping', 'life_expectancy', 'geography_audit', 'acs', 'nri',
                  'crosswalk_parts', 'nri_weighted', 'nri_strict', 'analysis_config',
                  'tract_audit', 'tract_analysis', 'exclusion_counts']
        # Stage database files, then replace prior successful exports.
        db_temp = CLEAN / 'project.duckdb.part'
        out = duckdb.connect(str(db_temp))
        for table in tables:
            table_frame = con.table(table).df()
            out.register('export_input', table_frame)
            out.execute(f'CREATE OR REPLACE TABLE {table} AS SELECT * FROM export_input')
        out.close()
        sqlite_temp = CLEAN / 'project.sqlite.part'
        with sqlite3.connect(sqlite_temp) as db:
            frame.to_sql('tract_analysis', db, if_exists='replace', index=False,
                         dtype={'GEOID': 'TEXT', 'GEOID2020': 'TEXT'})
            db.execute('DROP INDEX IF EXISTS tract_analysis_key')
            db.execute('CREATE UNIQUE INDEX tract_analysis_key ON tract_analysis(sample, GEOID)')
            assert db.execute('SELECT COUNT(*) FROM tract_analysis').fetchone()[0] == len(frame)
        db_temp.replace(CLEAN / 'project.duckdb')
        sqlite_temp.replace(CLEAN / 'project.sqlite')
        frame.to_csv(CLEAN / 'tract_analysis.csv', index=False)
        audit.to_csv(CLEAN / 'tract_audit.csv', index=False)
        (CLEAN / 'pipeline_audit.json').write_text(json.dumps(counts, indent=2) + '\n')
        print(json.dumps(counts, indent=2))
    except Exception as exc:
        message = str(exc)
        with (ROOT / 'NOTES.md').open('a') as handle:
            handle.write(f'\n## Cleaning blocked — {datetime.now(timezone.utc).isoformat()}\n\n{message}\n')
        raise SystemExit('BLOCKED: ' + message) from None
    finally:
        con.close()


if __name__ == '__main__':
    main()
