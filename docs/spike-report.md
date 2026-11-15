# Data spike report (data lane) — 2026-11-15

Branch `feat/26-data-spike`. Scripts: `data_pipeline/`, DDL: `sql/`. DB: `fieldshift` (Postgres+PostGIS+pgvector, 127.0.0.1:5433). Raw: `/srv/hackathon/data/raw/<dataset>/`.
No secrets in repo. No data files committed.

## Overall: see bottom line (updated at each dataset)

## Schema notes
- `sql/001_sot_schema.sql` = SOT §5 DDL verbatim except `vector(1536)` -> `vector(384)` (e5-small, per fieldshift-data brief). No DDL bug blocked us.
- `sql/002_spike_tables.sql` adds spike tables not in SOT §5 (proposal; need SOT PR if kept): `county`, `county_weather_daily`, `county_crop_share`, `county_smap`, `county_imerg_daily`, `county_yield`, `field_soil`, `field_crop_history`, `field_et_openet`, `field_ndvi_hls`, `spike_log`.
- County geometry: Census `cb_2023_us_county_500k` (public domain), 1,122 counties in the 12 states (`county`). "centroid" column = ST_PointOnSurface (always inside the county).

## Per item
### POWER daily (tier 1) — Go
- 1,122 counties x 1995-01-01..2025-12-31 = 12,704,406 rows in `county_weather_daily` (source_id=`power`), 1.4 GB in DB; raw gz JSON 373 MB at `raw/power/tier1_county/<fips>.json.gz`.
- Vars: T2M, T2M_MIN, T2M_MAX, PRECTOTCORR (mm/day), RH2M, WS2M, ALLSKY_SFC_SW_DWN (MJ/m2/day), community AG, one point per county (representative point). ET0 not requested -> NULL.
- Missing: 0 null in t2m/precip/rh; 47 null srad (0.0004 %). -999 -> NULL.
- Resolution (response header): sources MERRA2, SRB, SYN1DEG, POWER; "Source Native Resolution Daily Data" (MERRA-2 ~0.5x0.625 deg for met vars). API v2.10.3. Time standard LST.
- Timing: 627 s download (2 req/s limiter, 4 workers) + 67 s load. Licence: NASA open data; cite NASA POWER / LaRC.

### CDL tier 1 county shares 2008-2025 — Go
- National 30 m zips from `nass.usda.gov/sites/default/files/Research_and_Science/Cropland/Release/datasets/<yr>_30m_cdls.zip` (1.8-1.9 GB each; plain GET returns empty body, **HTTP Range works** -> `data_pipeline/rangedl.py`). Zonal pixel counts per county polygon (EPSG:5070, pixel centres in polygon, class 0 excluded).
- `county_crop_share`: 665,807 rows, 18 years (2008-2025) x 1,122 counties. Class names from official `.tif.vat.dbf` (2025/2012 etc. zips); 2023-2021 zips lacked the VAT in the extract so names were back-filled from other years' VAT by class code (9 rare classes remain NULL name).
- Sanity: Story 2025 corn 43.8 %, soy 28.9 %; 2012 corn 45.7 %, soy 28.3 %.
- Timing: ~85 s/year (download ~60 s + zonal ~15 s with 8 procs). National zips and extracted tifs were deleted after use (url in `raw/cdl/tier1_county/manifest_<yr>.json`). Licence: US gov work; cite USDA NASS CDL.

### CDL tier 2 Story 30 m 2008-2025 — Go
- `raw/cdl/tier2_story/cdl_<yr>_story_19169.tif` (18 files, 3.9 MB total, EPSG:5070, deflate). `field_crop_history` = 108,486 rows (6,027 fields x 18 yrs, majority class + share, from these clips).

### CSB Story County (field polygons) — Go (item 1 partly, item 2 Go)
- NationalCSB 2018-2025 rev23 (`CSB1825.gdb`, 3.76 GB zip, 15,973,095 national features; `raw/csb/national_tmp/*.zip`, extracted copy `raw/csb/ext` 5.4 GB). Official id column = **`CSBID`** (also `CSBYEARS, CSBACRES, CDL2018..CDL2025, STATEFIPS, CNTYFIPS`). `field_id = CSBID` as text.
- `fields`: 6,027 Story County fields (19169), 115,529 ha total, mean 19.2 ha. NOT ownership boundaries.
- Item 2 pin->field: `ST_Contains(geom, point)` on GiST = 0.27 ms (planning+exec), returns `field_id`+`area_ha` (e.g. -93.5077,42.1221 -> 191825001176283, 274.0 ha).
- Item 1 rotation stats (`data_pipeline/csb_rotation_stats.py`; strict corn/soy alternation 2018-2025, all 8 yrs): Story IA 19169: 6,027 fields, 1,716 strict alternation (28.5 %), 72.2 % all-corn/soy-years; McLean IL 17113: 8,643 fields, 49.2 % alternation, 80.2 % corn/soy; Champaign IL 17019: 8,537 fields, 44.8 %, 80.8 %. IL candidate loaded only as stats (polygons not in DB). Demo `field_id` x3 = see 12 demo fields below (all have 8 yrs of corn/soy).
- Timing: download 160 s, extract+load ~3 min.

### SSURGO (item 10) — Go
- Soil Data Access (`sdmdataaccess.sc.egov.usda.gov`, public): `mupolygon` WKT for IA169 (39,591 polygons, 107 MB JSON, `raw/ssurgo/tier2_story/mupoly_ia169.json`) + component/chorizon (surface horizon hzdept_r=0): `component_surface_ia169.csv`.
- `field_soil`: 6,027 fields (area-dominant mapunit; 86 mapunits). om_r (%, surface horizon, comppct-weighted), kffact, awc_r (cm/cm), drainagecl (dominant component). 6,017/6,027 have OM/K/AWC (10 NULL = mapunits without horizon data). Mean OM 5.6 %, K 0.27.
- Licence: NRCS/USDA public; cite SSURGO/SDA.

### OpenET (point ET) — partial
- API `openet-api.org/raster/timeseries/point`, Ensemble monthly ET (mm), reference gridMET, 12 random Story demo fields (25-80 ha, 8 yrs corn/soy, centroid points). `field_et_openet`: 1,440 rows (12 fields x 120 months, 2016-01..2025-12).
- **Limit:** ensemble/gridMET monthly is not available before 2016 (HTTP 406 "No collection ... covers start year 2013"; 2008 combo also rejected) -> no 2012-drought ET. Fallback: POWER 2012 weather + CDL/NASS.
- Raw JSON in `raw/openet/tier2_story/`. Licence: OpenET terms; cite OpenET (Melton et al. 2022) — check API terms before publishing derived data.
