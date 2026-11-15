"""Tier 1 Quick Screen: FAO-56 screening engine for an arbitrary user polygon (no DB dependency).

Ported from the team MATLAB prototype V8 (FieldShift_LiveAPI_Engineeee.m) with these honesty changes:
- No fallback constants. A failed external call -> that block is null and a line goes into `info_gaps`.
- Kc from FAO-56 Table 12 (not the prototype's 1.08/0.86/0.75). ET0 is FAO-56 Penman-Monteith (eq. 6) from NASA POWER.
- V8's blending weights (0.6 model / 0.4 trend, NWS x0.08), synthetic DEM grid / slope, NDVI and SOM proxies and
  the CROP_DB economics are not ported: they had no traceable source.
- Rotation candidates are listed in generation order and are NOT ranked.
Every number is a screening estimate, not a field-level prediction or a guarantee.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
import json
import math
import os
import statistics
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

LABEL = "screening estimate"
ENGINE = "FAO-56 engine (ported from team MATLAB prototype V8)"
CROPS = ("Corn", "Soy", "Wheat")
CACHE_DIR = Path(os.environ.get("QUICK_CACHE_DIR", "/srv/hackathon/data/cache/quick"))
TIMEOUT_S = 20.0
USER_AGENT = "ARTFARM-hackathon-demo"
HIST_START, HIST_END = 2015, 2024  # 10 complete years
PROJ_START, PROJ_END = 2026, 2039  # V8 queried Open-Meteo climate 2026-2039
POWER_PARAMS = "T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,ALLSKY_SFC_SW_DWN,RH2M,WS2M,PS,GWETROOT"
CORN_BELT_BOX = {"lat": (36.0, 48.0), "lon": (-104.0, -80.0)}  # V8 support region

# FAO-56 Table 12 (Allen et al. 1998), single crop coefficients, sub-humid climate (RHmin ~45 %, u2 ~2 m/s).
KC = {
    "Corn": {"ini": 0.30, "mid": 1.20, "end": 0.60, "note": "Maize (field, grain); Kc_end 0.60 (table range 0.60-0.35 by harvest moisture)"},
    "Soy": {"ini": 0.40, "mid": 1.15, "end": 0.50, "note": "Soybeans"},
    "Wheat": {"ini": 0.40, "mid": 1.15, "end": 0.40, "note": "Winter wheat; Kc_ini 0.40 (0.7 on frozen soils), Kc_end 0.40 (table range 0.25-0.4)"},
}
KC_SOURCE = "FAO-56 Table 12 (Allen et al. 1998, FAO Irrigation and Drainage Paper 56)"
# Season windows and stage fractions are screening assumptions chosen by the team, NOT sourced planting dates.
SEASON = {  # (start month, start day, end month, end day, starts in previous year)
    "Corn": (5, 1, 9, 30, False),
    "Soy": (5, 15, 9, 30, False),
    "Wheat": (10, 1, 7, 10, True),
}
STAGE_FRAC = (0.17, 0.28, 0.33, 0.22)  # ini, development, mid, late (FAO-56 4-stage curve shape; fractions assumed)

RELATIVE_INDEX_TOOLTIP = "Relative index vs continuous corn (=100) in the same location; not a guarantee or a measured saving."


# --------------------------------------------------------------------------------------------- HTTP + cache
def _cache_path(url: str) -> Path:
    return CACHE_DIR / (hashlib.sha256(url.encode()).hexdigest() + ".json")


def _http_get_json(url: str) -> dict:
    """Network GET (replaced in tests). Raises on any failure."""
    import httpx

    r = httpx.get(url, timeout=TIMEOUT_S, headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json, application/json"},
                  follow_redirects=True)
    r.raise_for_status()
    return r.json()


def fetch_json(url: str) -> dict:
    """Disk-cached GET. Only successful responses are cached."""
    p = _cache_path(url)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    data = _http_get_json(url)
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(data))
        tmp.replace(p)
    except OSError:
        pass
    return data


# --------------------------------------------------------------------------------------------- geometry
def _ring(polygon) -> list[tuple[float, float]]:
    pts = [(float(p[0]), float(p[1])) for p in polygon]
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    return pts


def polygon_metrics(polygon) -> dict:
    """V8 method: local tangent plane at the mean latitude using WGS84 meridian (Rm) and prime-vertical (Rn) radii,
    then shoelace area and summed edge lengths."""
    pts = _ring(polygon)
    a, f = 6378137.0, 1 / 298.257223563
    e2 = f * (2 - f)
    lon0 = sum(p[0] for p in pts) / len(pts)
    lat0d = sum(p[1] for p in pts) / len(pts)
    lat0 = math.radians(lat0d)
    den = math.sqrt(1 - e2 * math.sin(lat0) ** 2)
    rm, rn = a * (1 - e2) / den ** 3, a / den
    mlat, mlon = rm * math.pi / 180, rn * math.cos(lat0) * math.pi / 180
    xy = [((lo - lon0) * mlon, (la - lat0d) * mlat) for lo, la in pts]
    n = len(xy)
    area = abs(sum(xy[i][0] * xy[(i + 1) % n][1] - xy[(i + 1) % n][0] * xy[i][1] for i in range(n))) / 2
    perim = sum(math.hypot(xy[(i + 1) % n][0] - xy[i][0], xy[(i + 1) % n][1] - xy[i][1]) for i in range(n))
    # area-weighted centroid in the local plane
    cx = cy = 0.0
    sa = 0.0
    for i in range(n):
        x0, y0 = xy[i]
        x1, y1 = xy[(i + 1) % n]
        c = x0 * y1 - x1 * y0
        sa += c
        cx += (x0 + x1) * c
        cy += (y0 + y1) * c
    if abs(sa) > 1e-9:
        cx, cy = cx / (3 * sa), cy / (3 * sa)
    else:
        cx, cy = 0.0, 0.0
    clon, clat = lon0 + cx / mlon, lat0d + cy / mlat
    box = CORN_BELT_BOX
    inside = all(box["lat"][0] <= la <= box["lat"][1] and box["lon"][0] <= lo <= box["lon"][1] for lo, la in pts)
    return {"area_ha": round(area / 1e4, 3), "perimeter_km": round(perim / 1e3, 4), "vertex_count": n,
            "centroid": {"lon": round(clon, 6), "lat": round(clat, 6)}, "in_corn_belt_box": inside,
            "method": "WGS84 local tangent plane (Rm/Rn at mean latitude) + shoelace, as in MATLAB V8"}


# --------------------------------------------------------------------------------------------- FAO-56 ET0
def _es(t: float) -> float:
    return 0.6108 * math.exp(17.27 * t / (t + 237.3))


def et0_pm(doy: int, lat: float, tmax: float, tmin: float, rh: float, u2: float, rs: float, p_kpa: float, z: float | None) -> float:
    """FAO-56 Penman-Monteith daily ET0 (eq. 6), G = 0, ea from RHmean (eq. 19), Rso eq. 37 (or 36 without z)."""
    t = (tmax + tmin) / 2
    delta = 4098 * _es(t) / (t + 237.3) ** 2
    gamma = 0.000665 * p_kpa
    es = (_es(tmax) + _es(tmin)) / 2
    ea = rh / 100 * es
    phi = math.radians(lat)
    dr = 1 + 0.033 * math.cos(2 * math.pi * doy / 365)
    dec = 0.409 * math.sin(2 * math.pi * doy / 365 - 1.39)
    ws = math.acos(max(-1.0, min(1.0, -math.tan(phi) * math.tan(dec))))
    ra = 24 * 60 / math.pi * 0.0820 * dr * (ws * math.sin(phi) * math.sin(dec) + math.cos(phi) * math.cos(dec) * math.sin(ws))
    rso = (0.75 + 2e-5 * z) * ra if z is not None else 0.75 * ra
    rns = 0.77 * rs
    ratio = min(1.0, rs / rso) if rso > 0 else 1.0
    rnl = 4.903e-9 * ((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2 * (0.34 - 0.14 * math.sqrt(max(ea, 0))) * (1.35 * ratio - 0.35)
    rn = rns - rnl
    et0 = (0.408 * delta * rn + gamma * 900 / (t + 273) * u2 * (es - ea)) / (delta + gamma * (1 + 0.34 * u2))
    return max(0.0, et0)


def peff_month(p: float) -> float:
    """USDA SCS effective rainfall, monthly (as implemented in FAO CROPWAT)."""
    return p * (125 - 0.2 * p) / 125 if p <= 250 else 125 + 0.1 * p


def kc_on(crop: str, day_idx: int, season_len: int) -> float:
    k = KC[crop]
    f = [x * season_len for x in STAGE_FRAC]
    b1, b2, b3 = f[0], f[0] + f[1], f[0] + f[1] + f[2]
    if day_idx < b1:
        return k["ini"]
    if day_idx < b2:
        return k["ini"] + (k["mid"] - k["ini"]) * (day_idx - b1) / f[1]
    if day_idx < b3:
        return k["mid"]
    return k["mid"] + (k["end"] - k["mid"]) * (day_idx - b3) / f[3]


def _season_dates(crop: str, year: int) -> tuple[dt.date, dt.date]:
    m0, d0, m1, d1, prev = SEASON[crop]
    return dt.date(year - 1 if prev else year, m0, d0), dt.date(year, m1, d1)


def season_balance(crop: str, year: int, daily: dict[dt.date, tuple[float, float]]) -> dict | None:
    """daily: date -> (ET0 mm, P mm). Returns season ETc / Peff / deficit or None if >10 % days missing."""
    s, e = _season_dates(crop, year)
    n = (e - s).days + 1
    etc, months, missing = 0.0, {}, 0
    for i in range(n):
        d = s + dt.timedelta(days=i)
        v = daily.get(d)
        if v is None or v[0] is None or v[1] is None:
            missing += 1
            continue
        etc += kc_on(crop, i, n) * v[0]
        months[(d.year, d.month)] = months.get((d.year, d.month), 0.0) + v[1]
    if missing > 0.1 * n:
        return None
    scale = n / (n - missing) if missing else 1.0
    etc *= scale
    p = sum(months.values()) * scale
    pe = sum(peff_month(x) for x in months.values()) * scale
    return {"etc_mm": etc, "precip_mm": p, "peff_mm": pe, "deficit_mm": max(0.0, etc - pe)}


def _dist(vals: list[float]) -> dict | None:
    v = sorted(x for x in vals if x is not None)
    if not v:
        return None

    def q(p):
        k = (len(v) - 1) * p
        lo, hi = math.floor(k), math.ceil(k)
        return v[lo] + (v[hi] - v[lo]) * (k - lo)

    return {"p10": round(q(0.1), 1), "p50": round(q(0.5), 1), "p90": round(q(0.9), 1), "mean": round(statistics.fmean(v), 1), "n_years": len(v)}


def _summarize(crop: str, years: range, daily: dict) -> dict | None:
    rows = {y: season_balance(crop, y, daily) for y in years}
    rows = {y: r for y, r in rows.items() if r}
    if not rows:
        return None
    vals = list(rows.values())
    return {
        "years": [min(rows), max(rows)],
        "etc_mm": _dist([r["etc_mm"] for r in vals]),
        "precip_mm": _dist([r["precip_mm"] for r in vals]),
        "effective_precip_mm": _dist([r["peff_mm"] for r in vals]),
        "irrigation_deficit_mm": _dist([r["deficit_mm"] for r in vals]),
        "water_stress": {
            "share_of_years_with_deficit": round(sum(r["deficit_mm"] > 0 for r in vals) / len(vals), 2),
            "peff_to_etc_ratio": _dist([r["peff_mm"] / r["etc_mm"] if r["etc_mm"] > 0 else None for r in vals]),
        },
    }


# --------------------------------------------------------------------------------------------- external blocks
def _num(x):
    return None if x is None or x == -999 or x == -999.0 or (isinstance(x, float) and math.isnan(x)) else float(x)


def urls(lon: float, lat: float) -> dict[str, str]:
    return {
        "elevation": f"https://epqs.nationalmap.gov/v1/json?x={lon:.6f}&y={lat:.6f}&units=Meters&wkid=4326",
        "power": ("https://power.larc.nasa.gov/api/temporal/daily/point?parameters=" + POWER_PARAMS +
                  f"&community=AG&longitude={lon:.4f}&latitude={lat:.4f}&start={HIST_START}0101&end={HIST_END}1231&format=JSON"),
        "nws_points": f"https://api.weather.gov/points/{lat:.4f},{lon:.4f}",
        "open_meteo": ("https://climate-api.open-meteo.com/v1/climate?" f"latitude={lat:.4f}&longitude={lon:.4f}"
                       f"&start_date={PROJ_START}-01-01&end_date={PROJ_END}-12-31&models=MRI_AGCM3_2_S"
                       "&daily=temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum,shortwave_radiation_sum,"
                       "relative_humidity_2m_mean,wind_speed_10m_mean&wind_speed_unit=ms"),
    }


def get_elevation(url: str) -> dict:
    v = _num(fetch_json(url).get("value"))
    if v is None or v < -100:
        raise ValueError("invalid elevation")
    return {"value_m": round(v, 2), "point": "polygon centroid", "source": "USGS 3DEP Elevation Point Query Service (EPQS)"}


def get_power(url: str) -> dict:
    """Returns parsed daily series {date: {...}} from NASA POWER."""
    raw = fetch_json(url)
    par = raw["properties"]["parameter"]
    out = {}
    for key in par["T2M"]:
        d = dt.date(int(key[:4]), int(key[4:6]), int(key[6:8]))
        out[d] = {k: _num(par.get(k, {}).get(key)) for k in POWER_PARAMS.split(",")}
    geom_z = None
    try:
        geom_z = _num(raw["geometry"]["coordinates"][2])
    except Exception:
        pass
    return {"daily": out, "geom_elev_m": geom_z}


def get_nws(points_url: str) -> list[dict]:
    meta = fetch_json(points_url)
    fc = fetch_json(meta["properties"]["forecast"])
    return fc["properties"]["periods"]


def get_open_meteo(url: str, lat: float) -> dict:
    """Open-Meteo climate API. Its et0_fao_evapotranspiration is null for climate models (V8 summed NaNs with omitnan -> 0),
    so ET0 is computed here with the same FAO-56 PM from the model's Tmax/Tmin/RH/wind/shortwave.
    u2 from u10 by FAO-56 eq. 47; pressure from the model grid elevation by FAO-56 eq. 7."""
    raw = fetch_json(url)
    d = raw["daily"]
    z = _num(raw.get("elevation"))
    pk = 101.3 * ((293 - 0.0065 * (z or 0.0)) / 293) ** 5.26
    out = {}
    for i, t in enumerate(d["time"]):
        day = dt.date.fromisoformat(t)
        tx, tn, rh, u10, rs = (_num(d[k][i]) for k in ("temperature_2m_max", "temperature_2m_min", "relative_humidity_2m_mean",
                                                        "wind_speed_10m_mean", "shortwave_radiation_sum"))
        e = None
        if None not in (tx, tn, rh, u10, rs):
            e = et0_pm(day.timetuple().tm_yday, lat, tx, tn, rh, u10 * 4.87 / math.log(67.8 * 10 - 5.42), rs, pk, z)
        out[day] = (e, _num(d["precipitation_sum"][i]), _num(d["temperature_2m_mean"][i]))
    if all(v[0] is None for v in out.values()):
        raise ValueError("no ET0 inputs in Open-Meteo response")
    return out


# --------------------------------------------------------------------------------------------- crops / rotations
def normalize_crops(crops: list[str]) -> list[str]:
    alias = {"corn": "Corn", "maize": "Corn", "soy": "Soy", "soybean": "Soy", "soybeans": "Soy", "wheat": "Wheat"}
    out = []
    for c in crops:
        n = alias.get(str(c).strip().lower())
        if n is None:
            raise ValueError(f"unknown crop {c!r}; allowed: Corn, Soy, Wheat")
        out.append(n)
    if not 2 <= len(out) <= 3:
        raise ValueError("select 2-3 crops")
    if any(a == b for a, b in zip(out, out[1:])):
        raise ValueError("consecutive duplicate crop is not allowed")
    if len(set(out)) < 2:
        raise ValueError("select at least 2 different crops")
    return out


def rotation_candidates(crops: list[str]) -> list[list[str]]:
    """V8 generation rule: 2 crops -> both 2-year orders; 3 crops -> V8 3-year list filtered to the selection.
    No consecutive duplicates, including across the cycle wrap. Output order is generation order, NOT a ranking."""
    u = list(dict.fromkeys(crops))
    if len(u) == 2:
        seqs = [[u[0], u[1]], [u[1], u[0]]]
    else:
        seqs = [["Corn", "Soy", "Wheat"], ["Soy", "Wheat", "Corn"], ["Wheat", "Corn", "Soy"], ["Corn", "Soy", "Corn"]]
        seqs = [s for s in seqs if set(s) <= set(u)]
    # cyclic check: the rotation repeats, so last->first must also differ (drops V8's Corn-Soy-Corn,
    # which becomes corn-after-corn when the cycle restarts)
    return [s for s in seqs if all(a != b for a, b in zip(s, s[1:] + s[:1]))]


# --------------------------------------------------------------------------------------------- main
def _fetch_all(u: dict[str, str], lat: float) -> dict:
    jobs = {"elevation": (get_elevation, u["elevation"]), "power": (get_power, u["power"]),
            "nws": (get_nws, u["nws_points"]), "open_meteo": (lambda url: get_open_meteo(url, lat), u["open_meteo"])}
    res: dict = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {k: ex.submit(fn, url) for k, (fn, url) in jobs.items()}
        for k, f in futs.items():
            try:
                res[k] = f.result()
            except Exception as exc:  # any failure -> null block + info gap
                res[k] = exc
    return res


def quick_screen(polygon, crops) -> dict:
    pts = _ring(polygon)
    if len(pts) < 3:
        raise ValueError("polygon needs at least 3 distinct vertices")
    for lo, la in pts:
        if not (-180 <= lo <= 180 and -90 <= la <= 90):
            raise ValueError("coordinates must be [lon, lat] in WGS84 degrees")
    crops = normalize_crops(list(crops))
    geom = polygon_metrics(pts)
    if geom["area_ha"] <= 0:
        raise ValueError("polygon has zero area")
    lon, lat = geom["centroid"]["lon"], geom["centroid"]["lat"]
    u = urls(lon, lat)
    got = _fetch_all(u, lat)
    gaps: list[str] = []
    if not geom["in_corn_belt_box"]:
        gaps.append("Polygon is outside the V8 Corn Belt support box (36-48N, 104-80W); parameters may not apply.")

    def ok(k, msg):
        v = got.get(k)
        if isinstance(v, Exception):
            code = getattr(getattr(v, "response", None), "status_code", None)
            gaps.append(f"{msg} unavailable ({type(v).__name__}{f' HTTP {code}' if code else ''}); block left empty.")
            return None
        return v

    elevation = ok("elevation", "USGS 3DEP elevation")
    power = ok("power", "NASA POWER daily history")
    periods = ok("nws", "NWS forecast")
    om = ok("open_meteo", "Open-Meteo climate projection")

    # ---- history (NASA POWER) -> daily ET0 (PM) and P
    hist_daily: dict[dt.date, tuple] = {}
    climate_history = None
    if power:
        z = elevation["value_m"] if elevation else power["geom_elev_m"]
        per_year: dict[int, dict] = {}
        n_pm = n_skip = 0
        for d, r in power["daily"].items():
            need = [r["T2M_MAX"], r["T2M_MIN"], r["RH2M"], r["WS2M"], r["ALLSKY_SFC_SW_DWN"], r["PS"]]
            e = None
            if all(x is not None for x in need):
                e = et0_pm(d.timetuple().tm_yday, lat, r["T2M_MAX"], r["T2M_MIN"], r["RH2M"], r["WS2M"], r["ALLSKY_SFC_SW_DWN"], r["PS"], z)
                n_pm += 1
            else:
                n_skip += 1
            hist_daily[d] = (e, r["PRECTOTCORR"])
            y = per_year.setdefault(d.year, {"t": [], "p": 0.0, "e": 0.0, "w": []})
            if r["T2M"] is not None:
                y["t"].append(r["T2M"])
            y["p"] += r["PRECTOTCORR"] or 0.0
            y["e"] += e or 0.0
            if r["GWETROOT"] is not None:
                y["w"].append(r["GWETROOT"])
        rows = [{"year": y, "t2m_mean_c": round(statistics.fmean(v["t"]), 2) if v["t"] else None,
                 "precip_mm": round(v["p"], 1), "et0_pm_mm": round(v["e"], 1),
                 "root_zone_wetness_mean": round(statistics.fmean(v["w"]), 3) if v["w"] else None}
                for y, v in sorted(per_year.items())]
        climate_history = {
            "source": "NASA POWER daily (community=AG), MERRA-2/CERES based, ~0.5 x 0.625 deg grid - not field-level",
            "period": f"{HIST_START}-{HIST_END}", "point": "polygon centroid", "per_year": rows,
            "mean": {"t2m_c": _dist([r["t2m_mean_c"] for r in rows]), "precip_mm": _dist([r["precip_mm"] for r in rows]),
                     "et0_mm": _dist([r["et0_pm_mm"] for r in rows])},
            "et0_method": "FAO-56 Penman-Monteith (eq. 6), daily, G=0",
            "days_missing_inputs": n_skip,
        }
        if not elevation:
            gaps.append("Rso for ET0 used the NASA POWER grid-cell elevation instead of USGS 3DEP.")

    # ---- NWS forecast anomaly (reported only, not blended into results)
    forecast = None
    if periods is not None:
        temps = [((p["temperature"] - 32) * 5 / 9 if p.get("temperatureUnit", "F") == "F" else p["temperature"]) for p in periods
                 if p.get("temperature") is not None]
        doys = set()
        for p in periods:
            try:
                doys.add(dt.datetime.fromisoformat(p["startTime"]).timetuple().tm_yday)
            except Exception:
                pass
        base = [r["T2M"] for d, r in (power["daily"].items() if power else []) if d.timetuple().tm_yday in doys and r["T2M"] is not None]
        fmean = statistics.fmean(temps) if temps else None
        bmean = statistics.fmean(base) if base else None
        forecast = {
            "source": "NOAA National Weather Service api.weather.gov (7-day forecast periods)",
            "n_periods": len(periods), "forecast_mean_temp_c": round(fmean, 2) if fmean is not None else None,
            "baseline_mean_temp_c": round(bmean, 2) if bmean is not None else None,
            "baseline": f"NASA POWER T2M {HIST_START}-{HIST_END}, same calendar days",
            "anomaly_c": round(fmean - bmean, 2) if fmean is not None and bmean is not None else None,
            "note": "Mean of day-high/night-low periods vs daily-mean baseline; short-range context only, not used in crop cards.",
        }
        if forecast["anomaly_c"] is None:
            gaps.append("NWS forecast anomaly could not be computed (no NASA POWER baseline).")

    # ---- Open-Meteo climate projection
    proj_daily: dict[dt.date, tuple] = {}
    climate_projection = None
    if om:
        proj_daily = {d: (v[0], v[1]) for d, v in om.items()}

        def per(y0, y1):
            ys = range(y0, y1 + 1)
            t = [v[2] for d, v in om.items() if d.year in ys and v[2] is not None]
            return {"t2m_mean_c": round(statistics.fmean(t), 2) if t else None,
                    "precip_mm_per_year": _dist([sum(v[1] or 0 for d, v in om.items() if d.year == y) for y in ys]),
                    "et0_mm_per_year": _dist([sum(v[0] or 0 for d, v in om.items() if d.year == y) for y in ys])}

        climate_projection = {
            "source": "Open-Meteo Climate API, model MRI_AGCM3_2_S (CMIP6 HighResMIP), as queried by V8",
            "et0_method": "FAO-56 Penman-Monteith computed from model daily fields (API et0 field is null for climate models)",
            "note": "One climate model, one trajectory: a plausible range (scenario), not a forecast. "
                    "V8's 0.6/0.4 model-trend blending is not ported (unsourced weights).",
            "periods": {f"{PROJ_START}-2029": per(PROJ_START, 2029), f"2030-{PROJ_END}": per(2030, PROJ_END)},
        }

    # ---- crop cards
    cards = []
    for c in dict.fromkeys(crops):
        s, e = _season_dates(c, 2001)
        cards.append({
            "crop": c, "label": LABEL,
            "kc": {"ini": KC[c]["ini"], "mid": KC[c]["mid"], "end": KC[c]["end"], "note": KC[c]["note"], "source": KC_SOURCE},
            "season_window": {"start": s.strftime("%m-%d"), "end": e.strftime("%m-%d"), "label": "assumption",
                              "note": "Generic Corn Belt window chosen by the team; local planting dates not verified."},
            "history": _summarize(c, range(HIST_START, HIST_END + 1), hist_daily) if hist_daily else None,
            "projection": _summarize(c, range(PROJ_START, PROJ_END + 1), proj_daily) if proj_daily else None,
            "units": {"etc_mm": "mm per season", "effective_precip_mm": "mm per season (USDA SCS monthly method)",
                      "irrigation_deficit_mm": "mm per season = max(0, ETc - Peff), no soil storage credit"},
        })

    # ---- rotations (not ranked)
    by_crop = {cd["crop"]: cd for cd in cards}

    def mean_of(seq, block, key):
        vals = [by_crop[x][block][key]["mean"] for x in seq if by_crop[x][block] and by_crop[x][block][key]]
        return statistics.fmean(vals) if len(vals) == len(seq) else None

    corn_ref = None
    if hist_daily:
        cr = _summarize("Corn", range(HIST_START, HIST_END + 1), hist_daily)
        corn_ref = cr["etc_mm"]["mean"] if cr else None
    rotations = []
    for i, seq in enumerate(rotation_candidates(crops), 1):
        etc = mean_of(seq, "history", "etc_mm")
        dfc = mean_of(seq, "history", "irrigation_deficit_mm")
        rotations.append({
            "candidate": i, "sequence": seq, "label": LABEL, "ranked": False,
            "mean_season_etc_mm": round(etc, 1) if etc is not None else None,
            "mean_season_irrigation_deficit_mm": round(dfc, 1) if dfc is not None else None,
            "relative_water_use_index": ({"value": round(etc / corn_ref * 100, 1), "unit": "relative index (continuous corn = 100)",
                                          "tooltip": RELATIVE_INDEX_TOOLTIP} if etc is not None and corn_ref else None),
        })

    gaps += [
        "Economic assumptions (price, yield, cost) omitted: mockup CROP_DB values could not be matched to a specific "
        "USDA ERS/NASS table and year.",
        "Soil organic matter index omitted: prototype c_in / erosion coefficients have no traceable source.",
        "Soil water holding capacity not used (no SSURGO lookup in Tier 1); deficits ignore soil storage.",
        "Slope not computed: only the centroid elevation is queried (no DEM grid in Tier 1).",
    ]
    return {
        "label": LABEL, "engine": ENGINE, "tier": "quick",
        "generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "input": {"polygon": [list(p) for p in pts], "crops": crops},
        "geometry": geom, "elevation": elevation, "climate_history": climate_history, "forecast_anomaly": forecast,
        "climate_projection": climate_projection, "crop_cards": cards, "rotation_candidates": rotations,
        "economic_assumptions": [],
        "assumptions": [
            {"name": "season_window", "label": "assumption", "value": {c: SEASON[c][:4] for c in SEASON}},
            {"name": "stage_fractions", "label": "assumption", "value": list(STAGE_FRAC),
             "note": "FAO-56 four-stage Kc curve; stage length fractions assumed, not from FAO-56 Table 11."},
        ],
        "info_gaps": gaps,
        "sources": [KC_SOURCE, "NASA POWER (power.larc.nasa.gov)", "USGS 3DEP EPQS", "NOAA NWS api.weather.gov",
                    "Open-Meteo Climate API (MRI-AGCM3-2-S)", "USDA SCS effective rainfall (FAO CROPWAT)"],
        "disclaimer": "Screening estimate from coarse public grids at the polygon centroid. Not a field-level prediction, "
                      "not a guarantee, and does not replace local agronomic judgement. Candidates are not ranked.",
    }


async def quick_screen_async(polygon, crops) -> dict:
    return await asyncio.to_thread(quick_screen, polygon, crops)
