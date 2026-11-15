"""NASS bulk QuickStats crops file (keyless) -> county corn-grain / soybean yield (bu/ac), 12 Corn Belt states, 2008-2025 -> county_yield. Source: USDA NASS Quick Stats."""
import gzip, csv, psycopg, sys
F="/srv/hackathon/data/raw/nass_bulk/qs.crops_20261103.txt.gz"
ST={"IA","IL","IN","OH","NE","MN","SD","WI","MO","KS","MI","KY"}
want={"CORN, GRAIN - YIELD, MEASURED IN BU / ACRE":"corn","SOYBEANS - YIELD, MEASURED IN BU / ACRE":"soybeans"}
out={}
with gzip.open(F,"rt",encoding="utf-8",errors="replace") as f:
    r=csv.DictReader((l.replace("\0","") for l in f),delimiter="\t")
    for x in r:
        if x["AGG_LEVEL_DESC"]!="COUNTY" or x["STATE_ALPHA"] not in ST or x["SOURCE_DESC"]!="SURVEY" or x["FREQ_DESC"]!="ANNUAL": continue
        c=want.get(x["SHORT_DESC"]); 
        if not c or x["DOMAIN_DESC"]!="TOTAL": continue
        y=int(x["YEAR"]); 
        if y<2008: continue
        v=x["VALUE"].replace(",","").strip()
        try: val=float(v)
        except: continue   # (D), (Z) suppressed -> not loaded (NULL by absence)
        if not x["COUNTY_CODE"] or x["COUNTY_CODE"]=="998": continue
        out[(x["STATE_FIPS_CODE"].zfill(2)+x["COUNTY_CODE"].zfill(3),y,c)]=val
with psycopg.connect("") as c:
    c.execute("delete from county_yield")
    c.cursor().executemany("insert into county_yield values (%s,%s,%s,%s,'USDA NASS Quick Stats bulk qs.crops_20261103')",[(k[0],k[1],k[2],v) for k,v in out.items()])
print(len(out))
