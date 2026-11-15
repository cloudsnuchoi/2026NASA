"""Independently check MAT2 inputs/calculations; does not run MATLAB or write data.

Usage: python -m data_pipeline.matlab_yoonsung_smoke --input-dir PATH
Optional --output-dir checks MATLAB summary CSVs after a teammate presses Run.
"""
from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from datetime import datetime, timezone
import shutil
from pathlib import Path
from statistics import mean


def read(folder, name):
    with (folder / name).open(newline='', encoding='utf-8-sig') as stream:
        rows = list(csv.DictReader(stream))
    assert rows, f'Empty input: {name}'
    assert all(len(r['county_fips']) == 5 for r in rows if 'county_fips' in r)
    return rows


def number(value):
    return float(value) if value.strip() else math.nan


def near(actual, expected):
    assert math.isclose(actual, expected, rel_tol=1e-7, abs_tol=1e-7), (actual, expected)


def quantile(values, p):
    values = sorted(v for v in values if math.isfinite(v))
    if not values:
        return math.nan
    index = (len(values) - 1) * p
    lo, hi = math.floor(index), math.ceil(index)
    return values[lo] + (index - lo) * (values[hi] - values[lo])


def check(folder, output=None, expected_dir=None):
    fields = read(folder, 'fields_20.csv')
    mapping = {r['field_id']: r['county_fips'] for r in fields}
    assert len(mapping) == len(fields), 'Duplicate field mapping'
    counties = sorted(set(mapping.values()))
    engine = defaultdict(list)
    seen = set()
    for row in read(folder, 'engine_2012_deficit.csv'):
        if row['strategy_code'] == 'A':
            assert row['field_id'] not in seen, 'Duplicate strategy A field'
            seen.add(row['field_id'])
            value = number(row['season_water_deficit_mm'])
            if math.isfinite(value):
                engine[mapping[row['field_id']]].append(value)
    monthly = defaultdict(list)
    for row in read(folder, 'county_nldas_2012.csv'):
        monthly[row['county_fips']].append(row)
    pairs, nldas_expected = [], {}
    baseline_years = set(range(1995, 2025)) - {2012}
    for county in counties:
        rows = monthly[county]
        assert len({r['month'] for r in rows}) == len(rows), 'Duplicate NLDAS month'
        summaries = {}
        for column in ('mjjas_2012_rootmoist_kg_m2', 'baseline_mjjas_rootmoist_kg_m2', 'anomaly_2012_kg_m2'):
            values = {number(r[column]) for r in rows if math.isfinite(number(r[column]))}
            assert len(values) == 1, f'Missing/inconsistent summary: {county}/{column}'
            summaries[column] = values.pop()
        growing = [r for r in rows if 5 <= int(r['month'][5:7]) <= 9]
        target = [number(r['rootmoist_kg_m2']) for r in growing if r['month'][:4] == '2012']
        baseline = [number(r['rootmoist_kg_m2']) for r in growing if int(r['month'][:4]) in baseline_years]
        assert len(target) == 5 and len(baseline) == 29 * 5
        near(summaries['mjjas_2012_rootmoist_kg_m2'], mean(target))
        near(summaries['baseline_mjjas_rootmoist_kg_m2'], mean(baseline))
        anomaly = summaries['anomaly_2012_kg_m2']
        near(anomaly, mean(target) - mean(baseline))
        deficit = mean(engine[county])
        pairs.append((anomaly, deficit))
        nldas_expected[county] = (anomaly, deficit)
    xs, ys = zip(*pairs)
    dx, dy = [x-mean(xs) for x in xs], [y-mean(ys) for y in ys]
    r = sum(x*y for x, y in zip(dx, dy)) / math.sqrt(sum(x*x for x in dx)*sum(y*y for y in dy))
    seasons = read(folder, 'season_climate_1995_2025.csv')
    for county in counties:
        rows = [row for row in seasons if row['county_fips'] == county]
        assert {int(row['year']) for row in rows} == set(range(1995, 2026)) and len(rows) == 31
        for raw, anomaly in [('precip_mm', 'precip_anomaly_mm'), ('ET0_mm', 'ET0_anomaly_mm')]:
            baseline = mean(number(row[raw]) for row in rows if int(row['year']) in baseline_years)
            for row in rows:
                near(number(row[anomaly]), number(row[raw]) - baseline)
    flags = read(folder, 'engine_p90_years.csv')
    by_field = defaultdict(list)
    p90_union = defaultdict(list)
    for row in flags:
        assert row['season'] == 'engine_scored_year'
        by_field[row['field_id']].append(row)
        assert mapping[row['field_id']] == row['county_fips']
        p90_union[(row['county_fips'], int(row['year']))].append(int(row['is_p90']))
    assert set(by_field) == set(mapping)
    for field, rows in by_field.items():
        assert len(rows) == 28 and {int(row['year']) for row in rows} == set(range(1998, 2026)), field
        threshold = quantile([number(row['season_water_deficit_mm']) for row in rows], .9)
        for row in rows:
            near(number(row['p90_threshold_mm']), threshold)
            assert int(row['is_p90']) == int(number(row['season_water_deficit_mm']) >= threshold)
    groups = defaultdict(list)
    for filename, kind, identity in [('geos_s2s_next_season.csv', 'geos', 'member'), ('historical_31yr_distribution.csv', 'history', 'year')]:
        for row in read(folder, filename):
            assert row['season'] in ('MAM', 'JJ')
            assert row['variable'] in ('pr', 'tas')
            assert row['unit'] == {'pr': 'mm/day', 'tas': 'degC'}[row['variable']]
            near(number(row['anomaly']), number(row['value']) - number(row['baseline_value']))
            key = (row['county_fips'], row['season'], row['variable'], kind)
            assert row[identity] not in {item[0] for item in groups[key]}, 'Duplicate distribution sample'
            groups[key].append((row[identity], number(row['anomaly'])))
    assert len(groups) == len(counties)*2*2*2
    for key, samples in groups.items():
        assert len(samples) == (10 if key[3] == 'geos' else 31), key
        assert all(math.isfinite(v) for _, v in samples), key
    expected = {}
    nldas_rows = []
    for county in counties:
        source = monthly[county][0]
        anomaly, deficit = nldas_expected[county]
        nldas_rows.append(dict(
            county_fips=county,
            county_label=next(row['county_label'] for row in fields if row['county_fips'] == county),
            n_finite_fields=len(engine[county]), engine_A_deficit_2012_mm=deficit,
            mjjas_2012_rootmoist_kg_m2=number(source['mjjas_2012_rootmoist_kg_m2']),
            baseline_mjjas_rootmoist_kg_m2=number(source['baseline_mjjas_rootmoist_kg_m2']),
            anomaly_2012_kg_m2=anomaly, pearson_r=r, n_counties_for_r=len(counties)))
    expected['nldas_vs_engine_2012.csv'] = nldas_rows
    seasonal_rows = []
    for row in seasons:
        row = dict(row)
        key = (row['county_fips'], int(row['year']))
        row['is_2012'] = int(row['year'] == '2012')
        row['is_p90'] = int(any(p90_union[key])) if key in p90_union else ''
        row['p90_status'] = (
            'union of per-field annual scored engine P90 years' if key in p90_union
            else 'information gap: no scored engine year (1995-1997 need spinup)')
        seasonal_rows.append(row)
    expected['season_anomaly_1995_2025.csv'] = seasonal_rows
    forecast_rows = read(folder, 'geos_s2s_next_season.csv')
    distribution_rows = []
    for county in counties:
        for season in ('MAM', 'JJ'):
            for variable in ('pr', 'tas'):
                row = dict(county_fips=county, season=season,
                           period=next(item['period'] for item in forecast_rows
                                       if (item['county_fips'], item['season']) == (county, season)),
                           variable=variable, unit={'pr': 'mm/day', 'tas': 'degC'}[variable],
                           n_members=10, n_history_years=31)
                for kind in ('geos', 'history'):
                    values = [value for _, value in groups[(county, season, variable, kind)]]
                    for name, probability in [('p10', .1), ('p50', .5), ('p90', .9)]:
                        row[f'{kind}_{name}'] = quantile(values, probability)
                row['status'] = 'complete: 10 members and 31 historical years'
                row['distribution_basis'] = 'anomaly relative to exported POWER baseline'
                distribution_rows.append(row)
    expected['s2s_vs_history_box.csv'] = distribution_rows
    if expected_dir:
        expected_dir.mkdir(parents=True, exist_ok=True)
        existing = [expected_dir / name for name in expected if (expected_dir / name).exists()]
        if existing:
            archive = expected_dir / 'old' / datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
            archive.mkdir(parents=True, exist_ok=False)
            for path in existing:
                shutil.move(str(path), str(archive / path.name))
        for name, rows in expected.items():
            with (expected_dir / name).open('w', newline='', encoding='utf-8') as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
        print(f'Saved Python reference CSVs: {expected_dir} (not MATLAB-produced outputs)')
    if output:
        for row in read(output, 'nldas_vs_engine_2012.csv'):
            anomaly, deficit = nldas_expected[row['county_fips']]
            near(number(row['anomaly_2012_kg_m2']), anomaly)
            near(number(row['engine_A_deficit_2012_mm']), deficit)
            near(number(row['pearson_r']), r)
            assert int(row['n_counties_for_r']) == len(counties)
        result = read(output, 'season_anomaly_1995_2025.csv')
        assert len(result) == len(seasons)
        for row in result:
            key = (row['county_fips'], int(row['year']))
            if key in p90_union:
                assert int(row['is_p90']) == int(any(p90_union[key]))
            else:
                assert not math.isfinite(number(row['is_p90']))
        for row in read(output, 's2s_vs_history_box.csv'):
            for kind in ('geos', 'history'):
                values = [v for _, v in groups[(row['county_fips'], row['season'], row['variable'], kind)]]
                for name, p in [('p10', .1), ('p50', .5), ('p90', .9)]:
                    near(number(row[f'{kind}_{name}']), quantile(values, p))
    print(f'PASS: {len(counties)} county means, NLDAS r={r:.8f}; {len(seasons)} seasonal rows; {len(flags)} field/year P90 flags; {len(groups)} distributions (10/31 samples).')
    print('1988 outside 1995-2025 export; JJ excludes August. MATLAB runtime/PNG rendering not verified by this check.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--expected-dir', type=Path, help='Write three Python reference CSVs, archiving prior copies')
    args = parser.parse_args()
    check(args.input_dir, args.output_dir, args.expected_dir)
