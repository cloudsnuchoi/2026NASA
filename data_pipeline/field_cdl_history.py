"""Field-level CDL history 2008-2025: zonal majority class + share per CSB field from the Story 30 m CDL clips (pixel centres inside polygon)."""
import numpy as np, rasterio, geopandas as gpd, psycopg
from rasterio.features import rasterize
T="/srv/hackathon/data/raw/cdl/tier2_story"
with psycopg.connect("") as c:
    f=gpd.GeoDataFrame.from_postgis("select field_id,geom from fields where county_fips='19169' order by field_id",c,geom_col="geom",crs=4326).to_crs(5070)
    names=dict(c.execute("select distinct on (cdl_class) cdl_class,crop_name from county_crop_share where crop_name is not null order by cdl_class,year desc").fetchall())
    c.execute("delete from field_crop_history")
    for y in range(2008,2026):
        with rasterio.open(f"{T}/cdl_{y}_story_19169.tif") as s:
            a=s.read(1); lab=rasterize(((g,i+1) for i,g in enumerate(f.geometry)),out_shape=a.shape,transform=s.transform,fill=0,dtype="int32")
        m=lab>0; idx=lab[m]-1; cls=a[m].astype(int)
        cnt=np.zeros((len(f),256),dtype=np.int64); np.add.at(cnt,(idx,cls),1)
        rows=[]
        for i,fid in enumerate(f.field_id):
            tot=cnt[i].sum()
            if tot==0: continue
            k=int(cnt[i].argmax()); rows.append((fid,y,k,names.get(k),float(cnt[i,k]/tot)))
        c.cursor().executemany("insert into field_crop_history values (%s,%s,%s,%s,%s)",rows); print(y,len(rows),flush=True)
