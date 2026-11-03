# 도커 실행 (백엔드)

## 1. 개요

- 대상: 백엔드 (FastAPI + SAM2 + AnyDoor). 화면(`frontend/`)은 포함하지 않음
- 파일 (프로젝트 맨 위 폴더)
  - `Dockerfile`: 이미지 만드는 순서
  - `docker-compose.yml`: 실행 방법 (포트, 가중치 연결, GPU, 저장 위치)
  - `.dockerignore`: 이미지에 넣지 않을 것 (`backend/.env`, `storage/`, `checkpoints/`, `frontend/`, `docs/` 등)
  - `.env.docker.example`: 설정 본보기
- 이미지: `nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04` 기반, Python 3.10, PyTorch 2.5.1 (CUDA 12.1), AnyDoor 공식 코드 커밋 `44ca2b2` ([README 설치 4](../README.md#설치-4-python-패키지)·[설치 5](../README.md#설치-5-ai-모델-준비)와 같은 버전)
- 모델 가중치는 이미지에 넣지 않고 실행 시 PC 폴더를 읽기 전용으로 연결 (합계 약 21.7GB)

## 2. 준비물

| 항목 | 내용 |
|---|---|
| Docker | Windows: Docker Desktop (WSL2), 리눅스: Docker Engine + NVIDIA Container Toolkit. 컨테이너에서 GPU를 쓸 수 있어야 함 |
| GPU | VRAM 10GB 이상 (RTX 3080 10GB에서 확인) |
| 도커 메모리 | 24GB 이상. AnyDoor 가중치를 읽는 동안 컨테이너 최고 22.6GiB (한도 23.47GiB에서 확인, 여유 거의 없음). Windows는 `%USERPROFILE%\.wslconfig`의 `memory`로 지정 |
| 디스크 | 이미지 약 15.7GB |
| 가중치 | 아래 3개 파일 ([README 설치 5](../README.md#설치-5-ai-모델-준비)로 받음) |

| 파일 | 크기 | 폴더 설정 |
|---|---|---|
| `epoch=1-step=8687.ckpt` | 약 16.8GB | `ANYDOOR_WEIGHTS_DIR` (두 파일이 같은 폴더) |
| `dinov2_vitg14_pretrain.pth` | 약 4.5GB | `ANYDOOR_WEIGHTS_DIR` |
| `sam2.1_hiera_base_plus.pt` | 약 309MB | `SAM2_WEIGHTS_DIR` (기본 `./checkpoints/sam2`) |

- README 설치 5대로 받았다면 `ANYDOOR_WEIGHTS_DIR`은 `checkpoints/AnyDoor/path` 폴더 (컨테이너 `/opt/AnyDoor/path`에 연결)

## 3. 실행

1. 설정 파일 복사 (프로젝트 맨 위 폴더): `copy .env.docker.example .env` (cmd), `cp .env.docker.example .env` (리눅스)
2. `.env`를 열어 `ANYDOOR_WEIGHTS_DIR`을 내 PC 폴더로 수정. 경로는 `C:/Users/...`처럼 `/`로 적음
3. `docker compose up --build -d`

- `.env`는 `.gitignore`에 들어 있어 git에 올라가지 않음 (PC마다 경로가 다름)
- `ANYDOOR_WEIGHTS_DIR`이 없으면 compose가 시작 전에 안내 문구를 띄우고 멈춤
- 첫 빌드 약 6분 (인터넷 속도에 따라 다름), 이후 코드만 바꾸면 바뀐 단계부터 다시 만듦

### 설정 변수 (`.env`)

| 변수 | 필수 | 기본값 | 설명 |
|---|---|---|---|
| `ANYDOOR_WEIGHTS_DIR` | O | 없음 | AnyDoor 가중치 폴더 |
| `SAM2_WEIGHTS_DIR` | - | `./checkpoints/sam2` | SAM2 가중치 폴더 |
| `MOA_WARMUP` | - | `1` | `0`이면 서버 시작 시 AnyDoor 로딩·예열 생략 |

## 4. 확인

| 확인 | 주소·명령 | 정상 |
|---|---|---|
| 서버 | `http://localhost:8000/api/health` | `status`: `ok` |
| 합성 준비 | 같은 주소 | `warmup`: `done` (예열 중에는 `running`) |
| API 시험 | `http://localhost:8000/docs` | Swagger UI |
| 로그인 | `POST /api/auth/login` | 시험 계정 `test` / `test1234` (서버 시작 시 자동 생성) |
| 로그 | `docker logs moa-backend` | `[MOA] AnyDoor 예열 끝: 합성 준비 완료` |

- 측정값 (RTX 3080 10GB, 시스템 메모리 31.7GB): 예열 약 8.5분, 합성 1장 약 69초, 합성 중 GPU 최고 약 8.7GB, 컨테이너 메모리 최고 19.6GiB

## 5. 운영 명령

| 작업 | 명령 |
|---|---|
| 상태 | `docker ps` |
| 중지·삭제 (데이터 유지) | `docker compose down` |
| 다시 시작 | `docker compose up -d` |
| 코드 변경 반영 | `docker compose up --build -d` |
| 데이터까지 삭제 | `docker compose down -v` (볼륨 `moa_storage`의 올린 사진·결과·DB 삭제) |

## 6. 저장 위치와 DB

- 올린 사진·결과·SQLite 파일 (`moa_trial.db`): 이름 있는 볼륨 `moa_storage` → 컨테이너 `/app/storage`. 컨테이너를 삭제해도 남음
- DB: SQLite (`DATABASE_URL=sqlite:///storage/moa_trial.db`, `docker-compose.yml`에서 지정). MySQL 컨테이너는 없고, `backend/.env`는 이미지에 들어가지 않음
- SQLite에서는 `ON DELETE CASCADE` 같은 삭제 규칙이 동작하지 않을 수 있음: `backend/db.py`에 외래키를 켜는 설정이 없고 SQLite는 기본적으로 꺼져 있음 (실제 삭제 동작은 확인하지 않음)

## 7. 문제 해결

| 증상 | 원인 | 조치 |
|---|---|---|
| `.env 에 ANYDOOR_WEIGHTS_DIR 를 적어 주세요` | `.env`가 없거나 값이 비어 있음 | 3장 1~2번 |
| 8000번 포트가 이미 사용 중이라는 오류 | 다른 프로그램이 8000번 사용 | 그 프로그램 종료. 번호를 바꾸려면 `docker-compose.yml`의 `ports`와 화면의 `VITE_API_TARGET`을 함께 수정 |
| 컨테이너가 시작 직후 종료 | 메모리 부족일 수 있음 | `docker inspect -f "{{.State.OOMKilled}}" moa-backend`가 `true`면 도커 메모리를 올림 (Windows: `.wslconfig`의 `memory` 수정 후 `wsl --shutdown`, 모든 컨테이너 재시작됨) |
| `warmup`이 `running`에서 오래 머묾 | AnyDoor 가중치(16.8GB)를 읽는 중 | `docker logs -f moa-backend`로 진행 확인 |

## 8. 확인한 범위

- 환경: Windows 11, Docker Desktop 29.8.0 (WSL2), RTX 3080 10GB, 도커 메모리 `memory=24GB`
- 확인한 것: 이미지 빌드, 컨테이너 실행, `/api/health`, `/docs`, 로그인, 사진 올리기, SAM2 추출, AnyDoor 합성 (API로 호출), 합성 중 로그 오류 없음
- 확인하지 않은 것: 화면(`frontend/`) 연결, 컨테이너를 껐다 켠 뒤 데이터 유지, 요청 동시 처리, 리눅스·학교 서버 실행
