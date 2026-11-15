"""SSURGO for Story County (areasymbol IA169) via Soil Data Access (public). Per field: area-dominant mapunit; per mapunit: component-weighted
surface-horizon (hzdept_r=0) om_r (%), kffact, awc_r (cm/cm) and dominant-component drainage class. Writes field_soil."""
import json, requests, geopandas as gpd, pandas as pd, psycopg, shapely.wkt as W, numpy as np
D="/srv/hackathon/data/raw/ssurgo/tier2_story"
def sda(q):
    r=requests.post("https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest",data={"query":q,"format":"JSON+COLUMNNAME"},timeout=300); r.raise_for_status()
    t=r.json()["Table"]; return pd.DataFrame(t[1:],columns=t[0])
tab=sda("""SELECT mu.mukey, c.cokey, c.comppct_r, c.drainagecl, ch.om_r, ch.kffact, ch.awc_r FROM legend l JOIN mapunit mu ON mu.lkey=l.lkey
 JOIN component c ON c.mukey=mu.mukey LEFT JOIN chorizon ch ON ch.cokey=c.cokey AND ch.hzdept_r=0 WHERE l.areasymbol='IA169'""")
tab.to_csv(f"{D}/component_surface_ia169.csv",index=False)
for k in ["comppct_r","om_r","kffact","awc_r"]: tab[k]=pd.to_numeric(tab[k])
def agg(g):
    out={}
    for k in ["om_r","kffact","awc_r"]:
        m=g[k].notna(); out[k]=np.average(g.loc[m,k],weights=g.loc[m,"comppct_r"]) if m.any() and g.loc[m,"comppct_r"].sum()>0 else None
    dom=g.sort_values("comppct_r",ascending=False).iloc[0]; out["drainagecl"]=dom["drainagecl"]; out["comppct"]=g.comppct_r.sum()
    return pd.Series(out)
mu=tab.groupby("mukey").apply(agg)
raw=json.load(open(f"{D}/mupoly_ia169.json"))["Table"]
polys=gpd.GeoDataFrame({"mukey":[r[0] for r in raw]},geometry=[W.loads(r[1]) for r in raw],crs=4326).to_crs(5070)
with psycopg.connect("") as c:
    f=gpd.GeoDataFrame.from_postgis("select field_id, geom from fields where county_fips='19169'",c,geom_col="geom",crs=4326).to_crs(5070)
ov=gpd.overlay(f[["field_id","geom"]].set_geometry("geom").rename_geometry("geometry"),polys,how="intersection",keep_geom_type=False)
ov["a"]=ov.geometry.area
dom=ov.sort_values("a",ascending=False).drop_duplicates("field_id")
dom["share"]=dom.a/ov.groupby("field_id").a.sum().reindex(dom.field_id).values
rows=[]
for r in dom.itertuples():
    m=mu.loc[r.mukey] if r.mukey in mu.index else None
    rows.append((r.field_id,r.mukey,None if m is None else float(m.comppct),None if m is None or pd.isna(m.om_r) else float(m.om_r),None if m is None or pd.isna(m.kffact) else float(m.kffact),None if m is None else m.drainagecl,None if m is None or pd.isna(m.awc_r) else float(m.awc_r),"SSURGO SDA IA169; area-dominant mapunit (share=%.2f)"%r.share))
with psycopg.connect("") as c:
    c.execute("delete from field_soil")
    c.cursor().executemany("insert into field_soil values (%s,%s,%s,%s,%s,%s,%s,%s)",rows)
print(len(rows),"fields;",len(mu),"mapunits;",len(polys),"polygons")
