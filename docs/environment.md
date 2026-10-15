# 개발 환경 구축

## 1. 기준 환경

| 항목 | 기준 |
|---|---|
| 운영체제 | Windows 11 |
| Python | 3.10 |
| GPU | NVIDIA RTX 3080 10GB (CUDA 12.1) |
| 가상환경 | 저장소 최상위 디렉터리의 `CGI` |

## 2. 설치 순서

- 실행 위치: 저장소 최상위 디렉터리

1. 가상환경 생성

```bash
python -m venv CGI
```

2. PyTorch 설치 (CUDA 12.1용)

```bash
CGI\Scripts\python.exe -m pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121
```

3. SAM2 설치

```bash
CGI\Scripts\python.exe -m pip install "git+https://github.com/facebookresearch/sam2.git"
```

4. 나머지 패키지 설치 (AnyDoor, 백엔드, DB)

```bash
CGI\Scripts\python.exe -m pip install -r requirements.txt
```

5. xformers 설치 (합성 속도·메모리 개선, PyTorch 버전 유지를 위해 `--no-deps`)

```bash
CGI\Scripts\python.exe -m pip install xformers==0.0.28.post3 --index-url https://download.pytorch.org/whl/cu124 --no-deps
```

6. 모델 가중치 파일 배치 (저장소 미포함, AI 기능·서버 담당에게 요청)
   - SAM2: `checkpoints/sam2/sam2.1_hiera_base_plus.pt`
   - AnyDoor: [features/composition/README.md](../features/composition/README.md) "필요한 것"

7. MySQL 설정: [database.md](database.md)

## 3. 설치 확인

```bash
CGI\Scripts\python.exe scripts\check_env.py
```

- 점검 항목: Python·패키지 버전, GPU, AnyDoor 폴더, SAM2 모델 가중치 파일, `backend/.env`
- 정상: 마지막 줄 `결과: 17/17 통과`
- `[NG]` 항목은 해당 설치 순서를 다시 수행
- `A matching Triton is not available` 경고는 무시 (Windows에서 xformers 정상 동작)

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
