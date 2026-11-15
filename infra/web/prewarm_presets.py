"""Warm the /quick disk cache for the 4 pilot-county presets exactly as the frontend sends them.

Usage: /srv/hackathon/venv-api/bin/python infra/web/prewarm_presets.py [http://127.0.0.1:8095]
"""

import json
import math
import sys
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8095").rstrip("/")
COUNTIES = ["19169", "17113", "31109", "39159"]
CROPSETS = [["Corn", "Soy"], ["Corn", "Soy", "Wheat"], ["Corn", "Wheat"], ["Soy", "Wheat"]]


def get(path):
    return json.load(urllib.request.urlopen(BASE + path, timeout=120))


def post(path, body):
    req = urllib.request.Request(BASE + path, json.dumps(body).encode(), {"content-type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=180))


def simplify(pts, n=60):  # same rule as frontend/app.js
    if len(pts) <= n:
        return pts
    s = math.ceil(len(pts) / n)
    return [p for i, p in enumerate(pts) if i % s == 0]


fields = get("/api/fields-geo")["fields"]
for fips in COUNTIES:
    f = next(x for x in fields if x["county_fips"] == fips)
    for crops in CROPSETS:
        r = post("/api/quick", {"polygon": simplify(f["ring"]), "crops": crops})
        print(fips, f["field_id"], crops, "gaps:", len(r["info_gaps"]),
              "nulls:", [k for k in ("elevation", "climate_history", "forecast_anomaly", "climate_projection") if r[k] is None])
