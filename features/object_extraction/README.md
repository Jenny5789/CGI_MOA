# 객체 추출 (SAM2)

## 호출 방법

```python
from features.object_extraction import extract_object

mask = extract_object(
    image_rgb,                      # np.uint8, RGB, (H, W, 3)
    points=[(x1, y1), (x2, y2)],    # 객체 위 positive point (원본 픽셀 좌표)
    neg_points=[(x3, y3)],          # 제외할 곳 (선택)
    box=(x1, y1, x2, y2),           # 박스 (선택)
)
# mask: np.uint8, 0/1, (H, W) — 입력 이미지와 같은 크기
```

- `points`, `neg_points`, `box` 중 하나 이상 필요
- 좌표는 화면 좌표가 아니라 **원본 이미지 픽셀 좌표**
- 빈 마스크가 나오면 `RuntimeError`

## 설정

| 환경변수 | 기본값 |
|---|---|
| `SAM2_CHECKPOINT` | `checkpoints/sam2/sam2.1_hiera_base_plus.pt` |
| `SAM2_CONFIG` | `configs/sam2.1/sam2.1_hiera_b+.yaml` |
| `SAM2_DEVICE` | 자동 (cuda 우선) |

체크포인트는 저장소에 올리지 않는다.

## 테스트 (UI 없이)

```
python scripts/test_object_extraction.py 이미지경로 --points "487,731;483,443" --out mask.png
```
