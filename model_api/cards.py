"""Strategy cards (why, evidence, benefits, info_gaps, local_review_risks) + pros/cons/unique_feature.

All numbers in card text come from the Monte Carlo output of the same run (P50 unless stated).
"""

from __future__ import annotations

from . import config

ALFALFA_WATER_RISK = "High water use is a material risk in western/irrigated settings and must be reviewed locally."

EVIDENCE_TERMS = {"cover_rye": "cereal rye cover", "small_grain": "small grain rotation", "alfalfa": "alfalfa"}


def _m(row, metric, q="p50"):
    return row["metrics"][metric][q]


def _fmt(x, nd=0):
    return f"{x:.{nd}f}"


def _data_evidence(tier: str) -> list[dict]:
    ev = [
        {"doi": None, "url": config.DATA_SOURCE_URLS["POWER"], "quote": "Climate inputs from NASA POWER daily (county representative point)."},
        {"doi": None, "url": config.FAO56_URL, "quote": "Reference ET and crop coefficients follow FAO-56 (Allen et al. 1998)."},
    ]
    if tier == "field":
        ev.append({"doi": None, "url": config.DATA_SOURCE_URLS["SSURGO"], "quote": "Soil available water capacity and K factor from SSURGO (NRCS)."})
        ev.append({"doi": None, "url": config.DATA_SOURCE_URLS["CDL"], "quote": "Field crop history from USDA NASS Cropland Data Layer."})
    return ev


def build(sim: dict, evidence_lookup=None) -> list[dict]:
    """Attach card fields to each strategy row of a simulate() result (in place) and return rows."""
    rows = sim["strategies"]
    a = next(r for r in rows if r["candidate_id"] == "C-S")
    tier = sim["tier"]
    base_gaps = list(sim["info_gaps"])
    used_keys: set[str] = set()
    used_texts: set[str] = set()
    # fewer options first so single-option tabs keep their signature pros; later tabs get different ones
    for r in sorted(rows, key=lambda x: (len(x["options"]), x["candidate_id"])):
        opts = set(r["options"])
        bare_a, bare = _m(a, "winter_bare_days"), _m(r, "winter_bare_days")
        drain_a, drain = _m(a, "offseason_drainage_mm"), _m(r, "offseason_drainage_mm")
        eta_a, eta = _m(a, "eta_mm"), _m(r, "eta_mm")
        def_a, deficit = _m(a, "season_water_deficit_mm"), _m(r, "season_water_deficit_mm")
        etc = _m(r, "season_etc_mm")
        run_a, run = _m(a, "runoff_mm"), _m(r, "runoff_mm")
        pros: list[tuple[str, str]] = []
        cons: list[str] = []
        risks: list[str] = []
        if not opts:
            why = "Current convention on this field (CDL history shows corn-soybean)."
            min_eta = min(_m(x, "eta_mm") for x in rows)
            pros = [
                ("a_equipment", "Matches existing equipment, seed and grain markets; no new management to learn"),
                ("a_water", f"Lowest annual crop water use of the compared options in this run ({_fmt(eta)} mm/yr ET, P50)"
                 if eta <= min_eta else "No cover or extra crop to establish: lowest seed and field-operation needs"),
                ("a_yield", "County corn and soybean yields are published by USDA NASS for local benchmarking"),
            ]
            cons = [f"Bare soil about {_fmt(bare)} days between November and April each year (P50), exposing soil to erosion"]
            unique = "The reference every other tab is measured against (all % are relative to this tab)."
            risks = ["Winter bare-ground erosion exposure", "Nitrate leaching in wet springs with no living roots"]
        else:
            parts = []
            if "cover_rye" in opts:
                parts.append("a winter cereal rye cover keeps living roots over winter")
                pros.append(("bare", f"Cuts winter bare-ground days from {_fmt(bare_a)} to {_fmt(bare)} per year (P50 vs A)"))
                if drain < drain_a:
                    pros.append(("drain", f"Less off-season drainage (nitrate-leaching proxy): {_fmt(drain)} vs {_fmt(drain_a)} mm/yr for A (P50)"))
                cons.append(f"The cover uses water: annual ET {_fmt(eta)} vs {_fmt(eta_a)} mm/yr for A (P50); "
                            "terminate early before corn in dry springs")
                risks.append("Cereal rye termination timing and possible corn yield drag must be checked with local agronomists")
            if "small_grain" in opts:
                parts.append("a small grain adds a third crop family that breaks corn-soybean pest cycles")
                if deficit < def_a:
                    pros.append(("deficit", f"Lower growing-season water deficit: {_fmt(deficit)} vs {_fmt(def_a)} mm/yr for A (P50); "
                                 "the small grain uses spring moisture before summer drought"))
                pros.append(("pest", "Adds a third crop family, interrupting corn rootworm and soybean cyst nematode cycles"))
                cons.append("Small-grain markets are thinner than corn/soybean in central Iowa; check local buyers and contracts")
                risks.append("Small-grain harvest equipment, storage and local market access")
            if "alfalfa" in opts:
                parts.append("alfalfa adds deep roots, nitrogen fixation and forage")
                pros.append(("legume", "Perennial legume: fixes nitrogen and provides forage for livestock or hay sales"))
                pros.append(("deep", f"Deep roots (default 1.5 m) reach subsoil water; growing-season deficit {_fmt(deficit)} "
                             f"vs {_fmt(def_a)} mm/yr for A (P50)"))
                cons.append(f"Highest seasonal crop water demand of the options here ({_fmt(etc)} mm/yr, P50); "
                            "soil profile is left drier for the next corn")
                risks.append(ALFALFA_WATER_RISK)
                risks.append("Hay market, livestock outlet and establishment risk must be reviewed locally")
            why = "Adds to the current rotation: " + "; ".join(parts) + "."
            if run < run_a:
                pros.append(("runoff", f"Less surface runoff than A ({_fmt(run)} vs {_fmt(run_a)} mm/yr, P50)"))
            if len(opts) > 1:
                pros.append(("combo", f"Combines {len(opts)} changes: living cover {_fmt(_m(r, 'living_cover_days'))} days/yr (P50)"))
            unique = {
                frozenset({"cover_rye"}): "Only option that keeps the corn-soybean cash sequence unchanged while covering the soil all winter.",
                frozenset({"small_grain"}): "Third crop family without a cover crop: the simplest diversification step.",
                frozenset({"small_grain", "cover_rye"}): "Three crop families plus a cover after the small grain: most diversity per year.",
                frozenset({"alfalfa"}): "Only option with a perennial legume (multi-year living roots and forage).",
            }.get(frozenset(opts), "Combination of " + ", ".join(sorted(opts)) + ".")
        # exactly 3 pros; a pro template (key) is used by at most one tab
        chosen = [(k, t) for k, t in pros if k not in used_keys]
        fillers = [
            ("living", f"Living cover {_fmt(_m(r, 'living_cover_days'))} days/yr in this run (P50)"),
            ("cvar", f"Seasonal water-deficit CVaR {_fmt(r['metrics']['season_water_deficit_mm']['cvar'])} mm/yr (worst 10 % of samples)"),
            ("erosion", f"Erosion index {r['scores']['erosion_index']} vs {a['scores']['erosion_index']} for A (P50)"),
            ("om", f"Organic-matter index {r['scores']['organic_matter_index']} vs {a['scores']['organic_matter_index']} for A (P50)"),
            ("composite", f"Composite index P50 {r['composite']['p50']} under your weights"),
        ]
        for k, t in fillers:
            if len(chosen) >= 3:
                break
            if k not in used_keys and k not in {c[0] for c in chosen}:
                chosen.append((k, t))
        # more than 4 candidates (n=3 options): templates may repeat, but never the same sentence
        for k, t in pros + fillers:
            if len(chosen) >= 3:
                break
            if t not in used_texts and t not in {c[1] for c in chosen}:
                chosen.append((k, t))
        chosen = chosen[:3]
        used_keys.update(k for k, _ in chosen)
        used_texts.update(t for _, t in chosen)
        r["pros"] = [t for _, t in chosen]
        r["cons"] = cons or ["Requires local review"]
        r["unique_feature"] = unique
        r["why"] = why
        r["benefits"] = list(r["pros"])
        gaps = list(base_gaps)
        if "alfalfa" in opts or "small_grain" in opts:
            gaps.append("County yields loaded only for corn and soybeans; no small-grain or hay yield data")
        r["info_gaps"] = gaps
        r["local_review_risks"] = risks
        ev = _data_evidence(tier)
        if evidence_lookup is not None:
            for o in sorted(opts):
                ev.extend(evidence_lookup(EVIDENCE_TERMS[o], r["strategy_code"]))
        r["evidence"] = ev
        r.pop("_sc", None)
    return rows


def compare_response(sim: dict) -> dict:
    """SOT 6 POST /strategies/compare shape (+ 08:20 extensions) from a simulate() result with cards."""
    strategies = []
    for r in sorted(sim["strategies"], key=lambda x: x["rank"]):
        strategies.append({
            "strategy_code": r["strategy_code"],
            "candidate_id": r["candidate_id"],
            "label": r["label"],
            "sequence": r["sequence"],
            "rank": r["rank"],
            "goal_label": r["goal_label"],
            "why": r["why"],
            "evidence": r["evidence"],
            "benefits": r["benefits"],
            "info_gaps": r["info_gaps"],
            "local_review_risks": r["local_review_risks"],
            "scores": r["scores"],
            "p10": r["composite"]["p10"],
            "p50": r["composite"]["p50"],
            "p90": r["composite"]["p90"],
            "cvar": r["composite"]["cvar"],
            "display": r["display"],
            "pros": r["pros"],
            "cons": r["cons"],
            "unique_feature": r["unique_feature"],
            "weights_applied": sim["weights_applied"],
            "water_weight_boosted": sim["water_weight_boosted"],
            "scenario_results": [s for s in r["scenario_results"] if s["horizon"] != "historical"],
            "warnings": r["warnings"],
        })
    return {
        "field_id": sim["field_id"],
        "county_fips": sim["county_fips"],
        "priorities_normalized": sim["priorities_normalized"],
        "run_id": sim["run_id"],
        "unit": sim["unit"],
        "cvar_definition": sim["cvar_definition"],
        "period": sim["period"],
        "strategies": strategies,
        "assumptions": sim["assumptions"],
        "disclaimer": sim["disclaimer"],
    }
