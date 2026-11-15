# 김윤성 가이드 · ART FARM MATLAB (마감 20:30 KST)

MATLAB은 서비스 실행 중에 돌지 않습니다. 미리 계산·검증하는 용도이고, 결과 CSV/PNG를 엔진과 발표가 씁니다.

| 항목 | 값 |
| --- | --- |
| 포트 | **8889** → 브라우저 http://localhost:8889 |
| 접속 | 기존 방식 그대로 접속 (이 방 위쪽 "공개키를 등록했어요" 글의 `ssh ... -L 8889:...` 명령) |
| 로그인 | 본인 MathWorks 계정 (대신 로그인해 드리지 않아요) |
| 열 스크립트 | `~/Documents/MATLAB/projects/2026NASA-main/matlab/drought_compare_2012.m` |
| 예상 소요 | 1분 이내 |

## 입력 (읽기 전용)
- `/data/processed/v1/matlab/inputs/engine_2012_deficit.csv` (엔진 2012 물 부족, 필지×전략)
- `/data/processed/v1/matlab/inputs/drought_2012_county.csv` (윤성님 결과)
- `/data/processed/v1/matlab/inputs/fields_20.csv`

## 출력 (여기에 저장)
- `/data/processed/v1/matlab/outputs/yoonsung/drought_compare_2012.png`
- `/data/processed/v1/matlab/outputs/yoonsung/drought_compare_2012_summary.csv` (카운티별 값 + Pearson r, n)

## 실행 순서
1. 왼쪽 Current Folder에서 `~/Documents/MATLAB/projects/2026NASA-main/matlab/` 로 이동 → `drought_compare_2012.m` 더블클릭해 열기
2. 위쪽 **EDITOR → Run ▶** 클릭 (F5 대신 Run 버튼)
3. 명령 창에 `Saved ...` 줄이 나오면 끝. 결과 확인: 그림에 4개 카운티 막대와 산점도, 제목에 r과 n이 나오는지

참고: 윤성님이 만든 CSV 3개 중 `drought_2012_county.csv`는 이 대조(백테스트 검증)에, `climate_annual.csv`·`calibration_params.csv`는 엔진 보정 입력으로 쓰여요. 두 지표(강수 이상 vs 모의 물 부족)는 같은 단위가 아니라 '일관성 확인'이에요.

## 막힐 때
- 프롬프트가 `K>>`로 바뀌면 `dbquit` 입력 후 다시 Run
- "Output exists already" / "Refusing to overwrite": 이미 결과가 있어요. 1:1 방에 알려 주세요(덮어쓰기 대신 새 이름으로 처리)
- 파일 이름을 바꿔 저장할 때 **안에 있는 함수 이름과 같은 이름은 피하기** (서버 MATLAB이 안 돌던 원인)
- 빨간 오류 글자를 그대로 복사해 1:1 방에 붙이기 → 봇이 바로 답해요 (캡처도 읽어요)

## 완료 보고
결과 파일이 저장되면 1:1 방에 **"완료"** + 핵심 숫자 한 줄을 적어 주세요.

관련: [REMOTE.md (접속)](https://github.com/cloudsnuchoi/2026NASA/blob/main/infra/matlab/REMOTE.md) · [PIPELINE.md (입출력 전체)](https://github.com/cloudsnuchoi/2026NASA/blob/main/matlab/PIPELINE.md) · [TASKS.md](https://github.com/cloudsnuchoi/2026NASA/blob/main/matlab/TASKS.md)
