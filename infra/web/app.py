"""ART FARM public web front: static frontend + read-only reverse proxy to model_api.

- Serves ../../frontend at /
- Proxies an allow-list of model_api paths under /api/* (GET/POST only)
- POST /api/quick is computed in-process (model_api.quick) so the live 8090
  server does not need a restart.
- Per-IP sliding-window rate limit on /api/* only (RATE_PER_MIN, default 300 req/min);
  static assets are never counted.
- Cache headers: css/js/images/fonts "public, max-age=600"; HTML "public, max-age=60".

Run: infra/web/run_web.sh  (127.0.0.1:8095). Starlette + httpx (BSD-3).
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
import time
from collections import defaultdict, deque
from pathlib import Path

import httpx
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
FRONTEND = ROOT / "frontend"
UPSTREAM = os.environ.get("MODEL_API", "http://127.0.0.1:8090")
RATE_PER_MIN = int(os.environ.get("RATE_PER_MIN", "300"))
STATIC_EXT = re.compile(r"\.(css|js|mjs|png|jpe?g|gif|svg|webp|ico|woff2?|ttf|map|json)$", re.I)

GET_ALLOW = [
    r"/health",
    r"/fields",
    r"/glossary",
    r"/field/[A-Za-z0-9_\-]+/profile",
    r"/field/[A-Za-z0-9_\-]+/climate/history",
    r"/field/[A-Za-z0-9_\-]+/climate/outlook",
    r"/field/[A-Za-z0-9_\-]+/bare-periods",
    r"/field/[A-Za-z0-9_\-]+/vulnerable-seasons",
    r"/county/[0-9]{5}",
    r"/validation/backtest",
    r"/rotations/candidates",
    r"/evidence/search",
]
POST_ALLOW = [r"/simulate", r"/strategies/compare", r"/explain", r"/locate"]
GET_RE = [re.compile(p + r"$") for p in GET_ALLOW]
POST_RE = [re.compile(p + r"$") for p in POST_ALLOW]
MAX_BODY = 64 * 1024

_hits: dict[str, deque] = defaultdict(deque)
client = httpx.AsyncClient(base_url=UPSTREAM, timeout=60.0)


def client_ip(request: Request) -> str:
    return (
        request.headers.get("cf-connecting-ip")
        or request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "?")
    )


class RateLimit(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/"):
            ip = client_ip(request)
            now = time.monotonic()
            q = _hits[ip]
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= RATE_PER_MIN:
                return JSONResponse({"detail": f"rate limit: {RATE_PER_MIN} requests/min"}, status_code=429)
            q.append(now)
            return await call_next(request)
        # static files: not rate limited, cacheable
        resp = await call_next(request)
        if resp.status_code == 200 and "cache-control" not in resp.headers:
            path = request.url.path
            if STATIC_EXT.search(path):
                resp.headers["cache-control"] = "public, max-age=600"
            elif path.endswith("/") or path.endswith(".html"):
                resp.headers["cache-control"] = "public, max-age=60"
        return resp


async def quick(request: Request) -> Response:
    body = await request.body()
    if len(body) > MAX_BODY:
        return JSONResponse({"detail": "body too large"}, status_code=413)
    try:
        from model_api import quick as q  # noqa: PLC0415
    except Exception as exc:  # pragma: no cover
        return JSONResponse({"detail": f"quick engine unavailable: {exc}"}, status_code=503)
    import json

    try:
        payload = json.loads(body or b"{}")
        req = q.QuickRequest(**payload) if hasattr(q, "QuickRequest") else None
        polygon = req.polygon if req else payload["polygon"]
        crops = req.crops if req else payload["crops"]
    except Exception as exc:
        return JSONResponse({"detail": f"invalid request: {exc}"}, status_code=422)
    try:
        out = await asyncio.to_thread(q.quick_screen, polygon, crops)
    except ValueError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=422)
    return JSONResponse(out)


_fields_geo: dict | None = None


async def fields_geo(request: Request) -> Response:
    """Outer rings of the 20 pilot demo fields (from /fields + /field/{id}/profile), cached in memory."""
    global _fields_geo
    if _fields_geo is None:
        fl = (await client.get("/fields")).json()
        out = []
        for f in fl.get("fields", []):
            p = (await client.get(f"/field/{f['field_id']}/profile")).json()
            g = p.get("geometry") or {}
            polys = g.get("coordinates", []) if g.get("type") == "MultiPolygon" else [g.get("coordinates", [])]
            if not polys or not polys[0]:
                continue
            ring = max((pp[0] for pp in polys), key=len)
            if len(ring) > 1 and ring[0] == ring[-1]:
                ring = ring[:-1]
            out.append({"field_id": f["field_id"], "county_fips": f["county_fips"], "area_ha": f.get("area_ha"),
                        "ring": [[round(x, 6), round(y, 6)] for x, y in ring[:400]]})
        _fields_geo = {"fields": out, "source": "USDA Crop Sequence Boundaries via model_api; not ownership parcels"}
    return JSONResponse(_fields_geo)


async def proxy(request: Request) -> Response:
    path = "/" + request.path_params["path"]
    method = request.method
    allow = GET_RE if method == "GET" else POST_RE if method == "POST" else []
    if not any(r.match(path) for r in allow):
        return JSONResponse({"detail": "not allowed"}, status_code=403)
    body = None
    if method == "POST":
        body = await request.body()
        if len(body) > MAX_BODY:
            return JSONResponse({"detail": "body too large"}, status_code=413)
    try:
        r = await client.request(
            method,
            path,
            params=request.query_params,
            content=body,
            headers={"content-type": "application/json"} if body is not None else None,
        )
    except httpx.HTTPError as exc:
        return JSONResponse({"detail": f"upstream error: {type(exc).__name__}"}, status_code=502)
    return Response(
        r.content,
        status_code=r.status_code,
        media_type=r.headers.get("content-type", "application/json"),
    )


app = Starlette(
    routes=[
        Route("/api/quick", quick, methods=["POST"]),
        Route("/api/fields-geo", fields_geo, methods=["GET"]),
        Route("/api/{path:path}", proxy, methods=["GET", "POST"]),
        Mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="static"),
    ]
)
app.add_middleware(RateLimit)
