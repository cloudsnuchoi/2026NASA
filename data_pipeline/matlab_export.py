"""Export immutable, read-only DB/API snapshots for the L2 MATLAB lane."""

from __future__ import annotations

import csv
import io
import hashlib
import math
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
from urllib.request import Request, urlopen

ROOT = Path("/srv/hackathon/data/processed/v1/matlab")
API = os.environ.get("MODEL_API_BASE", "http://127.0.0.1:8090")


def api(path, payload=None):
    request = Request(
        API + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=180) as response:
        return json.load(response)


def sql_csv(query):
    env = dict(os.environ)
    env.update(
        PGHOST=env.get("PGHOST", "127.0.0.1"),
        PGPORT=env.get("PGPORT", "5433"),
        PGUSER=env.get("PGUSER", "hk"),
        PGDATABASE=env.get("PGDATABASE", "fieldshift"),
    )
    return subprocess.check_output(
        ["psql", "-X", "-v", "ON_ERROR_STOP=1", "-c", f"COPY ({query}) TO STDOUT WITH CSV HEADER"], env=env, text=True
    )


def write_csv(path, rows, columns):
    with path.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    path.chmod(0o644)


def main():
    inputs = ROOT / "inputs"
    inputs.mkdir(exist_ok=True)
    inputs.chmod(0o755)
    for name in ("woochan", "yoonsung", "jimin", "jieun"):
        folder = ROOT / "outputs" / name
        folder.mkdir(parents=True, exist_ok=True)
        if folder.stat().st_mode & 0o777 != 0o777:
            folder.chmod(0o777)
    demo = api("/fields")["fields"]
    ids = [f["field_id"] for f in demo]
    if len(ids) != 20 or not all(x.isdigit() for x in ids):
        raise ValueError("Expected exactly 20 numeric CSB IDs")
    selected = ",".join("'" + x + "'" for x in ids)
    vertices = ", ".join(f"ST_Y(ST_PointN(r,{i})) AS v{i}_lat, ST_X(ST_PointN(r,{i})) AS v{i}_lon" for i in range(1, 5))
    query = f"""SELECT field_id, county_fips, county_label, lat, lon, {vertices} FROM
        (SELECT f.field_id, f.county_fips, c.name AS county_label, ST_Y(f.centroid) AS lat,
        ST_X(f.centroid) AS lon, ST_ExteriorRing(ST_Transform(ST_OrientedEnvelope(ST_Transform(f.geom,5070)),4326)) AS r
        FROM fields f JOIN county c USING(county_fips) WHERE field_id IN ({selected})) q ORDER BY field_id"""
    for filename, query in [
        ("fields_20.csv", query),
        (
            "ndvi_hls_20fields.csv",
            f"SELECT field_id,date,product,ndvi,valid_frac FROM field_ndvi_hls WHERE field_id IN ({selected}) ORDER BY field_id,date,product",
        ),
    ]:
        with (inputs / filename).open("x") as stream:
            stream.write(sql_csv(query))
        (inputs / filename).chmod(0o644)
    deficits, quantiles, provenance = [], [], []
    for fid in ids:
        backtest = api(f"/validation/backtest?field_id={fid}&year=2012")
        for result in backtest["results"]:
            deficits.append(
                dict(
                    field_id=fid,
                    strategy_code=result["strategy_code"],
                    **{key: result["metrics"].get(key) for key in ("season_water_deficit_mm", "stress_days", "winter_bare_days")},
                )
            )
        compare = api("/strategies/compare", {"field_id": fid, "n": 500, "seed": 42})
        provenance.append({"field_id": fid, "run_id": compare["run_id"], "period": compare["period"]})
        for card in compare["strategies"]:
            quantiles.append(
                dict(
                    field_id=fid,
                    strategy_code=card["strategy_code"],
                    metric="composite_index",
                    **{q: card[q] for q in ("p10", "p50", "p90")},
                    unit=compare["unit"],
                )
            )
            for metric in ("vegetation_pct", "water_use_pct", "revenue_pct"):
                quantiles.append(
                    dict(
                        field_id=fid,
                        strategy_code=card["strategy_code"],
                        metric=metric,
                        **card["display"][metric],
                        unit="percent_relative_to_A",
                    )
                )
    write_csv(
        inputs / "engine_2012_deficit.csv",
        deficits,
        ["field_id", "strategy_code", "season_water_deficit_mm", "stress_days", "winter_bare_days"],
    )
    write_csv(
        inputs / "engine_p10p90_20fields.csv", quantiles, ["field_id", "strategy_code", "metric", "p10", "p50", "p90", "unit"]
    )
    target = inputs / "drought_2012_county.csv"
    if target.exists():
        raise FileExistsError(target)
    shutil.copyfile(ROOT / target.name, target)
    target.chmod(0o644)
    (inputs / "engine_provenance.json").write_text(json.dumps(provenance, indent=2))
    print(f"Exported {len(ids)} fields, {len(deficits)} backtests, {len(quantiles)} quantiles")


def yearly_p90(fields):
    """Real API scored-year deficits; no synthetic proxy or inferred P90 years."""
    import numpy as np

    rows = []
    for f in fields:
        block = []
        for year in range(1998, 2026):
            result = api(f"/validation/backtest?field_id={f['field_id']}&year={year}")
            a = next(r for r in result["results"] if r["strategy_code"] == "A")
            metric = a["metrics"]
            value = metric["season_water_deficit_mm"]
            if value is None or not math.isfinite(value):
                raise ValueError("Missing engine annual deficit")
            block.append(
                dict(
                    field_id=f["field_id"],
                    county_fips=f["county_fips"],
                    year=year,
                    is_p90=0,
                    season="engine_scored_year",
                    season_water_deficit_mm=value,
                    p90_threshold_mm=None,
                    status="API strategy A scored-year deficit; 3 spinup years; >= linear P90 (ties included)",
                    modelled_crop=metric["modelled_crop"],
                    window=metric["window"],
                )
            )
        threshold = float(np.quantile([r["season_water_deficit_mm"] for r in block], 0.9))
        for r in block:
            r["p90_threshold_mm"] = threshold
            r["is_p90"] = int(r["season_water_deficit_mm"] >= threshold)
        rows.extend(block)
    return rows


def extra_sets(root=ROOT):
    """MAT2 immutable extra snapshots; no DB writes or existing-file overwrites."""
    import numpy as np
    from model_api.hydro import et0_fao56

    inputs = root / "inputs"
    fields = list(csv.DictReader((inputs / "fields_20.csv").open()))
    counties = sorted({"19169", "17113", "31109", "39159"} | {r["county_fips"] for r in fields})
    selected = ",".join("'" + c + "'" for c in counties)
    names = [
        "county_nldas_2012.csv",
        "season_climate_1995_2025.csv",
        "engine_p90_years.csv",
        "geos_s2s_next_season.csv",
        "historical_31yr_distribution.csv",
        "engine_strategyB_assumptions.csv",
        "mat2_provenance.json",
    ]
    for name in names:
        if (inputs / name).exists():
            raise FileExistsError(inputs / name)

    def query(q):
        return list(csv.DictReader(io.StringIO(sql_csv(q))))

    def number(v):
        return float(v) if v not in ("", None) else float("nan")

    def emit(name, rows):
        cleaned = [
            {k: (None if isinstance(v, (float, np.floating)) and not math.isfinite(v) else v) for k, v in r.items()} for r in rows
        ]
        write_csv(inputs / name, cleaned, list(rows[0]))

    nldas = query(
        f"SELECT county_fips,month,rootmoist_kg_m2 FROM county_nldas_monthly WHERE county_fips IN ({selected}) AND month BETWEEN '1995-01-01' AND '2025-12-31' ORDER BY 1,2"
    )
    for c in counties:
        block = [r for r in nldas if r["county_fips"] == c]
        seasonal = {}
        for y in range(1995, 2026):
            vals = [number(r["rootmoist_kg_m2"]) for r in block if int(r["month"][:4]) == y and 5 <= int(r["month"][5:7]) <= 9]
            seasonal[y] = float(np.mean(vals)) if len(vals) == 5 else float("nan")
        baseline = np.mean([seasonal[y] for y in range(1995, 2025) if y != 2012])
        for r in block:
            r.update(
                mjjas_2012_rootmoist_kg_m2=seasonal[2012],
                baseline_mjjas_rootmoist_kg_m2=float(baseline),
                anomaly_2012_kg_m2=float(seasonal[2012] - baseline),
            )

    climate, historical, weather_counts = [], [], {}
    for c in counties:
        rows = query(
            f"SELECT date,t2m_c,tmin_c,tmax_c,precip_mm,rh2m_pct,ws2m_ms,srad_mj_m2 FROM county_weather_daily WHERE county_fips='{c}' AND source_id='power' AND date BETWEEN '1995-01-01' AND '2025-12-31' ORDER BY date"
        )
        lat = float(query(f"SELECT ST_Y(centroid) AS lat FROM county WHERE county_fips='{c}'")[0]["lat"])
        weather_counts[c] = len(rows)
        for y in range(1995, 2026):
            block = [r for r in rows if int(r["date"][:4]) == y and r["date"][5:] != "02-29"]
            if len(block) != 365:
                raise ValueError(f"Incomplete POWER year: {c}/{y}")
            a = {k: np.array([number(r[k]) for r in block]) for k in block[0] if k != "date"}
            # Match engine FAO-56 with the engine API elevation assumption (300 m default).
            # No imputation here: missing meteorology remains an information gap.
            et = et0_fao56(a["t2m_c"], a["tmax_c"], a["tmin_c"], a["rh2m_pct"], a["ws2m_ms"], a["srad_mj_m2"], lat, 300.0)
            months = np.array([int(r["date"][5:7]) for r in block])
            mask = (months >= 5) & (months <= 9)
            climate.append(
                dict(county_fips=c, year=y, precip_mm=float(np.sum(a["precip_mm"][mask])), ET0_mm=float(np.sum(et[mask])))
            )
            for season, ms in [("MAM", [3, 4, 5]), ("JJ", [6, 7])]:
                # GEOS table stores unweighted mean of monthly means, so match it exactly.
                for var, key, unit in [("pr", "precip_mm", "mm/day"), ("tas", "t2m_c", "degC")]:
                    value = float(np.mean([np.mean(a[key][months == m]) for m in ms]))
                    historical.append(
                        dict(
                            county_fips=c,
                            season=season,
                            period=f"{y}-" + ("03/05" if season == "MAM" else "06/07"),
                            year=y,
                            variable=var,
                            value=value,
                            baseline_value=None,
                            anomaly=None,
                            unit=unit,
                        )
                    )
        for metric in ["precip_mm", "ET0_mm"]:
            baseline = np.mean([r[metric] for r in climate if r["county_fips"] == c and r["year"] <= 2024 and r["year"] != 2012])
            for r in climate:
                if r["county_fips"] == c:
                    r["precip_anomaly_mm" if metric == "precip_mm" else "ET0_anomaly_mm"] = float(r[metric] - baseline)
    baselines = {}
    for c in counties:
        for season in ["MAM", "JJ"]:
            for var in ["pr", "tas"]:
                block = [r for r in historical if r["county_fips"] == c and r["season"] == season and r["variable"] == var]
                base = float(np.mean([r["value"] for r in block]))
                baselines[c, season, var] = base
                for r in block:
                    r["baseline_value"], r["anomaly"] = base, r["value"] - base
    geos = query(
        f"SELECT county_fips,season,year,member,variable,value,unit FROM county_scenario_year WHERE county_fips IN ({selected}) AND source_id='geos_s2s' AND variable IN ('pr','tas') ORDER BY 1,2,4,5"
    )
    forecast = []
    for r in geos:
        if r["season"] not in ("MAM", "JJ"):
            raise ValueError("Unsupported GEOS season")
        b = baselines[r["county_fips"], r["season"], r["variable"]]
        forecast.append(
            dict(
                county_fips=r["county_fips"],
                season=r["season"],
                period=r["year"] + ("-03/05" if r["season"] == "MAM" else "-06/07"),
                member=r["member"],
                variable=r["variable"],
                value=number(r["value"]),
                baseline_value=b,
                anomaly=number(r["value"]) - b,
                unit=r["unit"],
            )
        )
    for c in counties:
        for season in ["MAM", "JJ"]:
            for var in ["pr", "tas"]:
                assert (
                    len({r["member"] for r in forecast if (r["county_fips"], r["season"], r["variable"]) == (c, season, var)})
                    == 10
                )
    p90 = yearly_p90(fields)
    assumptions = []
    raw_assumptions = {}
    for f in fields:
        fid = f["field_id"]
        result = api("/strategies/compare", {"field_id": fid, "n": 100, "seed": 42})
        raw_assumptions[fid] = result["assumptions"]
        items = {a["item"]: a for a in result["assumptions"]}
        assert items["elevation_m"]["value"] == 300.0, "Engine elevation assumption changed"
        for item in ["crop_calendar", "rye_residue_cover_frac", "baseline_rotation", "elevation_m", "weather"]:
            a = items[item]
            assumptions.append(
                dict(field_id=fid, item=item, value=a["value"], unit=a["unit"], source=a["source"], run_id=result["run_id"])
            )
        calendar = items["crop_calendar"]["source"]
        assert "corn plant May 1 / harvest Sep 28" in calendar and "soybean May 10 / Sep 22" in calendar
        assert "planted 7 days after harvest, terminated 10 days" in calendar
        for item, value in dict(
            corn_plant_doy=121,
            corn_harvest_doy=271,
            soy_plant_doy=130,
            soy_harvest_doy=265,
            rye_plant_after_harvest_days=7,
            rye_terminate_before_plant_days=10,
        ).items():
            assumptions.append(
                dict(
                    field_id=fid,
                    item=item,
                    value=value,
                    unit="day (365-day engine calendar)",
                    source="Parsed/converted from API crop_calendar assumption: " + calendar,
                    run_id=result["run_id"],
                )
            )
    for name, data in zip(names, [nldas, climate, p90, forecast, historical, assumptions]):
        emit(name, data)
    provenance = dict(
        created_utc=datetime.now(timezone.utc).isoformat(),
        weather_rows=weather_counts,
        nldas_unit="rootmoist_kg_m2: kg/m2 (mm water), monthly mean; MJJAS mean of 5 monthly means",
        anomaly_baseline="season_climate/NLDAS: 1995-2011 + 2013-2024 (29 seasons); GEOS/history: 1995-2025 (31 seasons)",
        et0="model_api.hydro.et0_fao56; FAO-56 Penman-Monteith daily; missing radiation Hargreaves; county centroid latitude, API default elevation 300m; no meteorology imputation; Feb29 dropped as engine",
        season="GEOS MAM March-May2027 and JJ June-July2027, not full next growing season; equal weight monthly means, pr mm/day, tas degC; anomalies vs POWER, NOT model hindcast bias correction",
        coverage="Local POWER 1995-2025 only; 1988 not exported/not observable here. HLS 2012 unavailable.",
        p90="GET /validation/backtest for each field/year1998-2025, strategy A scored-year season_water_deficit_mm, 3 spinup years. Per-field linear P90 threshold, >= includes ties. Annual engine deficit, NOT May-Sep-only. 1995-1997 unavailable; pre-CDL crops may be inferred by engine. Plot union of field P90 years per county.",
        engine_assumptions=raw_assumptions,
        files={name: hashlib.sha256((inputs / name).read_bytes()).hexdigest() for name in names[:-1]},
    )
    with (inputs / names[-1]).open("x") as stream:
        json.dump(provenance, stream, indent=2)
    print("MAT2 exports:", {name: sum(1 for _ in (inputs / name).open()) - 1 for name in names[:-1]})


if __name__ == "__main__":
    import sys

    if "--extra" in sys.argv:
        extra_sets()
    else:
        main()
