# infra/ci · CI 워크플로 (설치 대기)

`ci.yml`은 2026-11-15 `.github/workflows/ci.yml`로 옮겼다(러너 `amolla-vps` 등록 완료). 아래는 기록용이다.

```bash
# 노트북 또는 VPS, 2026NASA 폴더에서 (gh 로그인 계정에 workflow 권한 필요: gh auth refresh -s workflow)
git checkout main && git pull --ff-only
mkdir -p .github/workflows && git mv infra/ci/ci.yml .github/workflows/ci.yml
git commit -m "ci: enable self-hosted CI workflow" && git push origin main   # admin 우회로 main 푸시 가능
```

내용 요약:
- 모든 job은 `runs-on: [self-hosted, linux]`에서 돈다.
- 포크 PR은 `head.repo.full_name == github.repository` 조건으로 실행하지 않는다.
- `python` job: `.py`가 있으면 ruff를 돌리고, `test_*.py`가 있으면 pytest를 돌린다.
- `frontend` job: `frontend/`나 `sim/`에 `package.json`이 있으면 lint, test, build를 돌린다.
- `ci-ok`: 위 둘을 묶은 필수 체크용 job이다.
- 폴더가 비어 있으면 job을 건너뛰고 성공으로 끝난다.
