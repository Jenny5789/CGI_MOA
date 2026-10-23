# 개발 환경 구축

새 Windows PC에서 MOA를 처음 설치하는 순서입니다. 각 단계마다 설치 대상, 필요한 이유, 설치 명령, 설치 확인 방법을 함께 적었습니다. 위에서부터 순서대로 명령을 붙여 넣어 실행하면 됩니다.

## 1. 전체 흐름

| 순서 | 내용 | 설치 대상 | 설치 방법 |
|---|---|---|---|
| 1 | PC 사양 확인 | NVIDIA GPU, 디스크 여유 공간 | 화면 확인 |
| 2 | 기본 프로그램 설치 | NVIDIA 드라이버, Git, Anaconda, Node.js 24, MySQL 8.0 | 드라이버·MySQL은 설치 파일, 나머지는 winget 명령 |
| 3 | 저장소 받기와 conda 환경 구축 | MOA 소스 코드, conda 환경 `CGI`, PyTorch·SAM2·AnyDoor 실행 패키지 | 명령 |
| 4 | AI 모델 준비 | AnyDoor 코드, 모델 가중치 파일 3개, 설정 파일 경로 수정 | 명령 |
| 5 | 데이터베이스 구축 | MySQL 데이터베이스·계정, 접속 설정 파일 | MySQL Workbench, 명령 |
| 6 | 설치 확인 | 점검 스크립트, 서버 실행 | 명령 |

- 다운로드: 모델 파일 약 21.7GB와 PyTorch 등 Python 패키지
- conda 환경: Python 버전과 패키지를 프로젝트별로 격리하는 실행 공간. PC에 이미 설치된 Python이나 다른 conda 환경에 영향 없음

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

### 3-1. NVIDIA 그래픽 드라이버 · 설치 파일

- 설치 대상: NVIDIA GPU를 Windows에서 사용하기 위한 드라이버
- 필요한 이유: PyTorch가 GPU로 AI 모델을 실행하려면 CUDA 12.1 이상을 지원하는 드라이버 필요. CUDA 자체는 PyTorch에 포함되어 별도 설치 불필요
- 받는 곳: https://www.nvidia.com/ko-kr/drivers/ 에서 그래픽 카드 모델 선택 후 최신 드라이버 다운로드
- 설치 방법: 받은 파일 실행 → 기본 선택대로 진행 → 설치 후 PC 재시작
- 설치 확인: 시작 메뉴에서 `PowerShell` 검색 → Windows PowerShell 실행 후 입력

```powershell
nvidia-smi
```

- 정상: 표 오른쪽 위 `CUDA Version`이 12.1 이상

### 3-2. Git · Anaconda · Node.js · winget 명령

- winget: Windows 10·11에 기본 포함된 프로그램 설치 명령. 설치 파일을 직접 찾지 않고 명령 한 줄로 공식 배포판 설치
- 실행 위치: Windows PowerShell

| 프로그램 | 설치 대상 | 필요한 이유 |
|---|---|---|
| Git | 소스 코드 버전 관리 프로그램 | GitHub에서 MOA 저장소·AnyDoor 코드 받기, SAM2 패키지 설치 |
| Anaconda | conda 환경 관리 도구와 Python 배포판 | MOA 전용 Python 3.10 환경 생성. Anaconda나 Miniconda가 이미 있으면 생략 |
| Node.js 24 | JavaScript 실행 환경과 패키지 관리 도구 npm | React 웹 화면 개발 서버 실행 |

```powershell
winget install -e --id Git.Git
winget install -e --id Anaconda.Anaconda3
winget install -e --id OpenJS.NodeJS.LTS --version 24.22.1
```

- 첫 실행 시 원본 사용 약관 동의를 묻는 경우 `Y` 입력
- `--version 24.22.1`: Node.js 24 고정. 생략하면 그 시점의 최신 LTS 버전 설치
- 설치 화면 방식이 필요한 경우 받는 곳: Git https://git-scm.com/downloads/win , Anaconda https://www.anaconda.com/download/success , Node.js https://nodejs.org/ko/download
- 설치 확인: PowerShell 창을 닫고 새로 연 뒤 실행

```powershell
git --version
node -v
npm -v
```

- 정상: `git version 2.xx`, `v24.x.x`, npm 버전 숫자

### 3-3. MySQL 8.0 · 설치 파일

- 설치 대상: 회원 정보와 로그인 기록을 저장하는 데이터베이스 서버
- 필요한 이유: 회원가입·로그인·사진첩 기능이 MySQL에 데이터 저장
- 설치 파일 방식인 이유: winget에서는 8.4만 제공, 팀 기준 버전은 8.0.46
- 설치 방법과 확인: [database.md](database.md) 2-1. 설치 중 정한 `root` 비밀번호는 5장에서 사용하므로 따로 기록

### 3-4. VS Code · 선택

- 설치 대상: 코드 편집기, 필수 아님
- 설치 명령: `winget install -e --id Microsoft.VisualStudioCode`

## 4. 저장소 받기와 conda 환경 구축

### 4-1. Anaconda PowerShell Prompt 열기

- 4장부터는 conda 명령을 쓸 수 있는 창에서 실행
- 시작 메뉴에서 `Anaconda PowerShell Prompt` 검색 → 실행
- 정상: 명령 줄 앞에 `(base)` 표시
- 일반 PowerShell에서 conda를 쓰려면 아래 명령을 1회 실행한 뒤 창을 새로 열기. 실행 정책 질문에는 `Y`

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
conda init powershell
```

### 4-2. 저장소 받기

- 설치 대상: MOA 전체 소스 코드
- 설치 위치 예시: `C:\CGI_MOA`. 경로에 한글·공백이 없는 폴더 권장

```powershell
cd C:\
git clone https://github.com/Jenny5789/CGI_MOA.git
cd CGI_MOA
```

- 이후 모든 명령은 이 `CGI_MOA` 폴더에서 실행. 창을 새로 열었다면 먼저 `cd C:\CGI_MOA`

### 4-3. conda 환경 `CGI` 생성과 활성화

- 설치 대상: Python 3.10이 들어 있는 MOA 전용 conda 환경
- 필요한 이유: MOA가 사용하는 PyTorch 2.5.1과 AnyDoor 패키지 조합이 Python 3.10 기준으로 검증됨

```powershell
conda create -n CGI python=3.10 -c conda-forge --override-channels -y
conda activate CGI
```

- `-c conda-forge --override-channels`: 커뮤니티 공개 채널 conda-forge에서 Python 설치. Anaconda 기본 채널의 약관 동의 절차 없이 진행
- 정상: 명령 줄 앞이 `(base)`에서 `(CGI)`로 변경
- 창을 새로 열 때마다 `conda activate CGI` 1회 실행. 4장 이후의 `python` 명령은 모두 `(CGI)` 상태에서 실행
- 이름 `CGI`: 팀 문서와 점검 스크립트가 이 이름 기준

### 4-4. pip 업그레이드

- 설치 대상: Python 패키지 설치 도구 pip 최신 버전
- 필요한 이유: 구버전 pip은 PyTorch 다운로드 서버의 일부 파일을 거부해 4-5 단계 실패

```powershell
python -m pip install --upgrade pip
```

### 4-5. PyTorch · 딥러닝 프레임워크

- 설치 대상: torch 2.5.1, torchvision 0.20.1의 CUDA 12.1 빌드
- 필요한 이유: SAM2와 AnyDoor 모델을 GPU에서 실행하는 기반 라이브러리

```powershell
python -m pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121
```

- `--index-url`: 일반 pip 저장소에는 GPU 미지원 빌드만 있어 PyTorch 공식 CUDA 12.1 저장소를 지정
- 설치 확인: `True`가 나오면 GPU 사용 가능

```powershell
python -c "import torch; print(torch.cuda.is_available())"
```

### 4-6. SAM2 · 상의 영역 분할 모델 코드

- 설치 대상: Meta의 Segment Anything 2 라이브러리
- 필요한 이유: 사용자가 사진에 찍은 점을 기준으로 상의 영역을 자동 분할
- 받는 곳: Meta 공식 GitHub 저장소 https://github.com/facebookresearch/sam2 . pip이 Git으로 직접 받아 설치

```powershell
python -m pip install "git+https://github.com/facebookresearch/sam2.git@2b90b9f5ceec907a1c18123530e92e794ad901a4"
```

- 마지막 `@2b90b9f...`: 개발 PC와 같은 코드 버전으로 고정. 최신 버전은 요구 PyTorch 버전이 달라져 4-5에서 설치한 PyTorch가 교체될 위험
- `Failed to build the SAM 2 CUDA extension` 안내: 일부 후처리 가속 기능만 제외, 영역 분할 결과에 영향 없음
- 모델 가중치 파일은 5-2 단계에서 별도 다운로드

### 4-7. 나머지 Python 패키지 일괄 설치

- 설치 대상: 저장소의 `requirements.txt`에 적힌 패키지 전체

| 구분 | 주요 패키지 | 역할 |
|---|---|---|
| AnyDoor 실행 | pytorch-lightning, transformers, open_clip_torch, timm, omegaconf, einops, opencv | 합성 모델 구성·이미지 처리 |
| 영역 분할 보조 | segment-anything, kornia | 마스크 후처리 |
| 백엔드 서버 | fastapi, uvicorn, python-multipart | 웹 API 서버, 이미지 업로드 처리 |
| 데이터베이스 | sqlalchemy, pymysql, python-dotenv | MySQL 접속, 접속 설정 파일 읽기 |

```powershell
python -m pip install -r requirements.txt
```

### 4-8. xformers · 합성 속도·GPU 메모리 최적화

- 설치 대상: 어텐션 연산을 빠르고 적은 메모리로 처리하는 라이브러리
- 필요한 이유: AnyDoor 합성 속도 향상과 GPU 메모리 사용량 감소

```powershell
python -m pip install xformers==0.0.28.post3 --index-url https://download.pytorch.org/whl/cu124 --no-deps
```

- `--no-deps`: xformers가 다른 PyTorch 버전을 함께 설치하지 않도록 차단, 4-5의 PyTorch 2.5.1 유지
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
- AnyDoor 저장소의 `environment.yaml`, `requirements.txt`는 사용하지 않음. 필요한 패키지는 4장에서 설치 완료

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
conda activate CGI
$env:ANYDOOR_DIR = "$PWD\checkpoints\AnyDoor"
python scripts\check_env.py
```

- `$env:ANYDOOR_DIR`: AnyDoor 폴더 위치를 서버와 점검 스크립트에 알려 주는 환경 변수. 창을 새로 열 때마다 1회 실행
- 점검 항목: 실행 환경, Python·패키지 버전, GPU, AnyDoor 폴더, SAM2 가중치 파일, `backend/.env`
- 정상: `가상환경 CGI` 항목을 제외한 모든 항목 `[OK]`
- `가상환경 CGI` 항목: 점검 스크립트가 venv 방식 가상환경만 인식해 conda 환경에서는 `[NG]` 표시. 실행 경로 끝이 `envs\CGI\python.exe`이면 정상
- 그 밖의 `[NG]` 항목: 해당 항목의 설치 단계를 다시 진행
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
| `git`, `conda`, `node`, `npm`을 찾을 수 없다는 오류 | 설치 전에 열어 둔 창 사용, 또는 일반 PowerShell에서 conda 실행 | 창을 닫고 새로 열기. conda는 4-1의 Anaconda PowerShell Prompt 사용 |
| `ModuleNotFoundError` | `(CGI)` 환경이 아닌 상태에서 실행 | `conda activate CGI` 후 재실행 |
| `npm` 실행 시 `이 시스템에서 스크립트를 실행할 수 없으므로` 오류 | PowerShell 스크립트 실행 정책 제한 | `npm` 대신 `npm.cmd` 사용, 또는 `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` 실행 후 `Y` |
| `torch.cuda.is_available()` 결과 `False` | GPU 미지원 PyTorch 설치, 또는 드라이버 미설치 | 3-1 드라이버 확인 후 4-5 명령 재실행 |
| 4-5 실행 중 `typing_extensions` 관련 설치 실패 | pip 구버전 | 4-4 pip 업그레이드 후 재실행 |
| `No space left on device` | 디스크 여유 공간 부족 | 여유 공간 확보 후 재실행 |
| 서버 예열 중 `epoch=1-step=8687.ckpt` 또는 `dinov2_vitg14_pretrain.pth` 경로 오류 | 모델 파일 위치·이름 불일치, 또는 설정 파일 미수정 | 5-2 저장 위치·파일 이름, 5-3 설정 파일 확인 |
| 백엔드 로그 `DB에 연결하지 못했습니다` | MySQL 계정·비밀번호·서비스 문제 | [database.md 4. 오류별 조치](database.md#4-오류별-조치) |

## 8. conda 환경 사용 규칙

- MOA의 Python 명령은 conda 환경 `CGI`에서만 실행
- `(CGI)` 표시 없이 `python`을 실행하면 다른 환경의 Python 실행 → 패키지 없음 오류

### 8-1. 현재 환경 확인

| 확인 위치 | 명령·화면 | 정상 |
|---|---|---|
| 명령 창 | 명령 줄 앞 표시 | `(CGI)` |
| 명령 창 | `python -c "import sys; print(sys.executable)"` | 끝이 `envs\CGI\python.exe` |
| VS Code | 오른쪽 아래 상태 표시줄의 Python 표시 | `CGI` 포함 |

### 8-2. VS Code 설정

- `Ctrl+Shift+P` → `Python: Select Interpreter` → 목록의 `CGI` conda 환경 선택
- 선택 후 VS Code 새 터미널에서 `CGI` 환경 자동 활성화

### 8-3. 패키지 추가·변경

- 설치: `(CGI)` 상태에서 `python -m pip install 패키지==버전`
- 설치 후 `requirements.txt`, "9. 주요 패키지 버전" 표, `scripts\check_env.py` 기준 버전에 반영

## 9. 주요 패키지 버전

- 개발 PC 확인값, 2026-10-15. Python 3.10, Node.js 24.19.0, npm 11.17.0, MySQL 8.0.46, NVIDIA 드라이버 595.95

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
