# Data provenance

Official source URLs and download attempts below. UTC timestamps are exact; project date uses America/Los_Angeles. Full SHA-256 checksums and byte counts are in `download_log.json`. Raw files are ignored by Git. No Census API key is logged.

| Local file | Source URL | UTC time | Pacific date | Status |
|---|---|---|---|---|
| usaleep_wa.csv | https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/NVSS/USALEEP/CSV/WA_A.CSV | 2026-11-17T07:45:19.272047+00:00 | 2026-11-16 | ok |
| tract_relationship_wa.txt | https://www2.census.gov/geo/docs/maps-data/data/rel2020/tract/tab20_tract20_tract10_st53.txt | 2026-11-17T07:45:19.694719+00:00 | 2026-11-16 | ok |
| nri_item.json | https://www.arcgis.com/sharing/rest/content/items/9da4eeb936544335a6db0cd7a8448a51?f=json | 2026-11-17T07:45:19.801243+00:00 | 2026-11-16 | ok |
| nri_dictionary.csv | https://fema.maps.arcgis.com/sharing/rest/content/items/4b9db412e99542029b3c37c37ad714bb/data | 2026-11-17T07:45:19.921082+00:00 | 2026-11-16 | ok |
| nri_layer.json | https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/National_Risk_Index_Census_Tracts/FeatureServer/0?f=json | 2026-11-17T07:45:20.316515+00:00 | 2026-11-16 | ok |
| nri_wa_count.json | https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/National_Risk_Index_Census_Tracts/FeatureServer/0/query?where=STATEFIPS+%3D+%2753%27&returnCountOnly=true&f=json | 2026-11-17T07:45:20.578364+00:00 | 2026-11-16 | ok |
| nri_wa.json | https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/National_Risk_Index_Census_Tracts/FeatureServer/0/query?where=STATEFIPS+%3D+%2753%27&outFields=%2A&returnGeometry=false&orderByFields=TRACTFIPS&resultRecordCount=2000&f=json | 2026-11-17T07:45:20.936775+00:00 | 2026-11-16 | failed |
| acs_B19013_metadata.json | https://api.census.gov/data/2015/acs/acs5/groups/B19013.json | 2026-11-17T07:45:23.888447+00:00 | 2026-11-16 | ok |
| acs_B17001_metadata.json | https://api.census.gov/data/2015/acs/acs5/groups/B17001.json | 2026-11-17T07:45:23.993177+00:00 | 2026-11-16 | ok |
| acs_2015_wa.json | https://api.census.gov/data/2015/acs/acs5?get=NAME%2CB19013_001E%2CB17001_001E%2CB17001_002E&for=tract%3A%2A&in=state%3A53+county%3A%2A | 2026-11-17T07:45:24.108098+00:00 | 2026-11-16 | failed |
| nri_wa.json | https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/National_Risk_Index_Census_Tracts/FeatureServer/0/query?where=STATEFIPS+%3D+%2753%27&outFields=%2A&returnGeometry=false&orderByFields=TRACTFIPS&resultRecordCount=2000&f=json | 2026-11-17T08:12:38.756944+00:00 | 2026-11-17 | ok |
| nri_wa.csv | derived from data/raw/nri_wa.json (official FEMA query above) | 2026-11-17T08:12:41.939493+00:00 | 2026-11-17 | ok |
| tract_relationship_national.txt | https://www2.census.gov/geo/docs/maps-data/data/rel2020/tract/tab20_tract20_tract10_natl.txt | 2026-11-17T08:15:18.192600+00:00 | 2026-11-17 | ok |
| acs_2015_wa.json | https://api.census.gov/data/2015/acs/acs5?get=NAME%2CB19013_001E%2CB17001_001E%2CB17001_002E&for=tract%3A%2A&in=state%3A53+county%3A%2A | 2026-11-18T01:48:30.450489+00:00 | 2026-11-17 | ok |

NRI CSV is serialized from FEMA's official JSON attributes (all columns), filtered to WA. Raw service responses and metadata are retained. We use the current FEMA Inland Flooding field (IFLD), version 1.20.0.

Optional EHD and TIGER maps are deferred; see `../NOTES.md`.
