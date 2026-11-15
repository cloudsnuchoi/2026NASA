"""Export immutable, read-only DB/API snapshots for the L2 MATLAB lane."""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
from urllib.request import Request, urlopen

ROOT = Path('/srv/hackathon/data/processed/v1/matlab')
API = os.environ.get('MODEL_API_BASE', 'http://127.0.0.1:8090')


def api(path, payload=None):
    request = Request(API + path, data=json.dumps(payload).encode() if payload is not None else None,
                      headers={'Content-Type': 'application/json'})
    with urlopen(request, timeout=180) as response:
        return json.load(response)


def sql_csv(query):
    env = dict(os.environ)
    env.update(PGHOST=env.get('PGHOST', '127.0.0.1'), PGPORT=env.get('PGPORT', '5433'),
               PGUSER=env.get('PGUSER', 'hk'), PGDATABASE=env.get('PGDATABASE', 'fieldshift'))
    return subprocess.check_output(['psql', '-X', '-v', 'ON_ERROR_STOP=1', '-c',
                                    f'COPY ({query}) TO STDOUT WITH CSV HEADER'], env=env, text=True)


def write_csv(path, rows, columns):
    with path.open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    path.chmod(0o644)


def main():
    inputs = ROOT / 'inputs'
    inputs.mkdir(exist_ok=True)
    inputs.chmod(0o755)
    for name in ('woochan', 'yoonsung', 'jimin', 'jieun'):
        folder = ROOT / 'outputs' / name
        folder.mkdir(parents=True, exist_ok=True)
        if folder.stat().st_mode & 0o777 != 0o777:
            folder.chmod(0o777)
    demo = api('/fields')['fields']
    ids = [f['field_id'] for f in demo]
    if len(ids) != 20 or not all(x.isdigit() for x in ids):
        raise ValueError('Expected exactly 20 numeric CSB IDs')
    selected = ','.join("'" + x + "'" for x in ids)
    vertices = ', '.join(f'ST_Y(ST_PointN(r,{i})) AS v{i}_lat, ST_X(ST_PointN(r,{i})) AS v{i}_lon'
                         for i in range(1, 5))
    query = f'''SELECT field_id, county_fips, county_label, lat, lon, {vertices} FROM
        (SELECT f.field_id, f.county_fips, c.name AS county_label, ST_Y(f.centroid) AS lat,
        ST_X(f.centroid) AS lon, ST_ExteriorRing(ST_Transform(ST_OrientedEnvelope(ST_Transform(f.geom,5070)),4326)) AS r
        FROM fields f JOIN county c USING(county_fips) WHERE field_id IN ({selected})) q ORDER BY field_id'''
    for filename, query in [('fields_20.csv', query), ('ndvi_hls_20fields.csv',
            f'SELECT field_id,date,product,ndvi,valid_frac FROM field_ndvi_hls WHERE field_id IN ({selected}) ORDER BY field_id,date,product')]:
        with (inputs / filename).open('x') as stream:
            stream.write(sql_csv(query))
        (inputs / filename).chmod(0o644)
    deficits, quantiles, provenance = [], [], []
    for fid in ids:
        backtest = api(f'/validation/backtest?field_id={fid}&year=2012')
        for result in backtest['results']:
            deficits.append(dict(field_id=fid, strategy_code=result['strategy_code'], **{
                key: result['metrics'].get(key) for key in ('season_water_deficit_mm', 'stress_days', 'winter_bare_days')}))
        compare = api('/strategies/compare', {'field_id': fid, 'n': 500, 'seed': 42})
        provenance.append({'field_id': fid, 'run_id': compare['run_id'], 'period': compare['period']})
        for card in compare['strategies']:
            quantiles.append(dict(field_id=fid, strategy_code=card['strategy_code'], metric='composite_index',
                                  **{q: card[q] for q in ('p10', 'p50', 'p90')}, unit=compare['unit']))
            for metric in ('vegetation_pct', 'water_use_pct', 'revenue_pct'):
                quantiles.append(dict(field_id=fid, strategy_code=card['strategy_code'], metric=metric,
                                      **card['display'][metric], unit='percent_relative_to_A'))
    write_csv(inputs / 'engine_2012_deficit.csv', deficits,
              ['field_id', 'strategy_code', 'season_water_deficit_mm', 'stress_days', 'winter_bare_days'])
    write_csv(inputs / 'engine_p10p90_20fields.csv', quantiles,
              ['field_id', 'strategy_code', 'metric', 'p10', 'p50', 'p90', 'unit'])
    target = inputs / 'drought_2012_county.csv'
    if target.exists():
        raise FileExistsError(target)
    shutil.copyfile(ROOT / target.name, target)
    target.chmod(0o644)
    (inputs / 'engine_provenance.json').write_text(json.dumps(provenance, indent=2))
    print(f'Exported {len(ids)} fields, {len(deficits)} backtests, {len(quantiles)} quantiles')


if __name__ == '__main__':
    main()
