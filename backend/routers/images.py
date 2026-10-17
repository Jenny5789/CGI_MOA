"""명세 3-1 사진 올리기, 3-2 최근 사용한 사진.

- 받는 값: file (jpg/png, 10MB 이하), kind ("garment" 상의 사진 / "person" 인물 사진),
  from_sample ("1"이면 예시 사진에서 고른 것, 생략 가능)
- 돌려주는 값: { image_id, url, width, height }
- 로그인 필요. 올린 회원 번호(user_id)를 함께 기록 → 그 회원만 추출·합성에 쓸 수 있음
- 사진과 정보(json)는 storage/images에 파일로 저장 (추출·합성이 읽는 곳)
- 올린 기록은 DB images 표에도 남긴다 (10/17) → GET /api/images/recent 가 최근 24시간 동안 올린 사진을 보여 줌.
  작은 사진(img_xxx_thumb.jpg, 긴 변 240px)도 함께 만들어 목록을 가볍게 한다
"""
import hashlib
import io
import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.auth import current_user
from backend.config import (ALLOWED_FORMATS, IMAGE_KINDS, IMAGES_DIR, MAX_UPLOAD_BYTES, RECENT_IMAGE_KEEP_HOURS,
                            RECENT_IMAGE_LIMIT)
from backend.db import UploadedImage, User, get_db, utcnow
from backend.errors import ApiError
from backend.file_keys import signed_url

router = APIRouter()
KST = timezone(timedelta(hours=9))


THUMB_SIDE = 240


@router.post("/api/images")
async def upload_image(file: UploadFile = File(...), kind: str = Form(...), from_sample: str = Form("0"),
                       user: User = Depends(current_user), db: Session = Depends(get_db)):
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

    # 최근 사용한 사진 목록용: 작은 사진 + DB 기록
    thumb_name = f"{image_id}_thumb.jpg"
    thumb = img.convert("RGB")
    thumb.thumbnail((THUMB_SIDE, THUMB_SIDE), Image.Resampling.LANCZOS)
    thumb.save(IMAGES_DIR / thumb_name, quality=80)
    db.add(UploadedImage(
        image_id=image_id, user_id=user.id, kind=kind, filename=filename, thumb=thumb_name,
        width=img.width, height=img.height, content_hash=hashlib.sha256(data).hexdigest(),
        from_sample=from_sample == "1", created_at=utcnow(),
    ))
    db.commit()

    return {"image_id": image_id, "url": signed_url(filename), "width": img.width, "height": img.height}


@router.get("/api/images/recent")
def recent_images(kind: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """명세 3-2. 최근 RECENT_IMAGE_KEEP_HOURS 동안 직접 올린 사진 (예시 사진 제외, 같은 파일은 한 번, 최신순)"""
    if kind not in IMAGE_KINDS:
        raise ApiError(400, "INVALID_KIND", "kind는 garment 또는 person이어야 합니다.")
    since = utcnow() - timedelta(hours=RECENT_IMAGE_KEEP_HOURS)
    db.execute(delete(UploadedImage).where(UploadedImage.created_at < since))  # 지난 기록 정리 (모든 회원 것을 함께)
    db.commit()
    rows = db.scalars(
        select(UploadedImage)
        .where(UploadedImage.user_id == user.id, UploadedImage.kind == kind, UploadedImage.from_sample.is_(False))
        .order_by(UploadedImage.created_at.desc())
    ).all()
    items, seen = [], set()
    for r in rows:
        if r.content_hash in seen or not (IMAGES_DIR / r.filename).is_file():
            continue
        seen.add(r.content_hash)
        url = signed_url(r.filename)
        has_thumb = r.thumb and (IMAGES_DIR / r.thumb).is_file()
        items.append({
            "image_id": r.image_id, "url": url, "thumb_url": signed_url(r.thumb) if has_thumb else url,
            "width": r.width, "height": r.height,
            "created_at": r.created_at.replace(tzinfo=timezone.utc).astimezone(KST).isoformat(timespec="seconds"),
        })
        if len(items) >= RECENT_IMAGE_LIMIT:
            break
    return {"items": items}
