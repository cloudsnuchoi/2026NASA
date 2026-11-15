# ART FARM — Data and resources

Links checked from the team VPS on 2026-11-15 ~19:20 KST with `curl -I -L` (HEAD), then a plain GET when HEAD was refused. "200" means the final response was HTTP 200. Some NASA Earthdata pages return 403 to non-browser clients from our server. For those we list a page that returned 200 and note the other one.

## NASA data

| Dataset | What we used it for | Official URL | Check |
| --- | --- | --- | --- |
| NASA POWER (daily, AG community) | Tier 1 Quick Screen weather (10 yr, live per point); Tier 2 daily weather for 1,122 Corn Belt counties, 1995–2025; FAO-56 reference ET | https://power.larc.nasa.gov/ · docs https://power.larc.nasa.gov/docs/ | 200 · 200 |
| HLS v2.0 (HLSL30 / HLSS30) | NDVI time series and bare-soil periods for pilot fields; input chips for Prithvi | https://hls.gsfc.nasa.gov/ · DOIs 10.5067/HLS/HLSL30.002, 10.5067/HLS/HLSS30.002 | 200 (hls.gsfc) · doi.org and earthdata.nasa.gov returned 403 from VPS (bot filter; open in a browser) |
| SMAP L3 Radiometer Soil Moisture (SPL3SMP v009, 36 km) | County context cell only, never field-precise | https://nsidc.org/data/spl3smp/versions/9 | 200 |
| GPM IMERG Final daily V07 (GPM_3IMERGDF) | County precipitation context 2001–2025, cross-check against POWER | https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDF_07/summary · https://gpm.nasa.gov/data/imerg · DOI 10.5067/GPM/IMERGDF/DAY/07 | 200 · 200 · doi.org 403 from VPS |
| NLDAS-2 Noah monthly (NLDAS_NOAH0125_M v2.0) | County root-zone soil moisture context 1995–2025 | https://disc.gsfc.nasa.gov/datasets/NLDAS_NOAH0125_M_2.0/summary · https://ldas.gsfc.nasa.gov/nldas/v2/models | 200 · 200 |
| GEOS-S2S-3 (NASA GMAO) | Next-season ensemble range (10 members, MAM and Jun–Jul 2027) | https://gmao.gsfc.nasa.gov/cms/geos-s2s/ · data https://portal.nccs.nasa.gov/datashare/gmao/geos-s2s-3/ | 200 (GET; HEAD 405) · 200 |
| NEX-GDDP-CMIP6 | 2030s climate ranges (ACCESS-CM2, MPI-ESM1-2-HR; SSP2-4.5, SSP5-8.5) | https://www.nccs.nasa.gov/services/data-collections/land-based-products/nex-gddp-cmip6 · https://registry.opendata.aws/nex-gddp-cmip6/ | 200 · 200 |
| Prithvi-EO-1.0-100M multi-temporal crop classification (NASA/IBM, Apache-2.0) | Crop-type inference on 20 pilot fields, 2024 (no fine-tuning) | https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-1.0-100M-multi-temporal-crop-classification | 200 |

## Other data and services

| Resource | What we used it for | URL | Check |
| --- | --- | --- | --- |
| USDA NASS Cropland Data Layer (CDL) 2008–2025 | Field crop history, county crop shares, Prithvi comparison | https://www.nass.usda.gov/Research_and_Science/Cropland/SARS1a.php | 200 (CropScape app redirects to a sign-in page from our server, so we cite this page) |
| USDA NASS Crop Sequence Boundaries (CSB) 2018–2025 | Field polygons; `field_id` = CSBID | https://www.nass.usda.gov/Research_and_Science/Crop-Sequence-Boundaries/index.php | 200 |
| USDA NRCS SSURGO via Soil Data Access | Soil available water capacity, K factor, organic matter, drainage class | https://sdmdataaccess.sc.egov.usda.gov/ · https://websoilsurvey.nrcs.usda.gov/ | 200 · 200 (nrcs.usda.gov SSURGO page timed out from VPS) |
| USDA NASS Quick Stats (bulk file) | County corn and soybean yield (bu/ac) as context | https://www.nass.usda.gov/datasets · https://quickstats.nass.usda.gov/ | 200 · 200 |
| USGS 3DEP (Elevation Point Query Service) | Quick Screen elevation | https://www.usgs.gov/3d-elevation-program · https://epqs.nationalmap.gov/v1/docs | 200 · 200 (GET; HEAD 403) |
| NOAA National Weather Service API (`/points`) | Quick Screen point metadata and near-term weather context | https://www.weather.gov/documentation/services-web-api · https://api.weather.gov/ | 200 · 200 |
| Open-Meteo Climate API (CMIP6 model MRI_AGCM3_2_S) | Quick Screen future-climate context. Must be shown as a range, not a year-by-year forecast (see si-use.md L1 gaps) | https://open-meteo.com/en/docs/climate-api | 200 |
| Esri World Imagery (basemap) | Quick Screen satellite basemap | https://www.arcgis.com/home/item.html?id=10df2279f9684e4a9f6a7f08febac2a9 · https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer | 200 · 200 |
| OpenET (Ensemble, monthly) | Field ET 2016–2025 to scale the crop coefficient per field | https://openet-api.org/ | 200 (GET; HEAD 405). Project site etdata.org did not answer from VPS — check in a browser |
| US Census cartographic boundary files (cb_2023_us_county_500k) | County polygons for the 12 Corn Belt states | https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html | 200 |
| FAO-56 (Allen et al. 1998), FAO Irrigation and Drainage Paper 56 | Method: Penman–Monteith ET0, crop coefficients, water stress | https://www.fao.org/3/x0490e/x0490e00.htm | 200 |
| DeepSeek API (LLM) | `/explain` tool-calling explainer; team chat bot | https://api-docs.deepseek.com/ | 200 |

### Pending (only add if the final UI cites it)

| Resource | Why pending | URL | Check |
| --- | --- | --- | --- |
| USDA ERS Commodity Costs and Returns | The Quick Screen price/yield/cost table must get a USDA ERS/NASS source and year (directive). Not cited in the UI yet. If L1 cites a different ERS or NASS table, replace this row. | https://www.ers.usda.gov/data-products/commodity-costs-and-returns/ | 200 |

Searched but not used in the product: NAIP imagery (search only, no tiles stored). Not used: ECOSTRESS, hyperspectral data, drone data.

## Citation notes

- NASA POWER: "These data were obtained from the NASA Langley Research Center (LaRC) POWER Project funded through the NASA Earth Science/Applied Science Program."
- OpenET: Melton et al. (2022). Check the OpenET API terms before publishing derived data.
- NEX-GDDP-CMIP6: file attributes state `cmip6_license: CC-BY-SA 4.0`; cite the NCCS technical note.
- NLDAS-2 Noah monthly DOI was not in the file attributes. It has not been confirmed, so we do not list one.
- No NASA logos, flags or mission insignia are used anywhere in ART FARM.
