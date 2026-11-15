# VPS MATLAB 원격 접속 (김우찬 · 김윤성용)

노트북에서는 브라우저만 씁니다. MATLAB 계산은 VPS(Hetzner 서버)가 합니다.
접속은 **SSH 터널**로만 합니다. 인터넷에 MATLAB 주소를 공개하지 않습니다.

| 사람 | 리눅스 아이디 | 포트 | 브라우저 주소 |
| --- | --- | --- | --- |
| 김우찬 | `woochan` | 8888 | http://localhost:8888 |
| 김윤성 | `yoonsung` | 8889 | http://localhost:8889 |

서버 IP는 Hylē가 1:1 채널로 알려 줍니다. 아래 `<서버IP>`에 그 값을 넣습니다.

---

## 1. SSH 키 만들기 (처음 한 번)

키는 "열쇠 한 쌍"입니다. **개인키**는 내 노트북에만 두고, **공개키**(`.pub`)만 Hylē에게 보냅니다.

### Windows (PowerShell)

1. 시작 메뉴에서 **PowerShell**을 엽니다.
2. 아래 줄을 붙여 넣고 Enter. 질문이 나오면 Enter만 세 번 누릅니다.
   ```powershell
   ssh-keygen -t ed25519 -f $HOME\.ssh\amolla_vps -C "amolla-vps"
   ```
3. 공개키 내용을 화면에 띄웁니다.
   ```powershell
   Get-Content $HOME\.ssh\amolla_vps.pub
   ```

### Mac (터미널)

1. **터미널** 앱을 엽니다(Spotlight에서 "터미널").
2. 아래 줄을 붙여 넣고 Enter. 질문이 나오면 Enter만 세 번 누릅니다.
   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/amolla_vps -C "amolla-vps"
   ```
3. 공개키 내용을 화면에 띄웁니다.
   ```bash
   cat ~/.ssh/amolla_vps.pub
   ```

## 2. 공개키를 Hylē에게 보내기

- `ssh-ed25519 AAAA… amolla-vps`로 시작하는 **한 줄 전체**를 복사해 Mattermost 1:1 채널에 붙입니다.
- `.pub`가 **없는** 파일(`amolla_vps`)은 개인키입니다. 절대 보내지 마세요.
- Hylē가 등록했다고 하면 다음 단계로 갑니다.

## 3. 접속 (매번)

터미널(또는 PowerShell)에서 아래 한 줄을 실행합니다. 김윤성은 `8888`을 모두 `8889`로, `woochan`을 `yoonsung`으로 바꿉니다.

```bash
ssh -i ~/.ssh/amolla_vps -N -L 8888:127.0.0.1:8888 woochan@<서버IP>
```
Windows에서는 `~/.ssh/amolla_vps` 대신 `$HOME\.ssh\amolla_vps`를 씁니다.

- 처음에는 "Are you sure you want to continue connecting?"이 나옵니다. `yes`를 입력합니다.
- 그다음 **아무것도 안 나오고 멈춘 것처럼 보이면 정상**입니다. 이 창이 터널입니다. **닫지 마세요.**
- 이 계정은 MATLAB 터널 전용이라 서버 셸(명령줄)에는 들어갈 수 없습니다.

## 4. 브라우저에서 MATLAB 열기

1. 크롬에서 http://localhost:8888 (김윤성은 http://localhost:8889)을 엽니다.
2. 토큰을 물으면 Hylē가 1:1로 준 토큰을 붙입니다.
3. "Sign in to MathWorks"가 나오면 **본인 학생 계정**으로 로그인합니다. 처음 한 번은 1–2분 걸립니다.
4. MATLAB 창이 뜨면 명령 창에 `ver`를 입력해 버전과 툴박스 목록이 나오는지 봅니다.

## 5. 툴박스(Add-Ons) 설치

1. 위쪽 **HOME** 탭 → **Add-Ons** → **Get Add-Ons**.
2. 검색창에 이름을 넣고 **Install**: Mapping Toolbox, Image Processing Toolbox, Statistics and Machine Learning Toolbox, Optimization Toolbox, Signal Processing Toolbox.
3. 라이선스에 없는 툴박스는 설치 버튼이 비활성입니다. 그 이름을 1:1 채널에 알려 주세요. Savitzky–Golay(`sgolayfilt`)는 Signal Processing Toolbox에 있습니다. 없으면 기본 함수 `smoothdata(x,"sgolay",n)`을 씁니다.

## 6. 파일 위치

| 무엇 | MATLAB 안의 경로 | 권한 |
| --- | --- | --- |
| 입력 CSV (서버가 미리 뽑아 둠) | `/data/processed/v1/inputs/` | 읽기 전용 |
| 원본 데이터 전체 | `/data/raw/` | 읽기 전용 |
| **결과 저장** | `/data/processed/v1/matlab/` | 쓰기 가능 |
| 스크립트 | `/home/matlab/Documents/MATLAB/projects/2026NASA/matlab/` | 쓰기 가능 |

- 결과 파일 이름과 열은 [matlab/TASKS.md](../../matlab/TASKS.md)를 그대로 따릅니다.
- 결과 파일마다 옆에 `{파일}.manifest.json`을 남깁니다(TASKS.md 마지막 절).
- git은 몰라도 됩니다. 스크립트를 위 폴더에 저장하면 Hylē가 커밋합니다.

## 7. 자주 막히는 문제

| 증상 | 해결 |
| --- | --- |
| `Permission denied (publickey)` | 공개키가 아직 등록 안 됨, 또는 `-i` 경로가 틀림. 1:1 채널에 그대로 붙여 주세요. |
| `bind: Address already in use` | 노트북에서 8888(8889)을 다른 프로그램이 씀. 앞 숫자만 바꿉니다: `-L 18888:127.0.0.1:8888` → 브라우저 http://localhost:18888 |
| 브라우저가 "연결할 수 없음" | 3단계 터널 창이 닫혔음. 다시 실행합니다. |
| 터널 창이 몇 분 뒤 끊김 | 명령에 `-o ServerAliveInterval=30`을 추가합니다. |
| MathWorks 로그인 뒤 라이선스 오류 | 화면을 캡처해 1:1 채널에 올립니다. 학생 라이선스가 서버에서 막히면 Hylē가 다른 방법을 정합니다. |
| 저장이 안 됨 (`Permission denied`) | `/data/processed/v1/matlab/` 아래에만 저장할 수 있습니다. |
| MATLAB이 느림 | 두 사람이 각자 다른 MATLAB(8888, 8889)을 씁니다. 큰 계산은 `parfor` 대신 한 번에 한 작업. |
