"""Tier 1 Quick Screen: geometry, validation, failure handling and response shape with mocked HTTP (no network)."""

from __future__ import annotations

import datetime as dt
import math

import pytest

from model_api import quick

LAT, LON = 42.0, -93.6
# ~400 m square around (LON, LAT)
D_LAT = 0.0018
D_LON = D_LAT / math.cos(math.radians(LAT))
SQUARE = [[LON - D_LON, LAT - D_LAT], [LON + D_LON, LAT - D_LAT], [LON + D_LON, LAT + D_LAT], [LON - D_LON, LAT + D_LAT]]


def _power_payload():
    par = {k: {} for k in quick.POWER_PARAMS.split(",")}
    d = dt.date(quick.HIST_START, 1, 1)
    while d <= dt.date(quick.HIST_END, 12, 31):
        key = d.strftime("%Y%m%d")
        season = -math.cos(2 * math.pi * (d.timetuple().tm_yday - 15) / 365)
        t = 9 + 15 * season
        vals = {"T2M": t, "T2M_MAX": t + 6, "T2M_MIN": t - 6, "PRECTOTCORR": 2.4, "ALLSKY_SFC_SW_DWN": 16 + 8 * season,
                "RH2M": 70.0, "WS2M": 3.0, "PS": 97.5, "GWETROOT": 0.6}
        for k, v in vals.items():
            par[k][key] = v
        d += dt.timedelta(days=1)
    return {"geometry": {"coordinates": [LON, LAT, 300.0]}, "properties": {"parameter": par}}


def _open_meteo_payload():
    keys = ("temperature_2m_mean", "temperature_2m_max", "temperature_2m_min", "precipitation_sum", "shortwave_radiation_sum",
            "relative_humidity_2m_mean", "wind_speed_10m_mean")
    vals = (11.0, 17.0, 5.0, 2.0, 15.0, 70.0, 4.0)
    daily = {"time": []} | {k: [] for k in keys}
    d = dt.date(quick.PROJ_START, 1, 1)
    while d <= dt.date(quick.PROJ_END, 12, 31):
        daily["time"].append(d.isoformat())
        for k, v in zip(keys, vals):
            daily[k].append(v)
        d += dt.timedelta(days=1)
    return {"elevation": 293.0, "daily": daily}


@pytest.fixture
def fake_http(monkeypatch, tmp_path):
    monkeypatch.setattr(quick, "CACHE_DIR", tmp_path)
    calls = []
    fail = set()

    def get(url):
        calls.append(url)
        for f in fail:
            if f in url:
                raise ConnectionError("mocked failure")
        if "epqs" in url:
            return {"value": 290.5}
        if "power.larc" in url:
            return _power_payload()
        if "/points/" in url:
            return {"properties": {"forecast": "https://api.weather.gov/gridpoints/DMX/1,1/forecast"}}
        if "gridpoints" in url:
            return {"properties": {"periods": [{"temperature": 50, "temperatureUnit": "F", "startTime": "2026-11-15T06:00:00-06:00"},
                                               {"temperature": 32, "temperatureUnit": "F", "startTime": "2026-11-15T18:00:00-06:00"}]}}
        if "open-meteo" in url:
            return _open_meteo_payload()
        raise AssertionError(url)

    monkeypatch.setattr(quick, "_http_get_json", get)
    return calls, fail


def test_square_area_and_perimeter():
    g = quick.polygon_metrics(SQUARE)
    # side = 2 * 0.0018 deg latitude ~ 399.8 m at 42N (meridian arc); expect ~16.0 ha, ~1.6 km
    assert 15.8 < g["area_ha"] < 16.2
    assert 1.58 < g["perimeter_km"] < 1.62
    assert abs(g["centroid"]["lon"] - LON) < 1e-6 and abs(g["centroid"]["lat"] - LAT) < 1e-6
    closed = quick.polygon_metrics(SQUARE + [SQUARE[0]])
    assert closed["area_ha"] == g["area_ha"]


def test_et0_pm_fao56_example_18():
    # FAO-56 Example 18 inputs (Uccle, 6 July): ET0 ~ 3.9 mm/day
    e = quick.et0_pm(187, 50.8, 21.5, 12.3, (63 + 84) / 2, 2.078, 22.07, 100.1, 100)
    assert 3.6 < e < 4.2


def test_consecutive_duplicate_rejected(client):
    r = client.post("/quick", json={"polygon": SQUARE, "crops": ["Corn", "Corn", "Soy"]})
    assert r.status_code == 422 and "consecutive" in r.json()["error"]["message"]


@pytest.mark.parametrize("body", [
    {"polygon": SQUARE[:2], "crops": ["Corn", "Soy"]},
    {"polygon": SQUARE, "crops": ["Corn"]},
    {"polygon": SQUARE, "crops": ["Corn", "Soy", "Wheat", "Corn"]},
    {"polygon": SQUARE, "crops": ["Corn", "Rice"]},
])
def test_bad_input_rejected(client, body):
    assert client.post("/quick", json=body).status_code == 422


def test_success_shape(client, fake_http):
    r = client.post("/quick", json={"polygon": SQUARE, "crops": ["Corn", "Soy", "Wheat"]})
    assert r.status_code == 200
    d = r.json()
    assert d["label"] == "screening estimate" and "MATLAB prototype V8" in d["engine"]
    for k in ("geometry", "elevation", "climate_history", "forecast_anomaly", "climate_projection", "crop_cards",
              "rotation_candidates", "economic_assumptions", "info_gaps", "sources", "disclaimer"):
        assert k in d
    assert d["elevation"]["value_m"] == 290.5
    assert [c["crop"] for c in d["crop_cards"]] == ["Corn", "Soy", "Wheat"]
    corn = d["crop_cards"][0]
    assert corn["kc"]["mid"] == 1.20 and "Table 12" in corn["kc"]["source"]
    h = corn["history"]
    assert h["etc_mm"]["p10"] <= h["etc_mm"]["p50"] <= h["etc_mm"]["p90"]
    assert h["irrigation_deficit_mm"]["mean"] >= 0
    assert corn["projection"] is not None
    assert d["forecast_anomaly"]["anomaly_c"] is not None
    for rot in d["rotation_candidates"]:
        assert rot["ranked"] is False
        assert all(a != b for a, b in zip(rot["sequence"], rot["sequence"][1:]))
        assert rot["relative_water_use_index"]["unit"].startswith("relative index")
    assert not any("best" in str(x).lower() or "recommend" in str(x).lower() for x in d["rotation_candidates"])


def test_two_crop_rotations():
    assert quick.rotation_candidates(["Corn", "Soy"]) == [["Corn", "Soy"], ["Soy", "Corn"]]
    for seq in quick.rotation_candidates(["Corn", "Soy", "Wheat"]):
        assert all(a != b for a, b in zip(seq, seq[1:] + seq[:1]))


def test_failure_gives_null_and_info_gap(fake_http):
    calls, fail = fake_http
    fail.update({"power.larc", "api.weather.gov"})
    d = quick.quick_screen(SQUARE, ["Corn", "Soy"])
    assert d["climate_history"] is None and d["forecast_anomaly"] is None
    assert d["elevation"] is not None and d["climate_projection"] is not None
    assert any("NASA POWER" in g for g in d["info_gaps"]) and any("NWS" in g for g in d["info_gaps"])
    assert d["crop_cards"][0]["history"] is None
    assert d["rotation_candidates"][0]["mean_season_etc_mm"] is None


def test_cache_reused(fake_http):
    calls, _ = fake_http
    quick.quick_screen(SQUARE, ["Corn", "Soy"])
    n = len(calls)
    quick.quick_screen(SQUARE, ["Soy", "Corn"])
    assert len(calls) == n  # second run served entirely from disk cache
