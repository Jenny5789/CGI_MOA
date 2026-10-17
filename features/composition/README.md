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

- 반환: `np.uint8` (H, W, 3) RGB, 인물 이미지와 같은 크기
- `ref_mask`: 상의 영역 추출 모듈(`extract_object`) 결과를 그대로 사용
- `tar_mask`: 영역을 감싸는 사각형만 사용 (칠한 모양은 결과에 영향 적음)
- 다시 그리는 범위: `tar_mask` 사각형(1.1배)을 다시 1.3배 넓힌 정사각형 (AnyDoor 기본 1.5~2.9배 무작위 대신 고정, `AnyDoorComposer(crop_ratio=...)`로 변경)
- `warmup()`: 모델 로딩 + 2스텝 시험 합성 (백엔드 시작 시 자동 실행)
- 모델은 첫 호출 시 1회 로딩 후 재사용
- 계산 방식: float16, save_memory (화질 차이 없음, 2026-10-11 확인)

### 원본 복원 후처리 (`restore.py`)

```python
from features.composition import find_garment, restore_original

garment = find_garment(result, tar_mask)                       # 합성 결과의 새 상의 영역 (SAM2), 실패 시 None
final = restore_original(tar_rgb, result, tar_mask, garment)   # RGB uint8, 인물 이미지와 같은 크기
```

- 착용 영역 상단 경계(세로줄마다 착용 영역 최상단을 이은 선) 위 = 원본, 아래 = 합성 결과 (블렌딩 폭 20px)
- 새 상의 영역은 경계 위라도 합성 결과 유지 (어깨 끝 잘림 방지)
- `find_garment`: 착용 영역을 감싼 박스를 프롬프트로 SAM2 실행, 착용 영역 대비 0.3~2배 밖이면 `None` (상단 경계만으로 복원)
- 서버: `backend/routers/compose.py`가 합성 직후 적용

## 3. 환경 변수

| 이름 | 용도 | 기본값 |
|---|---|---|
| `ANYDOOR_DIR` | AnyDoor 폴더 위치 | `Desktop\AnyDoor` |
| `MOA_RESTORE_ORIGINAL` | 서버의 원본 복원 후처리 켜기(1)·끄기(0) | `1` |

## 4. 필요 파일

- 준비: [environment.md 2. 설치 순서](../../docs/environment.md#2-설치-순서) 6단계

| 파일 | 종류 |
|---|---|
| AnyDoor 공식 저장소 폴더 | 실행 코드 |
| `epoch=1-step=8687.ckpt` (약 16.8GB) | AnyDoor 가중치 |
| `dinov2_vitg14_pretrain.pth` (약 4.5GB) | DINOv2 가중치 |

## 5. 성능 (RTX 3080 10GB, 2026-10-13 확인)

| 항목 | 값 |
|---|---|
| 합성 1건 (50스텝) | 약 1분 |
| 모델 로딩 | 1~2분 (백엔드 시작 시) |
| 최대 GPU 메모리 | 9.25GB |

## 6. 단위 테스트

- [scripts/README.md](../../scripts/README.md)의 `test_compose.py`
