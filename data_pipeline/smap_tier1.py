"""SMAP L3 (SPL3SMP v009, 36 km EASE-Grid 2.0) soil moisture AM at the cell containing each county representative point (context only, NOT field-precise).
Every STEP-th day Apr-Oct per year. Granule downloaded, reduced, deleted. Usage: smap_tier1.py YEAR0 YEAR1 STEP"""
import sys, os, h5py, numpy as np, pandas as pd, psycopg, earthaccess, datetime as dt
from concurrent.futures import ThreadPoolExecutor
TMP="/srv/hackathon/data/raw/smap/tier1_county/tmp"; os.makedirs(TMP,exist_ok=True)
earthaccess.login(strategy="netrc")
y0,y1,step=map(int,sys.argv[1:4])
with psycopg.connect("") as c:
    pts=c.execute("select county_fips,ST_X(centroid),ST_Y(centroid) from county order by 1").fetchall()
fips=[p[0] for p in pts]; plon=np.array([p[1] for p in pts]); plat=np.array([p[2] for p in pts])
res=[]
for y in range(y0,y1+1):
    r=earthaccess.search_data(short_name="SPL3SMP",temporal=(f"{y}-04-01",f"{y}-10-31"))
    res+= [g for i,g in enumerate(sorted(r,key=lambda g:g.data_links()[0])) if i%step==0]
print(len(res),"granules",flush=True)
idx=None
def proc(g):
    for a in range(3):
        try: f=earthaccess.download([g],TMP)[0]; break
        except Exception as e: pass
    else: return None
    h=h5py.File(f,"r"); gp=h["Soil_Moisture_Retrieval_Data_AM"]
    sm=gp["soil_moisture"][:]; q=gp["retrieval_qual_flag"][:]; lat=gp["latitude"][:]; lon=gp["longitude"][:]
    d=os.path.basename(f).split("_")[4]; unit="cm3/cm3"
    h.close(); os.remove(f); return d,sm,lat,lon,q,unit
rows=[]
with ThreadPoolExecutor(5) as ex:
    for r in ex.map(proc,res):
        if r is None: continue
        d,sm,lat,lon,q,unit=r
        if idx is None:
            ok=lat>-999; la=lat[ok]; lo=lon[ok]; ij=np.argwhere(ok)
            idx=[ij[np.argmin((la-y)**2+((lo-x)*np.cos(np.radians(y)))**2)] for x,y in zip(plon,plat)]; print("indexed",flush=True)
        v=np.array([sm[i,j] for i,j in idx],dtype="float64"); v[v<0]=np.nan
        date=f"{d[:4]}-{d[4:6]}-{d[6:]}"
        rows+=[(f,date,"SPL3SMP.009","soil_moisture_am",None if np.isnan(x) else float(x),"cm3/cm3") for f,x in zip(fips,v)]
with psycopg.connect("") as c:
    c.execute("delete from county_smap where date between %s and %s and product='SPL3SMP.009'",(f"{y0}-01-01",f"{y1}-12-31"))
    with c.cursor() as cur:
        with cur.copy("copy county_smap from stdin") as cp:
            for r in rows: cp.write_row(r)
print("rows",len(rows),"nonnull",sum(1 for r in rows if r[4] is not None))
