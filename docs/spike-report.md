# Data spike report (data lane) — 2026-11-15

Branch `feat/26-data-spike`. Scripts: `data_pipeline/`, DDL: `sql/`. DB: `fieldshift` (Postgres+PostGIS+pgvector, 127.0.0.1:5433). Raw: `/srv/hackathon/data/raw/<dataset>/`.
No secrets in repo. No data files committed.

## Overall: (updated live; see bottom) 

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
