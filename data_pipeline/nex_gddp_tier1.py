"""NEX-GDDP-CMIP6 (s3://nex-gddp-cmip6, anonymous) -> per-county (nearest 0.25 deg cell to representative point) annual/MAM/JJA means per year.
Usage: nex_gddp_tier1.py MODEL [MODEL...]. historical 1985-2014, ssp245+ssp585 2031-2040, vars pr,tasmax,tasmin. File downloaded, reduced, deleted."""
import sys, os, s3fs, numpy as np, xarray as xr, psycopg, time
from concurrent.futures import ThreadPoolExecutor
TMP="/srv/hackathon/data/raw/nex_gddp/tier1_county/tmp"; os.makedirs(TMP,exist_ok=True)
fs=s3fs.S3FileSystem(anon=True,client_kwargs={"region_name":"us-west-2"})
with psycopg.connect("") as c:
    pts=c.execute("select county_fips,ST_X(centroid),ST_Y(centroid) from county order by 1").fetchall()
fips=[p[0] for p in pts]; plon=np.array([p[1] for p in pts])%360; plat=np.array([p[2] for p in pts])
lat=-59.875+0.25*np.arange(600); lon=0.125+0.25*np.arange(1440)
ilat=xr.DataArray(np.abs(lat[None,:]-plat[:,None]).argmin(1),dims="c"); ilon=xr.DataArray(np.abs(lon[None,:]-plon[:,None]).argmin(1),dims="c")
def job(a):
    model,scn,var,yr=a
    key=f"nex-gddp-cmip6/NEX-GDDP-CMIP6/{model}/{scn}/r1i1p1f1/{var}/{var}_day_{model}_{scn}_r1i1p1f1_gn_{yr}.nc"
    cand=[key, key.replace(".nc","_v1.1.nc"), key.replace(".nc","_v2.0.nc")]
    ex=[k for k in cand if fs.exists(k)]
    if not ex: return a,None,"missing"
    q=f"{TMP}/{model}_{scn}_{var}_{yr}.nc"
    for t in range(3):
        try: fs.get(ex[0],q); break
        except Exception as e: time.sleep(5)
    else: return a,None,"dlfail"
    ds=xr.open_dataset(q); v=ds[var].isel(lat=ilat,lon=ilon).load(); mon=ds.time.dt.month.values; ds.close(); os.remove(q)
    v=v.values.astype("float64")
    if var=="pr": v=v*86400; unit="mm/day"
    else: v=v-273.15; unit="degC"
    out=[]
    for season,ms in [("ANN",range(1,13)),("MAM",[3,4,5]),("JJA",[6,7,8])]:
        m=np.isin(mon,list(ms)); s=v[m].mean(0)
        out+=[(f,"nex_gddp",model,scn,"r1i1p1f1",var,season,yr,float(x),unit) for f,x in zip(fips,s)]
    return a,out,ex[0].split("/")[-1]
tasks=[(m,s,v,y) for m in sys.argv[1:] for s,yrs in [("historical",range(1985,2015)),("ssp245",range(2031,2041)),("ssp585",range(2031,2041))] for v in ["pr","tasmax","tasmin"] for y in yrs]
print(len(tasks),"files",flush=True); n=0; t0=time.time()
with ThreadPoolExecutor(4) as ex_:
    for a,out,note in ex_.map(job,tasks):
        if out is None: print("SKIP",a,note,flush=True); continue
        with psycopg.connect("") as c:
            with c.cursor() as cur:
                cur.execute("delete from county_scenario_year where model=%s and scenario=%s and variable=%s and year=%s",(a[0],a[1],a[2],a[3]))
                with cur.copy("copy county_scenario_year(county_fips,source_id,model,scenario,member,variable,season,year,value,unit) from stdin") as cp:
                    for r in out: cp.write_row(r)
        n+=1
        if n%10==0: print(n,round(time.time()-t0),"s",note,flush=True)
print("done",n)
