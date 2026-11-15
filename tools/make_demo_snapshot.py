"""Generate JSON snapshots for the static GitHub Pages demo (docs/demo/snapshot/).

Usage: python3 tools/make_demo_snapshot.py [--web http://127.0.0.1:8095] [--api http://127.0.0.1:8090] [--no-explain]

- model_api endpoints are read from --api (read-only), /quick and /fields-geo from the web front --web.
- File key = METHOD_path (slashes -> "_", query appended) + "_" + FNV-1a-32 hex of the JSON body
  (compact separators, crops sorted Corn<Soy<Wheat). docs/demo/app.js computes the same key.
- No secrets are written: responses only; a final scan rejects key/token-looking strings.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "docs" / "demo" / "snapshot"
COUNTIES = ["19169", "17113", "31109", "39159"]
CROPSETS = [["Corn", "Soy"], ["Corn", "Soy", "Wheat"]]
CROP_ORDER = {"Corn": 0, "Soy": 1, "Wheat": 2}


def fnv1a(s: str) -> str:
    h = 0x811C9DC5
    for b in s.encode("utf-8"):
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"


def canon(body: dict) -> str:
    b = dict(body)
    if isinstance(b.get("crops"), list):
        b["crops"] = sorted(b["crops"], key=lambda c: CROP_ORDER.get(c, 9))
    return json.dumps(b, separators=(",", ":"), ensure_ascii=False)


def key(method: str, path: str, body: dict | None = None) -> str:
    k = method + "_" + re.sub(r"[^A-Za-z0-9_.=-]", "_", path.strip("/"))
    if body is not None:
        k += "_" + fnv1a(canon(body))
    return k + ".json"


def simplify(pts, n=60):  # same rule as frontend/app.js
    if len(pts) <= n:
        return pts
    s = math.ceil(len(pts) / n)
    return [p for i, p in enumerate(pts) if i % s == 0]


def call(base: str, path: str, body: dict | None = None, timeout=180):
    data = canon(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data, {"content-type": "application/json"} if data else {})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--web", default="http://127.0.0.1:8095")
    ap.add_argument("--api", default="http://127.0.0.1:8090")
    ap.add_argument("--no-explain", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    index: dict[str, str] = {}

    def save(method, path, body, base, timeout=180):
        try:
            j = call(base, path, body, timeout)
        except Exception as exc:  # noqa: BLE001
            print("SKIP", method, path, type(exc).__name__, exc, file=sys.stderr)
            return None
        k = key(method, path, body)
        (OUT / k).write_text(json.dumps(j, separators=(",", ":"), ensure_ascii=False))
        index[k] = method + " " + path
        print("ok", k)
        return j

    geo = save("GET", "/fields-geo", None, a.web + "/api")
    save("GET", "/fields", None, a.api)
    save("GET", "/glossary", None, a.api)
    fids = [f["field_id"] for f in geo["fields"]]
    jobs = []
    for fid in fids:
        jobs += [
            ("GET", f"/field/{fid}/profile", None, a.api),
            ("GET", f"/field/{fid}/climate/outlook", None, a.api),
            ("GET", f"/validation/backtest?field_id={fid}&year=2012", None, a.api),
            ("POST", "/simulate", {"field_id": fid, "n": 500, "seed": 42}, a.api),
            ("POST", "/strategies/compare", {"field_id": fid}, a.api),
        ]
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(lambda j: save(*j), jobs))
    presets = [next(f for f in geo["fields"] if f["county_fips"] == c) for c in COUNTIES]
    qjobs = [("POST", "/quick", {"polygon": simplify(f["ring"]), "crops": cs}, a.web + "/api", 300)
             for f in presets for cs in CROPSETS]
    with ThreadPoolExecutor(2) as ex:
        list(ex.map(lambda j: save(*j), qjobs))
    if not a.no_explain:
        ejobs = [("POST", "/explain", {"field_id": f["field_id"], "strategy_code": c, "lang": "en",
                  "question": f"Why might strategy {c} fit or not fit this field, and what should I check locally?"}, a.api, 120)
                 for f in presets for c in "ABCD"]
        with ThreadPoolExecutor(4) as ex:
            list(ex.map(lambda j: save(*j), ejobs))
    meta = {"generated": "2026-11-15", "source": "ART FARM model_api + FAO-56 quick screen (read-only)",
            "presets": {f["county_fips"]: f["field_id"] for f in presets}, "files": index}
    (OUT / "index.json").write_text(json.dumps(meta, indent=1))
    # secret scan
    bad = re.compile(r"(sk-[A-Za-z0-9]{16,}|api[_-]?key\"?\s*[:=]|bearer\s+[A-Za-z0-9._-]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{20,})", re.I)
    hits = [p.name for p in OUT.glob("*.json") if bad.search(p.read_text())]
    size = sum(p.stat().st_size for p in OUT.glob("*.json"))
    print(f"files={len(index)} size={size/1e6:.2f}MB secret_hits={hits}")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
