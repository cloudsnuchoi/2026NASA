# ART FARM — Space Apps submission form (copy-paste)

Fields in the order of the Space Apps project submission form. Copy the text inside each block. Generated 2026-11-15 20:30 KST, v2 updated 21:10 KST from `submission.md`, `si-use.md`, `data-links.md`; numbers and sources are in the `SOURCES` comment at the end of `submission.md`.

Open items before pressing Submit:
- TODO(Hylē): demo video link, if the form asks for one (owner: 강다은; recording plan in `demo-script.md`).
- Check the SI checkbox labels on the live form against section 6 below; tick only the ones that match.

---

## 1. Project Name

```
ART FARM
```

## 2. Summary (162 words, counted with whitespace split)

```
ART FARM (Field Shift: Adapting Farms with NASA Data) helps Corn Belt farmers compare crop rotations for soil health and weather and water resilience without being told what to plant. It has two tiers. Quick Screen works anywhere in the Corn Belt: the farmer clicks four corners and gets a screening estimate built from ten years of NASA POWER weather, USGS elevation and FAO-56 crop water formulas. Deep Analysis covers 20 pilot fields in four counties (Iowa, Illinois, Nebraska, Ohio). There, a Monte Carlo water-balance engine compares four strategies: corn-soybean, plus a rye cover, plus a small grain, or plus alfalfa. Results come as P10–P90 ranges with a worst-10% tail (CVaR), a replay of the real 2012 drought, and climate ranges from NASA GEOS-S2S and NEX-GDDP-CMIP6. NASA's Prithvi model checks crop labels against USDA maps. An AI explainer may only quote numbers that the engine returned. Every card lists drawbacks, information gaps and a reminder to confirm with a field soil test.
```

## 3. Project Demonstration link

```
https://cloudsnuchoi.github.io/2026NASA/submission/slides/
```

## 4. Project link

```
https://cloudsnuchoi.github.io/2026NASA/demo/
```

(Static snapshot, fixed. The live server is named inside Project Details.)

## 5. Project Details

```markdown
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

With only four counties, these are consistency checks, not statistical proof. **In progress:** the V8 prototype now runs on all 20 pilot fields (80 rotation cards, 0 failures; `v8_cards_20fields.csv`). Its annual crop water demand uses a different definition from the engine's seasonal water deficit, so we do not report that comparison as agreement.

### Team

- **Hylē** — full stack, data pipeline, model API, project lead
- **김윤성** — MATLAB: climate analysis (2012 drought, climate summaries)
- **김우찬** — MATLAB: vegetation and scenarios; prototype V8
- **고지은** — UI/UX + MATLAB slide figures
- **하지민** — UI/UX + MATLAB NDVI bare-soil analysis
- **강다은** — 3D simulation (planned) + demo video

### Links

- Project (static snapshot): https://cloudsnuchoi.github.io/2026NASA/demo/
- Live server (team VPS; may go offline after judging): https://watts-astrology-asus-blessed.trycloudflare.com
- Slides: https://cloudsnuchoi.github.io/2026NASA/submission/slides/

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
```

## 6. Use of SI (Artificial Intelligence)

Tick (match to the form's labels):
- [x] Yes, our team used SI
- [x] Code / software development (coding assistant: Claude Code; Codex/Gemini use by members not confirmed — leave out unless confirmed)
- [x] Text generation inside the product (DeepSeek explainer, numbers only from engine JSON)
- [x] Images (all site photos and the "ART FARM" logo are AI-generated, watermarked on the site)
- [x] Data analysis / modelling (Prithvi-EO-1.0 inference only)
- [ ] Video — not used
- [ ] Audio / voice — not used

Text:

```
We used SI in four places. (1) Software development: a coding assistant (Claude Code) wrote and tested code and documents from team-written specs; every change went through a branch and a human-merged pull request. It did not choose the problem, strategies or data sources, and did not create data values. (2) Explanations: the DeepSeek API writes plain-language explanations of strategy cards. It calls our model API as a tool and may only use numbers in the returned JSON; every number is matched to a JSON path and unmatched numbers are flagged as unverified. If no citation is found it returns "insufficient evidence". (3) Satellite crop check: NASA/IBM Prithvi-EO-1.0 crop classification, inference only (no fine-tuning), compared with the USDA Cropland Data Layer, which stays the label of record. (4) Images: all site photos and the ART FARM logo were generated with AI image tools; each photo carries a visible "AI-generated image" watermark and the footer says so. No SI-generated video or voice, no reinforcement learning, no fine-tuning. No NASA logos, flags or mission insignia are used.
```

## 7. NASA Data

| Link Text | URL |
| --- | --- |
| NASA POWER (daily, Agroclimatology) | https://power.larc.nasa.gov/ |
| HLS v2.0 Harmonized Landsat Sentinel-2 (HLSL30/HLSS30) | https://hls.gsfc.nasa.gov/ |
| SMAP L3 Radiometer Soil Moisture SPL3SMP v009 | https://nsidc.org/data/spl3smp/versions/9 |
| GPM IMERG Final Daily V07 (GPM_3IMERGDF) | https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDF_07/summary |
| NLDAS-2 Noah Monthly (NLDAS_NOAH0125_M v2.0) | https://disc.gsfc.nasa.gov/datasets/NLDAS_NOAH0125_M_2.0/summary |
| GEOS-S2S-3 (NASA GMAO) | https://gmao.gsfc.nasa.gov/cms/geos-s2s/ |
| NEX-GDDP-CMIP6 (NASA NCCS) | https://www.nccs.nasa.gov/services/data-collections/land-based-products/nex-gddp-cmip6 |
| Prithvi-EO-1.0-100M multi-temporal crop classification (NASA/IBM) | https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-1.0-100M-multi-temporal-crop-classification |

## 8. Space Agency Partner & Other Data

No space agency partner data used. Other data and services:

| Link Text | URL |
| --- | --- |
| USDA NASS Cropland Data Layer | https://www.nass.usda.gov/Research_and_Science/Cropland/SARS1a.php |
| USDA NASS Crop Sequence Boundaries | https://www.nass.usda.gov/Research_and_Science/Crop-Sequence-Boundaries/index.php |
| USDA NASS Quick Stats | https://quickstats.nass.usda.gov/ |
| USDA NRCS Soil Data Access (SSURGO) | https://sdmdataaccess.sc.egov.usda.gov/ |
| USGS 3D Elevation Program (EPQS) | https://www.usgs.gov/3d-elevation-program |
| OpenET | https://openet-api.org/ |
| NOAA National Weather Service API | https://www.weather.gov/documentation/services-web-api |
| Open-Meteo Climate API | https://open-meteo.com/en/docs/climate-api |
| Esri World Imagery (basemap) | https://www.arcgis.com/home/item.html?id=10df2279f9684e4a9f6a7f08febac2a9 |
| US Census cartographic boundary files | https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html |
| FAO-56 Crop Evapotranspiration (Allen et al. 1998) | https://www.fao.org/3/x0490e/x0490e00.htm |
| DeepSeek API (explainer LLM) | https://api-docs.deepseek.com/ |
