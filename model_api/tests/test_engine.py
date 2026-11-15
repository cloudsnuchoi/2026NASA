from model_api import cards, engine


def test_simulate_deterministic_with_seed(fake_repo):
    a = engine.simulate(fake_repo, field_id="TEST-FIELD-0001", n=100, seed=7)
    b = engine.simulate(fake_repo, field_id="TEST-FIELD-0001", n=100, seed=7)
    assert a["run_id"] == b["run_id"] and "s7" in a["run_id"]
    assert [s["composite"] for s in a["strategies"]] == [s["composite"] for s in b["strategies"]]


def test_simulate_all_strategies_cards_and_assumptions(fake_repo):
    sim = engine.simulate(fake_repo, field_id="TEST-FIELD-0001", n=100, seed=1)
    cards.build(sim)
    codes = [s["strategy_code"] for s in sim["strategies"]]
    assert codes == ["A", "B", "C", "D"]
    assert sorted(s["rank"] for s in sim["strategies"]) == [1, 2, 3, 4]
    pros = []
    for s in sim["strategies"]:
        for k in ("why", "evidence", "benefits", "info_gaps", "local_review_risks"):
            assert s[k], (s["strategy_code"], k)
        assert len(s["pros"]) == 3 and len(s["cons"]) >= 1
        pros += s["pros"]
        assert set(s["scores"]) == {"n_cycle_index", "erosion_index", "organic_matter_index", "pest_break_index",
                                    "water_use_index", "forage_index", "market_index"}
        assert all(0 <= v <= 1 for v in s["scores"].values())
        c = s["composite"]
        assert c["cvar"] <= c["p10"] <= c["p50"] <= c["p90"]
        assert {r["horizon"] for r in s["scenario_results"]} == {"historical", "next_season", "2030s"}
        assert "_sc" not in s
    assert len(pros) == len(set(pros)), "pros must not repeat across tabs"
    d = next(s for s in sim["strategies"] if s["strategy_code"] == "D")
    assert cards.ALFALFA_WATER_RISK in d["local_review_risks"]
    a = next(s for s in sim["strategies"] if s["strategy_code"] == "A")
    assert a["display"]["water_use_pct"]["p50"] == 0.0
    items = {x["item"] for x in sim["assumptions"]}
    assert {"kc_corn_mid", "elevation_m", "rule_priors", "crop_calendar"} <= items
    assert "awc_cm_cm" not in items  # measured from SSURGO for the field
    text = str(sim)
    assert "kg/ha" not in text.replace("no yields in kg/ha or t/ha", "")


def test_county_tier_uses_soil_defaults(fake_repo):
    sim = engine.simulate(fake_repo, county_fips="31055", n=60, seed=1)
    assert sim["tier"] == "county" and sim["field_id"] is None
    assert "awc_cm_cm" in {x["item"] for x in sim["assumptions"]}


def test_missing_scenarios_are_noted(monkeypatch):
    from model_api.tests.conftest import FakeRepo

    sim = engine.simulate(FakeRepo(with_scenarios=False), field_id="TEST-FIELD-0001", n=60, seed=2)
    assert all(len(s["scenario_results"]) == 1 for s in sim["strategies"])
    assert any("GEOS-S2S rows not loaded" in n for n in sim["notes"])


def test_priorities_normalized_and_water_boost():
    norm, applied, boosted = engine.normalize_priorities({"water": 1, "soil": 1, "stability": 0, "income": 0}, {"water_limited": True})
    assert norm == {"water": 0.5, "soil": 0.5, "stability": 0.0, "income": 0.0}
    assert boosted and applied["water"] > norm["water"]
    assert abs(sum(applied.values()) - 1) < 1e-3


def test_rotation_candidates_power_set():
    c = engine.rotation_candidates(["cover_rye", "small_grain"])
    assert [x["candidate_id"] for x in c] == ["C-S", "C-S+cover_rye", "C-S-W", "C-S-W+cover_rye"]
    assert [x["strategy_code"] for x in c] == ["A", "B", None, "C"]
    assert len(engine.rotation_candidates(["cover_rye", "small_grain", "alfalfa"])) == 8


def test_matlab_overrides(tmp_path, monkeypatch, fake_repo):
    (tmp_path / "calibration_params.csv").write_text("param,value,unit,method,source,notes\nkc_corn_mid,1.10,-,test,test,\n")
    monkeypatch.setenv("FS_MATLAB_DIR", str(tmp_path))
    ov, notes = engine.load_overrides(fake_repo)
    assert ov == {"kc_corn_mid": 1.10}
    assert any("field_dekad.csv not found" in n for n in notes)
    sim = engine.simulate(fake_repo, field_id="TEST-FIELD-0001", n=60, seed=3)
    assert "kc_corn_mid" not in {x["item"] for x in sim["assumptions"]}


def test_backtest_year(fake_repo):
    out = engine.backtest_year(fake_repo, "TEST-FIELD-0001", 2012)
    assert set(out) == set("ABCD")
    assert out["A"]["modelled_crop"] == "corn"  # CDL 2012 = Corn in the fake history
