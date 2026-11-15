"""GPM IMERG Final daily (GPM_3IMERGDF v07, 0.1 deg) county mean precipitation, tier 1 (12 Corn Belt states).
Usage: imerg_tier1.py START END   (YYYY-MM-DD). Needs ~/.netrc Earthdata login (GES DISC app approved).
Cells whose centre falls inside the county are averaged; counties with none use the nearest cell (SOT 2 context-cell rule).
Granule (31 MB/day) downloaded in threads (<=8), reduced serially (NetCDF/HDF5 is not thread-safe -> segfault), then deleted.
Reduced county series saved as parquet under raw/imerg/tier1_county/ and loaded into county_imerg_daily (idempotent per range)."""

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

RAW = "/srv/hackathon/data/raw/imerg/tier1_county"
TMP = RAW + "/tmp"
os.makedirs(TMP, exist_ok=True)
STATES = ["19", "17", "18", "39", "31", "27", "46", "55", "29", "20", "26", "21"]
earthaccess.login(strategy="netrc")
start, end = sys.argv[1], sys.argv[2]
cs = gpd.read_file("zip:///srv/hackathon/data/raw/census/cb/c.zip")
cs = cs[cs.STATEFP.isin(STATES)].to_crs(4326)
res = earthaccess.search_data(short_name="GPM_3IMERGDF", temporal=(start, end))
print(len(res), "granules", flush=True)


def dl(g):
    for a in range(4):
        try:
            time.sleep(0.5)  # <=2 req/s overall with 8 workers is enforced by granule time (~5 s each)
            return earthaccess.download([g], TMP)[0]
        except Exception:
            time.sleep(5 * (a + 1))
    return None


mapping = None
out = []
with ThreadPoolExecutor(6) as ex:
    for n, f in enumerate(ex.map(dl, res)):
        if f is None:
            print("FAILED granule", n, flush=True)
            continue
        ds = xr.open_dataset(f)
        p = ds["precipitation"].isel(time=0).sel(lon=slice(-105, -79), lat=slice(35, 50)).transpose("lat", "lon")
        date = str(ds.time.values[0])[:10]
        v = p.values.astype("float32")
        lat = p.lat.values
        lon = p.lon.values
        ds.close()
        os.remove(f)
        if mapping is None:
            LON, LAT = np.meshgrid(lon, lat)
            pts = gpd.GeoDataFrame({"i": np.arange(LON.size)}, geometry=gpd.points_from_xy(LON.ravel(), LAT.ravel()), crs=4326)
            j = gpd.sjoin(pts, cs[["GEOID", "geometry"]], predicate="within")[["i", "GEOID"]]
            miss = cs[~cs.GEOID.isin(set(j.GEOID))]
            extra = []
            for r_ in miss.itertuples():
                c = r_.geometry.representative_point()
                k = int(np.argmin((LON.ravel() - c.x) ** 2 + (LAT.ravel() - c.y) ** 2))
                extra.append((k, r_.GEOID))
            mapping = pd.concat([j, pd.DataFrame(extra, columns=["i", "GEOID"])]).astype({"i": "int64"})
            print("mapped", len(mapping), len(miss), "nearest-cell counties", flush=True)
        flat = v.ravel()[mapping.i.values]
        flat = np.where(flat < 0, np.nan, flat)  # fill value -9999.9 -> NULL
        s = pd.Series(flat).groupby(mapping.GEOID.values).mean()
        out += [(k, date, None if np.isnan(x) else float(x), "GPM_3IMERGDF.07") for k, x in s.items()]
        if n % 100 == 0:
            print(n, date, flush=True)
pd.DataFrame(out, columns=["county_fips", "date", "precip_mm", "product"]).to_parquet(f"{RAW}/county_daily_{start}_{end}.parquet")
with psycopg.connect("") as c:
    c.execute("delete from county_imerg_daily where date between %s and %s", (start, end))
    with c.cursor() as cur, cur.copy("copy county_imerg_daily(county_fips,date,precip_mm,product) from stdin") as cp:
        for o in out:
            cp.write_row(o)
print("rows", len(out))
