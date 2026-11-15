# Data usage check: submission form §7 / §8 (FINAL lane, 2026-11-15 22:00 KST)

Method: `grep -rnE` over the code we ship (`model_api/`, `data_pipeline/`, `frontend/`, `infra/`, `docs/demo/`), with `tests/` and the generated `data-sources.js` excluded. A resource stays listed only if the shipped code calls it, or its data was loaded into a table that the model API reads. Evidence is one `file:line` per call site, at commit `3e88ea6` plus this branch.

## §7 NASA data

| Resource | Evidence (file:line) | Verdict |
| --- | --- | --- |
| NASA POWER | `model_api/quick.py:244` (Tier 1 daily point API); `data_pipeline/power_tier1.py:36` (Tier 2 load) | used |
| HLS v2.0 (HLSL30/HLSS30) | `data_pipeline/hls_story.py:1`, `data_pipeline/contrast_fields.py:157`; `model_api/vision/fetch_hls_chips.py:40` (Prithvi chips) | used |
| SMAP L3 SPL3SMP v009 | `data_pipeline/smap_tier1.py:73` (load into `county_smap`); `model_api/repo.py:214-216` (read); `model_api/services.py:16,379` (response) | used |
| GPM IMERG Final V07 | `data_pipeline/imerg_tier1.py`; `model_api/repo.py:240` (`imerg_annual`); `model_api/services.py:22-31` | used |
| NLDAS-2 Noah monthly | `data_pipeline/nldas2_tier1.py`; `model_api/services.py:50-52`; `model_api/engine.py:417` (`nldas_check`) | used |
| GEOS-S2S-3 | `data_pipeline/geos_s2s_county.py`; `model_api/services.py:442-461` | used |
| NEX-GDDP-CMIP6 | `data_pipeline/nex_gddp_tier1.py`; `model_api/services.py:463-485` | used |
| Prithvi-EO-1.0-100M crop classification | `model_api/vision/prithvi_crop.py:1-4` (batch inference); `model_api/services.py:181` (`vision_result`) | used |

## §8 Other data and services

| Resource | Evidence (file:line) | Verdict |
| --- | --- | --- |
| USDA NASS Cropland Data Layer | `data_pipeline/field_cdl_history.py:1`; `model_api/cards.py:30,55` | used |
| USDA NASS Crop Sequence Boundaries | `data_pipeline/field_cdl_history.py:1`; `model_api/services.py:213` (`sources`) | used |
| USDA NASS Quick Stats (API + bulk) | `data_pipeline/nass_yield_validation.py:16` (API); `data_pipeline/nass_bulk_yield.py:1-7` (bulk, loaded into `county_yield`); `model_api/repo.py:208` (read) | used |
| USDA NRCS Soil Data Access (SSURGO) | `data_pipeline/ssurgo_story.py:17`, `data_pipeline/contrast_soil_probe.py:13`; `model_api/config.py:107` | used |
| USGS 3DEP EPQS | `model_api/quick.py:243` (URL), `model_api/quick.py:254-258` (`get_elevation`), `model_api/quick.py:339` (`_fetch_all`) | used (Tier 1 live call) |
| OpenET | `data_pipeline/contrast_fields.py:123` (`openet-api.org/raster/timeseries/point`); `model_api/engine.py:392` (`repo.openet`) | used |
| NOAA NWS API | `model_api/quick.py:246` (`/points`), `model_api/quick.py:340` (`get_nws`), `model_api/quick.py:436` (source label) | used (Tier 1 live call) |
| Open-Meteo Climate API | `model_api/quick.py:247` (`climate-api.open-meteo.com/v1/climate`), `model_api/quick.py:283` (`get_open_meteo`), `model_api/quick.py:340` | used (Tier 1 live call) |
| Esri World Imagery (basemap) | `frontend/app.js:180` = `docs/demo/app.js:180` (`L.tileLayer` World_Imagery) | used |
| US Census cartographic boundaries | `data_pipeline/load_counties.py:1,29` (cb_2023_us_county_500k into `county`); `model_api/repo.py:168` (point-in-county `ST_Contains`), `model_api/repo.py:70` | used (data shipped in DB) |
| FAO-56 (Allen et al. 1998) | `model_api/quick.py:1-5` (Kc from Table 12, Penman–Monteith eq. 6); `model_api/cards.py:26` (cited) | used (method) |
| DeepSeek API | `model_api/config.py:123` (`LLM_BASE_URL` default `https://api.deepseek.com`); `model_api/explain.py` | used |

## Not used, removed

| Resource | Evidence | Action |
| --- | --- | --- |
| USDA ERS Commodity Costs and Returns | No call or citation in `model_api/`, `data_pipeline/`, `frontend/`, `infra/` or `docs/demo/` (`grep -rniE "ers\.usda\|commodity cost\|costs.and.returns"` returns nothing). The app shows no price, revenue or cost figures. | Removed from `docs/DATA_SOURCES.md`, `frontend/data-sources.js`, `docs/demo/data-sources.js` and `docs/submission/data-links.md`. The UI methods box "[5] Agronomic formulas & economics" (`frontend/index.html:476-481`) said price/cost figures carry an ERS source; now it reads "Agronomic formulas & soil" and says no price, revenue or cost figures are shown. It was not in §7/§8 of the form. |

USGS 3DEP, NOAA NWS, Open-Meteo and Census were all suspected of being mockup leftovers. They are not: each one is called by the live Tier 1 Quick Screen (`model_api/quick.py`) or loaded into the `county` table the API reads. So they stay.

The static snapshot (`docs/demo/`) does not call EPQS, NWS or Open-Meteo itself: `docs/demo/app.js:82` sends custom-polygon Quick Screen to the live server. Snapshot results were made by the same `model_api/quick.py` calls.
