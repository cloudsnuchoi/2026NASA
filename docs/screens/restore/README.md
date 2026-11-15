# RESTORE lane — mockup v8 vs static demo vs live (2026-11-15 21:20 KST)

Reference: UI/UX team final mockup `mockup-v8.html` (inbox). Captures: `tools/capture_restore.py`
(Playwright Chromium, viewport captures 1280×900 and 390×844 touch; demo = `docs/` served locally,
live = `infra/web/app.py` on 127.0.0.1:8098). Our runs use the Story IA preset with Corn + Soybean.

| Step | Files | Difference vs mockup |
| --- | --- | --- |
| map | `{mockup,demo,live}-map-{1280,390}.png` | Same header + preset button row, left "Regional Baseline (NASA POWER)" + "Parcel Measurement (WGS84 + USGS 3DEP)" panels, "Select Crops" button, right map card + legend. Intentional: preset buttons are our 4 pilot counties (Story IA, McLean IL, Lancaster NE, Union OH) instead of Iowa/Nebraska/Illinois samples; the clear zone is the Corn Belt screening box (36–48°N, 80–104°W) with the translucent blue mask outside (mockup: a circle); baseline values come from `/quick` (NASA POWER 2015–2024 at the centroid), shown "—" until a field is drawn; "Mean NDVI / Soil Moist" → "Root-zone wetness" (what POWER returns; NDVI only exists for pilot fields, shown in results); elevation is the 3DEP centroid point only (no min/max/slope, we do not query a DEM grid); extra "Analysis tier" row and "Pilot demo field" legend item. |
| crops | `*-crops-*.png` | Same 3 cards, selected-slot bar, reset and "Confirm Selection". Intentional: card line shows FAO-56 Table 12 Kc ini/mid/end (mockup Ky and N-fixation numbers are not computed by our engine, removed); English text. |
| results | `*-results-*.png` | Same source bar, header, left column (Selected Crops, Step 1–2 3DEP & POWER, Step 3 climate table, dark Step 5 card) and right column (Step 4 scenario tabs, active scenario card, KPI strip, pro/con, local-check box, all-scenarios table, before/after photos, 4 chart tiles, engine report). Intentional fact corrections: engine label "FAO-56 engine (ported from team MATLAB prototype V8)"; source bar lists what we call (USGS 3DEP EPQS, NASA POWER, NOAA/NWS, Open-Meteo Climate API CMIP6, FAO-56) — USDA ERS removed because no price is used; no profit ($), "optimal allocation solver", soil-organic-matter % or "2030s stability %" (no sourced numbers) — replaced by the water-use index (continuous corn = 100), ETc, irrigation deficit, years with deficit and scenario-range deficit from `/quick`; Step 5 card shows Deep Analysis (Prithvi-EO, USDA CDL, gSSURGO, HLS NDVI) instead of a single optimum; tile ① is the measured field outline (no DEM contours); tile ④ is the precipitation P10–P90 possible range; photos are labelled illustrative/AI-generated. |
| compare | `*-compare-*.png` | Mockup has no strategy section; its all-scenarios table is captured. Ours: Tier 2 strategy comparison A–D in the same card language (dark source bar, white rounded-3xl card with the P10–P90 / P50 / CVaR 10% / 2012 backtest chart, four strategy cards with why, evidence, benefits, trade-offs, info gaps, check-locally, /explain button), then Information gaps and the S7 checklist. Not ranked; "D = reference". |

Other intentional differences (all steps):
- English UI (the story section was already English); ART FARM brand.
- Static demo only: a small "📦 static snapshot · live server" badge inside each page header (replaces the old banner that covered content).
- On touch screens buttons keep the 44 px minimum (UX audit F4); desktop uses the mockup sizes.

Remaining non-intentional differences: none found at 1280 / 390 in these captures (text length differs where the copy was translated).
