# Spike report: GPM IMERG daily + NLDAS-2 Noah monthly (tier 1) — lane 2

**Status: Go.** The earlier 403 is resolved. The "NASA GESDISC DATA ARCHIVE" app was approved, and GES DISC downloads work with `earthaccess.login(strategy="netrc")`. The one-granule test (2020-06-01, 32 MB) took about 5.5 s.

## GPM IMERG Final daily — Go
- Collection `GPM_3IMERGDF` **version 07** (CMR shows `V07B` files), 0.1 deg, variable `precipitation` (mm/day, "Daily mean precipitation rate (combined microwave-IR) estimate"). The file `DOI` attribute is `10.5067/GPM/IMERGDF/DAY/07`.
- `county_imerg_daily` (product `GPM_3IMERGDF.07`) holds **10,141,758 rows**: 1,122 counties x 9,039 days, **2001-01-01..2025-09-30**. 2025-09-30 is the latest Final-run day available in CMR on 2026-11-15. There are 0 NULLs and 0 failed granules.
- County value = mean of the 0.1 deg cell centres inside the county polygon. All 1,122 counties contain at least one cell centre, so none needed the nearest-cell fallback. The context-cell rule in SOT 2 applies: this is **context, not a field-precise value**.
- Sanity check against POWER `PRECTOTCORR`: daily r = 0.73 and mean 2.78 vs 2.53 mm/day. The difference is expected: IMERG days are UTC and POWER days are LST, and the two products have different resolution and source. Story 19169, May–Aug precipitation: 2012 = 207 mm, 2013 = 466 mm (the 2012 drought is visible).
- Raw granules (31 MB/day, about 280 GB over the whole run) were downloaded, reduced and deleted. Reduced county series are kept as `/srv/hackathon/data/raw/imerg/tier1_county/county_daily_<range>.parquet`.
- Timing: about 350 s per year (about 1 s/day). A 6-thread download pool gives about 1 req/s, below the 2 req/s limit. The full 2001–2025 run took about 2.8 h.
- Bug fixes in the loader: the old threaded NetCDF read segfaulted (HDF5 is not thread-safe), so reads are now serial. The `show_progress` kwarg does not exist in this earthaccess version. A mapping dtype bug is also fixed.
- Not loaded: 1998–2000 (TRMM-era GPM IMERG V07 begins 2000-06; not requested).

## NLDAS-2 Noah monthly — Go
- Collection `NLDAS_NOAH0125_M` **v2.0**, 0.125 deg, 372 monthly files (about 10 MB each, 3.9 GB raw at `/srv/hackathon/data/raw/nldas2/`) plus `county_monthly_1995-01_2025-12.parquet`.
- `county_nldas_monthly` (`sql/003_nldas_monthly.sql`) holds **417,384 rows**: 1,122 counties x 372 months, **1995-01..2025-12**, 0 NULLs. 1 county uses the nearest-cell fallback.
- Variables, taken from the NetCDF names and `units` attributes: `RootMoist` (kg m-2, root-zone soil moisture), `SoilM_0_10cm/10_40cm/40_100cm/100_200cm` (kg m-2), `Evap` (kg m-2, total evapotranspiration), `PotEvap`, `TVeg`, `ESoil`, `ECanop` (W m-2) and `Rainf` (kg m-2). Per-column units are in the SQL comments.
- The temporal aggregation of `Evap`/`Rainf` (monthly total vs mean) is not stated in the file attributes; the magnitudes (Jun about 99 kg m-2 Evap) look like monthly totals — **needs check against the NLDAS README before use**. W m-2 variables are rates.
- Sanity check (county mean, tier-1 average): July 2012 RootMoist 283.5 vs July 2013 357.1 kg m-2, so the 2012 drought is visible.
- Timing: 528 s for 372 files. The Noah LSM is model output, not an observation, and has coarse resolution: context only.

## Limits and constraints
- Rate stayed within 2 req/s per host and 8 parallel downloads. `/srv/hackathon/data` is 17 GB (limit 190 GB).
- DB: `county_imerg_daily` 1.0 GB, `county_nldas_monthly` 52 MB.
- No sudo, docker or push was used. No data files are committed.

## Licence / citation
- NASA GES DISC open data (Earthdata Login required to download). Access date 2026-11-15.
- IMERG: Huffman, G.J., et al., GPM IMERG Final Precipitation L3 1 day 0.1 degree x 0.1 degree V07, GES DISC, DOI 10.5067/GPM/IMERGDF/DAY/07.
- NLDAS-2 Noah: Xia, Y., et al., NLDAS Noah Land Surface Model L4 Monthly 0.125 x 0.125 degree V2.0, GES DISC. **DOI: not read from the file attributes (`DOI` empty); not confirmed.** Look it up on the GES DISC collection page.
