"""기록 찾기 도우미 (사진·추출 결과·합성 작업은 DB images·extractions·jobs 표, 합성 결과는 아직 storage/ 폴더의 json).

- 기록마다 user_id(만든 회원 번호)를 적고, 다른 회원의 기록은 "없음"(404)으로 답한다 (있는지 여부도 알리지 않음)
"""
import re
from datetime import datetime, timedelta, timezone

from backend.db import Extraction, Job, UploadedImage, open_session
from backend.errors import ApiError

KST = timezone(timedelta(hours=9))
_ID = re.compile(r"^[a-z]+_[0-9a-f]{12}$")


def now_kst():
    return datetime.now(KST).isoformat(timespec="seconds")


def is_owner(record, user) -> bool:
    return record.get("user_id") == user.id


def load_image_info(image_id, user=None):
    """사진 올리기(3-1) 때 DB images 표에 남긴 정보. 없거나 (user를 주면) 남의 것이면 404.
    돌려주는 모양은 예전 json 기록과 같다 (image_id, user_id, kind, width, height, filename)"""
    not_found = ApiError(404, "IMAGE_NOT_FOUND", "사진을 찾을 수 없습니다. 다시 올려 주세요.")
    if not isinstance(image_id, str) or not _ID.match(image_id):
        raise not_found
    with open_session() as s:  # 합성 일꾼 스레드에서도 불리므로 요청과 별도의 세션
        row = s.get(UploadedImage, image_id)
    if row is None or (user is not None and row.user_id != user.id):
        raise not_found
    return {"image_id": row.image_id, "user_id": row.user_id, "kind": row.kind,
            "width": row.width, "height": row.height, "filename": row.filename}


def load_extraction_info(extraction_id, user=None):
    """상의 추출(4-1) 때 DB extractions 표에 남긴 정보. 없거나 (user를 주면) 남의 것이면 404.
    돌려주는 모양은 예전 json 기록과 같다 (extraction_id, user_id, image_id, width, height, mask, cutout)"""
    not_found = ApiError(404, "EXTRACTION_NOT_FOUND", "추출 결과를 찾을 수 없습니다. 다시 추출해 주세요.")
    if not isinstance(extraction_id, str) or not _ID.match(extraction_id):
        raise not_found
    with open_session() as s:  # 합성 일꾼 스레드에서도 불리므로 요청과 별도의 세션
        row = s.get(Extraction, extraction_id)
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


def load_job_info(job_id):
    """합성 요청(5-1) 때 DB jobs 표에 남긴 작업 기록. 형식이 틀리거나 없으면 404 (주인 확인은 부르는 쪽에서)."""
    not_found = ApiError(404, "JOB_NOT_FOUND", "작업을 찾을 수 없습니다.")
    if not isinstance(job_id, str) or not _ID.match(job_id):
        raise not_found
    with open_session() as s:
        row = s.get(Job, job_id)
    if row is None:
        raise not_found
    return job_to_dict(row)
