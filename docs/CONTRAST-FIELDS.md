# Contrast demo fields (2026-11-15, data lane `feat/contrast-fields`)

## Problem

The 12 Story County (IA 19169) demo fields gave almost the same answers. They share one county POWER weather point, and 9 of the 12 sit on Clarion–Nicollet–Webster-type map units with nearly the same AWC (0.182–0.183). Across the 12 Story fields, strategy A composite P50 spans only 0.480–0.494 (range 0.014).

## What was added

8 CSB fields in 3 more Corn Belt counties, each with its own county POWER point (already in `county_weather_daily`), plus IMERG and NLDAS county rows (already loaded). The fields were chosen for contrasting soils within each county.

| County | Why this county (POWER 1995–2025, from DB) |
| --- | --- |
| **McLean, IL (17113)** | Wetter (974 mm/yr vs Story 841). Highest strict corn–soy alternation in the spike (49.2 % vs Story 28.5 %). Same latitude band, different soils (Drummer/Osco/Wyanet). |
| **Lancaster, NE (31109)** | Drier, hotter western edge (735 mm/yr, JJA Tmax 30.6 °C vs 28.7). 2012 precipitation was 474 mm (Story 585). Loess and claypan soils (Wymore, Aksarben). |
| **Union, OH (39159)** | Eastern, wet, cool (953 mm/yr, JJA Tmax 27.5 °C). Wet in 2012 (873 mm), so the drought backtest year goes the opposite way. Poorly drained till soils (Brookston/Blount/Pewamo). |

How fields were chosen (`data_pipeline/contrast_soil_probe.py`): CSB 2018–2025 rev23 polygons of 25–80 ha, corn or soy in all 8 CSB years, and compactness 4πA/P² > 0.6 (no slivers or strips). From a random sample of 14 per county I took the SSURGO area-dominant map unit (SDA spatial intersection) and kept fields on different map units with different drainage and AWC.

| field_id (CSBID) | County | ha | Dominant SSURGO component (mukey, share) | OM % | K | AWC cm/cm | Drainage | CDL 2008–2025 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 171825001292309 | McLean IL | 52.4 | Osco (199067, 0.33) | 2.58 | 0.366 | 0.229 | Well | SCSC… strict alternation |
| 171825006921423 | McLean IL | 56.8 | Drummer (620960, 0.36) | 5.54 | 0.240 | 0.185 | Poorly | CSCSCSCCCSCCCCCSCC (mostly corn) |
| 171825006923844 | McLean IL | 47.2 | Wyanet (199133, 0.46) | 2.68 | 0.315 | 0.143 | Well | CSCS… strict alternation |
| 311825001242480 | Lancaster NE | 64.1 | Aksarben (2733103, 0.54) | 3.39 | 0.317 | 0.166 | Well | CSCS… |
| 311825002820374 | Lancaster NE | 50.4 | Wymore (1691404, 0.65) | 2.93 | 0.321 | 0.213 | Mod. well | SCSC… |
| 311825008109480 | Lancaster NE | 29.3 | Yutan (2219244, 0.57) | 2.71 | 0.320 | 0.161 | Well | CSCSCSCSCSCSCCCCSC |
| 391825000729943 | Union OH | 29.7 | Brookston (1406060, 0.95) | 3.80 | 0.292 | 0.157 | Poorly | CSCS… |
| 391825009407249 | Union OH | 33.5 | Fox (1406067, 0.41) | 2.06 | 0.416 | 0.179 | Well | SCSCSCCSCS… |

The list is in `data_pipeline/contrast_fields.json`.

## What was loaded (insert-only, `ON CONFLICT DO NOTHING`, no existing row touched)

| Table | Rows | Source / method |
| --- | --- | --- |
| `fields` | 8 | National CSB 2018–2025 rev23 gdb, `field_id = CSBID`, area in EPSG:5070, stored in EPSG:4326, `centroid` = ST_PointOnSurface |
| `field_soil` | 8 | SSURGO via Soil Data Access: area-dominant mapunit by spatial intersection, comppct-weighted surface-horizon om_r, kffact, awc_r, dominant-component drainagecl (same aggregation as `ssurgo_story.py`) |
| `field_crop_history` | 144 (8 × 18 yrs, 2008–2025) | CropScape `GetCDLFile` county clips (`data_pipeline/cdl_cropscape_county.py`, raw at `raw/cdl/tier2_<fips>/`), zonal majority class + share |
| `field_et_openet` | 960 (8 × 120 months, 2016-01..2025-12) | OpenET Ensemble monthly ET, point API at the field centroid, gridMET reference (same call as `openet_story.py`); raw JSON in `raw/openet/tier2_contrast/` |
| `field_ndvi_hls` | 1,997 (2023: 657, 2024: 639, 2025: 701) | HLS v2.0 L30/S30 NDVI Apr–Nov, Fmask bits 1–5 masked, polygon mean (reuses the `hls_story.py` reader per county bbox) |

HLS clear scenes (valid_frac ≥ 0.8) per field-year range from 22 to 70, well above the 8 required. 82 granule reads raised transient `RasterioIOError` and were skipped, as in the Story run. Rows are one per field, date and product; overlapping MGRS tiles on the same date collapse into one row via the primary key.

Steps: `python data_pipeline/contrast_fields.py fields | cdl | openet | hls YEAR` (needs PG* env; `openet` needs `OPENET_API_KEY`). Request rate: CropScape and SDA ≤ 1 req/s, OpenET 1 req/s.

## model_api change (smallest one)

Demo fields were, and still are, "fields with an OpenET series" (`repo.demo_field_ids`), so the new fields are registered by their OpenET rows. Changes:
- `GET /fields`: demo fields are ordered with Story first, then by county. Each field gets `county_label` (e.g. `McLean County, IL (17113)`), and the response gets `counties: [{county_fips, county_label, n_fields}]`. Both are additive keys; the top-level `county_fips` stays `19169`.
- Tests: `test_integration_db.py` and `test_e2e_live.py` now expect 12 Story fields first (≥ 12 total), not exactly 12. New `model_api/tests/test_contrast_fields.py` checks ≥ 3 counties among demo fields and that strategy A composite P50 differs by > 0.02 between at least two demo fields. It is skipped if the DB is unreachable.

## Results (model_api on 127.0.0.1:8098, N = 500, seed 42, default priorities)

Every new field returned 200 on `/fields`, `/field/{id}/profile`, `/strategies/compare`, `/simulate` and `/validation/backtest?year=2012`. Script: `notebooks/contrast_fields_verify.py`.

| field_id | County | AWC | Kc scale (OpenET) | A sequence | Composite P50 A / B / C / D | MC season deficit P50 mm A / B / C / D | 2012 backtest deficit mm A / B / C / D |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 191825003869023 | Story IA | 0.183 | 1.169 | C-S | 0.482 / 0.569 / 0.551 / 0.526 | 188 / 187 / 130 / 154 | 463 / 451 / 366 / 513 |
| 191825002945908 | Story IA | 0.183 | 1.189 | C-S | 0.480 / 0.567 / 0.550 / 0.523 | 197 / 196 / 136 / 162 | 550 / 534 / 378 / 529 |
| 171825001292309 | McLean IL | 0.229 | 1.158 | C-S | 0.484 / 0.584 / 0.569 / 0.533 | 129 / 128 / 87 / 86 | 431 / 415 / 281 / 351 |
| 171825006921423 | McLean IL | 0.185 | 1.190 | C-C-C-C-C-S | 0.504 / 0.582 / 0.563 / 0.542 | 149 / 149 / 117 / 128 | 384 / 369 / 332 / 403 |
| 171825006923844 | McLean IL | 0.143 | 1.217 | C-S | 0.484 / 0.573 / 0.557 / 0.526 | 203 / 201 / 150 / 169 | 430 / 415 / 381 / 455 |
| 311825001242480 | Lancaster NE | 0.166 | 1.184 | C-S | 0.449 / 0.536 / 0.520 / 0.488 | 299 / 301 / 227 / 293 | 636 / 633 / 544 / 724 |
| 311825002820374 | Lancaster NE | 0.213 | 1.095 | C-S | 0.460 / 0.546 / 0.531 / 0.499 | 224 / 226 / 163 / 210 | 601 / 631 / 454 / 611 |
| 311825008109480 | Lancaster NE | 0.161 | 1.25 (clip) | C-S-C-C-C | 0.447 / 0.534 / 0.513 / 0.481 | 326 / 325 / 260 / 339 | 693 / 689 / 596 / 789 |
| 391825000729943 | Union OH | 0.157 | 1.25 (clip) | C-S | 0.489 / 0.574 / 0.559 / 0.527 | 212 / 209 / 152 / 174 | 286 / 276 / 250 / 300 |
| 391825009407249 | Union OH | 0.179 | 1.204 | C-S | 0.475 / 0.579 / 0.564 / 0.518 | 179 / 176 / 125 / 137 | 327 / 315 / 212 / 256 |

Spread for strategy A, all 12 Story fields vs the 8 contrast fields:

| Metric (strategy A) | Story 12 fields | Contrast 8 fields |
| --- | --- | --- |
| Composite P50 | 0.480–0.494 (range 0.014) | 0.447–0.504 (range 0.057) |
| MC season deficit P50 | 144–197 mm (range 53) | 129–326 mm (range 196) |
| 2012 backtest deficit | 400–550 mm (range 150) | 286–693 mm (range 407) |

How to read it: Lancaster NE is the dry end, with the largest deficits and the lowest composite. Union OH had a wet 2012, so its 2012 deficits are the smallest. McLean's high-AWC Osco field has the smallest MC deficit. Strategy C (with wheat) still has the lowest deficit in every county. These are relative indices, not guarantees, and not yield.

## Caveats (do not hide)

- Weather is still one county POWER point, so fields within one county share weather. Differences within a county come from SSURGO AWC/K, CDL sequence and the OpenET Kc scale.
- The crop calendar and stage dates are the team's Iowa defaults (`model_api/README.md`), applied unchanged to IL, NE and OH. That is an assumption, not a local calendar.
- 311825008109480 (Lancaster) has higher OpenET Jun–Sep ET than its neighbours in the 2023 drought (584 mm vs 389/457), and its Kc scale hits the 1.25 clip. It **may be irrigated**. Irrigation status is `미확인` (CSB has no irrigation flag; not checked against other sources). The engine is rainfed, so treat this field's deficit as an upper bound. Union OH 391825000729943 also hits the 1.25 clip.
- Two fields (311825001242480, 391825000729943) are within 0.4 km of the county boundary. They are not near water and are compact, and weather is county-level anyway.
- SSURGO "share" is the dominant map unit's share of the field area (0.33–0.95); a field is not uniform.
- OpenET terms: cite OpenET (Melton et al. 2022); check the API terms before publishing derived data (same as Story).
