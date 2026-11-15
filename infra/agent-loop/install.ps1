# agent-loop 한 줄 설치·실행 (Windows PowerShell). 다시 실행하면 업데이트 후 바로 켜져요.
#   irm https://raw.githubusercontent.com/cloudsnuchoi/2026NASA/main/infra/agent-loop/install.ps1 | iex
# 설정 다시 하기: $env:AMOLLA_SETUP=1 을 먼저 입력하고 위 한 줄 실행 (또는 %USERPROFILE%\.amolla-agent.json 삭제)
$ErrorActionPreference = "Continue"   # native 명령 오류는 $LASTEXITCODE로 확인
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"
$Repo = "cloudsnuchoi/2026NASA"
$Dir = if ($env:REPO_DIR) { $env:REPO_DIR } else { Join-Path $HOME "2026NASA" }
$Venv = Join-Path $HOME ".amolla-agent-venv"
$Cfg = if ($env:AMOLLA_AGENT_CONFIG) { $env:AMOLLA_AGENT_CONFIG } else { Join-Path $HOME ".amolla-agent.json" }
function Say($m) { Write-Host "`n▶ $m" -ForegroundColor Cyan }
function Die($m) { Write-Host "`n❌ $m" -ForegroundColor Red; throw $m }
function Has($c) { [bool](Get-Command $c -ErrorAction SilentlyContinue) }

Say "도구 확인"
$Py = $null
if (Has "py") { $Py = @("py", "-3") }
elseif ((Has "python") -and ((Get-Command python).Source -notlike "*WindowsApps*")) { $Py = @("python") }
if (-not $Py) { Die "Python 3가 없어요. 설치: winget install -e --id Python.Python.3.12  (설치 후 PowerShell 새로 열기)" }
if (-not (Has "git")) { Die "git이 없어요. 설치: winget install -e --id Git.Git" }
if (-not (Has "gh")) { Die "gh가 없어요. 설치: winget install -e --id GitHub.cli  그다음 gh auth login" }
gh auth status *> $null
if ($LASTEXITCODE -ne 0) { Die "GitHub 로그인이 안 돼 있어요. 실행: gh auth login -h github.com -p https -w" }
gh auth setup-git *> $null
$Ag = if (Has "codex") { "codex" } elseif (Has "agy") { "agy" } else { "" }
if (-not $Ag) { Write-Host "⚠ codex 도 agy 도 안 보여요. 설치·로그인 먼저 해 주세요 (설정은 계속 진행)." -ForegroundColor Yellow }
Write-Host "python · git · gh OK $(if ($Ag) { "· 에이전트 후보: $Ag" })"

Say "저장소 ($Dir)"
if (Test-Path (Join-Path $Dir ".git")) {
  if (-not (git -C $Dir status --porcelain)) {
    if ((git -C $Dir rev-parse --abbrev-ref HEAD) -eq "main") { git -C $Dir pull --ff-only -q }
  } else { Write-Host "⚠ 커밋 안 된 변경이 있어요. 작업은 깨끗한 상태에서만 시작돼요 (git status 확인)" -ForegroundColor Yellow }
} else {
  gh repo clone $Repo $Dir -- -q
  if ($LASTEXITCODE -ne 0) { Die "clone 실패. GitHub 초대를 수락했는지 확인하세요." }
}
git -C $Dir fetch -q origin main

Say "파이썬 환경 ($Venv)"
$VPy = Join-Path $Venv "Scripts\python.exe"
if (-not (Test-Path $VPy)) {
  if ($Py.Count -gt 1) { & $Py[0] $Py[1] -m venv $Venv } else { & $Py[0] -m venv $Venv }
  if (-not (Test-Path $VPy)) { Die "venv 만들기 실패" }
}
& $VPy -m pip install -q --disable-pip-version-check "requests>=2.31,<3"

# 실행 파일은 저장소 밖에 복사해서 씀 (브랜치를 바꿔도 loop가 안 바뀌게)
$Loop = Join-Path $Venv "agent_loop.py"
& $VPy -c "import subprocess,sys;open(sys.argv[1],'wb').write(subprocess.check_output(['git','-C',sys.argv[2],'show','origin/main:infra/agent-loop/agent_loop.py']))" $Loop $Dir
if ($LASTEXITCODE -ne 0) { Die "agent_loop.py 복사 실패 (git fetch 확인)" }

if (-not (Test-Path $Cfg) -or $env:AMOLLA_SETUP) {
  Say "설정 (채팅 주소·토큰·에이전트)"
  Write-Host "토큰 만드는 법: README 1단계 (Mattermost → 프로필 → 보안 → 개인 액세스 토큰)"
  $env:REPO_DIR = $Dir
  $env:AGENT = if ($env:AGENT) { $env:AGENT } elseif ($Ag) { $Ag } else { "codex" }
  & $VPy $Loop --setup --check
  Remove-Item Env:AGENT, Env:AMOLLA_SETUP -ErrorAction SilentlyContinue
}

Say "연결 확인"
& $VPy $Loop --check
if ($LASTEXITCODE -ne 0) { Die "연결 실패. 주소가 바뀌었으면: & '$VPy' '$Loop' --set-url <새주소>" }

Say "실행 — 이 PowerShell 창을 닫지 마세요 (끄기: Ctrl+C, 다시 켜기: 같은 한 줄 다시 실행)"
Write-Host "팁: 설정 > 시스템 > 전원에서 '절전 모드 안 함'으로 두면 노트북이 잠들지 않아요."
& $VPy $Loop
