# 상의 합성 (AnyDoor)

## 호출 방법

```python
from features.composition import compose

result = compose(
    ref_rgb,          # 옷 사진. np.uint8, RGB, (H, W, 3)
    ref_mask,         # 옷 윤곽. np.uint8, 0/1, 옷 사진과 같은 크기
    tar_rgb,          # 인물 사진. np.uint8, RGB, (H, W, 3)
    tar_mask,         # 입힐 영역. np.uint8, 0/1, 인물 사진과 같은 크기
    seed=1234,        # 같은 seed면 같은 결과 (선택, 없으면 무작위)
    on_progress=fn,   # 0~1 진행률을 받는 함수 (선택, 스텝마다 호출)
    steps=50,         # 스텝 수 (선택, 기본 50)
)
# result: np.uint8, RGB, 인물 사진과 같은 크기
```

- 옷 윤곽은 `features.object_extraction`의 `extract_object` 결과를 그대로 사용
- 입힐 영역은 AnyDoor가 감싸는 사각형만 사용 (모양은 결과에 영향 적음)
- 첫 호출 때 모델을 한 번 불러오고 이후 재사용
- `warmup()`: 모델을 불러오고 2스텝 합성을 한 번 돌려 둔다 (서버가 켜질 때 자동 실행, 첫 사용자도 처음부터 빠름)

## 설정

| 항목 | 값 |
|---|---|
| 스텝 수 | 50 |
| 계산 방식 | float16 + save_memory (화질 차이 없음, 2026-10-11 확인) |
| 모델 파일 여는 곳 | 본체 RAM (`load_on_cpu=True`). 16.8GB 파일을 RAM에서 열고 가중치(약 9.2GB)만 GPU로 |
| AnyDoor 위치 | 환경변수 `ANYDOOR_DIR` (기본 `Desktop\AnyDoor`) |

## 필요한 것 (저장소에 없음)

- AnyDoor 공식 저장소 폴더 (`run_inference.py`를 수정 없이 불러와 사용)
- AnyDoor 체크포인트 `epoch=1-step=8687.ckpt` (약 16.8GB), DINOv2 `dinov2_vitg14_pretrain.pth` (약 4.5GB)
- AnyDoor 폴더의 `configs/inference.yaml`(`pretrained_model`), `configs/anydoor.yaml`(DINOv2 경로)에 각 파일 위치 지정
- 모델 파일은 AI 기능 담당에게 받기

## 성능 (RTX 3080 10GB, 2026-10-13 기준)

| 항목 | 값 |
|---|---|
| 1장 (모델이 올라가 있을 때, 50스텝) | 약 1분 (1스텝 약 0.9초) |
| 모델 불러오기 | 약 1~2분 (서버는 켜질 때 미리 해 둠) |
| 예열 (2스텝) | 약 20초 |
| 최대 GPU 메모리 (파이토치 기준) | 9.25GB |

- 10/13 이전(모델 파일을 GPU에서 열던 때): 1장 약 2분(1스텝 약 2초). 같은 사진·seed로 결과 그림은 완전히 같음

## 테스트 (서버·화면 없이)

```
python scripts/test_compose.py --garment 옷.jpg --garment-mask 옷윤곽.png --person 인물.jpg --area 입힐영역.png --out compose.jpg
```

- 옷 윤곽 만들기: `python scripts/test_object_extraction.py 옷.jpg --points "x,y" --out 옷윤곽.png`
