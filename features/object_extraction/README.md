# 상의 추출 (SAM2)

## 호출

```python
from features.object_extraction import extract_object

mask = extract_object(
    image_rgb,                      # np.uint8, RGB, (H, W, 3)
    points=[(x1, y1), (x2, y2)],    # 포함 점 (원본 픽셀 좌표)
    neg_points=[(x3, y3)],          # 제외 점 (선택)
    box=(x1, y1, x2, y2),           # 박스 (선택)
)
# mask: np.uint8, 0/1, 입력과 같은 크기
```

- `points`, `box` 중 하나 이상 필요
- 좌표: 원본 이미지 픽셀 기준
- 빈 마스크면 `RuntimeError`

## 설정

| 환경변수 | 기본값 |
|---|---|
| `SAM2_CHECKPOINT` | `checkpoints/sam2/sam2.1_hiera_base_plus.pt` |
| `SAM2_CONFIG` | `configs/sam2.1/sam2.1_hiera_b+.yaml` |
| `SAM2_DEVICE` | 자동 (cuda 우선) |

- 체크포인트는 저장소에 없음 (AI 기능·서버 담당에게 받기)

## 시험

- [../../scripts/README.md](../../scripts/README.md) `test_object_extraction.py`
