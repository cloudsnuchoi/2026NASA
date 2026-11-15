"""GPM IMERG Final daily (GPM_3IMERGDF v07, 0.1 deg) county mean precipitation, for chosen periods. Raw granule downloaded, reduced, then deleted (31 MB/day).
Usage: imerg_tier1.py START END   (YYYY-MM-DD). Cells whose centre falls inside the county; counties with none use nearest cell."""
import sys, os, numpy as np, pandas as pd, xarray as xr, geopandas as gpd, psycopg, earthaccess, time
from concurrent.futures import ThreadPoolExecutor
TMP="/srv/hackathon/data/raw/imerg/tier1_county/tmp"; os.makedirs(TMP,exist_ok=True)
earthaccess.login(strategy="netrc")
start,end=sys.argv[1],sys.argv[2]
cs=gpd.read_file("zip:///srv/hackathon/data/raw/census/cb/c.zip"); cs=cs[cs.STATEFP.isin(["19","17","18","39","31","27","46","55","29","20","26","21"])].to_crs(4326)
res=earthaccess.search_data(short_name="GPM_3IMERGDF",temporal=(start,end)); print(len(res),"granules",flush=True)
mapping=None
def proc(g):
    global mapping
    for a in range(3):
        try: f=earthaccess.download([g],TMP)[0]; break
        except Exception as e: time.sleep(5)
    else: return None
    ds=xr.open_dataset(f,engine="h5netcdf" if False else None)
    p=ds["precipitation"].isel(time=0).sel(lon=slice(-105,-79),lat=slice(35,50))
    date=str(ds.time.values[0])[:10]
    v=p.transpose("lat","lon").values.astype("float32"); lat=p.lat.values; lon=p.lon.values; ds.close(); os.remove(f)
    return date,v,lat,lon
out=[]
with ThreadPoolExecutor(5) as ex:
    for r in ex.map(proc,res):
        if r is None: continue
        date,v,lat,lon=r
        if mapping is None:
            LON,LAT=np.meshgrid(lon,lat); pts=gpd.GeoDataFrame({"i":np.arange(LON.size)},geometry=gpd.points_from_xy(LON.ravel(),LAT.ravel()),crs=4326)
            j=gpd.sjoin(pts,cs[["GEOID","geometry"]],predicate="within")[["i","GEOID"]]
            have=set(j.GEOID); miss=cs[~cs.GEOID.isin(have)]
            extra=[]
            for r_ in miss.itertuples():
                c=r_.geometry.representative_point(); k=int(np.argmin((LON.ravel()-c.x)**2+(LAT.ravel()-c.y)**2)); extra.append((k,r_.GEOID))
            mapping=pd.concat([j,pd.DataFrame(extra,columns=["i","GEOID"])]); print("mapped",len(mapping),len(miss),"nearest-cell counties",flush=True)
        flat=v.ravel()[mapping.i.values]; flat=np.where(flat<0,np.nan,flat)
        s=pd.Series(flat).groupby(mapping.GEOID.values).mean()
        out+= [(k,date,None if np.isnan(x) else float(x),"GPM_3IMERGDF.07") for k,x in s.items()]
        if len(out)%(1122*20)<1122: print(date,flush=True)
with psycopg.connect("") as c:
    ds_=sorted({o[1] for o in out})
    c.execute("delete from county_imerg_daily where date between %s and %s",(start,end))
    with c.cursor() as cur:
        with cur.copy("copy county_imerg_daily(county_fips,date,precip_mm,product) from stdin") as cp:
            for o in out: cp.write_row(o)
print("rows",len(out))
