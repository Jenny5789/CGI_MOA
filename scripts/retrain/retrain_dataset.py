"""AnyDoor 재학습 학습 재료 (VITON-HD, 생성 영역 넓힘 + 조건 이미지 어깨 기준 배치).

원래 AnyDoor 학습 재료(datasets/vitonhd.py + datasets/base.py process_pairs)와 다른 점
- 생성 영역: 상의 라벨(image-parse-v3 5번) 박스 → agnostic-mask(상체 옷 + 팔) 모양 그대로
- 조건 이미지: 생성 영역 박스에 맞춰 늘림 → 옷 사진 비율 그대로,
  크기 = 어깨 너비 × K_A ÷ 옷 사진 몸통 너비, 위치 = 목에서 어깨 너비 × OFF 아래부터 (VITON-HD 관절 점)
- 생성 영역 안은 0(검정)으로 비우고 조건 이미지만 놓음, 좌우 뒤집기 증강 없음
- 거르기: 부위 지도 오류(상의 영역 < 상체+팔의 25%), 옷 마스크 오류(마스크 범위 ÷ 윤곽선 범위 < 0.6), 관절 점 없음
같은 점: 참조 이미지 처리, 크롭 정사각형 → 512, 출력 키(ref, jpg, hint, time_steps)

경로 (환경 변수)
- ANYDOOR_DIR: AnyDoor 공식 코드 폴더 (datasets/data_utils.py 사용). 기본 $HOME/Desktop/AnyDoor
- VITON_TRAIN_DIR: VITON-HD 학습용 폴더 (image, cloth, ...). 기본 $ANYDOOR_DIR/data/zalando-hd-resized/train
"""
import importlib.util
import json
import os
from pathlib import Path

import cv2
import numpy as np
from torch.utils.data import Dataset

AD = Path(os.environ.get("ANYDOOR_DIR", Path.home() / "Desktop" / "AnyDoor"))
VI = Path(os.environ.get("VITON_TRAIN_DIR", AD / "data" / "zalando-hd-resized" / "train"))
_spec = importlib.util.spec_from_file_location("anydoor_data_utils", AD / "datasets" / "data_utils.py")
du = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(du)

UPPER, MIN_TOP, MASK_RATIO = 5, 0.25, 0.6
KP_NECK, KP_RSH, KP_LSH, KP_HIP = 1, 2, 5, 8  # OpenPose BODY_25 목, 오른쪽 어깨, 왼쪽 어깨, 골반 가운데
K_A, OFF = 0.93, -0.25  # 옷 그림 크기·위치 기준 (어깨 너비 단위, 학습용 300쌍 중앙값)
CROP = (13, 20)  # 크롭 배율 1.3~1.9 (np.random.randint 범위 / 10, 서버 합성은 1.3)


def read(i, root=None):
    root = Path(root or VI)
    image = cv2.cvtColor(cv2.imread(str(root / "image" / f"{i}.jpg")), cv2.COLOR_BGR2RGB)
    cloth = cv2.cvtColor(cv2.imread(str(root / "cloth" / f"{i}.jpg")), cv2.COLOR_BGR2RGB)
    cmask = (cv2.imread(str(root / "cloth-mask" / f"{i}.jpg"), cv2.IMREAD_GRAYSCALE) > 127).astype(np.uint8)
    parse = cv2.imread(str(root / "image-parse-v3" / f"{i}.png"), cv2.IMREAD_UNCHANGED)
    if parse.ndim == 3:  # 팔레트 PNG가 컬러로 읽히는 경우 대비
        from PIL import Image
        parse = np.array(Image.open(root / "image-parse-v3" / f"{i}.png"))
    top = (parse == UPPER).astype(np.uint8)
    ag = (cv2.imread(str(root / "agnostic-mask" / f"{i}_mask.png"), cv2.IMREAD_GRAYSCALE) > 127).astype(np.uint8)
    k = json.loads((root / "openpose_json" / f"{i}_keypoints.json").read_text())
    p = np.array(k["people"][0]["pose_keypoints_2d"], np.float32).reshape(-1, 3)
    return image, cloth, cmask, top, ag, p


def mask_ok(cloth, cmask):
    """옷 마스크 오류 거르기: 마스크 범위 ÷ 윤곽선(Canny) 범위 ≥ 0.6"""
    e = cv2.Canny(cv2.cvtColor(cloth, cv2.COLOR_RGB2GRAY), 20, 60)
    e[:8], e[-8:], e[:, :8], e[:, -8:] = 0, 0, 0, 0
    ys, xs = np.nonzero(e)
    if ys.size < 200 or cmask.sum() < 10:
        return False
    ey1, ey2 = np.percentile(ys, [0.5, 99.5])
    ex1, ex2 = np.percentile(xs, [0.5, 99.5])
    my1, my2, mx1, mx2 = du.get_bbox_from_mask(cmask)
    return (my2 - my1) * (mx2 - mx1) / max((ey2 - ey1) * (ex2 - ex1), 1) >= MASK_RATIO


def usable(i):
    """학습에 쓸 수 있는 쌍인지와 옷 아랫단 위치(목 = 0, 골반 = 1)"""
    try:
        image, cloth, cmask, top, ag, p = read(i)
    except (AttributeError, FileNotFoundError, IndexError, KeyError, ValueError, cv2.error):
        return False, None
    if top.sum() < 1000 or ag.sum() < 1000 or cmask.sum() < 1000 or (p[[KP_NECK, KP_RSH, KP_LSH, KP_HIP], 2] < 0.1).any():
        return False, None
    if top.sum() / ag.sum() < MIN_TOP or not mask_ok(cloth, cmask):
        return False, None
    _, yb, _, _ = du.get_bbox_from_mask(top)
    return True, float((yb - p[KP_NECK, 1]) / max(p[KP_HIP, 1] - p[KP_NECK, 1], 1))


def body_width(cmask):
    """옷 사진 몸통 너비: 옷 높이 40~90% 구간에서 옷 가운데와 이어진 부분 너비의 중앙값 (떨어진 소매 제외)"""
    y1, y2, x1, x2 = du.get_bbox_from_mask(cmask)
    c = (x1 + x2) // 2
    out = []
    for row in cmask[y1 + int(0.4 * (y2 - y1)): y1 + int(0.9 * (y2 - y1))]:
        on = np.flatnonzero(row)
        if on.size == 0:
            continue
        j = on[np.argmin(np.abs(on - c))]
        if abs(j - c) > 0.05 * (x2 - x1):
            continue
        l = j
        while l > 0 and row[l - 1]:
            l -= 1
        r = j
        while r < len(row) - 1 and row[r + 1]:
            r += 1
        out.append(r - l + 1)
    return float(np.median(out)) if out else float((x2 - x1) * 0.6)


def placed_hint(cloth, cmask, p, H, W):
    """조건 이미지(옷 사진 고주파 지도)를 옷 사진 비율 그대로 어깨 기준으로 놓은 (H, W) 지도와 옷 모양"""
    S = float(np.linalg.norm(p[KP_LSH, :2] - p[KP_RSH, :2]))
    cy1, cy2, cx1, cx2 = du.get_bbox_from_mask(cmask)
    m3 = np.stack([cmask] * 3, -1)
    gar = (cloth * m3 + 255 * (1 - m3))[cy1:cy2, cx1:cx2].astype(np.uint8)
    hint = du.sobel(gar, cmask[cy1:cy2, cx1:cx2].astype(np.float32))
    sc = K_A * S / body_width(cmask)
    gh, gw = max(int(sc * (cy2 - cy1)), 2), max(int(sc * (cx2 - cx1)), 2)
    y0, x0 = int(p[KP_NECK, 1] + OFF * S), int(p[KP_NECK, 0] - gw / 2)
    big = np.zeros((H, W, 3), np.uint8)
    sil = np.zeros((H, W), np.uint8)
    hi = cv2.resize(hint, (gw, gh))
    sm = cv2.resize(cmask[cy1:cy2, cx1:cx2], (gw, gh), interpolation=cv2.INTER_NEAREST)
    ty1, tx1, ty2, tx2 = max(0, y0), max(0, x0), min(H, y0 + gh), min(W, x0 + gw)
    if ty2 > ty1 and tx2 > tx1:
        big[ty1:ty2, tx1:tx2] = hi[ty1 - y0:ty2 - y0, tx1 - x0:tx2 - x0]
        sil[ty1:ty2, tx1:tx2] = sm[ty1 - y0:ty2 - y0, tx1 - x0:tx2 - x0]
    return big, sil


def make_item(i, rng=np.random):
    image, cloth, cmask, top, ag, p = read(i)
    H, W = ag.shape
    # 참조 이미지 (process_pairs와 같은 처리, 좌우 뒤집기 없음)
    y1, y2, x1, x2 = du.get_bbox_from_mask(cmask)
    m3 = np.stack([cmask] * 3, -1)
    ref = (cloth * m3 + 255 * (1 - m3))[y1:y2, x1:x2]
    ref, _ = du.expand_image_mask(ref, cmask[y1:y2, x1:x2], ratio=rng.randint(11, 15) / 10)
    ref = cv2.resize(du.pad_to_square(ref, 255).astype(np.uint8), (224, 224))
    # 정답·조건 이미지
    box = du.get_bbox_from_mask(ag)
    crop = du.box2squre(image, du.expand_bbox(image, box, ratio=[CROP[0] / 10, CROP[1] / 10]))
    hint_big, sil = placed_hint(cloth, cmask, p, H, W)
    collage = image.copy()
    collage[ag > 0] = 0  # 생성 영역 안은 비움
    collage[sil > 0] = hint_big[sil > 0]
    cy1, cy2, cx1, cx2 = crop
    tgt = du.pad_to_square(image[cy1:cy2, cx1:cx2], pad_value=0).astype(np.uint8)
    col = du.pad_to_square(collage[cy1:cy2, cx1:cx2], pad_value=0).astype(np.uint8)
    cm = du.pad_to_square(np.stack([ag[cy1:cy2, cx1:cx2]] * 3, -1).astype(np.uint8), pad_value=2).astype(np.uint8)
    H2, W2 = col.shape[:2]
    tgt = cv2.resize(tgt, (512, 512)).astype(np.float32)
    col = cv2.resize(col, (512, 512)).astype(np.float32)
    cm = cv2.resize(cm, (512, 512), interpolation=cv2.INTER_NEAREST).astype(np.float32)
    cm[cm == 2] = -1  # 정사각형으로 채운 빈칸
    return dict(ref=ref.astype(np.float32) / 255, jpg=tgt / 127.5 - 1.0,
                hint=np.concatenate([col / 127.5 - 1.0, cm[:, :, :1]], -1),
                extra_sizes=np.array([cy2 - cy1, cx2 - cx1, H2, W2]), tar_box_yyxx_crop=np.array(crop))


class VitonHDWide(Dataset):
    """ids의 쌍을 돌려 가며 학습 재료를 만든다 (length로 한 바퀴 길이 지정)"""

    def __init__(self, ids, length=None):
        self.ids = list(ids)
        self.length = length or len(self.ids)

    def __len__(self):
        return self.length

    def __getitem__(self, idx):
        item = make_item(self.ids[idx % len(self.ids)])
        item["time_steps"] = np.array([np.random.randint(0, 1000)])  # base.py sample_timestep (VITON-HD 설정)과 같은 분포
        return item
