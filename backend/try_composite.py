# backend/try_composite.py
# 서버/DB/로그인 없이 합성 로직만 바로 돌려보는 개발용 도구.
# 사진 두 장을 주면 SAM 으로 객체를 뽑고, 배경에 올린 뒤,
# LAB 색이동 방식과 PCTNet 방식 결과를 나란히 저장한다.
#
# 사용 예:
#   python try_composite.py 객체.jpg 배경.jpg
#   python try_composite.py 객체.jpg 배경.jpg --point 640,900 --at 0.5,0.7 --scale 0.35
#
# --point  객체 사진에서 "이걸 가져와라" 하고 찍는 지점 (픽셀). 기본값은 사진 중앙.
# --at     배경 사진에서 객체를 놓을 위치. 0~1 비율 (0.5,0.7 = 가로 중앙, 세로 70%)
# --scale  객체 너비를 배경 너비의 몇 배로 할지 (0.35 = 35%)

import argparse
import os
import sys
import time

import cv2
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from pipeline import extract_mask_candidates, composite, unload_sam   # noqa: E402


def imread_unicode(path: str, flags=cv2.IMREAD_COLOR) -> np.ndarray | None:
    """cv2.imread 는 윈도우에서 한글 경로를 못 읽는다. 파일을 직접 읽어 디코딩한다."""
    try:
        data = np.fromfile(path, dtype=np.uint8)
    except OSError:
        return None
    if data.size == 0:
        return None
    return cv2.imdecode(data, flags)


def imwrite_unicode(path: str, image: np.ndarray):
    """cv2.imwrite 도 마찬가지로 한글 경로에서 조용히 실패한다."""
    ext = os.path.splitext(path)[1] or ".png"
    ok, buf = cv2.imencode(ext, image)
    if not ok:
        raise RuntimeError(f"인코딩 실패: {path}")
    with open(path, "wb") as f:
        f.write(buf.tobytes())


def build_placement_mask(bg_shape, obj_mask, at, scale):
    """
    배경 위 어디에 어떤 크기로 놓을지를 흰 사각형 마스크로 만든다.
    composite() 는 이 마스크의 bounding box 만 보므로 사각형이면 충분하다.
    객체의 가로세로 비율은 유지한다.
    """
    bh, bw = bg_shape[:2]
    x, y, w, h = cv2.boundingRect(obj_mask.astype(np.uint8))
    if w == 0 or h == 0:
        raise SystemExit("객체 마스크가 비어 있습니다. --point 위치를 바꿔보세요.")

    dw = int(bw * scale)
    dh = int(dw * (h / w))

    cx, cy = int(bw * at[0]), int(bh * at[1])
    x0, y0 = cx - dw // 2, cy - dh // 2

    mask = np.zeros((bh, bw), dtype=np.uint8)
    mask[max(0, y0):min(bh, y0 + dh), max(0, x0):min(bw, x0 + dw)] = 1
    if mask.sum() == 0:
        raise SystemExit("배치 영역이 배경 밖으로 나갔습니다. --at 값을 조정하세요.")
    return mask


def label(img_bgr, text):
    out = img_bgr.copy()
    cv2.rectangle(out, (0, 0), (out.shape[1], 32), (0, 0, 0), -1)
    cv2.putText(out, text, (10, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
    return out


def parse_pair(text, cast):
    parts = text.split(",")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("x,y 형식으로 입력하세요 (예: 640,900)")
    return (cast(parts[0]), cast(parts[1]))


def main():
    p = argparse.ArgumentParser(description="합성 로직 단독 테스트")
    p.add_argument("object_image", help="가져올 객체가 담긴 사진")
    p.add_argument("background_image", help="객체를 놓을 배경 사진")
    p.add_argument("--point", type=lambda s: parse_pair(s, int), default=None,
                   help="객체 사진에서 찍을 지점 (픽셀). 기본값: 사진 중앙")
    p.add_argument("--at", type=lambda s: parse_pair(s, float), default=(0.5, 0.5),
                   help="배경에서 놓을 위치, 0~1 비율. 기본값: 0.5,0.5")
    p.add_argument("--scale", type=float, default=0.4,
                   help="객체 너비 / 배경 너비. 기본값: 0.4")
    p.add_argument("--candidate", type=int, default=0,
                   help="SAM 후보 번호 (0=가장 큰 영역). 원하는 게 안 잡히면 1, 2 로 바꿔보세요")
    p.add_argument("--out", default="try_result.png", help="결과 저장 경로")
    args = p.parse_args()

    obj_rgb = imread_unicode(args.object_image)
    if obj_rgb is None:
        raise SystemExit(f"객체 사진을 읽을 수 없습니다: {args.object_image}")
    obj_rgb = cv2.cvtColor(obj_rgb, cv2.COLOR_BGR2RGB)

    bg_rgb = imread_unicode(args.background_image)
    if bg_rgb is None:
        raise SystemExit(f"배경 사진을 읽을 수 없습니다: {args.background_image}")
    bg_rgb = cv2.cvtColor(bg_rgb, cv2.COLOR_BGR2RGB)

    h, w = obj_rgb.shape[:2]
    point = args.point or (w // 2, h // 2)
    if not (0 <= point[0] < w and 0 <= point[1] < h):
        raise SystemExit(f"--point 가 사진 범위를 벗어났습니다. 사진 크기는 {w}x{h} 입니다.")

    print(f"[1/3] SAM 객체 추출 중... (최초 1회 모델 로딩에 시간이 걸립니다)")
    t0 = time.time()
    candidates = extract_mask_candidates(obj_rgb, [(point[0], point[1], 1)])
    print(f"      후보 {len(candidates)}개, {time.time() - t0:.1f}초")
    for i, c in enumerate(candidates):
        marker = " <- 사용" if i == args.candidate else ""
        print(f"      후보 {i}: 영역 {c['area'] / (h * w) * 100:5.1f}%{marker}")

    if not (0 <= args.candidate < len(candidates)):
        raise SystemExit(f"--candidate 는 0~{len(candidates) - 1} 사이여야 합니다.")
    ref_mask = candidates[args.candidate]["mask"]

    placement = build_placement_mask(bg_rgb.shape, ref_mask, args.at, args.scale)

    # SAM 이 GPU 에 올라가 있으면 PCTNet 이 쓸 자리가 줄어든다
    unload_sam()

    print("[2/3] LAB 색이동 방식으로 합성 중...")
    t0 = time.time()
    lab = composite(obj_rgb, ref_mask, bg_rgb, placement, method="lab")
    print(f"      {time.time() - t0:.2f}초")

    print("[3/3] PCTNet 방식으로 합성 중...")
    t0 = time.time()
    try:
        pct = composite(obj_rgb, ref_mask, bg_rgb, placement, method="pctnet")
        print(f"      {time.time() - t0:.2f}초")
    except Exception as e:
        print(f"      실패: {e}")
        pct = None

    height = 480
    def fit(img_rgb):
        s = height / img_rgb.shape[0]
        return cv2.resize(cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR),
                          (int(img_rgb.shape[1] * s), height))

    panels = [label(fit(bg_rgb), "background"), label(fit(lab), "LAB shift")]
    if pct is not None:
        panels.append(label(fit(pct), "PCTNet"))

    imwrite_unicode(args.out, np.concatenate(panels, axis=1))
    print(f"\n저장 완료: {os.path.abspath(args.out)}")


if __name__ == "__main__":
    main()
