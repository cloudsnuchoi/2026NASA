-- Spike extension tables (tier 1 county layer + raw spike outputs). Not in SOT section 5; proposed additions.
CREATE TABLE IF NOT EXISTS county (
  county_fips char(5) PRIMARY KEY, state_alpha char(2) NOT NULL, name text,
  geom geometry(MultiPolygon,4326) NOT NULL, centroid geometry(Point,4326), area_km2 numeric);
CREATE INDEX IF NOT EXISTS county_geom_gix ON county USING GIST(geom);
CREATE TABLE IF NOT EXISTS county_weather_daily (
  county_fips char(5) NOT NULL, date date NOT NULL, source_id text NOT NULL,
  t2m_c real, tmin_c real, tmax_c real, precip_mm real, rh2m_pct real, ws2m_ms real, srad_mj_m2 real, et0_mm real,
  PRIMARY KEY (county_fips, source_id, date));
CREATE TABLE IF NOT EXISTS county_crop_share (
  county_fips char(5) NOT NULL, year int NOT NULL, cdl_class int NOT NULL, crop_name text, pixels bigint, share numeric,
  PRIMARY KEY (county_fips, year, cdl_class));
CREATE TABLE IF NOT EXISTS county_smap (
  county_fips char(5) NOT NULL, date date NOT NULL, product text NOT NULL, variable text NOT NULL, value real, unit text,
  PRIMARY KEY (county_fips, date, product, variable));
CREATE TABLE IF NOT EXISTS county_yield (
  county_fips char(5) NOT NULL, year int NOT NULL, crop text NOT NULL, yield_bu_ac numeric, source text,
  PRIMARY KEY (county_fips, year, crop));
CREATE TABLE IF NOT EXISTS field_soil (
  field_id text NOT NULL, mukey text, comppct_r numeric, om_pct numeric, kffact numeric, drainagecl text, awc_cm_cm numeric, source text,
  PRIMARY KEY (field_id, mukey));
CREATE TABLE IF NOT EXISTS field_crop_history (
  field_id text NOT NULL, year int NOT NULL, cdl_class int, crop_name text, share numeric,
  PRIMARY KEY (field_id, year));
CREATE TABLE IF NOT EXISTS field_et_openet (
  field_id text NOT NULL, date date NOT NULL, variable text NOT NULL, value real, unit text, source text,
  PRIMARY KEY (field_id, date, variable));
CREATE TABLE IF NOT EXISTS field_ndvi_hls (
  field_id text NOT NULL, date date NOT NULL, product text NOT NULL, ndvi real, valid_frac real,
  PRIMARY KEY (field_id, date, product));
CREATE TABLE IF NOT EXISTS county_imerg_daily (
  county_fips char(5) NOT NULL, date date NOT NULL, precip_mm real, product text,
  PRIMARY KEY (county_fips, date));
CREATE TABLE IF NOT EXISTS spike_log (
  id serial PRIMARY KEY, item text, status text, rows_loaded bigint, note text, ts timestamptz DEFAULT now());
create table if not exists county_scenario_year(county_fips char(5) not null, source_id text not null default 'nex_gddp', model text not null, scenario text not null, member text not null default 'r1i1p1f1', variable text not null, season text not null, year int not null, value real, unit text, primary key(county_fips,source_id,model,scenario,member,variable,season,year));  -- seasonal/annual means per year from NEX-GDDP-CMIP6 daily at county rep point (nearest 0.25deg cell); tas* in C, pr in mm/day
