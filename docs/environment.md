# 개발 환경 구축

## 1. 기준 환경 (개발 PC 확인값, 2026-10-15)

| 항목 | 값 |
|---|---|
| 운영체제 | Windows 11 Pro for Workstations (10.0.26200) |
| CPU / 메모리 | Intel Xeon W-2223 3.60GHz / 32GB |
| GPU | NVIDIA GeForce RTX 3080 10GB, 드라이버 595.95 |
| CUDA | 12.1 (PyTorch에 포함, 별도 설치 불필요) |
| Python | 3.10.0 (python.org 설치판, `py` 런처 사용) |
| 가상환경 | 저장소 최상위 디렉터리 `CGI` |
| Node.js / npm | 24.19.0 / 11.17.0 |
| MySQL | 8.0.46 Community Server |


## 2. 설치 순서

- 실행 위치: 저장소 최상위 디렉터리

1. Python 3.10으로 가상환경 `CGI` 생성

```bash
py -3.10 -m venv CGI
```

2. PyTorch 설치 (CUDA 12.1용)

```bash
CGI\Scripts\python.exe -m pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121
```

3. SAM2 설치 (상의 영역 추출 모델 코드, 가중치 파일은 6단계)

```bash
CGI\Scripts\python.exe -m pip install "git+https://github.com/facebookresearch/sam2.git"
```

- Git 필요 (GitHub에서 설치)

4. 나머지 패키지 일괄 설치 (`requirements.txt`: AnyDoor, 백엔드, 데이터베이스용)

```bash
CGI\Scripts\python.exe -m pip install -r requirements.txt
```

5. xformers 설치 (합성 속도·GPU 메모리 개선)

```bash
CGI\Scripts\python.exe -m pip install xformers==0.0.28.post3 --index-url https://download.pytorch.org/whl/cu124 --no-deps
```

- `--no-deps`: 2단계에서 설치한 PyTorch 버전을 바꾸지 않음

6. AI 모델 파일 배치 (대용량이라 GitHub에 없음, AI 기능·서버 담당에게 요청)

| 파일 | 종류 | 용도 | 위치 |
|---|---|---|---|
| `sam2.1_hiera_base_plus.pt` | SAM2 가중치 | 상의 영역 추출 | 저장소 `checkpoints/sam2/` |
| AnyDoor 공식 저장소 폴더 | AnyDoor 실행 코드 | 이미지 합성 (합성 모듈이 불러와 실행) | `Desktop\AnyDoor` (다른 위치는 환경 변수 `ANYDOOR_DIR`) |
| `epoch=1-step=8687.ckpt` (약 16.8GB) | AnyDoor 가중치 | 이미지 합성 | AnyDoor 폴더, `configs/inference.yaml`에 경로 지정 |
| `dinov2_vitg14_pretrain.pth` (약 4.5GB) | DINOv2 가중치 | AnyDoor 내부 이미지 특징 추출 | AnyDoor 폴더, `configs/anydoor.yaml`에 경로 지정 |

7. MySQL 설정: [database.md](database.md)

## 3. 설치 확인

```bash
CGI\Scripts\python.exe scripts\check_env.py
```

- 점검 항목: Python·패키지 버전, GPU, AnyDoor 폴더, SAM2 모델 가중치 파일, `backend/.env`
- 정상: 마지막 줄 `결과: 17/17 통과`
- `[NG]` 항목은 해당 설치 순서를 다시 수행
- 실행 시 출력되는 `A matching Triton is not available` 경고는 무시

## 4. 주요 패키지 버전

| 용도 | 패키지 | 버전 |
|---|---|---|
| 공통 | torch / torchvision | 2.5.1+cu121 / 0.20.1+cu121 |
| 상의 영역 추출 (SAM2) | sam2 | 1.0 (GitHub 최신) |
| 이미지 합성 (AnyDoor) | numpy | 2.2.6 |
| | transformers | 5.14.1 |
| | pytorch-lightning | 1.9.5 |
| | xformers | 0.0.28.post3 |
| 백엔드 | fastapi / uvicorn | 0.143.0 / 0.54.0 |
| 데이터베이스 | SQLAlchemy / PyMySQL / python-dotenv | 2.0.54 / 1.2.3 / 1.2.4 |

- 전체 목록: [pip_freeze.txt](pip_freeze.txt)

## 5. 설치하지 않는 패키지

| 패키지 | 사유 |
|---|---|
| gradio 3.39.0, gradio-client | AnyDoor 데모 화면 전용, numpy 2 미지원 (numpy 2.2.6과 충돌) |
