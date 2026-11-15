# 한 PC에서 실행

NVIDIA GPU가 있는 PC 한 대에서 MOA 전체 서비스를 Docker Compose로 실행하는 구성. 화면, 웹 서비스 서버, MySQL, 모델 추론 서버 네 컨테이너가 함께 실행됨.

## 1. 구성

```
브라우저 ──▶ frontend :8080 ──/api──▶ backend ──▶ mysql
                                        └──HTTP──▶ model, GPU
```

| 컨테이너 | 이미지 | 역할 | 외부 공개 |
|---|---|---|---|
| `frontend` | `deploy/frontend.Dockerfile`, nginx | 화면 파일 제공, `/api` 요청을 웹 서비스 서버로 전달 | `WEB_PORT`, 기본 8080 |
| `backend` | `deploy/backend.Dockerfile` | 로그인, 사진·결과 관리, 합성 대기열, 원본 복원 후처리 | 없음 |
| `mysql` | `mysql:8.0` | 회원·세션·사진·작업·결과 기록 | 없음 |
| `model` | `model_server/Dockerfile`, CUDA 12.1 | SAM2 이미지 분할, AnyDoor 이미지 합성, Real-ESRGAN 초해상도 | 없음 |

| 데이터 보관 | 내용 |
|---|---|
| 볼륨 `mysql-data` | MySQL 데이터 |
| 볼륨 `storage` | 올린 사진, 분할 마스크, 합성 결과 |
| 폴더 `checkpoints/` | 가중치, 모델 컨테이너에 읽기 전용 연결 |

## 2. 준비 사항

| 항목 | 조건 |
|---|---|
| GPU | NVIDIA GPU, VRAM 10GB 이상. 10GB 미만은 `MODEL_SAVE_MEMORY=1` |
| Windows | Docker Desktop, WSL2 기반 실행, NVIDIA 그래픽 드라이버 |
| Linux | Docker Engine, Docker Compose, NVIDIA Container Toolkit |
| 디스크 | 가중치 약 5.3GB와 Docker 이미지 공간 |

- GPU 연결 확인: 아래 명령에서 GPU 이름이 나오면 정상

```
docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi
```

## 3. 실행

1. 저장소 받기

```
git clone https://github.com/Jenny5789/CGI_MOA.git
cd CGI_MOA/local
```

2. 가중치 받기: `checkpoints/`에 세 파일을 받고 SHA-256 확인. 이미 받은 파일은 건너뜀

```
docker compose --profile setup run --rm weights
```

| 파일 | 출처 | 크기 |
|---|---|---|
| `weights/mix35000_fp16.ckpt` | Hugging Face [`JI-SEOP/moa-anydoor-mix35000`](https://huggingface.co/JI-SEOP/moa-anydoor-mix35000) | 4.9GB |
| `sam2/sam2.1_hiera_base_plus.pt` | Meta 공식 배포 | 324MB |
| `realesrgan/RealESRGAN_x2plus.pth` | Real-ESRGAN 공식 릴리스 v0.2.1 | 67MB |

- Python이 있으면 저장소 최상위 폴더에서 `python scripts/download_weights.py`로도 같은 결과

3. 서비스 실행: 처음 한 번은 이미지 빌드로 시간이 걸림

```
docker compose up -d --build
```

4. 접속: http://localhost:8080
   - 시험 계정 `test` / `test1234`, 서버가 처음 켜질 때 자동 생성
   - 모델 적재·예열 약 1분 30초. 그동안 합성 요청에는 모델 준비 중 안내
   - 합성 1건 약 20~30초, RTX 3080 10GB 기준

## 4. 상태 확인

| 명령 | 동작 |
|---|---|
| `docker compose ps` | 컨테이너 상태. `model`이 `healthy`면 합성 가능 |
| `docker compose logs -f model` | 모델 적재 진행과 오류 |
| `docker compose logs -f backend` | 웹 서비스 서버 요청 기록 |

## 5. 멈추기와 데이터

| 명령 | 동작 |
|---|---|
| `docker compose stop` | 컨테이너 정지, 데이터 유지 |
| `docker compose up -d` | 다시 시작 |
| `docker compose down` | 컨테이너 삭제, 볼륨 데이터 유지 |
| `docker compose down -v` | 컨테이너와 볼륨 삭제. 회원·사진·결과 모두 삭제 |

- 재시작 정책 `unless-stopped`: PC를 다시 켜면 Docker가 켜질 때 함께 시작. Windows는 Docker Desktop 설정의 로그인 시 자동 시작 필요
- `docker compose stop`으로 멈춘 컨테이너는 직접 다시 시작할 때까지 꺼진 상태 유지

## 6. 설정 변경

- 같은 폴더의 `.env.example`을 `.env`로 복사해 수정, `.env`는 Git 제외

| 값 | 기본값 | 내용 |
|---|---|---|
| `WEB_PORT` | 8080 | 화면 접속 포트 |
| `MODEL_SAVE_MEMORY` | 0 | 1이면 부품 단위 GPU 적재, VRAM 10GB 미만용, 합성 시간 증가 |
| `MOA_WEIGHTS_REPO` | `JI-SEOP/moa-anydoor-mix35000` | 합성 가중치 Hugging Face 저장소 이름 |
| `HF_TOKEN` | 없음 | 이용 조건 동의 후 받는 저장소일 때 Hugging Face 읽기 토큰 |
| `MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD` | 기본 비밀번호 | 영문·숫자만. 첫 실행 뒤 바꾸려면 `docker compose down -v`로 DB 볼륨 삭제 후 다시 실행 |

## 7. 문제 해결

| 증상 | 원인 | 조치 |
|---|---|---|
| `could not select device driver "nvidia"` | Docker에서 GPU 미인식 | Windows는 NVIDIA 드라이버와 Docker Desktop WSL2 설정, Linux는 NVIDIA Container Toolkit 설치 |
| 합성 시 모델 준비 중 안내가 계속됨 | 모델 적재 실패 | `docker compose logs model`, 가중치 파일 위치 확인 |
| 모델 로그에 `CUDA out of memory` | VRAM 부족 | `.env`에 `MODEL_SAVE_MEMORY=1` 후 `docker compose up -d` |
| `port is already allocated` | 8080 포트 사용 중 | `.env`의 `WEB_PORT` 변경 |
| 가중치 받기 중단 | 네트워크 끊김 | 같은 명령 다시 실행, 받은 부분부터 이어 받음 |

## 8. 이용 조건

- 합성 가중치 `mix35000_fp16.ckpt`: 비상업 목적만 허용, 학습 데이터 VITON-HD 라이선스 CC BY-NC 4.0. 상세는 Hugging Face 모델 저장소 설명
- SAM2: Apache-2.0, Real-ESRGAN: BSD-3-Clause, AnyDoor: MIT
