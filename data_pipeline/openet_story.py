"""OpenET Ensemble monthly ET (mm) at centroids of N demo fields in Story County (point endpoint). Key from env OPENET_API_KEY (never logged). Stores field_et_openet."""
import os, time, json, requests, psycopg
OUT="/srv/hackathon/data/raw/openet/tier2_story"; os.makedirs(OUT,exist_ok=True)
H={"Authorization":os.environ["OPENET_API_KEY"],"Content-Type":"application/json","accept":"application/json"}
with psycopg.connect("") as c:
    fl=c.execute("""select f.field_id,ST_X(centroid),ST_Y(centroid) from fields f
      join (select field_id from field_crop_history where cdl_class in (1,5) group by 1 having count(*)=8) k using(field_id)
      where area_ha between 25 and 80 order by md5(f.field_id) limit 12""").fetchall()
    rows=[]
    for fid,lon,lat in fl:
        for y0,y1 in [(2016,2017),(2018,2022),(2023,2025)]:
            b={"date_range":[f"{y0}-01-01",f"{y1}-12-31"],"interval":"monthly","geometry":[round(lon,5),round(lat,5)],"model":"Ensemble","variable":"ET","reference_et":"gridMET","units":"mm","file_format":"JSON"}
            time.sleep(0.6)
            r=requests.post("https://openet-api.org/raster/timeseries/point",headers=H,json=b,timeout=180)
            if r.status_code!=200: print(fid,y0,r.status_code,r.text[:150]); continue
            open(f"{OUT}/{fid}_{y0}.json","w").write(r.text)
            for d in r.json(): rows.append((fid,d["time"],"et_ensemble_mm",d["et"],"mm","OpenET Ensemble monthly, point at CSB centroid, gridMET ref"))
    c.execute("delete from field_et_openet")
    c.cursor().executemany("insert into field_et_openet values (%s,%s,%s,%s,%s,%s) on conflict do nothing",rows)
    print(len(fl),"fields",len(rows),"rows")
