"""명세 4-1 상의 추출 (SAM2).

- 받는 값: { image_id, points: [{ x, y, label }] }
  - x, y: 사진 안 위치를 0~1 비율로 (왼쪽 위 0,0 / 오른쪽 아래 1,1)
  - label: 1 포함(왼쪽 클릭), 0 제외(오른쪽 클릭)
- 돌려주는 값: { extraction_id, mask_url, cutout_url, bbox: { x, y, w, h } }
  - mask: 원본과 같은 크기 흑백 PNG (상의 255, 나머지 0)
  - cutout: 상의만 남기고 배경을 투명하게 한 PNG
  - bbox: 상의를 감싸는 사각형 (원본 픽셀 기준)
- SAM2는 features/object_extraction의 extract_object를 그대로 쓴다 (처음 요청 때 모델을 불러와 이후 재사용)
- 임시: 로그인 확인 없음, 결과는 storage/extractions에 파일로 저장
"""
import json
import time
import uuid
from typing import List, Literal

import numpy as np
from fastapi import APIRouter
from PIL import Image
from pydantic import BaseModel, Field

from backend.config import EXTRACTIONS_DIR, IMAGES_DIR
from backend.errors import ApiError
from backend.gpu import GPU_LOCK
from backend.storage import load_image_info, now_kst
from features.object_extraction import extract_object

router = APIRouter()


class Point(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    label: Literal[0, 1]


class ExtractRequest(BaseModel):
    image_id: str
    points: List[Point] = Field(min_length=1)


def _to_pixel(ratio, size):
    # 0~1 비율 -> 픽셀 좌표. 1.0(오른쪽/아래 끝)은 마지막 픽셀로
    return min(int(ratio * size), size - 1)


@router.post("/api/extract")
def extract(req: ExtractRequest):
    info = load_image_info(req.image_id)
    w, h = info["width"], info["height"]

    pos = [(_to_pixel(p.x, w), _to_pixel(p.y, h)) for p in req.points if p.label == 1]
    neg = [(_to_pixel(p.x, w), _to_pixel(p.y, h)) for p in req.points if p.label == 0]
    if not pos:
        raise ApiError(400, "NO_POSITIVE_POINT", "상의 위에 포함 점(왼쪽 클릭)을 하나 이상 찍어 주세요.")

    image_rgb = np.array(Image.open(IMAGES_DIR / info["filename"]).convert("RGB"))

    started = time.perf_counter()
    try:
        with GPU_LOCK:
            mask = extract_object(image_rgb, points=pos, neg_points=neg)
    except RuntimeError:
        # 빈 마스크 (extract_object가 RuntimeError로 알려 줌)
        raise ApiError(400, "EMPTY_MASK", "상의를 찾지 못했습니다. 점 위치를 바꿔 다시 시도해 주세요.")
    elapsed = time.perf_counter() - started

    ys, xs = np.nonzero(mask)
    bbox = {"x": int(xs.min()), "y": int(ys.min()), "w": int(xs.max() - xs.min() + 1), "h": int(ys.max() - ys.min() + 1)}

    extraction_id = "ext_" + uuid.uuid4().hex[:12]
    mask_name = f"{extraction_id}_mask.png"
    cutout_name = f"{extraction_id}_cutout.png"
    EXTRACTIONS_DIR.mkdir(parents=True, exist_ok=True)

    alpha = Image.fromarray(mask * 255)
    alpha.save(EXTRACTIONS_DIR / mask_name)
    cutout = Image.fromarray(image_rgb).convert("RGBA")
    cutout.putalpha(alpha)
    cutout.save(EXTRACTIONS_DIR / cutout_name)

    record = {
        "extraction_id": extraction_id,
        "image_id": req.image_id,
        "points": [p.model_dump() for p in req.points],
        "bbox": bbox,
        "width": w,
        "height": h,
        "mask": mask_name,
        "cutout": cutout_name,
        "seconds": round(elapsed, 3),
        "created_at": now_kst(),
    }
    (EXTRACTIONS_DIR / f"{extraction_id}.json").write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")

    return {
        "extraction_id": extraction_id,
        "mask_url": f"/api/files/{mask_name}",
        "cutout_url": f"/api/files/{cutout_name}",
        "bbox": bbox,
    }
