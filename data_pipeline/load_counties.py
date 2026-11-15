"""Load Census cb_2023_us_county_500k for the 12 Corn Belt states into `county`. Source: US Census Bureau cartographic boundary (public domain)."""
import zipfile, sys, geopandas as gpd, psycopg
Z="/srv/hackathon/data/raw/census/cb/c.zip"
STATES={"19":"IA","17":"IL","18":"IN","39":"OH","31":"NE","27":"MN","46":"SD","55":"WI","29":"MO","20":"KS","26":"MI","21":"KY"}
g=gpd.read_file(f"zip://{Z}")
g=g[g.STATEFP.isin(STATES)].to_crs(4326)
g["geom"]=g.geometry.apply(lambda x: x if x.geom_type=="MultiPolygon" else __import__("shapely").geometry.MultiPolygon([x]))
a=g.to_crs(5070).area/1e6
with psycopg.connect("") as c:
    c.execute("truncate county")
    for (i,r),ar in zip(g.iterrows(),a):
        c.execute("insert into county(county_fips,state_alpha,name,geom,centroid,area_km2) values(%s,%s,%s,ST_SetSRID(ST_GeomFromWKB(%s),4326),ST_PointOnSurface(ST_SetSRID(ST_GeomFromWKB(%s),4326)),%s)",
          (r.GEOID,STATES[r.STATEFP],r.NAME,r.geom.wkb,r.geom.wkb,float(ar)))
print(len(g))
