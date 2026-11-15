"""Probe SSURGO (Soil Data Access, public) for candidate CSB fields: area-dominant mapunit per field polygon via SDA spatial
intersection, plus component-weighted surface-horizon om_r, kffact, awc_r and dominant-component drainagecl / compname.
Usage: contrast_soil_probe.py CAND.gpkg N_SAMPLE OUT.csv   (<=1 req/s to SDA)."""

import sys
import time

import geopandas as gpd
import numpy as np
import pandas as pd
import requests

SDA = "https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest"


def sda(q):
    time.sleep(1.0)
    r = requests.post(SDA, data={"query": q, "format": "JSON+COLUMNNAME"}, timeout=180)
    r.raise_for_status()
    t = r.json().get("Table", [])
    return pd.DataFrame(t[1:], columns=t[0]) if t else pd.DataFrame()


def dominant_mukey(geom):
    w = geom.simplify(0.00002).wkt
    d = sda(
        f"SELECT P.mukey, SUM(P.mupolygongeo.STIntersection(geometry::STGeomFromText('{w}',4326)).STArea()) AS a FROM mupolygon P "
        f"WHERE P.mupolygongeo.STIntersects(geometry::STGeomFromText('{w}',4326))=1 GROUP BY P.mukey"
    )
    d["a"] = pd.to_numeric(d["a"])
    d = d.sort_values("a", ascending=False)
    return d.iloc[0]["mukey"], float(d.iloc[0]["a"] / d["a"].sum())


def mapunit_props(mukeys):
    ks = ",".join(f"'{k}'" for k in mukeys)
    t = sda(
        "SELECT mu.mukey, mu.muname, c.compname, c.comppct_r, c.drainagecl, ch.om_r, ch.kffact, ch.awc_r FROM mapunit mu "
        "JOIN component c ON c.mukey=mu.mukey LEFT JOIN chorizon ch ON ch.cokey=c.cokey AND ch.hzdept_r=0 "
        f"WHERE mu.mukey IN ({ks})"
    )
    for k in ["comppct_r", "om_r", "kffact", "awc_r"]:
        t[k] = pd.to_numeric(t[k])
    out = {}
    for mk, g in t.groupby("mukey"):
        o = {}
        for k in ["om_r", "kffact", "awc_r"]:
            m = g[k].notna() & (g.comppct_r > 0)
            o[k] = float(np.average(g.loc[m, k], weights=g.loc[m, "comppct_r"])) if m.any() else None
        dom = g.sort_values("comppct_r", ascending=False).iloc[0]
        o.update(drainagecl=dom.drainagecl, compname=dom.compname, muname=dom.muname, comppct=float(g.comppct_r.sum()))
        out[mk] = o
    return out


if __name__ == "__main__":
    cand = gpd.read_file(sys.argv[1])
    n = int(sys.argv[2])
    s = cand.sample(min(n, len(cand)), random_state=7)
    rows = []
    for r in s.itertuples():
        try:
            mk, sh = dominant_mukey(r.geometry)
        except Exception as e:
            print("skip", r.CSBID, repr(e)[:80], flush=True)
            continue
        rows.append(dict(CSBID=r.CSBID, ha=r.ha, seq=r.seq, mukey=mk, share=sh))
    df = pd.DataFrame(rows)
    p = mapunit_props(df.mukey.unique())
    df = df.join(pd.DataFrame([{**{"mukey": k}, **v} for k, v in p.items()]).set_index("mukey"), on="mukey")
    df.to_csv(sys.argv[3], index=False)
    print(df.drop(columns=["muname"]).to_string())
