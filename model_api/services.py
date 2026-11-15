"""Read-side services for the SOT 6 endpoints (profile, bare periods, seasons, history, outlook, county, backtest)."""

from __future__ import annotations

import datetime as dt
from collections import defaultdict

import numpy as np

from . import config, hydro
from .engine import Params, load_overrides

SEASONS = {"spring": [3, 4, 5], "summer": [6, 7, 8], "fall": [9, 10, 11], "winter": [12, 1, 2]}
CONTEXT_SOURCES = [
    {"source_id": "power", "native_resolution": "see API metadata (MERRA-2 ~0.5 x 0.625 deg for met vars)"},
    {"source_id": "smap", "native_resolution": "nominal 36 km L3 (SPL3SMP)"},
    {"source_id": "imerg", "native_resolution": "nominal 0.1 deg (not loaded)"},
]


def _params(repo) -> Params:
    ov, _ = load_overrides(repo)
    return Params(ov)


def _round(x, nd=2):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), nd)


def _wx_frame(repo, fips: str):
    wx = repo.weather_daily(fips)
    if wx is None:
        return None
    dates = wx["date"]
    years = np.array([d.year for d in dates])
    months = np.array([d.month for d in dates])
    return wx, years, months


def _annual(wx_t, y0: int, y1: int) -> dict[int, dict]:
    wx, years, months = wx_t
    out = {}
    for y in range(y0, y1 + 1):
        sel = years == y
        if sel.sum() < 365:
            continue
        out[y] = {"precip_mm": float(np.nansum(wx["precip_mm"][sel])), "t2m_mean_c": float(np.nanmean(wx["t2m_c"][sel])),
                  "frost_days": int(np.nansum(wx["tmin_c"][sel] < 0)), "heat_days": int(np.nansum(wx["tmax_c"][sel] > 32))}
    return out


def _et0_by_year(repo, fips: str, lat: float, elev: float) -> dict[int, np.ndarray]:
    wx = repo.weather_daily(fips)
    ym = hydro.to_year_matrix(wx)
    e = hydro.et0_fao56(ym["t2m_c"], ym["tmax_c"], ym["tmin_c"], ym["rh2m_pct"], ym["ws2m_ms"], ym["srad_mj_m2"], lat, elev)
    return {int(y): e[i] for i, y in enumerate(ym["years"])}


def current_rotation(hist: list[dict]) -> str | None:
    recent = [h["crop_name"] for h in hist if h["year"] >= max((x["year"] for x in hist), default=0) - 7]
    if not recent:
        return None
    s = set(recent)
    if s <= {"Corn", "Soybeans"} and len(s) == 2:
        return "C-S"
    if s == {"Corn"}:
        return "C-C"
    return None


def ndvi_peaks(ndvi_rows: list[dict]) -> dict[int, float]:
    by = defaultdict(list)
    for r in ndvi_rows:
        v = r["ndvi"]
        if v is None or not (0.0 <= v <= 1.0) or (r["valid_frac"] or 0) < 0.5:
            continue
        by[r["date"].year].append(v)
    return {y: float(np.percentile(v, 95)) for y, v in by.items() if len(v) >= 5}


def profile(repo, field_id: str) -> dict | None:
    f = repo.field(field_id)
    if not f:
        return None
    prm = _params(repo)
    fips = f["county_fips"].strip()
    lat = f["centroid"]["coordinates"][1]
    gaps: list[str] = []
    hist = repo.crop_history(field_id)
    soil_rows = repo.soil(field_id)
    soil = {"om_pct": None, "k_factor": None, "awc_cm_cm": None}
    if soil_rows:
        s = soil_rows[0]
        soil = {"om_pct": s["om_pct"], "k_factor": s["kffact"], "awc_cm_cm": s["awc_cm_cm"], "drainagecl": s["drainagecl"], "mukey": s["mukey"]}
    else:
        gaps.append("SSURGO soil not loaded for this field")
    wt = _wx_frame(repo, fips)
    ann = _annual(wt, config.BASELINE_START_YEAR, config.BASELINE_END_YEAR) if wt else {}
    precip = float(np.mean([v["precip_mm"] for v in ann.values()])) if ann else None
    t2m = float(np.mean([v["t2m_mean_c"] for v in ann.values()])) if ann else None
    et0_mm_day = None
    if wt:
        e = _et0_by_year(repo, fips, lat, prm.values["elevation_m"])
        et0_mm_day = float(np.mean([e[y].mean() for y in e if config.BASELINE_START_YEAR <= y <= config.BASELINE_END_YEAR]))
    et_rows = [r for r in repo.openet(field_id) if r["value"] is not None]
    et_mm_day = None
    if et_rows:
        by = defaultdict(float)
        cnt = defaultdict(int)
        for r in et_rows:
            by[r["date"].year] += r["value"]
            cnt[r["date"].year] += 1
        full = [by[y] for y in by if cnt[y] == 12]
        if full:
            et_mm_day = float(np.mean(full)) / 365.0
    else:
        gaps.append("Actual ET (OpenET / NLDAS-2) not loaded for this field")
    peaks = ndvi_peaks(repo.ndvi(field_id))
    ndvi_peak = float(np.mean(list(peaks.values()))) if peaks else None
    if ndvi_peak is None:
        gaps.append("HLS NDVI series not loaded for this field")
    ndvi_class = None
    if ndvi_peak is not None:
        ndvi_class = "good" if ndvi_peak >= prm.values["ndvi_good"] else "fair" if ndvi_peak >= prm.values["ndvi_fair"] else "low"
        gaps.append(f"ndvi_class thresholds are team defaults (good >= {prm.values['ndvi_good']}, fair >= {prm.values['ndvi_fair']})")
    vis = repo.vision(field_id)
    vision = {"model_id": "ibm-nasa-geospatial/Prithvi-EO-1.0-100M-multi-temporal-crop-classification", "crop_pred": None,
              "bare_fraction": None, "agreement_with_cdl": None}
    if vis:
        v = vis[0]
        vision.update({"model_id": v["model_id"], "crop_pred": v["crop_pred"], "bare_fraction": _round(v["bare_fraction"]),
                       "agreement_with_cdl": _round(v["agreement_with_cdl"])})
    else:
        gaps.append("Prithvi vision result not loaded yet (CDL is the reference label)")
    hero = hero_state(wt, prm) if wt else "normal"
    county = repo.county(fips)
    return {
        "field_id": f["field_id"],
        "csb_version": f["csb_version"],
        "county_fips": fips,
        "state_alpha": f["state_alpha"],
        "area_ha": _round(f["area_ha"], 2),
        "current_rotation": f.get("current_rotation") or current_rotation(hist),
        "centroid": f["centroid"],
        "geometry": f["geometry"],
        "soil_summary": {"source_id": "gssurgo", "notes": "SSURGO SDA area-dominant mapunit, surface horizon (om_r, kffact, awc_r)"},
        "disclaimer": config.DISCLAIMER_FIELD,
        "sources": ["CSB", "CDL", "gSSURGO", "POWER", "HLS", "OpenET"],
        "region_label": f"{county['name']} County, {f['state_alpha']} (Corn Belt)" if county else None,
        "precip_mm_yr": _round(precip, 1),
        "et_mm_day": _round(et_mm_day, 2),
        "et0_mm_day": _round(et0_mm_day, 2),
        "ndvi_peak": _round(ndvi_peak, 3),
        "ndvi_class": ndvi_class,
        "t2m_mean_c": _round(t2m, 2),
        "cdl_history": [{"year": h["year"], "crop": h["crop_name"]} for h in sorted(hist, key=lambda x: -x["year"])],
        "soil": soil,
        "vision": vision,
        "hero_state": hero,
        "period": {"start": f"{config.BASELINE_START_YEAR}-01-01", "end": f"{config.BASELINE_END_YEAR}-12-31"},
        "info_gaps": gaps + ["Precipitation normal from POWER (IMERG not loaded); ET from OpenET Ensemble 2016-2025 (point)"],
    }


def hero_state(wt, prm: Params) -> str:
    wx, years, months = wt
    last = int(years.max())
    jja = np.isin(months, [6, 7, 8])
    base = (years >= config.BASELINE_START_YEAR) & (years < last)
    p_base = np.nansum(wx["precip_mm"][jja & base]) / max(len(set(years[base])), 1)
    p_last = np.nansum(wx["precip_mm"][jja & (years == last)])
    tx_anom = np.nanmean(wx["tmax_c"][jja & (years == last)]) - np.nanmean(wx["tmax_c"][jja & base])
    if p_last < prm.values["hero_drought_ratio"] * p_base:
        return "drought"
    if p_last > prm.values["hero_wet_ratio"] * p_base:
        return "wet"
    if tx_anom > prm.values["hero_heat_c"]:
        return "heat"
    mam = np.isin(months, [4, 5])
    frost_last = np.nansum(wx["tmin_c"][mam & (years == last)] < -2)
    frost_base = np.nansum(wx["tmin_c"][mam & base] < -2) / max(len(set(years[base])), 1)
    if frost_last > frost_base + 3:
        return "frost"
    return "normal"


def bare_periods(repo, field_id: str) -> dict | None:
    f = repo.field(field_id)
    if not f:
        return None
    prm = _params(repo)
    thr = prm.values["ndvi_bare_threshold"]
    obs = [r for r in repo.ndvi(field_id) if r["ndvi"] is not None and 0 <= r["ndvi"] <= 1 and (r["valid_frac"] or 0) >= 0.5]
    # one value per date (mean of L30/S30)
    by = defaultdict(list)
    for r in obs:
        by[r["date"]].append(r["ndvi"])
    series = sorted((d, float(np.mean(v))) for d, v in by.items())
    hist = {h["year"]: h["crop_name"] for h in repo.crop_history(field_id)}
    periods = []
    run: list[tuple[dt.date, float]] = []

    def close(run, nxt):
        if len(run) < 2:
            return
        start, end = run[0][0], run[-1][0]
        if (end - start).days < 20:
            return
        gaps = ["cloud-masked / low-valid-fraction dates omitted"]
        big = [(a[0], b[0]) for a, b in zip(run, run[1:]) if (b[0] - a[0]).days > 30]
        for a, b in big:
            gaps.append(f"no valid optical observation {a.isoformat()} to {b.isoformat()} (snow/cloud); assumed bare")
        if nxt is None:
            gaps.append("period still open at the end of the loaded HLS series")
        years = sorted({start.year, end.year})
        periods.append({
            "start": start.isoformat(), "end": end.isoformat(), "bare_days": (end - start).days + 1,
            "evidence": {
                "optical_dates": [d.isoformat() for d, _ in run][:: max(1, len(run) // 8)][:8],
                "cdl_year_label": {str(y): hist.get(y) for y in years},
                "method": "ndvi_and_cdl",
                "ndvi_threshold": thr,
                "gaps": gaps,
            },
        })

    for i, (d, v) in enumerate(series):
        if v < thr:
            run.append((d, v))
        else:
            close(run, (d, v))
            run = []
    close(run, None)
    return {"field_id": field_id, "periods": periods, "sources": ["HLS", "CDL"],
            "notes": f"Bare = HLS NDVI below {thr} (team default threshold) between valid observations; "
                     "CDL labels give the crop on either side."}


def vulnerable_seasons(repo, field_id: str | None = None, county_fips: str | None = None) -> dict | None:
    if field_id:
        f = repo.field(field_id)
        if not f:
            return None
        fips = f["county_fips"].strip()
    else:
        fips = county_fips
        if not repo.county(fips or ""):
            return None
    wt = _wx_frame(repo, fips)
    if wt is None:
        return None
    wx, years, months = wt
    last = int(years.max())
    base = (years >= config.BASELINE_START_YEAR) & (years <= config.BASELINE_END_YEAR)
    smap = repo.smap(fips)
    sm_dates = np.array([r["date"] for r in smap]) if smap else np.array([])
    sm_vals = np.array([np.nan if r["value"] is None else r["value"] for r in smap]) if smap else np.array([])
    out = []
    for season, mons in SEASONS.items():
        # winter of year Y = Dec(Y-1) + Jan-Feb(Y); simple month mask per season-year
        syear = np.where((months == 12) & (season == "winter"), years + 1, years)
        msk = np.isin(months, mons)
        yrs = sorted(set(syear[msk & base]))
        tot = {y: float(np.nansum(wx["precip_mm"][msk & (syear == y)])) for y in yrs + [last]}
        tm = {y: float(np.nanmean(wx["t2m_c"][msk & (syear == y)])) for y in yrs + [last]}
        bp = float(np.mean([tot[y] for y in yrs]))
        bt = float(np.mean([tm[y] for y in yrs]))
        p20 = float(np.percentile([tot[y] for y in yrs], 20))
        hazards = []
        heat = float(np.mean([np.nansum(wx["tmax_c"][msk & (syear == y)] > 32) for y in yrs]))
        frost = float(np.mean([np.nansum(wx["tmin_c"][msk & (syear == y)] < 0) for y in yrs]))
        drought_freq = float(np.mean([tot[y] < 0.75 * bp for y in yrs]))
        wet_freq = float(np.mean([tot[y] > 1.25 * bp for y in yrs]))
        if season in ("summer", "spring") and drought_freq >= 0.15:
            hazards.append("drought")
        if heat >= 3:
            hazards.append("heat")
        if season in ("spring", "fall") and frost >= 5:
            hazards.append("frost")
        if wet_freq >= 0.15 and season in ("spring", "summer"):
            hazards.append("heavy_rain")
        if season == "winter":
            hazards.append("bare_soil_erosion")
        sm_anom = None
        if sm_dates.size:
            smon = np.array([d.month for d in sm_dates])
            syr = np.array([d.year + (1 if (d.month == 12 and season == "winter") else 0) for d in sm_dates])
            mm = np.isin(smon, mons)
            ly = int(syr[mm].max()) if mm.any() else None
            if ly is not None:
                cur = np.nanmean(sm_vals[mm & (syr == ly)])
                clim = np.nanmean(sm_vals[mm & (syr < ly)])
                sm_anom = _round(cur - clim, 4) if not np.isnan(clim) else None
        out.append({
            "season": season,
            "hazards": hazards,
            "anomaly_year": last,
            "precip_anomaly_mm": _round(tot[last] - bp, 1),
            "t2m_anomaly_c": _round(tm[last] - bt, 2),
            "smap_sm_anomaly": sm_anom,
            "smap_unit": "cm3/cm3 difference vs SMAP 2015-2024 same-season mean",
            "climatology": {"precip_mm": _round(bp, 1), "precip_p20_mm": _round(p20, 1), "t2m_c": _round(bt, 2),
                            "heat_days_tmax_gt_32c": _round(heat, 1), "frost_days_tmin_lt_0c": _round(frost, 1),
                            "drought_year_fraction": _round(drought_freq, 2), "wet_year_fraction": _round(wet_freq, 2)},
            "notes": "SMAP is a context-cell assignment, not a field-precise measurement.",
        })
    return {
        "field_id": field_id,
        "county_fips": fips,
        "period": {"start": f"{config.BASELINE_START_YEAR}-01-01", "end": f"{config.BASELINE_END_YEAR}-12-31"},
        "seasons": out,
        "sources": CONTEXT_SOURCES,
        "notes": "Hazard flags: drought/heavy_rain if >= 15 % of baseline seasons are < 75 % / > 125 % of mean precipitation; "
                 "heat if >= 3 days/season with Tmax > 32 C; frost if >= 5 days with Tmin < 0 C (team defaults).",
    }


def climate_history(repo, field_id: str, years: int = 5) -> dict | None:
    f = repo.field(field_id)
    if not f:
        return None
    years = int(min(max(years, 1), 5))
    fips = f["county_fips"].strip()
    wt = _wx_frame(repo, fips)
    ann = _annual(wt, config.WEATHER_START_YEAR, config.WEATHER_END_YEAR) if wt else {}
    hist = {h["year"]: h["crop_name"] for h in repo.crop_history(field_id)}
    et = defaultdict(float)
    cnt = defaultdict(int)
    for r in repo.openet(field_id):
        if r["value"] is not None:
            et[r["date"].year] += r["value"]
            cnt[r["date"].year] += 1
    peaks = ndvi_peaks(repo.ndvi(field_id))
    last = max(ann) if ann else max(hist, default=dt.date.today().year)
    out = []
    for y in range(last, last - years, -1):
        a = ann.get(y, {})
        out.append({"year": y, "precip_mm": _round(a.get("precip_mm"), 1), "et_mm": _round(et[y], 1) if cnt.get(y) == 12 else None,
                    "ndvi_peak": _round(peaks.get(y), 3), "t2m_mean_c": _round(a.get("t2m_mean_c"), 2),
                    "frost_days": a.get("frost_days"), "heat_days": a.get("heat_days"),
                    "crop_cdl": hist.get(y), "naip_thumb_url": None})
    return {"field_id": field_id, "years": out, "sources": ["POWER", "OpenET", "HLS", "CDL"],
            "notes": "precip/t2m: NASA POWER county point; et_mm: OpenET Ensemble monthly sum (12 months only); "
                     "ndvi_peak: 95th percentile of valid HLS NDVI that year. NAIP thumbnails not loaded."}


def _pct(vals):
    if not vals:
        return {"p10": None, "p50": None, "p90": None}
    q = np.percentile(vals, [10, 50, 90])
    return {"p10": _round(q[0], 2), "p50": _round(q[1], 2), "p90": _round(q[2], 2)}


def climate_outlook(repo, fips: str, field_id: str | None = None) -> dict:
    rows = repo.scenario_year(fips)
    gaps = []
    wt = _wx_frame(repo, fips)
    nxt = None
    s2s = [r for r in rows if r["source_id"] == "geos_s2s"]
    if s2s and wt:
        wx, years, months = wt
        base = (years >= config.BASELINE_START_YEAR) & (years <= config.BASELINE_END_YEAR)
        season = "JJ" if any(r["season"] == "JJ" for r in s2s) else s2s[0]["season"]
        mons = {"JJ": [6, 7], "MAM": [3, 4, 5]}.get(season, [6, 7, 8])
        msk = np.isin(months, mons) & base
        p_clim = float(np.nanmean(wx["precip_mm"][msk]))
        t_clim = float(np.nanmean(wx["t2m_c"][msk]))
        pr = [(r["value"] / p_clim - 1) * 100 for r in s2s if r["variable"] == "pr" and r["season"] == season and r["value"] is not None]
        ta = [r["value"] - t_clim for r in s2s if r["variable"] == "tas" and r["season"] == season and r["value"] is not None]
        yr = s2s[0]["year"]
        inits = sorted({r["member"][:6] for r in s2s if r["member"][:6].isdigit()})
        nxt = {"source_id": "geos_s2s", "init": f"{inits[-1][:4]}-{inits[-1][4:6]}" if inits else None,
               "period": f"{yr}-{season}", "pr_anomaly_pct": _pct(pr), "tas_anomaly_c": _pct(ta),
               "n_members": len({r["member"] for r in s2s}), "native_resolution": "0.5 deg",
               "baseline": f"NASA POWER {config.BASELINE_START_YEAR}-{config.BASELINE_END_YEAR} same months (no hindcast bias correction)",
               "seasons_available": sorted({r["season"] for r in s2s})}
    else:
        gaps.append("GEOS-S2S rows not loaded for this county")
    mid = []
    nex = [r for r in rows if r["source_id"] == "nex_gddp"]
    for scen in ("ssp245", "ssp585"):
        models = sorted({r["model"] for r in nex if r["scenario"] == scen})
        prc, txc = [], []
        fut_years = sorted({r["year"] for r in nex if r["scenario"] == scen})
        for m in models:
            def mean(sc, var, m=m):
                v = [r["value"] for r in nex if r["model"] == m and r["scenario"] == sc and r["variable"] == var and r["season"] == "ANN"
                     and r["value"] is not None]
                return float(np.mean(v)) if v else None
            ph, pf, xh, xf = mean("historical", "pr"), mean(scen, "pr"), mean("historical", "tasmax"), mean(scen, "tasmax")
            if None not in (ph, pf) and ph > 0:
                prc.append((pf / ph - 1) * 100)
            if None not in (xh, xf):
                txc.append(xf - xh)
        if models:
            mid.append({"source_id": "nex_gddp", "scenario": scen, "period": f"{fut_years[0]}-{fut_years[-1]}",
                        "baseline_period": "1985-2014",
                        "pr_change_pct": {"min": _round(min(prc), 2), "p50": _round(float(np.median(prc)), 2), "max": _round(max(prc), 2)} if prc else None,
                        "tasmax_change_c": {"min": _round(min(txc), 2), "p50": _round(float(np.median(txc)), 2), "max": _round(max(txc), 2)} if txc else None,
                        "n_models": len(models), "models": models, "season": "ANN"})
    if not nex:
        gaps.append("NEX-GDDP-CMIP6 rows not loaded for this county")
    return {"field_id": field_id, "county_fips": fips, "next_season": nxt, "mid_century": mid,
            "label": "Possible ranges (scenarios), not a forecast of a single future.",
            "native_resolution_note": "Context-cell data (tens of km), not field-precise.", "info_gaps": gaps}


def county_summary(repo, fips: str) -> dict | None:
    c = repo.county(fips)
    if not c:
        return None
    gaps = []
    wt = _wx_frame(repo, fips)
    ann = _annual(wt, config.BASELINE_START_YEAR, config.BASELINE_END_YEAR) if wt else {}
    shares = repo.crop_shares(fips)
    by_year = defaultdict(dict)
    for r in shares:
        by_year[r["year"]][r["crop_name"] or str(r["cdl_class"])] = _round(r["share"], 4)
    latest = max(by_year) if by_year else None
    yields = defaultdict(dict)
    for r in repo.yields(fips):
        yields[r["year"]][r["crop"]] = r["yield_bu_ac"]
    smap = repo.smap(fips)
    sm = None
    if smap:
        vals = [r["value"] for r in smap if r["value"] is not None]
        last_year = max(r["date"].year for r in smap)
        cur = [r["value"] for r in smap if r["date"].year == last_year and r["value"] is not None]
        sm = {"product": smap[0]["product"], "unit": smap[0]["unit"], "mean_all": _round(float(np.mean(vals)), 4),
              "mean_latest_year": _round(float(np.mean(cur)), 4) if cur else None, "latest_year": last_year,
              "period": f"{smap[0]['date']}..{smap[-1]['date']}", "native_resolution": "nominal 36 km L3",
              "notes": "Context-cell value, not field-precise."}
    else:
        gaps.append("SMAP rows not loaded for this county")
    if repo.imerg_count(fips) == 0:
        gaps.append("GPM IMERG not loaded; POWER precipitation used")
    return {
        "county_fips": c["county_fips"], "state_alpha": c["state_alpha"], "name": c["name"], "area_km2": _round(c["area_km2"], 1),
        "centroid": {"type": "Point", "coordinates": [c["lon"], c["lat"]]},
        "tier": "field" if fips == config.STORY_FIPS else "county",
        "field_level_available": fips == config.STORY_FIPS,
        "climate": {
            "period": {"start": f"{config.BASELINE_START_YEAR}-01-01", "end": f"{config.BASELINE_END_YEAR}-12-31"},
            "precip_mm_yr": _round(float(np.mean([v["precip_mm"] for v in ann.values()])), 1) if ann else None,
            "t2m_mean_c": _round(float(np.mean([v["t2m_mean_c"] for v in ann.values()])), 2) if ann else None,
            "frost_days_yr": _round(float(np.mean([v["frost_days"] for v in ann.values()])), 1) if ann else None,
            "heat_days_yr": _round(float(np.mean([v["heat_days"] for v in ann.values()])), 1) if ann else None,
            "source_id": "power",
        },
        "crop_share": {"latest_year": latest, "latest": by_year.get(latest, {}),
                       "corn_soy_share_by_year": {y: _round((v.get("Corn") or 0) + (v.get("Soybeans") or 0), 4) for y, v in sorted(by_year.items())},
                       "source_id": "cdl", "unit": "fraction of classified county pixels"},
        "yield_bu_ac": {str(y): v for y, v in sorted(yields.items())[-5:]},
        "yield_unit": "bu/ac (USDA NASS county, bulk file)",
        "smap": sm,
        "outlook": climate_outlook(repo, fips),
        "info_gaps": gaps,
        "sources": ["POWER", "CDL", "NASS", "SMAP", "GEOS-S2S", "NEX-GDDP-CMIP6"],
    }


def backtest(repo, field_id: str, year: int, sim_one_year) -> dict | None:
    f = repo.field(field_id)
    if not f:
        return None
    hist = {h["year"]: h["crop_name"] for h in repo.crop_history(field_id)}
    fips = f["county_fips"].strip()
    y = {}
    for r in repo.yields(fips):
        if r["year"] == year:
            y[r["crop"]] = r["yield_bu_ac"]
    seq_code = {"Corn": "C", "Soybeans": "S"}
    observed = "-".join(seq_code.get(hist.get(yy), "?") for yy in (year - 1, year) if hist.get(yy))
    metrics = sim_one_year(field_id, year)
    results = []
    for code, m in metrics.items():
        results.append({
            "strategy_code": code, "year": year, "observed_sequence": observed if code == "A" else None,
            "observed_cdl": hist.get(year) if code == "A" else None,
            "notes": ("Deterministic water balance driven by the actual POWER weather of this year (previous year as spin-up); "
                      "observed CDL crop used for A. County yield is context only (NASS bulk file)."
                      + (" 2012 is the US drought stress year." if year == 2012 else "")),
            "metrics": m,
        })
    return {"field_id": field_id, "years": [year], "county_yield_bu_ac": {str(year): y or None}, "yield_unit": "bu/ac",
            "results": results, "sources": ["CDL", "CSB", "POWER", "SSURGO", "NASS"]}
