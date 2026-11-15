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

### NASS QuickStats bulk (item 11, optional) — Go
- `https://sb.nass.usda.gov/datasets/qs.crops_20261103.txt.gz` (1,132,568,713 B). Plain GET/HTTP2 broken (stream errors); Range download works. File contains NUL bytes -> stripped on read (`data_pipeline/nass_bulk_yield.py`).
- Filter: SURVEY, COUNTY, ANNUAL, DOMAIN TOTAL, `CORN, GRAIN - YIELD, MEASURED IN BU / ACRE` and `SOYBEANS - YIELD ...`, 12 states, 2008-2025, suppressed values `(D)` not loaded (absent = NULL).
- `county_yield`: 30,183 rows, 1,071 counties, 2008-2025 (15,545 corn rows). Story 2012: corn 157.6, soy 48.9 bu/ac (vs 2013 137.2 / 40.4 — 2012 shows no collapse in Story; keep in mind for backtest framing).
- Licence/cite: USDA NASS Quick Stats (bulk file, no API -> API disclaimer not needed).

### HLS L30/S30 NDVI (item 4) — Go
- `earthaccess` (netrc) search + HTTPS COG window reads (no files stored). 12 demo fields (same as OpenET), Apr 1-Nov 30, 2023/2024/2025, cloud_cover<=70 %. NDVI = (NIR-Red)/(NIR+Red), L30 B05/B04, S30 B8A/B04, scale 1e-4, Fmask bits 1-5 (cloud, adjacent, shadow, snow, water) masked, mean over field polygon pixels, `valid_frac` kept.
- `field_ndvi_hls`: 3,024 rows (HLSL30 1,116 + HLSS30 1,908 scene-field rows). Scenes with valid_frac>=0.8: 36-68 per field-year (median 52) >> 8 required.
- Sample field 191825002945908, 2023: NDVI 0.25 (Apr) -> 0.86 (Jun 23) -> 0.91 (Jul 10) -> 0.35 (Oct 7) -> 0.21 (Oct 30): bare -> emergence -> peak -> harvest visible. Monthly mean over all fields Apr 0.23, Jul 0.83, Aug 0.89, Oct 0.30.
- A few granule reads raised transient `RasterioIOError` (skipped, logged); scale 1e-4 reflectance, no BRDF/other QA beyond Fmask. Timing ~4 min/year with 6 threads. Licence: NASA LP DAAC HLS v2.0, cite DOI 10.5067/HLS/HLSL30.002 / S30.002 (verify DOIs before submission).

### SMAP L3 (item 5a) — Go (context only)
- `SPL3SMP` v009 (36 km EASE-Grid 2.0, NSIDC via earthaccess). Every 5th day Apr-Oct 2015-2025 (458 granules, 34 MB each, deleted after reduction). `county_smap`: 513,876 rows = 458 dates x 1,122 counties, variable `soil_moisture_am` (cm3/cm3), value of the 36 km cell containing the county representative point (not a county mean; many counties share a cell). 49.7 % null: no retrieval (frozen/snow/vegetation/RFI) — `retrieval_qual_flag` NOT applied, so non-null values may include flagged retrievals (QA pending).
- A full every-day run (2015-2025, ~2,350 granules, ~80 GB transfer) was started then stopped to free bandwidth; the 5-day sample is what is in DB. Context cell only; never show as field-precise.

### NLDAS-2 Noah (item 5b) / GPM IMERG — No-go (blocked on Earthdata authorisation)
- `earthaccess` search works, but every GES DISC download (`data.gesdisc.earthdata.nasa.gov`) returns **HTTP 403**; OPeNDAP also fails (NetCDF I/O failure). NSIDC (SMAP) and LP DAAC (HLS) work with the same login. Likely cause: the Earthdata account has not approved the **"NASA GESDISC DATA ARCHIVE"** application (Earthdata Login -> Applications -> Authorized Apps). I did not try to bypass. User action: approve the app; then run `data_pipeline/imerg_tier1.py START END` (loader written, tested only up to the 403).
- `county_imerg_daily` is empty. Fallback: POWER `PRECTOTCORR` (in `county_weather_daily`) for precipitation. ET: OpenET (2016+) / POWER-derived ET0 not computed.

### GEOS-S2S-3 (item 6) — partial
- `portal.nccs.nasa.gov/datashare/gmao/geos-s2s-3/NRT/APCN/202611/`: `202611_precip.tar.xz` (124,090,928 B) and `202611_at.tar.xz` (84,328,064 B), extracted under `raw/geos_s2s/tier2_story/x_precip|x_at`. Server drops connections (resume with curl -C needed).
- Contents: 40 files each = ensemble members by init date (20261003/08/13/18/23: 5 members each; 20261028: 15 members). Grid 0.5 deg global (720x361, lon -180..180), variables `PRECTOTCORR` (kg m-2 s-1) and `T2M` (K); monthly means, time stamps 1st of month 01:30.
- **Only 10 of 40 members have 9 time steps (Nov 2026-Jul 2027); the other 30 have 2 steps (Nov-Dec 2026).** So MAM 2027 is available (10 members), JJA is NOT (only Jun-Jul "JJ"; no August). Next-season distribution = 10 members only.
- Loaded `county_scenario_year` (source_id `geos_s2s`, model `GEOS-S2S-3`, scenario `forecast`, member = init+ens id, nearest 0.5 deg cell per county, year 2027, seasons MAM and JJ): 44,880 rows. Story 19169: pr MAM 2.1-5.6 (mean 3.7) mm/day, JJ 1.4-4.8 (2.7); T2M MAM 6.5-10.0 (8.5) degC, JJ 21.3-24.0 (23.0).
- **Raw model output, uncorrected**: no Hindcast climatology available publicly in the listing (`Hindcast/` has only `Vaisala/199102`; `Drift/for_APCN/*.drift.nc4` exist, semantics unverified) -> **anomaly vs hindcast NOT computed**. Story JJ precip mean of 2.7 mm/day looks low vs observed June-July climate (compare with POWER 1995-2025 in DB before use). Fallback per TEAM_SPEC item 6: show spread of members + POWER 1995-2025 climatology distribution.
- Licence: NASA GMAO, no explicit licence text found -> cite GMAO GEOS-S2S-3 + access date 2026-11-15.

### NAIP (item 9) — Go (search only, nothing downloaded)
- Planetary Computer STAC `naip`, pin at Story (-93.51, 42.01): 2015 (1 m), 2017 (1 m), 2019 (0.6 m), 2021 (0.6 m), 2023 (0.3 m), 2025 (0.6 m) = 6 vintages, 4 tiles each. >=3 needed. Tiles not stored (sim lane downloads on demand). Licence per AWS registry: public domain with attribution.

### NEX-GDDP-CMIP6 (item 7) — Go
- Public CC0 dataset (AWS Open Data `s3://nex-gddp-cmip6`, us-west-2; file attributes say `cmip6_license: CC-BY-SA 4.0` -> cite both; tech note + access date 2026-11-15). Direct S3 download of the global 0.25 deg files (180-245 MB per var-year) ran at ~0.5 MB/s here (one anonymous s3fs `get` was fast, threaded gets hung / returned zero-filled files). **Used NCCS THREDDS NCSS server-side bbox subset** (lat 36-49.5, lon 255-281 E; 4.6 MB/file, ~20-27 s) — `data_pipeline/nex_gddp_tier1.py` (4 threads).
- Models x scenarios: ACCESS-CM2, MPI-ESM1-2-HR, GFDL-ESM4 (member r1i1p1f1, v2.0 files) x historical 1985-2014, ssp245 and ssp585 2031-2040 x pr, tasmax, tasmin. 450 files requested.
- `county_scenario_year`: per county (nearest 0.25 deg cell to the representative point; not field-specific), per year, season ANN/MAM/JJA mean: `504900` rows total. Rows by model: ACCESS-CM2:504900. Units: tas* degC, pr mm/day (mean daily). Delta method (future window mean minus 1985-2014 mean, per model) is computed downstream from this table; no bias correction beyond what NEX-GDDP applies.
- Sanity (Story 19169): ACCESS-CM2 hist JJA tasmax 28.8 degC vs POWER 1995-2014 28.5 degC. JJA tasmax 2031-2040 minus 1985-2014: ACCESS-CM2 ssp245 +2.1; ACCESS-CM2 ssp585 +3.4. Annual precip change: ACCESS-CM2 ssp245 6.5%; ACCESS-CM2 ssp585 3.1%.
- Windows are 10-yr means from single realisation r1i1p1f1 per model: internal variability is large; show as range across models/scenarios, never as a point forecast.
