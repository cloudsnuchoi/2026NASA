"""Build MAT4 validation inputs: NASS county yield 2008-2023 (+ pct vs county mean) and engine deficit per county-year.

Inputs (no network, no engine change): validation/nass_yield.csv (NASS Quick Stats, already fetched by
nass_yield_validation.py for all 4 pilot counties 2001-2025) and matlab/inputs/engine_p90_years.csv
(API strategy A scored-year deficit per field-year). Missing yields stay empty.
"""
import pandas as pd

V1 = "/srv/hackathon/data/processed/v1"
n = pd.read_csv(f"{V1}/validation/nass_yield.csv")
n = n[(n.year >= 2008) & (n.year <= 2023)].copy()
n["crop"] = n.crop.map({"corn_grain": "corn", "soybeans": "soybean"})
n["county_mean_2008_2023"] = n.groupby(["county_fips", "crop"]).yield_bu_ac.transform("mean")
n["yield_change_pct"] = (n.yield_bu_ac / n.county_mean_2008_2023 - 1) * 100
n = n[["county_fips", "county", "state", "crop", "year", "yield_bu_ac", "county_mean_2008_2023", "yield_change_pct", "source"]]
n.round(3).to_csv(f"{V1}/validation/nass_yield_multi.csv", index=False)

e = pd.read_csv(f"{V1}/matlab/inputs/engine_p90_years.csv")
e = e[(e.year >= 2008) & (e.year <= 2023)]
g = e.groupby(["county_fips", "year"]).season_water_deficit_mm.agg(["mean", "count"]).reset_index()
g.columns = ["county_fips", "year", "engine_deficit_mm", "n_fields"]
g["source"] = "engine_p90_years.csv: API strategy A scored-year season deficit, mean over pilot fields in county"
g.round(2).to_csv(f"{V1}/validation/engine_deficit_county_year.csv", index=False)
print(len(n), len(g))
