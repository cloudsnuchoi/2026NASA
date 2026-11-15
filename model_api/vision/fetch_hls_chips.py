"""Fetch 3-date HLS v2.0 (L30/S30) 6-band 224x224 chips around each demo field centroid for Prithvi crop inference.

Offline batch only (not on the request path). Bands per Prithvi config: Blue, Green, Red, Narrow NIR, SWIR1, SWIR2
  L30: B02 B03 B04 B05 B06 B07 | S30: B02 B03 B04 B8A B11 B12  (scaled reflectance DN, x1e-4; fill -9999)
Windows: W1 Apr15-May31, W2 Jun1-Jul31, W3 Aug1-Sep30. Per field and window the granule with the lowest
chip invalid fraction (Fmask cloud/adjacent/shadow/snow bits 1-4, or fill) is chosen.
Requests are sequential with a sleep between file reads (<= ~2 req/s per host).
Output: {OUT}/chips/{field_id}_{year}.npz with stack (224,224,18) int16, valid (3,224,224), dates, sensors, crs, transform.
Usage: python -m model_api.vision.fetch_hls_chips YEAR
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time

import earthaccess
import geopandas as gpd
import numpy as np
import psycopg
import rasterio
from pyproj import Transformer
from rasterio.windows import Window

os.environ.update(
    GDAL_HTTP_NETRC="YES",
    GDAL_HTTP_NETRC_FILE=os.path.expanduser("~/.netrc"),
    GDAL_HTTP_COOKIEFILE="/srv/hackathon/data/cache/gdal_cookies",
    GDAL_HTTP_COOKIEJAR="/srv/hackathon/data/cache/gdal_cookies",
    GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
    CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
    GDAL_HTTP_MAX_RETRY="3",
    GDAL_HTTP_RETRY_DELAY="2",
)
OUT = os.environ.get("PRITHVI_DATA", "/srv/hackathon/data/raw/hls_prithvi")
CHIP = 224
BANDS = {"HLSL30": ["B02", "B03", "B04", "B05", "B06", "B07"], "HLSS30": ["B02", "B03", "B04", "B8A", "B11", "B12"]}
SLEEP = 0.6


def windows(year):
    return [
        ("W1", f"{year}-04-15", f"{year}-05-31"),
        ("W2", f"{year}-06-01", f"{year}-07-31"),
        ("W3", f"{year}-08-01", f"{year}-09-30"),
    ]


def granule_date(g):
    return dt.datetime.strptime(g["umm"]["GranuleUR"].split(".")[3][:7], "%Y%j").date().isoformat()


def cloud(g):
    u = g["umm"]
    if "CloudCover" in u:
        return float(u["CloudCover"])
    for a in u.get("AdditionalAttributes", []):
        if a.get("Name") == "CLOUD_COVERAGE":
            return float(a["Values"][0])
    return 100.0


def read(url, win, tries=4):
    for i in range(tries):
        time.sleep(SLEEP * (1 + 3 * i))
        try:
            with rasterio.open(url) as s:
                return s.read(1, window=win, boundless=True, fill_value=-9999 if s.dtypes[0] == "int16" else 255), s
        except rasterio.errors.RasterioIOError as e:
            print("retry", i, url.rsplit("/", 1)[-1], repr(e)[:80], flush=True)
    raise RuntimeError(f"read failed: {url}")


def chip_window(src, x, y):
    r, c = src.index(x, y)
    return Window(c - CHIP // 2, r - CHIP // 2, CHIP, CHIP)


def main(year: int):
    earthaccess.login(strategy="netrc")
    with psycopg.connect("") as c:
        ids = [r[0] for r in c.execute("select distinct field_id from field_ndvi_hls order by 1")]
        f = gpd.GeoDataFrame.from_postgis(
            "select field_id, county_fips, geom, st_x(centroid) lon, st_y(centroid) lat from fields where field_id = any(%s)",
            c,
            params=(ids,),
            geom_col="geom",
            crs=4326,
        )
    os.makedirs(f"{OUT}/chips", exist_ok=True)
    log = {}
    for fid, lon, lat in zip(f.field_id, f.lon, f.lat):
        path = f"{OUT}/chips/{fid}_{year}.npz"
        if os.path.exists(path):
            print("skip", fid, flush=True)
            continue
        t0 = time.time()
        stack, valid, dates, sensors = [], [], [], []
        ref_crs = ref_tr = None
        for wname, d0, d1 in windows(year):
            cands = []
            for sn in BANDS:
                gs = earthaccess.search_data(
                    short_name=sn, point=(lon, lat), temporal=(d0, d1), cloud_cover=(0, 60), version="2.0"
                )
                cands += [(sn, g) for g in gs]
            cands.sort(key=lambda a: cloud(a[1]))
            best = None
            for sn, g in cands:
                links = [u for u in g.data_links() if u.endswith(".tif")]
                fm = [u for u in links if u.endswith("Fmask.tif")]
                if not fm:
                    continue
                time.sleep(SLEEP)
                with rasterio.open(fm[0]) as s:
                    x, y = Transformer.from_crs(4326, s.crs, always_xy=True).transform(lon, lat)
                    w = chip_window(s, x, y)
                    if w.col_off < 0 or w.row_off < 0 or w.col_off + CHIP > s.width or w.row_off + CHIP > s.height:
                        continue
                    crs, tr = s.crs, s.window_transform(w)
                m, _ = read(fm[0], w)
                bad = ((m & 0b11110) != 0) | (m == 255)
                frac = float(bad.mean())
                if ref_crs is not None and crs != ref_crs:
                    continue  # keep one UTM grid for all 3 dates
                if best is None or frac < best[0]:
                    best = (frac, sn, g, links, w, crs, tr, bad)
                if frac < 0.02:
                    break
            if best is None:
                raise RuntimeError(f"{fid} {wname}: no usable granule")
            frac, sn, g, links, w, crs, tr, bad = best
            ref_crs, ref_tr = crs, tr
            arr = []
            for b in BANDS[sn]:
                u = [x for x in links if x.endswith(f".{b}.tif")][0]
                a, _ = read(u, w)
                arr.append(a)
            arr = np.stack(arr, -1).astype(np.int16)
            ok = ~bad & (arr > -9999).all(-1)
            stack.append(arr)
            valid.append(ok)
            dates.append(granule_date(g))
            sensors.append(sn)
            print(fid, wname, sn, dates[-1], "invalid", round(1 - ok.mean(), 3), flush=True)
        np.savez_compressed(
            path,
            stack=np.concatenate(stack, -1),
            valid=np.stack(valid),
            dates=np.array(dates),
            sensors=np.array(sensors),
            crs=str(ref_crs),
            transform=np.array(ref_tr)[:6],
        )
        log[fid] = {"dates": dates, "sensors": sensors, "sec": round(time.time() - t0, 1)}
        print(fid, "done", log[fid], flush=True)
    with open(f"{OUT}/chips/fetch_log_{year}.json", "a") as fh:
        fh.write(json.dumps(log) + "\n")


if __name__ == "__main__":
    main(int(sys.argv[1]))
