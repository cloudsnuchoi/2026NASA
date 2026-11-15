"""Read-only MATLAB/engine comparisons; missing/incompatible outputs never pass."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
import math
from pathlib import Path
from zoneinfo import ZoneInfo

from matlab_export import ROOT, api, sql_csv
import io


def read(path):
    if not path.exists():
        return []
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def finite(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def paired(rows, expected, metric, keys):
    differences = []
    missing = 0
    seen = set()
    for row in rows:
        key = tuple(row.get(k, '') for k in keys)
        value = finite(row.get(metric))
        reference = expected.get(key)
        if key in seen or reference is None or value is None:
            missing += 1
            continue
        seen.add(key)
        differences.append(value - reference)
    if not differences:
        return 'not validated — 동일 단위·기간·전략으로 연결 가능한 수치 없음'
    mae = sum(abs(x) for x in differences) / len(differences)
    return (f'비교 {len(differences)}/{len(expected)}건; MAE {mae:.3f}; '
            f'평균 차이 {sum(differences)/len(differences):.3f}; 제외 {missing}건. '
            '일치 판정 아님(허용 오차 미승인).')


def build(root=ROOT):
    fields = read(root / 'inputs/fields_20.csv')
    report = ['# MATLAB 검증', '', datetime.now(ZoneInfo('Asia/Seoul')).isoformat(), '',
              '관측 검증과 모델 간 비교를 구분한다. 누락·기간 불일치·API 실패는 not validated.', '']
    expected = {}
    errors = 0
    for field in fields:
        try:
            response = api(f"/validation/backtest?field_id={field['field_id']}&year=2012")
            for result in response['results']:
                for metric in ('season_water_deficit_mm', 'winter_bare_days'):
                    value = finite(result['metrics'].get(metric))
                    if value is not None:
                        expected[(field['field_id'], result['strategy_code'], metric)] = value
        except Exception:
            errors += 1
    report += [f'대상 {len(fields)}/20필지; API 실패 {errors}건.', '']
    v8 = read(root / 'outputs/woochan/v8_cards_20fields.csv')
    report += ['## V8 물 부족량', '']
    # V8 annual ETm is demand, not seasonal water deficit; rotations are not engine A-D.
    report += [f'V8 행 {len(v8)}건. not validated — V8 ETm_mm(연간 작물 물 요구량)은 '
               'engine season_water_deficit_mm(2012 계절 부족량)와 다르며 윤작도 A–D와 일대일 대응하지 않는다. '
               '공통 기후 기간·부족량 정의·승인된 전략 매핑이 필요하다.', '']
    bare = read(root / 'outputs/jimin/baresoil_days_20fields.csv')
    refs = {(fid, code, '2012'): value for (fid, code, metric), value in expected.items()
            if metric == 'winter_bare_days'}
    report += ['## NDVI 맨땅 일수', '']
    if bare and all('strategy_code' in r for r in bare):
        report += [paired(bare, refs, 'winter_bare_days', ('field_id', 'strategy_code', 'year'))]
    else:
        report += ['not validated — ' + ('NDVI 산출에 전략 매핑 없음; 관측 NDVI는 A–D 가상 전략 관측값이 아님.'
                                        if bare else 'outputs/jimin/baresoil_days_20fields.csv 없음.')]
    report += ['', 'HLS 관측 기간과 2012가 겹치지 않으면 2012 비교 불가. 전체 연간 bare_days를 겨울 181일 지표와 비교하지 않는다.', '',
               '## 2012 카운티 가뭄', '']
    drought = read(root / 'inputs/drought_2012_county.csv')
    county_ids = sorted({f['county_fips'] for f in fields})
    try:
        selected = ','.join("'" + x + "'" for x in county_ids if x.isdigit())
        query = f'''SELECT county_fips, to_char(date,'YYYY-MM') AS period, sum(precip_mm) AS precip_mm
            FROM county_weather_daily WHERE source_id='power' AND date BETWEEN '2012-01-01' AND '2012-12-31'
            AND county_fips IN ({selected or "''"}) GROUP BY county_fips, to_char(date,'YYYY-MM')'''
        engine = list(csv.DictReader(io.StringIO(sql_csv(query))))
        refs = {(r['county_fips'], r['period']): finite(r['precip_mm']) for r in engine}
        rows = [dict(r, precip_mm=r['value_2012']) for r in drought
                if r['variable'] == 'precip_mm' and r['county_fips'] in county_ids and len(r['period']) == 7]
        report += [paired(rows, refs, 'precip_mm', ('county_fips', 'period')) if rows else 'not validated — 카운티 산출 없음.']
    except Exception:
        report += ['not validated — DB 기후 비교 실패.']
    report += ['', '위 비교는 같은 POWER 자료의 월 강수 집계 교차 확인이며 독립 관측 검증이 아니다. '
               '가뭄 z-score와 필지 물 부족량(mm)은 동등하지 않다.', '',
               '## 정보 공백', '', '- MATLAB 실행·V8 출처 검증·NDVI 현장 임계값 보정은 별도 확인 필요.',
               '- coefficients.csv는 변경하지 않는다. 미확인 계수를 운영 보정값으로 승격하지 않는다.',
               '- coefficients_proposed.csv는 헤더만 생성: V8 Kc 1.08/0.86/0.75와 경제·회전 보너스의 문헌 표·단계·가중 근거 미확인으로 제안 행 보류.', '']
    return '\n'.join(report)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--out', type=Path, default=Path(__file__).resolve().parents[1] / 'docs/MATLAB-VALIDATION.md')
    args = parser.parse_args()
    content = build(args.root)
    temp = args.out.with_suffix('.tmp')
    temp.write_text(content)
    temp.replace(args.out)
    print(f'Wrote {args.out}')


if __name__ == '__main__':
    main()
