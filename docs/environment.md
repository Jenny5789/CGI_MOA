# 개발 환경 참고

- 설치 순서: [README 9. 설치 및 실행](../README.md#9-설치-및-실행)
- 이 문서: 설치 순서에 포함하지 않은 기준 환경, 오류별 조치, 모델 파일 확인, 패키지 버전

## 1. 기준 환경

- 개발 PC 확인값, 2026-10-15

| 항목 | 값 |
|---|---|
| 운영체제 | Windows 11 Pro for Workstations 10.0.26200 |
| CPU / 메모리 | Intel Xeon W-2223 3.60GHz / 32GB |
| GPU | NVIDIA GeForce RTX 3080 10GB, 드라이버 595.95, 합성 시 PyTorch 최대 할당 8.25GB |
| CUDA | 12.1, PyTorch에 포함되어 별도 설치 불필요 |
| Python | 3.10 |
| Node.js / npm | 24.19.0 / 11.17.0 |
| MySQL | 8.0.46 Community Server, 정식 구성 |

- AMD·Intel GPU만 있는 PC는 합성 모델 실행 불가

## 2. 설치 오류별 조치

| 증상 | 원인 | 조치 |
|---|---|---|
| `winget`을 찾을 수 없다는 오류 | Windows 앱 설치 관리자 미설치 | Microsoft Store에서 `앱 설치 관리자` 설치, 또는 아래 설치 파일 사용 |
| `git`, `node`, `npm`을 찾을 수 없다는 오류 | 설치 전에 열어 둔 창 사용 | 창을 닫고 새로 열기 |
| 시작 메뉴에 Anaconda PowerShell Prompt 없음 | 바로가기 미생성 | 일반 PowerShell에서 `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` 실행 후 `Y`, 이어서 `conda init powershell` 실행 후 창을 새로 열기 |
| `conda`를 찾을 수 없다는 오류 | 일반 PowerShell에서 conda 실행 | Anaconda PowerShell Prompt 사용, 또는 위 행의 `conda init powershell` |
| `ModuleNotFoundError` | `(CGI)` 환경이 아닌 상태에서 실행 | `conda activate CGI` 후 재실행 |
| `npm` 실행 시 `이 시스템에서 스크립트를 실행할 수 없으므로` 오류 | PowerShell 스크립트 실행 정책 제한 | `npm` 대신 `npm.cmd` 사용, 또는 `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` 실행 후 `Y` |
| `torch.cuda.is_available()` 결과 `False` | GPU 미지원 PyTorch 설치, 또는 드라이버 미설치 | `nvidia-smi`로 드라이버 확인 후 PyTorch 설치 줄 재실행 |
| PyTorch 설치 중 `typing_extensions` 관련 실패 | pip 구버전 | pip 업그레이드 줄 실행 후 재실행 |
| `No space left on device` | 디스크 여유 공간 부족 | 여유 공간 확보 후 재실행 |
| 서버 예열 중 `epoch=1-step=8687.ckpt` 또는 `dinov2_vitg14_pretrain.pth` 경로 오류 | 가중치 파일 위치·이름 불일치, 또는 설정 파일 미수정 | `python scripts\setup_models.py` 재실행, 3장 모델 파일 확인 |
| AnyDoor 폴더를 찾지 못하는 오류 | 환경 변수 `ANYDOOR_DIR` 미설정 또는 경로 불일치 | `conda env config vars set ANYDOOR_DIR=저장소경로\checkpoints\AnyDoor -n CGI` 실행 후 `conda activate CGI` |
| 백엔드 로그 `DATABASE_URL이 없습니다` | `backend\.env` 미작성 | `python scripts\setup_trial_env.py` 실행 |
| 백엔드 로그 `DB에 연결하지 못했습니다` | SQLite: `storage` 폴더 없음. MySQL: 계정·비밀번호·서비스 문제 | SQLite는 `python scripts\setup_trial_env.py` 재실행. MySQL은 [database.md 4. 오류별 조치](database.md#4-오류별-조치) |

- winget 대신 설치 파일을 쓰는 경우 받는 곳: Git https://git-scm.com/downloads/win , Anaconda https://www.anaconda.com/download/success , Node.js 24 https://nodejs.org/ko/download

## 3. 모델 파일 확인

### 3-1. 크기 확인

- 파일 오른쪽 클릭 → 속성의 바이트 수가 아래와 같으면 정상. 탐색기 목록에는 단위 차이로 약 309MB·15.7GB·4.2GB로 표시

| 파일 | 저장 위치 | 바이트 수 |
|---|---|---|
| `sam2.1_hiera_base_plus.pt` | `checkpoints\sam2\` | 323,606,802 |
| `epoch=1-step=8687.ckpt` | `checkpoints\AnyDoor\checkpoints\` | 16,836,620,171 |
| `dinov2_vitg14_pretrain.pth` | `checkpoints\AnyDoor\checkpoints\` | 4,546,108,579 |

### 3-2. 출처와 브라우저 다운로드

- 출처: SAM2·DINOv2는 Meta 공식 배포 주소, AnyDoor는 AnyDoor 공식 저장소가 안내하는 HuggingFace 주소
- 브라우저 주소창에 붙여 넣으면 다운로드 시작. 받은 파일을 3-1의 저장 위치로 이동하고, 이름이 바뀌었다면 표의 이름으로 변경
  - SAM2: https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_base_plus.pt
  - AnyDoor: https://huggingface.co/spaces/xichenhku/AnyDoor/resolve/main/epoch%3D1-step%3D8687.ckpt
  - DINOv2: https://dl.fbaipublicfiles.com/dinov2/dinov2_vitg14/dinov2_vitg14_pretrain.pth
- 다른 받는 곳: [ModelScope damo/AnyDoor](https://modelscope.cn/models/damo/AnyDoor/files)에 AnyDoor·DINOv2 가중치

### 3-3. AnyDoor 설정 파일

| 파일 | 줄 | 변경 전 | 변경 후 |
|---|---|---|---|
| `checkpoints\AnyDoor\configs\inference.yaml` | 1행 | `pretrained_model: path/epoch=1-step=8687.ckpt` | `pretrained_model: ./checkpoints/epoch=1-step=8687.ckpt` |
| `checkpoints\AnyDoor\configs\anydoor.yaml` | 83행 | `weight: path/dinov2_vitg14_pretrain.pth` | `weight: checkpoints/dinov2_vitg14_pretrain.pth` |

- 확인 명령: 결과가 표의 변경 후 값과 같으면 정상

```powershell
Select-String "pretrained_model" checkpoints\AnyDoor\configs\inference.yaml
Select-String "dinov2_vitg14_pretrain" checkpoints\AnyDoor\configs\anydoor.yaml
```

- `configs\demo.yaml`: AnyDoor 데모 화면 전용, 수정 불필요
- AnyDoor 저장소의 `environment.yaml`, `requirements.txt`는 사용하지 않음. 필요한 패키지는 README 설치 4에서 설치

## 4. conda 환경 사용 규칙

- MOA의 Python 명령은 conda 환경 `CGI`에서만 실행
- `(CGI)` 표시 없이 `python`을 실행하면 다른 환경의 Python 실행 → 패키지 없음 오류

| 확인 위치 | 명령·화면 | 정상 |
|---|---|---|
| 명령 창 | 명령 줄 앞 표시 | `(CGI)` |
| 명령 창 | `python -c "import sys; print(sys.executable)"` | 끝이 `envs\CGI\python.exe` |
| VS Code | 오른쪽 아래 상태 표시줄의 Python 표시 | `CGI` 포함 |

- VS Code: `Ctrl+Shift+P` → `Python: Select Interpreter` → 목록의 `CGI` conda 환경 선택
- 패키지 추가: `(CGI)` 상태에서 `python -m pip install 패키지==버전`. 설치 후 `requirements.txt`, 5장 표, `scripts\check_env.py` 기준 버전에 반영

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
- xformers: cu124 저장소의 0.0.28.post3과 PyTorch 2.5.1 CUDA 12.1 빌드 조합으로 개발 PC 동작 확인

## 6. 설치하지 않는 패키지

| 패키지 | 사유 |
|---|---|
| gradio 3.39.0, gradio-client | AnyDoor 데모 화면 전용, numpy 2 미지원으로 numpy 2.2.6과 충돌 |
