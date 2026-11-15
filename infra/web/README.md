# infra/web — ART FARM public web

- `app.py` (Starlette + httpx, BSD-3): serves `frontend/` and proxies an allow-list of read-only model_api paths under `/api/*` (GET/POST only, 64 KB body cap). `POST /api/quick` runs `model_api.quick` in-process; `GET /api/fields-geo` returns the 20 pilot field outlines. Per-IP rate limit 300 req/min on `/api/*` only (`RATE_PER_MIN`), IP from `cf-connecting-ip`; static assets are not counted and get `Cache-Control: public, max-age=600` (HTML: `max-age=60`).
- `run_web.sh` — uvicorn on 127.0.0.1:8095 (tmux `web`).
- `run_tunnel.sh` — Cloudflare quick tunnel (tmux `web-tunnel`), log `/srv/hackathon/logs/web-tunnel.log`, URL → `/srv/hackathon/state/status/demo_url.txt`.
- `prewarm_presets.py` — warms the `/quick` disk cache (`/srv/hackathon/data/cache/quick/`) for the 4 pilot-county presets.

Basemap: Esri World Imagery tiles with on-map attribution (display only).
