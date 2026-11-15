# ART FARM — Field Shift: Adapting Farms with NASA Data

Team **Amolra (아몰라)** · NASA Space Apps Challenge 2026 · Challenge: *Field Shift: Adapting Farms with NASA Data*

> Draft for the official submission page (status: 2026-11-15 20:00 KST draft). Public text only above the `SOURCES` comment at the end. Every number in the public text is listed in that comment with its source.

---

## Project Name

ART FARM

## Summary

<!-- word count: 162 words (counted with `wc -w` on the paragraph below; rechecked 22:00 KST, v3) -->

ART FARM (Field Shift: Adapting Farms with NASA Data) helps Corn Belt farmers compare crop rotations for soil health and weather and water resilience without being told what to plant. It has two tiers. Quick Screen works anywhere in the Corn Belt: the farmer clicks four corners and gets a screening estimate built from ten years of NASA POWER weather, USGS elevation and FAO-56 crop water formulas. Deep Analysis covers 20 pilot fields in four counties (Iowa, Illinois, Nebraska, Ohio). There, a Monte Carlo water-balance engine compares four strategies: corn-soybean, plus a rye cover, plus a small grain, or plus alfalfa. Results come as P10–P90 ranges with a worst-10% tail (CVaR), a replay of the real 2012 drought, and climate ranges from NASA GEOS-S2S and NEX-GDDP-CMIP6. NASA's Prithvi model checks crop labels against USDA maps. An AI explainer may only quote numbers that the engine returned. Every card lists drawbacks, information gaps and a reminder to confirm with a field soil test.

## Project Details

- Live (dynamic engine on our server): https://watts-astrology-asus-blessed.trycloudflare.com
- Backup (static snapshot): https://cloudsnuchoi.github.io/2026NASA/demo/
- Code: https://github.com/cloudsnuchoi/2026NASA
- Slides: https://cloudsnuchoi.github.io/2026NASA/submission/slides/

*"What should I plant next year so both my soil and my wallet survive?"*

Every autumn, a corn-soybean farmer in Iowa makes a choice that is hard to undo. Add a cereal rye cover? Bring in wheat or oats? Try alfalfa? The answer touches the soil, the water and next year's harvest, and the weather that decides it is uncertain. Satellites see things the farmer cannot see from the ground: how many days the soil lies bare, how dry the root zone was in a drought year, how warm and wet the next seasons may be. But that information is spread across many NASA and USDA archives, in formats a farmer has no time to learn.

Our team name, "Amolra," comes from the Korean phrase for "I have no idea!" That is the honest answer most of us would give if someone asked which rotation is "best" for a field we have never walked. So we did not build a machine that gives one answer. We built a tool that lays out the options, shows the range of what could happen, and says clearly what it does not know.

We built ART FARM so farmers never have to say "Amolra" again.

### What It Does & How It Works

ART FARM has **two tiers**.

**Tier 1 — Quick Screen (anywhere in the Corn Belt).** The user clicks the four corners of a field on a satellite basemap. The browser pulls ten years of daily NASA POWER weather for that point and USGS 3DEP elevation, then applies FAO-56 crop water formulas (reference evapotranspiration and crop coefficients). The user picks two or three of corn, soybean and wheat; the screen shows rotations without the same crop twice in a row. There is **no ranking**, and every result is labelled **"screening estimate"**. The calculation is a JavaScript port of our team's MATLAB prototype (V8).

**Tier 2 — Deep Analysis (20 pilot fields in 4 counties).** If the polygon overlaps one of our 20 pilot fields (Story County, Iowa: 12; McLean County, Illinois: 3; Lancaster County, Nebraska: 3; Union County, Ohio: 2), the tool calls our model API and shows four strategy cards:

| Code | Rotation | Role |
| --- | --- | --- |
| A | Corn–soybean (from the field's own USDA Cropland Data Layer history) | Current practice, the reference for all % values |
| B | A + winter cereal rye cover | Shorter bare-soil period, same cash crops |
| C | Corn–soybean–small grain + cover | Third crop family, pest-cycle break |
| D | Corn–soybean–alfalfa | Reference card: forage and nitrogen fixation, but high water use |

Strategies that match the crops the user selected are highlighted (corn + soybean → A, B; adding wheat → also C). D is shown as a reference card.

The engine behind the cards:

1. **Inputs per field.** USDA Crop Sequence Boundaries polygon and Cropland Data Layer crop history; SSURGO soil water capacity and erodibility; NASA POWER daily weather 1995–2025 (FAO-56 Penman–Monteith reference ET); OpenET monthly ET to scale the crop coefficient for that field; NASA HLS NDVI for bare-soil periods.
2. **Monte Carlo water balance.** A daily soil-water bucket (FAO-56 water stress, SCS curve-number runoff) is run over 500 resampled weather sequences with a fixed seed. Every strategy uses the same weather draws, so differences come from the rotation, not from luck.
3. **Uncertainty, not a point answer.** Each metric is returned as P10 / P50 / P90 and CVaR (the mean of the worst 10 % of samples).
4. **2012 drought stress test.** The same water balance is replayed with the actual 2009–2012 weather.
5. **Climate as ranges.** Next season: NASA GEOS-S2S ensemble (10 members). 2030s: NASA NEX-GDDP-CMIP6 (2 models × 2 emission scenarios). Both are shown only as distributions.
6. **Context layers.** NASA GPM IMERG precipitation, NLDAS-2 root-zone soil moisture and SMAP soil moisture are shown as coarse county-level context, with resolution labels, never as field-precise values.
7. **Satellite crop check.** We ran NASA/IBM's Prithvi-EO-1.0 crop-classification model (inference only, no fine-tuning) on HLS imagery of all 20 pilot fields for 2024 and compared it with the USDA Cropland Data Layer.
8. **Explanations.** An LLM explainer calls the model API as a tool and may only use numbers from the tool's JSON. Any number it writes that is not in that JSON is flagged as unverified.

Outside the pilot fields the tool says: *"Deep analysis available in 4 pilot counties."*

**A real example (Story County, Iowa, field 191825003869023, corn-soybean).**

- Growing-season water deficit for the current rotation (A), over 500 resampled seasons from 1995–2025 weather: **P10 115 mm, P50 188 mm, P90 265 mm**. With the next-season GEOS-S2S ensemble the range shifts to 136–309 mm (P10–P90).
- **2012 drought replay**, growing-season water deficit: **A 463 mm, B 451 mm, C 366 mm, D 513 mm**. Winter bare-soil days in 2012: A 181, B 9, C 3.
- So in the drought year the small-grain rotation (C) had the smallest deficit, the rye cover (B) almost removed the winter bare period but changed the deficit little, and alfalfa (D) had the largest deficit. These are relative model indices, not yield promises.

**Satellite AI check.** For 2024, Prithvi's most common class matched the USDA Cropland Data Layer crop on **19 of 20** pilot fields, with a mean pixel agreement of **0.883**. Most pilot fields are uniform corn or soybean fields, so this is not a general accuracy figure; the model card reports 60.64 % overall pixel accuracy on its own test set. Prithvi is a supporting layer; the crop label of record is the Cropland Data Layer.

**MATLAB cross-checks.** Our MATLAB members built the original formulas (prototype V8) and ran offline checks on the engine. The first comparison uses NASA data that the engine does not use in its calculation:

- *2012 drought vs NASA NLDAS-2 soil moisture* (`nldas_vs_engine_2012.csv`). Across the 4 pilot counties, the May–September 2012 NLDAS-2 root-zone soil-moisture anomaly and the engine's 2012 water deficit for the current rotation (A, mean over the county's pilot fields) have Pearson **r = −0.96 (n = 4 counties)**: where the root zone dried more, the engine found larger deficits. NLDAS-2 anomaly vs engine deficit: Lancaster NE −79 kg/m², 643 mm; Story IA −65 kg/m², 470 mm; McLean IL −64 kg/m², 415 mm; Union OH −44 kg/m², 307 mm.
- *2012 drought vs rainfall* (`drought_compare_2012_summary.csv`). The May–September 2012 precipitation anomaly against the same deficits gives r = −0.87 (n = 4): Lancaster −49.8 %, Story −49.0 %, McLean −32.2 %, Union −10.1 %. Both sides use NASA POWER weather, so this check is not independent. In the 1995–2025 May–September record (`season_anomaly_1995_2025.csv`), 2012 had the highest reference evapotranspiration (ET₀) in McLean, Story and Lancaster, and the lowest rainfall in Story and Lancaster.
- *Bare-soil days from HLS NDVI* (`baresoil_days_20fields.csv`). For all **20 pilot fields, 2023–2025** (60 field-years), the median is **81 bare-soil days per year** (range 19–139) and **43 winter bare days** (range 10–59; 59 field-years with a value). Cloud-free HLS observations covered 27–67 % of days. These years do not overlap the 2012 replay, so they are not compared with the engine's 2012 winter bare days.
- *Slide figures* (`fig_backtest2012.png`, `fig_p10p90.png`). These plot the engine's 2012 replay and P10–P90 ranges for three McLean IL fields. We checked the 2012 bars against the live model API, and they match.
- *USDA NASS county yields* (`nass_compare_2012_corr.csv`, `nass_compare_multi_corr.csv`). The 2012 yield change against the engine's 2012 deficit for the current rotation (A) gives soy r = −0.85 and corn r = −0.49, but with n = 4 counties this is only a check of direction. Over 2008–2023 (4 counties × 16 years, n = 64), county corn yield change and the engine's seasonal water deficit have r = −0.42 (p = 0.0006); for soybean, r = −0.24 (p = 0.058, not significant). This is a correlation, not causation, and yield is not what the engine optimises.
- *Next-season GEOS-S2S vs 31 years of history* (`s2s_vs_history_box.csv`). For spring (MAM) and June–July 2027, the 10-member GEOS-S2S precipitation and temperature anomalies are shown next to the 1995–2025 NASA POWER seasons for all 4 counties. The two products are different and not bias-corrected, so the comparison is shown as ranges only.
- *Crop coefficient sensitivity* (`kc_sensitivity.csv`). In the V8 prototype, changing Kc by ±10 % changed the May–Sep water deficit by −19 % to +21 % across all 20 fields × 4 rotations, and the order of the rotations did not change on any field. The V8 Kc values themselves (1.08/0.86/0.75) still lack a table citation (`coefficients_sources.csv`), and validation is ongoing.
- *NDVI vs deficit* (`ndvi_vs_deficit.csv`). Across 60 field-years from 2023–2025, the HLS NDVI anomaly and the engine's season water deficit show no significant relation (r = −0.09, p = 0.50). We report this as a null result.

With only four counties, these are consistency checks, not statistical proof. **In progress:** the V8 prototype now runs on all 20 pilot fields (80 rotation cards, 0 failures; `v8_cards_20fields.csv`). Its annual crop water demand uses a different definition from the engine's seasonal water deficit, so we do not report that comparison as agreement.

### Team

- **Hylē** — full stack, data pipeline, model API, project lead
- **김윤성** — MATLAB: climate analysis (2012 drought, climate summaries)
- **김우찬** — MATLAB: vegetation and scenarios; prototype V8
- **고지은** — UI/UX + MATLAB slide figures
- **하지민** — UI/UX + MATLAB NDVI bare-soil analysis
- **강다은** — 3D simulation (planned) + demo video

### Benefits & Impact

- **Decisions with the risk visible.** A farmer and a local adviser can see the spread of outcomes and the bad-year tail, not just an average.
- **A drought they remember.** The 2012 replay turns abstract risk into a year every Corn Belt farmer remembers.
- **Honest about trade-offs.** Cover crops cut bare-soil days but use spring water; alfalfa adds forage and nitrogen but uses the most water. The cards say so.
- **Free and open.** No login. Built on public NASA and USDA data that any county extension office could reuse.
- **A bridge to local experts.** Every card ends with what must be checked locally, so the tool starts a conversation instead of ending it.

### What makes it creative

- **Ranges and a stress test instead of fake forecasts.** We never show a single multi-year forecast. The future is a P10–P90 range from NASA seasonal and climate-model ensembles, and validity is tested against the real 2012 drought.
- **Numbers never come from the language model.** The engine computes; the LLM only explains. Every number in an explanation is matched to a JSON path in the engine response, and unmatched numbers are flagged.
- **Cons and soil-test flags on every card.** Each strategy card lists why, evidence, benefits, information gaps and risks for local review. Nitrogen is never given as a fixed kg value; the card asks for a field soil test.
- **No single "best" answer.** Priority sliders (water, soil, stability, income) re-weight the comparison, and the order changes. Strategy cards are never labelled "Recommended".
- **A foundation model used carefully.** Prithvi is used for inference only and checked against USDA labels, with its limits written next to the result.

### Tools, languages & datasets

- **Languages and tools:** Python (FastAPI, NumPy, pandas, psycopg, rasterio, earthaccess, PyTorch CPU), PostgreSQL + PostGIS + pgvector, MATLAB (offline prototype and analysis), JavaScript/HTML (Leaflet, Chart.js, Tailwind CSS).
- **NASA data:** NASA POWER, HLS (Landsat/Sentinel-2) v2.0, SMAP L3, GPM IMERG Final V07, NLDAS-2 Noah, GEOS-S2S-3, NEX-GDDP-CMIP6, Prithvi-EO-1.0 crop classification model.
- **Other data:** USDA NASS Cropland Data Layer, Crop Sequence Boundaries, Quick Stats bulk county yields; USDA NRCS SSURGO (Soil Data Access); USGS 3DEP elevation; OpenET; US Census county boundaries; NOAA NWS API, Open-Meteo climate API and Esri World Imagery (Quick Screen). Full list with links: `data-links.md`.
- **AI:** Prithvi-EO-1.0 (inference only); DeepSeek API for the explainer; coding assistants for software development. Details: `si-use.md`.

**Planned, not built for this submission:** a three.js voxel 3D field simulation, economic (revenue) comparison with cited prices, more pilot counties, and an evidence library with DOI citations in explanations (the explainer currently returns `insufficient_evidence` when no citation exists).

*ART FARM is a decision-support tool. It does not replace farmer judgment or local agronomic advice. All % values are relative indices against the current rotation (A), not guarantees.*

<!--
SOURCES (internal, not for public text). Retrieved 2026-11-15 ~19:00 KST.

Live model_api: http://127.0.0.1:8090 (health ok, db true).
- "20 pilot fields in four counties (Story 12, McLean 3, Lancaster 3, Union 2)": GET /fields -> 20 fields; docs/CONTRAST-FIELDS.md; docs/PRITHVI.md "대상"; docs/status/live.json data lane "데모 필지 20개, 4개 카운티".
- "ten years of NASA POWER weather" (Tier 1): frontend/index.html (feat/artfarm-web worktree) POWER URL start=20160101 end=20251231; DIRECTIVE.md "NASA POWER 10 yr".
- "NASA POWER daily weather 1995–2025": GET /simulate period {start 1995-01-01, end 2025-12-31}; docs/spike-report.md POWER section.
- "500 resampled ... fixed seed": POST /simulate {"field_id":"191825003869023","n":500,"seed":42} run_id mc-85c4b6b5c78cc8d6-n500-s42.
- "P10 115 mm, P50 188 mm, P90 265 mm": same response, strategy A metrics.season_water_deficit_mm p10 115.029, p50 188.337, p90 265.448 (cvar 300.564).
- "136–309 mm": same response, strategy A scenario_results horizon next_season source geos_s2s p10 135.983 p90 308.686 (n_members 10, period 2027-MAM+JJ).
- "2012: A 463, B 451, C 366, D 513 mm": GET /validation/backtest?field_id=191825003869023&year=2012 -> season_water_deficit_mm 462.8 / 450.9 / 365.6 / 512.9. Window 2009-2012. C and D = mean over rotation phases.
- "winter bare-soil days A 181, B 9, C 3": same response winter_bare_days 181.0 / 9.0 / 3.0 (D 131.8 not quoted).
- "GEOS-S2S 10 members", "NEX-GDDP 2 models x 2 scenarios": docs/spike-report.md GEOS-S2S + NEX-GDDP (ACCESS-CM2, MPI-ESM1-2-HR; ssp245, ssp585); /simulate scenario_results n_members.
- "Prithvi 19 of 20, mean pixel agreement 0.883, model card 60.64 % aAcc": docs/PRITHVI.md 요약 + 주의 1.
- "12 Corn Belt states" (MATLAB drought analysis): /srv/hackathon/data/processed/v1/matlab/drought_2012_county.csv(.manifest.json, 13,464 rows, script matlab/climate/drought_2012_analysis.m).
- MATLAB cross-checks (20:20 KST): /srv/hackathon/data/processed/v1/matlab/outputs/yoonsung/drought_compare_2012_summary.csv (pearson_r_precip_vs_deficit -0.8653, n_for_r 4; per-county engine_A_deficit_2012_mm 414.77/469.93/643.3/306.5, precip_anomaly_pct_2012_MJJAS -32.21/-49.02/-49.85/-10.06, tmax 1.42–3.51; rzsm_z NaN). outputs/jimin/baresoil_days_20fields.csv: 60 rows, 20 fields, 2023–2025; bare_days median 81 min 19 max 139; winter_bare_days median 43 min 10 max 59, 1 NaN (171825006923844 2023); coverage 0.274–0.666.
- Team roles: Hylē directive to SUB lane 2026-11-15 20:15 KST; 강다은 demo video added by Hylē (#68).
- v2 MATLAB (21:00 KST): outputs/yoonsung/nldas_vs_engine_2012.csv pearson_r -0.9578, n 4; anomaly_2012_kg_m2 -64.17 McLean / -65.20 Story / -79.17 Lancaster / -43.92 Union. season_anomaly_1995_2025.csv: max ET0_anomaly year 2012 in 17113 (172 mm), 19169 (202), 31109 (235); 39159 max 1999; min precip year 2012 in 19169 and 31109. outputs/jieun/fig_backtest2012.png fields 171825001292309/171825006921423/171825006923844 = GET /validation/backtest 2012: 431/415/281/351, 384/369/332/403, 430/415/381/455 mm. outputs/woochan/v8_cards_20fields.csv 80 rows, 20 fields; v8_failures_20fields.csv header only (11:21 UTC run). Re-confirmed by outputs/woochan/run_log.json run_id 20261115_120959: MATLAB 26.2 (R2026b), FieldShift_V8_batch success, 20/20 fields, 80 rows, 0 failed. python_smoke/ subfolders not cited (smoke tests).
- Live server URL: /srv/hackathon/state/status/demo_url.txt (20:17 KST).
- Old MATLAB validation status: /srv/hackathon/projects/2026NASA-mat/docs/MATLAB-VALIDATION.md (uncommitted, 2026-11-15T19:02 KST): V8 deficit not validated; NDVI bare days not validated; 2012 county check = same-source POWER cross-check only. docs/MATLAB-VALIDATION.md is not on main -> "in progress".
- CVaR definition: /strategies/compare cvar_definition.
- "unmatched numbers are flagged": model_api/README.md /explain (unverified_numbers); docs/QA-REPORT.md A10.
- "insufficient_evidence": model_api/README.md, QA-REPORT A10 (evidence_chunk empty).
- Strategy highlight rule (A,B / +C / D reference) and "Deep analysis available in 4 pilot counties": /srv/hackathon/inbox/DIRECTIVE.md.
- Quick Screen implementation status: L1 lane (feat/artfarm-web) in progress at 20:00 KST; re-check wording before final submission.
- 3D voxel sim: docs/status/live.json sim lane 0 % -> listed as planned.
- MATLAB v3 additions (outputs/ mtime before 22:50 KST): yoonsung/nass_compare_2012_corr.csv, nass_compare_multi_corr.csv (22:35), s2s_vs_history_box.csv (20:43); woochan/kc_sensitivity.csv (22:39; script work/woochan/woochan_kc_sensitivity.m, Kc x0.9/1.0/1.1, pct_change -19.21..-17.24 / +18.27..+21.06, rank_changed 0/80), coefficients_sources.csv (22:23, identical to coefficients_draft_from_V9.csv); jimin/ndvi_vs_deficit.csv (22:38).
- Removed from team draft (unsupported): 20 %/25 % claims, ECOSTRESS, hyperspectral, locusts/drones.
-->
