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

## 2. 요청

| 주소 | 입력 | 출력 |
|---|---|---|
| `GET /health` | 없음 | 적재 상태 `loading`·`ready`·`failed`, 가중치 파일, GPU 이름·VRAM |
| `POST /extract` | 파일 `image`, 문자 `points`·`neg_points`·`box` JSON | 0/255 마스크 PNG, 헤더 `X-Elapsed-Sec` |
| `POST /compose` | 파일 `garment`·`garment_mask`·`person`·`area`, 값 `seed`·`steps`·`shape_control`·`refine` | 결과 PNG, 헤더 `X-Crop-Box`·`X-Elapsed-Sec` |

- `X-Crop-Box`: 다시 그린 정사각형 위치 위,아래,왼쪽,오른쪽. 웹 서비스 서버의 박스 선 보정에 사용
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

## 4. 빌드와 실행

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

## 5. 동작 확인

```
CGI\Scripts\python.exe model_server/test_client.py http://localhost:8100 결과폴더
```

- 상품 사진 이미지 분할 → 모델 사진 합성 영역 생성 → 이미지 합성 순서로 요청, 결과 PNG 저장
