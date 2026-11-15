import numpy as np

from model_api import config, hydro


def prm():
    return {k: v[0] for k, v in config.DEFAULTS.items()}


def test_et0_seasonality_and_positive():
    doy = np.arange(1, 366)
    s = -np.cos(2 * np.pi * (doy - 15) / 365)
    t = 9 + 15 * s
    e = hydro.et0_fao56(t, t + 6, t - 6, np.full(365, 70.0), np.full(365, 2.0), 15 + 9 * s, 42.0, 300.0)
    assert (e >= 0).all()
    assert e[180] > 4 * max(e[10], 0.1)  # July >> January
    assert 3.0 < e[150:240].mean() < 8.0


def test_quantiles_cvar_tails():
    x = np.arange(100, dtype=float)
    hi = hydro.quantiles(x, higher_is_better=True)
    lo = hydro.quantiles(x, higher_is_better=False)
    assert hi["cvar"] == 4.5  # mean of lowest 10
    assert lo["cvar"] == 94.5  # mean of highest 10 (loss)
    assert hi["p10"] < hi["p50"] < hi["p90"]


def test_cycles_match_prd_strategies():
    assert hydro.cycle_for(()) == [("corn", None), ("soy", None)]
    assert hydro.cycle_for(("cover_rye",)) == [("corn", "rye"), ("soy", "rye")]
    assert [c[0] for c in hydro.cycle_for(("small_grain", "cover_rye"))] == ["corn", "soy", "wheat"]
    assert [c[0] for c in hydro.cycle_for(("alfalfa",))] == ["corn", "soy", "alfalfa1", "alfalfa2"]


def test_calendar_winter_bare_days():
    tab = hydro.calendar_table([hydro.cycle_for(()), hydro.cycle_for(("cover_rye",))], prm())
    winter = np.tile(hydro.WINTER_MASK, hydro.N_YEARS_TOTAL)
    bare_a = ((~tab["living"][0, 0]) & winter)[365:].sum() / hydro.N_YEARS_SCORED
    bare_b = ((~tab["living"][1, 0]) & winter)[365:].sum() / hydro.N_YEARS_SCORED
    assert bare_a == 181
    assert bare_b < 20


def test_run_mc_shapes_and_water_closure(fake_repo):
    ym = hydro.to_year_matrix(fake_repo.weather_daily("19169"))
    assert ym["n_filled"] == 1
    cycles = [hydro.cycle_for(()), hydro.cycle_for(("cover_rye",))]
    out = hydro.run_mc(ym, [hydro.historical_spec()], cycles, prm(), 42.0, 60, 1)
    r = out["results"]["historical"]
    assert r["eta_mm"].shape == (2, 60)
    # common random numbers: identical precipitation for both strategies
    assert np.allclose(r["precip_mm"][0], r["precip_mm"][1])
    # water balance closes within the bucket storage change bound
    resid = r["precip_mm"] - r["eta_mm"] - r["runoff_mm"] - r["drainage_mm"]
    taw = prm()["awc_cm_cm"] * 1000 * prm()["profile_depth_m"]
    assert np.abs(resid).max() <= taw / hydro.N_YEARS_SCORED + 1e-6
    # cover crop uses more water and leaves fewer bare winter days
    assert np.median(r["eta_mm"][1]) > np.median(r["eta_mm"][0])
    assert np.median(r["winter_bare_days"][1]) < np.median(r["winter_bare_days"][0])
