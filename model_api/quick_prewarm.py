"""Warm the Quick Screen disk cache for 4 preset ~400 m squares centred on demo fields (real network).

Run: python -m model_api.quick_prewarm [API_BASE]   (default API_BASE http://127.0.0.1:8090)
Prints the preset polygons as JSON for the frontend.
"""

from __future__ import annotations

import json
import math
import sys
import urllib.request

from . import quick

COUNTIES = {"19169": "Story IA", "17113": "McLean IL", "31109": "Lancaster NE", "39159": "Union OH"}
HALF_M = 200.0


def square(lon: float, lat: float) -> list[list[float]]:
    dlat = HALF_M / 111_320.0
    dlon = HALF_M / (111_320.0 * math.cos(math.radians(lat)))
    return [[round(lon - dlon, 6), round(lat - dlat, 6)], [round(lon + dlon, 6), round(lat - dlat, 6)],
            [round(lon + dlon, 6), round(lat + dlat, 6)], [round(lon - dlon, 6), round(lat + dlat, 6)]]


def presets(api_base: str) -> list[dict]:
    with urllib.request.urlopen(f"{api_base}/fields", timeout=20) as r:
        fields = json.load(r)["fields"]
    out = []
    for fips, name in COUNTIES.items():
        f = next((x for x in fields if x["county_fips"] == fips), None)
        if f:
            out.append({"name": name, "county_fips": fips, "field_id": f["field_id"], "polygon": square(f["lon"], f["lat"])})
    return out


def main() -> None:
    api = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8090"
    ps = presets(api)
    for p in ps:
        for crops in (["Corn", "Soy"], ["Corn", "Soy", "Wheat"]):
            d = quick.quick_screen(p["polygon"], crops)
            blocks = {k: d[k] is not None for k in ("elevation", "climate_history", "forecast_anomaly", "climate_projection")}
            print(f"{p['name']:<13} {'+'.join(crops):<15} area={d['geometry']['area_ha']} ha blocks={blocks}", file=sys.stderr)
    print(json.dumps(ps, indent=1))


if __name__ == "__main__":
    main()
