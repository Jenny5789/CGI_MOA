# 도커 실행 (백엔드 + 화면)

## 1. 개요

- 대상: 백엔드 (FastAPI + SAM2 + AnyDoor)와 화면 (`frontend/` 빌드 결과를 nginx로 제공). 화면 코드는 바꾸지 않고 그대로 빌드
- 구성: 브라우저 → `web` (nginx, 5180번) → `/api` 요청은 `backend` (FastAPI, 8000번)로 전달. 화면과 `/api`가 같은 주소라 CORS 설정이 필요 없음. backend 8000번은 기본으로 이 PC에서만 접속되고 (`BACKEND_BIND`), 외부에는 web 5180번만 열림
- 파일 (프로젝트 맨 위 폴더)
  - `Dockerfile`: backend 이미지 만드는 순서
  - `web.Dockerfile`: 화면 이미지 만드는 순서 (Node로 빌드 → nginx에 복사)
  - `nginx.conf`: 화면 제공, `/api`를 backend로 전달, 업로드 상한 20MB
  - `docker-compose.yml`: 실행 방법 (backend: 포트, 가중치 연결, GPU, 저장 위치 / web: 화면 포트)
  - `.dockerignore`, `web.Dockerfile.dockerignore`: 이미지에 넣지 않을 것 (각각 backend용, web용)
  - `.env.docker.example`: 설정 본보기
- backend 이미지: `nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04` 기반, Python 3.10, PyTorch 2.5.1 (CUDA 12.1), AnyDoor 공식 코드 커밋 `44ca2b2` ([README 7-2. 설치](../README.md#7-2-설치)와 같은 버전)
- 모델 가중치는 이미지에 넣지 않고 실행 시 PC 폴더를 읽기 전용으로 연결 (합계 약 21.7GB)

## 2. 준비물

| 항목 | 내용 |
|---|---|
| Docker | Windows: Docker Desktop (WSL2), 리눅스: Docker Engine + NVIDIA Container Toolkit. 컨테이너에서 GPU를 쓸 수 있어야 함 |
| GPU | VRAM 10GB 이상 (RTX 3080 10GB에서 확인) |
| 도커 메모리 | 24GB 이상. AnyDoor 가중치를 읽는 동안 컨테이너 최고 22.6GiB (한도 23.47GiB에서 확인, 여유 거의 없음). Windows는 `%USERPROFILE%\.wslconfig`의 `memory`로 지정 |
| 디스크 | 이미지 약 15.7GB (backend) + 약 131MB (web). 화면 빌드에 필요한 Node는 이미지 안에서 처리하므로 PC에 Node 불필요 |
| 가중치 | 아래 3개 파일 ([README 7-2. 설치](../README.md#7-2-설치)로 받음) |

| 파일 | 크기 | 폴더 설정 |
|---|---|---|
| `epoch=1-step=8687.ckpt` | 약 16.8GB | `ANYDOOR_WEIGHTS_DIR` (두 파일이 같은 폴더) |
| `dinov2_vitg14_pretrain.pth` | 약 4.5GB | `ANYDOOR_WEIGHTS_DIR` |
| `sam2.1_hiera_base_plus.pt` | 약 309MB | `SAM2_WEIGHTS_DIR` (기본 `./checkpoints/sam2`) |

- README 7-2대로 받았다면 `ANYDOOR_WEIGHTS_DIR`은 `checkpoints/AnyDoor/path` 폴더 (컨테이너 `/opt/AnyDoor/path`에 연결)

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
| `VITE_API_MODE` | - | `mixed` | 화면의 API 모드. 빌드할 때 굳으므로 바꾸면 `docker compose up --build -d`로 다시 빌드. `mock` 가짜 서버, `mixed` 실제+가짜, `real` 전부 실제 |
| `WEB_PORT` | - | `5180` | 화면이 열리는 PC 쪽 포트 |
| `BACKEND_BIND` | - | `127.0.0.1` | backend 8000번에 접속할 수 있는 주소. 기본은 이 PC에서만. 다른 PC에서 8000번으로 직접 접속해야 하면 `0.0.0.0` |

## 4. 확인

| 확인 | 주소·명령 | 정상 |
|---|---|---|
| 화면 | `http://localhost:5180` | 홈 화면 (탭 제목 `MOA`), 로그인하면 `/api/auth/login` 요청이 나감 |
| 서버 | `http://localhost:8000/api/health` | `status`: `ok` |
| 프록시 | `http://localhost:5180/api/health` | 서버와 같은 응답 |
| 합성 준비 | 같은 주소 | `warmup`: `done` (예열 중에는 `running`) |
| API 시험 | `http://localhost:8000/docs` | Swagger UI |
| 로그인 | `POST /api/auth/login` | 시험 계정 `test` / `test1234` (서버 시작 시 자동 생성) |
| 로그 | `docker logs moa-backend` | `[MOA] AnyDoor 예열 끝: 합성 준비 완료` |

- 측정값 (RTX 3080 10GB, 시스템 메모리 31.7GB): 예열 약 8.5분, 합성 1장 69초·120초 (두 번 측정, 차이 원인은 확인하지 못함), 합성 중 GPU 최고 8.7~9.3GB, 컨테이너 메모리 최고 19.6~20.1GiB
- 외부 접속 (휴대폰 등): `cloudflared tunnel --no-autoupdate --url http://localhost:5180` ([README 7-5. 외부 접속 · Cloudflare 터널](../README.md#7-5-외부-접속--cloudflare-터널)). 이 구성으로 터널에 접속하는 것은 확인하지 않음

## 5. 운영 명령

| 작업 | 명령 |
|---|---|
| 상태 | `docker ps` |
| 중지·삭제 (데이터 유지) | `docker compose down` |
| 다시 시작 | `docker compose up -d` |
| 코드 변경 반영 | `docker compose up --build -d` |
| 화면만 다시 빌드 | `docker compose up --build -d --no-deps web` (backend는 재시작되지 않아 예열을 다시 기다리지 않음) |
| 데이터까지 삭제 | `docker compose down -v` (볼륨 `moa_storage`의 올린 사진·결과·DB 삭제) |
| 설정 변경 반영 | `docker compose up -d` (`docker-compose.yml`·`.env`를 바꾼 뒤. 컨테이너가 다시 만들어지고 backend는 AnyDoor 예열을 다시 함, 볼륨 데이터는 유지) |
| 헬스체크 상태 | `docker ps`의 `STATUS`에 `healthy` 표시. backend는 서버 응답만 보고, 합성 준비 여부는 `/api/health`의 `warmup` |

- 자동 시작: backend·web 모두 `restart: unless-stopped`. 컨테이너가 스스로 종료되거나 Docker가 다시 시작되면 자동으로 켜짐. `docker compose stop·down`이나 `docker stop·kill`로 멈춘 것은 사람이 멈춘 것으로 보고 다시 켜지 않음
- 로그: 컨테이너마다 10MB 파일 3개까지 보관 (`docker logs`로 확인)

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
| 화면이 가짜 데이터(`mock`)로 동작 | 화면을 빌드할 때 `VITE_API_MODE`가 `mock`이었음 | `.env`의 `VITE_API_MODE` 확인 후 `docker compose up --build -d --no-deps web` |
| 5180번 포트가 이미 사용 중이라는 오류 | 다른 프로그램(예: `npm run dev`)이 5180번 사용 | 그 프로그램 종료 또는 `.env`의 `WEB_PORT` 변경 (터널 주소도 함께 변경) |
| 다른 PC에서 8000번으로 접속이 안 됨 | 기본값이 `127.0.0.1`이라 이 PC에서만 열림 (다른 PC는 5180번으로 접속) | 8000번 직접 접속이 필요하면 `.env`에 `BACKEND_BIND=0.0.0.0` 적고 `docker compose up -d` |
| 사진을 올리면 "요청을 처리하지 못했습니다" | 20MB를 넘는 파일을 nginx가 거절 (413). 10~20MB는 "사진은 10MB 이하만 올릴 수 있습니다."가 표시됨 | 사진을 10MB 이하로 줄여 올림 |

## 8. 확인한 범위

- 환경: Windows 11, Docker Desktop 29.8.0 (WSL2), RTX 3080 10GB, 도커 메모리 `memory=24GB`
- 확인한 것: backend·web 이미지 빌드, 컨테이너 실행, `/api/health`, `/docs`, 로그인, 사진 올리기, SAM2 추출, AnyDoor 합성 (API로 호출, backend 8000번과 web 5180번 경유 모두), 합성 중 로그 오류 없음
- 화면 (5180번) 확인: 홈 화면 열림, 브라우저에서 `test` 로그인 (`/api/auth/login`, `/api/me` 요청 확인), 마이페이지 주소 직접 열기, 업로드 상한 (12MB는 backend 응답, 25MB는 nginx 413)
- 운영 설정 확인: 컨테이너를 삭제하고 다시 만든 뒤 데이터 유지 (결과 번호, 사진·추출·작업·결과 파일 개수, DB 크기, `.file_key` 해시가 재생성 전과 같음), backend 8000번 제한 (이 PC의 4개 주소 모두 거절, 5180번은 모두 접속됨), 헬스체크 `healthy`, 재시작 정책 (web의 nginx를 종료하자 3초 안에 자동 재시작, `docker kill`로 종료한 경우는 재시작하지 않음)
- 확인하지 않은 것: 화면에서 마우스로 하는 전체 합성 흐름, Cloudflare 터널 연결, 다른 PC에서 5180번 접속 (Windows 방화벽 설정 포함), 서버 재부팅 후 자동 시작, backend 자동 재시작 (예열을 다시 함), 요청 동시 처리, 리눅스·학교 서버 실행
