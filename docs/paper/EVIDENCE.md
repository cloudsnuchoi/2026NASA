# Evidence — every number in `artfarm_paper.tex`

Repo paths are relative to the repo root. Engine/MATLAB outputs under `/srv/hackathon/data/processed/v1/matlab/outputs/` (O) are read-only and not committed. API = `http://127.0.0.1:8090` (read-only GET).

| Paper claim | Source artifact |
| --- | --- |
| Two tiers; Quick Screen = 10 y POWER + USGS 3DEP + FAO-56, "screening estimate", no ranking, JS port of MATLAB V8 | `docs/submission/submission.md` (lines 17, 33) |
| 500 resampled seasons, fixed seed, shared draws, P10/P50/P90 + CVaR (worst 10 %), SCS curve number | `docs/submission/submission.md` (lines 49–50, 125, 138) |
| Strategies A–D (corn–soy, +rye, +small grain, +alfalfa) | `docs/submission/submission.md` (line 17) |
| Field 191825003869023: P10 115 / P50 188 / P90 265 mm, CVaR 301 mm (300.564); GEOS-S2S 136–309 mm, 10 members | `docs/submission/submission.md` (lines 61, 126–127; POST /simulate run_id mc-85c4b6b5c78cc8d6-n500-s42) |
| 2012 backtest 462.8 / 450.9 / 365.6 / 512.9 mm; 88 stress days; spin-up 2009–2011 | API `GET /validation/backtest?field_id=191825003869023&year=2012` (re-queried 2026-11-15 ~23:00 KST, strategy A 462.8 mm, stress_days 88); `docs/submission/submission.md` line 128 |
| 20 pilot fields: Story 12, McLean 3, Lancaster 3, Union 2 | `docs/PRITHVI-AGREEMENT.md`; API `GET /fields` (total 20) |
| NASS table (yield change, deficit, fields), baseline 2001–2024 excl. 2012/2025, r = −0.49 / −0.85, n = 4, p ≈ 0.15 | `docs/validation/NASS-2012.md`, `docs/validation/nass_2012_table.csv`, figure `docs/validation/nass_2012_vs_engine.png` |
| Spearman ρ 0 (corn) and −0.4 (soy) | `docs/matlab-results/yoonsung/nass_compare_2012_corr.csv` (= O/yoonsung/nass_compare_2012_corr.csv) |
| Deficit vs POWER MJJAS precip anomaly r = −0.87 (−0.8653), n = 4; not independent | `docs/matlab-results/drought_compare_2012_summary.csv`; `docs/MATLAB-VALIDATION.md` (same-POWER caveat) |
| Fig. 1 2012 replay, three McLean fields, matches API | `docs/matlab-results/fig_backtest2012.png`; `docs/submission/submission.md` lines 72, 135 |
| HLS bare-soil: 60 field-years, 20 fields, 2023–2025; winter median 29.5 (2024, 10–55), 44.5 (2025, 23–55); 2023 one missing; mean coverage 0.57–0.60 (0.573/0.579/0.601) | computed from `docs/matlab-results/baresoil_days_20fields.csv` (= O/jimin/baresoil_days_20fields.csv); NaN field noted in `docs/submission/submission.md` line 133 |
| NDVI anomaly vs deficit r = −0.09, p = 0.498, n = 60; season length r = 0.00, p = 0.988, n = 55 | O/jimin/ndvi_vs_deficit.csv |
| HLS does not overlap 2012 | `docs/MATLAB-VALIDATION.md` |
| Kc ±10 %: 80 cases, 20 fields × 4 rotations; −19.21 … −17.24 %, +18.27 … +21.06 %; 0 rank changes | computed from O/woochan/kc_sensitivity.csv |
| MATLAB R2026b, V8 batch 20/20 fields, 80 rows, 0 failures | `docs/submission/submission.md` line 135 (O/woochan/run_log.json run 20261115_120959); `docs/matlab-results/v8_cards_20fields.csv` |
| V8 economic/index coefficients unvalidated; simplified ET0 proxy | `docs/matlab-results/v8_cards_20fields.csv` (assumptions, et0_label columns); `docs/MATLAB-VALIDATION.md` |
| Prithvi 19/20, 0.193–0.997, median 0.934, mean 0.883, model card aAcc 60.64 % | `docs/PRITHVI-AGREEMENT.md` |
| Dataset list (POWER, SMAP, IMERG, HLS, NLDAS-2, OpenET, GEOS-S2S, NEX-GDDP-CMIP6, Prithvi, CDL, CSB, NASS, SSURGO) and dataset DOIs | `docs/DATA_SOURCES.md`, `docs/submission/data-links.md` (IMERG, HLS DOIs), `docs/PRITHVI.md` (Prithvi DOI), `docs/submission/submission.md` line 111 |

## Citations

40 references in `references.bib`, each resolved by DOI through OpenAlex (`openalex_log.jsonl`, one line per query; key never logged).
- Papers: 33. Dataset/model records with DOIs: SMAP L3 enhanced (10.5067/4DQ54OUIJ9DL), IMERG Final daily V07 (10.5067/GPM/IMERGDF/DAY/07), HLSL30/HLSS30 v2.0, NLDAS-2 forcing (10.5067/6J5LHHOHZHN4), NEX-GDDP-CMIP6 (10.7917/OFSG3345), Prithvi crop-classification model (10.57967/hf/0954) — all found in OpenAlex.
- No OpenAlex dataset DOI was found/used for NASA POWER, OpenET or GEOS-S2S; they are cited through their peer-reviewed descriptions (Sparks 2018 nasapower; Melton 2022 OpenET; Molod 2020 GEOS-S2S v2) with MERRA-2 (Gelaro 2017) as POWER's source.
- The Prithvi paper (Jakubik et al.) is cited as the record OpenAlex returned for arXiv DOI 10.48550/arXiv.2310.18660 (SSRN 10.2139/ssrn.4804009, 2024).
- **Rejected:** Allen et al. 1998 FAO-56 paper — both OpenAlex searches returned a wrong record (an R package; a journal editorial board), so it is not cited; Pereira et al. 2021 (FAO-56 update) is cited instead.

## Interpretation sections

Qualitative only; no numbers beyond those above. Policy programme names are given without party names.
