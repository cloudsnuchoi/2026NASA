# matlab/contrib — 팀원 실행본과 에이전트 수정본

원칙: **팀원은 Run만 누른다. 스크립트 수정은 에이전트(MATLAB-fix 레인)가 한다.**

## 규칙

1. 팀원이 MATLAB 브라우저 세션에서 실행하다 실패하면, 오류 메시지와 출력 폴더
   (`/data/processed/v1/matlab/outputs/<name>/`)의 `*_failures*.csv`를 이슈 댓글로 남긴다.
   직접 고치지 않아도 된다.
2. 에이전트는 `matlab/*.m` 원본을 고치고, 팀원별 변경 내역을 `matlab/contrib/<name>/CHANGELOG.md`에 남긴다.
3. **사용자가 수정한 파일은 절대 덮어쓰지 않는다.** 팀원이 자기 사본(`matlab/contrib/<name>/*.m`
   또는 MATLAB Drive 사본)을 고쳐 두었고 그 내용이 저장소 원본과 다르면, 에이전트 수정본은
   `<원래이름>_fixed.m`으로 옆에 저장한다(예: `FieldShift_V8_batch_fixed.m`). 어느 쪽을 쓸지는 팀원이 고른다.
4. 출력 덮어쓰기 정책(4개 스크립트 공통): 기존 결과는 지우지 않고
   `outputs/<name>/old/<yyyymmdd_HHMMSS>/`로 옮긴 뒤 새 결과를 쓴다. 그래서 다시 Run 해도 안전하다.
5. 외부 API는 서버에서 미리 받아 둔다(`data_pipeline/v8_prefetch.py` →
   `/data/processed/v1/matlab/inputs/v8_api_cache/<field_id>/*.json`). MATLAB은 캐시를 먼저 읽고,
   캐시 파일이 없을 때만 `webread`(60 s 타임아웃, 재시도 2회)를 쓴다.
6. 결측(null)은 결측으로 둔다(정보 공백). 0이나 임의 값으로 채우지 않는다.

## 수정 전 확인 (에이전트)

- `python -m pytest -q data_pipeline/tests/test_matlab_static.py` — 블록/`end` 균형, 대화형 호출 금지,
  스크립트명≠로컬 함수명, 로컬 함수는 스크립트 코드 뒤, ID 텍스트 읽기, `/data` 컨테이너 경로.
- `python data_pipeline/v8_precheck.py --all` — 캐시가 V8 검증기를 통과하는지(Python 재구현, 네트워크 없음).
