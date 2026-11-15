"""USDA NASS Quick Stats API -> county yield (bu/ac) for 4 validation counties, 2001-2025.

Output: /srv/hackathon/data/processed/v1/validation/nass_yield.csv
The API key is read from /srv/hackathon/secrets/nass.key at runtime and never printed (masked in errors).
Withheld/missing years are kept as empty yield_bu_ac. Validation only; no DB writes.
"""

import csv
import datetime as dt
import os
import sys

import requests

KEY_FILE = "/srv/hackathon/secrets/nass.key"
URL = "https://quickstats.nass.usda.gov/api/api_GET/"
OUT = "/srv/hackathon/data/processed/v1/validation/nass_yield.csv"
SOURCE = "USDA NASS Quick Stats API"
COUNTIES = {"19169": ("Story", "IA"), "17113": ("McLean", "IL"), "31109": ("Lancaster", "NE"), "39159": ("Union", "OH")}
COMMODITIES = ["CORN", "SOYBEANS"]  # CORN includes GRAIN (util_practice) via short_desc filter below
YEARS = range(2001, 2026)


def _mask(msg, key):
    return str(msg).replace(key, "***")


def fetch(key, state, county_code, commodity):
    params = {
        "key": key, "format": "JSON", "source_desc": "SURVEY", "sector_desc": "CROPS", "group_desc": "FIELD CROPS",
        "commodity_desc": commodity, "statisticcat_desc": "YIELD", "unit_desc": "BU / ACRE", "agg_level_desc": "COUNTY",
        "state_alpha": state, "county_code": county_code, "year__GE": 2001, "year__LE": 2025, "domain_desc": "TOTAL",
        "freq_desc": "ANNUAL",
    }
    try:
        r = requests.get(URL, params=params, timeout=60)
    except requests.RequestException as e:
        raise SystemExit("request failed: " + _mask(e, key))
    if r.status_code == 400 and "no data" in r.text.lower():
        return []
    if r.status_code != 200:
        raise SystemExit(f"HTTP {r.status_code}: {_mask(r.text[:200], key)}")
    return r.json().get("data", [])


def main():
    key = open(KEY_FILE).read().strip()
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = {}
    for fips, (name, st) in COUNTIES.items():
        for com in COMMODITIES:
            for d in fetch(key, st, fips[2:], com):
                sd = d.get("short_desc", "")
                if com == "CORN" and sd != "CORN, GRAIN - YIELD, MEASURED IN BU / ACRE":
                    continue
                crop = "corn_grain" if com == "CORN" else "soybeans"
                v = d.get("Value", "").replace(",", "").strip()
                try:
                    val = float(v)
                except ValueError:
                    val = None  # (D) withheld etc.
                rows[(fips, crop, int(d["year"]))] = (name, val)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["county_fips", "county", "state", "crop", "year", "yield_bu_ac", "source", "retrieved_utc"])
        for fips, (name, st) in COUNTIES.items():
            for crop in ("corn_grain", "soybeans"):
                for y in YEARS:
                    name_, val = rows.get((fips, crop, y), (name, None))
                    w.writerow([fips, name, st, crop, y, "" if val is None else val, SOURCE, now])
    print("wrote", OUT, "non-missing:", sum(1 for v in rows.values() if v[1] is not None))


if __name__ == "__main__":
    sys.exit(main())
