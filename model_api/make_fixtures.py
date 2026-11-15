"""Write model_api/fixtures/*.json from the live DB (real data). Run: python -m model_api.make_fixtures"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from .main import app

FIELD = "191825003869023"  # Story County demo field (CSB 2018-2025 rev23)
OUT = Path(__file__).parent / "fixtures"

GETS = {
    "health": "/health",
    "fields": "/fields",
    "profile": f"/field/{FIELD}/profile",
    "bare_periods": f"/field/{FIELD}/bare-periods",
    "vulnerable_seasons": f"/field/{FIELD}/vulnerable-seasons",
    "climate_history": f"/field/{FIELD}/climate/history?years=5",
    "climate_outlook": f"/field/{FIELD}/climate/outlook",
    "county_19169": "/county/19169",
    "county_17113": "/county/17113",
    "locate_in": "/locate?lat=41.8658&lon=-93.5431",
    "locate_county_only": "/locate?lat=40.1&lon=-88.2",
    "locate_out": "/locate?lat=35.0&lon=-100.0",
    "glossary": "/glossary",
    "evidence_search": "/evidence/search?q=cereal%20rye&strategy=B",
    "backtest_2012": f"/validation/backtest?field_id={FIELD}&year=2012",
    "error_not_found": "/field/UNKNOWN/profile",
}
POSTS = {
    "compare": ("/strategies/compare", {"field_id": FIELD, "current_rotation": "C-S",
                                        "priorities": {"water": 0.3, "soil": 0.4, "stability": 0.2, "income": 0.1},
                                        "constraints": {"water_limited": False, "equipment": [], "market": []}}),
    "simulate": ("/simulate", {"field_id": FIELD, "n": 500, "seed": 42}),
    "simulate_county_17113": ("/simulate", {"county_fips": "17113", "n": 500, "seed": 42}),
    "rotations_candidates": ("/rotations/candidates", {"field_id": FIELD, "selected_options": ["cover_rye", "small_grain"]}),
}


def main() -> None:
    OUT.mkdir(exist_ok=True)
    c = TestClient(app)
    for name, path in GETS.items():
        r = c.get(path)
        (OUT / f"{name}.json").write_text(json.dumps(r.json(), indent=1, ensure_ascii=False, default=str) + "\n")
        print(r.status_code, name)
    for name, (path, body) in POSTS.items():
        r = c.post(path, json=body)
        data = r.json()
        if "latency_ms" in data:
            data["latency_ms"] = None  # keep fixtures stable
        (OUT / f"{name}.json").write_text(json.dumps(data, indent=1, ensure_ascii=False, default=str) + "\n")
        print(r.status_code, name)


if __name__ == "__main__":
    main()
