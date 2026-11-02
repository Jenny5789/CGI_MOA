"""기록 찾기 도우미 (사진은 DB images 표, 추출 결과는 아직 storage/ 폴더의 json).

- 기록마다 user_id(만든 회원 번호)를 적고, 다른 회원의 기록은 "없음"(404)으로 답한다 (있는지 여부도 알리지 않음)
"""
import json
import re
from datetime import datetime, timedelta, timezone

from backend.config import EXTRACTIONS_DIR
from backend.db import UploadedImage, open_session
from backend.errors import ApiError

KST = timezone(timedelta(hours=9))
_ID = re.compile(r"^[a-z]+_[0-9a-f]{12}$")


def now_kst():
    return datetime.now(KST).isoformat(timespec="seconds")


def is_owner(record, user) -> bool:
    return record.get("user_id") == user.id


def _load(directory, item_id, code, message, user=None):
    """기록 읽기. user를 주면 그 회원 것이 아닐 때도 없는 것처럼 404"""
    if not isinstance(item_id, str) or not _ID.match(item_id):
        raise ApiError(404, code, message)
    path = directory / f"{item_id}.json"
    if not path.is_file():
        raise ApiError(404, code, message)
    record = json.loads(path.read_text(encoding="utf-8"))
    if user is not None and not is_owner(record, user):
        raise ApiError(404, code, message)
    return record


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
    """상의 추출(4-1) 때 저장한 정보. 없거나 (user를 주면) 남의 것이면 404."""
    return _load(EXTRACTIONS_DIR, extraction_id, "EXTRACTION_NOT_FOUND", "추출 결과를 찾을 수 없습니다. 다시 추출해 주세요.", user)
