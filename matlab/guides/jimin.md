# 하지민 가이드 · ART FARM MATLAB (마감 20:30 KST)

MATLAB은 서비스 실행 중에 돌지 않습니다. 미리 계산·검증하는 용도이고, 결과 CSV/PNG를 엔진과 발표가 씁니다.

| 항목 | 값 |
| --- | --- |
| 포트 | **8890** → 브라우저 http://localhost:8890 |
| 접속 | 새로 접속: SSH 키를 만들고 공개키(.pub 한 줄)를 이 방에 올리면 자동 등록되고, 서버 주소가 든 `ssh ... -L 8890:...` 명령이 이 방에 와요 |
| 로그인 | 본인 MathWorks 계정 (대신 로그인해 드리지 않아요) |
| 열 스크립트 | `~/Documents/MATLAB/work/ndvi_baresoil.m` |
| 예상 소요 | 1분 이내 |

## 원칙
스크립트는 서버 에이전트가 고칩니다. **work/의 파일을 열고 Run ▶만** 누르세요. 에러가 나면 고치지 말고 빨간 에러 문구나 캡처를 1:1 방에 올리면 봇이 고쳐서 work/에 다시 넣어 드립니다(직접 고친 파일은 덮어쓰지 않고 `_fixed` 이름으로 넣어요).

## 입력 (읽기 전용)
- `/data/processed/v1/matlab/inputs/ndvi_hls_20fields.csv` (20필지 HLS NDVI 2023–2025)
- `/data/processed/v1/matlab/inputs/fields_20.csv`

## 출력 (여기에 저장)
- `/data/processed/v1/matlab/outputs/jimin/baresoil_days_20fields.csv` (필지·연도별 맨땅 일수)

## 실행 순서
1. 왼쪽 Current Folder에서 `~/Documents/MATLAB/work/` 로 이동 → `ndvi_baresoil.m` 더블클릭해 열기
2. 위쪽 **EDITOR → Run ▶** 클릭 (F5 대신 Run 버튼)
3. 명령 창에 `Saved ...` 줄이 나오면 끝. 결과 확인: 20필지 × 연도 행이 있고, 맨땅 일수가 0–365 사이인지

Savitzky–Golay 평활 후 NDVI < 기준값(스크립트 주석에 근거)인 날을 맨땅으로 셉니다. 기준값을 바꾸면 주석의 근거도 같이 고쳐 주세요.

## 막힐 때
- 프롬프트가 `K>>`로 바뀌면 `dbquit` 입력 후 다시 Run
- "Output exists already" / "Refusing to overwrite": 이미 결과가 있어요. 1:1 방에 알려 주세요(덮어쓰기 대신 새 이름으로 처리)
- 파일 이름을 바꿔 저장할 때 **안에 있는 함수 이름과 같은 이름은 피하기** (서버 MATLAB이 안 돌던 원인)
- 빨간 오류 글자를 그대로 복사해 1:1 방에 붙이기 → 봇이 바로 답해요 (캡처도 읽어요)

## 완료 보고
결과 파일이 저장되면 1:1 방에 **"완료"** + 핵심 숫자 한 줄을 적어 주세요.

관련: [REMOTE.md (접속)](https://github.com/cloudsnuchoi/2026NASA/blob/main/infra/matlab/REMOTE.md) · [PIPELINE.md (입출력 전체)](https://github.com/cloudsnuchoi/2026NASA/blob/main/matlab/PIPELINE.md) · [TASKS.md](https://github.com/cloudsnuchoi/2026NASA/blob/main/matlab/TASKS.md)
