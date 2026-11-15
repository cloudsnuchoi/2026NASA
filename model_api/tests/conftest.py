"""Shared fixtures: an in-memory fake repo with synthetic data (no DB needed)."""

from __future__ import annotations

import datetime as dt

import numpy as np
import pytest

FIELD = "TEST-FIELD-0001"
FIPS = "19169"


class FakeRepo:
    def __init__(self, with_scenarios: bool = True, evidence: list[dict] | None = None, with_imerg: bool = False,
                 with_nldas: bool = False, crop_names: list[str] | None = None, awc: float = 0.18, openet_scale: float = 1.0):
        self.with_scenarios = with_scenarios
        self.with_imerg = with_imerg
        self.with_nldas = with_nldas
        self.crop_names = crop_names
        self.awc = awc
        self.openet_scale = openet_scale
        self._evidence = evidence or []
        self._wx = self._make_weather()

    @staticmethod
    def _make_weather():
        rng = np.random.default_rng(0)
        d0, d1 = dt.date(1995, 1, 1), dt.date(2025, 12, 31)
        dates = [d0 + dt.timedelta(days=i) for i in range((d1 - d0).days + 1)]
        doy = np.array([d.timetuple().tm_yday for d in dates])
        season = -np.cos(2 * np.pi * (doy - 15) / 365)
        t = 9 + 15 * season + rng.normal(0, 3, len(dates))
        wet = rng.random(len(dates)) < 0.3
        p = np.where(wet, rng.gamma(0.8, 9.0, len(dates)) * (1 + 0.5 * season), 0.0)
        srad = np.clip(15 + 9 * season + rng.normal(0, 3, len(dates)), 1, 32)
        srad[5] = np.nan  # exercise the Hargreaves fallback
        return {"date": np.array(dates), "t2m_c": t, "tmin_c": t - 6, "tmax_c": t + 6, "precip_mm": p,
                "rh2m_pct": np.full(len(dates), 70.0), "ws2m_ms": np.full(len(dates), 3.0), "srad_mj_m2": srad}

    # fields
    def field(self, field_id):
        if field_id != FIELD:
            return None
        return {"field_id": FIELD, "csb_version": "test", "county_fips": FIPS, "state_alpha": "IA", "area_ha": 30.0,
                "current_rotation": None, "notes": None, "centroid": {"type": "Point", "coordinates": [-93.5, 42.0]},
                "geometry": {"type": "MultiPolygon", "coordinates": []}}

    def demo_field_ids(self):
        return [FIELD]

    def list_fields(self, field_ids=None, limit=100, offset=0):
        return [{"field_id": FIELD, "county_fips": FIPS, "state_alpha": "IA", "area_ha": 30.0, "csb_version": "test",
                 "lon": -93.5, "lat": 42.0}]

    def count_fields(self):
        return 1

    def soil(self, field_id):
        return [{"mukey": "1", "comppct_r": 100.0, "om_pct": 3.0, "kffact": 0.28, "drainagecl": "Well drained", "awc_cm_cm": self.awc,
                 "source": "test"}]

    def soil_medians(self):
        return {"awc_cm_cm": 0.18, "kffact": 0.28, "om_pct": 3.0, "n": 1}

    def crop_history(self, field_id):
        if self.crop_names:
            n = len(self.crop_names)
            return [{"year": y, "cdl_class": None, "crop_name": self.crop_names[(y - 2008) % n], "share": 0.9} for y in range(2008, 2026)]
        return [{"year": y, "cdl_class": 1 if y % 2 == 0 else 5, "crop_name": "Corn" if y % 2 == 0 else "Soybeans", "share": 0.9}
                for y in range(2008, 2026)]

    def ndvi(self, field_id):
        out = []
        d = dt.date(2023, 4, 1)
        while d < dt.date(2025, 11, 30):
            doy = d.timetuple().tm_yday
            v = 0.25 + (0.6 if 160 < doy < 260 else 0.0)
            out.append({"date": d, "product": "HLSL30", "ndvi": v, "valid_frac": 1.0})
            d += dt.timedelta(days=5)
        return out

    def openet(self, field_id):
        return [{"date": dt.date(y, m, 1), "variable": "et_ensemble_mm",
                 "value": self.openet_scale * (100.0 if 6 <= m <= 8 else 60.0 if m in (5, 9) else 15.0), "unit": "mm"}
                for y in range(2016, 2026) for m in range(1, 13)]

    def vision(self, field_id):
        return []

    def locate(self, lat, lon):
        return self.field(FIELD) if abs(lat - 42.0) < 0.05 and abs(lon + 93.5) < 0.05 else None

    # county
    def county(self, fips):
        if fips not in (FIPS, "31055"):
            return None
        return {"county_fips": fips, "state_alpha": "IA" if fips == FIPS else "NE", "name": "Story" if fips == FIPS else "Douglas",
                "area_km2": 1000.0, "lon": -93.46, "lat": 42.04}

    def county_at(self, lat, lon):
        return self.county("31055") if abs(lat - 41.26) < 0.5 else None

    def weather_daily(self, fips):
        return self._wx if self.county(fips) else None

    def crop_shares(self, fips, year=None):
        return [{"year": 2025, "cdl_class": 1, "crop_name": "Corn", "share": 0.44},
                {"year": 2025, "cdl_class": 5, "crop_name": "Soybeans", "share": 0.29}]

    def yields(self, fips):
        return [{"year": 2012, "crop": "corn", "yield_bu_ac": 150.0, "source": "test"}]

    def smap(self, fips):
        return [{"date": dt.date(2020 + i // 200, 1 + (i // 17) % 12, 1 + i % 17), "value": 0.25 + 0.01 * (i % 5), "unit": "cm3/cm3",
                 "product": "SPL3SMP.009"} for i in range(1000)]

    def scenario_year(self, fips):
        if not self.with_scenarios:
            return []
        rows = []
        for m in ("ens1", "ens2"):
            for season, pr, tas in (("MAM", 2.8, 9.0), ("JJ", 3.5, 23.0)):
                rows.append({"source_id": "geos_s2s", "model": "GEOS-S2S-3", "scenario": "forecast", "member": "20261003" + m,
                             "variable": "pr", "season": season, "year": 2027, "value": pr, "unit": "mm/day"})
                rows.append({"source_id": "geos_s2s", "model": "GEOS-S2S-3", "scenario": "forecast", "member": "20261003" + m,
                             "variable": "tas", "season": season, "year": 2027, "value": tas, "unit": "degC"})
        for model in ("MODEL-A", "MODEL-B"):
            for scen, years, dp, dtt in (("historical", range(1985, 2015), 1.0, 0.0), ("ssp245", range(2031, 2041), 1.05, 1.2),
                                          ("ssp585", range(2031, 2041), 1.02, 1.6)):
                for season in ("ANN", "MAM", "JJA"):
                    for y in years:
                        rows.append({"source_id": "nex_gddp", "model": model, "scenario": scen, "member": "r1i1p1f1", "variable": "pr",
                                     "season": season, "year": y, "value": 2.5 * dp, "unit": "mm/day"})
                        for v in ("tasmax", "tasmin"):
                            rows.append({"source_id": "nex_gddp", "model": model, "scenario": scen, "member": "r1i1p1f1", "variable": v,
                                         "season": season, "year": y, "value": 15.0 + dtt, "unit": "degC"})
        return rows

    def imerg_count(self, fips):
        return 365 * 3 if self.with_imerg else 0

    def imerg_annual(self, fips):
        if not self.with_imerg:
            return []
        return [{"year": y, "precip_mm": 1.2 * float(self._wx["precip_mm"][[d.year == y for d in self._wx["date"]]].sum()),
                 "days": 366 if y % 4 == 0 else 365} for y in (2022, 2023, 2024)]

    def imerg_daily(self, fips):
        if not self.with_imerg:
            return None
        sel = np.array([d.year >= 2022 and d.year <= 2024 for d in self._wx["date"]])
        return {"date": self._wx["date"][sel], "precip_mm": self._wx["precip_mm"][sel] * 1.2}

    def nldas_monthly(self, fips):
        if not self.with_nldas:
            return []
        out = []
        for y in range(1995, 2026):
            for m in range(1, 13):
                v = 300.0 + 40.0 * np.cos(2 * np.pi * (m - 4) / 12) + 5.0 * ((y * 7 + m) % 5 - 2)
                out.append({"month": dt.date(y, m, 1), "rootmoist_kg_m2": v, "soilm_0_10_kg_m2": 30.0, "soilm_10_40_kg_m2": 80.0,
                            "soilm_40_100_kg_m2": 160.0, "evap_kg_m2": 50.0, "rainf_kg_m2": 70.0})
        return out

    def evidence_search(self, q, strategy_code, limit=5):
        return [e for e in self._evidence if q.split()[0].lower() in e["quote"].lower()]

    def calibration_params(self):
        return {}


@pytest.fixture(autouse=True)
def _no_matlab(tmp_path, monkeypatch):
    monkeypatch.setenv("FS_MATLAB_DIR", str(tmp_path / "matlab_missing"))
    monkeypatch.delenv("LLM_API_KEY", raising=False)


@pytest.fixture
def fake_repo():
    return FakeRepo()


@pytest.fixture
def client(fake_repo):
    from fastapi.testclient import TestClient

    from model_api.main import app

    app.state.repo = fake_repo
    yield TestClient(app)
    app.state.repo = None
    app.state.llm_client = None
    app.state.llm_model = None
