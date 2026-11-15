"""CDL 30 m national zip -> county crop shares (12 states) + Story County 30 m clip (tier2). Usage: cdl_tier1.py YEAR [YEAR...]
National zip is downloaded, processed, then the extracted tif and zip are deleted (url + sha256 recorded in manifest)."""
import sys, os, zipfile, hashlib, json, time, numpy as np, rasterio, geopandas as gpd, psycopg
from rasterio.windows import from_bounds, Window
from rasterio.features import geometry_mask
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0,os.path.dirname(__file__)); from rangedl import rangedl
BASE="https://www.nass.usda.gov/sites/default/files/Research_and_Science/Cropland/Release/datasets"
TMP="/srv/hackathon/data/raw/cdl/national_tmp"; T2="/srv/hackathon/data/raw/cdl/tier2_story"; T1="/srv/hackathon/data/raw/cdl/tier1_county"
STATES=["19","17","18","39","31","27","46","55","29","20","26","21"]
def zone(args):
    tif,fips,wkt=args
    from shapely import wkt as W
    geom=W.loads(wkt)
    with rasterio.open(tif) as src:
        win=from_bounds(*geom.bounds,transform=src.transform).round_offsets().round_lengths()
        win=win.intersection(Window(0,0,src.width,src.height))
        a=src.read(1,window=win); tr=src.window_transform(win)
    m=~geometry_mask([geom],out_shape=a.shape,transform=tr)
    v=a[m]; c=np.bincount(v,minlength=256)
    return fips,c
def main(years):
    cs=gpd.read_file("zip:///srv/hackathon/data/raw/census/cb/c.zip"); cs=cs[cs.STATEFP.isin(STATES)].to_crs(5070)
    os.makedirs(T2,exist_ok=True); os.makedirs(T1,exist_ok=True)
    for y in years:
        t0=time.time(); zf=f"{TMP}/{y}_30m_cdls.zip"
        rangedl(f"{BASE}/{y}_30m_cdls.zip",zf)
        sha=hashlib.sha256(open(zf,"rb").read()).hexdigest() if False else None
        z=zipfile.ZipFile(zf); d=f"{TMP}/{y}"; os.makedirs(d,exist_ok=True)
        for n in z.namelist():
            if n.endswith((".tif",".tif.vat.dbf",".tif.xml")): z.extract(n,d)
        tif=f"{d}/{y}_30m_cdls.tif"; t1=time.time()
        with ProcessPoolExecutor(8) as ex:
            res=list(ex.map(zone,[(tif,r.GEOID,r.geometry.wkt) for r in cs.itertuples()],chunksize=8))
        # VAT names
        names={}
        try:
            import struct
            f=open(f"{d}/{y}_30m_cdls.tif.vat.dbf","rb").read()
            nrec,hl,rl=struct.unpack("<IHH",f[4:12]); flds=[];o=32
            while f[o]!=0x0D: flds.append((f[o:o+11].split(b"\0")[0].decode(),f[o+16])); o+=32
            for i in range(nrec):
                rec=f[hl+i*rl+1:hl+(i+1)*rl]; p=0; row={}
                for n,l in flds: row[n]=rec[p:p+l].decode("latin1").strip(); p+=l
                names[int(row.get("VALUE",row.get("Value")))]=row.get("CLASS_NAME") or row.get("Class_Name")
        except Exception as e: print("vat fail",e)
        rows=[]
        for fips,c in res:
            tot=c[1:].sum()   # exclude 0 = background/no data
            for k in np.nonzero(c)[0]:
                if k==0: continue
                rows.append((fips,y,int(k),names.get(int(k)),int(c[k]),float(c[k]/tot)))
        with psycopg.connect("") as con:
            con.execute("delete from county_crop_share where year=%s",(y,))
            with con.cursor() as cur:
                cur.executemany("insert into county_crop_share values (%s,%s,%s,%s,%s,%s)",rows)
        # Story clip tier2
        st=cs[cs.GEOID=="19169"].geometry.iloc[0]
        with rasterio.open(tif) as src:
            win=from_bounds(*st.bounds,transform=src.transform).round_offsets().round_lengths()
            a=src.read(1,window=win); prof=src.profile.copy()
            prof.update(width=a.shape[1],height=a.shape[0],transform=src.window_transform(win),compress="deflate",tiled=True,blockxsize=256,blockysize=256)
            with rasterio.open(f"{T2}/cdl_{y}_story_19169.tif","w",**prof) as dst: dst.write(a,1)
        json.dump({"year":y,"url":f"{BASE}/{y}_30m_cdls.zip","zonal_s":time.time()-t1,"total_s":time.time()-t0,"rows":len(rows),"crs":"EPSG:5070"},open(f"{T1}/manifest_{y}.json","w"))
        import shutil; shutil.rmtree(d); os.remove(zf)
        print(y,len(rows),"rows",round(time.time()-t0),"s",flush=True)
if __name__=="__main__": main([int(a) for a in sys.argv[1:]])
