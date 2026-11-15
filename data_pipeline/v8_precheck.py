"""Pre-run check: Python re-implementation of the FieldShift_V8_batch.m data path.

Reads v8_api_cache (no network), applies the same validators as the patched
MATLAB batch (USGS, POWER, NWS, Open-Meteo) and recomputes geo/dem/env/proj and
the four rotation cards with MATLAB rounding. Allocation (fminsearch) is not
re-implemented. Diagnostic only; MATLAB remains the source of the outputs.

Usage: python data_pipeline/v8_precheck.py [--all]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import date, timedelta
from pathlib import Path

import numpy as np

INPUTS = Path("/srv/hackathon/data/processed/v1/matlab/inputs")
CACHE = INPUTS / "v8_api_cache"


def mround(x: float, n: int = 0) -> float:
    """MATLAB round(): half away from zero."""
    f = 10.0**n
    return math.copysign(math.floor(abs(x) * f + 0.5), x) / f


def _days(a: date, b: date) -> list[date]:
    return [a + timedelta(i) for i in range((b - a).days + 1)]


def load(fid: str, name: str):
    return json.loads((CACHE / fid / f"{name}.json").read_text())


def terrain(fid: str, lat4, lon4) -> tuple[dict, dict]:
    poly_lat, poly_lon = list(lat4) + [lat4[0]], list(lon4) + [lon4[0]]
    lat0 = math.radians(np.mean(lat4))
    a, e2 = 6378137.0, 0.00669437999014
    den = math.sqrt(1 - e2 * math.sin(lat0) ** 2)
    rm, rn = a * (1 - e2) / den**3, a / den
    x = (np.array(poly_lon) - np.mean(lon4)) * rn * math.cos(lat0) * math.pi / 180
    y = (np.array(poly_lat) - np.mean(lat4)) * rm * math.pi / 180
    area = 0.5 * abs(np.dot(x[:-1], y[1:]) - np.dot(x[1:], y[:-1]))
    elev = [float(load(fid, f"epqs_{k}")["value"]) for k in range(1, 5)]
    if not all(math.isfinite(e) and e >= -100 for e in elev):
        raise ValueError("USGS: invalid elevation")
    slope = max(0.8, mround((max(elev) - min(elev)) / max(1, math.sqrt(area)) * 100 * 1.8, 2))
    return {"area_m2": area}, {"elev": elev, "slope_pct": slope}


def power(fid: str) -> dict:
    p = load(fid, "power")["properties"]["parameter"]
    keys = [d.strftime("%Y%m%d") for d in _days(date(2016, 1, 1), date(2025, 12, 31))]
    if sorted(p["T2M"]) != keys:
        raise ValueError("POWER: incomplete dates")
    arr = {k: np.array([p[k][d] for d in keys], float) for k in p}
    t, tx, tn, pr, rad, gw = (arr[k] for k in ("T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "ALLSKY_SFC_SW_DWN", "GWETROOT"))
    allv = np.concatenate([t, tx, tn, pr, rad, gw])
    if (~np.isfinite(allv)).any() or ((t <= -90) | (tx <= -90) | (tn <= -90) | (tx < tn) | (pr < 0) | (rad < 0) | (gw < 0) | (gw > 1)).any():
        raise ValueError("POWER: missing/invalid values (-999 fill?)")
    yr = np.array([int(k[:4]) for k in keys])
    et0 = np.maximum(0, 0.0023 * (np.maximum(5.0, rad) * 0.408) * np.maximum(0, t + 17.8) * np.sqrt(np.maximum(0, tx - tn)))
    past = {"temp": [], "precip": [], "evap": [], "ndvi": [], "sm": []}
    for y in range(2016, 2026):
        m = yr == y
        past["temp"].append(mround(t[m].mean(), 2))
        past["precip"].append(mround(pr[m].sum(), 1))
        past["evap"].append(mround(et0[m].sum(), 1))
        g = gw[m & (gw > 0)].mean()
        w = min(1.25, past["precip"][-1] / max(400, past["evap"][-1]))
        past["ndvi"].append(mround(min(0.88, max(0.48, 0.42 + 0.32 * g + 0.14 * w)), 3))
        past["sm"].append(mround(g, 3))
    cur = {
        "temp": mround(np.mean(past["temp"]), 1),
        "precip": mround(np.mean(past["precip"]), 0),
        "evap": mround(np.mean(past["evap"]), 0),
        "ndvi": mround(np.mean(past["ndvi"]), 2),
        "sm": mround(np.mean(past["sm"]), 2),
    }
    return {"past": past, "current": cur}


def climate(fid: str, env: dict) -> dict:
    yrs = np.arange(2016, 2026)
    slope_t = min(0.08, max(0.015, np.polyfit(yrs, env["past"]["temp"], 1)[0]))
    slope_p = min(4.0, max(-6.0, np.polyfit(yrs, env["past"]["precip"], 1)[0]))
    slope_e = min(6.5, max(1.5, np.polyfit(yrs, env["past"]["evap"], 1)[0]))
    periods = load(fid, "nws_forecast")["properties"]["periods"]
    temps = [pp["temperature"] for pp in periods]
    if not temps or not all(pp["temperatureUnit"] == "F" for pp in periods) or not all(isinstance(v, (int, float)) for v in temps):
        raise ValueError("NWS: invalid periods")
    cur = env["current"]
    anom = min(1.2, max(-1.2, ((np.mean(temps) - 32) * 5 / 9 - cur["temp"]) * 0.08))
    d = load(fid, "openmeteo")["daily"]
    times = d["time"]
    exp = [x.isoformat() for x in _days(date(2026, 1, 1), date(2039, 12, 31))]
    tv = np.array([np.nan if v is None else v for v in d["temperature_2m_mean"]], float)
    pv = np.array([np.nan if v is None else v for v in d["precipitation_sum"]], float)
    ev = np.array([np.nan if v is None else v for v in d["et0_fao_evapotranspiration"]], float)
    et0_missing = bool(np.isnan(ev).all())
    if (
        len(times) != len(exp) or set(exp) - set(times) or len(tv) != len(times)
        or len(pv) != len(times) or len(ev) != len(times)
        or (~np.isfinite(np.concatenate([tv, pv]))).any()
        or (not et0_missing and (~np.isfinite(ev)).any())
        or (pv < 0).any() or (ev[np.isfinite(ev)] < 0).any()
    ):
        raise ValueError("Open-Meteo: incomplete or invalid")
    y = np.array([int(s[:4]) for s in times])
    st = {"temp": [], "precip": [], "evap": []}
    for yr in (2026, 2027, 2028):
        m = y == yr
        st["temp"].append(mround(0.6 * tv[m].mean() + 0.4 * (cur["temp"] + slope_t * (yr - 2023) + anom), 2))
        st["precip"].append(mround(0.6 * pv[m].sum() + 0.4 * (cur["precip"] + slope_p * (yr - 2023)), 1))
        tr_e = cur["evap"] + slope_e * (yr - 2023)
        st["evap"].append(mround(tr_e if et0_missing else 0.6 * np.nansum(ev[m]) + 0.4 * tr_e, 1))
    m20, m30 = (y >= 2026) & (y <= 2029), (y >= 2030) & (y <= 2039)
    ep = {
        "temp": [cur["temp"], mround(0.6 * tv[m20].mean() + 0.4 * (cur["temp"] + slope_t * 4.5 + anom), 1),
                 mround(0.6 * tv[m30].mean() + 0.4 * (cur["temp"] + slope_t * 12.0 + anom), 1)],
        "precip": [cur["precip"], mround(0.6 * pv[m20].sum() / 4 + 0.4 * (cur["precip"] + slope_p * 4.5)),
                   mround(0.6 * pv[m30].sum() / 10 + 0.4 * (cur["precip"] + slope_p * 12.0))],
    }
    if et0_missing:
        ep["evap"] = [cur["evap"], mround(cur["evap"] + slope_e * 4.5), mround(cur["evap"] + slope_e * 12.0)]
    else:
        ep["evap"] = [cur["evap"], mround(0.6 * np.nansum(ev[m20]) / 4 + 0.4 * (cur["evap"] + slope_e * 4.5)),
                      mround(0.6 * np.nansum(ev[m30]) / 10 + 0.4 * (cur["evap"] + slope_e * 12.0))]
    return {"shortTerm": st, "epochs": ep, "nwsAnomaly_C": mround(anom, 2), "et0ModelAvailable": not et0_missing,
            "openmeteo_et0_units": load(fid, "openmeteo")["daily_units"].get("et0_fao_evapotranspiration")}


DB = {
    "Corn": dict(kc=1.08, ky=1.25, y=200, pr=4.60, cost=680, cin=1.00, nfix=0),
    "Soy": dict(kc=0.86, ky=0.85, y=62, pr=11.5, cost=450, cin=1.08, nfix=65),
    "Wheat": dict(kc=0.75, ky=0.65, y=80, pr=6.20, cost=310, cin=1.22, nfix=15),
}
ROTS = [(("Corn", "Soy", "Wheat"), False, 1.11), (("Soy", "Wheat", "Corn"), True, 1.10),
        (("Wheat", "Corn", "Soy"), True, 1.10), (("Corn", "Soy", "Corn"), False, 1.08)]


def cards(geo: dict, dem: dict, env: dict, proj: dict) -> list[dict]:
    cur, st, ep = env["current"], proj["shortTerm"], proj["epochs"]
    runoff = 0.12 + 0.015 * dem["slope_pct"]
    p_eff = np.mean(st["precip"]) * (1 - runoff)
    et0 = np.mean(st["evap"])
    acres = geo["area_m2"] * 0.000247105
    out = []
    for seq, cover, bump in ROTS:
        kc = np.mean([DB[c]["kc"] for c in seq])
        ky = np.mean([DB[c]["ky"] for c in seq])
        nuniq = len(set(seq))
        akc = kc * (1 - (0.06 * cover + 0.05 * (nuniq - 1)))
        etm = akc * et0
        store = 160 * cur["sm"] * (1 + 0.08 * cover)
        deficit = max(0, 1 - min(etm, p_eff + store) / etm)
        heat = 0.035 * max(0, np.mean(st["temp"]) - cur["temp"]) * ky
        ym = max(0.45, (1 - ky * deficit - heat) * bump)
        rev = np.mean([DB[c]["y"] * DB[c]["pr"] for c in seq])
        nfix = np.mean([DB[c]["nfix"] for c in seq])
        cost = np.mean([DB[c]["cost"] for c in seq]) + cover * 35 - nfix * 0.85
        profit = max(40, rev * ym - cost)
        scores = []
        for i in range(3):
            e_def = max(0, 1 - min(1, (ep["precip"][i] * (1 - runoff) + store) / (akc * ep["evap"][i])))
            e_heat = max(0, ep["temp"][i] - cur["temp"]) * 0.04 * ky
            scores.append(mround(100 * max(0.35, (1 - ky * e_def - e_heat) * bump), 1))
        out.append({"rotation": "-".join(seq), "ETm_mm": mround(etm, 1), "deficitPct": mround(deficit * 100, 1),
                    "netProfit_ac": mround(profit, 1), "profit_usd": mround(acres * profit),
                    "waterIdx": mround(etm / (1.08 * et0) * 100, 1), "epochScores": scores})
    return out


def run_field(row: dict) -> dict:
    fid = row["field_id"].strip()
    lat4 = [float(row[f"v{k}_lat"]) for k in range(1, 5)]
    lon4 = [float(row[f"v{k}_lon"]) for k in range(1, 5)]
    geo, dem = terrain(fid, lat4, lon4)
    env = power(fid)
    proj = climate(fid, env)
    cs = cards(geo, dem, env, proj)
    vals = [v for c in cs for v in [c["ETm_mm"], c["deficitPct"], c["netProfit_ac"], c["profit_usd"], *c["epochScores"]]]
    if not all(math.isfinite(v) for v in vals):
        raise ValueError("cards: nonfinite output")
    return {"field_id": fid, "geo": geo, "dem": dem, "env_current": env["current"], "proj": proj, "cards": cs}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    with open(INPUTS / "fields_20.csv", newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    ok = 0
    for i, row in enumerate(rows if args.all else rows[:1], 1):
        try:
            res = run_field(row)
            ok += 1
            if i == 1:
                print(json.dumps(res, indent=1, default=float))
            print(f"[{i}] {res['field_id']} PASS et0ModelAvailable={res['proj']['et0ModelAvailable']}")
        except (ValueError, KeyError, FileNotFoundError) as exc:
            print(f"[{i}] {row['field_id']} FAIL {type(exc).__name__}: {exc}")
    print(f"pre-run check: {ok}/{len(rows) if args.all else 1} fields pass")


if __name__ == "__main__":
    main()
