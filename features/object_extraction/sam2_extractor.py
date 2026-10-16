"""SAM2 객체 추출.

입력: RGB uint8 이미지 (H, W, 3) + 원본 픽셀 좌표의 point / box 프롬프트
출력: uint8 0/1 마스크 (H, W)

모델은 처음 호출할 때 한 번만 로딩하고 이후 재사용한다.
"""
import cv2
import numpy as np

from . import config


class Sam2Extractor:
    def __init__(self, checkpoint=None, model_config=None, device=None):
        self.checkpoint = checkpoint or config.SAM2_CHECKPOINT
        self.model_config = model_config or config.SAM2_CONFIG
        self.device = device or config.SAM2_DEVICE or None
        self._predictor = None

    def _load(self):
        if self._predictor is not None:
            return self._predictor

        import torch
        from sam2.build_sam import build_sam2
        from sam2.sam2_image_predictor import SAM2ImagePredictor

        if self.device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"

        model = build_sam2(self.model_config, self.checkpoint, device=self.device)
        self._predictor = SAM2ImagePredictor(model)
        return self._predictor

    def extract(
        self,
        image_rgb,
        points=None,
        neg_points=None,
        box=None,
        multimask=None,
        postprocess=True,
    ):
        """객체 마스크를 반환한다.

        image_rgb  : np.ndarray, RGB uint8, (H, W, 3)
        points     : [(x, y), ...] 객체 위 positive point
        neg_points : [(x, y), ...] 제외할 영역의 negative point
        box        : (x1, y1, x2, y2)
        multimask  : None이면 자동. point 1개만 줬을 때만 후보 3개 중 score 최대를
                     고르고, point가 여러 개이거나 box가 있으면 단일 마스크를 쓴다
                     (여러 프롬프트에서 후보 선택은 작은 부분만 고르는 경향이 있음)
        postprocess: 포함 점이 찍힌 연결 영역만 남기고(점이 없으면 가장 큰 영역) 작은 내부 구멍을 채운다

        return     : np.ndarray, uint8 0/1, (H, W)
        """
        _check_image(image_rgb)
        h, w = image_rgb.shape[:2]

        points = [tuple(p) for p in (points or [])]
        neg_points = [tuple(p) for p in (neg_points or [])]
        if not points and not neg_points and box is None:
            raise ValueError("points, neg_points, box 중 하나 이상이 필요합니다.")
        _check_coords(points + neg_points, box, w, h)

        if multimask is None:
            multimask = len(points) + len(neg_points) == 1 and box is None
        kwargs = {"multimask_output": multimask}
        if points or neg_points:
            kwargs["point_coords"] = np.array(points + neg_points, dtype=np.float32)
            kwargs["point_labels"] = np.array(
                [1] * len(points) + [0] * len(neg_points), dtype=np.int32
            )
        if box is not None:
            kwargs["box"] = np.array(box, dtype=np.float32)

        import torch

        predictor = self._load()
        with torch.inference_mode(), torch.autocast(
            device_type=self.device,
            dtype=torch.bfloat16,
            enabled=(self.device == "cuda"),
        ):
            predictor.set_image(image_rgb)
            masks, scores, _ = predictor.predict(**kwargs)

        mask = masks[int(np.argmax(scores))].astype(np.uint8)

        if postprocess:
            mask = keep_clicked_components(mask, points)
            mask = fill_small_holes(mask)

        if mask.sum() == 0:
            raise RuntimeError("빈 마스크가 생성되었습니다. 프롬프트를 바꿔 다시 시도하세요.")
        return mask


_default_extractor = None


def extract_object(image_rgb, points=None, neg_points=None, box=None, **kwargs):
    """모듈 단위 진입점. 기본 extractor를 한 번만 만들어 재사용한다."""
    global _default_extractor
    if _default_extractor is None:
        _default_extractor = Sam2Extractor()
    return _default_extractor.extract(
        image_rgb, points=points, neg_points=neg_points, box=box, **kwargs
    )


def keep_clicked_components(mask, points=(), close_kernel_px=15):
    """포함 점이 찍힌 연결 영역을 모두 남긴다 (팔 등에 가려 상의가 여러 조각으로 나뉜 경우).
    점이 하나도 영역 위에 없으면(박스만 준 경우 등) 가장 큰 연결 영역만 남긴다.
    연결 판단은 closing한 사본으로 한다."""
    closed = cv2.morphologyEx(
        mask, cv2.MORPH_CLOSE, np.ones((close_kernel_px, close_kernel_px), np.uint8)
    )
    n, labels, stats, _ = cv2.connectedComponentsWithStats(closed, connectivity=8)
    if n <= 1:
        return mask
    keep = {int(labels[int(y), int(x)]) for x, y in points} - {0}
    if not keep:
        keep = {1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))}
    return mask & np.isin(labels, list(keep)).astype(np.uint8)


def fill_small_holes(mask, max_hole_area=400):
    """마스크 내부의 작은 구멍(max_hole_area 이하)을 채운다."""
    inv = (1 - mask).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(inv, connectivity=8)
    out = mask.copy()
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] <= max_hole_area:
            out[labels == i] = 1
    return out


def _check_image(image_rgb):
    if not isinstance(image_rgb, np.ndarray) or image_rgb.ndim != 3 or image_rgb.shape[2] != 3:
        raise ValueError("image_rgb는 (H, W, 3) RGB 배열이어야 합니다.")
    if image_rgb.dtype != np.uint8:
        raise ValueError("image_rgb는 uint8이어야 합니다.")


def _check_coords(pts, box, w, h):
    for x, y in pts:
        if not (0 <= x < w and 0 <= y < h):
            raise ValueError(f"좌표 ({x}, {y})가 이미지 범위({w}x{h})를 벗어났습니다.")
    if box is not None:
        x1, y1, x2, y2 = box
        if not (0 <= x1 < x2 <= w and 0 <= y1 < y2 <= h):
            raise ValueError(f"box {box}가 올바르지 않습니다.")
