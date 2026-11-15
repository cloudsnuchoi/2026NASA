# 김우찬 가이드 · ART FARM MATLAB (마감 20:30 KST)

MATLAB은 서비스 실행 중에 돌지 않습니다. 미리 계산·검증하는 용도이고, 결과 CSV/PNG를 엔진과 발표가 씁니다.

| 항목 | 값 |
| --- | --- |
| 포트 | **8888** → 브라우저 http://localhost:8888 |
| 접속 | 기존 방식 그대로 접속 (이 방 위쪽 "공개키를 등록했어요" 글의 `ssh ... -L 8888:...` 명령) |
| 로그인 | 본인 MathWorks 계정 (대신 로그인해 드리지 않아요) |
| 열 스크립트 | `~/Documents/MATLAB/projects/2026NASA-main/matlab/FieldShift_V8_batch.m` |
| 예상 소요 | 약 10분 (20필지 × 외부 API 호출) |

## 입력 (읽기 전용)
- `/data/processed/v1/matlab/inputs/fields_20.csv` (20필지 꼭짓점 4개)

## 출력 (여기에 저장)
- `/data/processed/v1/matlab/outputs/woochan/v8_cards_20fields.csv`
- `/data/processed/v1/matlab/outputs/woochan/coefficients_sources.csv` (계수 출처 표, 직접 작성)

## 실행 순서
1. 왼쪽 Current Folder에서 `~/Documents/MATLAB/projects/2026NASA-main/matlab/` 로 이동 → `FieldShift_V8_batch.m` 더블클릭해 열기
2. 위쪽 **EDITOR → Run ▶** 클릭 (F5 대신 Run 버튼)
3. 명령 창에 `Saved ...` 줄이 나오면 끝. 결과 확인: `v8_cards_20fields.csv`에 20필지 × 카드 행이 있는지, `v8_failures_20fields.csv`가 비었는지

계수 출처 표: 초안 `/data/processed/v1/matlab/woochan/coefficients_draft_from_V9.csv`를 열어 `source` 칸에 FAO-56 표 번호(Kc, 예: Table 12), USDA ERS/NASS 가격·비용의 연도를 채워 `outputs/woochan/coefficients_sources.csv`로 저장.

## 막힐 때
- 프롬프트가 `K>>`로 바뀌면 `dbquit` 입력 후 다시 Run
- "Output exists already" / "Refusing to overwrite": 이미 결과가 있어요. 1:1 방에 알려 주세요(덮어쓰기 대신 새 이름으로 처리)
- 파일 이름을 바꿔 저장할 때 **안에 있는 함수 이름과 같은 이름은 피하기** (서버 MATLAB이 안 돌던 원인)
- 빨간 오류 글자를 그대로 복사해 1:1 방에 붙이기 → 봇이 바로 답해요 (캡처도 읽어요)

## 완료 보고
결과 파일이 저장되면 1:1 방에 **"완료"** + 핵심 숫자 한 줄을 적어 주세요.

관련: [REMOTE.md (접속)](https://github.com/cloudsnuchoi/2026NASA/blob/main/infra/matlab/REMOTE.md) · [PIPELINE.md (입출력 전체)](https://github.com/cloudsnuchoi/2026NASA/blob/main/matlab/PIPELINE.md) · [TASKS.md](https://github.com/cloudsnuchoi/2026NASA/blob/main/matlab/TASKS.md)
