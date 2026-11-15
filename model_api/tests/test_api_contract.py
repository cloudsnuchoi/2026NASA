"""Contract tests: responses carry every key of the SOT 6 example JSON (extra keys allowed)."""

F = "TEST-FIELD-0001"

SOT_PROFILE = {"field_id", "csb_version", "county_fips", "state_alpha", "area_ha", "current_rotation", "centroid", "geometry",
               "soil_summary", "disclaimer", "sources", "region_label", "precip_mm_yr", "et_mm_day", "et0_mm_day", "ndvi_peak",
               "ndvi_class", "t2m_mean_c", "cdl_history", "soil", "vision", "hero_state", "period", "info_gaps"}
SOT_COMPARE = {"field_id", "priorities_normalized", "run_id", "unit", "strategies", "disclaimer"}
SOT_STRATEGY = {"strategy_code", "label", "why", "evidence", "benefits", "info_gaps", "local_review_risks", "scores", "p10", "p50",
                "p90", "cvar", "candidate_id", "rank", "goal_label", "display", "pros", "cons", "unique_feature", "weights_applied",
                "water_weight_boosted", "scenario_results"}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok" and r.json()["time"].endswith("Z")


def test_not_found_format(client):
    r = client.get("/field/NOPE/profile")
    assert r.status_code == 404
    assert r.json() == {"error": {"code": "not_found", "message": "Unknown field_id"}}
    assert client.get("/county/99999").json()["error"]["code"] == "not_found"
    assert client.post("/simulate", json={"field_id": "NOPE"}).json()["error"]["code"] == "not_found"


def test_profile_contract(client):
    p = client.get(f"/field/{F}/profile").json()
    assert SOT_PROFILE <= set(p)
    assert p["current_rotation"] == "C-S"
    assert p["hero_state"] in {"normal", "drought", "wet", "heat", "frost"}
    assert p["ndvi_class"] in {"good", "fair", "low"}
    assert set(p["soil"]) >= {"om_pct", "k_factor", "awc_cm_cm"}
    assert p["cdl_history"][0]["year"] == 2025


def test_bare_periods_contract(client):
    b = client.get(f"/field/{F}/bare-periods").json()
    assert set(b) >= {"field_id", "periods", "sources"} and b["periods"]
    p = b["periods"][0]
    assert set(p) >= {"start", "end", "bare_days", "evidence"}
    assert set(p["evidence"]) >= {"optical_dates", "cdl_year_label", "method", "gaps"}


def test_vulnerable_seasons_contract(client):
    v = client.get(f"/field/{F}/vulnerable-seasons").json()
    assert set(v) >= {"field_id", "period", "seasons", "sources"}
    assert {s["season"] for s in v["seasons"]} == {"spring", "summer", "fall", "winter"}
    for s in v["seasons"]:
        assert set(s) >= {"season", "hazards", "precip_anomaly_mm", "t2m_anomaly_c", "smap_sm_anomaly", "notes"}


def test_compare_contract(client):
    body = {"field_id": F, "current_rotation": "C-S", "priorities": {"water": 3, "soil": 4, "stability": 2, "income": 1},
            "constraints": {"water_limited": False, "equipment": [], "market": []}, "n": 100}
    c = client.post("/strategies/compare", json=body).json()
    assert SOT_COMPARE <= set(c)
    assert c["priorities_normalized"] == {"water": 0.3, "soil": 0.4, "stability": 0.2, "income": 0.1}
    assert c["unit"] == "index_0_1"
    assert len(c["strategies"]) == 4
    for s in c["strategies"]:
        assert SOT_STRATEGY <= set(s), SOT_STRATEGY - set(s)
        assert set(s["display"]) >= {"vegetation_pct", "water_use_pct", "revenue_pct", "basis"}
        for sr in s["scenario_results"]:
            assert set(sr) >= {"horizon", "source_id", "metric", "p10", "p50", "p90", "cvar"}


def test_simulate_county_and_strategy_subset(client):
    r = client.post("/simulate", json={"county_fips": "31055", "strategies": ["A", "D"], "n": 60}).json()
    assert [s["strategy_code"] for s in r["strategies"]] == ["A", "D"]
    assert r["assumptions"] and r["latency_ms"] is not None
    bad = client.post("/simulate", json={"field_id": F, "strategies": ["Z"]})
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "invalid_request"
    assert client.post("/simulate", json={}).status_code == 422


def test_water_cap_warning(client):
    r = client.post("/simulate", json={"field_id": F, "n": 60, "constraints": {"water_cap_mm": 100}}).json()
    assert r["water_weight_boosted"] is True
    assert all(s["warnings"] for s in r["strategies"])


def test_candidates(client):
    r = client.post("/rotations/candidates", json={"field_id": F, "selected_options": ["cover_rye", "small_grain"]}).json()
    assert r["n_options"] == 2 and len(r["candidates"]) == 4
    assert set(r["candidates"][0]) >= {"candidate_id", "strategy_code", "sequence", "options", "feasible", "warnings"}


def test_backtest_contract(client):
    b = client.get(f"/validation/backtest?field_id={F}&year=2012").json()
    assert set(b) >= {"field_id", "years", "county_yield_bu_ac", "results", "sources"}
    assert b["results"][0]["strategy_code"] == "A" and b["results"][0]["observed_sequence"] == "S-C"
    assert client.get(f"/validation/backtest?field_id={F}&year=1995").status_code == 422


def test_history_outlook_county_locate_glossary(client):
    h = client.get(f"/field/{F}/climate/history?years=5").json()
    assert len(h["years"]) == 5 and h["years"][0]["year"] == 2025
    assert set(h["years"][0]) >= {"year", "precip_mm", "et_mm", "ndvi_peak", "t2m_mean_c", "crop_cdl", "naip_thumb_url"}
    o = client.get(f"/field/{F}/climate/outlook").json()
    assert set(o) >= {"field_id", "next_season", "mid_century", "label", "native_resolution_note"}
    assert o["next_season"]["n_members"] == 2 and len(o["mid_century"]) == 2
    c = client.get("/county/19169").json()
    assert c["name"] == "Story" and c["yield_unit"].startswith("bu/ac")
    loc = client.get("/locate?lat=42.0&lon=-93.5").json()
    assert loc["in_service_area"] and loc["field_id"] == F
    out = client.get("/locate?lat=10&lon=10").json()
    assert out == {**out, "in_service_area": False, "field_id": None, "message": "Outside the service area."}
    g = client.get("/glossary").json()
    assert {"term_id", "ko", "en", "short_ko", "short_en", "source_url"} <= set(g["terms"][0])
    assert client.get("/fields").json()["total"] == 1


def test_evidence_insufficient(client):
    e = client.get("/evidence/search?q=cereal%20rye&strategy=B").json()
    assert e == {"query": "cereal rye", "strategy_code": "B", "hits": [], "insufficient_evidence": True}
