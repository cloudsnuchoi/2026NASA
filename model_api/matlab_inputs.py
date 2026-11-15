"""Offline MATLAB outputs (CSV) loader. Missing files are skipped and reported, never fatal.

Files (TEAM_SPEC 7.4): field_dekad.csv, field_season.csv, climate_annual.csv, scenario_climate.csv,
calibration_params.csv, coefficients.csv. ``calibration_params.csv`` and ``coefficients.csv`` rows
(``param,value,...``) override ``config.DEFAULTS`` / rule priors with the same ``param`` name.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path

from . import config

FILES = (
    "field_dekad.csv",
    "field_season.csv",
    "climate_annual.csv",
    "scenario_climate.csv",
    "calibration_params.csv",
    "coefficients.csv",
)

_cache: dict[str, tuple[float, list[dict]]] = {}


def _read_csv(path: Path) -> list[dict]:
    mtime = path.stat().st_mtime
    hit = _cache.get(str(path))
    if hit and hit[0] == mtime:
        return hit[1]
    with path.open(newline="", encoding="utf-8") as fh:
        rows = [{k: (v if v != "" else None) for k, v in row.items()} for row in csv.DictReader(fh)]
    _cache[str(path)] = (mtime, rows)
    return rows


def load(directory: str | None = None) -> dict:
    """Return {"tables": {name: rows}, "overrides": {param: value}, "notes": [..]}."""
    d = Path(directory or os.environ.get("FS_MATLAB_DIR", config.MATLAB_DIR))
    tables: dict[str, list[dict]] = {}
    notes: list[str] = []
    for name in FILES:
        p = d / name
        if not p.is_file():
            notes.append(f"MATLAB input {name} not found in {d}; item skipped (defaults used where needed)")
            continue
        try:
            tables[name.removesuffix(".csv")] = _read_csv(p)
        except Exception as exc:  # malformed file must not break the API
            notes.append(f"MATLAB input {name} unreadable ({type(exc).__name__}); item skipped")
    overrides: dict[str, float] = {}
    for t in ("calibration_params", "coefficients"):
        for row in tables.get(t, []):
            try:
                if row.get("param") and row.get("value") is not None:
                    overrides[row["param"].strip()] = float(row["value"])
            except (TypeError, ValueError):
                notes.append(f"{t}: non-numeric value for {row.get('param')!r} ignored")
    return {"tables": tables, "overrides": overrides, "notes": notes, "dir": str(d)}
