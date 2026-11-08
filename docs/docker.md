# Docker로 실행

MOA 서비스(서버, DB, 화면)를 Docker Compose로 한 번에 실행하는 방법

## 1. 구성

| 컨테이너 | 내용 | 주소 |
|---|---|---|
| `cgimoa-backend` | FastAPI 서버, SAM2 추출, AnyDoor 합성 (GPU) | http://localhost:8000 (이 PC에서만) |
| `cgimoa-mysql` | MySQL 8.0.46 | 컨테이너끼리만 접속 (포트 공개 안 함) |
| `cgimoa-frontend` | 화면 빌드 결과 + nginx, `/api`는 backend로 전달 | http://localhost:5180 |

| 파일 | 역할 |
|---|---|
| `docker-compose.yml` | 세 컨테이너 묶음 (`cgimoa`) |
| `Dockerfile`, `.dockerignore` | backend 이미지 |
| `frontend.Dockerfile`, `frontend.Dockerfile.dockerignore`, `nginx.conf` | frontend 이미지 |
| `.env.docker.example` | `.env` 작성 예시 (`.env`는 git 제외) |
| `scripts/make_inference_ckpt.py` | AnyDoor 추론용 가중치 만들기 |

## 2. 준비

- Docker Desktop (WSL2), NVIDIA GPU 드라이버
- 가중치: 이미지에 넣지 않고 실행할 때 폴더를 연결
  - AnyDoor: `epoch=1-step=8687.ckpt`, `dinov2_vitg14_pretrain.pth` (한 폴더에)
  - SAM2: `sam2.1_hiera_base_plus.pt` (`checkpoints/sam2`)
- AnyDoor 추론용 가중치 만들기: 학습 전용 값(`optimizer_states` 등) 제거, 16.8GB → 9.8GB
  ```
  python scripts/make_inference_ckpt.py 원본.ckpt 새폴더/epoch=1-step=8687.ckpt
  ```
  - 마지막 줄 `비교: 원본과 모두 같음` 확인
  - 같은 폴더에 `dinov2_vitg14_pretrain.pth` 복사 (또는 `mklink /H`로 하드 링크)
  - 원본 가중치를 그대로 쓰면 모델 준비 중 메모리 부족이 날 수 있음 (6장)
- `.env` 작성
  ```
  copy .env.docker.example .env
  ```
  - `ANYDOOR_WEIGHTS_DIR`: 추론용 가중치 폴더 (`/`로 구분)
  - `MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD`: 영문·숫자만 (DB 접속 주소에 들어감)

## 3. 실행과 확인

```
docker compose up --build -d
docker compose ps
```

- `cgimoa-mysql`이 `healthy`가 된 뒤 backend가 켜짐 (서버는 시작할 때 DB 연결을 한 번만 시도)
- `docker compose logs backend`에서 아래 두 줄 확인
  - `DB 연결 완료 (로그인 기능 사용 가능)`
  - `[MOA] AnyDoor 예열 끝: 합성 준비 완료` (켜고 약 3~4분 뒤)
- http://localhost:5180 → 시험 계정으로 로그인 → 합성하기
- http://localhost:5180/api/health 의 `"warmup":"done"`이면 합성 가능

## 4. 멈추기와 데이터

| 명령 | 결과 |
|---|---|
| `docker compose stop` | 멈춤 (`docker compose start`로 다시 켬) |
| `docker compose down` | 컨테이너 삭제, 데이터는 남음 |
| `docker compose down -v` | 컨테이너와 **데이터 모두 삭제** (회원, 기록, 올린 사진) |

- 데이터 보관함: `storage` (사진·결과), `mysql-data` (DB)
- 코드를 고친 뒤 `docker compose up --build -d`: 바뀐 컨테이너만 다시 켜짐

## 5. 가중치 교체

- `.env`의 `ANYDOOR_WEIGHTS_DIR`를 새 폴더로 바꾸고 `docker compose up -d` (backend만 다시 켜지고 예열 다시 함)
- 폴더 안 파일 이름은 `epoch=1-step=8687.ckpt` 유지 (AnyDoor 설정 `configs/inference.yaml`이 이 이름을 찾음)
- `save_weights_only=True`로 저장한 가중치(재학습 결과)는 정리 불필요. 학습 기록이 든 파일만 2장의 스크립트로 정리

## 6. 메모리

- 모델 준비(예열) 때 메모리가 가장 많이 필요함: 빈 모델과 가중치 파일 내용이 동시에 올라감
- Docker Desktop은 WSL 메모리 한도(`%USERPROFILE%\.wslconfig`의 `memory`) 안에서만 실행

| 가중치 | backend 최고 메모리 | 예비 공간(swap) | 결과 |
|---|---|---|---|
| 원본 (16.8GB) | 22.77GiB | 2.90GiB | 한도 23.47GiB에 닿음, 실패하기도 함 |
| 추론용 (9.8GB) | 20.02GiB | 0 | 여유 약 3GiB |

확인: 2026-11-08, WSL 한도 24GB (mysql 0.49GiB, frontend 0.02GiB 별도)

## 7. 측정값

확인: 2026-11-08, RTX 3080 10GB, 추론용 가중치

| 항목 | 값 |
|---|---|
| 예열 | 약 3분 30초 |
| 합성 (요청 → 결과) | 약 51초 (DDIM 50스텝 18초) |
| 이미지 크기 | backend 10.4GB, frontend 131MB |
| 첫 빌드 | PyTorch 단계만 약 9분. 코드만 고치면 위 단계는 재사용 |

## 8. 문제 해결

| 증상 | 원인·조치 |
|---|---|
| 로그인 시 `503 DB_UNAVAILABLE` | backend가 DB에 연결하지 못함. mysql이 `healthy`인지 확인, `.env` 비밀번호 확인 후 `docker compose restart backend` |
| `warmup`이 `failed`, 로그에 `Cannot allocate memory` | 메모리 부족. 추론용 가중치 사용 (2장), 다른 컨테이너·프로그램 종료 |
| 화면에 가짜 데이터가 나옴 | `VITE_API_MODE`가 `mock`. `frontend.Dockerfile`의 값 확인 후 `docker compose up --build -d` |
| `port is already allocated` | 5180·8000을 다른 프로그램이 사용 중 (`npm run dev`, 직접 켠 서버) |