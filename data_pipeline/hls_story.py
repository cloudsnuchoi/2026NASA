"""HLS v2.0 (HLSL30 + HLSS30) NDVI per field (12 demo fields, Story County), Apr-Nov. COG windows read over HTTPS (Earthdata netrc); no files stored.
NDVI=(NIR-Red)/(NIR+Red); L30 red=B04 nir=B05; S30 red=B04 nir=B8A. Fmask: pixel valid if cloud(bit1), adjacent(bit2), shadow(bit3), snow/ice(bit4), water(bit5) all 0.
Reflectance scale 0.0001, fill -9999. Mean over valid pixels inside the field polygon. Usage: hls_story.py YEAR"""

import sys
import os
import earthaccess
import rasterio
import psycopg
import geopandas as gpd
import time
from rasterio.windows import from_bounds
from rasterio.features import geometry_mask
from concurrent.futures import ThreadPoolExecutor

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
earthaccess.login(strategy="netrc")
year = int(sys.argv[1])
with psycopg.connect("") as c:
    ids = [r[0] for r in c.execute("select distinct field_id from field_et_openet order by 1")]
    f = gpd.GeoDataFrame.from_postgis(
        "select field_id,geom from fields where field_id=any(%s)", c, params=(ids,), geom_col="geom", crs=4326
    )
bb = tuple(f.total_bounds)
grs = []
for sn in ["HLSL30", "HLSS30"]:
    r = earthaccess.search_data(short_name=sn, bounding_box=bb, temporal=(f"{year}-04-01", f"{year}-11-30"), cloud_cover=(0, 70))
    grs += [(sn, g) for g in r]
print(len(grs), "granules", flush=True)


def one(a):
    sn, g = a
    ln = [u for u in g.data_links() if u.endswith(".tif")]
    nir = "B05" if sn == "HLSL30" else "B8A"
    d = {k: [u for u in ln if u.endswith(k + ".tif")] for k in ["B04", nir, "Fmask"]}
    if not all(d.values()):
        return []
    date = g["umm"]["GranuleUR"].split(".")[3][:7]
    date = __import__("datetime").datetime.strptime(date, "%Y%j").date().isoformat()
    out = []
    try:
        with rasterio.open(d["B04"][0]) as sr, rasterio.open(d[nir][0]) as sn_, rasterio.open(d["Fmask"][0]) as sf:
            ff = f.to_crs(sr.crs)
            for r in ff.itertuples():
                geom = r.geom
                x0, y0, x1, y1 = geom.bounds
                lft, b, rr, t = sr.bounds
                if x0 < lft or x1 > rr or y0 < b or y1 > t:
                    continue
                w = from_bounds(x0, y0, x1, y1, sr.transform).round_offsets().round_lengths()
                if w.width < 1 or w.height < 1:
                    continue
                red = sr.read(1, window=w).astype("float64")
                n = sn_.read(1, window=w).astype("float64")
                fm = sf.read(1, window=w)
                tr = sr.window_transform(w)
                inside = ~geometry_mask([geom], out_shape=red.shape, transform=tr)
                npx = inside.sum()
                if npx == 0:
                    continue
                bad = (fm & 0b111110) != 0
                ok = inside & ~bad & (red > -9999) & (n > -9999)
                vf = ok.sum() / npx
                if ok.sum() == 0:
                    out.append((r.field_id, date, sn, None, 0.0))
                    continue
                rd = red[ok] * 1e-4
                nr = n[ok] * 1e-4
                nd = ((nr - rd) / (nr + rd + 1e-9)).mean()
                out.append((r.field_id, date, sn, float(nd), float(vf)))
    except Exception as e:
        print("ERR", g["umm"]["GranuleUR"], repr(e)[:100], flush=True)
    return out


rows = []
t0 = time.time()
with ThreadPoolExecutor(6) as ex:
    for i, o in enumerate(ex.map(one, grs)):
        rows += o
        if i % 50 == 0:
            print(i, len(rows), round(time.time() - t0), "s", flush=True)
with psycopg.connect("") as c:
    c.execute("delete from field_ndvi_hls where date between %s and %s", (f"{year}-01-01", f"{year}-12-31"))
    c.cursor().executemany("insert into field_ndvi_hls values (%s,%s,%s,%s,%s) on conflict do nothing", rows)
print("rows", len(rows))
