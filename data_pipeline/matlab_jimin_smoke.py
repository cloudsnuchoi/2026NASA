"""Offline Python smoke of Jimin's extra MATLAB computations.

Does not execute MATLAB. SciPy SG and the explicit MATLAB least-squares code
specify the same quadratic 11-point windows, including clamped edge windows.
Never overwrites teammate MATLAB outputs: writes under outputs/jimin/python_smoke.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy.signal import savgol_filter

CALENDAR_UNIT = "day (365-day engine calendar)"


def supported_curve(block: pd.DataFrame, year: int) -> pd.DataFrame:
    dates = pd.date_range(f"{year}-01-01", f"{year}-12-31")
    good = block.ndvi.between(-1, 1) & block.valid_frac.between(0.5, 1)
    raw = block.loc[good].groupby("date").ndvi.mean().reindex(dates).to_numpy()
    filled = raw.copy()
    known = np.flatnonzero(np.isfinite(raw))
    for a, b in zip(known[:-1], known[1:]):
        if b - a <= 20:
            filled[a:b + 1] = np.interp(np.arange(a, b + 1), [a, b], raw[[a, b]])
    smooth = np.full(len(dates), np.nan)
    edges = np.diff(np.r_[False, np.isfinite(filled), False].astype(int))
    for a, b in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)):
        if b - a >= 11:
            smooth[a:b] = savgol_filter(filled[a:b], 11, 2, mode="interp")
    smooth[(dates.month == 2) & (dates.day == 29)] = np.nan
    return pd.DataFrame({"date": dates, "ndvi_smooth": smooth})


def phenology(daily: pd.DataFrame) -> dict:
    values = daily.ndvi_smooth.to_numpy()
    supported = np.isfinite(values)
    row = dict(greenup_doy=np.nan, peak_doy=np.nan, senescence_doy=np.nan,
               season_length_days=np.nan, threshold_ndvi=np.nan,
               supported_days=int(supported.sum()), status="information_gap_no_supported_days")
    if not supported.any():
        return row
    ix = np.flatnonzero(supported)
    peak = ix[np.argmax(values[ix])]
    row["peak_doy"] = peak + 1
    lo, hi = np.min(values[ix]), values[peak]
    if hi - lo <= 1e-6:
        row["status"] = "information_gap_flat_curve"
        return row
    threshold = lo + 0.2 * (hi - lo)
    row["threshold_ndvi"] = threshold
    rise = np.flatnonzero((values[:-1] < threshold) & (values[1:] >= threshold)) + 1
    fall = np.flatnonzero((values[:-1] >= threshold) & (values[1:] < threshold)) + 1
    rise, fall = rise[rise <= peak], fall[fall > peak]
    row["status"] = "information_gap_missing_transition"
    if len(rise):
        row["greenup_doy"] = rise[-1] + 1
    if len(fall):
        row["senescence_doy"] = fall[0] + 1
    if len(rise) and len(fall):
        row["season_length_days"] = fall[0] - rise[-1]
        row["status"] = "provisional_dominant_peak_screening"
    return row


def anomalies(daily: pd.DataFrame) -> pd.DataFrame:
    out = daily.groupby(["field_id", "year"], as_index=False).agg(
        ndvi_mean=("ndvi_smooth", "mean"), supported_days=("ndvi_smooth", "count"))
    out["field_available_year_mean"] = out.groupby("field_id").ndvi_mean.transform("mean")
    out["baseline_year_count"] = out.groupby("field_id").ndvi_mean.transform("count")
    year_lists = out[out.ndvi_mean.notna()].groupby("field_id").year.agg(lambda v: ";".join(v.astype(str)))
    out["baseline_years"] = out.field_id.map(year_lists).fillna("")
    enough = (out.baseline_year_count >= 2) & out.ndvi_mean.notna()
    out["ndvi_anomaly"] = (out.ndvi_mean - out.field_available_year_mean).where(enough)
    out["status"] = np.where(enough, "available_years_only_variable_support_not_climatology",
                             "information_gap_need_two_years")
    return out


def bare_comparison(daily: pd.DataFrame, assumptions: pd.DataFrame) -> pd.DataFrame:
    assert not assumptions.duplicated(["field_id", "item"]).any(), "Duplicate assumption key"
    rows = []
    for (field_id, year), block in daily.groupby(["field_id", "year"]):
        support = block.ndvi_smooth.notna().to_numpy()
        dates = pd.DatetimeIndex(block.date)
        support &= ~((dates.month == 2) & (dates.day == 29))
        low = support & (block.ndvi_smooth.to_numpy() < 0.3)
        winter = (dates.month <= 4) | (dates.month >= 11)
        a = assumptions[assumptions.field_id == field_id].set_index("item")
        for crop in ("corn", "soy"):
            items = [f"{crop}_plant_doy", f"{crop}_harvest_doy",
                     "rye_plant_after_harvest_days", "rye_terminate_before_plant_days"]
            row = dict(field_id=field_id, year=year, calendar_crop=crop,
                       observed_low_ndvi_days=int(low.sum()) if support.any() else np.nan,
                       observed_winter_low_ndvi_days=int((low & winter).sum()) if (support & winter).any() else np.nan,
                       supported_days=int(support.sum()), coverage=float(support.sum() / 365),
                       assumed_no_living_cover_days=np.nan, assumed_no_living_cover_on_supported_days=np.nan,
                       assumption_sources="", run_ids="", baseline_rotation=a.loc["baseline_rotation", "value"]
                       if "baseline_rotation" in a.index else "",
                       rye_spring_end_doy=np.nan, rye_fall_start_doy=np.nan,
                       rye_residue_cover_frac=np.nan, residue_fraction_source="",
                       status="information_gap_missing_calendar")
            # Terminated residue surface fraction is not living rye cover.
            if "rye_residue_cover_frac" in a.index:
                residue = a.loc["rye_residue_cover_frac"]
                assert residue.unit == "fraction", "Unexpected residue fraction unit"
                fraction = float(pd.to_numeric(residue.value, errors="coerce"))
                assert np.isnan(fraction) or (np.isfinite(fraction) and 0 <= fraction <= 1)
                row.update(rye_residue_cover_frac=fraction, residue_fraction_source=residue.source)
            if all(item in a.index for item in items):
                sel = a.loc[items]
                assert (sel.unit == CALENDAR_UNIT).all(), "Unexpected calendar unit"
                vals = pd.to_numeric(sel.value, errors="coerce").to_numpy(dtype=float)
                row["assumption_sources"] = ";".join(sorted(set(sel.source)))
                row["run_ids"] = ";".join(sorted(set(sel.run_id)))
                if np.isfinite(vals).all() and (sel.source.str.len() > 0).all() and (sel.run_id.str.len() > 0).all():
                    p, h, after, before = vals
                    assert np.equal(vals, np.floor(vals)).all()
                    assert 1 <= p <= h <= 365 and after >= 1 and before >= 1 and p - before >= 1 and h + after <= 365
                    doy = dates.dayofyear - (dates.is_leap_year & (dates.month > 2)).astype(int)
                    living = (doy <= p - before) | ((doy >= p) & (doy <= h)) | (doy >= h + after)
                    row.update(rye_spring_end_doy=int(p - before), rye_fall_start_doy=int(h + after),
                               assumed_no_living_cover_days=int(before + after - 2),
                               assumed_no_living_cover_on_supported_days=int((support & ~living).sum())
                               if support.any() else np.nan,
                               status="calendar_scenario_assumption_not_observed_rye")
            rows.append(row)
    return pd.DataFrame(rows)


def self_check() -> None:
    """Synthetic fixtures test algorithms only; never enter reported data outputs."""
    def observations(dates, values):
        return pd.DataFrame({"date": pd.to_datetime(dates), "ndvi": values, "valid_frac": 1.0})
    # Independent explicit least-squares formula used by the MATLAB code.
    # Check both segment edges and interior against SciPy mode='interp'.
    for n in (11, 12, 35):
        v = np.sin(np.arange(n) / 3) + np.arange(n) * 0.01
        fitted = []
        for j in range(n):
            start = min(max(j - 5, 0), n - 11)
            idx = np.arange(start, start + 11)
            x = idx - j
            coef = np.linalg.lstsq(np.column_stack([np.ones(11), x, x*x]), v[idx], rcond=None)[0]
            fitted.append(coef[0])
        assert np.allclose(fitted, savgol_filter(v, 11, 2, mode="interp"), atol=1e-12, rtol=0)
    empty = supported_curve(observations(["2023-01-01"], [np.nan]), 2023)
    assert empty.ndvi_smooth.isna().all()
    gap = supported_curve(observations(["2023-01-01", "2023-01-11", "2023-03-01", "2023-03-11"],
                                      [0.1, 0.2, 0.8, 0.9]), 2023)
    assert gap.ndvi_smooth.iloc[11:59].isna().all(), "Long gap bridged"
    assert np.isnan(phenology(gap)["greenup_doy"]), "Crossed unsupported gap"
    curve = np.r_[np.linspace(0.1, 0.8, 101), np.linspace(0.79, 0.1, 100)]
    p = phenology(pd.DataFrame({"ndvi_smooth": curve}))
    assert 1 <= p["greenup_doy"] <= p["peak_doy"] < p["senescence_doy"] <= 201
    assert phenology(pd.DataFrame({"ndvi_smooth": [0.2] * 30}))["status"] == "information_gap_flat_curve"
    duplicate = observations(["2024-02-20", "2024-02-20", "2024-03-10"], [0.1, 0.3, 0.4])
    leap = supported_curve(duplicate, 2024)
    assert np.isclose(leap.ndvi_smooth.iloc[50], 0.2)
    assert leap.loc[leap.date.eq("2024-02-29"), "ndvi_smooth"].isna().all()
    a = anomalies(pd.DataFrame({"field_id": ["001", "001", "002"], "year": [2023, 2024, 2023],
                               "ndvi_smooth": [0.2, 0.6, 0.3]}))
    assert np.allclose(a.loc[a.field_id == "001", "ndvi_anomaly"], [-0.2, 0.2])
    assert a.loc[a.field_id == "002", "ndvi_anomaly"].isna().all()
    # Verify inclusive calendar endpoints independently over the full 365 days.
    days = pd.date_range("2023-01-01", "2023-12-31")
    daily = pd.DataFrame({"field_id": "001", "year": 2023, "date": days, "ndvi_smooth": 0.2})
    items = ["corn_plant_doy", "corn_harvest_doy", "soy_plant_doy", "soy_harvest_doy",
             "rye_plant_after_harvest_days", "rye_terminate_before_plant_days"]
    assumptions = pd.DataFrame({"field_id": "001", "item": items, "value": ["121", "271", "130", "265", "7", "10"],
                                "unit": CALENDAR_UNIT, "source": "synthetic algorithm test", "run_id": "test"})
    assumptions = pd.concat([assumptions, pd.DataFrame([dict(
        field_id="001", item="rye_residue_cover_frac", value="0.5", unit="fraction",
        source="synthetic residue assumption; not living cover", run_id="test")])], ignore_index=True)
    comparison = bare_comparison(daily, assumptions)
    assert comparison.rye_spring_end_doy.tolist() == [111, 120]
    assert comparison.rye_fall_start_doy.tolist() == [278, 272]
    assert (comparison.rye_residue_cover_frac == 0.5).all()
    assert comparison.residue_fraction_source.str.contains("not living cover").all()
    assert (comparison.assumed_no_living_cover_days == 15).all()
    assert (comparison.assumed_no_living_cover_on_supported_days == 15).all()
    missing = bare_comparison(daily, assumptions.iloc[:0])
    assert missing.assumed_no_living_cover_days.isna().all()
    assert missing.rye_spring_end_doy.isna().all() and missing.rye_fall_start_doy.isna().all()
    assert missing.rye_residue_cover_frac.isna().all()
    assert (missing.residue_fraction_source == "").all()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("/srv/hackathon/data"))
    parser.add_argument("--self-test-only", action="store_true")
    args = parser.parse_args()
    self_check()
    if args.self_test_only:
        print("Jimin computation edge-case checks passed")
        return
    base = args.data_root / "processed/v1/matlab"
    obs = pd.read_csv(base / "inputs/ndvi_hls_20fields.csv", dtype={"field_id": str}, parse_dates=["date"])
    fields = pd.read_csv(base / "inputs/fields_20.csv", dtype={"field_id": str})
    assert not fields.field_id.duplicated().any() and fields.field_id.notna().all()
    assert obs.date.notna().all() and set(obs.field_id) <= set(fields.field_id)
    years = sorted(obs.date.dt.year.unique())
    assert years and min(years) >= 2013, "2012 not observable with HLS"
    seasons, days = [], []
    for field_id in fields.field_id:
        for year in years:
            block = obs[(obs.field_id == field_id) & (obs.date.dt.year == year)]
            daily = supported_curve(block, int(year))
            seasons.append(dict(field_id=field_id, year=year, **phenology(daily)))
            days.append(daily.assign(field_id=field_id, year=year))
    daily = pd.concat(days, ignore_index=True)
    assumptions = pd.read_csv(base / "inputs/engine_strategyB_assumptions.csv", dtype=str, keep_default_na=False)
    assert set(("field_id", "item", "value", "unit", "source", "run_id")) <= set(assumptions.columns)
    season, anomaly, bare = pd.DataFrame(seasons), anomalies(daily), bare_comparison(daily, assumptions)
    assert len(season) == len(fields) * len(years)
    assert len(bare) == 2 * len(season)
    assert ((bare.coverage >= 0) & (bare.coverage <= 1)).all()
    assert (bare.observed_low_ndvi_days.dropna() <= bare.supported_days[bare.observed_low_ndvi_days.notna()]).all()
    out = base / "outputs/jimin/python_smoke"
    out.mkdir(parents=True, exist_ok=True)
    outputs = {"growing_season_20fields.csv": season, "jimin_supported_daily.csv": daily,
               "jimin_ndvi_anomaly.csv": anomaly, "bare_vs_strategyB.csv": bare,
               "jimin_strategyB_assumptions_used.csv": assumptions}
    existing = [out / name for name in outputs if (out / name).exists()]
    if existing:
        archive = out / "old" / datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        archive.mkdir(parents=True)
        for path in existing:
            shutil.move(str(path), archive / path.name)
    for name, frame in outputs.items():
        frame.to_csv(out / name, index=False)
    print(f"PASS: {len(season)} field-years, {len(bare)} calendar scenarios, years {years}; outputs {out}")
    print(f"Supported days range {season.supported_days.min()}..{season.supported_days.max()}; "
          f"transition statuses {season.status.value_counts().to_dict()}")
    print("Python smoke only; explicit SG formula matches SciPy within 1e-12; MATLAB runtime remains unverified.")


if __name__ == "__main__":
    main()
