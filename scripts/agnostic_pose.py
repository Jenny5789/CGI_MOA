"""관절 점으로 상체·팔 영역(agnostic-mask)을 그리는 함수. VITON-HD 마스크를 쉐이프리스에서 재현하려고 씀

HR-VITON 계열 공개 코드의 agnostic 생성 방식(어깨·팔·몸통·목을 어깨 너비 비례 굵기로 칠함)을 따름.
VITON-HD 학습용 사진에 적용해 제공된 agnostic-mask 와 겹치는 정도(IoU)로 검증한 뒤 쓴다 (calibrate 함수)
p: OpenPose BODY_25 (25, 3). 쓰는 점: 1 목, 2·3·4 오른쪽 어깨·팔꿈치·손목, 5·6·7 왼쪽, 9 오른쪽 골반, 12 왼쪽 골반
"""
import numpy as np
from PIL import Image, ImageDraw


def pose_region(p, H, W):
    pd = p[:, :2].astype(np.float64).copy()
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    la = np.linalg.norm(pd[5] - pd[2])
    lb = np.linalg.norm(pd[12] - pd[9])
    if lb > 0:  # 골반 폭을 어깨 폭에 맞춰 넓힘
        c = (pd[9] + pd[12]) / 2
        pd[9] = c + (pd[9] - c) / lb * la
        pd[12] = c + (pd[12] - c) / lb * la
    r = int(la / 16) + 1

    def t(i):
        return tuple(pd[i])

    def dot(i, rx, ry):
        x, y = pd[i]
        d.ellipse((x - rx, y - ry, x + rx, y + ry), fill=255)

    d.line([t(2), t(5)], fill=255, width=r * 10)
    for i in (2, 5):
        dot(i, r * 5, r * 5)
    for i in (3, 4, 6, 7):  # 팔 (점이 없으면 건너뜀)
        if not p[i - 1, 2] > 0 or not p[i, 2] > 0:
            continue
        d.line([t(i - 1), t(i)], fill=255, width=r * 10)
        dot(i, r * 5, r * 5)
    if p[9, 2] > 0 and p[12, 2] > 0:  # 몸통
        for i in (9, 12):
            dot(i, r * 3, r * 6)
        d.line([t(2), t(9)], fill=255, width=r * 6)
        d.line([t(5), t(12)], fill=255, width=r * 6)
        d.line([t(9), t(12)], fill=255, width=r * 12)
        d.polygon([t(2), t(5), t(12), t(9)], fill=255)
    x, y = pd[1]  # 목
    d.rectangle((x - r * 7, y - r * 7, x + r * 7, y + r * 7), fill=255)
    return np.array(img) > 0


def agnostic(p, H, W, keep_out, must_in):
    """관절 점 영역에서 머리·하체(keep_out)를 빼고, 상의·팔(must_in)은 반드시 포함"""
    return (pose_region(p, H, W) & ~keep_out) | must_in


def calibrate(viton_root, n=300, seed=0):
    """VITON-HD 학습용 n장에서 재현 마스크와 제공 마스크의 IoU (부위 번호: 5 상의, 14·15 팔, 4·13 얼굴, 9·12·16~19 하체)"""
    import json
    import os

    import cv2

    rng = np.random.default_rng(seed)
    ids = sorted(f[:-4] for f in os.listdir(f"{viton_root}/image"))
    out = {"pose": [], "pose+top+arms": []}
    for i in rng.choice(ids, n, replace=False):
        gt = cv2.imread(f"{viton_root}/agnostic-mask/{i}_mask.png", cv2.IMREAD_GRAYSCALE) > 127
        parse = np.array(Image.open(f"{viton_root}/image-parse-v3/{i}.png"))
        p = np.array(json.load(open(f"{viton_root}/openpose_json/{i}_keypoints.json"))["people"][0]["pose_keypoints_2d"]).reshape(-1, 3)
        H, W = gt.shape
        head = np.isin(parse, (4, 13))
        lower = np.isin(parse, (9, 12, 16, 17, 18, 19))
        top_arms = np.isin(parse, (5, 14, 15))
        for k, m in (("pose", pose_region(p, H, W) & ~head & ~lower), ("pose+top+arms", agnostic(p, H, W, head | lower, top_arms))):
            out[k].append((m & gt).sum() / max((m | gt).sum(), 1))
    return {k: [round(float(np.percentile(v, q)), 3) for q in (10, 25, 50, 75)] for k, v in out.items()}


if __name__ == "__main__":
    import sys
    print("IoU 10/25/50/75%:", calibrate(sys.argv[1] if len(sys.argv) > 1 else r"C:\CGI_MOA\Dataset\TryOn\VitonHD\train"))
