"""Hit a running model_api for every contrast demo field + two Story fields and print a markdown results table.
Usage: python notebooks/contrast_fields_verify.py [BASE]   (default http://127.0.0.1:8098)."""

import json
import sys

import httpx

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8098").rstrip("/")
STORY = ["191825003869023", "191825002945908"]
c = httpx.Client(base_url=BASE, timeout=120)
fl = {f["field_id"]: f for f in c.get("/fields").json()["fields"]}
ids = STORY + [f for f in fl if not f.startswith("19")]
rows = []
for fid in ids:
    st = {}
    p = c.get(f"/field/{fid}/profile")
    st["profile"] = p.status_code
    prof = p.json()
    cmp_ = c.post("/strategies/compare", json={"field_id": fid, "n": 500, "seed": 42})
    st["compare"] = cmp_.status_code
    comp = {s["strategy_code"]: s["p50"] for s in cmp_.json()["strategies"]}
    sim = c.post("/simulate", json={"field_id": fid, "n": 500, "seed": 42, "scenarios": True})
    st["simulate"] = sim.status_code
    sj = sim.json()
    simp = {s["strategy_code"]: s["composite"]["p50"] for s in sj["strategies"]}
    defm = {s["strategy_code"]: s["metrics"]["season_water_deficit_mm"]["p50"] for s in sj["strategies"]}
    bt = c.get("/validation/backtest", params={"field_id": fid, "year": 2012})
    st["backtest"] = bt.status_code
    btd = {r["strategy_code"]: r["metrics"]["season_water_deficit_mm"] for r in bt.json()["results"]}
    soil = (prof.get("soil") or prof.get("ssurgo") or [{}])
    soil = soil[0] if isinstance(soil, list) and soil else soil
    rows.append(dict(field_id=fid, county=fl[fid]["county_label"], status=st, compare_p50=comp, simulate_p50=simp,
                     mc_deficit_p50=defm, bt2012_deficit=btd, awc=sj["inputs"].get("awc_cm_cm"),
                     kc_scale=sj["inputs"].get("kc_field_scale"), seq_a=next(s["sequence"] for s in sj["strategies"]
                                                                             if s["strategy_code"] == "A")))
json.dump(rows, open("/tmp/fields2/verify.json", "w"), indent=1)
S = "ABCD"
print("| field_id | county | AWC | kc scale | A seq | composite P50 A/B/C/D (compare) | MC deficit P50 mm A/B/C/D | 2012 backtest deficit mm A/B/C/D | HTTP |")
print("|---|---|---|---|---|---|---|---|---|")
for r in rows:
    f = lambda d, n=3: " / ".join("—" if d.get(k) is None else f"{d[k]:.{n}f}" for k in S)  # noqa: E731
    ok = "all 200" if set(r["status"].values()) == {200} else json.dumps(r["status"])
    print(f"| {r['field_id']} | {r['county']} | {r['awc']} | {r['kc_scale']} | {r['seq_a']} | {f(r['compare_p50'])} | "
          f"{f(r['mc_deficit_p50'], 0)} | {f(r['bt2012_deficit'], 0)} | {ok} |")
