"""Data access. ``PgRepo`` reads the live DB (read-only). Tests inject a fake with the same methods."""

from __future__ import annotations

import json
import threading
from typing import Any

import numpy as np

from . import config, db


def _f(x: Any) -> float | None:
    return None if x is None else float(x)


class PgRepo:
    def __init__(self) -> None:
        self._cache: dict[tuple, Any] = {}
        self._lock = threading.Lock()

    def _cached(self, key: tuple, fn):
        with self._lock:
            if key in self._cache:
                return self._cache[key]
        val = fn()
        with self._lock:
            if len(self._cache) > 512:
                self._cache.clear()
            self._cache[key] = val
        return val

    # ---- fields -------------------------------------------------------------------------------
    def field(self, field_id: str) -> dict | None:
        def load():
            rows = db.query(
                "SELECT field_id, csb_version, county_fips, state_alpha, area_ha, current_rotation, notes, "
                "ST_AsGeoJSON(centroid) AS centroid, ST_AsGeoJSON(geom, 6) AS geometry "
                "FROM fields WHERE field_id = %s",
                (field_id,),
            )
            if not rows:
                return None
            r = rows[0]
            r["area_ha"] = _f(r["area_ha"])
            r["centroid"] = json.loads(r["centroid"]) if r["centroid"] else None
            r["geometry"] = json.loads(r["geometry"]) if r["geometry"] else None
            return r

        return self._cached(("field", field_id), load)

    def demo_field_ids(self) -> list[str]:
        # The data lane picked 12 Story demo fields; they are the fields with OpenET + HLS series.
        rows = self._cached(
            ("demo_ids",),
            lambda: db.query("SELECT DISTINCT field_id FROM field_et_openet ORDER BY field_id"),
        )
        return [r["field_id"] for r in rows]

    def list_fields(self, field_ids: list[str] | None = None, limit: int = 100, offset: int = 0) -> list[dict]:
        if field_ids is not None:
            rows = db.query(
                "SELECT field_id, county_fips, state_alpha, area_ha, csb_version, ST_X(centroid) AS lon, ST_Y(centroid) AS lat "
                "FROM fields WHERE field_id = ANY(%s) ORDER BY field_id",
                (field_ids,),
            )
        else:
            rows = db.query(
                "SELECT field_id, county_fips, state_alpha, area_ha, csb_version, ST_X(centroid) AS lon, ST_Y(centroid) AS lat "
                "FROM fields ORDER BY field_id LIMIT %s OFFSET %s",
                (limit, offset),
            )
        for r in rows:
            r["area_ha"] = _f(r["area_ha"])
            r["lon"], r["lat"] = _f(r["lon"]), _f(r["lat"])
        return rows

    def count_fields(self) -> int:
        return int(db.query("SELECT count(*) AS n FROM fields")[0]["n"])

    def soil(self, field_id: str) -> list[dict]:
        rows = db.query(
            "SELECT mukey, comppct_r, om_pct, kffact, drainagecl, awc_cm_cm, source FROM field_soil WHERE field_id = %s",
            (field_id,),
        )
        for r in rows:
            for k in ("comppct_r", "om_pct", "kffact", "awc_cm_cm"):
                r[k] = _f(r[k])
        return rows

    def soil_medians(self) -> dict:
        def load():
            r = db.query(
                "SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY awc_cm_cm) AS awc, "
                "percentile_cont(0.5) WITHIN GROUP (ORDER BY kffact) AS k, "
                "percentile_cont(0.5) WITHIN GROUP (ORDER BY om_pct) AS om, count(*) AS n FROM field_soil"
            )[0]
            return {"awc_cm_cm": _f(r["awc"]), "kffact": _f(r["k"]), "om_pct": _f(r["om"]), "n": int(r["n"])}

        return self._cached(("soil_medians",), load)

    def crop_history(self, field_id: str) -> list[dict]:
        rows = db.query(
            "SELECT year, cdl_class, crop_name, share FROM field_crop_history WHERE field_id = %s ORDER BY year",
            (field_id,),
        )
        for r in rows:
            r["share"] = _f(r["share"])
        return rows

    def ndvi(self, field_id: str) -> list[dict]:
        rows = db.query(
            "SELECT date, product, ndvi, valid_frac FROM field_ndvi_hls WHERE field_id = %s ORDER BY date",
            (field_id,),
        )
        for r in rows:
            r["ndvi"], r["valid_frac"] = _f(r["ndvi"]), _f(r["valid_frac"])
        return rows

    def openet(self, field_id: str) -> list[dict]:
        rows = db.query(
            "SELECT date, variable, value, unit FROM field_et_openet WHERE field_id = %s ORDER BY date", (field_id,)
        )
        for r in rows:
            r["value"] = _f(r["value"])
        return rows

    def vision(self, field_id: str) -> list[dict]:
        return db.query(
            "SELECT year, model_id, crop_pred, bare_fraction, agreement_with_cdl FROM vision_result "
            "WHERE field_id = %s ORDER BY year DESC",
            (field_id,),
        )

    def locate(self, lat: float, lon: float) -> dict | None:
        rows = db.query(
            "SELECT field_id FROM fields WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) LIMIT 1",
            (lon, lat),
        )
        return self.field(rows[0]["field_id"]) if rows else None

    # ---- county (tier 1) ----------------------------------------------------------------------
    def county(self, fips: str) -> dict | None:
        def load():
            rows = db.query(
                "SELECT county_fips, state_alpha, name, area_km2, ST_X(centroid) AS lon, ST_Y(centroid) AS lat "
                "FROM county WHERE county_fips = %s",
                (fips,),
            )
            if not rows:
                return None
            r = rows[0]
            r["county_fips"] = r["county_fips"].strip()
            r["area_km2"], r["lon"], r["lat"] = _f(r["area_km2"]), _f(r["lon"]), _f(r["lat"])
            return r

        return self._cached(("county", fips), load)

    def county_at(self, lat: float, lon: float) -> dict | None:
        rows = db.query(
            "SELECT county_fips FROM county WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) LIMIT 1",
            (lon, lat),
        )
        return self.county(rows[0]["county_fips"].strip()) if rows else None

    def weather_daily(self, fips: str) -> dict[str, np.ndarray] | None:
        def load():
            rows = db.query(
                "SELECT date, t2m_c, tmin_c, tmax_c, precip_mm, rh2m_pct, ws2m_ms, srad_mj_m2 FROM county_weather_daily "
                "WHERE county_fips = %s AND source_id = %s AND date >= %s AND date <= %s ORDER BY date",
                (fips, config.WEATHER_SOURCE, f"{config.WEATHER_START_YEAR}-01-01", f"{config.WEATHER_END_YEAR}-12-31"),
            )
            if not rows:
                return None
            out = {"date": np.array([r["date"] for r in rows])}
            for k in ("t2m_c", "tmin_c", "tmax_c", "precip_mm", "rh2m_pct", "ws2m_ms", "srad_mj_m2"):
                out[k] = np.array([np.nan if r[k] is None else float(r[k]) for r in rows])
            return out

        return self._cached(("wx", fips), load)

    def crop_shares(self, fips: str, year: int | None = None) -> list[dict]:
        if year is None:
            rows = db.query(
                "SELECT year, cdl_class, crop_name, share FROM county_crop_share WHERE county_fips = %s "
                "AND cdl_class IN (1, 5, 24, 28, 36, 37, 27) ORDER BY year, cdl_class",
                (fips,),
            )
        else:
            rows = db.query(
                "SELECT year, cdl_class, crop_name, share FROM county_crop_share WHERE county_fips = %s AND year = %s "
                "ORDER BY share DESC",
                (fips, year),
            )
        for r in rows:
            r["share"] = _f(r["share"])
        return rows

    def yields(self, fips: str) -> list[dict]:
        rows = db.query(
            "SELECT year, crop, yield_bu_ac, source FROM county_yield WHERE county_fips = %s ORDER BY year, crop", (fips,)
        )
        for r in rows:
            r["yield_bu_ac"] = _f(r["yield_bu_ac"])
        return rows

    def smap(self, fips: str) -> list[dict]:
        rows = db.query(
            "SELECT date, value, unit, product FROM county_smap WHERE county_fips = %s AND variable = 'soil_moisture_am' "
            "ORDER BY date",
            (fips,),
        )
        for r in rows:
            r["value"] = _f(r["value"])
        return rows

    def scenario_year(self, fips: str) -> list[dict]:
        def load():
            rows = db.query(
                "SELECT source_id, model, scenario, member, variable, season, year, value, unit FROM county_scenario_year "
                "WHERE county_fips = %s",
                (fips,),
            )
            for r in rows:
                r["value"] = _f(r["value"])
            return rows

        return self._cached(("scen", fips), load)

    def imerg_count(self, fips: str) -> int:
        return int(db.query("SELECT count(*) AS n FROM county_imerg_daily WHERE county_fips = %s", (fips,))[0]["n"])

    def imerg_annual(self, fips: str) -> list[dict]:
        """GPM IMERG daily county precipitation summed per calendar year: [{year, precip_mm, days}]."""
        def load():
            rows = db.query(
                "SELECT extract(year FROM date)::int AS year, sum(precip_mm) AS precip_mm, count(precip_mm) AS days "
                "FROM county_imerg_daily WHERE county_fips = %s GROUP BY 1 ORDER BY 1",
                (fips,),
            )
            return [{"year": int(r["year"]), "precip_mm": _f(r["precip_mm"]), "days": int(r["days"])} for r in rows]

        return self._cached(("imerg_annual", fips), load)

    def imerg_daily(self, fips: str) -> dict[str, np.ndarray] | None:
        def load():
            rows = db.query("SELECT date, precip_mm FROM county_imerg_daily WHERE county_fips = %s ORDER BY date", (fips,))
            if not rows:
                return None
            return {"date": np.array([r["date"] for r in rows]),
                    "precip_mm": np.array([np.nan if r["precip_mm"] is None else float(r["precip_mm"]) for r in rows])}

        return self._cached(("imerg_daily", fips), load)

    def nldas_monthly(self, fips: str) -> list[dict]:
        """NLDAS-2 Noah monthly county means (kg/m2 = mm of water for moisture, rainf and evap)."""
        def load():
            rows = db.query(
                "SELECT month, rootmoist_kg_m2, soilm_0_10_kg_m2, soilm_10_40_kg_m2, soilm_40_100_kg_m2, evap_kg_m2, rainf_kg_m2 "
                "FROM county_nldas_monthly WHERE county_fips = %s ORDER BY month",
                (fips,),
            )
            for r in rows:
                for k in list(r):
                    if k != "month":
                        r[k] = _f(r[k])
            return rows

        return self._cached(("nldas", fips), load)

    # ---- evidence / params ---------------------------------------------------------------------
    def evidence_search(self, q: str, strategy_code: str | None, limit: int = 5) -> list[dict]:
        sql = (
            "SELECT source_title, doi, url, quote, license, strategy_code FROM evidence_chunk "
            "WHERE to_tsvector('simple', coalesce(quote,'') || ' ' || coalesce(source_title,'')) @@ plainto_tsquery('simple', %s)"
        )
        params: list = [q]
        if strategy_code:
            sql += " AND (strategy_code = %s OR strategy_code IS NULL)"
            params.append(strategy_code)
        sql += " LIMIT %s"
        params.append(limit)
        return db.query(sql, params)

    def calibration_params(self) -> dict[str, float]:
        rows = db.query("SELECT param, value FROM calibration_param")
        return {r["param"]: float(r["value"]) for r in rows if r["value"] is not None}

    def backtest_rows(self, field_id: str, year: int) -> list[dict]:
        return db.query(
            "SELECT strategy_code, year, observed_cdl, observed_sequence, county_yield_bu_ac, notes, metrics "
            "FROM backtest_result WHERE field_id = %s AND year = %s",
            (field_id, year),
        )


_repo: PgRepo | None = None


def get_repo() -> PgRepo:
    global _repo
    if _repo is None:
        _repo = PgRepo()
    return _repo
