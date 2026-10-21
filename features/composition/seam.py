"""박스 선 보정 (개선 포아송): AnyDoor가 다시 그린 정사각형(크롭 영역)을 원본에 붙인 테두리에 생기는 선을 없앤다.

- 원인: 다시 그린 정사각형의 배경 밝기·색이 원본과 조금 달라, 붙인 자리 테두리가 선으로 보임
  (AnyDoor crop_back은 크롭 영역에서 테두리 5px를 뺀 범위를 붙임)
- 방법: 테두리를 따라 "원본 - 합성 결과" 색 차이를 재고, 튀는 값(원본과 내용이 다른 곳)은 버리고 옆 값으로 채운 뒤,
  둘레를 따라 부드럽게 해서 네모 안쪽으로 부드럽게 이어 보정 (Coons 보간)
  - OpenCV seamlessClone(기존 포아송)은 테두리 전체를 맞춰, 테두리에 원본과 다른 것이 걸치면 안쪽으로 번짐
- 시험: CGI_MOA 작업일지 10/21 ②·③ (100장 박스 선 세기 평균 2.49 → 0.57, 기존 포아송의 하얀 빛 번짐 없음)
"""
import numpy as np

MARGIN = 5      # AnyDoor crop_back이 붙일 때 빼는 테두리 (run_inference.py crop_back의 m)
K_OUT = 25      # 테두리 색 차이(밝기)가 가운데값에서 이만큼 넘게 벗어나면 튀는 값으로 보고 제외
WIN = 41        # 둘레를 따라 부드럽게 하는 폭 (px)
MIN_OK = 0.2    # 정상 테두리가 이 비율보다 적으면 보정하지 않음
LUM = np.array([0.299, 0.587, 0.114], np.float32)


def fix_seam(person, result, crop_box, margin=MARGIN):
    """박스 선 보정 결과(RGB uint8)를 돌려준다. 보정할 수 없으면 합성 결과 그대로.

    person  : np.uint8 (H, W, 3) 원본 인물 사진
    result  : np.uint8 (H, W, 3) AnyDoor 합성 결과 (person과 같은 크기)
    crop_box: (위, 아래, 왼쪽, 오른쪽) AnyDoor 크롭 영역 (anydoor_composer.last_crop_box), None이면 보정 안 함
    """
    if crop_box is None:
        return result
    H, W = result.shape[:2]
    y1, y2, x1, x2 = crop_box
    y1, y2, x1, x2 = max(y1 + margin, 0), min(y2 - margin, H), max(x1 + margin, 0), min(x2 - margin, W)  # 실제로 붙인 범위
    h, w = y2 - y1, x2 - x1
    if h < 3 or w < 3:
        return result

    res = result[y1:y2, x1:x2].astype(np.float32)
    org = person[y1:y2, x1:x2].astype(np.float32)
    # 둘레 좌표 (시계 방향: 위 → 오른쪽 → 아래 → 왼쪽)
    ys = np.r_[np.zeros(w, int), np.arange(1, h), np.full(w - 1, h - 1), np.arange(h - 2, 0, -1)]
    xs = np.r_[np.arange(w), np.full(h - 1, w - 1), np.arange(w - 2, -1, -1), np.zeros(h - 2, int)]
    d = org[ys, xs] - res[ys, xs]  # 테두리의 "원본 - 합성 결과" 색 차이
    dl = d @ LUM
    ok = np.abs(dl - np.median(dl)) <= K_OUT  # 튀는 값 제외
    if ok.mean() < MIN_OK:
        return result

    idx = np.arange(len(ys))
    for c in range(3):  # 제외한 곳은 양옆 정상 값으로 메움
        d[:, c] = np.interp(idx, idx[ok], d[ok, c], period=len(ys))
    win = min(WIN, len(ys))
    pad = np.r_[d[-win:], d, d[:win]]  # 둘레는 고리 모양이라 앞뒤를 이어 붙여 부드럽게
    kern = np.ones(win, np.float32) / win
    d = np.stack([np.convolve(pad[:, c], kern, mode="same")[win:-win] for c in range(3)], 1)

    B = np.zeros((h, w, 3), np.float32)
    B[ys, xs] = d
    s = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
    t = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    corner = (1 - s) * (1 - t) * B[0, 0] + s * (1 - t) * B[0, w - 1] + (1 - s) * t * B[h - 1, 0] + s * t * B[h - 1, w - 1]
    # 네 변의 보정 값을 안쪽으로 부드럽게 잇기 (Coons 보간)
    corr = (1 - t) * B[0][None] + t * B[h - 1][None] + (1 - s) * B[:, 0][:, None] + s * B[:, w - 1][:, None] - corner
    out = result.copy()
    out[y1:y2, x1:x2] = (res + corr).round().clip(0, 255).astype(np.uint8)
    return out
