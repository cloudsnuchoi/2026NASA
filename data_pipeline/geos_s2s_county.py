"""GEOS-S2S-3 NRT APCN 202611 (NCCS datashare, public) -> county_scenario_year (model GEOS-S2S-3, scenario 'forecast', source_id 'geos_s2s').
Extracts nearest 0.5 deg cell to each county representative point; only members with the 9-month length (time Nov-2026..Jul-2027) give 2027 seasons.
Seasons: MAM (mean Mar-May 2027), JJ (mean Jun-Jul 2027; August is NOT in the 9-month files -> not JJA). member = '<initdate>ens<N>'.
precip PRECTOTCORR kg m-2 s-1 -> mm/day; temperature variable name is read from the file (K -> degC). Usage: geos_s2s_county.py precip|at"""
import sys, glob, os, numpy as np, xarray as xr, psycopg
kind=sys.argv[1]; D="/srv/hackathon/data/raw/geos_s2s/tier2_story/x_"+kind
with psycopg.connect("") as c:
    pts=c.execute("select county_fips,ST_X(centroid),ST_Y(centroid) from county order by 1").fetchall()
fips=[p[0] for p in pts]; plon=np.array([p[1] for p in pts]); plat=np.array([p[2] for p in pts])
rows=[]; info=[]
for f in sorted(glob.glob(D+"/*9mo.nc4")):
    d=xr.open_dataset(f); var=list(d.data_vars)[0]
    if d.time.size<9: continue
    v=d[var]
    if "lev" in v.dims: v=v.isel(lev=0)
    ilat=np.abs(d.lat.values[None,:]-plat[:,None]).argmin(1); ilon=np.abs(d.lon.values[None,:]-plon[:,None]).argmin(1)
    a=v.values[:,ilat,ilon].astype("float64")   # (time, county)
    mon=[(t.year,t.month) for t in d.time.to_index()]
    if kind=="precip": a=a*86400; unit="mm/day"; vn="pr"
    else: unit=d[var].attrs.get("units","?"); vn="tas"; a=a-273.15 if np.nanmean(a)>200 else a; unit="degC"
    member=os.path.basename(f).split(".")[2]+"."+os.path.basename(f).split(".")[3]
    member=member.split(".")[0]
    for season,ms in [("MAM",[(2027,3),(2027,4),(2027,5)]),("JJ",[(2027,6),(2027,7)])]:
        ix=[i for i,m in enumerate(mon) if m in ms]; s=a[ix].mean(0)
        rows+=[(fc,"geos_s2s","GEOS-S2S-3","forecast",member,vn,season,2027,float(x),unit) for fc,x in zip(fips,s)]
    info.append((os.path.basename(f),var,d.time.size))
print(info[:2],len(info),"members")
with psycopg.connect("") as c:
    c.execute("delete from county_scenario_year where source_id='geos_s2s' and variable=%s",("pr" if kind=="precip" else "tas",))
    with c.cursor() as cur:
        with cur.copy("copy county_scenario_year(county_fips,source_id,model,scenario,member,variable,season,year,value,unit) from stdin") as cp:
            for r in rows: cp.write_row(r)
print("rows",len(rows))
