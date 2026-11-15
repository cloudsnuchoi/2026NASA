# ART FARM — Use of SI (AI) disclosure

Draft 2026-11-15 20:00 KST. Ledger: [docs/si-log.md](../si-log.md). Space Apps calls AI tools "SI" in the submission form; both terms are used here.

## Where SI was used

| Area | Tool | What it did | What it did NOT do |
| --- | --- | --- | --- |
| Software development | Coding assistants: Claude Code (Anthropic) — recorded in si-log. Codex CLI / Gemini agents are allowed by AGENTS.md; whether team members used them is **not confirmed** (ask before 22:00) | Wrote and tested code in `model_api/`, `data_pipeline/`, `model_api/vision/`, QA tests, site pages and these submission documents, from team-written specs (PRD, SOT, issues). Every change went through a branch and PR merged by a human | Did not choose the problem, the strategies or the data sources. Did not make up data values: all numbers come from public datasets and our engine |
| Runtime explanations (`POST /explain`) | DeepSeek API (OpenAI-compatible, `deepseek-flash`) | Writes a plain-language explanation of strategy cards. It calls our model API as a tool and may only use numbers in the tool JSON; each number is matched to a JSON path, unmatched numbers are returned in `unverified_numbers`. Citations only from our evidence search; if none, `insufficient_evidence: true` | Does not compute any metric, rank strategies or invent citations |
| Team chat bot (orchestration) | DeepSeek API | Summarised task status and routed tasks in the team chat during the hackathon | Not part of the product a farmer sees |
| Satellite crop classification | Prithvi-EO-1.0-100M crop classification (NASA/IBM foundation model) | Inference only on HLS chips for 20 pilot fields (2024), compared with USDA CDL | No fine-tuning, no reinforcement learning. Supporting layer only; CDL is the label of record |
| Images / logo | **Not confirmed (미확인)** | Frontend assets `frontend/assets/img01–img12` and the "ART FARM" logo come from the team mockup and design team. Whether any were SI-generated is not recorded | — Owner (design team / L1) must confirm before 22:00 |

Not used: SI-generated video or voice (planned 30-second video uses screen capture; see `video-script.md`), RL, fine-tuning of any model.

## Where the product must show SI labels — current state

Checked on 2026-11-15 ~19:30 KST against the L1 frontend in progress (`frontend/index.html` in worktree `2026NASA-web`, branch `feat/artfarm-web`, not yet committed) and the docs site on `main`.

| Place | Required label | Current state |
| --- | --- | --- |
| `/explain` output in the UI | "AI-generated explanation (DeepSeek). Numbers come from the ART FARM engine; check with a local adviser." | **Missing**: no explainer panel or SI label found in the frontend yet |
| Footer / About | "This site uses AI: Prithvi (satellite crop check, inference only), DeepSeek (explanations), coding assistants (development)." | **Missing** |
| Prithvi result | "Satellite AI crop estimate (Prithvi-EO-1.0); USDA CDL is the reference" | **Missing** in frontend (API returns `vision` fields) |
| Docs site (`docs/architecture.html`, `docs/models.html`) | Mentions DeepSeek as the LLM provider | Present (Korean text) |
| Generated images (if any) | Visible "AI-generated" caption | Unknown — see images row above |

## Gaps for L1 (frontend) before final submission

1. Add SI labels: `/explain` panel, footer "Use of AI" line, Prithvi badge (table above).
2. Remove the word **"Recommended"** (3 occurrences in `frontend/index.html`). Directive: no "Recommended", no ranking in Quick Screen.
3. Label every Quick Screen result **"screening estimate"** (0 occurrences now).
4. Replace "MATLAB engine" wording (10 "MATLAB" occurrences) with "FAO-56 engine (ported from team MATLAB prototype V8)".
5. `CROP_DB` price / cost / yield values (e.g. `price: 4.60, cost: 680`) have no source. Add a USDA ERS/NASS source and year plus an "assumption" label, or remove the numbers.
6. Add the "relative index, not a guarantee" tooltip to water-saving % and soil-organic-matter index (0 occurrences of "relative index" now).
7. Add "Decision support only — does not replace farmer judgment" (0 occurrences now).
8. The Open-Meteo source note says "climate model 60 % + past 10-year trend 40 %" for 2026–2039 daily values. Show this only as a range or scenario, never as a deterministic multi-year forecast (AGENTS.md rule), or drop it.
9. Map has `attributionControl: false`. Esri World Imagery and Leaflet attribution must be visible on the map.
10. Translate remaining Korean UI text to English (design request).
11. Confirm image/logo provenance (SI or not) and caption accordingly. No NASA logos.
