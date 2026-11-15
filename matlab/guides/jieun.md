# 고지은 가이드 · ART FARM MATLAB (마감 20:30 KST)

MATLAB은 서비스 실행 중에 돌지 않습니다. 미리 계산·검증하는 용도이고, 결과 CSV/PNG를 엔진과 발표가 씁니다.

| 항목 | 값 |
| --- | --- |
| 포트 | **8891** → 브라우저 http://localhost:8891 |
| 접속 | 새로 접속: SSH 키를 만들고 공개키(.pub 한 줄)를 이 방에 올리면 자동 등록되고, 서버 주소가 든 `ssh ... -L 8891:...` 명령이 이 방에 와요 |
| 로그인 | 본인 MathWorks 계정 (대신 로그인해 드리지 않아요) |
| 열 스크립트 | `~/Documents/MATLAB/projects/2026NASA-main/matlab/slide_figures.m` |
| 예상 소요 | 1분 이내 |

## 입력 (읽기 전용)
- `/data/processed/v1/matlab/inputs/engine_p10p90_20fields.csv` (전략별 P10–P90)
- `/data/processed/v1/matlab/inputs/engine_2012_deficit.csv` (2012 백테스트)

## 출력 (여기에 저장)
- `/data/processed/v1/matlab/outputs/jieun/fig_p10p90.png`
- `/data/processed/v1/matlab/outputs/jieun/fig_backtest2012.png`

## 실행 순서
1. 왼쪽 Current Folder에서 `~/Documents/MATLAB/projects/2026NASA-main/matlab/` 로 이동 → `slide_figures.m` 더블클릭해 열기
2. 위쪽 **EDITOR → Run ▶** 클릭 (F5 대신 Run 버튼)
3. 명령 창에 `Saved ...` 줄이 나오면 끝. 결과 확인: PNG 2장이 열리고, 전략 A–D가 모두 보이는지

그림은 슬라이드에 바로 들어가요. 남는 시간에는 공개 데모 URL(~uiux-design에 공지)로 UI를 써 보고 버그를 ~uiux-design에 남겨 주세요.

## 막힐 때
- 프롬프트가 `K>>`로 바뀌면 `dbquit` 입력 후 다시 Run
- "Output exists already" / "Refusing to overwrite": 이미 결과가 있어요. 1:1 방에 알려 주세요(덮어쓰기 대신 새 이름으로 처리)
- 파일 이름을 바꿔 저장할 때 **안에 있는 함수 이름과 같은 이름은 피하기** (서버 MATLAB이 안 돌던 원인)
- 빨간 오류 글자를 그대로 복사해 1:1 방에 붙이기 → 봇이 바로 답해요 (캡처도 읽어요)

## 완료 보고
결과 파일이 저장되면 1:1 방에 **"완료"** + 핵심 숫자 한 줄을 적어 주세요.

관련: [REMOTE.md (접속)](https://github.com/cloudsnuchoi/2026NASA/blob/main/infra/matlab/REMOTE.md) · [PIPELINE.md (입출력 전체)](https://github.com/cloudsnuchoi/2026NASA/blob/main/matlab/PIPELINE.md) · [TASKS.md](https://github.com/cloudsnuchoi/2026NASA/blob/main/matlab/TASKS.md)
