"""L3 simulation engine: candidates -> Monte Carlo water balance -> 7-axis rule/index scores -> cards.

No single optimum is returned: ``rank`` is only the display order under the user's slider weights, and
every candidate keeps its full card (why, evidence, benefits, info_gaps, local_review_risks).
No yields in kg/ha or t/ha are produced. CVaR = mean of the worst 10 % of Monte Carlo samples.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import threading
import time
from collections import OrderedDict

import numpy as np

from . import config, hydro, matlab_inputs

CVAR_DEFINITION = "CVaR = mean of the worst 10 % of Monte Carlo samples (lower tail for indices, upper tail for deficits)."

# candidate_id -> (strategy_code, options, sequence, label)
CANDIDATES: dict[str, tuple[str | None, tuple[str, ...], str, str]] = {
    "C-S": ("A", (), "C-S", "Baseline corn-soy"),
    "C-S+cover_rye": ("B", ("cover_rye",), "C-S", "C-S + cereal rye cover"),
    "C-S-W": (None, ("small_grain",), "C-S-W", "C-S-wheat or oats (no cover)"),
    "C-S-W+cover_rye": ("C", ("small_grain", "cover_rye"), "C-S-W", "C-S-wheat or oats + cover"),
    "C-S-Alf": ("D", ("alfalfa",), "C-S-Alf-Alf", "C-S-alfalfa"),
    "C-S-Alf+cover_rye": (None, ("alfalfa", "cover_rye"), "C-S-Alf-Alf", "C-S-alfalfa + cereal rye cover"),
    "C-S-W-Alf": (None, ("small_grain", "alfalfa"), "C-S-W-Alf-Alf", "C-S-wheat-alfalfa"),
    "C-S-W-Alf+cover_rye": (None, ("small_grain", "alfalfa", "cover_rye"), "C-S-W-Alf-Alf", "C-S-wheat-alfalfa + covers"),
}
CODE_TO_CANDIDATE = {v[0]: k for k, v in CANDIDATES.items() if v[0]}


def candidate_for_options(options) -> str:
    o = set(options)
    for cid, (_, opts, _, _) in CANDIDATES.items():
        if set(opts) == o:
            return cid
    raise KeyError(f"no candidate for options {sorted(o)}")


def rotation_candidates(selected: list[str], constraints: dict | None = None) -> list[dict]:
    """All 2^n subsets of the selected options (TEAM_SPEC 2.3)."""
    constraints = constraints or {}
    sel = [o for o in hydro.OPTIONS if o in set(selected)]
    out = []
    for r in range(len(sel) + 1):
        for combo in itertools.combinations(sel, r):
            cid = candidate_for_options(combo)
            code, opts, seq, _ = CANDIDATES[cid]
            warnings = []
            if "alfalfa" in opts and (constraints.get("water_limited") or constraints.get("water_cap_mm")):
                warnings.append("Alfalfa has high seasonal water use; review against the water limit (shown, not hidden).")
            out.append({"candidate_id": cid, "strategy_code": code, "sequence": seq, "options": list(combo),
                        "feasible": True, "warnings": warnings})
    return out


# ---------------------------------------------------------------------------------------------------
# parameters + assumptions
# ---------------------------------------------------------------------------------------------------
class Params:
    def __init__(self, overrides: dict[str, float] | None = None, override_source: str = "calibration") -> None:
        self.values = {k: v[0] for k, v in config.DEFAULTS.items()}
        self.overridden: dict[str, str] = {}
        for k, v in (overrides or {}).items():
            self.values[k] = v
            self.overridden[k] = override_source
        self.used_defaults: set[str] = set()
        self.measured: dict[str, str] = {}

    def set_measured(self, key: str, value, source: str) -> None:
        if value is None:
            return
        self.values[key] = float(value)
        self.measured[key] = source

    def as_dict(self) -> dict:
        return dict(self.values)

    def assumptions(self, keys) -> list[dict]:
        out = []
        for k in keys:
            if k in self.measured or k in self.overridden:
                continue
            v, unit, src = config.DEFAULTS[k]
            out.append({"item": k, "value": self.values[k], "unit": unit, "source": src})
        return out


HYDRO_KEYS = [k for k in config.DEFAULTS if not k.startswith(("ndvi_", "hero_", "heat_"))]


def rule_prior(axis: str, options: tuple[str, ...], overrides: dict[str, float]) -> float:
    pr = {c: overrides.get(f"prior_{axis}_{c}", v) for c, v in config.RULE_PRIORS[axis].items()}
    a = pr["A"]
    d = {"cover_rye": pr["B"] - a, "small_grain": pr["C"] - pr["B"], "alfalfa": pr["D"] - a}
    return float(np.clip(a + sum(d[o] for o in options), 0.0, 1.0))


# ---------------------------------------------------------------------------------------------------
# scenarios (delta method)
# ---------------------------------------------------------------------------------------------------
SEASON_MONTHS = {"MAM": [3, 4, 5], "JJ": [6, 7], "JJA": [6, 7, 8]}


def _clim(ym: dict, months: list[int], var: str) -> float:
    sel = np.isin(hydro.MONTH_OF_DOY, months)
    yrs = (ym["years"] >= config.BASELINE_START_YEAR) & (ym["years"] <= config.BASELINE_END_YEAR)
    return float(ym[var][yrs][:, sel].mean())


def scenario_specs(rows: list[dict], ym: dict) -> tuple[list[hydro.ScenarioSpec], list[str]]:
    notes: list[str] = []
    specs: list[hydro.ScenarioSpec] = []
    s2s = [r for r in rows if r["source_id"] == "geos_s2s"]
    if s2s:
        members: dict[str, dict] = {}
        for r in s2s:
            members.setdefault(r["member"], {})[(r["variable"], r["season"])] = r["value"]
        mem_list = []
        for label, vals in sorted(members.items()):
            ratio, dtx = np.ones(12), np.zeros(12)
            for season in ("MAM", "JJ"):
                months = SEASON_MONTHS[season]
                pr, tas = vals.get(("pr", season)), vals.get(("tas", season))
                if pr is not None:
                    ratio[np.array(months) - 1] = np.clip(pr / max(_clim(ym, months, "precip_mm"), 1e-6), 0.2, 5.0)
                if tas is not None:
                    dtx[np.array(months) - 1] = tas - _clim(ym, months, "t2m_c")
            mem_list.append((label, ratio, dtx.copy(), dtx.copy()))
        year = sorted({r["year"] for r in s2s})
        specs.append(hydro.ScenarioSpec("next_season", "next_season", "geos_s2s", "forecast", mem_list,
                                        period=f"{year[0]}-MAM+JJ" if year else None))
        notes.append("GEOS-S2S next season: member MAM and Jun-Jul means applied as precip ratio / temperature shift vs the "
                     "POWER 1995-2024 climatology of the same months (raw model vs POWER, no hindcast bias correction).")
    else:
        notes.append("GEOS-S2S rows not loaded for this county; next_season scenario skipped.")
    nex = [r for r in rows if r["source_id"] == "nex_gddp"]
    for scen in ("ssp245", "ssp585"):
        models = sorted({r["model"] for r in nex if r["scenario"] == scen})
        mem_list = []
        for m in models:
            def mean(scenario, var, season, m=m):
                v = [r["value"] for r in nex if r["model"] == m and r["scenario"] == scenario and r["variable"] == var
                     and r["season"] == season and r["value"] is not None]
                return float(np.mean(v)) if v else None

            ratio, dtx, dtn = np.ones(12), np.zeros(12), np.zeros(12)
            ok = True
            for season, months in (("ANN", list(range(1, 13))), ("MAM", [3, 4, 5]), ("JJA", [6, 7, 8])):
                idx = np.array(months) - 1
                ph, pf = mean("historical", "pr", season), mean(scen, "pr", season)
                xh, xf = mean("historical", "tasmax", season), mean(scen, "tasmax", season)
                nh, nf = mean("historical", "tasmin", season), mean(scen, "tasmin", season)
                if None in (ph, pf, xh, xf, nh, nf):
                    ok = False
                    break
                ratio[idx] = pf / ph if ph > 0 else 1.0
                dtx[idx], dtn[idx] = xf - xh, nf - nh
            if ok:
                mem_list.append((m, ratio, dtx, dtn))
        if mem_list:
            fut_years = sorted({r["year"] for r in nex if r["scenario"] == scen})
            specs.append(hydro.ScenarioSpec(f"2030s_{scen}", "2030s", "nex_gddp", scen, mem_list,
                                            period=f"{fut_years[0]}-{fut_years[-1]}"))
        else:
            notes.append(f"NEX-GDDP-CMIP6 {scen} rows not loaded for this county; scenario skipped.")
    if nex:
        notes.append("NEX-GDDP-CMIP6 2030s: delta method per model (2031-2040 vs model historical 1985-2014; MAM, JJA, "
                     "else annual) applied to resampled POWER years. Models: "
                     + ", ".join(sorted({r["model"] for r in nex})) + ". Distribution across models, not a forecast.")
    return specs, notes


# ---------------------------------------------------------------------------------------------------
# run + cache
# ---------------------------------------------------------------------------------------------------
_cache: "OrderedDict[str, dict]" = OrderedDict()
_cache_lock = threading.Lock()


def _scores(res: dict, options: tuple[str, ...], kff: float, overrides: dict[str, float], prm: dict) -> dict[str, np.ndarray]:
    """7-axis 0-1 indices per Monte Carlo sample (higher = better). Rules documented in README."""
    precip = np.maximum(res["precip_mm"], 1.0)
    n = precip.shape[-1]
    water = np.clip(1.0 - res["eta_mm"] / precip, 0, 1)
    erosion = np.clip(1.0 - 0.6 * (res["winter_bare_days"] / 181.0) * (kff / 0.28) - 0.4 * (res["runoff_mm"] / (0.1 * precip)), 0, 1)
    om = 0.5 * rule_prior("organic_matter", options, overrides) + 0.5 * np.clip(res["living_cover_days"] / 365.0, 0, 1)
    ncy = 0.5 * rule_prior("n_cycle", options, overrides) + 0.5 * np.clip(
        1.0 - res["offseason_drainage_mm"] / prm["ref_offseason_drainage_mm"], 0, 1)
    full = np.ones(n)
    return {
        "n_cycle_index": ncy,
        "erosion_index": erosion,
        "organic_matter_index": om,
        "pest_break_index": full * rule_prior("pest_break", options, overrides),
        "water_use_index": water,
        "forage_index": full * rule_prior("forage", options, overrides),
        "market_index": full * rule_prior("market", options, overrides),
        "_stability": np.clip(1.0 - res["season_water_deficit_mm"] / np.maximum(res["season_etc_mm"], 1.0), 0, 1) * 0.7
        + 0.3 * rule_prior("pest_break", options, overrides),
    }


def normalize_priorities(pri: dict | None, constraints: dict | None) -> tuple[dict, dict, bool]:
    keys = ("water", "soil", "stability", "income")
    pri = pri or {}
    raw = {k: max(float(pri.get(k, 0.25) or 0.0), 0.0) for k in keys}
    tot = sum(raw.values()) or 1.0
    norm = {k: round(v / tot, 4) if sum(raw.values()) else 0.25 for k, v in raw.items()}
    applied = dict(norm)
    boosted = False
    c = constraints or {}
    if c.get("water_limited") or c.get("water_cap_mm"):
        applied["water"] = applied["water"] * 2 + 0.1
        t = sum(applied.values())
        applied = {k: round(v / t, 4) for k, v in applied.items()}
        boosted = True
    return norm, applied, boosted


def composite(sc: dict[str, np.ndarray], w: dict) -> np.ndarray:
    soil = (sc["erosion_index"] + sc["organic_matter_index"] + sc["n_cycle_index"]) / 3.0
    income = 0.8 * sc["market_index"] + 0.2 * sc["forage_index"]
    return w["water"] * sc["water_use_index"] + w["soil"] * soil + w["stability"] * sc["_stability"] + w["income"] * income


def load_overrides(repo) -> tuple[dict[str, float], list[str]]:
    notes = []
    ov: dict[str, float] = {}
    try:
        ov.update(repo.calibration_params())
    except Exception:
        notes.append("calibration_param table unreadable; defaults used")
    m = matlab_inputs.load()
    ov.update(m["overrides"])
    notes.extend(m["notes"])
    if ov:
        notes.append(f"{len(ov)} calibration parameter(s) override defaults: {', '.join(sorted(ov))}")
    else:
        notes.append("No calibration_param rows (DB or MATLAB CSV): all coefficients are documented defaults")
    return ov, notes


def location_inputs(repo, field_id: str | None, county_fips: str | None) -> dict:
    """Resolve field or county -> weather county, latitude, soil. Raises KeyError for unknown ids."""
    if field_id:
        f = repo.field(field_id)
        if not f:
            raise KeyError("Unknown field_id")
        fips = f["county_fips"].strip()
        lat = f["centroid"]["coordinates"][1] if f.get("centroid") else repo.county(fips)["lat"]
        soil_rows = repo.soil(field_id)
        tier = "field"
    else:
        c = repo.county(county_fips or "")
        if not c:
            raise KeyError("Unknown county_fips")
        f = None
        fips, lat, soil_rows, tier = c["county_fips"], c["lat"], [], "county"

    def wavg(key):
        vals = [(r[key], r.get("comppct_r") or 1.0) for r in soil_rows if r.get(key) is not None]
        if not vals:
            return None
        return sum(v * w for v, w in vals) / sum(w for _, w in vals)

    soil = {"awc_cm_cm": wavg("awc_cm_cm"), "kffact": wavg("kffact"), "om_pct": wavg("om_pct"),
            "drainagecl": next((r["drainagecl"] for r in soil_rows if r.get("drainagecl")), None),
            "mukey": [r["mukey"] for r in soil_rows]}
    return {"field": f, "county_fips": fips, "lat": float(lat), "soil": soil, "tier": tier}


def simulate(repo, *, field_id: str | None = None, county_fips: str | None = None, n: int = 500, seed: int = 42,
             candidate_ids: list[str] | None = None, priorities: dict | None = None, constraints: dict | None = None,
             scenarios: bool = True) -> dict:
    t0 = time.perf_counter()
    loc = location_inputs(repo, field_id, county_fips)
    cids = candidate_ids or [CODE_TO_CANDIDATE[c] for c in "ABCD"]
    for c in cids:
        if c not in CANDIDATES:
            raise ValueError(f"Unknown candidate_id {c!r}")
    if "C-S" not in cids:
        cids = ["C-S"] + list(cids)  # baseline A is always included (relative % need it)
    n = int(min(max(n, 50), 5000))
    overrides, notes = load_overrides(repo)
    prm = Params(overrides)
    src_soil = "SSURGO SDA field_soil (area-dominant mapunit)"
    prm.set_measured("awc_cm_cm", loc["soil"]["awc_cm_cm"], src_soil)
    prm.set_measured("kffact", loc["soil"]["kffact"], src_soil)
    info_gaps: list[str] = []
    if loc["tier"] == "county":
        info_gaps.append("Tier 1 county run: no field polygon or SSURGO soil loaded for this county; soil defaults used.")
    elif loc["soil"]["awc_cm_cm"] is None:
        info_gaps.append("SSURGO AWC missing for this field's mapunit; default used.")

    key = hashlib.sha1(json.dumps([loc["county_fips"], round(loc["lat"], 3), prm.values, n, seed, cids, scenarios],
                                  sort_keys=True, default=str).encode()).hexdigest()[:16]
    with _cache_lock:
        cached = _cache.get(key)
    if cached is None:
        wx = repo.weather_daily(loc["county_fips"])
        if wx is None:
            raise LookupError("No POWER daily weather loaded for this county")
        ym = hydro.to_year_matrix(wx)
        specs = [hydro.historical_spec()]
        scen_notes: list[str] = []
        if scenarios:
            extra, scen_notes = scenario_specs(repo.scenario_year(loc["county_fips"]), ym)
            specs += extra
        cycles = [hydro.cycle_for(CANDIDATES[c][1]) for c in cids]
        mc = hydro.run_mc(ym, specs, cycles, prm.as_dict(), loc["lat"], n, seed)
        cached = {"mc": mc, "specs": specs, "scen_notes": scen_notes, "years": [int(ym["years"][0]), int(ym["years"][-1])],
                  "n_filled": ym["n_filled"]}
        with _cache_lock:
            _cache[key] = cached
            while len(_cache) > 64:
                _cache.popitem(last=False)
    mc, specs = cached["mc"], cached["specs"]
    hist = mc["results"]["historical"]
    norm, applied, boosted = normalize_priorities(priorities, constraints)
    kff = prm.values["kffact"]

    rows = []
    a_idx = cids.index("C-S")
    for i, cid in enumerate(cids):
        code, opts, seq, label = CANDIDATES[cid]
        res = {m: hist[m][i] for m in hydro.METRICS}
        sc = _scores(res, opts, kff, overrides, prm.values)
        comp = composite(sc, applied)
        metrics = {m: {"unit": "days/yr" if m.endswith("days") else "mm/yr",
                       **hydro.quantiles(res[m], higher_is_better=m in ("living_cover_days", "veg_index_days", "precip_mm"))}
                   for m in hydro.METRICS}
        a_res = {m: hist[m][a_idx] for m in hydro.METRICS}

        def rel(metric):
            x = (res[metric] / np.maximum(a_res[metric], 1e-6) - 1.0) * 100.0
            q = np.percentile(x, [10, 50, 90])
            return {"p10": round(float(q[0]), 1), "p50": round(float(q[1]), 1), "p90": round(float(q[2]), 1)}

        scen_results = []
        for ci, spec in enumerate(specs):
            r = mc["results"][spec.name]
            q = hydro.quantiles(r["season_water_deficit_mm"][i], higher_is_better=False)
            item = {"horizon": spec.horizon or "historical", "source_id": spec.source_id, "metric": "season_water_deficit_mm",
                    "unit": "mm/yr", **q, "n_members": len(spec.members), "period": spec.period}
            if spec.scenario and spec.scenario.startswith("ssp"):
                item["scenario"] = spec.scenario
            scen_results.append(item)
        warnings = []
        cap = (constraints or {}).get("water_cap_mm")
        if cap and metrics["season_etc_mm"]["p50"] > float(cap):
            warnings.append(f"Seasonal crop water demand P50 {metrics['season_etc_mm']['p50']} mm exceeds water_cap_mm {cap}.")
        rows.append({
            "candidate_id": cid, "strategy_code": code, "label": label, "sequence": seq, "options": list(opts),
            "cycle": [list(x) for x in hydro.cycle_for(opts)],
            "metrics": metrics,
            "scores": {k: round(float(np.median(v)), 3) for k, v in sc.items() if not k.startswith("_")},
            "stability_index": round(float(np.median(sc["_stability"])), 3),
            "composite": hydro.quantiles(comp, higher_is_better=True),
            "display": {"vegetation_pct": rel("veg_index_days"), "water_use_pct": rel("eta_mm"),
                        "revenue_pct": {"p10": None, "p50": None, "p90": None},
                        "basis": "relative index change vs strategy A; not a guarantee"},
            "scenario_results": scen_results,
            "warnings": warnings,
            "_sc": sc,
        })
    order = sorted(range(len(rows)), key=lambda j: -rows[j]["composite"]["p50"])
    for rnk, j in enumerate(order, start=1):
        rows[j]["rank"] = rnk
    _goal_labels(rows, applied)

    assumptions = prm.assumptions(HYDRO_KEYS)
    assumptions.append({"item": "crop_calendar", "value": None, "unit": None, "source": hydro.CROP_DATES_NOTE})
    assumptions.append({"item": "small_grain", "value": None, "unit": None,
                        "source": "small grain modelled as winter wheat; oats not modelled separately"})
    assumptions.append({"item": "rule_priors", "value": config.RULE_PRIORS, "unit": "index_0_1",
                        "source": "team default rule scores (qualitative ranking from PRD 4); not measured. "
                                  "pest_break, forage, market are rule-only; n_cycle and organic_matter blend rule + MC."})
    assumptions.append({"item": "hydrologic_soil_group", "value": "B", "unit": None,
                        "source": "HSG not loaded; TR-55 group B curve numbers"})
    assumptions.append({"item": "weather", "value": f"{cached['years'][0]}-{cached['years'][1]}", "unit": None,
                        "source": f"NASA POWER daily at county representative point ({loc['county_fips']}); "
                                  f"{cached['n_filled']} missing values filled by day-of-year mean; ET0 by FAO-56 Penman-Monteith"})
    info_gaps += [
        "In-field soil test not provided",
        "Crop prices not loaded: revenue_pct left empty (no yields in kg/ha or t/ha are produced)",
        "County IMERG rows not loaded: POWER precipitation used for the water balance",
        "Tile drainage and irrigation not modelled",
    ]
    out = {
        "run_id": f"mc-{key}-n{n}-s{seed}",
        "field_id": loc["field"]["field_id"] if loc["field"] else None,
        "county_fips": loc["county_fips"],
        "tier": loc["tier"],
        "n": n,
        "seed": seed,
        "period": {"start": f"{cached['years'][0]}-01-01", "end": f"{cached['years'][1]}-12-31"},
        "unit": "index_0_1",
        "cvar_definition": CVAR_DEFINITION,
        "inputs": {"lat": round(loc["lat"], 5), "awc_cm_cm": prm.values["awc_cm_cm"], "kffact": kff,
                   "om_pct": loc["soil"]["om_pct"], "drainagecl": loc["soil"]["drainagecl"], "mukey": loc["soil"]["mukey"]},
        "priorities_normalized": norm,
        "weights_applied": applied,
        "water_weight_boosted": boosted,
        "strategies": rows,
        "assumptions": assumptions,
        "notes": notes + cached["scen_notes"],
        "info_gaps": info_gaps,
        "disclaimer": config.DISCLAIMER_COMPARE,
        "latency_ms": None,
    }
    out["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    return out


GOALS = {"water": "Water saving", "soil": "Soil health", "stability": "Stability / resilience", "income": "Income / market fit"}


def _goal_labels(rows: list[dict], w: dict) -> None:
    """Give every tab a distinct goal label = the priority group where it stands out most (greedy, unique)."""
    groups = {}
    for r in rows:
        s = r["_sc"]
        groups[r["candidate_id"]] = {
            "water": float(np.median(s["water_use_index"])),
            "soil": float(np.median((s["erosion_index"] + s["organic_matter_index"] + s["n_cycle_index"]) / 3)),
            "stability": float(np.median(s["_stability"])),
            "income": float(np.median(0.8 * s["market_index"] + 0.2 * s["forage_index"])),
        }
    adv = []
    for cid, g in groups.items():
        for k, v in g.items():
            others = [groups[o][k] for o in groups if o != cid]
            adv.append((v - (np.mean(others) if others else 0.0), cid, k))
    taken_c, taken_g = {"C-S"}, set()
    next(r for r in rows if r["candidate_id"] == "C-S")["goal_label"] = "Current practice (baseline)"
    for _, cid, k in sorted(adv, reverse=True):
        if cid in taken_c or (k in taken_g and len(taken_g) < min(len(GOALS), len(rows) - 1)):
            continue
        taken_c.add(cid)
        taken_g.add(k)
        next(r for r in rows if r["candidate_id"] == cid)["goal_label"] = GOALS[k]
    for r in rows:
        r.setdefault("goal_label", GOALS["income"])
        r["group_scores"] = {k: round(v, 3) for k, v in groups[r["candidate_id"]].items()}


def backtest_year(repo, field_id: str, year: int) -> dict[str, dict]:
    """Deterministic one-year water balance for A-D driven by the actual POWER weather of ``year``.

    The rotation phase of each strategy is set so that the scored year's cash crop equals the CDL crop
    observed on the field that year (corn or soybean); other years fall back to phase 0.
    """
    loc = location_inputs(repo, field_id, None)
    overrides, _ = load_overrides(repo)
    prm = Params(overrides)
    prm.set_measured("awc_cm_cm", loc["soil"]["awc_cm_cm"], "ssurgo")
    prm.set_measured("kffact", loc["soil"]["kffact"], "ssurgo")
    ym = hydro.to_year_matrix(repo.weather_daily(loc["county_fips"]))
    yrs = list(ym["years"])
    if year not in yrs or (year - 1) not in yrs:
        raise ValueError(f"year must be within {yrs[1]}-{yrs[-1]} (needs the previous year as spin-up)")
    hist = {h["year"]: h["crop_name"] for h in repo.crop_history(field_id)}
    obs = {"Corn": "corn", "Soybeans": "soy"}.get(hist.get(year))
    codes = list("ABCD")
    cycles = [hydro.cycle_for(CANDIDATES[CODE_TO_CANDIDATE[c]][1]) for c in codes]
    phases = []
    for cyc in cycles:
        L = len(cyc)
        ph = next((p for p in range(L) if cyc[(p + 1) % L][0] == obs), 0) if obs else 0
        phases.append([ph])
    draws = np.array([[yrs.index(year - 1), yrs.index(year)]])
    mc = hydro.run_mc(ym, [hydro.historical_spec()], cycles, prm.as_dict(), loc["lat"], 1, 0,
                      year_draws=draws, phases=np.array(phases), n_scored=1)
    res = mc["results"]["historical"]
    out = {}
    for i, c in enumerate(codes):
        cyc = cycles[i]
        out[c] = {m: round(float(res[m][i][0]), 1) for m in hydro.METRICS}
        out[c]["modelled_crop"] = cyc[(phases[i][0] + 1) % len(cyc)][0]
        out[c]["unit"] = "mm or days in the scored year"
    return out
