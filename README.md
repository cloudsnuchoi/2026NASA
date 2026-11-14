# 2026NASA · Field Shift

Team **아몰라** · [NASA Space Apps Challenge 2026](https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/) (Seoul) · Challenge 07 *Field Shift: Adapting Farms with NASA Data*.

A **decision-support** tool for Corn Belt corn–soy farmers. It compares crop-rotation strategies that may improve soil health and resilience to weather and water, using NASA Earth observations. It **supports, and does not replace**, farmer judgment and local agronomic expertise.

Repository: [github.com/cloudsnuchoi/2026NASA](https://github.com/cloudsnuchoi/2026NASA) · License: [Apache-2.0](LICENSE)

---

## What this prototype decides

**Question.** What crop to add to or change in an existing rotation to improve soil health and resilience to weather and water?

**Where.** One Iowa or Illinois county (rainfed Corn Belt, main case; picked in the 09:00–11:00 KST data spike). A Nebraska water-limited contrast is optional and cuttable.

**Strategies compared**

| Code | Rotation |
| --- | --- |
| `A` | Baseline corn–soy (`C-S`) |
| `B` | `C-S` plus a winter cereal rye cover crop |
| `C` | `C-S`–wheat or oats plus a cover crop |
| `D` | `C-S`–alfalfa (forage, nitrogen fixation, deep roots; water-use risk must be flagged, especially in the West) |

**Outputs.** Bare-field periods, vulnerable seasons, a multi-criteria comparison, and per-strategy *why / evidence / benefits / information gaps / local-review risks*, with priority sliders and a field map. Uncertainty is shown with Monte Carlo percentiles and CVaR. Validation is a CDL / Crop Sequence Boundaries backtest.

AI is organized in four layers: **vision** (Prithvi crop-classification checkpoint, inference only, CDL fallback) → **forecast/scenarios** (NASA GEOS-S2S seasonal ensemble, NASA NEX-GDDP-CMIP6 for the 2030s; distributions only) → **simulation** (Monte Carlo water balance + CVaR, rule/index scoring) → **LLM explanation** with tool-calling and citation-only RAG. The live engine for this weekend is **rule/index scoring + Monte Carlo + CVaR**. There is no reinforcement learning and no model fine-tuning. An LLM may call the model API and attach citations; it does not compute numbers. MATLAB is **offline only** (analysis and calibration exported to the database).

---

## Team docs (source of truth)

These documents are frozen in Korean. Identifiers in code stay English.

| Doc | Role |
| --- | --- |
| [docs/TEAM_SPEC.md](docs/TEAM_SPEC.md) | **Start here.** Product lock status, user flow & screens, requirement traceability, data mapping, AI 4-layer architecture, data spike, roles & handoff contracts, CLI guide, timeline |
| [docs/PRD.md](docs/PRD.md) | Problem, users, decision, scope, success criteria, demo, cut order |
| [docs/SOT.md](docs/SOT.md) | Datasets, IDs/units/CRS, aggregation, directories, DB schema, API contract |
| [docs/CHECKLIST.md](docs/CHECKLIST.md) | 16-hour timeline (KST) and Space Apps submission checklist |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Decision log |
| [docs/si-log.md](docs/si-log.md) | Use of AI (SI) log for the submission form |
| [AGENTS.md](AGENTS.md) | Rules for Codex CLI / Gemini CLI (agy) agents, per role |
| [GEMINI.md](GEMINI.md) | Gemini CLI entry point (imports AGENTS.md) |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Issue → branch → PR → one review → squash merge; hourly 10-minute sync |

---

## Repository layout

```text
data_pipeline/   # ETL, manifests, QA (raw data stays on the VPS under /data/raw)
model_api/       # FastAPI model service
rag/             # Evidence cards and citation search
frontend/        # Public, no-login demo UI
matlab/          # Offline analysis only (fixed Parquet/CSV outputs)
sim/             # three.js voxel simulation for the demo video
infra/           # Docker Compose, Postgres + PostGIS + pgvector
notebooks/       # EDA
docs/            # PRD, SOT, checklist, decisions
```

Do not commit secrets or raw/processed rasters. See `.gitignore` and the directory rules in [docs/SOT.md](docs/SOT.md).

---

## Stack (weekend)

- API: FastAPI (`model_api/`)
- Database: Postgres + PostGIS + pgvector (evidence cards only; keyword+DOI fallback if embeddings slip)
- Frontend: public URL with no login
- Hosting: team VPS (see `infra/`)
- NASA inputs (minimum one, preferably more): POWER, GPM IMERG, SMAP (context cell only), HLS (Landsat/Sentinel-2), SRTM, NLDAS-2, GEOS-S2S, NEX-GDDP-CMIP6 — full table in SOT

---

## Space Apps submission reminders

- Deadline: **2026-11-15 23:59 Asia/Seoul (KST)**; aim to finish by 23:55.
- Demo: **≤30-second video** or **≤7 slides including title**. English (or English subtitles).
- Links must open **without** a login, password, or sign-up.
- Use **at least one NASA dataset or resource** for global-award eligibility. List NASA Data and Other Data separately, with licenses in References.
- Disclose SI (AI) use. Do not use or alter NASA logos, flags, or mission identifiers.

Official challenge: https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/
