"""Run Prithvi crop classification (inference only, CPU) on fetched HLS chips and upsert vision_result rows.

Per field: crop_pred = majority Prithvi class among chip pixels inside the CSB polygon;
class_fractions = share of each of the 13 official classes inside the polygon;
bare_fraction = share of pixels classed 'Developed/Barren' or 'Fallow/Idle Cropland' (the two non-vegetated /
idle classes in the official list);
agreement_with_cdl = share of in-polygon pixels whose Prithvi class equals the CDL 2024 pixel mapped by class name
(CDL 1 Corn, 5 Soybeans, 24 Winter Wheat, 36 Alfalfa, 61 Fallow/Idle Cropland, 2 Cotton, 4 Sorghum,
111 Open Water, 141-143 Forest). Pixels with other CDL codes are excluded from the denominator because the official
CDL->13-class reclass table could not be confirmed (see docs/PRITHVI.md).
CDL rasters: {CDL_ROOT}/tier2_<fips>/ (per-county 30 m clips). Usage: python -m model_api.vision.run_prithvi YEAR
"""

from __future__ import annotations

import glob
import json
import os
import sys
import time

import geopandas as gpd
import numpy as np
import psycopg
import rasterio
from affine import Affine
from rasterio.features import geometry_mask
from rasterio.warp import Resampling, reproject

from model_api.vision import prithvi_crop as P

OUT = os.environ.get("PRITHVI_DATA", "/srv/hackathon/data/raw/hls_prithvi")
CDL_ROOT = os.environ.get("CDL_ROOT", "/srv/hackathon/data/raw/cdl")
CKPT = f"{OUT}/model/{P.CKPT_NAME}"
CDL_TO_CLASS = {1: "Corn", 5: "Soybeans", 24: "Winter Wheat", 36: "Alfalfa", 61: "Fallow/Idle Cropland", 2: "Cotton",
                4: "Sorghum", 111: "Open Water", 141: "Forest", 142: "Forest", 143: "Forest"}
BARE = ("Developed/Barren", "Fallow/Idle Cropland")


def cdl_path(fips: str, year: int) -> str:
    if fips == "19169":
        return f"{CDL_ROOT}/tier2_story/cdl_{year}_story_19169.tif"
    return f"{CDL_ROOT}/tier2_{fips}/cdl_{year}_{fips}.tif"


def main(year: int):
    files = sorted(glob.glob(f"{OUT}/chips/*_{year}.npz"))
    ids = [os.path.basename(p).split("_")[0] for p in files]
    with psycopg.connect("") as c:
        f = gpd.GeoDataFrame.from_postgis(
            "select field_id, county_fips, geom from fields where field_id = any(%s)", c, params=(ids,), geom_col="geom", crs=4326
        ).set_index("field_id")
    t0 = time.time()
    model = P.load(CKPT)
    t_load = time.time() - t0
    rows, timings, report = [], [], []
    os.makedirs(f"{OUT}/pred", exist_ok=True)
    for path, fid in zip(files, ids):
        z = np.load(path)
        stack, valid = z["stack"].astype(np.float32), z["valid"]
        crs, tr = str(z["crs"]), Affine(*z["transform"].tolist())
        # invalid (cloud/fill) pixels -> band mean => 0 after normalisation
        for t in range(3):
            stack[~valid[t], t * 6 : (t + 1) * 6] = P.MEANS[t * 6 : (t + 1) * 6]
        t1 = time.time()
        cls, prob = P.predict(model, stack)
        dt = time.time() - t1
        timings.append(dt)
        geom = f.loc[[fid]].to_crs(crs).geometry.iloc[0]
        inside = ~geometry_mask([geom], out_shape=cls.shape, transform=tr)
        n = int(inside.sum())
        counts = np.bincount(cls[inside], minlength=13)
        fr = {P.CLASSES[i]: round(float(counts[i] / n), 4) for i in range(13) if counts[i]}
        pred = P.CLASSES[int(counts.argmax())]
        bare = round(sum(fr.get(k, 0.0) for k in BARE), 4)
        cdl_chip = np.zeros(cls.shape, np.uint8)
        cdl = rasterio.open(cdl_path(f.loc[fid, "county_fips"].strip(), year))
        reproject(rasterio.band(cdl, 1), cdl_chip, dst_transform=tr, dst_crs=crs, resampling=Resampling.nearest, dst_nodata=0)
        cmp = inside & np.isin(cdl_chip, list(CDL_TO_CLASS))
        agree = None
        if cmp.sum():
            want = np.vectorize(lambda v: P.CLASSES.index(CDL_TO_CLASS[v]))(cdl_chip[cmp])
            agree = round(float((cls[cmp] == want).mean()), 4)
        cdl_vals, cdl_n = np.unique(cdl_chip[inside], return_counts=True)
        cdl_major = int(cdl_vals[cdl_n.argmax()])
        inval = round(float(1 - valid[:, inside].mean()), 4)
        dates = ";".join(z["dates"].tolist())
        note = (
            f"CPU inference, pure-PyTorch forward of released checkpoint, no fine-tuning; sensors {';'.join(z['sensors'].tolist())}; "
            f"{n} px in polygon, cloud/fill px in polygon {inval:.1%} (mean-filled); CDL-compared px {int(cmp.sum())}; "
            f"bare_fraction = Developed/Barren + Fallow/Idle Cropland; model card aAcc 60.64 %, mIoU 0.4269"
        )
        rows.append((fid, year, P.MODEL_ID, dates, pred, json.dumps(fr), bare, agree, note))
        report.append({"field_id": fid, "dates": dates, "crop_pred": pred, "bare_fraction": bare, "agreement_with_cdl": agree,
                       "cdl_major_code": cdl_major, "px": n, "cmp_px": int(cmp.sum()), "invalid_in_field": inval,
                       "top": sorted(fr.items(), key=lambda kv: -kv[1])[:3], "infer_s": round(dt, 2)})
        np.savez_compressed(f"{OUT}/pred/{fid}_{year}.npz", cls=cls, maxprob=prob.max(0).astype(np.float16), inside=inside)
        print(json.dumps(report[-1]), flush=True)
    with psycopg.connect("") as c:
        c.cursor().executemany(
            "insert into vision_result (field_id, year, model_id, scene_dates, crop_pred, class_fractions, bare_fraction, "
            "agreement_with_cdl, notes) values (%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s) "
            "on conflict (field_id, year, model_id) do update set scene_dates=excluded.scene_dates, crop_pred=excluded.crop_pred, "
            "class_fractions=excluded.class_fractions, bare_fraction=excluded.bare_fraction, "
            "agreement_with_cdl=excluded.agreement_with_cdl, notes=excluded.notes",
            rows,
        )
    summ = {"year": year, "fields": len(rows), "load_s": round(t_load, 1), "infer_mean_s": round(float(np.mean(timings)), 2),
            "total_s": round(time.time() - t0, 1), "torch_threads": __import__("torch").get_num_threads()}
    print("SUMMARY", json.dumps(summ))
    with open(f"{OUT}/pred/report_{year}.json", "w") as fh:
        json.dump({"summary": summ, "fields": report}, fh, indent=1)


if __name__ == "__main__":
    main(int(sys.argv[1]))
