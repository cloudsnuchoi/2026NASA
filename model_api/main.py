"""Field Shift model API (FastAPI). Contract: docs/SOT.md section 6. Run: uvicorn model_api.main:app"""

from __future__ import annotations

import datetime as dt
import logging

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import cards, config, db, engine, explain as explain_mod, glossary as glossary_mod, services
from .repo import get_repo

log = logging.getLogger("model_api")

app = FastAPI(title="Field Shift model API", version="0.1.0",
              description="Rotation strategy comparison (MC water balance + CVaR + 7-axis index). Not a single optimum.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class APIError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


def err(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


@app.exception_handler(APIError)
async def _api_error(_: Request, exc: APIError):
    return err(exc.status, exc.code, exc.message)


@app.exception_handler(StarletteHTTPException)
async def _http_error(_: Request, exc: StarletteHTTPException):
    return err(exc.status_code, "not_found" if exc.status_code == 404 else "http_error", str(exc.detail))


@app.exception_handler(RequestValidationError)
async def _validation_error(_: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    return err(422, "invalid_request", f"{'.'.join(str(x) for x in first.get('loc', []))}: {first.get('msg', 'invalid')}")


@app.exception_handler(db.DBUnavailable)
async def _db_error(_: Request, exc: db.DBUnavailable):
    return err(503, "db_unavailable", "Database is not reachable")


def repo(request: Request):
    return getattr(request.app.state, "repo", None) or get_repo()


def _not_found(what: str):
    raise APIError(404, "not_found", f"Unknown {what}")


# ---------------------------------------------------------------------------------------------------
@app.get("/health")
def health(request: Request):
    r = repo(request)
    ok = True
    try:
        r.county(config.STORY_FIPS)
    except Exception:
        ok = False
    return {"status": "ok", "time": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "db": ok}


@app.get("/fields")
def fields(request: Request, all: bool = False, limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
    r = repo(request)
    if all:
        rows, total = r.list_fields(None, limit, offset), r.count_fields()
    else:
        rows = r.list_fields(r.demo_field_ids())
        total = len(rows)
    return {"county_fips": config.STORY_FIPS, "demo_only": not all, "total": total,
            "fields": [{**x, "centroid": {"type": "Point", "coordinates": [x.pop("lon"), x.pop("lat")]}} for x in rows],
            "notes": "Demo fields = the 12 Story County CSB fields with OpenET + HLS series. CSB polygons are not ownership parcels."}


@app.get("/field/{field_id}/profile")
def profile(field_id: str, request: Request):
    out = services.profile(repo(request), field_id)
    return out if out is not None else _not_found("field_id")


@app.get("/field/{field_id}/bare-periods")
def bare_periods(field_id: str, request: Request):
    out = services.bare_periods(repo(request), field_id)
    return out if out is not None else _not_found("field_id")


@app.get("/field/{field_id}/vulnerable-seasons")
def vulnerable_seasons(field_id: str, request: Request):
    out = services.vulnerable_seasons(repo(request), field_id=field_id)
    return out if out is not None else _not_found("field_id")


@app.get("/field/{field_id}/climate/history")
def climate_history(field_id: str, request: Request, years: int = Query(5, ge=1, le=5)):
    out = services.climate_history(repo(request), field_id, years)
    return out if out is not None else _not_found("field_id")


@app.get("/field/{field_id}/climate/outlook")
def climate_outlook(field_id: str, request: Request):
    r = repo(request)
    f = r.field(field_id)
    if not f:
        _not_found("field_id")
    return services.climate_outlook(r, f["county_fips"].strip(), field_id)


@app.get("/county/{fips}")
def county(fips: str, request: Request):
    out = services.county_summary(repo(request), fips)
    return out if out is not None else _not_found("county_fips")


@app.get("/county/{fips}/vulnerable-seasons")
def county_vulnerable_seasons(fips: str, request: Request):
    out = services.vulnerable_seasons(repo(request), county_fips=fips)
    return out if out is not None else _not_found("county_fips")


@app.get("/locate")
def locate(request: Request, lat: float = Query(..., ge=-90, le=90), lon: float = Query(..., ge=-180, le=180)):
    r = repo(request)
    f = r.locate(lat, lon)
    if f:
        return {"in_service_area": True, "service_tier": "field", "field_id": f["field_id"], "county_fips": f["county_fips"].strip(),
                "state_alpha": f["state_alpha"], "area_ha": round(f["area_ha"], 2) if f["area_ha"] else None,
                "geometry": f["geometry"], "message": None}
    c = r.county_at(lat, lon)
    if c:
        return {"in_service_area": False, "service_tier": "county", "field_id": None, "county_fips": c["county_fips"],
                "state_alpha": c["state_alpha"], "area_ha": None, "geometry": None,
                "message": "Outside the field-level service area (Story County, IA). County-level summary: /county/" + c["county_fips"]}
    return {"in_service_area": False, "service_tier": None, "field_id": None, "county_fips": None, "state_alpha": None,
            "area_ha": None, "geometry": None, "message": "Outside the service area."}


@app.get("/glossary")
def glossary():
    return glossary_mod.glossary()


@app.get("/evidence/search")
def evidence_search(request: Request, q: str = Query(..., min_length=1), strategy: str | None = None):
    return _evidence(repo(request), q, strategy)


def _evidence(r, q: str, strategy: str | None) -> dict:
    try:
        rows = r.evidence_search(q, strategy)
    except Exception:
        rows = []
    hits = [{"source_title": x["source_title"], "doi": x.get("doi"), "url": x.get("url"), "quote": x["quote"],
             "license": x.get("license") or "see source page"} for x in rows if x.get("doi") or x.get("url")]
    return {"query": q, "strategy_code": strategy, "hits": hits, "insufficient_evidence": not hits}


# ---------------------------------------------------------------------------------------------------
class Constraints(BaseModel):
    water_limited: bool = False
    water_cap_mm: float | None = None
    equipment: list[str] = []
    market: list[str] = []


class Priorities(BaseModel):
    water: float = 0.25
    soil: float = 0.25
    stability: float = 0.25
    income: float = 0.25


class SimulateRequest(BaseModel):
    field_id: str | None = None
    county_fips: str | None = None
    n: int = Field(500, ge=50, le=5000)
    seed: int = 42
    candidate_ids: list[str] | None = None
    strategies: list[str] | None = Field(None, description="Strategy codes A-D (alternative to candidate_ids)")
    priorities: Priorities = Priorities()
    constraints: Constraints = Constraints()
    scenarios: bool = True


class CompareRequest(BaseModel):
    field_id: str
    current_rotation: str | None = "C-S"
    priorities: Priorities = Priorities()
    constraints: Constraints = Constraints()
    candidate_ids: list[str] | None = None
    n: int = Field(500, ge=50, le=5000)
    seed: int = 42


class CandidatesRequest(BaseModel):
    field_id: str
    current_rotation: str | None = "C-S"
    selected_options: list[str] = Field(default_factory=list, max_length=3)
    constraints: Constraints = Constraints()


class ExplainRequest(BaseModel):
    field_id: str
    candidate_id: str | None = None
    strategy_code: str | None = None
    question: str = Field(..., min_length=1, max_length=2000)
    lang: str = "ko"


def _run(r, *, field_id=None, county_fips=None, n=500, seed=42, candidate_ids=None, strategies=None, priorities=None,
         constraints=None, scenarios=True) -> dict:
    if strategies and not candidate_ids:
        bad = [s for s in strategies if s not in engine.CODE_TO_CANDIDATE]
        if bad:
            raise APIError(422, "invalid_request", f"Unknown strategy code(s): {bad}")
        candidate_ids = [engine.CODE_TO_CANDIDATE[s] for s in strategies]
    if not field_id and not county_fips:
        raise APIError(422, "invalid_request", "field_id or county_fips is required")
    try:
        sim = engine.simulate(r, field_id=field_id, county_fips=county_fips, n=n, seed=seed, candidate_ids=candidate_ids,
                              priorities=priorities, constraints=constraints, scenarios=scenarios)
    except KeyError as exc:
        raise APIError(404, "not_found", str(exc).strip("'"))
    except ValueError as exc:
        raise APIError(422, "invalid_request", str(exc))
    except LookupError as exc:
        raise APIError(404, "not_found", str(exc))
    cards.build(sim, evidence_lookup=lambda q, code: [
        {"doi": h["doi"], "url": h["url"], "quote": h["quote"]} for h in _evidence(r, q, code)["hits"]])
    return sim


@app.post("/simulate")
def simulate(req: SimulateRequest, request: Request):
    return _run(repo(request), field_id=req.field_id, county_fips=req.county_fips, n=req.n, seed=req.seed,
                candidate_ids=req.candidate_ids, strategies=req.strategies, priorities=req.priorities.model_dump(),
                constraints=req.constraints.model_dump(), scenarios=req.scenarios)


@app.post("/strategies/compare")
def compare(req: CompareRequest, request: Request):
    sim = _run(repo(request), field_id=req.field_id, n=req.n, seed=req.seed, candidate_ids=req.candidate_ids,
               priorities=req.priorities.model_dump(), constraints=req.constraints.model_dump())
    return cards.compare_response(sim)


@app.post("/rotations/candidates")
def rotation_candidates(req: CandidatesRequest, request: Request):
    bad = [o for o in req.selected_options if o not in ("cover_rye", "small_grain", "alfalfa")]
    if bad:
        raise APIError(422, "invalid_request", f"Unknown option(s): {bad}")
    if not repo(request).field(req.field_id):
        _not_found("field_id")
    cands = engine.rotation_candidates(req.selected_options, req.constraints.model_dump())
    return {"field_id": req.field_id, "n_options": len(set(req.selected_options)), "candidates": cands}


@app.get("/validation/backtest")
def backtest(request: Request, field_id: str, year: int = 2012):
    r = repo(request)
    try:
        out = services.backtest(r, field_id, year, lambda fid, y: engine.backtest_year(r, fid, y))
    except ValueError as exc:
        raise APIError(422, "invalid_request", str(exc))
    return out if out is not None else _not_found("field_id")


@app.post("/explain")
def explain(req: ExplainRequest, request: Request):
    r = repo(request)
    if not r.field(req.field_id):
        _not_found("field_id")

    def trimmed_compare(args):
        c = cards.compare_response(_run(r, field_id=args["field_id"]))
        for s in c["strategies"]:
            s.pop("evidence", None)
        c.pop("assumptions", None)
        return c

    def trimmed_profile(args):
        p = services.profile(r, args["field_id"]) or {"error": {"code": "not_found", "message": "Unknown field_id"}}
        p.pop("geometry", None)
        return p

    tools = {
        "get_profile": trimmed_profile,
        "compare_strategies": trimmed_compare,
        "get_climate_history": lambda a: services.climate_history(r, a["field_id"], int(a.get("years") or 5)),
        "get_outlook": lambda a: services.climate_outlook(r, r.field(a["field_id"])["county_fips"].strip(), a["field_id"]),
        "get_vulnerable_seasons": lambda a: services.vulnerable_seasons(r, field_id=a["field_id"]),
        "search_evidence": lambda a: _evidence(r, a.get("q") or "", a.get("strategy_code")),
    }
    client = getattr(request.app.state, "llm_client", None)
    model = getattr(request.app.state, "llm_model", None)
    try:
        return explain_mod.explain(req.model_dump(), tools, client=client, model=model or config.llm_settings()["model"])
    except explain_mod.LLMUnavailable as exc:
        raise APIError(503, "llm_unavailable", str(exc))
    except Exception as exc:  # provider errors after retries
        log.warning("explain failed: %s", type(exc).__name__)
        raise APIError(502, "llm_error", f"LLM provider error ({type(exc).__name__})")
