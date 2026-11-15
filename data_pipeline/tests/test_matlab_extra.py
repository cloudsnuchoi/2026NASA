"""MAT2 snapshot contracts and staging safety; no DB/API calls or source writes.

Real-data checks skip only when exports have not arrived. Stage tests use tiny
local files: the independent jimin/yoonsung algorithm smoke modules own science
output comparisons, while these checks validate exported input arithmetic.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import fmean

import pytest

from data_pipeline import matlab_export, matlab_extra_stage

INPUTS = Path('/srv/hackathon/data/processed/v1/matlab/inputs')
COUNTIES = {'17113', '19169', '31109', '39159'}
YEARS = set(range(1995, 2026))
BASELINE_YEARS = set(range(1995, 2025)) - {2012}
SNAPSHOTS = (
    'county_nldas_2012.csv', 'season_climate_1995_2025.csv',
    'engine_p90_years.csv', 'geos_s2s_next_season.csv',
    'historical_31yr_distribution.csv', 'engine_strategyB_assumptions.csv',
    'mat2_provenance.json',
)


@pytest.fixture(scope='module')
def snapshots():
    missing = [name for name in (*SNAPSHOTS, 'fields_20.csv') if not (INPUTS / name).is_file()]
    if missing:
        pytest.skip(f'MAT2 immutable exports not ready: {missing}')
    return INPUTS


def read_rows(root, name):
    with (root / name).open(encoding='utf-8', newline='') as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        assert rows and all(None not in row for row in rows), name
        return rows


def grouped(rows, *keys):
    result = defaultdict(list)
    for row in rows:
        result[tuple(row[k] for k in keys)].append(row)
    return result


def finite(row, key):
    value = float(row[key])
    assert math.isfinite(value), (key, row)
    return value


def test_real_snapshot_hashes(snapshots):
    provenance = json.loads((snapshots / 'mat2_provenance.json').read_text())
    assert set(provenance['files']) == set(SNAPSHOTS[:-1])
    for name, expected in provenance['files'].items():
        assert hashlib.sha256((snapshots / name).read_bytes()).hexdigest() == expected, name


def test_nldas_monthly_coverage_and_29year_baseline(snapshots):
    rows = read_rows(snapshots, 'county_nldas_2012.csv')
    assert len(rows) == 1488
    counties = grouped(rows, 'county_fips')
    assert {c for c, in counties} == COUNTIES
    assert len(BASELINE_YEARS) == 29
    for block in counties.values():
        months = {r['month'][:7] for r in block}
        assert len(block) == len(months) == 31 * 12
        assert months == {f'{year}-{month:02}' for year in YEARS for month in range(1, 13)}
        seasonal = {
            year: fmean(finite(r, 'rootmoist_kg_m2') for r in block
                        if int(r['month'][:4]) == year and 5 <= int(r['month'][5:7]) <= 9)
            for year in YEARS
        }
        baseline = fmean(seasonal[year] for year in BASELINE_YEARS)
        for r in block:
            assert finite(r, 'mjjas_2012_rootmoist_kg_m2') == pytest.approx(seasonal[2012])
            assert finite(r, 'baseline_mjjas_rootmoist_kg_m2') == pytest.approx(baseline)
            assert finite(r, 'anomaly_2012_kg_m2') == pytest.approx(seasonal[2012] - baseline)


def test_climate_31year_coverage_and_anomalies(snapshots):
    rows = read_rows(snapshots, 'season_climate_1995_2025.csv')
    assert len(rows) == 124
    counties = grouped(rows, 'county_fips')
    assert {c for c, in counties} == COUNTIES
    for block in counties.values():
        assert len(block) == 31
        assert {int(r['year']) for r in block} == YEARS
        for metric, anomaly in [('precip_mm', 'precip_anomaly_mm'), ('ET0_mm', 'ET0_anomaly_mm')]:
            baseline = fmean(finite(r, metric) for r in block if int(r['year']) in BASELINE_YEARS)
            for r in block:
                assert finite(r, metric) >= 0
                assert finite(r, anomaly) == pytest.approx(finite(r, metric) - baseline)


def test_p90_years_match_annual_scored_deficit_quantile(snapshots):
    rows = read_rows(snapshots, 'engine_p90_years.csv')
    assert len(rows) == 560
    assert {r['county_fips'] for r in rows} == COUNTIES
    fields = {r['field_id']: r['county_fips'] for r in read_rows(snapshots, 'fields_20.csv')}
    by_field = grouped(rows, 'field_id')
    assert set(by_field) == {(fid,) for fid in fields}
    required = {'field_id', 'county_fips', 'year', 'is_p90', 'season',
                'season_water_deficit_mm', 'p90_threshold_mm', 'status', 'modelled_crop', 'window'}
    assert required <= rows[0].keys()
    for (fid,), block in by_field.items():
        assert len(block) == 28
        # The first three weather years supply spin-up, not scored results.
        assert {int(r['year']) for r in block} == set(range(1998, 2026))
        deficits = sorted(finite(r, 'season_water_deficit_mm') for r in block)
        assert deficits[0] >= 0
        # Independently reproduce numpy.quantile(.9, method='linear') using
        # adjacent order statistics, without calling exporter/engine helpers.
        index = (len(deficits) - 1) * 0.9
        lo, hi = math.floor(index), math.ceil(index)
        threshold = deficits[lo] + (index - lo) * (deficits[hi] - deficits[lo])
        for row in block:
            assert row['county_fips'] == fields[fid]
            assert row['season'] == 'engine_scored_year'
            assert row['status'] and row['modelled_crop'] and row['window']
            assert finite(row, 'p90_threshold_mm') == pytest.approx(threshold)
            flag = finite(row, 'is_p90')
            assert flag in (0, 1)
            assert bool(flag) == (finite(row, 'season_water_deficit_mm') >= threshold)


def test_geos_members_match_history_by_county_season_variable(snapshots):
    history = read_rows(snapshots, 'historical_31yr_distribution.csv')
    forecast = read_rows(snapshots, 'geos_s2s_next_season.csv')
    assert len(history) == 496
    assert len(forecast) == 160
    hist_groups = grouped(history, 'county_fips', 'season', 'variable')
    geos_groups = grouped(forecast, 'county_fips', 'season', 'variable')
    expected = {(c, s, v) for c in COUNTIES for s in ('MAM', 'JJ') for v in ('pr', 'tas')}
    assert set(hist_groups) == set(geos_groups) == expected
    for key, block in hist_groups.items():
        assert len(block) == 31
        assert {int(r['year']) for r in block} == YEARS
        members = geos_groups[key]
        assert len(members) == len({r['member'] for r in members}) == 10
        assert all(r['member'] for r in members)
        baseline = fmean(finite(r, 'value') for r in block)
        suffix = '03/05' if key[1] == 'MAM' else '06/07'
        for r in block + members:
            assert r['unit'] == ('mm/day' if key[2] == 'pr' else 'degC')
            assert r['period'] == f"{r['year'] if 'year' in r else '2027'}-{suffix}"
            assert finite(r, 'baseline_value') == pytest.approx(baseline)
            assert finite(r, 'anomaly') == pytest.approx(finite(r, 'value') - baseline)


def test_strategy_assumptions_cover_all_exported_fields(snapshots):
    fields = read_rows(snapshots, 'fields_20.csv')
    rows = read_rows(snapshots, 'engine_strategyB_assumptions.csv')
    assert len(rows) == 220
    by_field = grouped(rows, 'field_id')
    assert set(by_field) == {(r['field_id'],) for r in fields}
    assert len(by_field) == 20
    expected = {'crop_calendar', 'rye_residue_cover_frac', 'baseline_rotation', 'elevation_m', 'weather',
                'corn_plant_doy', 'corn_harvest_doy', 'soy_plant_doy', 'soy_harvest_doy',
                'rye_plant_after_harvest_days', 'rye_terminate_before_plant_days'}
    provenance = json.loads((snapshots / 'mat2_provenance.json').read_text())
    for (fid,), block in by_field.items():
        assert len(block) == len(expected)
        assert {r['item'] for r in block} == expected
        assert all(r['source'] and r['run_id'] for r in block)
        # The raw calendar is documented in source, with null value/unit;
        # dimensionless rotation and weather labels also have no unit.
        for r in block:
            if r['item'] == 'crop_calendar':
                assert r['value'] == r['unit'] == ''
            else:
                assert r['value']
                if r['item'] not in {'baseline_rotation', 'weather'}:
                    assert r['unit']
        assert len({r['run_id'] for r in block}) == 1
        exported = {r['item']: r for r in block}
        raw = {r['item']: r for r in provenance['engine_assumptions'][fid]}
        for item in expected & raw.keys():
            for key in ('value', 'unit', 'source'):
                value = raw[item][key]
                assert exported[item][key] == ('' if value is None else str(value))


def test_write_csv_exclusive_create_preserves_existing_bytes(tmp_path):
    path = tmp_path / 'export.csv'
    matlab_export.write_csv(path, [{'value': None}], ['value'])
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        matlab_export.write_csv(path, [{'value': 0}], ['value'])
    assert path.read_bytes() == original
    assert read_rows(tmp_path, path.name) == [{'value': ''}]


@pytest.mark.parametrize('name', SNAPSHOTS)
def test_extra_export_preflights_every_existing_snapshot(tmp_path, snapshots, name):
    inputs = tmp_path / 'inputs'
    inputs.mkdir()
    (inputs / 'fields_20.csv').write_bytes((snapshots / 'fields_20.csv').read_bytes())
    protected = inputs / name
    protected.write_bytes(b'existing immutable snapshot\n')
    before = {p.name: p.read_bytes() for p in inputs.iterdir()}
    # Actual exporter, without API/DB mocks: its full-batch guard must raise
    # before issuing any query or creating any other snapshot.
    with pytest.raises(FileExistsError) as exc:
        matlab_export.extra_sets(tmp_path)
    assert str(protected) in str(exc.value)
    assert {p.name: p.read_bytes() for p in inputs.iterdir()} == before


@pytest.fixture
def stage_tree(tmp_path):
    repo, root = tmp_path / 'repo', tmp_path / 'data'
    (repo / 'matlab').mkdir(parents=True)
    for names in matlab_extra_stage.SCRIPTS.values():
        for name in names:
            (repo / 'matlab' / name).write_text(f'% upstream {name}\n')
    return repo, root


def tree_bytes(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}


@pytest.mark.parametrize('tracked', [False, True], ids=['untracked-user-file', 'modified-tracked-file'])
@pytest.mark.parametrize('user,name', [(u, n) for u, ns in matlab_extra_stage.SCRIPTS.items() for n in ns])
def test_stage_modification_blocks_entire_batch(stage_tree, tracked, user, name):
    repo, root = stage_tree
    if tracked:
        matlab_extra_stage.stage(root, repo)
        # Every upstream script changes; no earlier target may be updated
        # before the protected script later in the batch is checked.
        for source in (repo / 'matlab').glob('*.m'):
            source.write_text(source.read_text() + '% new upstream version\n')
    folder = root / 'work' / user
    folder.mkdir(parents=True, exist_ok=True)
    protected = folder / name
    protected.write_text('% teammate edits must survive\n')
    before = tree_bytes(root)
    with pytest.raises(FileExistsError, match='Teammate modification preserved'):
        matlab_extra_stage.stage(root, repo)
    assert tree_bytes(root) == before
    if not tracked:
        assert set(root.rglob('.agent_sha.json')) == set()


def test_stage_updates_owned_files_and_preserves_unknown_ledger_entries(stage_tree):
    repo, root = stage_tree
    matlab_extra_stage.stage(root, repo)
    unknown = {'teammate_script.m': 'unrecognized historical checksum', 'notes.txt': 'another owner'}
    for user, names in matlab_extra_stage.SCRIPTS.items():
        folder = root / 'work' / user
        ledger = folder / '.agent_sha.json'
        hashes = json.loads(ledger.read_text())
        hashes.update(unknown)
        ledger.write_text(json.dumps(hashes))
        (folder / 'teammate_script.m').write_text('% unrelated teammate work\n')
        for name in names:
            source = repo / 'matlab' / name
            source.write_text(source.read_text() + '% upstream update\n')
    matlab_extra_stage.stage(root, repo)
    for user, names in matlab_extra_stage.SCRIPTS.items():
        folder = root / 'work' / user
        hashes = json.loads((folder / '.agent_sha.json').read_text())
        assert all(hashes[k] == v for k, v in unknown.items())
        assert (folder / 'teammate_script.m').read_text() == '% unrelated teammate work\n'
        for name in names:
            assert (folder / name).read_bytes() == (repo / 'matlab' / name).read_bytes()
            assert hashes[name] == matlab_extra_stage.sha(folder / name)
    before = tree_bytes(root)
    matlab_extra_stage.stage(root, repo)
    assert tree_bytes(root) == before


def test_stage_missing_last_source_does_not_place_partial_batch(stage_tree):
    repo, root = stage_tree
    last_name = list(matlab_extra_stage.SCRIPTS.values())[-1][-1]
    (repo / 'matlab' / last_name).unlink()
    with pytest.raises(FileNotFoundError):
        matlab_extra_stage.stage(root, repo)
    assert not root.exists()
