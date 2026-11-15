"""NLDAS-2 Noah monthly (NLDAS_NOAH0125_M v2.0, 0.125 deg) county means for tier 1 (12 Corn Belt states).
Usage: nldas2_tier1.py START_YYYY-MM END_YYYY-MM. Raw monthly files (~10 MB) kept under raw/nldas2/.
County value = mean of cells whose centre is inside the county; counties with none use the nearest cell. NaN cells (water/ocean) ignored.
Variable names/units are read from the files (see sql/003_nldas_monthly.sql)."""

import sys
import os
import time
import numpy as np
import pandas as pd
import xarray as xr
import geopandas as gpd
import psycopg
import earthaccess
from concurrent.futures import ThreadPoolExecutor

RAW = "/srv/hackathon/data/raw/nldas2"
os.makedirs(RAW, exist_ok=True)
STATES = ["19", "17", "18", "39", "31", "27", "46", "55", "29", "20", "26", "21"]
VARS = {
    "RootMoist": "rootmoist_kg_m2",
    "SoilM_0_10cm": "soilm_0_10_kg_m2",
    "SoilM_10_40cm": "soilm_10_40_kg_m2",
    "SoilM_40_100cm": "soilm_40_100_kg_m2",
    "SoilM_100_200cm": "soilm_100_200_kg_m2",
    "Evap": "evap_kg_m2",
    "PotEvap": "potevap_w_m2",
    "TVeg": "tveg_w_m2",
    "ESoil": "esoil_w_m2",
    "ECanop": "ecanop_w_m2",
    "Rainf": "rainf_kg_m2",
}
earthaccess.login(strategy="netrc")
s, e = sys.argv[1], sys.argv[2]
cs = gpd.read_file("zip:///srv/hackathon/data/raw/census/cb/c.zip")
cs = cs[cs.STATEFP.isin(STATES)].to_crs(4326)
res = earthaccess.search_data(short_name="NLDAS_NOAH0125_M", temporal=(s + "-01", e + "-28"))
print(len(res), "granules", flush=True)


def dl(g):
    for a in range(4):
        try:
            time.sleep(0.5)
            return earthaccess.download([g], RAW)[0]
        except Exception:
            time.sleep(5 * (a + 1))


mapping = None
rows = []
with ThreadPoolExecutor(4) as ex:
    for f in ex.map(dl, res):
        if f is None:
            print("FAILED", flush=True)
            continue
        ds = xr.open_dataset(f)
        sub = ds.sel(lon=slice(-105, -79), lat=slice(35, 50))
        month = str(ds.time.values[0])[:7] + "-01"
        if mapping is None:
            LON, LAT = np.meshgrid(sub.lon.values, sub.lat.values)
            pts = gpd.GeoDataFrame({"i": np.arange(LON.size)}, geometry=gpd.points_from_xy(LON.ravel(), LAT.ravel()), crs=4326)
            j = gpd.sjoin(pts, cs[["GEOID", "geometry"]], predicate="within")[["i", "GEOID"]]
            miss = cs[~cs.GEOID.isin(set(j.GEOID))]
            ex_ = []
            for r in miss.itertuples():
                c = r.geometry.representative_point()
                ex_.append((int(np.argmin((LON.ravel() - c.x) ** 2 + (LAT.ravel() - c.y) ** 2)), r.GEOID))
            mapping = pd.concat([j, pd.DataFrame(ex_, columns=["i", "GEOID"])])
            print("mapped", len(mapping), len(miss), "nearest-cell", flush=True)
        d = pd.DataFrame({VARS[k]: sub[k].isel(time=0).transpose("lat", "lon").values.ravel()[mapping.i.values] for k in VARS})
        d["county_fips"] = mapping.GEOID.values
        g = d.groupby("county_fips").mean(numeric_only=True).reset_index()
        g["month"] = month
        rows.append(g)
        ds.close()
df = pd.concat(rows)
cols = ["county_fips", "month"] + list(VARS.values())
df = df[cols].astype(object).where(df[cols].notna(), None)
df.to_parquet(f"{RAW}/county_monthly_{s}_{e}.parquet") if False else pd.concat(rows)[cols].to_parquet(
    f"{RAW}/county_monthly_{s}_{e}.parquet"
)
with psycopg.connect("") as c:
    c.execute("delete from county_nldas_monthly where month between %s and %s", (s + "-01", e + "-28"))
    with c.cursor() as cur, cur.copy(f"copy county_nldas_monthly({','.join(cols)}) from stdin") as cp:
        for r in df.itertuples(index=False):
            cp.write_row(r)
print("rows", len(df))
