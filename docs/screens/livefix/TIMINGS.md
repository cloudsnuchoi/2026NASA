# LIVEFIX timings (2026-11-17, KST ~11:16)

Measured against a lane-local web server (`uvicorn infra.web.app:app` on 127.0.0.1:8099, this worktree) proxying to the live
model_api on 127.0.0.1:8090. `/api/quick` runs in-process in the web app (`model_api.quick.quick_screen`), so the 8099 numbers are
the same code path as the public web (:8095). Client wall-clock times (Python `time.perf_counter`, loopback, no tunnel).

## /api/quick — new field never requested before

- Polygon (lon, lat), ~0.6 km square, random offset around 40.71, -93.88 (Corn Belt, southern Iowa):
  `[[-93.85403, 40.73587], [-93.84803, 40.73587], [-93.84803, 40.74187], [-93.85403, 40.74187]]`, crops Corn + Soy + Wheat.
- First call: **3.08 s** (NASA POWER daily 2015–2024, USGS 3DEP EPQS, NOAA NWS, Open-Meteo CMIP6 fetched over the network).
- Immediate repeat: **0.16 s** → cached. The response has no `cached` field; caching is the server's disk cache of upstream GETs
  (`model_api/quick.py: fetch_json`, `QUICK_CACHE_DIR`), and the result itself is recomputed (`generated_utc` is per call).
- Browser runs (Playwright, same day): another new custom field around 40.6123, -93.7311 took 7.99 s on first call;
  the 52-vertex Story County pilot ring on first call took 11.41 s; repeats were 0.17–0.39 s.

## /api/simulate — pilot field

- `{"field_id": "191825000014952", "n": 500, "seed": 42}` (Story County, IA): **0.038 s** first call from this client,
  0.022 s repeat; response `latency_ms` 12.2 (server compute; `model_api/engine.py` keeps an in-memory result cache).
- Seasons in the response: **n = 500** resampled Monte Carlo seasons, drawn from weather `period` 1995-01-01 → 2025-12-31,
  `run_id` mc-68d334b160099d92-n500-s42, CVaR = mean of the worst 10 % of samples.
- Browser (Playwright) Deep call including the proxy: 0.09–0.27 s.

## Can NASA POWER 2025 daily data be added to climate_history?

**Yes.** POWER currently serves complete 2025 daily data (checked 2026-11-17: all 9 parameters the engine requests —
T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, ALLSKY_SFC_SW_DWN, RH2M, WS2M, PS, GWETROOT — return 365/365 days for 2025 with no -999 fill
values at 40.74, -93.85), and `climate_history` is built from the constants `HIST_START, HIST_END = 2015, 2024` in
`model_api/quick.py` (the POWER URL and every 10-year summary derive from them), so it is a one-constant change
(2016–2025 keeps a 10-year window; it also changes the POWER URL, so every field re-fetches once). Not changed in this lane.
