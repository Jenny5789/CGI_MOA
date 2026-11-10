# 이미지 합성 모듈 (AnyDoor)

## 1. 개요

- 역할: 추출한 상의를 인물 이미지의 착용 영역에 합성
- 모델: AnyDoor (확산 모델 기반 이미지 합성), 공식 코드(`run_inference.py`)를 수정 없이 불러와 사용
- 사용처: 백엔드 `routers/compose.py` ([api.md 5. 이미지 합성 API](../../docs/api.md#5-이미지-합성-api-anydoor))

## 2. 함수

```python
from features.composition import compose, warmup

result = compose(ref_rgb, ref_mask, tar_rgb, tar_mask, seed=1234, on_progress=fn, steps=50)
```

| 인자 | 형식 | 필수 | 설명 |
|---|---|---|---|
| `ref_rgb` | `np.uint8` (H, W, 3) | O | 상의 이미지 (RGB) |
| `ref_mask` | `np.uint8` (H, W) | O | 상의 영역 (1: 상의, 0: 나머지), 상의 이미지와 같은 크기 |
| `tar_rgb` | `np.uint8` (H, W, 3) | O | 인물 이미지 (RGB) |
| `tar_mask` | `np.uint8` (H, W) | O | 착용 영역 (1: 합성 위치), 인물 이미지와 같은 크기 |
| `seed` | `int` | - | 같은 값이면 같은 결과 (생략 시 무작위) |
| `on_progress` | 함수 | - | 진행률(0~1)을 받는 함수, 스텝마다 호출 |
| `steps` | `int` | - | 스텝 수 (기본 50, 줄이면 빨라지나 품질 변화) |
| `shape_control` | `bool` | - | 참이면 칠한 모양 그대로 다시 그림 (기본 거짓: 칠한 영역을 감싼 사각형) |
| `refine` | `bool` | - | 참이면 상의 영역 가장자리를 보정 모델(iseg, CPU)로 다듬은 뒤 합성 (기본 거짓) |

- 반환: `np.uint8` (H, W, 3) RGB, 인물 이미지와 같은 크기
- `ref_mask`: 상의 영역 추출 모듈(`extract_object`) 결과를 그대로 사용
- `tar_mask`: 기본은 영역을 감싸는 사각형만 사용, `shape_control=True`면 칠한 모양 그대로 (AnyDoor 웹 데모 Enable Shape Control과 같음, 2026-10-17)
- `refine`: AnyDoor 웹 데모 Reference Mask Refine과 같음. 긴 변 1024px로 줄여 계산 (1024px 상의 사진 약 1.6초)
- 다시 그리는 범위: `tar_mask` 사각형(1.1배)을 다시 1.3배 넓힌 정사각형 (AnyDoor 기본 1.5~2.9배 무작위 대신 고정, `AnyDoorComposer(crop_ratio=...)`로 변경)
- `warmup()`: 모델 로딩 + 2스텝 시험 합성 (백엔드 시작 시 자동 실행)
- 모델은 첫 호출 시 1회 로딩 후 재사용
- 계산 방식: 16비트 연산·가중치. 32비트 가중치 대비 평균 픽셀 차이 0.033/255, 2026-11-09 확인
- 가중치 적재 방식: 2026-11-09부터 적용
  - mmap 적재: 가중치 파일을 RAM에 통째로 복사하지 않고 필요한 부분만 읽음
  - 16비트 가중치: U-Net·ControlNet·VAE·DINOv2 네 부품을 16비트로 변환, 확산 일정 값은 32비트 유지
  - DINOv2 중복 적재 생략: 합성 가중치 파일에 같은 값이 모두 있어 `dinov2_vitg14_pretrain.pth`를 읽지 않음
  - 네 부품 GPU 상주: 16비트 기준 SAM2와 함께 올려도 VRAM 10GB 이내
- `AnyDoorComposer(save_memory=True)`: VRAM이 더 작은 GPU용 부품 단위 적재, 2026-10-21 도입
  - 큰 부품 네 개를 CPU에 두고 사용 중인 묶음만 GPU 적재
  - 묶음 교체 순서: 기존 묶음 해제 후 새 묶음 적재. `_shift_out_first`가 AnyDoor `low_vram_shift` 대체

### 원본 복원 후처리 (`restore.py`)

```python
from features.composition import restore_scene

final, info = restore_scene(tar_rgb, result, tar_mask, extract=extract_object, crop_box=last_crop_box())
# final: RGB uint8, 인물 이미지와 같은 크기 / info: method object·boundary, garment_found, seam_fix
```

- 물체 기준 원본 복원, 2026-11-10: 위치가 아닌 각 픽셀이 무엇인지로 원본과 합성 결과를 나눔
  - SAM2로 찾는 영역 4개: 원본 사람, 합성 결과 사람, 새 상의, 원래 상의
  - 합성 결과에서 가져올 곳: 합성 영역 상단 경계 아래의 합성 결과 사람과 새 상의
  - 원래 사람이 있었는데 합성 결과 사람이 덮지 않은 곳: 원래 사람을 지운 원본 배경 추정으로 채움
  - 배경·얼굴·머리: 원본 그대로. 원본과 합성 결과가 바뀌는 선이 항상 사람·옷 윤곽에 놓임
  - 효과: 기존 방식의 어깨·팔 옆 세로 잔상과 박스 선 보정의 붉은 얼룩 제거, 다시 그린 정사각형 안 배경 중 원본 그대로인 비율 85.5~91.3% → 98.1~99.2%
- 사람을 찾지 못하면 기존 상단 경계 방식 `restore_original`로 처리, 이때만 박스 선 보정 적용
  - 상단 경계: 세로줄마다 합성 영역 최상단을 이은 선, 위 = 원본, 아래 = 합성 결과, 블렌딩 폭 20px
- `find_garment`: 합성 영역을 감싼 박스를 프롬프트로 SAM2 실행, 합성 영역 대비 0.3~2배 밖이면 `None`
- 서버: `backend/routers/compose.py`가 합성 직후 적용, SAM2는 `backend/model_client.extract`

### 박스 선 보정 (`seam.py`)

```python
from features.composition import compose, fix_seam, last_crop_box

result = compose(ref_rgb, ref_mask, tar_rgb, tar_mask)
result = fix_seam(tar_rgb, result, last_crop_box())   # RGB uint8, 인물 이미지와 같은 크기
```

- 문제: AnyDoor가 다시 그린 정사각형(크롭 영역)을 원본에 붙인 테두리가 선으로 보임 (다시 그린 부분의 배경 밝기·색이 원본과 조금 다름)
- 방법: 테두리의 "원본 - 합성 결과" 색 차이 중 튀는 값(원본과 내용이 다른 곳)은 빼고, 그 차이만큼 네모 안쪽을 부드럽게 보정
- `last_crop_box()`: 가장 최근 합성의 크롭 영역 (위, 아래, 왼쪽, 오른쪽), `compose` 직후 호출
- 효과 (100장 시험, 2026-10-21): 박스 선 세기(테두리 안팎 밝기 차이) 평균 2.49 → 0.57
- 서버: `backend/routers/compose.py`가 원본 복원을 끈 경우, 또는 원본 복원이 사람을 찾지 못해 상단 경계 방식으로 처리할 때 적용

## 3. 환경 변수

| 이름 | 용도 | 기본값 |
|---|---|---|
| `ANYDOOR_DIR` | AnyDoor 폴더 위치 | `Desktop\AnyDoor` |
| `ANYDOOR_CKPT` | 합성 가중치 파일, 16비트 추론용 파일 지정 권장 | AnyDoor `configs/inference.yaml`의 원본 파일 |
| `MOA_RESTORE_ORIGINAL` | 서버의 원본 복원 후처리 켜기(1)·끄기(0) | `1` |
| `MOA_SEAM_FIX` | 서버의 박스 선 보정 켜기(1)·끄기(0) | `1` |

## 4. 필요 파일

- 준비: [README 7-2. 설치 5단계 AI 모델 코드 · 가중치 파일 다운로드](../../README.md#7-2-설치)

| 파일 | 종류 |
|---|---|
| AnyDoor 공식 저장소 폴더 | 실행 코드 |
| `epoch=1-step=8687.ckpt` (약 16.8GB) | AnyDoor 가중치 |
| `dinov2_vitg14_pretrain.pth` (약 4.5GB) | DINOv2 가중치, 학습용. 합성에서는 읽지 않음 |
| 16비트 추론용 가중치 약 4.9GB | 선택. `python scripts\convert_weights_fp16.py 원본.ckpt 새파일.ckpt`로 생성 후 `ANYDOOR_CKPT`에 지정 |

## 5. 성능 · RTX 3080 10GB

| 항목 | 기존 일괄 적재 | 부품 단위 적재 2026-10-21 | 16비트 가중치·전 부품 GPU 상주 2026-11-09 |
|---|---|---|---|
| 합성 1건, 50스텝 | 36.9~41.1초 | 24.4~25.4초 | 15.3~17.0초 |
| 모델 적재 · 예열 | 152.1초 | 100.8초 | 74.6초 |
| PyTorch 최대 할당 메모리 | 9.70GB | 8.25GB | 5.94GB |
| 공유 GPU 메모리 최대 사용량 | 3,199MB | 218MB | 84MB |

- 2026-10-21 비교 조건: 서버 종료 상태, 같은 입력과 seed, 상의 경계 보정 적용, 예열 → SAM2 추출 → 합성 2회
- 2026-11-09 비교 조건: 서버 종료 상태, SAM2 적재·추출 6회 → 예열 → 서로 다른 3쌍 합성, 16비트 추론용 파일 사용.
  같은 3쌍의 32비트 부품 단위 적재 결과 대비 평균 픽셀 차이 0.047~0.109/255
- 비교 표 전체: [README.md 6. 합성 속도 개선](../../README.md#구성-요소별-gpu-순차-적재--2026-10-21)

## 6. 단위 테스트

- [scripts/README.md](../../scripts/README.md)의 `test_compose.py`
