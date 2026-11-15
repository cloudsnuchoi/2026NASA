"""CDL 30 m county clips from CropScape (GetCDLFile by FIPS), 2008-2025, for tier-2 contrast counties.
Usage: cdl_cropscape_county.py FIPS [FIPS...]. Writes raw/cdl/tier2_<fips>/cdl_<yr>_<fips>.tif. <=1 req/s. Cite USDA NASS CDL / CropScape."""

import os
import re
import sys
import time

import requests

R = "/srv/hackathon/data/raw/cdl"
S = "https://nassgeodata.gmu.edu/axis2/services/CDLService/GetCDLFile"
for fips in sys.argv[1:]:
    d = f"{R}/tier2_{fips}"
    os.makedirs(d, exist_ok=True)
    for y in range(2008, 2026):
        out = f"{d}/cdl_{y}_{fips}.tif"
        if os.path.exists(out) and os.path.getsize(out) > 1000:
            continue
        for attempt in range(4):
            try:
                time.sleep(1.0)
                x = requests.get(S, params={"year": y, "fips": fips}, timeout=180).text
                url = re.search(r"<returnURL>(.*?)</returnURL>", x).group(1)
                time.sleep(1.0)
                b = requests.get(url, timeout=300)
                b.raise_for_status()
                open(out, "wb").write(b.content)
                print(fips, y, len(b.content), flush=True)
                break
            except Exception as e:
                print(fips, y, "retry", attempt, repr(e)[:120], flush=True)
                time.sleep(5)
