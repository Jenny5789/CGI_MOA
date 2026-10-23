# 개발 환경 구축

새 Windows PC에서 MOA를 처음 설치하는 순서입니다. 각 단계마다 설치 대상, 필요한 이유, 받는 곳, 설치 확인 방법을 함께 적었습니다. 위에서부터 순서대로 진행하면 됩니다.

## 1. 전체 흐름

| 순서 | 내용 | 설치 대상 |
|---|---|---|
| 1 | PC 사양 확인 | NVIDIA GPU, 디스크 여유 공간 |
| 2 | 기본 프로그램 설치 | NVIDIA 드라이버, Git, Python 3.10, Node.js 24, MySQL 8.0 |
| 3 | 저장소 받기 | MOA 소스 코드 |
| 4 | Python 가상환경과 패키지 설치 | PyTorch, SAM2, AnyDoor 실행 패키지, 백엔드 패키지, xformers |
| 5 | AI 모델 준비 | AnyDoor 코드, 모델 가중치 파일 3개, 설정 파일 경로 수정 |
| 6 | 데이터베이스 구축 | MySQL 데이터베이스·계정, 접속 설정 파일 |
| 7 | 설치 확인 | 점검 스크립트, 서버 실행 |

- 다운로드: 모델 파일 약 21.7GB와 PyTorch 등 Python 패키지
- 명령 입력 창: Windows PowerShell. 아래 명령은 모두 PowerShell에 한 줄씩 붙여 넣어 실행

### PowerShell 여는 방법

- 시작 메뉴에서 `PowerShell` 검색 → Windows PowerShell 실행
- 특정 폴더에서 열기: 탐색기에서 해당 폴더를 열고 빈 곳을 마우스 오른쪽 클릭 → `터미널에서 열기`
- 프로그램을 새로 설치한 뒤에는 PowerShell 창을 닫고 새로 열어야 설치한 명령이 인식됨

## 2. PC 사양 확인

| 항목 | 필요 조건 | 개발 PC 검증 사양 |
|---|---|---|
| 운영체제 | Windows 64비트 | Windows 11 Pro for Workstations |
| GPU | NVIDIA GPU | GeForce RTX 3080 10GB, 합성 시 PyTorch 최대 할당 8.25GB |
| 메모리 | - | 32GB |
| 디스크 | 모델 파일 약 21.7GB와 Python 패키지를 저장할 여유 공간 | - |

- GPU 확인: `Ctrl+Shift+Esc`로 작업 관리자 실행 → 성능 탭 → GPU 항목의 이름과 전용 GPU 메모리
- AMD·Intel GPU만 있는 PC는 합성 모델 실행 불가

## 3. 기본 프로그램 설치

이미 설치된 프로그램은 설치 확인 명령으로 버전만 확인하고 넘어갑니다.

### 3-1. NVIDIA 그래픽 드라이버

- 설치 대상: NVIDIA GPU를 Windows에서 사용하기 위한 드라이버
- 필요한 이유: PyTorch가 GPU로 AI 모델을 실행하려면 CUDA 12.1 이상을 지원하는 드라이버 필요. CUDA 자체는 PyTorch에 포함되어 별도 설치 불필요
- 받는 곳: https://www.nvidia.com/ko-kr/drivers/ 에서 그래픽 카드 모델 선택 후 최신 드라이버 다운로드
- 설치 방법: 받은 파일 실행 → 기본 선택대로 진행 → 설치 후 PC 재시작
- 설치 확인

```powershell
nvidia-smi
```

- 정상: 표 오른쪽 위 `CUDA Version`이 12.1 이상

### 3-2. Git

- 설치 대상: 소스 코드 버전 관리 프로그램
- 필요한 이유: GitHub에서 MOA 저장소와 AnyDoor 코드를 받고, SAM2 패키지를 설치할 때 사용
- 받는 곳: https://git-scm.com/downloads/win → `Click here to download` 클릭
- 설치 방법: 받은 파일 실행 → 모든 화면에서 기본값 그대로 `Next` → `Install`
- 설치 확인: 새 PowerShell 창에서 실행, `git version 2.xx` 형식이면 정상

```powershell
git --version
```

### 3-3. Python 3.10

- 설치 대상: AI 모델과 백엔드 서버를 실행하는 Python 언어
- 필요한 이유: MOA가 사용하는 PyTorch 2.5.1과 AnyDoor 패키지 조합이 Python 3.10 기준으로 검증됨. 3.11 이상이나 3.9 이하는 사용하지 않음
- 받는 곳: https://www.python.org/downloads/windows/ → `Python 3.10.x` 항목 중 `Windows installer (64-bit)`가 있는 버전 선택. 개발 PC는 3.10.0
- 설치 방법
  1. 받은 파일 실행
  2. 첫 화면 아래 `Install launcher for all users`와 `Add Python 3.10 to PATH` 모두 체크
  3. `Install Now` 클릭
  4. 마지막 화면에 `Disable path length limit`가 보이면 클릭 후 `Close`
- 설치 확인: 새 PowerShell 창에서 실행, `Python 3.10.x`가 나오면 정상

```powershell
py -3.10 --version
```

- `py`는 Python 런처. PC에 여러 Python 버전이 있어도 `py -3.10`으로 3.10을 지정해 실행

### 3-4. Node.js 24

- 설치 대상: JavaScript 실행 환경과 패키지 관리 도구 npm
- 필요한 이유: React로 만든 웹 화면을 개발 서버로 실행할 때 사용
- 받는 곳: https://nodejs.org/ko/download → 버전 `v24`의 Windows 설치 프로그램 `.msi` 다운로드
- 설치 방법: 받은 파일 실행 → 기본값 그대로 `Next` → `Install`. 중간의 `Tools for Native Modules` 자동 설치 체크는 하지 않아도 됨
- 설치 확인: 새 PowerShell 창에서 실행, `v24.x.x`와 npm 버전이 나오면 정상

```powershell
node -v
npm -v
```

### 3-5. MySQL 8.0

- 설치 대상: 회원 정보와 로그인 기록을 저장하는 데이터베이스 서버
- 필요한 이유: 회원가입·로그인·사진첩 기능이 MySQL에 데이터 저장
- 설치 방법과 확인: [database.md](database.md) 2-1. 설치 중 정한 `root` 비밀번호는 6장에서 사용하므로 따로 기록

### 3-6. VS Code · 선택

- 설치 대상: 코드 편집기
- 받는 곳: https://code.visualstudio.com/
- 필요한 이유: 필수 아님. 저장소 폴더를 열면 `.vscode/settings.json`에 따라 가상환경 `CGI`가 자동 선택됨

## 4. 저장소 받기와 Python 패키지 설치

### 4-1. 저장소 받기

- 설치 대상: MOA 전체 소스 코드
- 설치 위치 예시: `C:\MOA`. 경로에 한글·공백이 없는 폴더를 권장
- 실행 순서

```powershell
cd C:\
git clone https://github.com/Jenny5789/CGI_MOA.git
cd CGI_MOA
```

- 결과: `C:\CGI_MOA` 폴더 생성
- 이후 모든 명령은 이 `CGI_MOA` 폴더에서 실행. PowerShell을 새로 열었다면 먼저 `cd C:\CGI_MOA`

### 4-2. 가상환경 `CGI` 생성

- 설치 대상: MOA 전용 Python 실행 공간
- 필요한 이유: PC에 설치된 다른 Python 패키지와 버전 충돌 방지. MOA의 모든 패키지는 이 안에만 설치

```powershell
py -3.10 -m venv CGI
```

- 결과: `CGI_MOA\CGI` 폴더 생성. `.gitignore` 등록 폴더라 GitHub에 올라가지 않음
- 이름 `CGI` 고정: `scripts/check_env.py`, `.vscode/settings.json`, `.gitignore`가 이 이름 기준
- 아래 명령의 `CGI\Scripts\python.exe`는 이 가상환경의 Python을 직접 지정해 실행한다는 뜻. 가상환경 활성화 과정 불필요

### 4-3. pip 업그레이드

- 설치 대상: Python 패키지 설치 도구 pip 최신 버전
- 필요한 이유: Python 3.10에 포함된 pip 23.0.1은 PyTorch 다운로드 서버의 일부 파일을 거부해 4-4 단계 실패

```powershell
CGI\Scripts\python.exe -m pip install --upgrade pip
```

### 4-4. PyTorch · 딥러닝 프레임워크

- 설치 대상: torch 2.5.1, torchvision 0.20.1의 CUDA 12.1 빌드
- 필요한 이유: SAM2와 AnyDoor 모델을 GPU에서 실행하는 기반 라이브러리

```powershell
CGI\Scripts\python.exe -m pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121
```

- `--index-url`: 일반 pip 저장소에는 GPU 미지원 빌드만 있어 PyTorch 공식 CUDA 12.1 저장소를 지정
- 설치 확인: `True`가 나오면 GPU 사용 가능

```powershell
CGI\Scripts\python.exe -c "import torch; print(torch.cuda.is_available())"
```

### 4-5. SAM2 · 상의 영역 분할 모델 코드

- 설치 대상: Meta의 Segment Anything 2 라이브러리
- 필요한 이유: 사용자가 사진에 찍은 점을 기준으로 상의 영역을 자동 분할
- 받는 곳: Meta 공식 GitHub 저장소 https://github.com/facebookresearch/sam2 . pip이 Git으로 직접 받아 설치

```powershell
CGI\Scripts\python.exe -m pip install "git+https://github.com/facebookresearch/sam2.git@2b90b9f5ceec907a1c18123530e92e794ad901a4"
```

- 마지막 `@2b90b9f...`: 개발 PC와 같은 코드 버전으로 고정. 최신 버전은 요구 PyTorch 버전이 달라져 4-4에서 설치한 PyTorch가 교체될 위험
- 모델 가중치 파일은 5-2 단계에서 별도 다운로드

### 4-6. 나머지 Python 패키지 일괄 설치

- 설치 대상: 저장소의 `requirements.txt`에 적힌 패키지 전체

| 구분 | 주요 패키지 | 역할 |
|---|---|---|
| AnyDoor 실행 | pytorch-lightning, transformers, open_clip_torch, timm, omegaconf, einops, opencv | 합성 모델 구성·이미지 처리 |
| 영역 분할 보조 | segment-anything, kornia | 마스크 후처리 |
| 백엔드 서버 | fastapi, uvicorn, python-multipart | 웹 API 서버, 이미지 업로드 처리 |
| 데이터베이스 | sqlalchemy, pymysql, python-dotenv | MySQL 접속, 접속 설정 파일 읽기 |

```powershell
CGI\Scripts\python.exe -m pip install -r requirements.txt
```

### 4-7. xformers · 합성 속도·GPU 메모리 최적화

- 설치 대상: 어텐션 연산을 빠르고 적은 메모리로 처리하는 라이브러리
- 필요한 이유: AnyDoor 합성 속도 향상과 GPU 메모리 사용량 감소

```powershell
CGI\Scripts\python.exe -m pip install xformers==0.0.28.post3 --index-url https://download.pytorch.org/whl/cu124 --no-deps
```

- `--no-deps`: xformers가 다른 PyTorch 버전을 함께 설치하지 않도록 차단, 4-4의 PyTorch 2.5.1 유지
- cu124 저장소의 0.0.28.post3과 PyTorch 2.5.1 CUDA 12.1 빌드 조합으로 개발 PC 동작 확인

## 5. AI 모델 준비

### 5-1. AnyDoor 코드 받기

- 설치 대상: 상의 착용 합성 모델 AnyDoor의 공식 소스 코드
- 받는 곳: AnyDoor 공식 GitHub 저장소 https://github.com/ali-vilab/AnyDoor

```powershell
git clone https://github.com/ali-vilab/AnyDoor checkpoints\AnyDoor
git -C checkpoints\AnyDoor checkout 44ca2b2
```

- 결과: `CGI_MOA\checkpoints\AnyDoor` 폴더 생성. `checkpoints/`는 `.gitignore` 등록 폴더
- `checkout 44ca2b2`: 개발 PC와 같은 코드 버전으로 고정. MOA 합성 모듈이 AnyDoor `run_inference.py`의 특정 코드 줄을 바꿔 실행하므로 다른 버전은 실행 오류 가능
- `detached HEAD` 안내 문구는 정상

### 5-2. 모델 가중치 파일 받기

- 설치 대상: 학습이 끝난 AI 모델 파일 3개. 코드만으로는 모델이 동작하지 않고 이 파일이 있어야 추론 가능

| 파일 | 모델 | 역할 | 크기 | 저장 위치 |
|---|---|---|---|---|
| `sam2.1_hiera_base_plus.pt` | SAM 2.1 Base+ | 상의 영역 분할 | 약 309MB | `checkpoints\sam2\` |
| `epoch=1-step=8687.ckpt` | AnyDoor | 착용 이미지 합성 | 약 16.8GB | `checkpoints\AnyDoor\checkpoints\` |
| `dinov2_vitg14_pretrain.pth` | DINOv2 ViT-g/14 | AnyDoor 내부의 상의 이미지 특징 추출 | 약 4.5GB | `checkpoints\AnyDoor\checkpoints\` |

- 방법 1, 명령으로 받기: 아래 4줄을 차례로 실행. 파일이 커서 진행률 표시가 오래 지속됨

```powershell
New-Item -ItemType Directory -Force checkpoints\sam2, checkpoints\AnyDoor\checkpoints
curl.exe -L -o checkpoints\sam2\sam2.1_hiera_base_plus.pt https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_base_plus.pt
curl.exe -L -o "checkpoints\AnyDoor\checkpoints\epoch=1-step=8687.ckpt" "https://huggingface.co/spaces/xichenhku/AnyDoor/resolve/main/epoch%3D1-step%3D8687.ckpt"
curl.exe -L -o checkpoints\AnyDoor\checkpoints\dinov2_vitg14_pretrain.pth https://dl.fbaipublicfiles.com/dinov2/dinov2_vitg14/dinov2_vitg14_pretrain.pth
```

- 방법 2, 브라우저로 받기: 아래 주소를 브라우저 주소창에 붙여 넣으면 다운로드 시작. 받은 파일을 표의 저장 위치로 이동. 파일 이름이 바뀌었다면 표의 이름으로 변경
  - SAM2: https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_base_plus.pt
  - AnyDoor: https://huggingface.co/spaces/xichenhku/AnyDoor/resolve/main/epoch%3D1-step%3D8687.ckpt
  - DINOv2: https://dl.fbaipublicfiles.com/dinov2/dinov2_vitg14/dinov2_vitg14_pretrain.pth
- 출처: SAM2·DINOv2는 Meta 공식 배포 주소, AnyDoor는 AnyDoor 공식 저장소가 안내하는 HuggingFace 주소. 다른 받는 곳: [ModelScope damo/AnyDoor](https://modelscope.cn/models/damo/AnyDoor/files)
- 크기 확인: 파일 오른쪽 클릭 → 속성의 바이트 수가 아래와 같으면 정상. 탐색기 목록에는 단위 차이로 약 309MB·15.7GB·4.2GB로 표시

| 파일 | 바이트 수 |
|---|---|
| `sam2.1_hiera_base_plus.pt` | 323,606,802 |
| `epoch=1-step=8687.ckpt` | 16,836,620,171 |
| `dinov2_vitg14_pretrain.pth` | 4,546,108,579 |

### 5-3. AnyDoor 설정 파일의 경로 수정

- 수정 이유: AnyDoor 공식 설정 파일에는 모델 파일 위치가 `path/...` 자리표시 값으로 되어 있어 5-2에서 받은 위치로 변경 필요

| 파일 | 줄 | 변경 전 | 변경 후 |
|---|---|---|---|
| `checkpoints\AnyDoor\configs\inference.yaml` | 1행 | `pretrained_model: path/epoch=1-step=8687.ckpt` | `pretrained_model: ./checkpoints/epoch=1-step=8687.ckpt` |
| `checkpoints\AnyDoor\configs\anydoor.yaml` | 83행 | `weight: path/dinov2_vitg14_pretrain.pth` | `weight: checkpoints/dinov2_vitg14_pretrain.pth` |

- 방법 1, 명령으로 수정: 아래 2줄 실행

```powershell
(Get-Content checkpoints\AnyDoor\configs\inference.yaml) -replace 'path/epoch=1-step=8687.ckpt', './checkpoints/epoch=1-step=8687.ckpt' | Set-Content checkpoints\AnyDoor\configs\inference.yaml
(Get-Content checkpoints\AnyDoor\configs\anydoor.yaml) -replace 'path/dinov2_vitg14_pretrain.pth', 'checkpoints/dinov2_vitg14_pretrain.pth' | Set-Content checkpoints\AnyDoor\configs\anydoor.yaml
```

- 방법 2, 메모장으로 수정: `notepad checkpoints\AnyDoor\configs\inference.yaml` 실행 → 표의 변경 전 값을 변경 후 값으로 고쳐 저장. `anydoor.yaml`도 같은 방법
- 수정 확인: 아래 2줄 실행 결과가 표의 변경 후 값과 같으면 정상

```powershell
Select-String "pretrained_model" checkpoints\AnyDoor\configs\inference.yaml
Select-String "dinov2_vitg14_pretrain" checkpoints\AnyDoor\configs\anydoor.yaml
```

- `configs\demo.yaml`: AnyDoor 데모 화면 전용, 수정 불필요

## 6. 데이터베이스 구축

- 진행 문서: [database.md](database.md) 2-2 ~ 2-4
- 내용: MySQL에 데이터베이스 `cgi`와 서버 접속 계정 `cgi_app` 생성 → `backend\.env` 접속 설정 파일 작성 → 서버 연결 확인

## 7. 설치 확인

### 7-1. 점검 스크립트 실행

```powershell
$env:ANYDOOR_DIR = "$PWD\checkpoints\AnyDoor"
CGI\Scripts\python.exe scripts\check_env.py
```

- 첫 줄 `$env:ANYDOOR_DIR`: AnyDoor 폴더 위치를 서버와 점검 스크립트에 알려 주는 환경 변수. PowerShell 창을 새로 열 때마다 1회 실행
- 점검 항목: 가상환경, Python·패키지 버전, GPU, AnyDoor 폴더, SAM2 가중치 파일, `backend/.env`
- 정상: 마지막 줄 `결과: 18/18 통과`
- `[NG]` 항목: 해당 항목의 설치 단계를 다시 진행
- `A matching Triton is not available` 경고: Windows에서 항상 출력되는 안내, 무시

### 7-2. 서버 실행 확인

- 점검 스크립트가 확인하지 않는 AnyDoor·DINOv2 가중치 파일, 설정 파일 수정, MySQL 접속은 서버 실행으로 확인
- 실행 방법: [README 9. 실행 방법](../README.md#9-실행-방법)의 백엔드 실행 → 프론트엔드 실행 순서
- 정상
  - 백엔드 로그 `DB 연결 완료`
  - http://localhost:8000/api/health 의 `warmup` 값 `done`
  - http://localhost:5180 에서 테스트 계정 `test` / `test1234` 로그인 후 합성 완료

### 7-3. 자주 발생하는 오류

| 증상 | 원인 | 조치 |
|---|---|---|
| `git`, `py`, `node`, `npm`을 찾을 수 없다는 오류 | 설치 전에 열어 둔 PowerShell 창 사용 | PowerShell 창을 닫고 새로 열기 |
| `py -3.10` 실행 시 Python 3.10을 찾을 수 없다는 오류 | 다른 버전의 Python만 설치됨 | 3-3의 Python 3.10 설치 |
| `npm` 실행 시 `이 시스템에서 스크립트를 실행할 수 없으므로` 오류 | PowerShell 스크립트 실행 정책 제한 | `npm` 대신 `npm.cmd` 사용, 또는 `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` 실행 후 `Y` |
| `torch.cuda.is_available()` 결과 `False` | GPU 미지원 PyTorch 설치, 또는 드라이버 미설치 | 3-1 드라이버 확인 후 4-4 명령 재실행 |
| 4-4 실행 중 `typing_extensions` 관련 설치 실패 | pip 구버전 | 4-3 pip 업그레이드 후 재실행 |
| `No space left on device` | 디스크 여유 공간 부족 | 여유 공간 확보 후 재실행 |
| 서버 예열 중 `epoch=1-step=8687.ckpt` 또는 `dinov2_vitg14_pretrain.pth` 경로 오류 | 모델 파일 위치·이름 불일치, 또는 설정 파일 미수정 | 5-2 저장 위치·파일 이름, 5-3 설정 파일 확인 |
| 백엔드 로그 `DB에 연결하지 못했습니다` | MySQL 계정·비밀번호·서비스 문제 | [database.md 4. 오류별 조치](database.md#4-오류별-조치) |

## 8. 가상환경 사용 규칙

- Python 실행은 가상환경 `CGI`만 사용, 아나콘다 등 다른 환경 사용 안 함
- 활성화 없이 `python`만 입력하면 PC에 설치된 다른 Python 실행 → 패키지 없음 오류

### 8-1. 실행 방법

| 방법 | 명령 |
|---|---|
| 가상환경 경로로 직접 실행, 기본 방식 | `CGI\Scripts\python.exe ...` |
| 활성화 후 실행, 명령 프롬프트 | `CGI\Scripts\activate` 실행 후 `python ...` |
| 활성화 후 실행, PowerShell | `CGI\Scripts\Activate.ps1` 실행 후 `python ...` |

- 활성화되면 명령 줄 앞에 `(CGI)` 표시
- 새 PC의 PowerShell 실행 정책에 따라 `Activate.ps1` 실행 차단 가능. 이 경우 직접 실행 방식 사용

### 8-2. 현재 환경 확인

| 확인 위치 | 명령·화면 | 정상 |
|---|---|---|
| 터미널 | `python -c "import sys; print(sys.executable)"` | 끝이 `CGI\Scripts\python.exe` |
| 점검 스크립트 | `python scripts\check_env.py` | 첫 줄 `[OK] 가상환경 CGI` |
| VS Code | 오른쪽 아래 상태 표시줄의 Python 표시 | `CGI` 포함 |

### 8-3. VS Code 설정

- 저장소 최상위 디렉터리를 VS Code로 열면 `.vscode/settings.json` 적용: 기본 인터프리터 `CGI`, 새 터미널에서 `CGI` 자동 활성화
- 다른 환경이 선택된 경우: `Ctrl+Shift+P` → `Python: Select Interpreter` → `.\CGI\Scripts\python.exe` 선택

### 8-4. 패키지 추가·변경

- 설치: `CGI\Scripts\python.exe -m pip install 패키지==버전`
- 설치 후 `requirements.txt`, "9. 주요 패키지 버전" 표, `scripts\check_env.py` 기준 버전에 반영

## 9. 주요 패키지 버전

- 개발 PC 확인값, 2026-10-15. Python 3.10.0, Node.js 24.19.0, npm 11.17.0, MySQL 8.0.46, NVIDIA 드라이버 595.95

| 용도 | 패키지 | 버전 |
|---|---|---|
| 공통 | torch / torchvision | 2.5.1+cu121 / 0.20.1+cu121 |
| 상의 영역 추출 · SAM2 | sam2 | 1.0, GitHub 커밋 2b90b9f |
| 이미지 합성 · AnyDoor | numpy | 2.2.6 |
| | transformers | 5.14.1 |
| | pytorch-lightning | 1.9.5 |
| | xformers | 0.0.28.post3 |
| 백엔드 | fastapi / uvicorn | 0.143.0 / 0.54.0 |
| 데이터베이스 | SQLAlchemy / PyMySQL / python-dotenv | 2.0.54 / 1.2.3 / 1.2.4 |

- 전체 목록: [pip_freeze.txt](pip_freeze.txt)

## 10. 설치하지 않는 패키지

| 패키지 | 사유 |
|---|---|
| gradio 3.39.0, gradio-client | AnyDoor 데모 화면 전용, numpy 2 미지원으로 numpy 2.2.6과 충돌 |
