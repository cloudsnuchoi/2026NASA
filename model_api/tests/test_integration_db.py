"""Integration test against the live read-only DB. Skipped when the DB is unreachable."""

import pytest

from model_api import db

pytestmark = pytest.mark.skipif(not db.available(), reason="fieldshift DB not reachable")


def test_simulate_real_demo_field_and_tier1_county():
    from fastapi.testclient import TestClient

    from model_api.main import app

    app.state.repo = None
    c = TestClient(app)
    fields = c.get("/fields").json()["fields"]
    story = [f for f in fields if f["county_fips"].strip() == "19169"]
    assert len(story) == 12 and fields[:12] == story  # Story first, then contrast fields (docs/CONTRAST-FIELDS.md)
    r = c.post("/simulate", json={"field_id": fields[0]["field_id"], "n": 200})
    assert r.status_code == 200, r.text
    sim = r.json()
    assert [s["strategy_code"] for s in sim["strategies"]] == ["A", "B", "C", "D"]
    assert sim["tier"] == "field" and sim["inputs"]["awc_cm_cm"] is not None
    r2 = c.post("/simulate", json={"county_fips": "17113", "n": 100})
    assert r2.status_code == 200 and r2.json()["tier"] == "county"
