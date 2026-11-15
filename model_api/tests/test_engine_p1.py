"""Regression tests for the QA P1 findings (docs/QA-REPORT.md E1, E3, E4) and the NLDAS context.

Unit tests use the in-memory FakeRepo (no DB). The ``live`` tests run against the read-only DB and skip
when it is unreachable.
"""

from __future__ import annotations

import pytest

from model_api import db, engine, services
from model_api.tests.conftest import FIELD, FakeRepo

IMERG_GAP = "County IMERG rows not loaded"

# three synthetic "fields": different CDL histories and soils
FIELD_VARIANTS = {
    "corn_soy": dict(),
    "corn_corn_soy": dict(crop_names=["Corn", "Corn", "Soybeans"], awc=0.15),
    "continuous_corn": dict(crop_names=["Corn"], awc=0.21, openet_scale=1.15),
}


def _distinct(values) -> int:
    return len({round(v, 1) for v in values})


def _strategy_pairs_differ(per_code: dict[str, tuple[float, float]]) -> bool:
    """Every pair of strategies differs in season_water_deficit_mm or stress_days."""
    codes = sorted(per_code)
    return all(per_code[a] != per_code[b] for i, a in enumerate(codes) for b in codes[i + 1:])


# ---- E3: strategies change the simulation -------------------------------------------------------
@pytest.mark.parametrize("variant", sorted(FIELD_VARIANTS))
def test_simulate_strategies_differ_in_deficit_or_stress(variant):
    sim = engine.simulate(FakeRepo(**FIELD_VARIANTS[variant]), field_id=FIELD, n=120, seed=3, scenarios=False)
    per = {s["strategy_code"]: (s["metrics"]["season_water_deficit_mm"]["p50"], s["metrics"]["stress_days"]["p50"])
           for s in sim["strategies"]}
    assert _strategy_pairs_differ(per), per


@pytest.mark.parametrize("variant", sorted(FIELD_VARIANTS))
def test_backtest_2012_strategies_differ(variant):
    bt = engine.backtest_year(FakeRepo(**FIELD_VARIANTS[variant]), FIELD, 2012)
    per = {c: (m["season_water_deficit_mm"], m["stress_days"]) for c, m in bt.items()}
    assert _strategy_pairs_differ(per), per
    # C and D are averaged over their rotation phases and actually score wheat / alfalfa years
    assert {p["modelled_crop"] for p in bt["C"]["phases"]} == {"corn", "soy", "wheat"}
    assert {"alfalfa1", "alfalfa2"} <= {p["modelled_crop"] for p in bt["D"]["phases"]}
    # A follows the observed CDL crop; B is the same crop with a rye cover
    assert bt["A"]["modelled_sequence"] == bt["B"]["modelled_sequence"]
    assert bt["B"]["winter_bare_days"] < bt["A"]["winter_bare_days"]


def test_cover_crop_changes_water_balance_inputs():
    from model_api import hydro

    prm = engine.Params().as_dict()
    a = hydro._year_arrays("corn", None, None, prm)
    b = hydro._year_arrays("corn", "rye", "rye", prm)
    assert b["living"].sum() > a["living"].sum()          # winter/spring cover ET
    assert b["cn"][150] < a["cn"][150]                    # TR-55 SR + crop residue during the corn season
    assert b["kc"][125] < a["kc"][125]                    # FAO-56 ch.7 mulch evaporation reduction


def test_base_rotation_from_cdl():
    hist = [{"year": 2018 + i, "crop_name": c} for i, c in enumerate(["Soybeans", "Corn"] * 4)]
    assert engine.base_rotation(hist)[0] == ("corn", "soy")
    hist = [{"year": 2018 + i, "crop_name": "Corn"} for i in range(8)]
    assert engine.base_rotation(hist)[0] == ("corn",)
    assert engine.base_rotation([])[0] == ("corn", "soy")


# ---- E4: field-specific inputs matter ------------------------------------------------------------
def test_fields_give_different_composite_p50():
    p50 = {}
    for name, kw in FIELD_VARIANTS.items():
        sim = engine.simulate(FakeRepo(**kw), field_id=FIELD, n=120, seed=3, scenarios=False)
        p50[name] = [s["composite"]["p50"] for s in sim["strategies"]]
        assert sim["inputs"]["baseline_rotation"]
        assert sim["inputs"]["kc_field_scale"] is not None
    assert len({tuple(v) for v in p50.values()}) == len(p50), p50
    a_p50 = {name: v[0] for name, v in p50.items()}
    assert len(set(a_p50.values())) >= 2, a_p50


def test_assumptions_have_sources():
    sim = engine.simulate(FakeRepo(), field_id=FIELD, n=60, seed=1, scenarios=False)
    for a in sim["assumptions"]:
        assert a["source"], a
    items = {a["item"] for a in sim["assumptions"]}
    assert {"baseline_rotation", "cover_crop_effects", "rye_residue_cover_frac", "cn_row_crop_residue"} <= items
    assert "kc_field_scale" not in items  # calibrated from OpenET for this field


# ---- E1: IMERG note is conditional on rows ------------------------------------------------------
def test_imerg_gap_only_without_rows():
    without = engine.simulate(FakeRepo(with_imerg=False), field_id=FIELD, n=60, seed=1, scenarios=False)
    assert any(IMERG_GAP in g for g in without["info_gaps"])
    assert without["inputs"]["imerg_check"]["loaded"] is False

    with_ = engine.simulate(FakeRepo(with_imerg=True), field_id=FIELD, n=60, seed=1, scenarios=False)
    assert not any("IMERG" in g for g in with_["info_gaps"])
    assert any("GPM IMERG loaded" in n for n in with_["notes"])
    chk = with_["inputs"]["imerg_check"]
    assert chk["loaded"] and chk["imerg_to_power_ratio"] == pytest.approx(1.2, abs=0.02)
    assert with_["inputs"]["precip_source"] == "power"


def test_imerg_profile_and_sources_conditional():
    p0 = services.profile(FakeRepo(with_imerg=False), FIELD)
    p1 = services.profile(FakeRepo(with_imerg=True), FIELD)
    assert any("IMERG not loaded" in g for g in p0["info_gaps"])
    assert not any("IMERG not loaded" in g for g in p1["info_gaps"])
    assert "IMERG" in p1["sources"] and "IMERG" not in p0["sources"]
    v0 = services.vulnerable_seasons(FakeRepo(with_imerg=False), FIELD)
    v1 = services.vulnerable_seasons(FakeRepo(with_imerg=True), FIELD)
    im0 = next(s for s in v0["sources"] if s["source_id"] == "imerg")
    im1 = next(s for s in v1["sources"] if s["source_id"] == "imerg")
    assert "not loaded" in im0["native_resolution"] and not im0["loaded"]
    assert "not loaded" not in im1["native_resolution"] and im1["loaded"]


# ---- NLDAS context -------------------------------------------------------------------------------
def test_nldas_fields_when_rows():
    v = services.vulnerable_seasons(FakeRepo(with_nldas=True), FIELD)
    assert all(s["nldas_rootmoist_anomaly_kg_m2"] is not None for s in v["seasons"])
    assert all("nldas_unit" in s for s in v["seasons"])
    assert v["info_gaps"] == []
    sim = engine.simulate(FakeRepo(with_nldas=True), field_id=FIELD, n=60, seed=1, scenarios=False)
    assert sim["inputs"]["nldas_check"]["n_months"] >= 24
    assert not any("NLDAS" in g for g in sim["info_gaps"])
    assert services.profile(FakeRepo(with_nldas=True), FIELD)["nldas"]["latest_rootmoist_kg_m2"] is not None


def test_nldas_gap_when_missing():
    v = services.vulnerable_seasons(FakeRepo(with_nldas=False), FIELD)
    assert all(s["nldas_rootmoist_anomaly_kg_m2"] is None for s in v["seasons"])
    assert any("NLDAS" in g for g in v["info_gaps"])
    sim = engine.simulate(FakeRepo(with_nldas=False), field_id=FIELD, n=60, seed=1, scenarios=False)
    assert sim["inputs"]["nldas_check"] is None
    assert any("NLDAS" in g for g in sim["info_gaps"])


# ---- live DB (skips when unreachable) -----------------------------------------------------------
live = pytest.mark.skipif(not db.available(), reason="fieldshift DB not reachable")


@pytest.fixture(scope="module")
def live_repo():
    from model_api.repo import PgRepo

    return PgRepo()


@live
def test_live_three_demo_fields_strategies_differ(live_repo):
    ids = live_repo.demo_field_ids()[:3]
    assert len(ids) == 3
    for fid in ids:
        sim = engine.simulate(live_repo, field_id=fid, n=200, seed=42, scenarios=False)
        per = {s["strategy_code"]: (s["metrics"]["season_water_deficit_mm"]["p50"], s["metrics"]["stress_days"]["p50"])
               for s in sim["strategies"]}
        assert _strategy_pairs_differ(per), (fid, per)
        bt = engine.backtest_year(live_repo, fid, 2012)
        per_bt = {c: (m["season_water_deficit_mm"], m["stress_days"]) for c, m in bt.items()}
        assert _strategy_pairs_differ(per_bt), (fid, per_bt)


@live
def test_live_demo_fields_composite_spread(live_repo):
    p50 = []
    for fid in live_repo.demo_field_ids():
        sim = engine.simulate(live_repo, field_id=fid, n=200, seed=42, scenarios=False)
        p50.append(next(s for s in sim["strategies"] if s["strategy_code"] == "A")["composite"]["p50"])
    assert len(set(p50)) >= 2, p50


@live
def test_live_imerg_and_nldas_reflect_db(live_repo):
    fid = live_repo.demo_field_ids()[0]
    sim = engine.simulate(live_repo, field_id=fid, n=60, seed=1, scenarios=False)
    has_imerg = bool(live_repo.imerg_annual(sim["county_fips"]))
    assert any(IMERG_GAP in g for g in sim["info_gaps"]) is (not has_imerg)
    has_nldas = bool(live_repo.nldas_monthly(sim["county_fips"]))
    assert (sim["inputs"]["nldas_check"] is not None) is has_nldas
