"""Load Story County (19169) CSB v2018-2025 rev23 polygons into `fields` (field_id = CSBID, official NASS column). Also builds field_crop_history from CSB CDL20xx columns."""
import pyogrio, psycopg, geopandas as gpd
from shapely.geometry import MultiPolygon
G="/srv/hackathon/data/raw/csb/ext/CSB1825.gdb"
df=pyogrio.read_dataframe(G,where="STATEFIPS='19' AND CNTYFIPS='169'")
print(len(df), df.columns.tolist()[:6])
if len(df)==0:
    df=pyogrio.read_dataframe(G,where="STATEFIPS='19'",max_features=5); print(df.head()); raise SystemExit
g5070=df.geometry
area=g5070.area/1e4
gg=df.to_crs(4326)
gg["geometry"]=gg.geometry.apply(lambda x: x if x.geom_type=="MultiPolygon" else MultiPolygon([x]))
with psycopg.connect("") as c:
    c.execute("delete from field_crop_history; delete from field_soil; delete from fields where county_fips='19169'")
    for (i,r),ar in zip(gg.iterrows(),area):
        c.execute("insert into fields(field_id,csb_version,county_fips,state_alpha,geom,centroid,area_ha,notes) values (%s,%s,'19169','IA',ST_SetSRID(ST_GeomFromWKB(%s),4326),ST_PointOnSurface(ST_SetSRID(ST_GeomFromWKB(%s),4326)),%s,%s)",
            (str(r.CSBID),"CSB 2018-2025 rev23",r.geometry.wkb,r.geometry.wkb,float(ar),"CSB polygon is not an ownership boundary"))
        for y in range(2018,2026):
            v=r[f"CDL{y}"]
            if v==v and v is not None: c.execute("insert into field_crop_history(field_id,year,cdl_class,share) values (%s,%s,%s,NULL)",(str(r.CSBID),y,int(v)))
print("done")
