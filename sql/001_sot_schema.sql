CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE data_source (
  source_id       text PRIMARY KEY,
  name            text NOT NULL,
  is_nasa         boolean NOT NULL,
  official07      boolean NOT NULL,
  license         text,
  citation        text,
  access_url      text,
  notes           text
);

CREATE TABLE fields (
  field_id        text PRIMARY KEY,          -- CSB id
  csb_version     text,
  county_fips     char(5) NOT NULL,
  state_alpha     char(2) NOT NULL,
  geom            geometry(MultiPolygon, 4326) NOT NULL,
  centroid        geometry(Point, 4326),
  area_ha         numeric,
  current_rotation text,                     -- e.g. 'C-S'
  notes           text
);

CREATE INDEX fields_geom_gix ON fields USING GIST (geom);

CREATE TABLE field_season (
  field_id        text NOT NULL REFERENCES fields (field_id),
  year            integer NOT NULL,
  season          text NOT NULL,             -- spring|summer|fall|winter|annual
  ndvi_p50        numeric,
  bare_days       integer,
  bare_start      date,
  bare_end        date,
  precip_mm       numeric,
  tmin_c          numeric,
  tmax_c          numeric,
  et0_mm          numeric,
  smap_sm_anomaly numeric,                   -- context cell, not field-precise
  source_notes    text,
  PRIMARY KEY (field_id, year, season)
);

CREATE TABLE climate_daily (
  field_id        text NOT NULL REFERENCES fields (field_id),
  date            date NOT NULL,
  source_id       text NOT NULL REFERENCES data_source (source_id),
  t2m_c           numeric,
  tmin_c          numeric,
  tmax_c          numeric,
  precip_mm       numeric,
  et0_mm          numeric,
  qa_flag         text,
  PRIMARY KEY (field_id, date, source_id)
);

CREATE TABLE strategy_score (
  field_id        text NOT NULL REFERENCES fields (field_id),
  strategy_code   text NOT NULL,             -- A|B|C|D
  run_id          text NOT NULL,
  n_cycle_index   numeric,
  erosion_index   numeric,
  organic_matter_index numeric,
  pest_break_index numeric,
  water_use_index numeric,
  forage_index    numeric,
  market_index    numeric,
  p10             numeric,
  p50             numeric,
  p90             numeric,
  cvar            numeric,
  unit            text,                      -- unit of p10/p50/p90/cvar
  card            jsonb NOT NULL,            -- why, evidence, benefits, gaps, risks
  created_at      timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (field_id, strategy_code, run_id)
);

CREATE TABLE backtest_result (
  field_id        text NOT NULL REFERENCES fields (field_id),
  strategy_code   text NOT NULL,
  year            integer NOT NULL,
  observed_cdl    text,
  observed_sequence text,
  county_yield_bu_ac numeric,
  notes           text,
  metrics         jsonb,
  PRIMARY KEY (field_id, strategy_code, year)
);

CREATE TABLE evidence_chunk (
  chunk_id        bigserial PRIMARY KEY,
  strategy_code   text,                      -- nullable = general
  source_title    text NOT NULL,
  doi             text,
  url             text,
  license         text,
  quote           text NOT NULL,
  embedding       vector(384)               -- 모델 확정 후 차원 고정
);

-- 주말 안에 임베딩이 실패하면 embedding 을 비우고 키워드 검색만 한다.
CREATE INDEX evidence_chunk_t_idx ON evidence_chunk
  USING GIN (to_tsvector('simple', coalesce(quote, '') || ' ' || coalesce(source_title, '')));

-- 2026-11-15 08:20 추가: MATLAB 산출, 시나리오, 비전 (TEAM_SPEC 7.4)
CREATE TABLE field_dekad (
  field_id        text NOT NULL REFERENCES fields (field_id),
  year            integer NOT NULL,
  dekad           smallint NOT NULL,         -- 1..36
  date_start      date NOT NULL,
  ndvi_raw        numeric,
  ndvi_sg         numeric,                   -- Savitzky-Golay smoothed
  n_obs           integer,
  bare_flag       boolean,
  precip_mm       numeric,
  et0_mm          numeric,
  t2m_c           numeric,
  sm_anom_ctx     numeric,                   -- context cell, not field-precise
  qa_flag         text,
  PRIMARY KEY (field_id, year, dekad)
);

CREATE TABLE climate_annual (
  field_id        text NOT NULL REFERENCES fields (field_id),
  year            integer NOT NULL,
  precip_mm       numeric,
  et_mm           numeric,                   -- actual ET (NLDAS-2, context cell)
  et0_mm          numeric,                   -- FAO-56 reference ET from POWER
  t2m_mean_c      numeric,
  ndvi_peak       numeric,
  gdd_c           numeric,                   -- base 10 C
  frost_days      integer,                   -- tmin < 0 C
  heat_days       integer,                   -- tmax > 32 C
  crop_cdl        text,
  source_ids      text,                      -- ';' separated
  PRIMARY KEY (field_id, year)
);

CREATE TABLE scenario_climate (
  field_id        text NOT NULL REFERENCES fields (field_id),
  horizon         text NOT NULL,             -- next_season | 2030s
  source_id       text NOT NULL,             -- geos_s2s | nex_gddp
  scenario        text NOT NULL,             -- forecast | ssp245 | ssp585
  model           text NOT NULL,
  member          text NOT NULL DEFAULT 'mean',
  variable        text NOT NULL,             -- pr | tas | tasmax | tasmin
  period          text NOT NULL,             -- e.g. 2027-JJA, 2031-2040
  value           numeric,
  unit            text,
  baseline_period text,
  anomaly         numeric,
  anomaly_unit    text,
  PRIMARY KEY (field_id, horizon, source_id, scenario, model, member, variable, period)
);

CREATE TABLE vision_result (
  field_id        text NOT NULL REFERENCES fields (field_id),
  year            integer NOT NULL,
  model_id        text NOT NULL,             -- e.g. ibm-nasa-geospatial/Prithvi-EO-1.0-100M-multi-temporal-crop-classification
  scene_dates     text NOT NULL,             -- 3 HLS dates, ';' separated
  crop_pred       text,                      -- field majority class
  class_fractions jsonb,                     -- {class: fraction}
  bare_fraction   numeric,
  agreement_with_cdl numeric,                -- pixel agreement 0-1
  notes           text,
  PRIMARY KEY (field_id, year, model_id)
);

CREATE TABLE calibration_param (
  param           text PRIMARY KEY,
  value           numeric,
  unit            text,
  method          text,
  source          text,
  notes           text
);
