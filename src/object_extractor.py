from pathlib import Path
import sys

# 기존 객체 추출/합성 실험 코드
LEGACY_PIPELINE_ROOT = Path.home() / "Desktop" / "compositing_lab"

# 기존 compositing 모듈 사용
sys.path.insert(0, str(LEGACY_PIPELINE_ROOT))

from compositing.segmentation import segment


def extract_with_sam2(
    image_rgb,
    point=None,
    box=None,
    points=None,
    neg_points=None,
):
    """
    기존 객체 추출 파이프라인의 SAM2 기능을
    MOA에서 재사용한다.

    Input
        image_rgb  : RGB 이미지
        point      : 단일 Positive Point (x, y)
        box        : Bounding Box (x1, y1, x2, y2)
        points     : 여러 Positive Points
        neg_points : Negative Points

    Output
        binary_mask: uint8 0/1 Mask
    """

    mask = segment(
        image_rgb=image_rgb,
        point=point,
        box=box,
        points=points,
        neg_points=neg_points,
    )

    return mask