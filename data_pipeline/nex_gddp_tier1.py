"""NEX-GDDP-CMIP6 via NCCS THREDDS NCSS (server-side bbox subset, public) -> per-county (nearest 0.25 deg cell to representative point) annual/MAM/JJA means per year.
bbox lat 36-49.5, lon 255-281 (E) covers the 12 Corn Belt states. historical 1985-2014, ssp245+ssp585 2031-2040, vars pr,tasmax,tasmin, member r1i1p1f1, v2.0 files.
Why NCSS: direct S3 download of full global files (~200 MB each) ran at ~0.5 MB/s here; NCSS returns ~4.6 MB per file in ~27 s.
Dataset licence: CC0 per AWS registry (file attrs say cmip6_license CC-BY-SA 4.0 -> cite both). Usage: nex_gddp_tier1.py MODEL [MODEL...]"""
import sys, os, requests, numpy as np, xarray as xr, psycopg, time, threading
from concurrent.futures import ThreadPoolExecutor
TMP="/srv/hackathon/data/raw/nex_gddp/tier1_county/tmp"; os.makedirs(TMP,exist_ok=True)
BASE="https://ds.nccs.nasa.gov/thredds/ncss/grid/AMES/NEX/GDDP-CMIP6"
with psycopg.connect("") as c:
    pts=c.execute("select county_fips,ST_X(centroid),ST_Y(centroid) from county order by 1").fetchall()
fips=[p[0] for p in pts]; plon=np.array([p[1] for p in pts])%360; plat=np.array([p[2] for p in pts])
GRID={"GFDL-ESM4":"gr1"}  # grid label differs per model in file names
NCLOCK=threading.Lock()  # netCDF4/HDF5 not thread-safe
def job(a):
    model,scn,var,yr=a
    url=f"{BASE}/{model}/{scn}/r1i1p1f1/{var}/{var}_day_{model}_{scn}_r1i1p1f1_{GRID.get(model,'gn')}_{yr}_v2.0.nc"
    q=f"{TMP}/{model}_{scn}_{var}_{yr}.nc"; ok=False
    for t in range(4):
        try:
            time.sleep(0.5)
            r=requests.get(url,params=dict(var=var,north=49.5,south=36.0,west=255.0,east=281.0,time_start=f"{yr}-01-01T00:00:00Z",time_end=f"{yr}-12-31T23:59:59Z",accept="netcdf4"),timeout=180)
            if r.status_code==404: return a,None,"missing"
            if r.status_code==200 and len(r.content)>10000: open(q,"wb").write(r.content); ok=True; break
        except Exception as e: pass
        time.sleep(5)
    if not ok: return a,None,"dlfail"
    with NCLOCK:
        ds=xr.open_dataset(q); la=ds.lat.values; lo=ds.lon.values; v=ds[var].values; mon=ds.time.dt.month.values; ds.close()
    os.remove(q)
    ilat=np.abs(la[None,:]-plat[:,None]).argmin(1); ilon=np.abs(lo[None,:]-plon[:,None]).argmin(1)
    v=v[:,ilat,ilon].astype("float64")
    if var=="pr": v=v*86400; unit="mm/day"
    else: v=v-273.15; unit="degC"
    out=[]
    for season,ms in [("ANN",range(1,13)),("MAM",[3,4,5]),("JJA",[6,7,8])]:
        m=np.isin(mon,list(ms)); s=v[m].mean(0)
        out+=[(f,"nex_gddp",model,scn,"r1i1p1f1",var,season,yr,float(x),unit) for f,x in zip(fips,s)]
    return a,out,"ok"
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
        if n%10==0: print(n,round(time.time()-t0),"s",flush=True)
print("done",n)
