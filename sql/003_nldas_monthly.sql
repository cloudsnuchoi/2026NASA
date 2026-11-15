-- NLDAS-2 Noah monthly (NLDAS_NOAH0125_M v2.0, 0.125 deg) county means, tier 1. Units are the NetCDF `units` attributes as read from the files.
CREATE TABLE IF NOT EXISTS county_nldas_monthly (
  county_fips char(5) NOT NULL, month date NOT NULL,           -- first day of month
  rootmoist_kg_m2 real,      -- RootMoist, Root zone soil moisture (kg m-2)
  soilm_0_10_kg_m2 real,     -- SoilM_0_10cm (kg m-2)
  soilm_10_40_kg_m2 real,    -- SoilM_10_40cm (kg m-2)
  soilm_40_100_kg_m2 real,   -- SoilM_40_100cm (kg m-2)
  soilm_100_200_kg_m2 real,  -- SoilM_100_200cm (kg m-2)
  evap_kg_m2 real,           -- Evap, Total evapotranspiration (kg m-2)
  potevap_w_m2 real,         -- PotEvap, Potential evapotranspiration (W m-2)
  tveg_w_m2 real,            -- TVeg, Transpiration (W m-2)
  esoil_w_m2 real,           -- ESoil, Direct evaporation from bare soil (W m-2)
  ecanop_w_m2 real,          -- ECanop, Canopy water evaporation (W m-2)
  rainf_kg_m2 real,          -- Rainf, Liquid precipitation (rainfall) (kg m-2)
  PRIMARY KEY (county_fips, month));
