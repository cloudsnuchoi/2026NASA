"""Load the contrast demo fields listed in contrast_fields.json (McLean IL, Lancaster NE, Union OH) into the field tables.
Insert-only: every INSERT uses ON CONFLICT DO NOTHING and nothing is deleted, so Story rows are never touched.
Steps (usage: contrast_fields.py STEP [ARG]):
  fields   CSB polygon (/tmp-free: reads CSB gdb by CSBID) -> fields; SSURGO (SDA, same aggregation as ssurgo_story.py) -> field_soil
  cdl      CDL 2008-2025 zonal majority + share from CropScape county clips (cdl_cropscape_county.py) -> field_crop_history
  openet   OpenET Ensemble monthly ET 2016-2025 at the field representative point (OPENET_API_KEY from env, never logged) -> field_et_openet
  hls YEAR HLS L30/S30 NDVI Apr-Nov (same method as hls_story.py) -> field_ndvi_hls
"""

import json
import os
import sys
import time

import geopandas as gpd
import numpy as np
import psycopg
import pyogrio
import requests
from shapely.geometry import MultiPolygon

HERE = os.path.dirname(os.path.abspath(__file__))
SEL = json.load(open(f"{HERE}/contrast_fields.json"))["fields"]
IDS = [f["field_id"] for f in SEL]
CSB = "/srv/hackathon/data/raw/csb/ext/CSB1825.gdb"
RAW = "/srv/hackathon/data/raw"


def load_fields():
    sys.path.insert(0, HERE)
    from contrast_soil_probe import dominant_mukey, mapunit_props

    rows = []
    for st in sorted({f["county_fips"] for f in SEL}):
        ids = ",".join(f"'{f['field_id']}'" for f in SEL if f["county_fips"] == st)
        df = pyogrio.read_dataframe(CSB, where=f"STATEFIPS='{st[:2]}' AND CNTYFIPS='{st[2:]}' AND CSBID IN ({ids})")
        df["ha"] = df.geometry.area / 1e4
        rows.append(df.to_crs(4326))
    df = gpd.pd.concat(rows)
    assert set(df.CSBID.astype(str)) == set(IDS), set(IDS) - set(df.CSBID.astype(str))
    meta = {f["field_id"]: f for f in SEL}
    soil = []
    for r in df.itertuples():
        fid = str(r.CSBID)
        mk, share = dominant_mukey(r.geometry)
        soil.append((fid, mk, share))
    props = mapunit_props(sorted({s[1] for s in soil}))
    with psycopg.connect("") as c:
        for r in df.itertuples():
            fid = str(r.CSBID)
            g = r.geometry if r.geometry.geom_type == "MultiPolygon" else MultiPolygon([r.geometry])
            c.execute(
                "insert into fields(field_id,csb_version,county_fips,state_alpha,geom,centroid,area_ha,notes) values "
                "(%s,%s,%s,%s,ST_SetSRID(ST_GeomFromWKB(%s),4326),ST_PointOnSurface(ST_SetSRID(ST_GeomFromWKB(%s),4326)),%s,%s) "
                "on conflict do nothing",
                (fid, "CSB 2018-2025 rev23", meta[fid]["county_fips"], meta[fid]["state_alpha"], g.wkb, g.wkb, float(r.ha),
                 "CSB polygon is not an ownership boundary; contrast demo field"),
            )
        for fid, mk, share in soil:
            p = props.get(mk, {})
            area = meta[fid]["county_fips"]
            c.execute(
                "insert into field_soil values (%s,%s,%s,%s,%s,%s,%s,%s) on conflict do nothing",
                (fid, mk, p.get("comppct"), p.get("om_r"), p.get("kffact"), p.get("drainagecl"), p.get("awc_r"),
                 f"SSURGO SDA spatial ({area}); area-dominant mapunit (share=%.2f) {p.get('compname')}" % share),
            )
    print(len(df), "fields loaded;", len(soil), "soil rows")


def load_cdl():
    import rasterio
    from rasterio.features import rasterize

    with psycopg.connect("") as c:
        f = gpd.GeoDataFrame.from_postgis(
            "select field_id,county_fips,geom from fields where field_id=any(%s) order by field_id", c, params=(IDS,),
            geom_col="geom", crs=4326,
        )
        names = dict(c.execute(
            "select distinct on (cdl_class) cdl_class,crop_name from county_crop_share where crop_name is not null "
            "order by cdl_class,year desc").fetchall())
        rows = []
        for fips, g in f.groupby(f.county_fips.str.strip()):
            for y in range(2008, 2026):
                p = f"{RAW}/cdl/tier2_{fips}/cdl_{y}_{fips}.tif"
                if not os.path.exists(p):
                    print("missing", p)
                    continue
                with rasterio.open(p) as s:
                    gg = g.to_crs(s.crs)
                    a = s.read(1)
                    lab = rasterize(((geom, i + 1) for i, geom in enumerate(gg.geom)), out_shape=a.shape,
                                    transform=s.transform, fill=0, dtype="int32")
                for i, fid in enumerate(gg.field_id):
                    v = a[lab == i + 1].astype(int)
                    if v.size == 0:
                        continue
                    cnt = np.bincount(v, minlength=256)
                    k = int(cnt.argmax())
                    rows.append((fid, y, k, names.get(k), float(cnt[k] / v.size)))
        c.cursor().executemany("insert into field_crop_history values (%s,%s,%s,%s,%s) on conflict do nothing", rows)
    print(len(rows), "crop-history rows")


def load_openet():
    out = f"{RAW}/openet/tier2_contrast"
    os.makedirs(out, exist_ok=True)
    h = {"Authorization": os.environ["OPENET_API_KEY"], "Content-Type": "application/json", "accept": "application/json"}
    with psycopg.connect("") as c:
        fl = c.execute("select field_id,ST_X(centroid),ST_Y(centroid) from fields where field_id=any(%s) order by 1",
                       (IDS,)).fetchall()
        rows = []
        for fid, lon, lat in fl:
            for y0, y1 in [(2016, 2017), (2018, 2022), (2023, 2025)]:
                fn = f"{out}/{fid}_{y0}.json"
                if os.path.exists(fn):
                    js = json.load(open(fn))
                else:
                    b = {"date_range": [f"{y0}-01-01", f"{y1}-12-31"], "interval": "monthly",
                         "geometry": [round(lon, 5), round(lat, 5)], "model": "Ensemble", "variable": "ET",
                         "reference_et": "gridMET", "units": "mm", "file_format": "JSON"}
                    time.sleep(1.0)
                    r = requests.post("https://openet-api.org/raster/timeseries/point", headers=h, json=b, timeout=180)
                    if r.status_code != 200:
                        print(fid, y0, r.status_code, r.text[:150])
                        continue
                    open(fn, "w").write(r.text)
                    js = r.json()
                for d in js:
                    rows.append((fid, d["time"], "et_ensemble_mm", d["et"], "mm",
                                 "OpenET Ensemble monthly, point at CSB centroid, gridMET ref"))
        c.cursor().executemany("insert into field_et_openet values (%s,%s,%s,%s,%s,%s) on conflict do nothing", rows)
    print(len(fl), "fields", len(rows), "rows")


def load_hls(year):
    # Reuse the Story reader (granule search + Fmask + polygon mean), but per county bbox and insert-only.
    import types

    src = open(f"{HERE}/hls_story.py").read()
    head = src.split("earthaccess.login")[0]  # imports + GDAL env
    fn_src = "def one(a):" + src.split("def one(a):")[1].split("\nrows = []")[0]
    mod = types.ModuleType("hls_contrast")
    exec(head, mod.__dict__)
    import earthaccess
    from concurrent.futures import ThreadPoolExecutor

    earthaccess.login(strategy="netrc")
    with psycopg.connect("") as c:
        fall = gpd.GeoDataFrame.from_postgis("select field_id,county_fips,geom from fields where field_id=any(%s)", c,
                                             params=(IDS,), geom_col="geom", crs=4326)
    rows = []
    for fips, f in fall.groupby(fall.county_fips.str.strip()):
        mod.f = f[["field_id", "geom"]].set_geometry("geom")
        exec(fn_src, mod.__dict__)
        grs = []
        for sn in ["HLSL30", "HLSS30"]:
            r = earthaccess.search_data(short_name=sn, bounding_box=tuple(f.total_bounds),
                                        temporal=(f"{year}-04-01", f"{year}-11-30"), cloud_cover=(0, 70))
            grs += [(sn, g) for g in r]
        print(fips, year, len(grs), "granules", flush=True)
        t0 = time.time()
        with ThreadPoolExecutor(6) as ex:
            for i, o in enumerate(ex.map(mod.one, grs)):
                rows += o
                if i % 100 == 0:
                    print(fips, i, len(rows), round(time.time() - t0), "s", flush=True)
    with psycopg.connect("") as c:
        c.cursor().executemany("insert into field_ndvi_hls values (%s,%s,%s,%s,%s) on conflict do nothing", rows)
    print("rows", len(rows))


if __name__ == "__main__":
    step = sys.argv[1]
    {"fields": load_fields, "cdl": load_cdl, "openet": load_openet}.get(step, lambda: load_hls(int(sys.argv[2])))()
