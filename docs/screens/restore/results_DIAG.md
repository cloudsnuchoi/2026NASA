# Results page — diagnosis & restore (lane RESULTS, 2026-11-15 KST)

Status: **READY** (frontend only: `frontend/app.js`, `frontend/index.html`; no engine / model_api change).

## How it was measured
Playwright (Chromium) on a local uvicorn `infra.web.app:app` at `127.0.0.1:8099` serving this worktree, upstream model API `http://127.0.0.1:8090` (live path — `ARTFARM_STATIC` not set, no snapshot used).
Each case: map page → preset button (or 4 custom corners via a test hook `window.__artfarmTest.addVertex`) → Change crops → Confirm → results page. Every `/api/{quick,simulate,strategies,explain}` response was captured and compared with the rendered DOM.
Custom field: 41.302,-89.404 / 41.302,-89.396 / 41.297,-89.396 / 41.297,-89.404. `/explain` is only called on a button click and `/strategies` is not used by this page, so neither appears.

## Results (API response vs displayed)
"Match" = every scenario row in the comparison table shows the response's deficit (mm) and water-use index for the same candidate, in the same order.

| Case | Crops | /api calls (status) | quick: elev m · precip mm/yr | Scenarios (seq: ETc / deficit mm / water idx) — response | Displayed table rows | Match | /simulate A–D deficit P50 [P10–P90] CVaR10 (mm/yr) | Tier-2 shown |
|---|---|---|---|---|---|---|---|---|
| Story IA | Corn+Soy | quick(200) simulate(200) | 295.9 · 821 | Corn-Soy: 551 / 171 / 95.1<br>Soy-Corn: 551 / 171 / 95.1 | [1번 결과] Corn → Soybean 551 mm 171 mm 95.1 not estimated<br>[2번 결과] Soybean → Corn 551 mm 171 mm 95.1 not estimated | ✓ | A: 163 [95–236] 270<br>B: 162 [93–233] 267<br>C: 109 [52–186] 208<br>D: 129 [57–211] 250 | run mc-68d334b160099d92-n5 ✓ |
| Story IA | Corn+Soy+Wheat | quick(200) simulate(200) quick(200) | 295.9 · 821 | Corn-Soy-Wheat: 531 / 126 / 91.6<br>Soy-Wheat-Corn: 531 / 126 / 91.6<br>Wheat-Corn-Soy: 531 / 126 / 91.6 | [1번 결과] Corn → Soybean → Wheat 531 mm 127 mm 91.6 not estimated<br>[2번 결과] Soybean → Wheat → Corn 531 mm 127 mm 91.6 not estimated<br>[3번 결과] Wheat → Corn → Soybean 531 mm 127 mm 91.6 not estimated | ✓ | A: 163 [95–236] 270<br>B: 162 [93–233] 267<br>C: 109 [52–186] 208<br>D: 129 [57–211] 250 | run mc-68d334b160099d92-n5 ✓ |
| McLean IL | Corn+Soy | quick(200) simulate(200) | 209.3 · 973 | Corn-Soy: 527 / 144 / 95.1<br>Soy-Corn: 527 / 144 / 95.1 | [1번 결과] Corn → Soybean 527 mm 144 mm 95.1 not estimated<br>[2번 결과] Soybean → Corn 527 mm 144 mm 95.1 not estimated | ✓ | A: 129 [86–190] 215<br>B: 128 [83–185] 210<br>C: 87 [49–135] 162<br>D: 86 [50–146] 175 | run mc-efb7a222064be1a6-n5 ✓ |
| McLean IL | Corn+Soy+Wheat | quick(200) simulate(200) quick(200) | 209.3 · 973 | Corn-Soy-Wheat: 514 / 96 / 92.9<br>Soy-Wheat-Corn: 514 / 96 / 92.9<br>Wheat-Corn-Soy: 514 / 96 / 92.9 | [1번 결과] Corn → Soybean → Wheat 515 mm 96 mm 92.9 not estimated<br>[2번 결과] Soybean → Wheat → Corn 515 mm 96 mm 92.9 not estimated<br>[3번 결과] Wheat → Corn → Soybean 515 mm 96 mm 92.9 not estimated | ✓ | A: 129 [86–190] 215<br>B: 128 [83–185] 210<br>C: 87 [49–135] 162<br>D: 86 [50–146] 175 | run mc-efb7a222064be1a6-n5 ✓ |
| Lancaster NE | Corn+Soy | quick(200) simulate(200) | 354.6 · 771 | Corn-Soy: 610 / 227 / 95.0<br>Soy-Corn: 610 / 227 / 95.0 | [1번 결과] Corn → Soybean 610 mm 227 mm 95.0 not estimated<br>[2번 결과] Soybean → Corn 610 mm 227 mm 95.0 not estimated | ✓ | A: 299 [227–400] 440<br>B: 301 [224–401] 442<br>C: 227 [150–325] 359<br>D: 293 [199–405] 459 | run mc-5e734b69b7caf6a7-n5 ✓ |
| Lancaster NE | Corn+Soy+Wheat | quick(200) simulate(200) quick(200) | 354.6 · 771 | Corn-Soy-Wheat: 597 / 193 / 93.1<br>Soy-Wheat-Corn: 597 / 193 / 93.1<br>Wheat-Corn-Soy: 597 / 193 / 93.1 | [1번 결과] Corn → Soybean → Wheat 597 mm 193 mm 93.1 not estimated<br>[2번 결과] Soybean → Wheat → Corn 597 mm 193 mm 93.1 not estimated<br>[3번 결과] Wheat → Corn → Soybean 597 mm 193 mm 93.1 not estimated | ✓ | A: 299 [227–400] 440<br>B: 301 [224–401] 442<br>C: 227 [150–325] 359<br>D: 293 [199–405] 459 | run mc-5e734b69b7caf6a7-n5 ✓ |
| Custom 41.30,-89.40 | Corn+Soy | quick(200) | 143.9 · 977 | Corn-Soy: 501 / 113 / 95.1<br>Soy-Corn: 501 / 113 / 95.1 | [1번 결과] Corn → Soybean 501 mm 113 mm 95.1 not estimated<br>[2번 결과] Soybean → Corn 501 mm 113 mm 95.1 not estimated | ✓ | — | — (not a pilot field) |
| Custom 41.30,-89.40 | Corn+Soy+Wheat | quick(200) quick(200) | 143.9 · 977 | Corn-Soy-Wheat: 486 / 75 / 92.3<br>Soy-Wheat-Corn: 486 / 75 / 92.3<br>Wheat-Corn-Soy: 486 / 75 / 92.3 | [1번 결과] Corn → Soybean → Wheat 486 mm 75 mm 92.3 not estimated<br>[2번 결과] Soybean → Wheat → Corn 486 mm 75 mm 92.3 not estimated<br>[3번 결과] Wheat → Corn → Soybean 486 mm 75 mm 92.3 not estimated | ✓ | — | — (not a pilot field) |

Tier-2 numbers: /simulate deficit P50 [P10–P90] and CVaR10 come from `metrics.season_water_deficit_mm` (mm/yr, CVaR = mean of the worst 10 %); the Tier-2 block renders the run_id of that same response (✓).

## Proof that presets give different numbers (Corn+Soy+Wheat, candidate 1)
| Field | Elevation (3DEP) | 10-yr precip | ETm | Deficit | Water idx | /simulate A deficit P50 | CVaR10 |
|---|---|---|---|---|---|---|---|
| Story IA | 295.9 m | 821 mm | 531 mm | 126 mm | 91.6 | 163 mm (95–236) | 270 mm |
| McLean IL | 209.3 m | 973 mm | 514 mm | 96 mm | 92.9 | 129 mm (86–190) | 215 mm |
| Lancaster NE | 354.6 m | 771 mm | 597 mm | 193 mm | 93.1 | 299 mm (227–400) | 440 mm |
| Custom 41.30,-89.40 | 143.9 m | 977 mm | 486 mm | 75 mm | 92.3 | — (not pilot) | — |

## Diagnosis
- **No frontend state bug found.** Displayed numbers equal the response for all 8 runs, and differ between Story / McLean / Lancaster / custom. No snapshot path on live, no first-result reuse across fields, no hard-coded defaults. Page errors: none.
- Corn+Soy runs make only one `/quick` call: the map-page baseline call (`crops: [Corn, Soy]`, same polygon) is reused. This is the identical request body, so it is correct; any other crop set issues a fresh `/quick`.
- **Why scenarios look identical within one field:** the engine returns the same ETc / deficit / index for every permutation of the same crop set (e.g. Corn→Soy vs Soy→Corn), because it averages seasonal per-crop values; order effects (N credit, residue) are not modelled. This is an engine property, not a display bug; the page states it in the trade-off box. Changing it is out of scope (no engine changes in this lane).

## Restore (mockup v8 results structure)
- Title `맞춤형 윤작 시나리오 추천 결과 (N개 시나리오 · 순위 미적용)` + English subtitle; source banner, Change Crops / Start Over kept; "Screening estimate" and "A decision aid — it does not replace your judgement" kept.
- Left: Selected Crops (선택 작물), STEP 1~2 (area, 3DEP elevation, 10-yr temp/precip, ET₀, drought-year ratio, NDVI (pilot HLS peak or "not estimated") / root-zone wetness), STEP 3 climate table (past / near-term NWS / scenario periods), **STEP 5 area allocation** (unranked equal split of the measured area; net profit and N need "not estimated"), Tier-2 deep-analysis card.
- Main: STEP 4 tabs `[N번 결과]`, scenario card with mockup KPI slots — ETm (+deficit), 단작 대비 물 사용 (= index − 100, relative), Soil OM change **not estimated** (shows current gSSURGO OM for pilot fields as context), 2030s stability **not estimated** (substitute: scenario-range deficit P50); net-profit slot "not estimated" with the water-use index beneath; pros/cons; prescription box (slope/fertilizer "not estimated", 3DEP centroid + info gaps); all-scenarios table (profit column "not estimated"); Before/After photos with AI-generated label; 4-panel charts; V8 report accordion. Tier-2 strategies A–D (P10–P90, CVaR, 2012, /explain) unchanged below.

## Screens
- `results_live_1280.png`, `results_live_390.png` (Story IA, Corn+Soy+Wheat, live API), `results_live_1280_custom.png` (custom field, Corn+Soy).
- `results_mockup_1280.png`, `results_mockup_390.png` — mockup-v8 results page opened directly; its render function is closure-scoped, so the slots are empty (structure only).

## Checks
- `pytest data_pipeline/tests`: 101 passed. `ruff check .`: all checks passed. `tools/test_static_demo.py`: 1 skipped (environment), and `docs/demo` was not touched (sync_demo.sh not run).
- `node` syntax check of `frontend/app.js`: OK.
