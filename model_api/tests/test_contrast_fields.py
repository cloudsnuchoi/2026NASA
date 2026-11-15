"""Contrast demo fields (docs/CONTRAST-FIELDS.md): demo fields must span >= 3 counties and give visibly different results.
Skipped when the fieldshift DB is unreachable."""

import pytest

from model_api import db, engine

pytestmark = pytest.mark.skipif(not db.available(), reason="fieldshift DB not reachable")


@pytest.fixture(scope="module")
def live_repo():
    from model_api.repo import PgRepo

    return PgRepo()


def test_demo_fields_span_three_counties_story_first(live_repo):
    rows = live_repo.list_fields(live_repo.demo_field_ids())
    fips = [r["county_fips"].strip() for r in rows]
    assert len(set(fips)) >= 3, fips
    assert fips[0] == "19169"


def test_composite_a_differs_between_demo_fields(live_repo):
    p50 = {}
    for fid in live_repo.demo_field_ids():
        sim = engine.simulate(live_repo, field_id=fid, n=200, seed=42, scenarios=False)
        p50[fid] = next(s for s in sim["strategies"] if s["strategy_code"] == "A")["composite"]["p50"]
    assert max(p50.values()) - min(p50.values()) > 0.02, p50
