# 상의 영역 추출 모듈 (SAM2)

## 1. 개요

- 역할: 이미지에서 사용자가 지정한 좌표(포함 점, 제외 점, 사각형 영역)로 상의 영역을 분할
- 모델: SAM2.1 Hiera Base+ (Meta)
- 사용처: 백엔드 `routers/extract.py` ([api.md 4-1. 상의 영역 추출](../../docs/api.md#4-1-상의-영역-추출))

## 2. 함수

```python
from features.object_extraction import extract_object

mask = extract_object(image_rgb, points=[(x1, y1)], neg_points=[(x2, y2)], box=(x1, y1, x2, y2))
```

| 인자 | 형식 | 필수 | 설명 |
|---|---|---|---|
| `image_rgb` | `np.uint8` (H, W, 3) | O | RGB 이미지 |
| `points` | `[(x, y), ...]` | 조건 | 포함 점 (상의 위) |
| `neg_points` | `[(x, y), ...]` | - | 제외 점 |
| `box` | `(x1, y1, x2, y2)` | 조건 | 상의를 감싸는 사각형 영역 |
| `postprocess` | `bool` | - | 포함 점이 찍힌 영역만 남기고(점이 없으면 가장 큰 영역) 작은 구멍 채움 (기본 `True`) |

- 조건: `points`, `neg_points`, `box` 중 1개 이상
- 좌표: 원본 이미지 픽셀 기준 (0~1 비율 아님)
- 반환: `np.uint8` (H, W), 상의 영역 1·나머지 0
- 예외

| 예외 | 발생 조건 |
|---|---|
| `ValueError` | 좌표 없음, 좌표가 이미지 범위 밖 |
| `RuntimeError` | 지정 위치에서 상의 영역을 찾지 못함 (빈 결과) |

- 모델은 첫 호출 시 1회 로딩 후 재사용

## 3. 환경 변수

| 이름 | 용도 | 기본값 |
|---|---|---|
| `SAM2_CHECKPOINT` | 모델 가중치 파일 경로 | `checkpoints/sam2/sam2.1_hiera_base_plus.pt` |
| `SAM2_CONFIG` | 모델 설정 파일 | `configs/sam2.1/sam2.1_hiera_b+.yaml` |
| `SAM2_DEVICE` | 실행 장치 | 자동 (GPU 우선) |

- 모델 가중치 파일 준비: [environment.md 2. 설치 순서](../../docs/environment.md#2-설치-순서) 6단계

## 4. 단위 테스트

- [scripts/README.md](../../scripts/README.md)의 `test_object_extraction.py`
