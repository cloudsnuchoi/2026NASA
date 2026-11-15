"""Live end-to-end QA against a running model_api + the real `fieldshift` DB.

Run the server first (read-only DB):
    PGHOST=127.0.0.1 PGPORT=5433 PGUSER=hk PGDATABASE=fieldshift \
        .venv/bin/uvicorn model_api.main:app --host 127.0.0.1 --port 8099
    QA_API_BASE=http://127.0.0.1:8099 .venv/bin/python -m pytest -q model_api/tests/test_e2e_live.py

The whole module is skipped when the server or its DB is unreachable, so CI stays green.
Known open defects are marked ``xfail(strict=False)`` and documented in docs/QA-REPORT.md.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import os

import pytest

httpx = pytest.importorskip("httpx")

BASE = os.environ.get("QA_API_BASE", "http://127.0.0.1:8099").rstrip("/")
STORY = "19169"
TIER1 = ["17113", "31109", "18157"]  # McLean IL, Lancaster NE, Tippecanoe IN
POINT_OTHER_STATE = (40.4909, -88.8473)  # McLean County, IL
POINT_OUTSIDE = (39.7392, -104.9903)  # Denver, CO (outside the 12-state Corn Belt)
SEVEN_AXES = ("n_cycle_index", "erosion_index", "organic_matter_index", "pest_break_index", "water_use_index",
              "forage_index", "market_index")
CARD5 = ("why", "evidence", "benefits", "info_gaps", "local_review_risks")
OPTIMUM_KEYS = {"best", "best_strategy", "optimal", "optimum", "recommended", "recommendation", "winner"}
EPS = 1e-6


def _reachable() -> tuple[bool, list[str]]:
    try:
        h = httpx.get(f"{BASE}/health", timeout=3).json()
        if not h.get("db"):
            return False, []
        return True, [f["field_id"] for f in httpx.get(f"{BASE}/fields", timeout=20).json()["fields"]]
    except Exception:
        return False, []


UP, DEMO = _reachable()
pytestmark = pytest.mark.skipif(not UP, reason=f"model_api/DB not reachable at {BASE}")


def _strict(text: str):
    def bad(c):
        raise ValueError(f"non-finite JSON constant {c}")
    return json.loads(text, parse_constant=bad)


def get(path: str, **params):
    r = httpx.get(f"{BASE}{path}", params=params, timeout=60)
    return r.status_code, _strict(r.text)


def post(path: str, body: dict):
    r = httpx.post(f"{BASE}{path}", json=body, timeout=120)
    return r.status_code, _strict(r.text)


# ---------------------------------------------------------------------------------------------------
# generic invariants
# ---------------------------------------------------------------------------------------------------
def walk(x, path="$"):
    yield path, x
    if isinstance(x, dict):
        for k, v in x.items():
            yield from walk(v, f"{path}.{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from walk(v, f"{path}[{i}]")


def check_finite_and_ordered(doc) -> None:
    for p, v in walk(doc):
        if isinstance(v, float):
            assert math.isfinite(v), f"non-finite at {p}"
        if isinstance(v, dict):
            if all(v.get(k) is not None for k in ("p10", "p50", "p90")):
                assert v["p10"] <= v["p50"] + EPS and v["p50"] <= v["p90"] + EPS, f"P10<=P50<=P90 violated at {p}: {v}"
                if v.get("cvar") is not None:  # CVaR sits in one tail (README: lower for indices, upper for deficits)
                    assert v["cvar"] <= v["p10"] + EPS or v["cvar"] >= v["p90"] - EPS, f"CVaR not in a tail at {p}: {v}"
            if all(v.get(k) is not None for k in ("min", "p50", "max")):
                assert v["min"] <= v["p50"] + EPS <= v["max"] + 2 * EPS, f"min<=p50<=max violated at {p}: {v}"


def check_no_single_optimum(doc) -> None:
    for p, v in walk(doc):
        if isinstance(v, dict):
            hit = OPTIMUM_KEYS & set(v)
            assert not hit, f"single-optimum key {hit} at {p}"
    assert "not a single optimum" in doc["disclaimer"].lower()


def check_assumptions(doc) -> None:
    notes = " ".join(doc.get("notes", []))
    if "documented defaults" in notes or "defaults used" in notes:
        assert doc["assumptions"], "defaults used but assumptions[] empty"
    for a in doc["assumptions"]:
        assert {"item", "value", "unit", "source"} <= set(a), a
        assert a["source"], a
    assert isinstance(doc["info_gaps"], list) and doc["info_gaps"]


def check_strategy_cards(strats: list[dict], compare: bool) -> None:
    assert len(strats) >= 3, "SOT: at least 3 strategies, default 4"
    codes = [s["strategy_code"] for s in strats if s["strategy_code"]]
    assert set("ABCD") <= set(codes), codes
    assert sorted(s["rank"] for s in strats) == list(range(1, len(strats) + 1))
    all_pros = []
    for s in strats:
        for k in CARD5:
            assert k in s, f"{s['strategy_code']}: card item {k} missing"
        assert isinstance(s["why"], str) and s["why"].strip()
        assert s["evidence"] and all(e.get("url") or e.get("doi") for e in s["evidence"])
        assert s["benefits"] and s["local_review_risks"] and isinstance(s["info_gaps"], list)
        assert len(s["pros"]) == 3 and len(s["cons"]) >= 1
        all_pros += s["pros"]
        for ax in SEVEN_AXES:
            assert 0.0 <= s["scores"][ax] <= 1.0, (s["strategy_code"], ax, s["scores"][ax])
        q = s if compare else s["composite"]
        assert q["cvar"] <= q["p10"] + EPS, f"{s['strategy_code']}: index CVaR must be <= P10: {q}"
        d = s["display"]
        assert d["basis"] == "relative index change vs strategy A; not a guarantee"
        assert d["revenue_pct"] == {"p10": None, "p50": None, "p90": None} or all(
            d["revenue_pct"][k] is not None for k in ("p10", "p50", "p90"))
        if s["strategy_code"] == "A":
            assert d["vegetation_pct"]["p50"] == 0.0 and d["water_use_pct"]["p50"] == 0.0
        for r in s["scenario_results"]:
            assert r["unit"] == "mm/yr" and r["metric"] == "season_water_deficit_mm"
            assert r["cvar"] >= r["p90"] - EPS, f"deficit CVaR must be >= P90 (upper tail): {r}"
            assert r["n_members"] >= 1
            if r["source_id"] == "nex_gddp":
                assert r["scenario"] in ("ssp245", "ssp585")
    assert len(set(all_pros)) == len(all_pros), "SOT: pros must not repeat across tabs"


def check_error(doc, code: str) -> None:
    assert set(doc) == {"error"} and doc["error"]["code"] == code and doc["error"]["message"]


# ---------------------------------------------------------------------------------------------------
# global endpoints
# ---------------------------------------------------------------------------------------------------
def test_health():
    st, d = get("/health")
    assert st == 200 and d["status"] == "ok" and d["db"] is True
    dt.datetime.strptime(d["time"], "%Y-%m-%dT%H:%M:%SZ")


def test_fields_demo_list():
    st, d = get("/fields")
    # 12 Story fields + contrast demo fields in other Corn Belt counties (feat/contrast-fields)
    assert st == 200 and d["demo_only"] is True and d["total"] == len(d["fields"]) >= 12
    assert sum(f["county_fips"].strip() == STORY for f in d["fields"]) == 12
    for f in d["fields"]:
        lon, lat = f["centroid"]["coordinates"]
        assert -105.0 < lon < -80.0 and 36.0 < lat < 49.5  # Corn Belt 12 states
        assert f["area_ha"] > 0


def test_glossary():
    st, d = get("/glossary")
    assert st == 200 and d["terms"]
    for t in d["terms"]:
        assert {"term_id", "ko", "en", "short_ko", "short_en", "source_url"} <= set(t)


def test_evidence_search_contract():
    st, d = get("/evidence/search", q="cereal rye", strategy="B")
    assert st == 200 and d["query"] == "cereal rye" and d["strategy_code"] == "B"
    assert d["insufficient_evidence"] is (not d["hits"])
    for h in d["hits"]:
        assert h.get("doi") or h.get("url")


def test_unknown_ids_use_sot_error_shape():
    st, d = get("/field/NOPE/profile")
    assert st == 404
    check_error(d, "not_found")
    st, d = get("/county/00000")
    assert st == 404
    check_error(d, "not_found")
    st, d = post("/simulate", {"field_id": "NOPE"})
    assert st == 404
    check_error(d, "not_found")
    st, d = post("/simulate", {})
    assert st == 422
    check_error(d, "invalid_request")


# ---------------------------------------------------------------------------------------------------
# per demo field
# ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("fid", DEMO)
def test_profile(fid):
    st, d = get(f"/field/{fid}/profile")
    assert st == 200
    check_finite_and_ordered(d)
    for k in ("field_id", "csb_version", "county_fips", "state_alpha", "area_ha", "current_rotation", "centroid", "geometry",
              "soil_summary", "disclaimer", "sources", "region_label", "precip_mm_yr", "et_mm_day", "et0_mm_day", "ndvi_peak",
              "ndvi_class", "t2m_mean_c", "cdl_history", "soil", "vision", "hero_state", "period", "info_gaps"):
        assert k in d, k
    assert d["field_id"] == fid and len(d["county_fips"].strip()) == 5
    assert d["centroid"]["type"] == "Point" and d["geometry"]["type"] in ("Polygon", "MultiPolygon")
    assert d["ndvi_class"] in ("good", "fair", "low", None)
    assert d["hero_state"] in ("normal", "drought", "wet", "heat", "frost")
    assert 500 < d["precip_mm_yr"] < 1200, "Story County annual precip should be ~800-950 mm"
    assert 5 < d["t2m_mean_c"] < 14
    if d["ndvi_peak"] is not None:
        assert 0 < d["ndvi_peak"] <= 1
    if d["et_mm_day"] is not None:
        assert 0.5 < d["et_mm_day"] < 5
    assert {"model_id", "crop_pred", "bare_fraction", "agreement_with_cdl"} <= set(d["vision"])
    if d["vision"]["crop_pred"] is None:
        assert any("Prithvi" in g for g in d["info_gaps"])
    for k in ("om_pct", "k_factor", "awc_cm_cm"):
        assert k in d["soil"]
    years = [c["year"] for c in d["cdl_history"]]
    assert years == sorted(years, reverse=True)


@pytest.mark.parametrize("fid", DEMO)
def test_bare_periods(fid):
    st, d = get(f"/field/{fid}/bare-periods")
    assert st == 200 and d["field_id"] == fid and isinstance(d["periods"], list)
    for p in d["periods"]:
        s, e = dt.date.fromisoformat(p["start"]), dt.date.fromisoformat(p["end"])
        assert s <= e and p["bare_days"] == (e - s).days + 1 > 0
        assert {"optical_dates", "cdl_year_label", "method", "gaps"} <= set(p["evidence"])


@pytest.mark.parametrize("fid", DEMO)
def test_vulnerable_seasons(fid):
    st, d = get(f"/field/{fid}/vulnerable-seasons")
    assert st == 200
    check_finite_and_ordered(d)
    assert {"field_id", "period", "seasons", "sources"} <= set(d)
    assert {s["season"] for s in d["seasons"]} == {"winter", "spring", "summer", "fall"}
    for s in d["seasons"]:
        assert {"season", "hazards", "precip_anomaly_mm", "t2m_anomaly_c", "smap_sm_anomaly", "notes"} <= set(s)
        assert "not a field-precise" in s["notes"]
    assert all(x.get("native_resolution") for x in d["sources"])


@pytest.mark.parametrize("fid", DEMO)
def test_climate_history(fid):
    st, d = get(f"/field/{fid}/climate/history", years=5)
    assert st == 200 and d["field_id"] == fid
    check_finite_and_ordered(d)
    ys = [y["year"] for y in d["years"]]
    assert 1 <= len(ys) <= 5 and ys == sorted(ys, reverse=True)
    for y in d["years"]:
        assert {"year", "precip_mm", "et_mm", "ndvi_peak", "t2m_mean_c", "crop_cdl", "naip_thumb_url"} <= set(y)
        if y["precip_mm"] is not None:
            assert 300 < y["precip_mm"] < 1600
        if y["ndvi_peak"] is not None:
            assert 0 < y["ndvi_peak"] <= 1


@pytest.mark.parametrize("fid", DEMO)
def test_climate_outlook_is_distribution_only(fid):
    st, d = get(f"/field/{fid}/climate/outlook")
    assert st == 200
    check_finite_and_ordered(d)
    assert "not a forecast" in d["label"].lower()
    assert d["native_resolution_note"]
    ns = d["next_season"]
    if ns is None:
        assert d["info_gaps"]
    else:
        assert ns["source_id"] == "geos_s2s" and ns["n_members"] >= 2
        assert {"p10", "p50", "p90"} <= set(ns["pr_anomaly_pct"]) and {"p10", "p50", "p90"} <= set(ns["tas_anomaly_c"])
    for m in d["mid_century"]:
        assert m["source_id"] == "nex_gddp" and m["scenario"] in ("ssp245", "ssp585") and m["n_models"] >= 1
        assert {"min", "p50", "max"} <= set(m["pr_change_pct"])


@pytest.mark.parametrize("fid", DEMO)
def test_rotation_candidates(fid):
    st, d = post("/rotations/candidates", {"field_id": fid, "selected_options": ["cover_rye", "small_grain", "alfalfa"]})
    assert st == 200 and d["n_options"] == 3 and len(d["candidates"]) == 8
    assert len({c["candidate_id"] for c in d["candidates"]}) == 8


@pytest.mark.parametrize("fid", DEMO)
def test_simulate_field(fid):
    st, d = post("/simulate", {"field_id": fid, "n": 500, "seed": 42})
    assert st == 200
    check_finite_and_ordered(d)
    assert d["tier"] == "field" and d["field_id"] == fid and d["unit"] == "index_0_1"
    assert d["run_id"].endswith("-n500-s42") and "10 %" in d["cvar_definition"]
    assert abs(sum(d["priorities_normalized"].values()) - 1) < 1e-3
    check_no_single_optimum(d)
    check_assumptions(d)
    check_strategy_cards(d["strategies"], compare=False)
    for s in d["strategies"]:
        assert {r["horizon"] for r in s["scenario_results"]} >= {"historical"}
        for m, q in s["metrics"].items():
            assert q["unit"] in ("mm/yr", "days/yr"), m
            if q["unit"] == "days/yr":
                assert 0 <= q["p10"] and q["p90"] <= 366, (m, q)
            else:
                assert q["p10"] >= 0 and q["p90"] < 3000, (m, q)
    if all(s["display"]["revenue_pct"]["p50"] is None for s in d["strategies"]):
        assert any("price" in g.lower() for g in d["info_gaps"])


@pytest.mark.parametrize("fid", DEMO)
def test_compare_field(fid):
    body = {"field_id": fid, "priorities": {"water": 0.3, "soil": 0.4, "stability": 0.2, "income": 0.1},
            "constraints": {"water_limited": False}}
    st, d = post("/strategies/compare", body)
    assert st == 200
    check_finite_and_ordered(d)
    for k in ("field_id", "priorities_normalized", "run_id", "unit", "strategies", "disclaimer"):
        assert k in d, k
    assert d["unit"] == "index_0_1"
    check_no_single_optimum(d)
    check_strategy_cards(d["strategies"], compare=True)
    assert d["assumptions"]
    labels = [s["goal_label"] for s in d["strategies"]]
    assert len(set(labels)) == len(labels), f"goal labels should be distinct: {labels}"


@pytest.mark.parametrize("fid", DEMO)
def test_backtest_2012_contract(fid):
    st, d = get("/validation/backtest", field_id=fid, year=2012)
    assert st == 200
    check_finite_and_ordered(d)
    assert d["years"] == [2012] and d["yield_unit"] == "bu/ac" and "2012" in d["county_yield_bu_ac"]
    assert [r["strategy_code"] for r in d["results"]] == list("ABCD")
    for r in d["results"]:
        m = r["metrics"]
        assert m["season_water_deficit_mm"] >= 0 and 0 <= m["winter_bare_days"] <= 181
        assert r["notes"]


@pytest.mark.xfail(strict=False, reason="QA-REPORT E3: backtest forces every strategy onto the observed cash crop "
                                        "and the bucket refills before planting, so A-D deficits are identical")
@pytest.mark.parametrize("fid", DEMO[:3])
def test_backtest_2012_differentiates_strategies(fid):
    _, d = get("/validation/backtest", field_id=fid, year=2012)
    deficits = {r["metrics"]["season_water_deficit_mm"] for r in d["results"]}
    assert len(deficits) > 1, f"all strategies show the same 2012 deficit {deficits}"


@pytest.mark.xfail(strict=False, reason="QA-REPORT E1: engine.py adds 'County IMERG rows not loaded' unconditionally "
                                        "although county_imerg_daily now has rows for all 1,122 counties")
def test_imerg_gap_note_matches_db():
    _, c = get(f"/county/{STORY}")
    imerg_loaded = not any("IMERG" in g for g in c["info_gaps"])  # county_summary checks the table
    _, s = post("/simulate", {"field_id": DEMO[0]})
    _, p = get(f"/field/{DEMO[0]}/profile")
    if imerg_loaded:
        assert not any("IMERG rows not loaded" in g for g in s["info_gaps"])
        assert not any("IMERG not loaded" in g for g in p["info_gaps"])


# ---------------------------------------------------------------------------------------------------
# tier 1 counties
# ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("fips", TIER1)
def test_county_summary(fips):
    st, d = get(f"/county/{fips}")
    assert st == 200
    check_finite_and_ordered(d)
    assert d["county_fips"] == fips and d["tier"] == "county" and d["field_level_available"] is False
    assert 400 < d["climate"]["precip_mm_yr"] < 1500 and 3 < d["climate"]["t2m_mean_c"] < 16
    assert d["yield_unit"].startswith("bu/ac")
    for yr, v in d["yield_bu_ac"].items():
        if v.get("corn") is not None:
            assert 20 < v["corn"] < 300, (yr, v)
        if v.get("soybeans") is not None:
            assert 5 < v["soybeans"] < 100, (yr, v)
    share = sum(d["crop_share"]["latest"].values())
    assert 0.3 < share <= 1.0 + 1e-3, f"crop shares (subset of classes) should sum to <= 1: {share}"
    if d["smap"]:
        assert d["smap"]["unit"] == "cm3/cm3" and 0 < d["smap"]["mean_all"] < 0.6
        assert "not field-precise" in d["smap"]["notes"]
    st, v = get(f"/county/{fips}/vulnerable-seasons")
    assert st == 200 and len(v["seasons"]) == 4
    check_finite_and_ordered(v)


@pytest.mark.parametrize("fips", TIER1)
def test_simulate_county(fips):
    st, d = post("/simulate", {"county_fips": fips})
    assert st == 200
    check_finite_and_ordered(d)
    assert d["tier"] == "county" and d["field_id"] is None and d["county_fips"] == fips
    assert any("Tier 1 county run" in g for g in d["info_gaps"])
    assert any(a["item"] == "awc_cm_cm" for a in d["assumptions"]), "county run must list default soil AWC"
    check_no_single_optimum(d)
    check_assumptions(d)
    check_strategy_cards(d["strategies"], compare=False)


# ---------------------------------------------------------------------------------------------------
# /locate
# ---------------------------------------------------------------------------------------------------
def test_locate_story_field():
    _, f = get(f"/field/{DEMO[-1]}/profile")
    lon, lat = f["centroid"]["coordinates"]
    st, d = get("/locate", lat=lat, lon=lon)
    assert st == 200 and d["service_tier"] == "field" and d["in_service_area"] is True
    assert d["field_id"] and d["county_fips"] == STORY and d["geometry"]["type"] in ("Polygon", "MultiPolygon")


def test_locate_other_corn_belt_state():
    st, d = get("/locate", lat=POINT_OTHER_STATE[0], lon=POINT_OTHER_STATE[1])
    assert st == 200 and d["service_tier"] == "county" and d["county_fips"] == "17113" and d["state_alpha"] == "IL"
    assert d["field_id"] is None and d["in_service_area"] is False and d["message"]


def test_locate_outside():
    st, d = get("/locate", lat=POINT_OUTSIDE[0], lon=POINT_OUTSIDE[1])
    assert st == 200 and d["service_tier"] is None and d["in_service_area"] is False and d["field_id"] is None
    assert d["message"] == "Outside the service area."


@pytest.mark.xfail(strict=False, reason="QA-REPORT A4: a Story County point off any CSB field is told it is outside Story")
def test_locate_story_non_field_message():
    st, d = get("/locate", lat=42.0267, lon=-93.6170)  # downtown Ames: in Story, not on a CSB polygon
    assert st == 200 and d["county_fips"] == STORY and d["service_tier"] == "county"
    assert "Outside the field-level service area (Story County" not in (d["message"] or "")


# ---------------------------------------------------------------------------------------------------
# /explain (LLM, optional)
# ---------------------------------------------------------------------------------------------------
def test_explain_one_field():
    if not DEMO:
        pytest.skip("no demo fields")
    st, d = post("/explain", {"field_id": DEMO[0], "strategy_code": "B", "lang": "en",
                              "question": "Why might strategy B reduce winter erosion on this field?"})
    if st == 503 and d["error"]["code"] == "llm_unavailable":
        pytest.skip("LLM_API_KEY not configured on the server")
    assert st == 200, d
    for k in ("answer", "tool_calls", "citations", "insufficient_evidence", "unverified_numbers"):
        assert k in d, k
    assert d["answer"].strip()
    for t in d["tool_calls"]:
        assert "endpoint" in t and isinstance(t["json_paths_used"], list)
    _, ev = get("/evidence/search", q="cereal rye", strategy="B")
    if ev["insufficient_evidence"]:
        assert d["citations"] == [] or d["insufficient_evidence"] is True
