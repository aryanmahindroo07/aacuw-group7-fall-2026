"""Download official inputs, preserve provenance, and fail on unexpected responses.

Run from any directory: python src/download.py [--refresh] [--only nri ...]
Never store an API key in a file or print a request URL containing one.
"""
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
LOG = ROOT / "data/download_log.json"
SERVICE = ("https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/"
           "National_Risk_Index_Census_Tracts/FeatureServer/0")
ITEM = "https://www.arcgis.com/sharing/rest/content/items/9da4eeb936544335a6db0cd7a8448a51"
DICTIONARY = "https://fema.maps.arcgis.com/sharing/rest/content/items/4b9db412e99542029b3c37c37ad714bb/data"
ACS = "https://api.census.gov/data/2015/acs/acs5"
NRI_FIELDS = ["TRACTFIPS", "STATEFIPS", "NRI_VER", "RISK_SCORE", "RISK_RATNG", "EAL_VALT"]
for hazard in ["DRGT", "WFIR", "HWAV", "CFLD", "IFLD"]:
    NRI_FIELDS += [hazard + "_RISKS", hazard + "_RISKR"]


def require_columns(frame, columns, source):
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{source}: missing columns {missing}; stop and inspect NOTES.md")


class Downloader:
    def __init__(self, refresh=False):
        self.refresh = refresh
        self.log = json.loads(LOG.read_text()) if LOG.exists() else []
        RAW.mkdir(parents=True, exist_ok=True)

    def record(self, entry):
        self.log.append(entry)
        LOG.write_text(json.dumps(self.log, indent=2) + "\n")
        lines = ["# Data provenance", "", "Official source URLs and download attempts below. "
                 "UTC timestamps are exact; project date uses America/Los_Angeles. "
                 "Full SHA-256 checksums and byte counts are in `download_log.json`. "
                 "Raw files are ignored by Git. No Census API key is logged.", "",
                 "| Local file | Source URL | UTC time | Pacific date | Status |",
                 "|---|---|---|---|---|"]
        for row in self.log:
            lines.append(f"| {row['file']} | {row['url']} | {row['timestamp_utc']} | "
                         f"{row['download_date_pacific']} | {row['status']} |")
        lines += ["", "NRI CSV is serialized from FEMA's official JSON attributes (all columns), "
                  "filtered to WA. Raw service responses and metadata are retained. "
                  "Version 1.20.0 uses Inland Flooding (IFLD), approved by the user.", "",
                  "Optional EHD and TIGER maps are deferred; see `../NOTES.md`."]
        (ROOT / "data/README.md").write_text("\n".join(lines) + "\n")

    def fetch(self, filename, url, validator, params=None):
        path = RAW / filename
        # A cache hit requires successful provenance AND an unchanged checksum.
        previous = next((x for x in reversed(self.log)
                         if x['file'] == filename and x['status'] == 'ok'), None)
        if not self.refresh and path.exists() and previous:
            if hashlib.sha256(path.read_bytes()).hexdigest() == previous['sha256']:
                validator(path.read_bytes())
                print(f"Cached: {filename}")
                return path
        public_params = {k: v for k, v in (params or {}).items() if k != 'key'}
        public_url = requests.Request('GET', url, params=public_params).prepare().url
        now = datetime.now(timezone.utc)
        entry = dict(file=filename, url=public_url, timestamp_utc=now.isoformat(),
                     download_date_pacific=now.astimezone(ZoneInfo('America/Los_Angeles')).date().isoformat())
        try:
            response = requests.get(url, params=params, timeout=(15, 90))
            if response.status_code != 200:
                raise ValueError(f"HTTP {response.status_code}")
            content = response.content
            validator(content)
            temp = path.with_suffix(path.suffix + '.part')
            temp.write_bytes(content)
            temp.replace(path)
            entry.update(status='ok', bytes=len(content), sha256=hashlib.sha256(content).hexdigest())
            self.record(entry)
            print(f"Downloaded: {filename} ({len(content):,} bytes)")
            return path
        except Exception as exc:
            # requests exceptions can contain the secret URL. Only retain safe validation text.
            detail = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
            if params and params.get('key'):
                detail = detail.replace(params['key'], '[REDACTED]')
            entry.update(status='failed', error=detail)
            self.record(entry)
            raise ValueError(f"{filename}: {detail}") from None


def csv_validator(columns):
    def validate(content):
        frame = pd.read_csv(StringIO(content.decode('utf-8-sig')), dtype=str)
        require_columns(frame, columns, 'CSV')
        if frame.empty:
            raise ValueError('Empty CSV')
    return validate


def json_object(content):
    try:
        obj = json.loads(content)
    except (ValueError, UnicodeDecodeError):
        raise ValueError('Expected JSON, received HTML or invalid JSON (Census may require CENSUS_API_KEY)')
    if not isinstance(obj, dict) or 'error' in obj:
        raise ValueError('Expected a JSON object without an API error')
    return obj


def usaleep(d):
    d.fetch('usaleep_wa.csv', 'https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/NVSS/USALEEP/CSV/WA_A.CSV',
            csv_validator(['Tract ID', 'e(0)', 'se(e(0))', 'Abridged life table flag']))


def relationship(d):
    def validate(content):
        frame = pd.read_csv(StringIO(content.decode('utf-8-sig')), sep='|', dtype=str)
        require_columns(frame, ['GEOID_TRACT_10', 'GEOID_TRACT_20', 'AREALAND_PART', 'AREAWATER_PART'], 'Census relationship')
        if frame.empty:
            raise ValueError('Empty relationship file')
    d.fetch('tract_relationship_wa.txt', 'https://www2.census.gov/geo/docs/maps-data/data/rel2020/tract/tab20_tract20_tract10_st53.txt', validate)
    # National file also captures WA 2010 tracts intersecting 2020 tracts outside WA.
    d.fetch('tract_relationship_national.txt', 'https://www2.census.gov/geo/docs/maps-data/data/rel2020/tract/tab20_tract20_tract10_natl.txt', validate)


def nri(d):
    def item_check(content):
        item = json_object(content)
        if item.get('owner') != 'FEMA_NationalRiskIndex' or '1.20.0' not in item.get('description', ''):
            raise ValueError('Unexpected NRI owner/version; inspect official metadata')
    d.fetch('nri_item.json', ITEM, item_check, {'f': 'json'})
    def dictionary_check(content):
        csv_validator(['Field Name', 'Field Alias', 'Version'])(content)
        frame = pd.read_csv(StringIO(content.decode('utf-8-sig')))
        if not set(NRI_FIELDS).issubset(set(frame['Field Name'])):
            raise ValueError('NRI dictionary lacks selected fields')
        if set(frame['Version'].dropna()) != {'1.20.0'}:
            raise ValueError('Unexpected dictionary version')
    d.fetch('nri_dictionary.csv', DICTIONARY, dictionary_check)
    def layer_check(content):
        obj = json_object(content)
        if not set(NRI_FIELDS).issubset({x['name'] for x in obj.get('fields', [])}):
            raise ValueError('NRI service fields differ from the verified dictionary')
    d.fetch('nri_layer.json', SERVICE, layer_check, {'f': 'json'})
    count_path = d.fetch('nri_wa_count.json', SERVICE + '/query', json_object,
                         {'where': "STATEFIPS = '53'", 'returnCountOnly': 'true', 'f': 'json'})
    expected = json.loads(count_path.read_text())['count']
    def records_check(content):
        obj = json_object(content)
        features = obj.get('features', [])
        if obj.get('exceededTransferLimit') or len(features) != expected or expected == 0:
            raise ValueError('NRI response is incomplete; stop rather than accepting truncated data')
        frame = pd.DataFrame([f['attributes'] for f in features])
        require_columns(frame, NRI_FIELDS, 'NRI records')
        if not frame['STATEFIPS'].astype(str).eq('53').all():
            raise ValueError('NRI returned records outside WA')
        # The actual row field contains a release date, not the semantic version.
        if not frame['NRI_VER'].astype(str).eq('December 2025').all():
            raise ValueError('Unexpected NRI row version')
    path = d.fetch('nri_wa.json', SERVICE + '/query', records_check,
                   {'where': "STATEFIPS = '53'", 'outFields': '*', 'returnGeometry': 'false',
                    'orderByFields': 'TRACTFIPS', 'resultRecordCount': 2000, 'f': 'json'})
    frame = pd.DataFrame([f['attributes'] for f in json.loads(path.read_text())['features']])
    target = RAW / 'nri_wa.csv'
    frame.to_csv(target, index=False)
    now = datetime.now(timezone.utc)
    d.record(dict(file='nri_wa.csv', url='derived from data/raw/nri_wa.json (official FEMA query above)',
                  timestamp_utc=now.isoformat(), download_date_pacific=now.astimezone(ZoneInfo('America/Los_Angeles')).date().isoformat(),
                  status='ok', bytes=target.stat().st_size, sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
    print(f"NRI Washington: {len(frame):,} rows; version {frame['NRI_VER'].unique().tolist()}")


def acs(d):
    # Preserve official variable labels so the poverty denominator can be reviewed.
    for group in ['B19013', 'B17001']:
        def metadata_check(content):
            obj = json_object(content)
            if group + '_001E' not in obj.get('variables', {}):
                raise ValueError('ACS variable metadata does not contain expected estimate')
        d.fetch(f'acs_{group}_metadata.json', ACS + f'/groups/{group}.json', metadata_check)
    params = {'get': 'NAME,B19013_001E,B17001_001E,B17001_002E', 'for': 'tract:*', 'in': 'state:53 county:*'}
    key = os.environ.get('CENSUS_API_KEY')
    if key:
        params['key'] = key
    def validate(content):
        try:
            obj = json.loads(content)
        except ValueError:
            raise ValueError('Census returned non-JSON (Missing Key). Set CENSUS_API_KEY locally; do not commit it.')
        if not isinstance(obj, list) or len(obj) < 2:
            raise ValueError('Census response is not a populated table')
        require_columns(pd.DataFrame(obj[1:], columns=obj[0]),
                        ['NAME', 'B19013_001E', 'B17001_001E', 'B17001_002E', 'state', 'county', 'tract'], 'ACS')
    d.fetch('acs_2015_wa.json', ACS, validate, params)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--only', nargs='+', choices=['usaleep', 'relationship', 'nri', 'acs'])
    args = parser.parse_args()
    d = Downloader(args.refresh)
    failures = []
    for name in args.only or ['usaleep', 'relationship', 'nri', 'acs']:
        try:
            globals()[name](d)
        except Exception as exc:
            message = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
            print(f'BLOCKED {name}: {message}')
            failures.append(f'- {name}: {message}')
    if failures:
        with (ROOT / 'NOTES.md').open('a') as handle:
            handle.write('\n## Download blockers — ' + datetime.now(timezone.utc).isoformat() + '\n\n' + '\n'.join(failures) + '\n')
        raise SystemExit(1)


if __name__ == '__main__':
    main()
