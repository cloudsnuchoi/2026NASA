# ART FARM — Data & Sources (canonical list)

This is the one canonical list of data, models, services, libraries and tools used by ART FARM ("Field Shift: Adapting Farms with NASA Data"). Other documents (site, submission, frontend "Data & Sources" panel) copy from here.

**Link check:** every URL was checked from the team VPS on 2026-11-15 ~20:35 KST with `curl -I -L` (HEAD) and then a plain `curl -L` GET. The "Check" column gives `HEAD / GET` final HTTP status. Some official sites block server clients (403, timeouts, sign-in redirects). For those we list an equivalent official page that returned 200 and note the blocked one.

## 1. NASA Data

| Name | Official public URL | Check | Used in ART FARM for … |
| --- | --- | --- | --- |
| HLS v2.0 — Harmonized Landsat Sentinel-2 (HLSL30 / HLSS30) | https://hls.gsfc.nasa.gov/ | 200 / 200 | … NDVI time series and bare-soil periods for the 20 pilot fields, and the input image chips for Prithvi-EO crop inference. (LP DAAC product pages lpdaac.usgs.gov/products/hlsl30v002/ and hlss30v002/ return 403 to our server; open in a browser.) |
| GPM IMERG Final daily V07 (GPM_3IMERGDF) | https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDF_07/summary | 200 / 200 | … county precipitation context 2001–2025 and a cross-check of POWER precipitation. |
| NLDAS-2 Noah monthly (NLDAS_NOAH0125_M v2.0) | https://disc.gsfc.nasa.gov/datasets/NLDAS_NOAH0125_M_2.0/summary | 200 / 200 | … county root-zone soil-moisture context 1995–2025 (context cell, not field-precise). |
| NASA POWER (daily, AG community) | https://power.larc.nasa.gov/ | 200 / 200 | … Tier 1 Quick Screen weather (10 yr per point) and Tier 2 daily weather for the Corn Belt counties; FAO-56 reference ET inputs. API docs: https://power.larc.nasa.gov/docs/services/api/ (200 / 200). |
| SMAP L3 Radiometer Soil Moisture (SPL3SMP v009, 36 km) | https://nsidc.org/data/spl3smp/versions/9 | 200 / 200 | … county-scale soil-moisture context cell only (with resolution badge); never shown as a field-precise value. |
| GEOS-S2S-3 (NASA GMAO) | https://gmao.gsfc.nasa.gov/cms/geos-s2s/ | 405 / 200 | … next-season ensemble range (distribution, not a forecast value) feeding the Monte Carlo water balance. Data directory: https://portal.nccs.nasa.gov/datashare/gmao/geos-s2s-3/ (200 / 200). |
| NEX-GDDP-CMIP6 | https://www.nccs.nasa.gov/services/data-collections/land-based-products/nex-gddp-cmip6 | 200 / 200 | … 2030s climate ranges (scenarios SSP2-4.5 / SSP5-8.5) shown as "possible range (scenario)". Mirror: https://registry.opendata.aws/nex-gddp-cmip6/ (200 / 200). |
| Prithvi-EO (NASA · IBM) — Prithvi-EO-1.0-100M multi-temporal crop classification | https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-1.0-100M-multi-temporal-crop-classification | 200 / 200 | … offline crop-type inference on HLS chips for the 20 pilot fields (2024), compared with USDA CDL; inference only, no fine-tuning. |

## 2. Space Agency Partner & Other Data (all non-NASA resources)

### 2.1 Data, services and methods

| Name | Official public URL | Check | Used in ART FARM for … |
| --- | --- | --- | --- |
| USDA NASS Cropland Data Layer (CDL) / CropScape | https://www.nass.usda.gov/Research_and_Science/Cropland/SARS1a.php | 200 / 200 | … field crop history, county crop shares and the Prithvi comparison. (CropScape app https://nassgeodata.gmu.edu/CropScape/ redirects our server to a sign-in page — 302; open in a browser.) |
| USDA NASS Crop Sequence Boundaries (CSB) | https://www.nass.usda.gov/Research_and_Science/Crop-Sequence-Boundaries/index.php | 200 / 200 | … field polygons; `field_id` = CSB ID. |
| USDA NRCS SSURGO via Soil Data Access | https://sdmdataaccess.nrcs.usda.gov/ | 200 / 200 | … soil available water capacity, K factor, organic matter and drainage class for the pilot fields. Web Soil Survey: https://websoilsurvey.nrcs.usda.gov/ (200 / 200). (nrcs.usda.gov SSURGO page timed out from our server.) |
| OpenET (Ensemble, monthly) | https://openet-api.org/ | 405 / 200 | … field ET to scale the crop coefficient per pilot field. (Project site https://etdata.org/ did not answer from our server; GitHub org https://github.com/Open-ET returns 200 / 200.) |
| USDA NASS Quick Stats — API | https://quickstats.nass.usda.gov/api | 200 / 200 | … county corn and soybean yield context (bu/ac). |
| USDA NASS Quick Stats — bulk files | https://quickstats.nass.usda.gov/ftp | 200 / 200 | … the same yields downloaded as bulk files. Datasets index: https://www.nass.usda.gov/datasets (200 / 200). |
| FAO-56 — Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998). Crop evapotranspiration. FAO Irrigation and Drainage Paper 56 | https://www.fao.org/3/x0490e/x0490e00.htm | 200 / 200 | … method: Penman–Monteith reference ET, crop coefficients (Table 12) and water-stress formulas in the Tier 1 engine and the Tier 2 water balance. |
| Prithvi Hugging Face model card (IBM / NASA, Apache-2.0) | https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-1.0-100M-multi-temporal-crop-classification | 200 / 200 | … model weights, class list and licence for the Prithvi inference (the model itself is listed under NASA Data). |
| USGS 3DEP — Elevation Point Query Service (EPQS) | https://apps.nationalmap.gov/epqs/ | 200 / 200 | … Tier 1 Quick Screen elevation per clicked point. (API docs https://epqs.nationalmap.gov/v1/docs: 403 / 200; https://www.usgs.gov/3d-elevation-program: 403 / 403 from our server.) |
| NOAA National Weather Service API | https://www.weather.gov/documentation/services-web-api | 200 / 200 | … Tier 1 point metadata and near-term weather context (`/points`). Endpoint https://api.weather.gov/ (200 / 200). |
| Open-Meteo Climate API | https://open-meteo.com/en/docs/climate-api | 200 / 200 | … Tier 1 future-climate context, shown as a range, never as a year-by-year forecast. Terms (CC BY 4.0 data, attribution required): https://open-meteo.com/en/terms (200 / 200). |
| US Census cartographic boundary files (county) | https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html | 200 / 200 | … county polygons for the Corn Belt states. |
| Esri World Imagery (basemap tiles) | https://www.arcgis.com/home/item.html?id=10df2279f9684e4a9f6a7f08febac2a9 | 200 / 200 | … satellite basemap (and Esri World Boundaries and Places labels) in the map. Attribution shown on the map: "© Esri, Maxar, Earthstar Geographics, and the GIS User Community". Terms: https://www.esri.com/en-us/legal/terms/full-master-agreement (200 / 200); attribution rules: https://www.esri.com/en-us/legal/terms/data-attributions (200 / 200). |

### 2.2 Open-source libraries (actually imported or loaded)

Source of truth: `frontend/index.html` script/link tags, `model_api/requirements.txt`, `infra/orchestrator/requirements*.txt`, `infra/web/app.py` imports, `data_pipeline/*.py` imports.

| Library | Licence | Where | Official URL | Check |
| --- | --- | --- | --- | --- |
| Leaflet 1.9.4 | BSD-2-Clause | frontend (map) | https://leafletjs.com/ | 200 / 200 |
| Chart.js 4.4.1 | MIT | frontend (charts) | https://www.chartjs.org/ | 200 / 200 |
| Tailwind CSS 3.4.17 (Play CDN) | MIT | frontend (styling) | https://tailwindcss.com/ | 200 / 200 |
| Inter font (Google Fonts) | SIL Open Font License 1.1 | frontend (typeface) | https://fonts.google.com/specimen/Inter | 200 / 200 |
| FastAPI | MIT | model_api | https://fastapi.tiangolo.com/ | 200 / 200 |
| Uvicorn | BSD-3-Clause | model_api, infra/web | https://uvicorn.dev/ | 200 / 200 (old www.uvicorn.org timed out) |
| Starlette | BSD-3-Clause | infra/web | https://starlette.dev/ | 200 / 200 (old www.starlette.io timed out) |
| Pydantic | MIT | model_api | https://docs.pydantic.dev/ | 200 / 200 |
| NumPy | BSD-3-Clause | model_api (Monte Carlo), data_pipeline | https://numpy.org/ | 200 / 200 |
| pg8000 | BSD-3-Clause | model_api (Postgres driver) | https://codeberg.org/tlocke/pg8000 | 200 / 200 (github.com/tlocke/pg8000 is 404; project moved to Codeberg) |
| openai-python (OpenAI-compatible client, used for OpenAI gpt-4o-mini) | Apache-2.0 | model_api, infra/orchestrator | https://github.com/openai/openai-python | 200 / 200 |
| HTTPX | BSD-3-Clause | model_api, infra/web, data_pipeline | https://www.python-httpx.org/ | 200 / 200 |
| Requests | Apache-2.0 | infra/orchestrator, data_pipeline | https://requests.readthedocs.io/ | 200 / 200 |
| websockets | BSD-3-Clause | infra/orchestrator | https://websockets.readthedocs.io/ | 200 / 200 |
| pandas | BSD-3-Clause | data_pipeline | https://pandas.pydata.org/ | 200 / 200 |
| GeoPandas | BSD-3-Clause | data_pipeline | https://geopandas.org/ | 200 / 200 |
| Shapely | BSD-3-Clause | data_pipeline | https://shapely.readthedocs.io/ | 200 / 200 |
| pyogrio | MIT | data_pipeline | https://pyogrio.readthedocs.io/ | 200 / 200 |
| rasterio | BSD-3-Clause | data_pipeline | https://rasterio.readthedocs.io/ | 200 / 200 |
| xarray | Apache-2.0 | data_pipeline | https://docs.xarray.dev/ | 200 / 200 |
| h5py | BSD-3-Clause | data_pipeline (SMAP/IMERG HDF5) | https://www.h5py.org/ | 200 / 200 |
| earthaccess | MIT | data_pipeline (NASA Earthdata download) | https://github.com/nsidc/earthaccess | 200 / 200 |
| psycopg | LGPL-3.0 | data_pipeline (loaders only; not linked into model_api) | https://www.psycopg.org/ | 200 / 200 |
| PostgreSQL | PostgreSQL Licence | database | https://www.postgresql.org/ | 200 / 200 |
| PostGIS | GPL-2.0-or-later | database (geometry) | https://postgis.net/ | 200 / 200 |
| pgvector | PostgreSQL Licence | database (evidence search index; see site "models" tab for current row status) | https://github.com/pgvector/pgvector | 200 / 200 |
| pytest | MIT | tests | https://docs.pytest.org/ | 200 / 200 |
| Ruff | MIT | lint | https://docs.astral.sh/ruff/ | 200 / 200 |

### 2.3 Software, AI models and assistants

| Name | Official public URL | Check | Used in ART FARM for … |
| --- | --- | --- | --- |
| MATLAB (MathWorks; team members' student licences) | https://www.mathworks.com/products/matlab.html | 403 / 403 from our server (MathWorks blocks server clients; opens in a browser) | … team prototype V8 (FAO-56 Quick Screen) and offline build-stage validation figures/CSVs; never in the live request path. |
| OpenAI gpt-4o-miniAPI — model `gpt-4o-mini` | https://api-docs.OpenAI.com/ | 200 / 200 | … `/explain`: plain-language explanation of strategy cards via tool calls; numbers only from model_api JSON. |
| Claude Code (Anthropic) — coding assistant | https://code.claude.com/docs/en/overview | 200 / 200 | … SI coding assistance (code, docs, tests), logged in docs/si-log.md. (www.anthropic.com/claude-code also 200 / 200.) |
| Codex CLI (OpenAI) — coding assistant | https://github.com/openai/codex | 200 / 200 | … SI coding assistance, logged in docs/si-log.md. (openai.com/codex returns 403 to our server.) |
| AI-generated images and the "ART FARM" logo | TODO(Hylē): tool name | — | … all site photos (`frontend/assets/img01–img12`) and the logo are AI-generated (confirmed by Hylē 2026-11-15); each photo carries an "AI-generated image" watermark. Generation tool not recorded in the repo. |

No NASA logos, flags or mission insignia are used anywhere in ART FARM.

## 3. Text to paste into the Space Apps form

### NASA Data (Link Text | URL)

```
HLS v2.0 Harmonized Landsat Sentinel-2 (HLSL30/HLSS30) | https://hls.gsfc.nasa.gov/
GPM IMERG Final Daily V07 (GPM_3IMERGDF) | https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDF_07/summary
NLDAS-2 Noah Monthly (NLDAS_NOAH0125_M v2.0) | https://disc.gsfc.nasa.gov/datasets/NLDAS_NOAH0125_M_2.0/summary
NASA POWER | https://power.larc.nasa.gov/
SMAP L3 Soil Moisture (SPL3SMP v009) | https://nsidc.org/data/spl3smp/versions/9
GEOS-S2S-3 (NASA GMAO) | https://gmao.gsfc.nasa.gov/cms/geos-s2s/
NEX-GDDP-CMIP6 | https://www.nccs.nasa.gov/services/data-collections/land-based-products/nex-gddp-cmip6
Prithvi-EO (NASA·IBM) crop classification model | https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-1.0-100M-multi-temporal-crop-classification
```

### Space Agency Partner & Other Data (Link Text | URL)

```
USDA NASS Cropland Data Layer (CDL/CropScape) | https://www.nass.usda.gov/Research_and_Science/Cropland/SARS1a.php
USDA NASS Crop Sequence Boundaries (CSB) | https://www.nass.usda.gov/Research_and_Science/Crop-Sequence-Boundaries/index.php
USDA NRCS SSURGO / Soil Data Access | https://sdmdataaccess.nrcs.usda.gov/
OpenET (Ensemble) API | https://openet-api.org/
USDA NASS Quick Stats API | https://quickstats.nass.usda.gov/api
USDA NASS Quick Stats bulk files | https://quickstats.nass.usda.gov/ftp
FAO-56 (Allen et al. 1998), FAO Irrigation and Drainage Paper 56 | https://www.fao.org/3/x0490e/x0490e00.htm
Prithvi Hugging Face model card (IBM/NASA, Apache-2.0) | https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-1.0-100M-multi-temporal-crop-classification
USGS 3DEP Elevation Point Query Service | https://apps.nationalmap.gov/epqs/
NOAA National Weather Service API | https://www.weather.gov/documentation/services-web-api
Open-Meteo Climate API (CC BY 4.0) | https://open-meteo.com/en/docs/climate-api
US Census cartographic boundary files | https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html
Esri World Imagery basemap (© Esri, Maxar, Earthstar Geographics, GIS User Community) | https://www.arcgis.com/home/item.html?id=10df2279f9684e4a9f6a7f08febac2a9
Esri terms of use | https://www.esri.com/en-us/legal/terms/full-master-agreement
Leaflet (BSD-2-Clause) | https://leafletjs.com/
Chart.js (MIT) | https://www.chartjs.org/
Tailwind CSS (MIT) | https://tailwindcss.com/
Inter font (SIL OFL 1.1) | https://fonts.google.com/specimen/Inter
FastAPI (MIT) | https://fastapi.tiangolo.com/
Uvicorn (BSD-3-Clause) | https://uvicorn.dev/
Starlette (BSD-3-Clause) | https://starlette.dev/
Pydantic (MIT) | https://docs.pydantic.dev/
NumPy (BSD-3-Clause) | https://numpy.org/
pg8000 (BSD-3-Clause) | https://codeberg.org/tlocke/pg8000
openai-python client (Apache-2.0) | https://github.com/openai/openai-python
HTTPX (BSD-3-Clause) | https://www.python-httpx.org/
Requests (Apache-2.0) | https://requests.readthedocs.io/
websockets (BSD-3-Clause) | https://websockets.readthedocs.io/
pandas (BSD-3-Clause) | https://pandas.pydata.org/
GeoPandas (BSD-3-Clause) | https://geopandas.org/
Shapely (BSD-3-Clause) | https://shapely.readthedocs.io/
pyogrio (MIT) | https://pyogrio.readthedocs.io/
rasterio (BSD-3-Clause) | https://rasterio.readthedocs.io/
xarray (Apache-2.0) | https://docs.xarray.dev/
h5py (BSD-3-Clause) | https://www.h5py.org/
earthaccess (MIT) | https://github.com/nsidc/earthaccess
psycopg (LGPL-3.0) | https://www.psycopg.org/
PostgreSQL (PostgreSQL Licence) | https://www.postgresql.org/
PostGIS (GPL-2.0) | https://postgis.net/
pgvector (PostgreSQL Licence) | https://github.com/pgvector/pgvector
pytest (MIT) | https://docs.pytest.org/
Ruff (MIT) | https://docs.astral.sh/ruff/
MATLAB (MathWorks, student licences) | https://www.mathworks.com/products/matlab.html
OpenAI gpt-4o-miniAPI (gpt-4o-mini) | https://api-docs.OpenAI.com/
Claude Code coding assistant (Anthropic) | https://code.claude.com/docs/en/overview
Codex CLI coding assistant (OpenAI) | https://github.com/openai/codex
AI-generated images and logo (tool: TODO(Hylē): tool name) | TODO(Hylē): tool URL
```

The last row needs the generation tool name and its official URL from Hylē before pasting.
