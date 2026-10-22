# 개발 환경 구축

## 1. 기준 환경 · 개발 PC 확인값, 2026-10-15

| 항목 | 값 |
|---|---|
| 운영체제 | Windows 11 Pro for Workstations 10.0.26200 |
| CPU / 메모리 | Intel Xeon W-2223 3.60GHz / 32GB |
| GPU | NVIDIA GeForce RTX 3080 10GB, 드라이버 595.95 |
| CUDA | 12.1, PyTorch에 포함되어 별도 설치 불필요 |
| Python | 3.10.0 python.org 설치판, `py` 런처 사용 |
| 가상환경 | 저장소 최상위 디렉터리 안의 `CGI` 폴더 |
| Node.js / npm | 24.19.0 / 11.17.0 |
| MySQL | 8.0.46 Community Server |

## 2. 설치 순서

- 실행 셸: PowerShell
- 실행 위치: 1단계 이후 모두 저장소 최상위 디렉터리 `CGI_MOA`
- 소요: 모델 파일 약 21.7GB 다운로드 포함

### 0. 사전 설치

| 프로그램 | 기준 | 용도 |
|---|---|---|
| Git | 최신 | 저장소·AnyDoor 받기, SAM2 설치 |
| Python | 3.10, python.org 설치판, 설치 화면에서 `py` 런처 포함 | 가상환경 |
| Node.js | 24 | 프론트엔드 |
| NVIDIA 드라이버 | CUDA 12.1 지원 버전 | GPU 추론 |
| MySQL | 8.0, [database.md](database.md) 2-1 | 로그인·회원 정보 |

### 1. 저장소 받기

```powershell
git clone https://github.com/Jenny5789/CGI_MOA.git
cd CGI_MOA
```

### 2. 가상환경 `CGI` 생성

```powershell
py -3.10 -m venv CGI
```

- 위치: 저장소 안 `CGI_MOA\CGI`. `.gitignore` 등록 폴더라 GitHub에 올라가지 않음
- 이름 `CGI` 고정: `scripts/check_env.py`, `.vscode/settings.json`, `.gitignore`가 이 이름 기준

### 3. pip 업그레이드

```powershell
CGI\Scripts\python.exe -m pip install --upgrade pip
```

- Python 3.10 기본 pip 23.0.1은 PyTorch 다운로드 주소의 `typing_extensions` 파일을 거부해 4단계 실패

### 4. PyTorch 설치 · CUDA 12.1용

```powershell
CGI\Scripts\python.exe -m pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121
```

### 5. SAM2 설치 · 상의 영역 추출 모델 코드

```powershell
CGI\Scripts\python.exe -m pip install "git+https://github.com/facebookresearch/sam2.git@2b90b9f5ceec907a1c18123530e92e794ad901a4"
```

- 개발 PC와 같은 커밋으로 고정. 최신 커밋은 요구 PyTorch 버전 변경 시 4단계 PyTorch 교체 위험
- 가중치 파일은 9단계

### 6. 나머지 패키지 일괄 설치

```powershell
CGI\Scripts\python.exe -m pip install -r requirements.txt
```

- `requirements.txt`: AnyDoor, 백엔드, 데이터베이스용 패키지

### 7. xformers 설치 · 합성 속도·GPU 메모리 개선

```powershell
CGI\Scripts\python.exe -m pip install xformers==0.0.28.post3 --index-url https://download.pytorch.org/whl/cu124 --no-deps
```

- `--no-deps`: 4단계 PyTorch 버전 유지
- cu124 주소의 0.0.28.post3과 PyTorch 2.5.1+cu121 조합으로 개발 PC 동작 확인

### 8. AnyDoor 코드 받기

```powershell
git clone https://github.com/ali-vilab/AnyDoor checkpoints\AnyDoor
git -C checkpoints\AnyDoor checkout 44ca2b2
```

- 위치: 저장소 `checkpoints\AnyDoor`. `checkpoints/`는 `.gitignore` 등록 폴더
- 커밋 `44ca2b2` 고정: 합성 모듈이 `run_inference.py`의 정해진 코드 줄을 바꿔 실행하므로 다른 커밋은 실행 오류 가능
- 서버·점검 실행 시 환경 변수 `ANYDOOR_DIR`로 이 폴더 지정: 3장, [README.md 10-1](../README.md#10-1-백엔드)

### 9. AI 모델 파일 받기

| 파일 | 용도 | 크기 | 저장 위치 |
|---|---|---|---|
| `sam2.1_hiera_base_plus.pt` | SAM2 가중치, 상의 영역 추출 | 323,606,802바이트, 약 309MB | `checkpoints\sam2\` |
| `epoch=1-step=8687.ckpt` | AnyDoor 가중치, 이미지 합성 | 16,836,620,171바이트, 약 16.8GB | `checkpoints\AnyDoor\checkpoints\` |
| `dinov2_vitg14_pretrain.pth` | DINOv2 가중치, AnyDoor 내부 이미지 특징 추출 | 4,546,108,579바이트, 약 4.5GB | `checkpoints\AnyDoor\checkpoints\` |

```powershell
New-Item -ItemType Directory -Force checkpoints\sam2, checkpoints\AnyDoor\checkpoints
curl.exe -L -o checkpoints\sam2\sam2.1_hiera_base_plus.pt https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_base_plus.pt
curl.exe -L -o "checkpoints\AnyDoor\checkpoints\epoch=1-step=8687.ckpt" "https://huggingface.co/spaces/xichenhku/AnyDoor/resolve/main/epoch%3D1-step%3D8687.ckpt"
curl.exe -L -o checkpoints\AnyDoor\checkpoints\dinov2_vitg14_pretrain.pth https://dl.fbaipublicfiles.com/dinov2/dinov2_vitg14/dinov2_vitg14_pretrain.pth
```

- 출처: SAM2·DINOv2는 Meta 공식 배포 주소, AnyDoor는 AnyDoor 공식 저장소 안내의 HuggingFace 주소
- 다른 받는 곳: [ModelScope damo/AnyDoor](https://modelscope.cn/models/damo/AnyDoor/files)에 AnyDoor·DINOv2 가중치 모두 있음
- 크기 확인: 파일 속성의 바이트 수가 표와 같으면 정상. 탐색기 목록은 GiB 기준이라 약 15.7GB·4.2GB·309MB로 표시

### 10. AnyDoor 설정 파일 수정

- 공식 설정의 `path/...` 자리표시 값을 9단계 저장 위치로 변경

| 파일 | 줄 | 변경 전 | 변경 후 |
|---|---|---|---|
| `checkpoints\AnyDoor\configs\inference.yaml` | 1행 | `pretrained_model: path/epoch=1-step=8687.ckpt` | `pretrained_model: ./checkpoints/epoch=1-step=8687.ckpt` |
| `checkpoints\AnyDoor\configs\anydoor.yaml` | 83행 | `weight: path/dinov2_vitg14_pretrain.pth` | `weight: checkpoints/dinov2_vitg14_pretrain.pth` |

- `configs/demo.yaml`: AnyDoor Gradio 데모 전용, 수정 불필요

### 11. MySQL 설정

- [database.md](database.md) 2장

## 3. 설치 확인

```powershell
$env:ANYDOOR_DIR = "$PWD\checkpoints\AnyDoor"
CGI\Scripts\python.exe scripts\check_env.py
```

- 점검 항목: 가상환경, Python·패키지 버전, GPU, AnyDoor 폴더, SAM2 가중치 파일, `backend/.env`
- 정상: 마지막 줄 `결과: 18/18 통과`
- `[NG]` 항목은 해당 설치 순서 재수행
- 실행 시 출력되는 `A matching Triton is not available` 경고는 무시
- 점검 제외 항목: AnyDoor·DINOv2 가중치 파일, 10단계 설정 수정, MySQL 접속
  - AnyDoor 확인: 서버 실행 후 `/api/health`의 `warmup` 값 `done`, [README.md 10-1](../README.md#10-1-백엔드)
  - MySQL 확인: [database.md](database.md) 2-4

## 4. 가상환경 사용 규칙

- Python 실행은 가상환경 `CGI`만 사용, 아나콘다 등 다른 환경 사용 안 함
- 활성화 없이 `python`만 입력하면 PC에 설치된 다른 Python 실행 → 패키지 없음 오류

### 4-1. 실행 방법

| 방법 | 명령 |
|---|---|
| 가상환경 경로로 직접 실행, 기본 방식 | `CGI\Scripts\python.exe ...` |
| 활성화 후 실행, 명령 프롬프트 | `CGI\Scripts\activate` 실행 후 `python ...` |
| 활성화 후 실행, PowerShell | `CGI\Scripts\Activate.ps1` 실행 후 `python ...` |

- 활성화되면 명령 줄 앞에 `(CGI)` 표시
- 새 PC의 PowerShell 실행 정책에 따라 `Activate.ps1` 실행 차단 가능. 이 경우 직접 실행 방식 사용

### 4-2. 현재 환경 확인

| 확인 위치 | 명령·화면 | 정상 |
|---|---|---|
| 터미널 | `python -c "import sys; print(sys.executable)"` | 끝이 `CGI\Scripts\python.exe` |
| 점검 스크립트 | `python scripts\check_env.py` | 첫 줄 `[OK] 가상환경 CGI` |
| VS Code | 오른쪽 아래 상태 표시줄의 Python 표시 | `CGI` 포함 |

### 4-3. VS Code 설정

- 저장소 최상위 디렉터리를 VS Code로 열면 `.vscode/settings.json` 적용: 기본 인터프리터 `CGI`, 새 터미널에서 `CGI` 자동 활성화
- 다른 환경이 선택된 경우: `Ctrl+Shift+P` → `Python: Select Interpreter` → `.\CGI\Scripts\python.exe` 선택

### 4-4. 패키지 추가·변경

- 설치: `CGI\Scripts\python.exe -m pip install 패키지==버전`
- 설치 후 `requirements.txt`, "5. 주요 패키지 버전" 표, `scripts\check_env.py` 기준 버전에 반영

## 5. 주요 패키지 버전

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

## 6. 설치하지 않는 패키지

| 패키지 | 사유 |
|---|---|
| gradio 3.39.0, gradio-client | AnyDoor 데모 화면 전용, numpy 2 미지원으로 numpy 2.2.6과 충돌 |
