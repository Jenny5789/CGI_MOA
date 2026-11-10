"""재학습 가중치용 입력 구성: 팀 재학습 학습 재료와 같은 형식으로 AnyDoor 입력을 만든다.

- 배경: 재학습 가중치 aug·mix는 scripts/retrain/retrain_dataset.py 형식으로 학습됨
  - 생성 영역 안만 검게 비우고 생성 영역 밖 몸은 원본 유지
  - 옷 윤곽선 지도를 옷 사진 비율 그대로, 어깨 너비 기준 크기로 목 아래에 배치
  원래 AnyDoor 형식으로 넣으면 학습 때 본 적 없는 입력이 되어 2026-11-10 비교에서 공식 가중치보다 불리했다
- 11/10 시험 결과: mix35000 같은 8건에서 실루엣 일치도 0.912 → 0.804, 셔츠 색 차이 8.21 → 13.53으로 기존 입력보다 불리,
  7건 중 2건 깨짐. 학습 생성 영역은 VITON-HD agnostic 마스크 모양이고 앱 합성 영역은 사용자가 칠한 모양이라 생긴 차이로 추정.
  배포는 ANYDOOR_INPUT=anydoor, 이 형식은 합성 영역을 학습 생성 영역 모양으로 만드는 단계가 생기면 다시 시험
- inference_item·placed_hint·body_width·server_crop: retrain_dataset.py의 같은 이름 함수를 그대로 옮김.
  AnyDoor data_utils 함수는 anydoor_composer가 불러온 run_inference.py 이름 공간에서 받음
- 관절 점: 학습·평가는 VITON-HD OpenPose 값을 썼고 앱 사진에는 없음. 새 모델 없이 SAM2 사람 영역으로 계산
  - 어깨: 몸 윤곽 양쪽 끝선이 목에서 바깥으로 벌어지다 팔을 따라 수직에 가깝게 꺾이는 지점, 좌우 높이는 가운데로 맞춤
  - 목: OpenPose 정의와 같이 두 어깨의 가운데
  - 11/10 사람 6명 사진에서 위치 육안 확인, 결과 품질은 공식 대 재학습 합성 비교로 검증
"""
import cv2
import numpy as np

KP_NECK, KP_RSH, KP_LSH = 1, 2, 5  # OpenPose BODY_25 목, 오른쪽 어깨, 왼쪽 어깨
K_A, OFF = 0.93, -0.25  # 옷 그림 크기·위치 기준, retrain_dataset.py와 같은 값
SERVER_CROP = 1.3  # 다시 그릴 정사각형 배율, anydoor_composer CROP_RATIO와 같음
KNEE_SLOPE, KNEE_RUN = 0.6, 12  # 어깨 꺾임: 끝선 기울기가 이 값보다 작아지는 첫 지점, 평균 구간 줄 수
JOINT_INSET = 0.07  # 어깨 관절: 실루엣 끝에서 몸 폭의 이 비율만큼 안쪽


# ---------- 관절 점 ----------

def _edges(mask, cx):
    """줄마다 몸 가운데 cx와 이어진 부분의 왼쪽·오른쪽 끝, 없으면 nan"""
    h, w = mask.shape
    left, right = np.full(h, np.nan), np.full(h, np.nan)
    for y in range(h):
        row = mask[y]
        on = np.flatnonzero(row)
        if on.size == 0:
            continue
        j = cx if row[cx] else on[np.argmin(np.abs(on - cx))]
        if abs(j - cx) > 0.05 * w:
            continue
        l = j
        while l > 0 and row[l - 1]:
            l -= 1
        r = j
        while r < w - 1 and row[r + 1]:
            r += 1
        left[y], right[y] = l, r
    return left, right


def _smooth(v, k=9):
    v = v.copy()
    ok = ~np.isnan(v)
    if not ok.any():
        return np.zeros_like(v)
    v[~ok] = np.interp(np.flatnonzero(~ok), np.flatnonzero(ok), v[ok])
    return np.convolve(np.pad(v, k // 2, mode="edge"), np.ones(k) / k, mode="valid")


def _knee(edge, y0, y1, outward, min_shift):
    """y0~y1에서 끝선이 바깥으로 min_shift 이상 벌어진 뒤 기울기가 KNEE_SLOPE보다 작아지는 첫 줄, 없으면 None"""
    base = edge[y0]
    for y in range(y0, y1 - KNEE_RUN):
        moved = (base - edge[y]) if outward < 0 else (edge[y] - base)
        if moved >= min_shift and np.abs(np.diff(edge[y:y + KNEE_RUN])).mean() < KNEE_SLOPE:
            return y
    return None


def estimate_keypoints(person):
    """사람 영역 0/1 → OpenPose BODY_25 형식 (25, 3), 목·좌우 어깨만 채움. 계산 실패 시 None"""
    m = person.astype(bool)
    ys, xs = np.where(m)
    if ys.size == 0:
        return None
    top, bot = ys.min(), ys.max()
    hp = bot - top
    cx = int(np.median(xs[ys < top + 0.15 * hp]))
    left, right = _edges(m, cx)
    ls, rs = _smooth(left), _smooth(right)
    y0, y1 = top + int(0.06 * hp), top + int(0.45 * hp)
    head = np.nanmax((right - left)[top + int(0.02 * hp): top + int(0.08 * hp)])
    yl = _knee(ls, y0, y1, -1, 0.35 * head)
    yr = _knee(rs, y0, y1, +1, 0.35 * head)
    if yl is None or yr is None:
        return None
    y = int(round((yl + yr) / 2))  # 머리카락이 한쪽 어깨를 덮어도 좌우 높이를 맞춤
    width = rs[y] - ls[y]
    p = np.zeros((25, 3), np.float32)
    p[KP_RSH] = (ls[y] + JOINT_INSET * width, y, 1)  # 오른쪽 어깨: 사진 왼쪽
    p[KP_LSH] = (rs[y] - JOINT_INSET * width, y, 1)  # 왼쪽 어깨: 사진 오른쪽
    p[KP_NECK] = ((p[KP_RSH, 0] + p[KP_LSH, 0]) / 2, y, 1)
    return p


# ---------- 입력 구성: retrain_dataset.py와 같은 계산 ----------

def body_width(cmask, du):
    """옷 사진 몸통 너비: 옷 높이 40~90% 구간에서 옷 가운데와 이어진 부분 너비의 중앙값"""
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


class _NS:
    """run_inference.py 이름 공간 dict를 du.함수 형태로 쓰기 위한 감싸개"""

    def __init__(self, ns):
        self._ns = ns

    def __getattr__(self, name):
        return self._ns[name]


def placed_hint(cloth, cmask, p, h, w, du):
    """옷 윤곽선 지도를 옷 사진 비율 그대로 어깨 기준으로 놓은 (h, w) 지도와 옷 모양"""
    s = float(np.linalg.norm(p[KP_LSH, :2] - p[KP_RSH, :2]))
    cy1, cy2, cx1, cx2 = du.get_bbox_from_mask(cmask)
    m3 = np.stack([cmask] * 3, -1)
    gar = (cloth * m3 + 255 * (1 - m3))[cy1:cy2, cx1:cx2].astype(np.uint8)
    hint = du.sobel(gar, cmask[cy1:cy2, cx1:cx2].astype(np.float32))
    sc = K_A * s / body_width(cmask, du)
    gh, gw = max(int(sc * (cy2 - cy1)), 2), max(int(sc * (cx2 - cx1)), 2)
    y0, x0 = int(p[KP_NECK, 1] + OFF * s), int(p[KP_NECK, 0] - gw / 2)
    big = np.zeros((h, w, 3), np.uint8)
    sil = np.zeros((h, w), np.uint8)
    hi = cv2.resize(hint, (gw, gh))
    sm = cv2.resize(cmask[cy1:cy2, cx1:cx2], (gw, gh), interpolation=cv2.INTER_NEAREST)
    ty1, tx1, ty2, tx2 = max(0, y0), max(0, x0), min(h, y0 + gh), min(w, x0 + gw)
    if ty2 > ty1 and tx2 > tx1:
        big[ty1:ty2, tx1:tx2] = hi[ty1 - y0:ty2 - y0, tx1 - x0:tx2 - x0]
        sil[ty1:ty2, tx1:tx2] = sm[ty1 - y0:ty2 - y0, tx1 - x0:tx2 - x0]
    return big, sil


def server_crop(tar_image, tar_mask, du, ratio=SERVER_CROP):
    """AnyDoor가 다시 그리는 정사각형: 생성 영역 박스를 ratio배로 키운 뒤 정사각형으로"""
    h, w = tar_mask.shape
    by1, by2, bx1, bx2 = du.get_bbox_from_mask(tar_mask)
    yc, xc, bh, bw = 0.5 * (by1 + by2), 0.5 * (bx1 + bx2), ratio * (by2 - by1 + 1), ratio * (bx2 - bx1 + 1)
    return tuple(int(v) for v in du.box2squre(tar_image, (max(0, int(yc - bh / 2)), min(h, int(yc + bh / 2)),
                                                          max(0, int(xc - bw / 2)), min(w, int(xc + bw / 2)))))


def inference_item(ref_image, ref_mask, tar_image, tar_mask, p, ns, ratio=SERVER_CROP):
    """AnyDoor process_pairs 대신 쓰는 입력. 출력 키는 run_inference.py와 같음
    ns: anydoor_composer가 불러온 run_inference.py 이름 공간"""
    du = _NS(ns)
    y1, y2, x1, x2 = du.get_bbox_from_mask(ref_mask)
    m3 = np.stack([ref_mask] * 3, -1)
    ref = (ref_image * m3 + 255 * (1 - m3))[y1:y2, x1:x2]
    ref, _ = du.expand_image_mask(ref, ref_mask[y1:y2, x1:x2], ratio=1.2)
    ref = cv2.resize(du.pad_to_square(ref, 255).astype(np.uint8), (224, 224))
    h, w = tar_mask.shape
    crop = server_crop(tar_image, tar_mask, du, ratio)
    hint_big, sil = placed_hint(ref_image, ref_mask, p, h, w, du)
    collage = tar_image.copy()
    collage[tar_mask > 0] = 0
    collage[sil > 0] = hint_big[sil > 0]
    cy1, cy2, cx1, cx2 = crop
    tgt = du.pad_to_square(tar_image[cy1:cy2, cx1:cx2], pad_value=0).astype(np.uint8)
    col = du.pad_to_square(collage[cy1:cy2, cx1:cx2], pad_value=0).astype(np.uint8)
    cm = du.pad_to_square(np.stack([tar_mask[cy1:cy2, cx1:cx2]] * 3, -1).astype(np.uint8), pad_value=2).astype(np.uint8)
    h2, w2 = col.shape[:2]
    tgt = cv2.resize(tgt, (512, 512)).astype(np.float32)
    col = cv2.resize(col, (512, 512)).astype(np.float32)
    cm = cv2.resize(cm, (512, 512), interpolation=cv2.INTER_NEAREST).astype(np.float32)
    cm[cm == 2] = -1
    return dict(ref=ref.astype(np.float32) / 255, jpg=tgt / 127.5 - 1.0, hint=np.concatenate([col / 127.5 - 1.0, cm[:, :, :1]], -1),
                extra_sizes=np.array([cy2 - cy1, cx2 - cx1, h2, w2]), tar_box_yyxx_crop=np.array(crop))
