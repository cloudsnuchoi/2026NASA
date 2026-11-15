"""Configuration and documented default coefficients.

Every default here is either a literature value (source named) or a team default rule score.
Whenever the engine uses one of these instead of a measured/loaded value, it adds an entry to the
response ``assumptions`` list. MATLAB ``calibration_params.csv`` / ``coefficients.csv`` rows with the same
``param`` name override these values (see ``matlab_inputs.py``).
"""

from __future__ import annotations

import os

DISCLAIMER_COMPARE = (
    "Supportive comparison only. Not a single optimum. Not a substitute for farmer or agronomist judgment. "
    "Nitrogen figures, if any, are literature ranges pending a field soil test."
)
DISCLAIMER_FIELD = "CSB boundaries are not ownership parcels. This tool supports, and does not replace, farmer judgment."

STORY_FIPS = "19169"
WEATHER_SOURCE = "power"
WEATHER_START_YEAR = 1995
WEATHER_END_YEAR = 2025
BASELINE_START_YEAR = 1995
BASELINE_END_YEAR = 2024

MATLAB_DIR = os.environ.get("FS_MATLAB_DIR", "/srv/hackathon/data/processed/v1/matlab")

FAO56 = "FAO-56 (Allen et al. 1998, FAO Irrigation and Drainage Paper 56)"
FAO56_URL = "https://www.fao.org/3/x0490e/x0490e00.htm"
TR55 = "USDA NRCS TR-55 curve numbers (1986), hydrologic soil group B"

# param -> (value, unit, source)
DEFAULTS: dict[str, tuple[float, str, str]] = {
    # site
    "elevation_m": (300.0, "m", "default; SRTM elevation not loaded in DB (psychrometric constant only)"),
    "awc_cm_cm": (0.18, "cm/cm", "default when SSURGO AWC missing (close to Story County field_soil median)"),
    "kffact": (0.28, "dimensionless", "default when SSURGO K factor missing (close to Story County mean 0.27)"),
    "profile_depth_m": (1.5, "m", "soil profile depth of the single bucket (FAO-56 Table 22 max root depth range)"),
    "evap_layer_m": (0.15, "m", FAO56 + " surface evaporation layer Ze 0.10-0.15 m"),
    # Kc (FAO-56 Table 12)
    "kc_corn_ini": (0.30, "-", FAO56 + " Table 12 maize grain"),
    "kc_corn_mid": (1.20, "-", FAO56 + " Table 12 maize grain"),
    "kc_corn_end": (0.60, "-", FAO56 + " Table 12 maize grain"),
    "kc_soy_ini": (0.40, "-", FAO56 + " Table 12 soybeans"),
    "kc_soy_mid": (1.15, "-", FAO56 + " Table 12 soybeans"),
    "kc_soy_end": (0.50, "-", FAO56 + " Table 12 soybeans"),
    "kc_wheat_ini": (0.40, "-", FAO56 + " Table 12 winter wheat with frozen soils (Iowa winters)"),
    "kc_wheat_mid": (1.15, "-", FAO56 + " Table 12 winter wheat"),
    "kc_wheat_end": (0.30, "-", FAO56 + " Table 12 winter wheat (0.25-0.4)"),
    "kc_alfalfa_ini": (0.40, "-", FAO56 + " Table 12 alfalfa hay, averaged cutting effects"),
    "kc_alfalfa_mid": (0.95, "-", FAO56 + " Table 12 alfalfa hay, averaged cutting effects"),
    "kc_alfalfa_end": (0.90, "-", FAO56 + " Table 12 alfalfa hay, averaged cutting effects"),
    "kc_cover_dormant": (0.40, "-", "assumption: cereal rye is not in FAO-56 Table 12; winter wheat with frozen soils Kc_ini used as analogue"),
    "kc_cover_spring": (0.90, "-", "assumption (no source): spring rye regrowth between FAO-56 winter wheat Kc_ini 0.4 and Kc_mid 1.15"),
    "kc_bare": (0.30, "-", "assumption: FAO-56 Table 12 lowest Kc_ini (0.3) used for bare soil between crops"),
    # root depth (FAO-56 Table 22, lower end of range; the bucket profile is 1.5 m)
    "zr_corn_m": (1.0, "m", FAO56 + " Table 22 maize 1.0-1.7 m (lower end)"),
    "zr_soy_m": (0.6, "m", FAO56 + " Table 22 soybeans 0.6-1.3 m (lower end)"),
    "zr_wheat_m": (1.5, "m", FAO56 + " Table 22 wheat 1.5-1.8 m (lower end)"),
    "zr_alfalfa_m": (1.5, "m", FAO56 + " Table 22 alfalfa 1.0-2.0 m (capped at the 1.5 m bucket)"),
    "zr_cover_m": (0.6, "m", "assumption (no source): cereal rye cover rooting depth by termination"),
    # depletion fraction p (FAO-56 Table 22)
    "p_corn": (0.55, "-", FAO56 + " Table 22 maize p = 0.55"),
    "p_soy": (0.50, "-", FAO56 + " Table 22 soybeans p = 0.50"),
    "p_wheat": (0.55, "-", FAO56 + " Table 22 wheat p = 0.55"),
    "p_alfalfa": (0.55, "-", FAO56 + " Table 22 alfalfa hay p = 0.55"),
    "p_cover": (0.55, "-", "assumption: FAO-56 Table 22 wheat p used for the cereal rye cover"),
    "p_depletion": (0.55, "-", FAO56 + " Table 22 depletion fraction p (fallback)"),
    # cover crop residue (B, C): mulch + infiltration
    "rye_residue_cover_frac": (0.5, "fraction", "assumption (no source): surface fraction covered by terminated rye residue; "
                                                "effect size per FAO-56 ch. 7 (evaporation -5 % per 10 % mulch cover)"),
    "cn_row_crop_residue": (75.0, "-", "USDA NRCS TR-55 (1986) Table 2-2b row crops SR + crop residue, good, HSG B"),
    # field calibration (OpenET Ensemble monthly ET at the CSB centroid)
    "kc_field_scale": (1.0, "-", "default 1.0: no OpenET field ET to calibrate main-crop Kc for this location"),
    "kc_field_scale_min": (0.80, "-", "assumption (no source): lower bound of the OpenET-based field Kc scale"),
    "kc_field_scale_max": (1.25, "-", "assumption (no source): upper bound of the OpenET-based field Kc scale"),
    # curve numbers (TR-55, HSG B; hydrologic group not loaded)
    "cn_row_crop": (78.0, "-", TR55 + " row crops straight row good"),
    "cn_small_grain": (75.0, "-", TR55 + " small grain straight row good"),
    "cn_legume_meadow": (72.0, "-", TR55 + " close-seeded legumes / rotation meadow good"),
    "cn_fallow_residue": (83.0, "-", TR55 + " fallow, crop residue cover good"),
    # bare detection / classes
    "ndvi_bare_threshold": (0.35, "NDVI", "team default; SOT section 7 leaves the threshold open"),
    "ndvi_good": (0.75, "NDVI", "team default for ndvi_class=good; SOT section 7 leaves the threshold open"),
    "ndvi_fair": (0.50, "NDVI", "team default for ndvi_class=fair; SOT section 7 leaves the threshold open"),
    "hero_drought_ratio": (0.70, "ratio", "team default: JJA precip < 70 % of baseline -> drought"),
    "hero_wet_ratio": (1.30, "ratio", "team default: JJA precip > 130 % of baseline -> wet"),
    "hero_heat_c": (1.5, "degC", "team default: JJA Tmax anomaly > 1.5 C -> heat"),
    "heat_tmax_c": (32.0, "degC", "TEAM_SPEC 7.4 heat_days threshold (tmax > 32 C)"),
    # reference scales for 0-1 indices
    "ref_offseason_drainage_mm": (250.0, "mm/yr", "team default scale for n_cycle_index leaching proxy"),
    "ref_stress_days": (60.0, "days/yr", "team default scale for stability"),
}

# Team default rule priors for the 7 axes (0-1, higher = better). Qualitative ordering from PRD 4 /
# DECISIONS 03:50; NOT measured values. Overridable via calibration_params.csv (param e.g. prior_market_A).
RULE_PRIORS: dict[str, dict[str, float]] = {
    "n_cycle": {"A": 0.35, "B": 0.50, "C": 0.55, "D": 0.80},
    "organic_matter": {"A": 0.30, "B": 0.50, "C": 0.55, "D": 0.70},
    "pest_break": {"A": 0.30, "B": 0.35, "C": 0.60, "D": 0.70},
    "forage": {"A": 0.10, "B": 0.30, "C": 0.40, "D": 0.90},
    "market": {"A": 0.80, "B": 0.75, "C": 0.50, "D": 0.40},
}

DATA_SOURCE_URLS = {
    "POWER": "https://power.larc.nasa.gov/",
    "SSURGO": "https://sdmdataaccess.sc.egov.usda.gov/",
    "CDL": "https://www.nass.usda.gov/Research_and_Science/Cropland/SARS1a.php",
    "CSB": "https://www.nass.usda.gov/Research_and_Science/Crop-Sequence-Boundaries/index.php",
    "FAO-56": FAO56_URL,
    "NEX-GDDP-CMIP6": "https://www.nccs.nasa.gov/data-collections/nex-gddp-cmip6/",
    "GEOS-S2S": "https://gmao.gsfc.nasa.gov/gmao-products/geos-s2s-3/",
    "SMAP": "https://nsidc.org/data/spl3smp",
    "HLS": "https://www.earthdata.nasa.gov/data/projects/hls",
    "OpenET": "https://openetdata.org/",
    "NASS": "https://sb.nass.usda.gov/datasets/",
}


def llm_settings() -> dict:
    return {
        "api_key": os.environ.get("LLM_API_KEY"),
        "base_url": os.environ.get("LLM_BASE_URL", "https://api.deepseek.com"),
        "model": os.environ.get("LLM_MODEL", "deepseek-flash"),
    }
