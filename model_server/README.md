# 모델 추론 서버

SAM2 이미지 분할과 AnyDoor 기반 이미지 합성 모델을 HTTP로 제공하는 GPU 전용 서버. 웹 서비스 서버와 분리해 GPU가 있는 컴퓨터의 Docker 컨테이너로 실행.

## 1. 구성

| 파일 | 역할 |
|---|---|
| `app.py` | FastAPI 모델 서버. 시작 시 모델 적재·예열, 이미지 분할·합성 요청 처리 |
| `requirements.txt` | 서버 패키지 목록. 개발 PC conda 환경 `CGI` 검증 버전으로 고정 |
| `Dockerfile` | 컨테이너 이미지 구성 |
| `Dockerfile.dockerignore` | 빌드 시 전송 제외 목록. `features`, `model_server`만 허용 |
| `test_client.py` | 서버 동작 확인용 요청 스크립트 |
| `docker-compose.yml` | 배포용 실행 묶음. GPU 연결, 가중치 읽기 전용 연결, 상태 확인, 자동 재시작 |
| `.env.example`, `.gitignore` | compose 설정값 본보기, `.env` Git 제외 |

## 2. 요청

| 주소 | 입력 | 출력 |
|---|---|---|
| `GET /health` | 없음 | 적재 상태 `loading`·`ready`·`failed`, 가중치 파일, 입력 형식, 초해상도 가중치 파일, GPU 이름·VRAM |
| `POST /extract` | 파일 `image`, 문자 `points`·`neg_points`·`box` JSON, `image_key` | 0/255 마스크 PNG, 헤더 `X-Elapsed-Sec`. 빈 마스크는 422 `EMPTY_MASK` |
| `POST /compose` | 파일 `garment`·`garment_mask`·`person`·`area`, 값 `seed`·`steps`·`shape_control`·`refine` | 결과 PNG, 헤더 `X-Crop-Box`·`X-Elapsed-Sec`·`X-Input-Mode` |
| `GET /progress` | 없음 | 진행 중인 합성의 스텝 진행률 0~1, 합성 중이 아니면 null |

- `X-Crop-Box`: 다시 그린 정사각형 위치 위,아래,왼쪽,오른쪽. 웹 서비스 서버의 박스 선 보정에 사용
- `image_key`: 직전 요청과 같은 값이면 SAM2 이미지 인코딩 생략. 같은 사진에서 점만 바꿔 다시 분할할 때 시간 단축
- 웹 서비스 서버 연결: 웹 서비스 서버에 `MODEL_SERVER_URL` 설정, `backend/model_client.py`가 요청 담당
- 적재 완료 전 `/extract`·`/compose` 요청은 503
- 환경 변수 `MODEL_TOKEN` 설정 시 헤더 `X-Model-Token` 불일치 요청은 401

## 3. 환경 변수

| 이름 | 기본값 | 내용 |
|---|---|---|
| `ANYDOOR_CKPT` | `/weights/anydoor/official_fp16.ckpt` | 합성 가중치 파일 |
| `SAM2_CHECKPOINT` | `/weights/sam2/sam2.1_hiera_base_plus.pt` | SAM2 가중치 파일 |
| `ANYDOOR_DIR` | `/opt/AnyDoor` | AnyDoor 공식 코드 위치, 이미지에 포함 |
| `MODEL_TOKEN` | 비움 | 요청 토큰 |
| `MODEL_SAVE_MEMORY` | `0` | `1`이면 부품 단위 GPU 적재, VRAM 10GB 미만 GPU용 |
| `UPSCALE_CKPT` | `/weights/realesrgan/RealESRGAN_x2plus.pth` | 초해상도 가중치 파일, 없으면 초해상도 없이 합성 |
| `ANYDOOR_INPUT` | `anydoor` | 합성 입력 형식. `retrain`이면 SAM2 사람 영역으로 목·어깨를 계산해 재학습 학습 형식으로 입력, 시험용 |

## 4. 실행 · compose, 배포용

`model_server` 폴더에서 실행.

```
docker compose up -d --build
docker compose ps
```

- 기본 설정: 가중치 `../checkpoints/weights/official_fp16.ckpt`, SAM2 `../checkpoints/sam2`, 초해상도 `../checkpoints/realesrgan`, 포트 8100
- 초해상도 가중치: Real-ESRGAN 공식 릴리스 v0.2.1의 `RealESRGAN_x2plus.pth`, 67,061,725바이트, SHA-256 `49fafd45f8fd7aa8d31ab2a22d14d91b536c34494a5cfe31eb5d89c2fa266abb`. `checkpoints/realesrgan`에 배치
- 다른 가중치·토큰·포트: `.env.example`을 `.env`로 복사해 수정
- `docker compose ps`의 상태 `healthy`: `/health`가 ready, 적재·예열 약 65~90초
- 자동 재시작 `unless-stopped`: 개발 PC 재부팅 후 Docker 실행 시 자동 실행. 평소 개발 중에는 `docker compose down`으로 내려 VRAM 확보
- 웹 서비스 서버 쪽 구성: `deploy/README.md`

## 5. 빌드와 실행 · 명령 직접 입력

저장소 최상위 폴더, PowerShell 기준.

```
docker build -f model_server/Dockerfile -t moa-model:1 .
```

```
docker run -d --name moa-model --gpus all -p 8100:8100 -v "${PWD}\checkpoints\weights:/weights/anydoor:ro" -v "${PWD}\checkpoints\sam2:/weights/sam2:ro" moa-model:1
```

- `checkpoints\weights`: `scripts/convert_weights_fp16.py`로 만든 16비트 합성 가중치 폴더
- 다른 가중치 사용: `-e ANYDOOR_CKPT=/weights/anydoor/aug10000_fp16.ckpt`
- 상시 운영 시 `--restart unless-stopped` 추가. Docker 재시작 시 컨테이너 자동 재실행
- 적재 확인: `docker logs -f moa-model`에서 `적재·예열 완료` 줄, 또는 `http://localhost:8100/health`의 `ready`

## 6. 동작 확인

```
CGI\Scripts\python.exe model_server/test_client.py http://localhost:8100 결과폴더
```

- 상품 사진 이미지 분할 → 모델 사진 합성 영역 생성 → 이미지 합성 순서로 요청, 결과 PNG 저장
