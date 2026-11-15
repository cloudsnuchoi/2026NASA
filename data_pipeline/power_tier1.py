"""NASA POWER daily (AG community) at county representative points, 1995-2025. Rate limit 2 req/s, 4 workers. Raw JSON gz cached; loads county_weather_daily (source_id='power')."""
import os, json, gzip, time, threading, io, requests, psycopg
from concurrent.futures import ThreadPoolExecutor
RAW="/srv/hackathon/data/raw/power/tier1_county"
P="T2M,T2M_MIN,T2M_MAX,PRECTOTCORR,RH2M,WS2M,ALLSKY_SFC_SW_DWN"
lock=threading.Lock(); last=[0.0]
def throttle():
    with lock:
        w=last[0]+0.5-time.time()
        if w>0: time.sleep(w)
        last[0]=time.time()
def fetch(row):
    fips,lon,lat=row; f=f"{RAW}/{fips}.json.gz"
    if os.path.exists(f): return fips,True
    for a in range(4):
        throttle()
        try:
            r=requests.get("https://power.larc.nasa.gov/api/temporal/daily/point",params=dict(parameters=P,community="AG",longitude=round(lon,4),latitude=round(lat,4),start="19950101",end="20251231",format="JSON"),timeout=120)
            if r.status_code==200:
                with gzip.open(f+".tmp","wt") as g: g.write(r.text)
                os.rename(f+".tmp",f); return fips,True
        except Exception as e: pass
        time.sleep(3*(a+1))
    return fips,False
def load(fips):
    d=json.load(gzip.open(f"{RAW}/{fips}.json.gz","rt")); p=d["properties"]["parameter"]
    def v(k,dt):
        x=p[k][dt]; return "\\N" if x==-999 or x==-999.0 else repr(x)
    buf=io.StringIO()
    for dt in p["T2M"]:
        buf.write("\t".join([fips,f"{dt[:4]}-{dt[4:6]}-{dt[6:]}","power",v("T2M",dt),v("T2M_MIN",dt),v("T2M_MAX",dt),v("PRECTOTCORR",dt),v("RH2M",dt),v("WS2M",dt),v("ALLSKY_SFC_SW_DWN",dt),"\\N"])+"\n")
    return buf.getvalue(), d["header"]
if __name__=="__main__":
    with psycopg.connect("") as c:
        pts=c.execute("select county_fips,ST_X(centroid),ST_Y(centroid) from county order by 1").fetchall()
    t=time.time()
    with ThreadPoolExecutor(4) as ex: res=list(ex.map(fetch,pts))
    bad=[f for f,ok in res if not ok]; print("fetched",len(res)-len(bad),"failed",bad,time.time()-t)
    with psycopg.connect("") as c:
        c.execute("delete from county_weather_daily where source_id='power'")
        with c.cursor() as cur:
            with cur.copy("copy county_weather_daily(county_fips,date,source_id,t2m_c,tmin_c,tmax_c,precip_mm,rh2m_pct,ws2m_ms,srad_mj_m2,et0_mm) from stdin") as cp:
                for f,ok in res:
                    if ok: cp.write(load(f)[0])
    print("loaded",time.time()-t)
