"""Prefetch every external API response FieldShift_V8_batch.m needs (20 fields).

MATLAB in the browser sessions cannot reliably reach epqs.nationalmap.gov /
Open-Meteo within its 8-12 s timeouts, so we fetch once on the server and the
MATLAB batch reads ``v8_api_cache/<field_id>/*.json`` first.

URLs are byte-identical to the V8 ``sprintf`` formats (same parameters,
same %.6f / %.4f rounding). Raw response bodies are saved unchanged; nothing
is filled or interpolated. Null values stay null (-> information gap in V8).

Usage: python data_pipeline/v8_prefetch.py [--only FIELD_ID ...] [--force]
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

INPUTS = Path("/srv/hackathon/data/processed/v1/matlab/inputs")
CACHE = INPUTS / "v8_api_cache"
TIMEOUT_S = 60
RETRIES = 4
MIN_INTERVAL_S = 0.5  # <= 2 requests/s per host
UA = "FieldShift_AgriEngine_MATLAB/1.0 (ART FARM hackathon prefetch)"

_last_call: dict[str, float] = {}


def epqs_url(lat: float, lon: float) -> str:
    return (
        f"https://epqs.nationalmap.gov/v1/json?x={lon:.6f}&y={lat:.6f}"
        "&wkid=4326&units=Meters"
    )


def power_url(lat: float, lon: float) -> str:
    return (
        "https://power.larc.nasa.gov/api/temporal/daily/point?"
        "parameters=T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,ALLSKY_SFC_SW_DWN,GWETROOT"
        f"&community=ag&longitude={lon:.4f}&latitude={lat:.4f}"
        "&start=20160101&end=20251231&format=JSON"
    )


def nws_points_url(lat: float, lon: float) -> str:
    return f"https://api.weather.gov/points/{lat:.4f},{lon:.4f}"


def openmeteo_url(lat: float, lon: float) -> str:
    return (
        "https://climate-api.open-meteo.com/v1/climate?"
        f"latitude={lat:.4f}&longitude={lon:.4f}"
        "&start_date=2026-01-01&end_date=2039-12-31"
        "&models=MRI_AGCM3_2_S"
        "&daily=temperature_2m_mean,precipitation_sum,et0_fao_evapotranspiration"
    )


def _throttle(url: str) -> None:
    host = urlparse(url).netloc
    wait = _last_call.get(host, 0.0) + MIN_INTERVAL_S - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_call[host] = time.monotonic()


def fetch(url: str) -> tuple[int, object | None, str]:
    """Return (http_status, parsed_json_or_None, error_text)."""
    status, err = 0, ""
    for attempt in range(1, RETRIES + 1):
        _throttle(url)
        try:
            r = requests.get(
                url,
                timeout=TIMEOUT_S,
                headers={"User-Agent": UA, "Accept": "application/geo+json, application/json"},
            )
            status = r.status_code
            if r.ok:
                return status, r.json(), ""
            err = r.text[:300]
            if status in (400, 404):
                break
        except (requests.RequestException, ValueError) as exc:
            err = f"{type(exc).__name__}: {exc}"[:300]
        time.sleep(min(30, 2**attempt))
    return status, None, err


def fetch_field(row: dict, force: bool) -> list[dict]:
    fid = row["field_id"].strip()
    lats = [float(row[f"v{k}_lat"]) for k in range(1, 5)]
    lons = [float(row[f"v{k}_lon"]) for k in range(1, 5)]
    pin_lat, pin_lon = sum(lats) / 4, sum(lons) / 4  # V8: mean(lat4), mean(lon4)
    out = CACHE / fid
    out.mkdir(parents=True, exist_ok=True)

    jobs = [(f"epqs_{k + 1}", epqs_url(lats[k], lons[k])) for k in range(4)]
    jobs += [
        ("power", power_url(pin_lat, pin_lon)),
        ("nws_points", nws_points_url(pin_lat, pin_lon)),
        ("openmeteo", openmeteo_url(pin_lat, pin_lon)),
    ]
    records = []
    for name, url in jobs:
        records.append(_save(out, fid, name, url, force))
        if name == "nws_points":
            path = out / "nws_points.json"
            fc_url = ""
            if path.is_file():
                fc_url = json.loads(path.read_text())["properties"].get("forecast", "")
            if fc_url:
                records.append(_save(out, fid, "nws_forecast", fc_url, force))
            else:
                records.append(_rec(fid, "nws_forecast", "", 0, "no forecast URL"))
    return records


def _rec(fid: str, name: str, url: str, status: int, err: str) -> dict:
    return {
        "field_id": fid,
        "name": name,
        "url": url,
        "http_status": status,
        "ok": not err,
        "error": err,
        "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def _save(out: Path, fid: str, name: str, url: str, force: bool) -> dict:
    path = out / f"{name}.json"
    if path.is_file() and not force:
        rec = _rec(fid, name, url, 200, "")
        rec["cached"] = True
        return rec
    status, body, err = fetch(url)
    if body is not None:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(body))
        tmp.replace(path)
    rec = _rec(fid, name, url, status, err)
    print(f"{fid} {name:13s} {status} {'OK' if not err else 'FAIL ' + err[:80]}", flush=True)
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    with open(INPUTS / "fields_20.csv", newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if args.only:
        rows = [r for r in rows if r["field_id"].strip() in set(args.only)]
    CACHE.mkdir(parents=True, exist_ok=True)
    manifest_path = CACHE / "manifest.json"
    old = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {"files": []}
    by_key = {(r["field_id"], r["name"]): r for r in old.get("files", [])}
    for row in rows:
        for rec in fetch_field(row, args.force):
            if rec.pop("cached", False) and (rec["field_id"], rec["name"]) in by_key:
                continue
            by_key[(rec["field_id"], rec["name"])] = rec
    files = sorted(by_key.values(), key=lambda r: (r["field_id"], r["name"]))
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "script": "data_pipeline/v8_prefetch.py",
        "note": "Raw API bodies, unmodified. Nulls stay null (information gap).",
        "files": files,
    }
    manifest_path.write_text(json.dumps(manifest, indent=1))
    ok = sum(1 for f in files if f["ok"])
    print(f"manifest: {ok}/{len(files)} files OK")


if __name__ == "__main__":
    main()
