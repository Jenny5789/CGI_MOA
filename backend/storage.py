"""기록 찾기 도우미 (사진·추출 결과·합성 작업 기록은 DB images·extractions·jobs 표에서 읽는다. 합성 결과는 DB results 표, routers/results.py가 다룸).

- 기록마다 user_id(만든 회원 번호)를 적고, 다른 회원의 기록은 "없음"(404)으로 답한다 (있는지 여부도 알리지 않음)
- load_*_info는 db(요청의 DB 세션)를 넘기면 그 세션으로 읽는다. 안 넘기면 별도 세션을 연다 (합성 일꾼 스레드처럼 요청 밖에서 부를 때)
- ensure_cutout: 추출 결과의 cutout 사진은 추출 때 만들지 않고, /api/files로 처음 요청할 때 만든다
"""
import os
import re
import uuid

from PIL import Image

from backend.config import EXTRACTIONS_DIR, IMAGES_DIR
from backend.db import Extraction, Job, UploadedImage, open_session
from backend.errors import ApiError

_ID = re.compile(r"^[a-z]+_[0-9a-f]{12}$")
_CUTOUT_NAME = re.compile(r"^(ext_[0-9a-f]{12})_cutout\.png$")


def is_owner(record, user) -> bool:
    return record.get("user_id") == user.id


def _get(model, key, db):
    """한 행을 읽는다. db(요청의 DB 세션)를 받았으면 그것으로, 없으면 별도 세션을 열어서 (합성 일꾼 스레드처럼 요청 밖에서 부를 때).
    세션을 닫은 뒤에도 읽어 둔 칸은 쓸 수 있다"""
    if db is not None:
        return db.get(model, key)
    with open_session() as s:
        return s.get(model, key)


def load_image_info(image_id, user=None, db=None):
    """사진 올리기(3-1) 때 DB images 표에 남긴 정보. 없거나 (user를 주면) 남의 것이면 404.
    돌려주는 모양은 예전 json 기록과 같다 (image_id, user_id, kind, width, height, filename)"""
    not_found = ApiError(404, "IMAGE_NOT_FOUND", "사진을 찾을 수 없습니다. 다시 올려 주세요.")
    if not isinstance(image_id, str) or not _ID.match(image_id):
        raise not_found
    row = _get(UploadedImage, image_id, db)
    if row is None or (user is not None and row.user_id != user.id):
        raise not_found
    return {"image_id": row.image_id, "user_id": row.user_id, "kind": row.kind,
            "width": row.width, "height": row.height, "filename": row.filename}


def load_extraction_info(extraction_id, user=None, db=None):
    """상의 추출(4-1) 때 DB extractions 표에 남긴 정보. 없거나 (user를 주면) 남의 것이면 404.
    돌려주는 모양은 예전 json 기록과 같다 (extraction_id, user_id, image_id, width, height, mask, cutout)"""
    not_found = ApiError(404, "EXTRACTION_NOT_FOUND", "추출 결과를 찾을 수 없습니다. 다시 추출해 주세요.")
    if not isinstance(extraction_id, str) or not _ID.match(extraction_id):
        raise not_found
    row = _get(Extraction, extraction_id, db)
    if row is None or (user is not None and row.user_id != user.id):
        raise not_found
    return {"extraction_id": row.extraction_id, "user_id": row.user_id, "image_id": row.image_id,
            "width": row.width, "height": row.height, "mask": row.mask, "cutout": row.cutout}


def job_to_dict(row):
    """DB jobs 행 → 예전 json 기록과 같은 모양 (routers/compose.py가 메모리에 두는 작업 정보도 이 모양)"""
    return {"job_id": row.job_id, "user_id": row.user_id, "status": row.status, "progress": row.progress,
            "result_id": row.result_id, "error": row.error, "extraction_id": row.extraction_id,
            "person_image_id": row.person_image_id, "area_mask": row.area_mask, "garment_mask": row.garment_mask,
            "refine": row.refine, "shape_control": row.shape_control, "seed": row.seed}


def load_job_info(job_id, db=None):
    """합성 요청(5-1) 때 DB jobs 표에 남긴 작업 기록. 형식이 틀리거나 없으면 404 (주인 확인은 부르는 쪽에서)."""
    not_found = ApiError(404, "JOB_NOT_FOUND", "작업을 찾을 수 없습니다.")
    if not isinstance(job_id, str) or not _ID.match(job_id):
        raise not_found
    row = _get(Job, job_id, db)
    if row is None:
        raise not_found
    return job_to_dict(row)


def ensure_cutout(name):
    """추출 결과의 cutout 사진(ext_xxx_cutout.png)이 없으면 만든다: 상의 사진에 윤곽을 투명도로 입힌 PNG.
    화면이 쓰지 않는 파일을 원본 크기로 저장하느라 추출 응답이 늦어지지 않게, 추출 때는 만들지 않고 처음 요청할 때 만든다 (11/9).
    파일이 있거나 새로 만들었으면 True, 이 이름으로 만들 수 있는 사진이 아니면 False.
    열쇠(?key=)는 부르는 쪽(routers/files.py)이 이미 확인했다"""
    match = _CUTOUT_NAME.match(name)
    if match is None:
        return False
    path = EXTRACTIONS_DIR / name
    if path.is_file():
        return True
    try:
        ext = load_extraction_info(match.group(1))
        if ext["cutout"] != name:
            return False
        info = load_image_info(ext["image_id"])
        image = Image.open(IMAGES_DIR / info["filename"]).convert("RGB").convert("RGBA")
        image.putalpha(Image.open(EXTRACTIONS_DIR / ext["mask"]).convert("L"))
    except (ApiError, OSError):  # 기록이 없거나 사진·윤곽 파일이 없음
        return False
    tmp = EXTRACTIONS_DIR / f"{name}.{uuid.uuid4().hex[:8]}.tmp"  # 동시에 요청이 와도 쓰다 만 파일이 보이지 않게 임시 이름에 쓰고 바꾼다
    try:
        image.save(tmp, format="PNG")
        os.replace(tmp, path)
    except OSError:
        tmp.unlink(missing_ok=True)
        return False
    return True
