# backend/pipeline.py
# SAM(객체 추출) 과 AnyDoor(배경 합성) 를 감싸는 모듈.
#
# 중요한 설계 원칙:
#   - SAM은 "1단계 객체 추출" 때 딱 한 번만 돌린다.
#     그 결과(마스크)를 저장해두고, 합성 단계에서는 재사용만 한다.
#     (예전 구조는 합성할 때 SAM을 또 돌려서, 사용자가 본 미리보기와
#      실제 합성에 쓰인 마스크가 달라질 수 있었다)
#   - 배경의 "배치 영역"은 AI가 정하지 않는다.
#     사용자가 화면에서 드래그/리사이즈로 확정한 영역을 그대로 받아 쓴다.

import sys
import os
import gc
import numpy as np
import cv2
import torch

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAM_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "segment-anything"))
ANYDOOR_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "AnyDoor"))
sys.path.insert(0, SAM_DIR)
sys.path.insert(0, ANYDOOR_DIR)

SAM_CHECKPOINT = os.path.join(SAM_DIR, "checkpoints", "sam_vit_h_4b8939.pth")
SAM_MODEL_TYPE = "vit_h"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


# ---------------------------------------------------------------------------
# 1) SAM: 원본 사진 + 클릭 좌표 -> 객체 마스크
# ---------------------------------------------------------------------------
_sam_predictor = None


def _get_sam_predictor():
    global _sam_predictor
    if _sam_predictor is None:
        # 10GB VRAM 카드에서는 AnyDoor(~9.7GB)가 GPU에 남아있으면
        # SAM이 들어갈 자리가 없어 극도로 느려진다 (공유 메모리로 스필오버).
        # SAM을 새로 로딩하기 전엔 AnyDoor를 먼저 내려서 자리를 비운다.
        unload_anydoor()

        from segment_anything import sam_model_registry, SamPredictor
        print("[pipeline] SAM 모델 로딩...")
        sam = sam_model_registry[SAM_MODEL_TYPE](checkpoint=SAM_CHECKPOINT)
        sam.to(device=DEVICE)
        _sam_predictor = SamPredictor(sam)
    return _sam_predictor


def extract_mask_candidates(image_rgb: np.ndarray,
                             points: list[tuple[int, int, int]] | None = None) -> list[dict]:
    """
    사용자가 찍은 점들로 SAM 후보 마스크를 만들어 전부 반환한다.
    각 항목은 {"mask": 0/1 배열, "score": SAM 자체 신뢰도, "area": 픽셀 수}.

    points: (x, y, label) 목록. label 1 = 이 지점을 포함(더하기), 0 = 제외(빼기).
      - 점 하나만 주면 SAM이 후보 3개(작은 부분/중간/전체)를 내놓는다.
      - 점을 여러 개 주면 SAM은 그 조건을 모두 만족하는 마스크 하나로 좁힌다.
        (사람 + 가방을 각각 찍으면 둘을 합친 하나의 객체로 잡히는 식)

    면적이 큰 순서로 정렬해서 반환한다 — 인덱스 0이 가장 큰(보통 '전체 객체') 후보다.
    이유: SAM의 score는 "경계가 얼마나 깔끔한가"를 기준으로 매겨져서, 애매한 지점을
    클릭하면 티셔츠처럼 작고 국소적인 부위가 score는 더 높게 나오는 경우가 있다.
    우리 제품은 "사용자가 지정한 것 전체"를 뽑는 게 목적이라 면적 기준으로 정렬한다.
    """
    predictor = _get_sam_predictor()
    predictor.set_image(image_rgb)

    h, w = image_rgb.shape[:2]
    if not points:
        points = [(w // 2, h // 2, 1)]

    coords = np.array([[p[0], p[1]] for p in points])
    labels = np.array([p[2] for p in points])

    # 점이 하나뿐일 때만 후보 3개를 받는다. 여러 개면 사용자가 이미 의도를 좁힌
    # 것이므로 SAM에게도 하나로 결정하게 맡긴다(후보를 내밀면 오히려 헷갈린다).
    multi = len(points) == 1

    masks, scores, _ = predictor.predict(
        point_coords=coords,
        point_labels=labels,
        multimask_output=multi,
    )

    cleaned = [_fill_mask_holes(masks[i].astype(np.uint8)) for i in range(len(masks))]
    candidates = []
    for i in range(len(masks)):
        mask = cleaned[i]
        alpha = _refine_with_birefnet(image_rgb, mask)
        candidates.append({
            "mask": mask,                      # 0/1 이진 마스크 (합성 로직이 쓰는 값)
            "alpha": alpha,                    # 0~255 부드러운 알파 (미리보기/컷아웃용)
            "score": float(scores[i]),
            "area": int(mask.sum()),
        })
    candidates.sort(key=lambda c: c["area"], reverse=True)
    return candidates


def _refine_with_birefnet(image_rgb: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    SAM 마스크를 BiRefNet 으로 다시 다듬는다.

    SAM 은 '어떤 덩어리를 고를지'는 잘하지만 경계가 픽셀 단위로 각지고, 인식표처럼
    재질이 다른 작은 부위를 구멍으로 남기는 일이 있다. BiRefNet 은 반대로 '무엇을
    고를지'는 못 정하지만 경계를 훨씬 정밀하게(털 한 올 수준까지) 뽑는다.
    그래서 SAM 이 고른 영역을 BiRefNet 에게 넘겨 경계만 다시 그리게 한다.

    반환값은 0~255 알파. BiRefNet 을 못 쓰는 환경이면 SAM 마스크를 그대로
    0/255 로 바꿔서 돌려주므로, 이 단계가 없어도 파이프라인은 그대로 동작한다.
    """
    try:
        from birefnet_client import refine_mask
        alpha = refine_mask(image_rgb, mask)
    except Exception as e:
        print(f"[pipeline] BiRefNet 재분할 건너뜀: {e}")
        alpha = None

    if alpha is None or alpha.shape[:2] != mask.shape[:2]:
        return (mask * 255).astype(np.uint8)

    # BiRefNet 은 크롭 영역 안에서 '두드러진 물체'를 찾으므로, 사용자가 고른 것과
    # 다른 물체를 잡아버릴 수 있다. SAM 마스크와 겹치는 정도가 너무 낮으면
    # 엉뚱한 걸 잡은 것으로 보고 SAM 결과를 그대로 쓴다.
    refined_bin = alpha > 128
    sam_bin = mask.astype(bool)
    overlap = np.logical_and(refined_bin, sam_bin).sum()
    if sam_bin.sum() == 0 or overlap / sam_bin.sum() < 0.5:
        print("[pipeline] BiRefNet 결과가 SAM 선택과 크게 어긋나 무시함")
        return (mask * 255).astype(np.uint8)

    return alpha


def _fill_mask_holes(mask: np.ndarray, hole_ratio: float = 0.02) -> np.ndarray:
    """
    SAM 마스크 내부의 자잘한 구멍을 메운다.

    왜 필요한가: 검은 바지처럼 어두운 단색 옷은 주름 때문에 생긴 명암 차이를 SAM이
    "다른 영역"으로 오인해서, 옷 안쪽이 줄무늬처럼 숭숭 뚫린 마스크가 나오는 경우가 있다.
    이 상태로 합성하면 하반신이 지지직거리는 것처럼 보인다.

    두 단계로 처리한다:
      1) 모폴로지 닫기(closing)로 얇은 틈과 점 노이즈를 메운다.
      2) 그래도 남은 '내부 구멍' 중 작은 것만 채운다. 전체를 무조건 채우지 않는 이유는
         가방 손잡이 사이처럼 배경이 실제로 비쳐 보여야 하는 큰 구멍을 살리기 위해서다.
         구멍 넓이가 마스크 전체의 hole_ratio(기본 2%)보다 작을 때만 메운다.
    """
    h, w = mask.shape[:2]
    k = max(3, (min(h, w) // 200) | 1)   # 이미지 크기에 비례한 홀수 커널
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    total_area = int(closed.sum())
    if total_area == 0:
        return closed

    # 배경(0) 영역들에 라벨을 매겨서, 바깥 배경과 이어지지 않은 것 = 내부 구멍
    num, labels = cv2.connectedComponents((1 - closed).astype(np.uint8))
    border_labels = set(labels[0, :]) | set(labels[-1, :]) | set(labels[:, 0]) | set(labels[:, -1])

    filled = closed.copy()
    for label in range(1, num):
        if label in border_labels:
            continue                      # 바깥 배경이므로 건드리지 않는다
        hole = labels == label
        if hole.sum() < total_area * hole_ratio:
            filled[hole] = 1
    return filled


def make_cutout_png(image_rgb: np.ndarray, mask: np.ndarray) -> bytes:
    """
    마스크를 알파 채널로 붙여서, 배경이 투명한 미리보기 PNG 바이트를 만든다.

    mask 는 0/1 이진 마스크도 되고, BiRefNet 이 만든 0~255 알파도 된다.
    후자면 털 가장자리가 부드럽게 반투명 처리돼서 훨씬 자연스럽게 보인다.
    """
    bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
    bgra = cv2.cvtColor(bgr, cv2.COLOR_BGR2BGRA)
    alpha = mask if mask.max() > 1 else (mask * 255)
    bgra[:, :, 3] = alpha.astype(np.uint8)

    ok, buf = cv2.imencode(".png", bgra)
    if not ok:
        raise RuntimeError("cutout PNG 인코딩 실패")
    return buf.tobytes()


def unload_sam():
    """AnyDoor를 돌리기 전에 SAM을 GPU에서 내려 VRAM을 확보한다 (10GB 카드 대응)."""
    global _sam_predictor
    if _sam_predictor is not None:
        del _sam_predictor
        _sam_predictor = None
        gc.collect()
        torch.cuda.empty_cache()
        print("[pipeline] SAM GPU 메모리 해제 완료")


def unload_anydoor():
    """
    SAM을 돌리기 전에 AnyDoor를 GPU에서 내린다 (unload_sam()의 반대 방향).
    run_inference.py는 import 시점에 모델을 전역변수로 한 번만 로딩해서 캐싱하므로,
    그 모듈 캐시를 지우고 참조를 끊어야 GPU 메모리가 실제로 회수된다.
    """
    if "run_inference" in sys.modules:
        del sys.modules["run_inference"]
        gc.collect()
        torch.cuda.empty_cache()
        print("[pipeline] AnyDoor GPU 메모리 해제 완료")


# ---------------------------------------------------------------------------
# 2) AnyDoor: (원본+객체마스크) 를 (배경+배치영역) 에 합성
# ---------------------------------------------------------------------------
def _import_anydoor():
    """
    run_inference.py 안에 './configs/...', './dinov2' 같은 cwd 기준 상대경로가 있어서
    AnyDoor 폴더에서 실행될 때만 정상 동작한다. 서버의 cwd는 backend/ 이므로
    최초 import(=모델 로딩) 하는 순간에만 잠깐 이동했다가 되돌아온다.
    """
    if "run_inference" in sys.modules:
        from run_inference import inference_single_image
        return inference_single_image

    prev_cwd = os.getcwd()
    try:
        os.chdir(ANYDOOR_DIR)
        from run_inference import inference_single_image
        return inference_single_image
    finally:
        os.chdir(prev_cwd)


# 색 보정 강도 조절값 -------------------------------------------------------
# 원본이 촬영된 환경과 배경 사진의 환경 차이를, 객체 색에 얼마나 반영할지 정한다.
# 1.0 이면 환경 차이를 그대로 다 반영, 0.0 이면 색 보정을 아예 안 한다.
# 밝기(L)를 색조(a,b)보다 세게 잡는 이유: 조명이 바뀌면 밝기는 크게 변하지만
# 색조는 과하게 옮기면 분홍 티셔츠가 잔디색으로 물드는 식으로 원본 정체성이 깨진다.
LIGHT_STRENGTH = 0.6      # 밝기 보정 강도
COLOR_STRENGTH = 0.4      # 색조(색온도) 보정 강도
MAX_L_SHIFT = 25.0        # 밝기 이동 상한 (LAB의 L, 0~255 스케일 기준)
MAX_AB_SHIFT = 10.0       # 색조 이동 상한
EDGE_FEATHER = 2.0        # 경계 부드럽게 하는 가우시안 시그마 (픽셀 수 아님, +-3배로 번짐)


def _prepare_object(ref_image_rgb: np.ndarray, ref_mask: np.ndarray,
                     placement_mask: np.ndarray):
    """
    원본에서 객체만 잘라내 사용자가 정한 배치 크기로 맞춘다.
    합성 경로가 여러 개라도 '객체를 어디에 어떤 크기로 놓는가'는 하나여야 하므로
    이 계산을 한 곳에 모아 공유한다.

    반환: (배치 크기로 맞춘 객체 RGB, 같은 크기의 마스크, 붙일 좌상단 좌표, 배치 bbox)
    """
    ref_bbox = cv2.boundingRect(ref_mask.astype(np.uint8))
    dst_bbox = cv2.boundingRect(placement_mask.astype(np.uint8))
    if ref_bbox[2] == 0 or ref_bbox[3] == 0:
        raise ValueError("객체 마스크가 비어 있습니다.")
    if dst_bbox[2] == 0 or dst_bbox[3] == 0:
        raise ValueError("배치 영역 마스크가 비어 있습니다.")

    rx, ry, rw, rh = ref_bbox
    dx, dy, dw, dh = dst_bbox
    obj = cv2.resize(ref_image_rgb[ry:ry + rh, rx:rx + rw], (dw, dh),
                     interpolation=cv2.INTER_LANCZOS4)
    obj_mask = cv2.resize(ref_mask[ry:ry + rh, rx:rx + rw].astype(np.uint8), (dw, dh),
                          interpolation=cv2.INTER_NEAREST)
    return obj, obj_mask, (dx, dy), dst_bbox


def composite(ref_image_rgb: np.ndarray, ref_mask: np.ndarray,
              bg_image_rgb: np.ndarray, placement_mask: np.ndarray,
              guidance_scale: float = 5.0,
              seed: int | None = None,
              method: str = "auto") -> np.ndarray:
    """
    원본 객체의 픽셀을 그대로 옮기되, 조명/색감만 배경 환경에 맞춰 보정하는 합성.
    두 방식 중 하나로 보정하며, 어느 쪽이든 객체 픽셀을 '재생성'하지는 않는다.

    [pctnet] 보정 없이 붙인 뒤 PCTNet(libcom) 에게 객체 영역 색감을 배경에 맞추게 한다.
      학습된 하모나이제이션 모델이라 영역별로 다르게 보정할 수 있다. 원본 해상도
      그대로 색만 옮기므로 디테일 손실이 없다.

    [lab] 원본이 찍힌 환경과 배경 환경의 LAB 평균 차이만큼 객체 색을 평행이동한다.
      - 원본 환경 : 원본 사진에서 객체가 아닌 부분 (예: 하얀 스튜디오 배경)
      - 배경 환경 : 배치될 자리 주변의 배경 픽셀 (예: 그늘진 골목길)
      평균만 옮기고 대비는 건드리지 않아 객체 내부의 명암/질감 관계가 보존된다.
      (Poisson Blending 은 경계값 기준으로 내부를 재구성해서, 흰 배경 스튜디오 사진처럼
       대비가 약한 원본은 사람이 반투명해지는 문제가 있었다 - 2026-09-04 실측)

    ref_image_rgb  : 사용자가 올린 원본 사진
    ref_mask       : 그 사진에서 SAM이 뽑아낸 객체 영역 (0/1)
    bg_image_rgb   : 사용자가 고른 배경 사진
    placement_mask : 사용자가 드래그/리사이즈로 확정한 '객체가 놓일 영역' (0/1)
    method         : "auto"   PCTNet 을 쓰고, 못 쓰면 lab 으로 넘어간다 (기본)
                     "pctnet" PCTNet 만 쓴다. 실패하면 예외 (비교 측정용)
                     "lab"    LAB 색이동만 쓴다 (비교 측정용)
    guidance_scale, seed : 쓰지 않는다. 난수가 없는 결정론적 계산이라 같은 입력이면
                     항상 같은 결과가 나온다. 호출부/DB 스키마 호환을 위해 인자만 남겨둔다.

    그림자 생성은 여기서 하지 않는다 (별도 논의 중).
    """
    obj, obj_mask, (dx, dy), dst_bbox = _prepare_object(
        ref_image_rgb, ref_mask, placement_mask)

    # 2) PCTNet 경로: 보정 없이 붙인 다음 모델에게 객체 색감을 맡긴다
    if method in ("auto", "pctnet"):
        from harmony_client import harmonize

        pasted = _feathered_paste(bg_image_rgb, obj, obj_mask, (dx, dy))
        fg_mask = _placed_mask(bg_image_rgb.shape, obj_mask, (dx, dy))
        harmonized = harmonize(pasted, fg_mask)
        if harmonized is not None:
            return harmonized
        if method == "pctnet":
            raise RuntimeError("PCTNet 보정에 실패했습니다 (harmony_client 로그 확인).")
        print("[pipeline] PCTNet 을 쓸 수 없어 LAB 색이동으로 합성합니다")

    # 3) LAB 경로: 두 환경의 조명 차이를 구해 객체 색을 옮긴 뒤 얹는다
    shift = _estimate_lighting_shift(ref_image_rgb, ref_mask, bg_image_rgb, dst_bbox)
    return _feathered_paste(bg_image_rgb, _apply_lab_shift(obj, shift), obj_mask, (dx, dy))


def _lab_mean(image_rgb: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray | None:
    """마스크가 1인 픽셀들의 LAB 평균. 샘플이 너무 적으면 None."""
    lab = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    if mask is None:
        return lab.reshape(-1, 3).mean(axis=0)
    sel = mask.astype(bool)
    if sel.sum() < 100:                       # 통계로 쓰기엔 표본이 부족
        return None
    return lab[sel].mean(axis=0)


def _estimate_lighting_shift(ref_image_rgb: np.ndarray, ref_mask: np.ndarray,
                              bg_image_rgb: np.ndarray,
                              dst_bbox: tuple[int, int, int, int]) -> np.ndarray:
    """
    '원본이 찍힌 환경'과 '놓일 자리의 환경'의 LAB 평균 차이를 구한다.
    배경 환경은 배치 영역 전체가 아니라 그 **주변 띠**에서 뽑는다. 그늘에 놓으면
    그늘의 밝기를, 양지에 놓으면 양지의 밝기를 따라가게 하기 위해서다.
    """
    ref_env = _lab_mean(ref_image_rgb, 1 - ref_mask.astype(np.uint8))

    # 배치 영역 주변 띠(ring)를 만든다: bbox 를 여유있게 넓힌 사각형에서 bbox 자체를 뺀다
    bh, bw = bg_image_rgb.shape[:2]
    dx, dy, dw, dh = dst_bbox
    margin = max(20, int(max(dw, dh) * 0.3))
    x0, y0 = max(dx - margin, 0), max(dy - margin, 0)
    x1, y1 = min(dx + dw + margin, bw), min(dy + dh + margin, bh)

    ring = np.zeros((bh, bw), dtype=np.uint8)
    ring[y0:y1, x0:x1] = 1
    ring[dy:dy + dh, dx:dx + dw] = 0

    dst_env = _lab_mean(bg_image_rgb, ring)
    if dst_env is None:                       # 배치 영역이 화면을 거의 다 덮은 경우
        dst_env = _lab_mean(bg_image_rgb)
    if ref_env is None or dst_env is None:
        return np.zeros(3, dtype=np.float32)  # 판단할 근거가 없으면 보정하지 않는다

    delta = dst_env - ref_env
    delta[0] = np.clip(delta[0] * LIGHT_STRENGTH, -MAX_L_SHIFT, MAX_L_SHIFT)
    delta[1] = np.clip(delta[1] * COLOR_STRENGTH, -MAX_AB_SHIFT, MAX_AB_SHIFT)
    delta[2] = np.clip(delta[2] * COLOR_STRENGTH, -MAX_AB_SHIFT, MAX_AB_SHIFT)
    return delta.astype(np.float32)


def _apply_lab_shift(obj_rgb: np.ndarray, shift: np.ndarray) -> np.ndarray:
    """
    객체의 LAB 값을 shift 만큼 평행이동한다.
    평균만 옮기고 대비는 그대로 두므로, 원본의 명암/질감 관계가 보존된다.
    """
    if not np.any(shift):
        return obj_rgb
    lab = cv2.cvtColor(obj_rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    lab += shift.reshape(1, 1, 3)
    lab = np.clip(lab, 0, 255).astype(np.uint8)
    return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)


def _overlap_slices(bg_shape, obj_shape, top_left: tuple[int, int]):
    """
    배경 위 top_left 에 객체를 놓았을 때 실제로 겹치는 영역을
    (객체쪽 슬라이스, 배경쪽 슬라이스) 로 돌려준다. 안 겹치면 None.

    붙이기와 마스크 생성이 반드시 같은 영역을 가리켜야 하므로 계산을 여기 하나로 모은다.
    """
    bh, bw = bg_shape[:2]
    oh, ow = obj_shape[:2]
    x0, y0 = top_left

    dx0, dy0 = max(x0, 0), max(y0, 0)
    dx1, dy1 = min(x0 + ow, bw), min(y0 + oh, bh)
    if dx1 <= dx0 or dy1 <= dy0:
        return None

    sx0, sy0 = max(0, -x0), max(0, -y0)
    h, w = dy1 - dy0, dx1 - dx0
    return (
        (slice(sy0, sy0 + h), slice(sx0, sx0 + w)),
        (slice(dy0, dy1), slice(dx0, dx1)),
    )


def _placed_mask(bg_shape, obj_mask: np.ndarray, top_left: tuple[int, int]) -> np.ndarray:
    """객체 마스크를 배경 좌표계의 전체 크기 마스크로 옮긴다 (PCTNet 입력용)."""
    full = np.zeros(bg_shape[:2], dtype=np.uint8)
    region = _overlap_slices(bg_shape, obj_mask.shape, top_left)
    if region is None:
        return full
    src_slice, dst_slice = region
    full[dst_slice] = (obj_mask[src_slice] > 0).astype(np.uint8) * 255
    return full


# 접지 그림자(2D 단서 기반) 조절값 ------------------------------------------
# AnyDoor 재생성 없이, 발밑에 타원을 그려 넣는 결정론적 방식.
# 광원을 실제로 측정하지 않는다 — 단일 2D 사진에서 광원 방향/세기를 복원하는 건
# 근본적으로 정보가 부족한 역문제(ill-posed)라, 대신 '그럴듯해 보이는' 고정된
# 형태를 깐다. 이 방식의 장점은 diffusion처럼 예측 불가능한 잡음이 안 생기고
# (2026-09-20 실측: AnyDoor가 인물 머리 위 하늘에 얼룩을 만든 사례 있음),
# 밀리초 단위로 끝난다는 것이다.
FOOTPRINT_WIDTH_RATIO = 0.55   # 객체 bbox 너비 대비 그림자 타원의 너비 비율
SHADOW_SQUASH = 0.30           # 타원 세로/가로 비율 (얕게 눌린 접지 그림자 모양)
SYNTH_SHADOW_MAX = 0.4         # 그림자 중심부의 최대 감광 비율
SYNTH_SHADOW_FEATHER = 0.35    # 타원 크기 대비 블러 강도 (가장자리를 부드럽게)


def _synthetic_shadow(bg_shape: tuple[int, int], obj_mask: np.ndarray,
                       top_left: tuple[int, int]) -> np.ndarray:
    """
    객체의 발밑(bbox 하단)에 부드러운 타원 그림자를 그려 0~1 감광 맵으로 돌려준다.

    광원 방향을 추정하지 않고 항상 객체 바로 아래에 곧게 그린다. 방향까지
    자동으로 추정하려면 배경 사진 속 다른 물체의 그림자를 분석하거나 밝기
    비대칭을 읽어야 하는데, 이런 휴리스틱은 틀렸을 때 오히려 그림자가 없는 것보다
    더 부자연스러워 보일 위험이 있어 첫 구현에서는 뺐다. 필요해지면 이 함수의
    '중심 x좌표'만 옮기면 되도록 구조를 열어뒀다.
    """
    h, w = bg_shape[:2]
    # obj_mask 는 배치 크기(dw x dh)만큼의 '로컬' 마스크다 (_prepare_object 반환값).
    # boundingRect 도 그 로컬 좌표계 기준이므로, 배경 캔버스 위 실제 위치를 구하려면
    # top_left(배경 좌표계에서 객체를 붙인 좌상단)를 반드시 더해야 한다.
    # 이걸 빠뜨리면 그림자가 객체와 전혀 무관한 엉뚱한 위치(로컬 좌표를 배경 좌표인 양
    # 착각한 위치)에 찍힌다 -> 2026-09-21 실측으로 발견 (그림자 x범위가 사람 위치와
    # 전혀 안 겹침).
    lx, ly, bw, bh = cv2.boundingRect(obj_mask.astype(np.uint8))
    if bw == 0 or bh == 0:
        return np.zeros((h, w), dtype=np.float32)
    x, y = lx + top_left[0], ly + top_left[1]

    ew = max(4.0, bw * FOOTPRINT_WIDTH_RATIO)
    eh = max(3.0, ew * SHADOW_SQUASH)

    # 접지면 중심: bbox 하단 가장자리의 가로 중앙에, 타원 절반 정도가 아래로
    # 삐져나오게 살짝 내려서 찍는다. 이러면 타원 위쪽 절반은 객체 마스크에 가려
    # 자연스럽게 '객체 밑에서 나오는' 모양이 되고, 아래쪽 절반만 실제로 보인다.
    cx = x + bw / 2.0
    cy = y + bh + eh * 0.15

    shadow = np.zeros((h, w), dtype=np.float32)
    cv2.ellipse(shadow, (int(round(cx)), int(round(cy))),
               (int(round(ew / 2)), int(round(eh / 2))),
               0, 0, 360, 1.0, thickness=-1)

    sigma = max(2.0, eh * SYNTH_SHADOW_FEATHER)
    shadow = cv2.GaussianBlur(shadow, (0, 0), sigmaX=sigma)

    # 가우시안 블러는 타원 크기에 비해 시그마가 크면 중심 밝기 자체를 눌러버린다
    # (에너지가 옆으로 퍼지면서 봉우리 값이 낮아짐). 가장자리를 부드럽게 하는 목적은
    # 유지하면서 중심부는 항상 의도한 최대 밝기가 나오도록, 블러 후 자체 최대값으로
    # 나눠 다시 0~1로 정규화한다.
    peak = shadow.max()
    if peak > 0:
        shadow = shadow / peak

    # 객체 자신 위에는 그림자가 얹히면 안 된다 (원본 픽셀 보존 원칙)
    obj_full = _placed_mask(bg_shape, obj_mask, top_left) > 0
    shadow[obj_full] = 0.0

    return np.clip(shadow * SYNTH_SHADOW_MAX, 0.0, SYNTH_SHADOW_MAX)


def composite_with_synthetic_shadow(ref_image_rgb: np.ndarray, ref_mask: np.ndarray,
                                     bg_image_rgb: np.ndarray, placement_mask: np.ndarray,
                                     method: str = "auto",
                                     shadow_strength: float = 1.0) -> np.ndarray:
    """
    AnyDoor 없이, 결정론적인 접지 그림자만 얹는 합성.

    composite_with_shadow() 와 목적은 같지만(그림자 없는 밋밋함 개선) 수단이
    다르다 — diffusion 재생성 대신 순수 이미지 연산이라 수 밀리초 안에 끝나고,
    같은 입력이면 항상 같은 결과가 나온다. 대신 배경 조명 방향을 반영하지 않고
    항상 객체 바로 아래에 그림자를 깐다는 한계가 있다.
    """
    base = composite(ref_image_rgb, ref_mask, bg_image_rgb, placement_mask, method=method)
    if shadow_strength <= 0:
        return base

    _, obj_mask, top_left, _ = _prepare_object(ref_image_rgb, ref_mask, placement_mask)
    shadow = _synthetic_shadow(bg_image_rgb.shape, obj_mask, top_left)
    if shadow.max() <= 0:
        return base

    factor = np.clip(1.0 - shadow * float(shadow_strength), 0.0, 1.0)[:, :, None]
    return np.clip(base.astype(np.float32) * factor, 0, 255).astype(np.uint8)


def _feathered_paste(bg_rgb: np.ndarray, obj_rgb: np.ndarray, obj_mask: np.ndarray,
                      top_left: tuple[int, int]) -> np.ndarray:
    """
    객체를 배경 위에 얹는다. 경계가 칼로 자른 것처럼 보이지 않도록 알파를 살짝만 흐린다.
    EDGE_FEATHER 는 픽셀 수가 아니라 가우시안 시그마다(실제 번짐 폭은 약 +-3배).
    크게 잡으면 다리처럼 가는 부위가 통째로 반투명해지므로 작게 유지한다.
    """
    out = bg_rgb.copy()
    region = _overlap_slices(out.shape, obj_rgb.shape, top_left)
    if region is None:
        return out
    src_slice, dst_slice = region

    src = obj_rgb[src_slice].astype(np.float32)
    m = obj_mask[src_slice].astype(np.float32)

    alpha = cv2.GaussianBlur(m, (0, 0), sigmaX=EDGE_FEATHER) if EDGE_FEATHER > 0 else m
    alpha = np.clip(alpha, 0.0, 1.0)[:, :, None]

    dst = out[dst_slice].astype(np.float32)
    out[dst_slice] = np.clip(src * alpha + dst * (1 - alpha), 0, 255).astype(np.uint8)
    return out


def composite_anydoor(ref_image_rgb: np.ndarray, ref_mask: np.ndarray,
                       bg_image_rgb: np.ndarray, placement_mask: np.ndarray,
                       guidance_scale: float = 5.0,
                       seed: int | None = None) -> np.ndarray:
    """
    [현재 미사용 - 위 composite() 로 대체됨. 참고/롤백용으로 남겨둠]
    AnyDoor로 배치 영역을 통째로 '다시 생성'하던 예전 방식. 사람처럼 디테일이 중요한
    대상에서 DINOv2 224px 인코딩 병목 때문에 원본이 크게 뭉개지는 문제가 있어
    (2026-09-04 실측: 얼굴/가방 디테일 소실, 1건당 15분) 기본 경로에서 뺐다.

    ref_image_rgb  : 사용자가 올린 원본 사진 (예: 손 위의 햄스터)
    ref_mask       : 그 사진에서 SAM이 뽑아낸 객체 영역 (0/1)
    bg_image_rgb   : 사용자가 고른 배경 사진
    placement_mask : 사용자가 드래그/리사이즈로 확정한 '객체가 놓일 영역' (0/1)
                     -> 배경에 원래 뭐가 있었는지와 무관하게, 이 영역에 객체를 그린다
    seed           : 결과 재현용 시드. 같은 입력 + 같은 시드 = 항상 같은 결과.
                     None 이면 매번 다른 결과가 나온다.

    주의: AnyDoor의 crop_back()은 마스크 '모양'이 아니라 마스크 주변의
    정사각형 영역 전체를 새로 생성한 걸로 덮어쓴다. 그 정사각형 안에
    들어간 다른 사물(예: 고양이, 가구)까지 같이 뭉개져서 나온다.
    그래서 AnyDoor가 뱉은 결과에서 '우리가 원한 마스크 영역'만 취하고,
    나머지는 원본 배경으로 되돌리는 후처리를 여기서 한 번 더 한다.
    """
    unload_sam()
    inference_single_image = _import_anydoor()

    raw_result = inference_single_image(
        ref_image_rgb, ref_mask,
        bg_image_rgb.copy(), placement_mask,
        guidance_scale=guidance_scale,
        seed=seed,
    )

    return _blend_with_original(raw_result, bg_image_rgb, placement_mask)


# 그림자 이식 조절값 -------------------------------------------------------
# AnyDoor 결과에서 '어두워진 정도'만 뽑아 기본 합성 결과에 곱한다. 텍스처는 가져오지
# 않으므로 AnyDoor가 배경을 뭉개놓아도 그 손상이 결과에 섞이지 않는다.
SHADOW_MAX = 0.55          # 최대 감광 비율. 1.0이면 완전히 검게 만들 수 있어 상한을 둔다
SHADOW_ZONE_RATIO = 0.35   # 객체 크기의 몇 배까지를 그림자가 생길 수 있는 범위로 볼지
SHADOW_MIN_LEVEL = 0.04    # 이보다 옅은 감광은 텍스처 재생성 잡음으로 보고 버린다


def _extract_shadow(generated_rgb: np.ndarray, original_bg_rgb: np.ndarray,
                     object_mask: np.ndarray) -> np.ndarray:
    """
    AnyDoor 생성 결과와 원본 배경을 비교해 '어두워진 정도'만 0~1 맵으로 뽑는다.

    왜 텍스처를 안 가져오고 감광량만 가져오는가:
      AnyDoor는 배치 영역 주변 정사각형을 통째로 다시 그리기 때문에, 그 결과를 그대로
      쓰면 잔디·바닥 같은 배경 텍스처까지 재생성본(뭉개진 것)으로 바뀐다. 반면 그림자는
      본질적으로 '넓은 영역의 완만한 밝기 저하'라서, 밝기 비율만 뽑아 강하게 블러하면
      텍스처 차이(고주파 잡음)는 평균으로 상쇄되고 그림자 성분(저주파)만 남는다.

    object_mask : 객체가 실제로 차지하는 영역(0/1). 객체 자신은 원본 픽셀을 그대로
                  써야 하므로 그림자 대상에서 제외한다.
    """
    orig_lum = original_bg_rgb.astype(np.float32).mean(axis=2)
    gen_lum = generated_rgb.astype(np.float32).mean(axis=2)

    # 어두워진 쪽만 취한다. 밝아진 곳은 그림자가 아니라 생성 잡음이다.
    darkening = np.clip(1.0 - (gen_lum + 1.0) / (orig_lum + 1.0), 0.0, 1.0)

    # 그림자가 생길 수 있는 범위: 객체 주변으로만 한정한다.
    # (정사각형 크롭 전체를 허용하면 멀리 떨어진 곳의 재생성 차이까지 그림자로 오인한다)
    # 객체에서 margin 픽셀 이내인 바깥 영역만 그림자 후보로 삼는다.
    # 큰 객체에서는 margin 이 수백 픽셀이 되는데, 그 크기의 타원 커널로 dilate 하면
    # 매우 느려진다. 거리 변환은 커널 크기와 무관하게 한 번에 끝난다.
    x, y, w, h = cv2.boundingRect(object_mask.astype(np.uint8))
    margin = max(8, int(max(w, h) * SHADOW_ZONE_RATIO))
    outside = (1 - (object_mask > 0).astype(np.uint8))
    dist = cv2.distanceTransform(outside, cv2.DIST_L2, 3)
    zone = ((dist > 0) & (dist <= margin)).astype(np.float32)

    darkening *= zone

    # 강한 블러로 텍스처 잡음을 지우고 그림자의 완만한 형태만 남긴다
    sigma = max(3.0, max(w, h) * 0.04)
    darkening = cv2.GaussianBlur(darkening, (0, 0), sigmaX=sigma)

    # 블러가 객체 바깥의 짙은 그림자를 객체 안쪽으로 번지게 하므로 여기서 다시 지운다.
    # (블러 전에만 지우면 객체 발밑이 같이 어두워져서 원본 픽셀이 훼손된다)
    darkening[object_mask.astype(bool)] = 0.0

    darkening[darkening < SHADOW_MIN_LEVEL] = 0.0
    return np.clip(darkening, 0.0, SHADOW_MAX)


def composite_with_shadow(ref_image_rgb: np.ndarray, ref_mask: np.ndarray,
                           bg_image_rgb: np.ndarray, placement_mask: np.ndarray,
                           method: str = "auto",
                           guidance_scale: float = 5.0,
                           seed: int | None = None,
                           shadow_strength: float = 1.0) -> np.ndarray:
    """
    객체는 원본 픽셀 그대로 두고, AnyDoor 에게는 그림자만 얻어 오는 합성.

    배경: composite() 와 동일 (원본 픽셀 + PCTNet/LAB 색보정) -> 디테일 손실 없음
    추가: AnyDoor 생성 결과에서 객체 바깥의 감광 성분만 뽑아 곱한다 -> 접지 그림자

    AnyDoor 를 기본 경로에서 뺀 이유(DINOv2 224px 로 객체가 뭉개짐)는 객체를 재생성할
    때만 발생한다. 여기서는 객체 픽셀을 AnyDoor 결과로 바꾸지 않으므로 그 문제를 피하면서
    지금 파이프라인에 없는 그림자만 가져올 수 있다.

    shadow_strength : 0 이면 그림자 없음(= composite() 와 동일), 1 이면 추출된 그대로.
    """
    base = composite(ref_image_rgb, ref_mask, bg_image_rgb, placement_mask,
                     guidance_scale=guidance_scale, seed=seed, method=method)
    if shadow_strength <= 0:
        return base

    _, obj_mask, top_left, _ = _prepare_object(ref_image_rgb, ref_mask, placement_mask)
    object_full = _placed_mask(bg_image_rgb.shape, obj_mask, top_left)

    unload_sam()
    inference_single_image = _import_anydoor()
    # crop_back() 이 정사각형 입력일 때 tar_image 를 제자리에서 덮어쓰므로 사본을 넘긴다
    generated = inference_single_image(
        ref_image_rgb, ref_mask,
        bg_image_rgb.copy(), placement_mask,
        guidance_scale=guidance_scale,
        seed=seed,
    )
    if generated.shape[:2] != bg_image_rgb.shape[:2]:
        generated = cv2.resize(generated, (bg_image_rgb.shape[1], bg_image_rgb.shape[0]))

    shadow = _extract_shadow(generated, bg_image_rgb, object_full // 255)
    if shadow.max() <= 0:
        print("[pipeline] AnyDoor 결과에서 그림자 성분을 찾지 못해 기본 합성을 사용합니다")
        return base

    factor = np.clip(1.0 - shadow * float(shadow_strength), 0.0, 1.0)[:, :, None]
    return np.clip(base.astype(np.float32) * factor, 0, 255).astype(np.uint8)


def _blend_with_original(generated_rgb: np.ndarray, original_bg_rgb: np.ndarray,
                          placement_mask: np.ndarray, feather: int = 2) -> np.ndarray:
    """
    마스크 영역만 생성 결과를 쓰고, 나머지는 원본 배경 그대로 되돌린다.
    경계가 딱딱하게 잘려 보이지 않도록 마스크 가장자리를 살짝 블러(feather)한다.

    주의: feather 는 '픽셀 수'가 아니라 가우시안 시그마다. 실제로 번지는 폭은
    대략 +-3*feather 픽셀이 된다. 이 값을 크게 잡으면 몸통처럼 두꺼운 부위는
    멀쩡한데 다리/꼬리처럼 가는 부위는 블러가 그 폭 전체를 덮어버려서
    알파가 1까지 못 올라가고 안개처럼 흐려진다. (9로 뒀다가 겪은 문제)
    """
    h, w = original_bg_rgb.shape[:2]
    if generated_rgb.shape[:2] != (h, w):
        generated_rgb = cv2.resize(generated_rgb, (w, h))

    mask_f = placement_mask.astype(np.float32)
    if feather > 0:
        mask_f = cv2.GaussianBlur(mask_f, (0, 0), sigmaX=feather)
    mask_f = np.clip(mask_f, 0, 1)[:, :, None]

    blended = generated_rgb.astype(np.float32) * mask_f + original_bg_rgb.astype(np.float32) * (1 - mask_f)
    return np.clip(blended, 0, 255).astype(np.uint8)
