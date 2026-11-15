# PORT lane — team mockup V8 results dashboard → live #results

Baseline (mockup, Iowa/Story sample, Corn+Soy+Wheat): `port_baseline_1280.png`
Port (local uvicorn :8098 → model API :8090, Corn+Soy+Wheat): `port_live_1280.png` (Story 19169), `port_live_mclean_1280.png` (McLean 17113)

What was ported: mockup `page-results` body (HTML, verbatim → `frontend/mockup_results.html`) and its script
(CROP_DB/constants/state, `runFieldShiftLiveApiEngine`, `computeFaoRotationCards`, `optimizeCropAllocation`,
`renderResultsDashboard`, `renderBeforeAfterPhotos`, `drawMatlab`, `drawTile*`, `renderConsoleReport` + helpers, verbatim →
`frontend/mockup_results.js`). Binding lives in `renderPorted()` in `frontend/app.js`. Tier-2 Deep Analysis (A–D, /explain) stays below.

| Value | Story (19169) | McLean (17113) | Source |
| --- | --- | --- | --- |
| Area | 28.72 ha (71.0 ac) | 52.41 ha (129.5 ac) | engine (/api/quick geometry, WGS84 shoelace) |
| Elevation median (min~max) | 295.89m (292.19~299.99m) | 209.32m (205.62~213.42m) | median = engine USGS 3DEP centroid; min/max relief = prototype grid shifted to centroid (prototype estimate) |
| 10-yr mean temp / precip | 10.15°C / 821.4 mm/yr | 11.46°C / 973.3 mm/yr | engine (NASA POWER per_year) |
| 10-yr ET0 | 942.2 mm/yr | 929.5 mm/yr | engine (FAO-56 PM per_year) |
| ETm (active scenario) | 772 mm/yr | 762 mm/yr | engine mean_season_etc_mm where sequence matches a /api/quick candidate; else mockup formula on engine ET0 |
| Net profit (USDA ERS constants) | $22,901 | $41,948 | prototype estimate (team V8) |
| Soil organic matter index | +13.3% | +13.3% | prototype estimate (team V8) |
| 2030s stability % | 92.3% | 107.5% | prototype estimate (team V8) |
| STEP 5 allocation | 옥수수 20.0% (5.7 ha) \| 대두(콩) 56.8% (16.3 ha) \| 밀 23.2% (6.7 ha) | 옥수수 20.0% (10.5 ha) \| 대두(콩) 60.0% (31.4 ha) \| 밀 20.0% (10.5 ha) | prototype estimate (team V8) |
| Pilot-field deficit P10–P90 / CVaR10% | Pilot-field engine: deficit P10–P90 95–236 mm, CVaR10% 270 mm (n=500 seasons) | Pilot-field engine: deficit P10–P90 86–190 mm, CVaR10% 215 mm (n=500 seasons) | engine (/api/simulate, n=500, seed 42) |

Binding notes
- The 10-yr series (temp, precip, ET0, root-zone wetness) is injected before the mockup's own drought/regression/scenario steps, so its trend, 2030s epochs and scenario math run on engine numbers. The mockup's 2030s trend extrapolation and the NDVI series are still its own (prototype).
- The mockup also calls external APIs (USGS EPQS grid, NASA POWER) itself; climate is overwritten by the engine series, elevation is re-anchored to the engine centroid.
- `/api/quick` returns centroid elevation only, so min/max are the prototype relief shifted to the centroid.

Checks: pytest data_pipeline/tests tools 111 passed / 1 skipped; ruff clean; `tools/test_static_demo.py` not run (pytest missing from /srv/hackathon/venv; it tests docs/demo, which this lane did not change).
