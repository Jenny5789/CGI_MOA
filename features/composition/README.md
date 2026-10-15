# 상의 합성 (AnyDoor)

## 호출

```python
from features.composition import compose

result = compose(
    ref_rgb,          # 옷 사진. np.uint8, RGB, (H, W, 3)
    ref_mask,         # 옷 윤곽. np.uint8, 0/1, 옷 사진과 같은 크기
    tar_rgb,          # 인물 사진. np.uint8, RGB, (H, W, 3)
    tar_mask,         # 입힐 영역. np.uint8, 0/1, 인물 사진과 같은 크기
    seed=1234,        # 선택. 같으면 같은 결과
    on_progress=fn,   # 선택. 0~1 진행률
    steps=50,         # 선택. 스텝 수
)
# result: np.uint8, RGB, 인물 사진과 같은 크기
```

- 옷 윤곽: `extract_object` 결과 그대로
- 입힐 영역: 감싸는 사각형만 사용됨
- 모델은 첫 호출 때 한 번 불러와 재사용
- `warmup()`: 모델 불러오기 + 2스텝 합성 (서버 켤 때 자동)

## 설정

| 항목 | 값 |
|---|---|
| 스텝 수 | 50 |
| 계산 | float16 + save_memory |
| AnyDoor 위치 | 환경변수 `ANYDOOR_DIR` (기본 `Desktop\AnyDoor`) |

## 필요한 것 (저장소에 없음, AI 기능·서버 담당에게 받기)

- AnyDoor 공식 저장소 폴더 (`run_inference.py` 수정 없이 사용)
- 체크포인트 `epoch=1-step=8687.ckpt` (약 16.8GB), DINOv2 `dinov2_vitg14_pretrain.pth` (약 4.5GB)
- AnyDoor 폴더 `configs/inference.yaml`(`pretrained_model`), `configs/anydoor.yaml`(DINOv2 경로)에 파일 위치 지정

## 성능 (RTX 3080 10GB, 2026-10-13 확인)

| 항목 | 값 |
|---|---|
| 합성 1장 (50스텝) | 약 1분 |
| 모델 불러오기 | 1~2분 (서버 켤 때) |
| 최대 GPU 메모리 | 9.25GB |

## 시험

- [../../scripts/README.md](../../scripts/README.md) `test_compose.py`
