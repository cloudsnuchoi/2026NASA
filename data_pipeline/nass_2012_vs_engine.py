"""2012 NASS yield anomaly vs engine 2012 season water deficit (strategy A, county field mean). Validation only."""

import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

V = "/srv/hackathon/data/processed/v1"
y = pd.read_csv(f"{V}/validation/nass_yield.csv", dtype={"county_fips": str})
dfc = pd.read_csv(f"{V}/matlab/inputs/engine_2012_deficit.csv", dtype={"field_id": str})
fl = pd.read_csv(f"{V}/matlab/inputs/fields_20.csv", dtype={"field_id": str, "county_fips": str})
a = dfc[dfc.strategy_code == "A"].merge(fl[["field_id", "county_fips"]], on="field_id")
eng = a.groupby("county_fips").season_water_deficit_mm.agg(["mean", "count"]).rename(columns={"mean": "deficit_mm", "count": "n_fields"})
rows = []
for (f, c, crop), g in y.groupby(["county_fips", "county", "crop"]):
    base = g[(g.year != 2012) & (g.year <= 2024)].yield_bu_ac.dropna()
    v = g[g.year == 2012].yield_bu_ac.iloc[0]
    rows.append(dict(county_fips=f, county=c, crop=crop, y2012=v, baseline=base.mean(), n_base=len(base)))
t = pd.DataFrame(rows)
t["pct"] = (t.y2012 / t.baseline - 1) * 100
t = t.merge(eng, on="county_fips", how="left")
t.to_csv("docs/validation/nass_2012_table.csv", index=False)
print(t.round(1).to_string())
stats = {}
fig, ax = plt.subplots(figsize=(7, 4.5))
for crop, col, mk in (("corn_grain", "#c0392b", "o"), ("soybeans", "#2874a6", "s")):
    s = t[t.crop == crop]
    ax.scatter(s.deficit_mm, s.pct, c=col, marker=mk, s=60, label=crop.replace("_grain", ""))
    for _, r in s.iterrows():
        ax.annotate(r.county, (r.deficit_mm, r.pct), textcoords="offset points", xytext=(5, 4), fontsize=8)
    stats[crop] = s.deficit_mm.corr(s.pct)
ax.set_xlabel("Engine 2012 season water deficit, strategy A (mm, field mean per county)")
ax.set_ylabel("NASS 2012 yield vs 2001-24 mean excl. 2012 (%)")
ax.set_title("n = 4 counties per crop; yield is not the engine objective", fontsize=9)
ax.axhline(0, c="grey", lw=0.5)
ax.legend()
fig.tight_layout()
fig.savefig("docs/validation/nass_2012_vs_engine.png", dpi=150)
print(stats)
