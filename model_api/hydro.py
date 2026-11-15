"""FAO-56 style daily soil-water bucket + Monte Carlo over resampled POWER weather years.

Model (TEAM_SPEC 5.2):
  * ET0: FAO-56 Penman-Monteith (eq. 6) from POWER T2M/T2M_MIN/T2M_MAX/RH2M/WS2M/ALLSKY_SFC_SW_DWN.
    Days with missing radiation use Hargreaves (FAO-56 eq. 52).
  * ETc = Kc(crop, day) * ET0; ETa = Ks * ETc with FAO-56 eq. 84 water-stress coefficient.
  * Single top-down depletion bucket over a fixed profile; crops see TAW = 1000 * AWC * Zr(crop).
  * Runoff: SCS curve number (TR-55) per land state; infiltration beyond field capacity drains.
  * MC: each sample draws 1 spin-up + 4 scored calendar years with replacement from the loaded POWER years
    (common random numbers across strategies), plus a random rotation phase per strategy and, for scenario
    runs, a random ensemble member / model (delta method).
  * CVaR convention: mean of the worst 10 % of samples (lower tail of a "higher is better" quantity,
    upper tail of a loss such as water deficit). The response ``unit`` / ``cvar_definition`` repeats this.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

DAYS = 365
N_YEARS_SCORED = 4
N_YEARS_TOTAL = N_YEARS_SCORED + 1  # one spin-up year
MONTH_OF_DOY = np.array([m for m, n in enumerate([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31], start=1) for _ in range(n)])
WINTER_MASK = np.zeros(DAYS, bool)
WINTER_MASK[:120] = True  # Jan 1 - Apr 30
WINTER_MASK[304:] = True  # Nov 1 - Dec 31


# ---------------------------------------------------------------------------------------------------
# weather
# ---------------------------------------------------------------------------------------------------
def to_year_matrix(wx: dict[str, np.ndarray]) -> dict:
    """Daily county series -> (Y, 365) matrices (Feb 29 dropped). NaNs filled by day-of-year mean."""
    dates = wx["date"]
    years = np.array([d.year for d in dates])
    keep = np.array([not (d.month == 2 and d.day == 29) for d in dates])
    out: dict = {}
    uy = sorted(set(years[keep]))
    full = [y for y in uy if int(((years == y) & keep).sum()) == DAYS]
    out["years"] = np.array(full)
    filled = 0
    for k in ("t2m_c", "tmin_c", "tmax_c", "precip_mm", "rh2m_pct", "ws2m_ms", "srad_mj_m2"):
        mat = np.vstack([wx[k][(years == y) & keep] for y in full]).astype(float)
        nan = np.isnan(mat)
        if nan.any():
            filled += int(nan.sum())
            clim = np.nanmean(mat, axis=0)
            mat[nan] = np.take(clim, np.where(nan)[1])
        out[k] = mat
    out["n_filled"] = filled
    return out


def et0_fao56(tmean, tmax, tmin, rh, u2, rs, lat_deg: float, elev_m: float):
    """FAO-56 Penman-Monteith reference ET (mm/day). Arrays broadcast; last axis = day of year (365)."""
    doy = np.arange(1, DAYS + 1)
    phi = np.deg2rad(lat_deg)
    dr = 1 + 0.033 * np.cos(2 * np.pi * doy / 365)
    dec = 0.409 * np.sin(2 * np.pi * doy / 365 - 1.39)
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(dec), -1, 1))
    ra = 24 * 60 / np.pi * 0.0820 * dr * (ws * np.sin(phi) * np.sin(dec) + np.cos(phi) * np.cos(dec) * np.sin(ws))
    pres = 101.3 * ((293 - 0.0065 * elev_m) / 293) ** 5.26
    gamma = 0.000665 * pres

    def es(t):
        return 0.6108 * np.exp(17.27 * t / (t + 237.3))

    es_ = (es(tmax) + es(tmin)) / 2
    ea = np.clip(rh, 0, 100) / 100.0 * es_
    delta = 4098 * es(tmean) / (tmean + 237.3) ** 2
    rso = (0.75 + 2e-5 * elev_m) * ra
    rs_ok = np.where(np.isnan(rs), 0.0, rs)
    rns = 0.77 * rs_ok
    ratio = np.clip(np.where(rso > 0, rs_ok / rso, 0.5), 0.25, 1.0)
    rnl = 4.903e-9 * ((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2 * (0.34 - 0.14 * np.sqrt(np.maximum(ea, 0))) * (1.35 * ratio - 0.35)
    rn = rns - rnl
    et0 = (0.408 * delta * rn + gamma * 900 / (tmean + 273) * u2 * (es_ - ea)) / (delta + gamma * (1 + 0.34 * u2))
    harg = 0.0023 * (tmean + 17.8) * np.sqrt(np.maximum(tmax - tmin, 0)) * 0.408 * ra
    et0 = np.where(np.isnan(rs), harg, et0)
    return np.maximum(et0, 0.0)


@dataclass
class ScenarioSpec:
    name: str  # "historical" | "next_season" | "2030s_ssp245" ...
    horizon: str | None
    source_id: str | None
    scenario: str | None
    # each member: (label, pr_ratio[12], dtmax[12], dtmin[12])
    members: list[tuple[str, np.ndarray, np.ndarray, np.ndarray]]
    period: str | None = None
    notes: list[str] = field(default_factory=list)


def historical_spec() -> ScenarioSpec:
    one, zero = np.ones(12), np.zeros(12)
    return ScenarioSpec("historical", None, "power", "historical", [("power", one, zero, zero)])


def member_weather(ym: dict, spec: ScenarioSpec, lat: float, elev: float):
    """Return P (M, Y, 365) and ET0 (M, Y, 365) for each member of the scenario (delta method)."""
    ps, es_ = [], []
    mi = MONTH_OF_DOY - 1
    for _, ratio, dtx, dtn in spec.members:
        dtx_d, dtn_d = dtx[mi], dtn[mi]
        tmax = ym["tmax_c"] + dtx_d
        tmin = ym["tmin_c"] + dtn_d
        tmean = ym["t2m_c"] + (dtx_d + dtn_d) / 2
        ps.append(ym["precip_mm"] * ratio[mi])
        es_.append(et0_fao56(tmean, tmax, tmin, ym["rh2m_pct"], ym["ws2m_ms"], ym["srad_mj_m2"], lat, elev))
    return np.stack(ps), np.stack(es_)


# ---------------------------------------------------------------------------------------------------
# crop calendars (Iowa defaults; documented in assumptions)
# ---------------------------------------------------------------------------------------------------
OPTIONS = ("cover_rye", "small_grain", "alfalfa")


def cycle_for(options: tuple[str, ...] | list[str], base: tuple[str, ...] | list[str] | None = None) -> list[tuple[str, str | None]]:
    """Rotation cycle (main crop, fall state) per calendar year for a set of added options (TEAM_SPEC 2.3).

    ``base`` is the field's own corn/soy cash sequence from CDL (e.g. ("corn", "corn", "soy")). It is used for
    A (current practice) and B (A + cereal rye after every cash crop). Options that change the cash sequence
    (small grain, alfalfa) use the fixed C-S-W / C-S-Alf-Alf rotations of PRD 4.
    """
    o = set(options)
    rye = "rye" if "cover_rye" in o else None
    if base and not ({"small_grain", "alfalfa"} & o):
        return [(c, rye) for c in base]
    cyc: list[tuple[str, str | None]] = [("corn", rye)]
    if "small_grain" in o:
        cyc += [("soy", "wheat"), ("wheat", "cover_after_wheat" if rye else None)]
    else:
        cyc += [("soy", rye)]
    if "alfalfa" in o:
        cyc += [("alfalfa1", "alfalfa"), ("alfalfa2", rye)]
    return cyc


CROP_DATES_NOTE = (
    "Iowa crop calendar defaults (day of year): corn plant May 1 / harvest Sep 28; soybean May 10 / Sep 22; "
    "winter wheat plant Oct 2 / harvest Jul 15; cereal rye cover planted 7 days after harvest, terminated 10 days "
    "before the next cash crop; post-wheat cover planted Jul 24; alfalfa spring-seeded Apr 15, second year "
    "terminated Oct 15. Kc is linear between stage break points (ini/dev/mid/late) in the FAO-56 Table 11 pattern; "
    "the stage dates are the team Iowa calendar above, not a verified Table 11 row (assumption)."
)
# end of the initial (ini) stage per crop; residue mulch acts on soil evaporation until this day
INI_END = {"corn": 151, "soy": 150, "alfalfa1": 135}
HARVEST = {"corn": 271, "soy": 265, "wheat": 196, "alfalfa2": 288}
PLANT = {"corn": 121, "soy": 130, "wheat": 1, "alfalfa1": 105, "alfalfa2": 1}


def _year_arrays(main: str, spring: str | None, fall: str | None, prm: dict) -> dict[str, np.ndarray]:
    doy = np.arange(1, DAYS + 1)
    a = {
        "kc": np.full(DAYS, prm["kc_bare"]),
        "zr": np.full(DAYS, prm["evap_layer_m"]),
        "p": np.zeros(DAYS),
        "cn": np.full(DAYS, prm["cn_fallow_residue"]),
        "living": np.zeros(DAYS, bool),
        "main": np.zeros(DAYS, bool),
    }

    def put(start, end, kp, zr, cn, main_from=None, p=None):
        sl = (doy >= start) & (doy <= end)
        scale = prm.get("kc_field_scale", 1.0) if main_from is not None else 1.0
        a["kc"][sl] = scale * np.interp(doy[sl], [k[0] for k in kp], [k[1] for k in kp])
        a["zr"][sl] = zr
        a["p"][sl] = prm["p_depletion"] if p is None else p
        a["cn"][sl] = cn
        a["living"][sl] = True
        if main_from is not None:
            a["main"][sl & (doy >= main_from)] = True

    # spring carry-over from the previous fall
    residue = spring in ("rye", "cover_after_wheat") and main in INI_END
    term = PLANT.get(main, 121) - 10
    if spring in ("rye", "cover_after_wheat"):
        put(1, term, [(1, prm["kc_cover_dormant"]), (60, prm["kc_cover_dormant"]), (term, prm["kc_cover_spring"])],
            prm["zr_cover_m"], prm["cn_small_grain"], p=prm["p_cover"])
    # main crop (row crops planted into terminated rye residue get the TR-55 "SR + crop residue" curve number)
    cn_row = prm["cn_row_crop_residue"] if residue else prm["cn_row_crop"]
    if main == "corn":
        put(121, 271, [(121, prm["kc_corn_ini"]), (151, prm["kc_corn_ini"]), (191, prm["kc_corn_mid"]),
                       (241, prm["kc_corn_mid"]), (271, prm["kc_corn_end"])], prm["zr_corn_m"], cn_row, 121, p=prm["p_corn"])
    elif main == "soy":
        put(130, 265, [(130, prm["kc_soy_ini"]), (150, prm["kc_soy_ini"]), (180, prm["kc_soy_mid"]),
                       (240, prm["kc_soy_mid"]), (265, prm["kc_soy_end"])], prm["zr_soy_m"], cn_row, 130, p=prm["p_soy"])
    elif main == "wheat":
        put(1, 196, [(1, prm["kc_wheat_ini"]), (60, prm["kc_wheat_ini"]), (121, prm["kc_wheat_mid"]),
                     (166, prm["kc_wheat_mid"]), (196, prm["kc_wheat_end"])], prm["zr_wheat_m"], prm["cn_small_grain"], 60,
            p=prm["p_wheat"])
    elif main == "alfalfa1":
        put(105, 304, [(105, prm["kc_alfalfa_ini"]), (135, prm["kc_alfalfa_mid"]), (280, prm["kc_alfalfa_mid"]),
                       (304, prm["kc_alfalfa_end"])], prm["zr_alfalfa_m"], prm["cn_legume_meadow"], 105, p=prm["p_alfalfa"])
    elif main == "alfalfa2":
        put(1, 288, [(1, prm["kc_cover_dormant"]), (90, prm["kc_cover_dormant"]), (121, prm["kc_alfalfa_mid"]),
                     (258, prm["kc_alfalfa_mid"]), (288, prm["kc_alfalfa_end"])], prm["zr_alfalfa_m"], prm["cn_legume_meadow"], 91,
            p=prm["p_alfalfa"])
    if residue:
        # FAO-56 ch. 7: organic mulch cuts soil evaporation ~5 % per 10 % of surface covered. Applied to the
        # evaporation-dominated days between rye termination and the end of the crop's initial stage.
        sl = (doy > term) & (doy <= INI_END[main])
        a["kc"][sl] *= max(0.0, 1.0 - 0.5 * prm["rye_residue_cover_frac"])
    # fall state
    if fall == "rye":
        start = HARVEST[main] + 7
        put(start, DAYS, [(start, prm["kc_cover_dormant"]), (DAYS, prm["kc_cover_dormant"])], prm["zr_cover_m"], prm["cn_small_grain"],
            p=prm["p_cover"])
    elif fall == "wheat":
        put(275, DAYS, [(275, prm["kc_wheat_ini"]), (DAYS, prm["kc_wheat_ini"])], prm["zr_cover_m"], prm["cn_small_grain"],
            p=prm["p_wheat"])
    elif fall == "cover_after_wheat":
        put(205, DAYS, [(205, prm["kc_cover_dormant"]), (260, prm["kc_cover_spring"]), (305, prm["kc_cover_dormant"]),
                        (DAYS, prm["kc_cover_dormant"])], prm["zr_cover_m"], prm["cn_small_grain"], p=prm["p_cover"])
    elif fall == "alfalfa":
        put(305, DAYS, [(305, prm["kc_cover_dormant"]), (DAYS, prm["kc_cover_dormant"])], prm["zr_alfalfa_m"], prm["cn_legume_meadow"])
    return a


def calendar_table(cycles: list[list[tuple[str, str | None]]], prm: dict, years_total: int = N_YEARS_TOTAL) -> dict[str, np.ndarray]:
    """(S, Pmax, 5*365) arrays per candidate cycle and rotation phase."""
    pmax = max(len(c) for c in cycles)
    keys = ("kc", "zr", "p", "cn", "living", "main")
    tab = {k: np.zeros((len(cycles), pmax, years_total * DAYS), dtype=bool if k in ("living", "main") else float) for k in keys}
    for si, cyc in enumerate(cycles):
        L = len(cyc)
        for ph in range(pmax):
            p0 = ph % L
            for k in range(years_total):
                main, fall = cyc[(p0 + k) % L]
                spring = cyc[(p0 + k - 1) % L][1]
                ya = _year_arrays(main, spring, fall, prm)
                for key in keys:
                    tab[key][si, ph, k * DAYS:(k + 1) * DAYS] = ya[key]
    tab["cycle_len"] = np.array([len(c) for c in cycles])
    return tab


# ---------------------------------------------------------------------------------------------------
# Monte Carlo
# ---------------------------------------------------------------------------------------------------
METRICS = (
    "season_water_deficit_mm", "stress_days", "season_etc_mm", "eta_mm", "runoff_mm", "drainage_mm",
    "offseason_drainage_mm", "living_cover_days", "winter_bare_days", "veg_index_days", "precip_mm",
)


def run_mc(ym: dict, specs: list[ScenarioSpec], cycles: list[list[tuple[str, str | None]]], prm: dict, lat: float, n: int, seed: int,
           year_draws: np.ndarray | None = None, phases: np.ndarray | None = None, n_scored: int = N_YEARS_SCORED,
           n_spinup: int = 1, trace: bool = False) -> dict:
    """Return {scenario_name: {metric: array (S, N)}} plus draws. Units: mm/yr or days/yr (mean over scored years).

    ``trace=True`` also returns daily ETa and root-zone available water (mm) for every (scenario, strategy, sample);
    use it only for small deterministic runs (calibration / checks).
    """
    rng = np.random.default_rng(seed)
    Y = len(ym["years"])
    total = n_scored + n_spinup
    ys = rng.integers(0, Y, size=(n, total)) if year_draws is None else np.asarray(year_draws)
    n = ys.shape[0]
    tab = calendar_table(cycles, prm, total)
    S = len(cycles)
    if phases is None:
        phases = np.stack([rng.integers(0, L, size=n) for L in tab["cycle_len"]])  # (S, N)
    member_idx = []
    Pw, Ew = [], []
    day = np.arange(total * DAYS)
    yslot, dy = day // DAYS, day % DAYS
    for spec in specs:
        P_m, E_m = member_weather(ym, spec, lat, prm["elevation_m"])
        mi = rng.integers(0, len(spec.members), size=n)
        member_idx.append(mi)
        yy = ys[:, yslot]  # (N, D)
        Pw.append(P_m[mi[:, None], yy, dy[None, :]])
        Ew.append(E_m[mi[:, None], yy, dy[None, :]])
    Pw = np.stack(Pw).astype(np.float64)  # (C, N, D)
    Ew = np.stack(Ew).astype(np.float64)
    C = len(specs)

    awc_mm = prm["awc_cm_cm"] * 1000.0
    taw_max = awc_mm * prm["profile_depth_m"]
    Dr = np.zeros((C, S, n))
    acc = {m: np.zeros((C, S, n)) for m in METRICS}
    sidx = np.arange(S)[:, None]
    tr_eta, tr_aw = [], []
    for d in range(total * DAYS):
        kc = tab["kc"][sidx, phases, d][None]
        zr = tab["zr"][sidx, phases, d][None]
        pp = tab["p"][sidx, phases, d][None]
        cn = tab["cn"][sidx, phases, d][None]
        liv = tab["living"][sidx, phases, d][None]
        main = tab["main"][sidx, phases, d][None]
        P = Pw[:, None, :, d]
        E0 = Ew[:, None, :, d]
        Smax = 25400.0 / cn - 254.0
        Ia = 0.2 * Smax
        Q = np.where(P > Ia, (P - Ia) ** 2 / (P + 0.8 * Smax), 0.0)
        Dr = Dr - (P - Q)
        drain = np.maximum(-Dr, 0.0)
        Dr = np.maximum(Dr, 0.0)
        taw = awc_mm * zr
        ks = np.clip((taw - Dr) / ((1.0 - pp) * taw), 0.0, 1.0)
        etc = kc * E0
        eta = ks * etc
        Dr = np.minimum(Dr + eta, taw_max)
        if trace:
            tr_eta.append(eta)
            tr_aw.append(taw_max - Dr)
        if d >= n_spinup * DAYS:
            acc["season_water_deficit_mm"] += main * (etc - eta)
            acc["stress_days"] += main & (ks < 0.99)
            acc["season_etc_mm"] += main * etc
            acc["eta_mm"] += eta
            acc["runoff_mm"] += Q
            acc["drainage_mm"] += drain
            acc["offseason_drainage_mm"] += (~main) * drain
            acc["living_cover_days"] += liv
            acc["winter_bare_days"] += (~liv) & WINTER_MASK[dy[d]]
            acc["veg_index_days"] += liv * ks
            acc["precip_mm"] += P
    out = {spec.name: {m: acc[m][ci] / n_scored for m in METRICS} for ci, spec in enumerate(specs)}
    res = {"results": out, "year_draws": ys, "phases": phases, "years": ym["years"]}
    if trace:
        res["trace"] = {"eta_mm": np.stack(tr_eta, axis=-1), "soil_water_mm": np.stack(tr_aw, axis=-1)}  # (C, S, N, D)
    return res


def quantiles(x: np.ndarray, higher_is_better: bool) -> dict:
    """P10/P50/P90 and CVaR = mean of the worst 10 % of samples."""
    x = np.asarray(x, float)
    q10, q50, q90 = np.percentile(x, [10, 50, 90])
    k = max(1, int(np.ceil(0.1 * x.size)))
    s = np.sort(x)
    cvar = s[:k].mean() if higher_is_better else s[-k:].mean()
    return {"p10": round(float(q10), 3), "p50": round(float(q50), 3), "p90": round(float(q90), 3), "cvar": round(float(cvar), 3)}
