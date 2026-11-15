-- QA data-sanity checks for the fieldshift DB (read-only). Run: data_pipeline/qa_checks.sh
-- Every row: check | observed | expectation | status (PASS / WARN / FAIL / INFO).
-- Thresholds are plausibility bounds for the 12-state Corn Belt, not calibration values.
\set ON_ERROR_STOP on
\pset footer off
\pset tuples_only on
\pset format unaligned
\pset fieldsep ' | '

-- 1. row counts -------------------------------------------------------------------------------------
SELECT 'rows.' || relname, n_live_tup::text, '>0 (empty = data gap)',
       CASE WHEN n_live_tup > 0 THEN 'PASS'
            WHEN relname IN ('climate_daily', 'climate_annual', 'field_season', 'field_dekad', 'scenario_climate',
                             'calibration_param', 'evidence_chunk', 'vision_result', 'strategy_score',
                             'backtest_result', 'data_source') THEN 'WARN' ELSE 'FAIL' END
FROM pg_stat_user_tables WHERE schemaname = 'public' AND relname NOT IN ('spatial_ref_sys', 'spike_log')
ORDER BY relname;

-- 2. key formats ------------------------------------------------------------------------------------
SELECT 'fips.county_format', count(*)::text, '0 non-5-digit FIPS', CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END
FROM county WHERE county_fips !~ '^[0-9]{5}$';
SELECT 'fips.county_states', string_agg(DISTINCT state_alpha, ','), '12 Corn Belt states',
       CASE WHEN count(DISTINCT state_alpha) = 12 THEN 'PASS' ELSE 'FAIL' END FROM county;
SELECT 'fips.state_prefix', count(*)::text, '0 FIPS whose state prefix disagrees with state_alpha',
       CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END
FROM county WHERE (state_alpha, left(county_fips, 2)) NOT IN
  (('IA','19'),('IL','17'),('IN','18'),('KS','20'),('KY','21'),('MI','26'),('MN','27'),('MO','29'),('NE','31'),('OH','39'),('SD','46'),('WI','55'));
SELECT 'fips.fields_story', count(*)::text, 'all fields in 19169', CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END
FROM fields WHERE county_fips !~ '^[0-9]{5}$' OR county_fips <> '19169';
SELECT 'fips.orphans.' || t, n::text, '0 county_fips not in county', CASE WHEN n = 0 THEN 'PASS' ELSE 'FAIL' END FROM (
  SELECT 'weather' t, count(DISTINCT w.county_fips) n FROM county_weather_daily w LEFT JOIN county c USING (county_fips) WHERE c.county_fips IS NULL
  UNION ALL SELECT 'imerg', count(DISTINCT x.county_fips) FROM county_imerg_daily x LEFT JOIN county c USING (county_fips) WHERE c.county_fips IS NULL
  UNION ALL SELECT 'nldas', count(DISTINCT x.county_fips) FROM county_nldas_monthly x LEFT JOIN county c USING (county_fips) WHERE c.county_fips IS NULL
  UNION ALL SELECT 'yield', count(DISTINCT x.county_fips) FROM county_yield x LEFT JOIN county c USING (county_fips) WHERE c.county_fips IS NULL
) q;
SELECT 'ids.field_id_numeric', count(*)::text, '0 non-numeric CSB ids', CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END
FROM fields WHERE field_id !~ '^[0-9]+$';

-- 3. duplicate keys ---------------------------------------------------------------------------------
SELECT 'dup.' || t, n::text, '0 duplicate natural keys', CASE WHEN n = 0 THEN 'PASS' ELSE 'FAIL' END FROM (
  SELECT 'weather' t, count(*) - count(DISTINCT (county_fips, date, source_id)) n FROM county_weather_daily
  UNION ALL SELECT 'imerg', count(*) - count(DISTINCT (county_fips, date)) FROM county_imerg_daily
  UNION ALL SELECT 'nldas', count(*) - count(DISTINCT (county_fips, month)) FROM county_nldas_monthly
  UNION ALL SELECT 'scenario', count(*) - count(DISTINCT (county_fips, source_id, model, scenario, member, variable, season, year)) FROM county_scenario_year
  UNION ALL SELECT 'smap', count(*) - count(DISTINCT (county_fips, date, variable)) FROM county_smap
  UNION ALL SELECT 'yield', count(*) - count(DISTINCT (county_fips, year, crop)) FROM county_yield
  UNION ALL SELECT 'crop_share', count(*) - count(DISTINCT (county_fips, year, cdl_class)) FROM county_crop_share
  UNION ALL SELECT 'field_crop_history', count(*) - count(DISTINCT (field_id, year)) FROM field_crop_history
  UNION ALL SELECT 'field_soil', count(*) - count(DISTINCT field_id) FROM field_soil
  UNION ALL SELECT 'field_ndvi', count(*) - count(DISTINCT (field_id, date, product)) FROM field_ndvi_hls
  UNION ALL SELECT 'field_et', count(*) - count(DISTINCT (field_id, date, variable)) FROM field_et_openet
) q;

-- 4. coverage and date ranges -----------------------------------------------------------------------
SELECT 'range.weather', min(date) || '..' || max(date) || ' counties=' || count(DISTINCT county_fips), '1995-01-01..2025-12-31, 1122',
       CASE WHEN min(date) = '1995-01-01' AND max(date) >= '2025-12-01' AND count(DISTINCT county_fips) = 1122 THEN 'PASS' ELSE 'FAIL' END
FROM county_weather_daily;
SELECT 'range.weather_days_per_county', min(n) || '..' || max(n), 'equal per county (complete daily series)',
       CASE WHEN min(n) = max(n) THEN 'PASS' ELSE 'FAIL' END
FROM (SELECT county_fips, count(*) n FROM county_weather_daily GROUP BY 1) q;
SELECT 'range.imerg', min(date) || '..' || max(date) || ' counties=' || count(DISTINCT county_fips), 'loaded for 1122 counties (if present)',
       CASE WHEN count(*) = 0 THEN 'WARN' WHEN count(DISTINCT county_fips) = 1122 THEN 'PASS' ELSE 'WARN' END
FROM county_imerg_daily;
SELECT 'range.imerg_days_per_county', min(n) || '..' || max(n), 'equal per county',
       CASE WHEN min(n) = max(n) THEN 'PASS' ELSE 'WARN' END
FROM (SELECT county_fips, count(*) n FROM county_imerg_daily GROUP BY 1) q;
SELECT 'range.nldas', min(month) || '..' || max(month) || ' counties=' || count(DISTINCT county_fips), '1995-01..2025-12, 1122',
       CASE WHEN count(DISTINCT county_fips) = 1122 THEN 'PASS' ELSE 'WARN' END FROM county_nldas_monthly;
SELECT 'range.nldas_month_day1', count(*)::text, '0 months not on day 1', CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END
FROM county_nldas_monthly WHERE extract(day FROM month) <> 1;
SELECT 'range.smap', min(date) || '..' || max(date), '2015-03/04 onwards', CASE WHEN min(date) >= '2015-03-01' THEN 'PASS' ELSE 'FAIL' END FROM county_smap;
SELECT 'range.yield', min(year) || '..' || max(year) || ' counties=' || count(DISTINCT county_fips), '>=2008..2025', 'INFO' FROM county_yield;
SELECT 'range.crop_history', min(year) || '..' || max(year) || ' fields=' || count(DISTINCT field_id), '2008..2025, 6027',
       CASE WHEN count(DISTINCT field_id) = 6027 THEN 'PASS' ELSE 'WARN' END FROM field_crop_history;
SELECT 'coverage.demo_series', (SELECT count(DISTINCT field_id) FROM field_et_openet) || ' ET / ' ||
       (SELECT count(DISTINCT field_id) FROM field_ndvi_hls) || ' NDVI', '12 demo fields each', 'INFO';

-- 5. null ratios ------------------------------------------------------------------------------------
SELECT 'null.' || c, round(100.0 * nulls / NULLIF(n, 0), 3) || ' %', lim, CASE WHEN 100.0 * nulls / NULLIF(n, 0) <= lim_v THEN 'PASS' ELSE sev END FROM (
  SELECT 'weather.precip_mm' c, count(*) n, count(*) FILTER (WHERE precip_mm IS NULL) nulls, '<=0.1 %' lim, 0.1 lim_v, 'FAIL' sev FROM county_weather_daily
  UNION ALL SELECT 'weather.t2m_c', count(*), count(*) FILTER (WHERE t2m_c IS NULL), '<=0.1 %', 0.1, 'FAIL' FROM county_weather_daily
  UNION ALL SELECT 'weather.srad', count(*), count(*) FILTER (WHERE srad_mj_m2 IS NULL), '<=0.1 % (Hargreaves fill)', 0.1, 'WARN' FROM county_weather_daily
  UNION ALL SELECT 'weather.et0_mm', count(*), count(*) FILTER (WHERE et0_mm IS NULL), '<=1 % (or drop column)', 1, 'WARN' FROM county_weather_daily
  UNION ALL SELECT 'imerg.precip_mm', count(*), count(*) FILTER (WHERE precip_mm IS NULL), '<=1 %', 1, 'WARN' FROM county_imerg_daily
  UNION ALL SELECT 'nldas.rainf', count(*), count(*) FILTER (WHERE rainf_kg_m2 IS NULL), '<=1 %', 1, 'WARN' FROM county_nldas_monthly
  UNION ALL SELECT 'nldas.rootmoist', count(*), count(*) FILTER (WHERE rootmoist_kg_m2 IS NULL), '<=1 %', 1, 'WARN' FROM county_nldas_monthly
  UNION ALL SELECT 'scenario.value', count(*), count(*) FILTER (WHERE value IS NULL), '<=1 %', 1, 'WARN' FROM county_scenario_year
  UNION ALL SELECT 'field_soil.awc', count(*), count(*) FILTER (WHERE awc_cm_cm IS NULL), '<=1 %', 1, 'WARN' FROM field_soil
  UNION ALL SELECT 'field_ndvi.ndvi', count(*), count(*) FILTER (WHERE ndvi IS NULL), '<=30 % (cloud mask)', 30, 'WARN' FROM field_ndvi_hls
  UNION ALL SELECT 'field_et.value', count(*), count(*) FILTER (WHERE value IS NULL), '<=1 %', 1, 'WARN' FROM field_et_openet
) q ORDER BY 1;

-- 6. physical plausibility --------------------------------------------------------------------------
SELECT 'phys.weather_t', min(tmin_c) || '..' || max(tmax_c) || ' degC', 'tmin>=-50, tmax<=50, tmin<=tmax',
       CASE WHEN min(tmin_c) >= -50 AND max(tmax_c) <= 50 AND count(*) FILTER (WHERE tmin_c > tmax_c) = 0 THEN 'PASS' ELSE 'FAIL' END
FROM county_weather_daily;
SELECT 'phys.weather_precip', min(precip_mm) || '..' || max(precip_mm) || ' mm/day', '0..300 mm/day',
       CASE WHEN min(precip_mm) >= 0 AND max(precip_mm) <= 300 THEN 'PASS' ELSE 'FAIL' END FROM county_weather_daily;
SELECT 'phys.weather_rh_ws_srad', 'rh ' || min(rh2m_pct) || '..' || max(rh2m_pct) || ', ws ' || min(ws2m_ms) || '..' || max(ws2m_ms)
       || ', srad ' || min(srad_mj_m2) || '..' || max(srad_mj_m2), 'rh 0..100 %, ws 0..30 m/s, srad 0..40 MJ/m2/d',
       CASE WHEN min(rh2m_pct) >= 0 AND max(rh2m_pct) <= 100 AND min(ws2m_ms) >= 0 AND max(ws2m_ms) <= 30
                 AND min(srad_mj_m2) >= 0 AND max(srad_mj_m2) <= 40 THEN 'PASS' ELSE 'FAIL' END FROM county_weather_daily;
SELECT 'phys.power_annual_precip', round(min(p)) || '..' || round(max(p)) || ' mm/yr', 'county-year 150..2000 mm',
       CASE WHEN min(p) >= 150 AND max(p) <= 2000 THEN 'PASS' ELSE 'WARN' END
FROM (SELECT county_fips, extract(year FROM date), sum(precip_mm) p FROM county_weather_daily GROUP BY 1, 2) q;
SELECT 'phys.imerg_precip', min(precip_mm) || '..' || max(precip_mm) || ' mm/day', '0..400 mm/day',
       CASE WHEN count(*) = 0 THEN 'WARN' WHEN min(precip_mm) >= 0 AND max(precip_mm) <= 400 THEN 'PASS' ELSE 'FAIL' END FROM county_imerg_daily;
-- IMERG vs POWER annual totals over common full years (2020-2024): ratio far from 1 => unit problem
SELECT 'phys.imerg_vs_power_ratio', round(avg(i / NULLIF(p, 0))::numeric, 3) || ' (min ' || round(min(i / NULLIF(p, 0))::numeric, 2)
       || ', max ' || round(max(i / NULLIF(p, 0))::numeric, 2) || ')', 'mean 0.8..1.25 (same mm/day unit)',
       CASE WHEN avg(i / NULLIF(p, 0)) BETWEEN 0.8 AND 1.25 THEN 'PASS' ELSE 'FAIL' END
FROM (SELECT x.county_fips, extract(year FROM x.date) y, sum(x.precip_mm) i, sum(w.precip_mm) p
      FROM county_imerg_daily x JOIN county_weather_daily w ON w.county_fips = x.county_fips AND w.date = x.date
      WHERE x.date BETWEEN '2020-01-01' AND '2024-12-31' GROUP BY 1, 2) q;
-- NLDAS-2 NOAH monthly: kg/m2 fields are monthly accumulations (= mm/month); W/m2 fields are monthly means
SELECT 'phys.nldas_rainf', round(min(r)) || '..' || round(max(r)) || ' mm/yr (county-year sum of kg/m2)', 'county-year 150..2000 mm',
       CASE WHEN min(r) >= 150 AND max(r) <= 2000 THEN 'PASS' ELSE 'FAIL' END
FROM (SELECT county_fips, extract(year FROM month), sum(rainf_kg_m2) r FROM county_nldas_monthly GROUP BY 1, 2 HAVING count(*) = 12) q;
SELECT 'phys.nldas_vs_power_ratio', round(avg(n / NULLIF(p, 0))::numeric, 3), '2015-2024 county totals, mean 0.8..1.25 (Rainf excludes snow)',
       CASE WHEN avg(n / NULLIF(p, 0)) BETWEEN 0.8 AND 1.25 THEN 'PASS' ELSE 'FAIL' END
FROM (SELECT n.county_fips, n.n, p.p
      FROM (SELECT county_fips, sum(rainf_kg_m2) n FROM county_nldas_monthly
            WHERE month BETWEEN '2015-01-01' AND '2024-12-01' GROUP BY 1) n
      JOIN (SELECT county_fips, sum(precip_mm) p FROM county_weather_daily
            WHERE date BETWEEN '2015-01-01' AND '2024-12-31' GROUP BY 1) p USING (county_fips)) q;
SELECT 'phys.nldas_evap', round(min(e)) || '..' || round(max(e)) || ' mm/yr', 'county-year 200..1000 mm (drought years may dip below)',
       CASE WHEN min(e) >= 200 AND max(e) <= 1000 THEN 'PASS' ELSE 'WARN' END
FROM (SELECT county_fips, extract(year FROM month), sum(evap_kg_m2) e FROM county_nldas_monthly GROUP BY 1, 2 HAVING count(*) = 12) q;
SELECT 'phys.nldas_soilm_layers', 'max 0-10cm ' || round(max(soilm_0_10_kg_m2)::numeric, 1) || ', 10-40 ' || round(max(soilm_10_40_kg_m2)::numeric, 1)
       || ', 40-100 ' || round(max(soilm_40_100_kg_m2)::numeric, 1) || ', 100-200 ' || round(max(soilm_100_200_kg_m2)::numeric, 1),
       'layer water <= layer depth*0.55 (100/300/600/1000 mm)',
       CASE WHEN max(soilm_0_10_kg_m2) <= 55 AND max(soilm_10_40_kg_m2) <= 165 AND max(soilm_40_100_kg_m2) <= 330
                 AND max(soilm_100_200_kg_m2) <= 550 AND min(soilm_0_10_kg_m2) >= 0 THEN 'PASS' ELSE 'FAIL' END
FROM county_nldas_monthly;
SELECT 'phys.nldas_potevap', round(min(potevap_w_m2)::numeric, 2) || '..' || round(max(potevap_w_m2)::numeric, 1) || ' W/m2',
       '-5..600 W/m2 monthly mean', CASE WHEN min(potevap_w_m2) >= -5 AND max(potevap_w_m2) <= 600 THEN 'PASS' ELSE 'WARN' END
FROM county_nldas_monthly;
SELECT 'phys.nldas_used_by_api', '0 references in model_api/*.py (grep)', 'used, or labelled not used', 'INFO';
SELECT 'phys.scenario_units', string_agg(DISTINCT variable || ':' || unit, ','), 'pr mm/day, tas/tasmax/tasmin degC',
       CASE WHEN bool_and((variable = 'pr' AND unit = 'mm/day') OR (variable LIKE 'tas%' AND unit = 'degC')) THEN 'PASS' ELSE 'FAIL' END
FROM county_scenario_year;
SELECT 'phys.scenario_values', 'pr ' || round(min(value) FILTER (WHERE variable = 'pr')::numeric, 2) || '..' || round(max(value) FILTER (WHERE variable = 'pr')::numeric, 2)
       || ' mm/day, t ' || round(min(value) FILTER (WHERE variable <> 'pr')::numeric, 1) || '..' || round(max(value) FILTER (WHERE variable <> 'pr')::numeric, 1),
       'pr 0..20 mm/day, t -30..45 degC',
       CASE WHEN min(value) FILTER (WHERE variable = 'pr') >= 0 AND max(value) FILTER (WHERE variable = 'pr') <= 20
                 AND min(value) FILTER (WHERE variable <> 'pr') >= -30 AND max(value) FILTER (WHERE variable <> 'pr') <= 45 THEN 'PASS' ELSE 'FAIL' END
FROM county_scenario_year;
SELECT 'phys.scenario_members', source_id || '/' || scenario || ': ' || count(DISTINCT CASE WHEN source_id = 'nex_gddp' THEN model ELSE member END), 'S2S 10 members; NEX 2 models (3 planned)', 'INFO'
FROM county_scenario_year GROUP BY source_id, scenario ORDER BY 1;
SELECT 'phys.smap', min(value) || '..' || max(value) || ' ' || string_agg(DISTINCT unit, ','), '0.02..0.6 cm3/cm3',
       CASE WHEN min(value) >= 0.0 AND max(value) <= 0.65 THEN 'PASS' ELSE 'FAIL' END FROM county_smap;
SELECT 'phys.yield.' || crop, min(yield_bu_ac) || '..' || max(yield_bu_ac) || ' bu/ac', 'corn 10..320, soy 3..100',
       CASE WHEN (crop = 'corn' AND min(yield_bu_ac) >= 10 AND max(yield_bu_ac) <= 320)
              OR (crop = 'soybeans' AND min(yield_bu_ac) >= 3 AND max(yield_bu_ac) <= 100) THEN 'PASS' ELSE 'FAIL' END
FROM county_yield GROUP BY crop;
SELECT 'phys.crop_share_sum', round(min(s), 4) || '..' || round(max(s), 4), 'county-year share sums 0.99..1.01',
       CASE WHEN min(s) >= 0.99 AND max(s) <= 1.01 THEN 'PASS' ELSE 'FAIL' END
FROM (SELECT county_fips, year, sum(share) s FROM county_crop_share GROUP BY 1, 2) q;
SELECT 'phys.ndvi_range', min(ndvi) || '..' || max(ndvi), '-1..1 (NDVI definition)',
       CASE WHEN min(ndvi) >= -1 AND max(ndvi) <= 1 THEN 'PASS' ELSE 'FAIL' END FROM field_ndvi_hls;
SELECT 'phys.openet', min(value) || '..' || max(value) || ' mm/month', '0..250 mm/month',
       CASE WHEN min(value) >= 0 AND max(value) <= 250 THEN 'PASS' ELSE 'FAIL' END FROM field_et_openet;
SELECT 'phys.soil', 'awc ' || min(awc_cm_cm) || '..' || max(awc_cm_cm) || ', k ' || min(kffact) || '..' || max(kffact) || ', om ' || min(om_pct) || '..' || max(om_pct) || ' %',
       'awc 0.02..0.4, k 0.02..0.7, om 0..20 % (mineral soils)',
       CASE WHEN max(om_pct) > 20 THEN 'WARN' WHEN min(awc_cm_cm) >= 0.02 AND max(awc_cm_cm) <= 0.4 THEN 'PASS' ELSE 'FAIL' END FROM field_soil;
SELECT 'phys.soil_om_gt20', count(*) || ' fields, mukeys ' || coalesce(string_agg(DISTINCT mukey, ','), '-'), 'organic (muck) units should be flagged in UI',
       CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'WARN' END FROM field_soil WHERE om_pct > 20;

-- 7. geometry ---------------------------------------------------------------------------------------
SELECT 'geom.fields_valid', count(*) FILTER (WHERE NOT ST_IsValid(geom)) || ' of ' || count(*), '0 invalid polygons',
       CASE WHEN count(*) FILTER (WHERE NOT ST_IsValid(geom)) = 0 THEN 'PASS' ELSE 'WARN' END FROM fields;
SELECT 'geom.fields_srid', string_agg(DISTINCT ST_SRID(geom)::text, ','), 'EPSG:4326 storage (SOT 2)',
       CASE WHEN bool_and(ST_SRID(geom) = 4326) THEN 'PASS' ELSE 'FAIL' END FROM fields;
SELECT 'geom.field_centroid_in_story', count(*) || ' outside', '0 centroids outside 19169',
       CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'WARN' END
FROM fields f WHERE NOT ST_Intersects(f.centroid, (SELECT geom FROM county WHERE county_fips = '19169'));
SELECT 'geom.field_area_ha', round(min(area_ha), 2) || '..' || round(max(area_ha), 1), '0.5..500 ha',
       CASE WHEN min(area_ha) >= 0.5 AND max(area_ha) <= 500 THEN 'PASS' ELSE 'WARN' END FROM fields;
