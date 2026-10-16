"""명세 3-1 사진 올리기.

- 받는 값: file (jpg/png, 10MB 이하), kind ("garment" 상의 사진 / "person" 인물 사진)
- 돌려주는 값: { image_id, url, width, height }
- 로그인 필요. 올린 회원 번호(user_id)를 함께 기록 → 그 회원만 추출·합성에 쓸 수 있음
- 사진과 정보(json)는 DB 없이 storage/images에 파일로 저장
"""
import io
import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from backend.auth import current_user
from backend.config import ALLOWED_FORMATS, IMAGE_KINDS, IMAGES_DIR, MAX_UPLOAD_BYTES
from backend.db import User
from backend.errors import ApiError
from backend.file_keys import signed_url

router = APIRouter()
KST = timezone(timedelta(hours=9))


@router.post("/api/images")
async def upload_image(file: UploadFile = File(...), kind: str = Form(...), user: User = Depends(current_user)):
    if kind not in IMAGE_KINDS:
        raise ApiError(400, "INVALID_KIND", "kind는 garment 또는 person이어야 합니다.")

    # 10MB를 넘으면 끝까지 읽지 않고 거절
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise ApiError(400, "IMAGE_TOO_LARGE", "사진은 10MB 이하만 올릴 수 있습니다.")

    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError):
        raise ApiError(400, "INVALID_IMAGE", "이미지를 읽을 수 없습니다.")
    if img.format not in ALLOWED_FORMATS:
        raise ApiError(400, "INVALID_IMAGE", "jpg 또는 png 사진만 올릴 수 있습니다.")

    # 휴대폰 사진의 회전 정보(EXIF)를 반영해 바로 세워 저장한다.
    # 화면에 보이는 방향과 SAM2가 보는 방향이 같아야 찍은 점 위치가 맞는다.
    ext = ALLOWED_FORMATS[img.format]
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGBA" if ext == ".png" and "A" in img.getbands() else "RGB")

    image_id = "img_" + uuid.uuid4().hex[:12]
    filename = image_id + ext
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    if ext == ".jpg":
        img.save(IMAGES_DIR / filename, quality=95)
    else:
        img.save(IMAGES_DIR / filename)

    info = {
        "image_id": image_id,
        "user_id": user.id,
        "kind": kind,
        "width": img.width,
        "height": img.height,
        "filename": filename,
        "created_at": datetime.now(KST).isoformat(timespec="seconds"),
    }
    (IMAGES_DIR / f"{image_id}.json").write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")

    return {"image_id": image_id, "url": signed_url(filename), "width": img.width, "height": img.height}
